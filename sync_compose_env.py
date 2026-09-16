#!/usr/bin/env python3
"""Create or extend a Compose interpolation environment file."""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Iterator
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("sync_compose_env.py requires PyYAML (install python3-yaml).")


# Only ${NAME-default} and ${NAME:-default} supply values suitable for .env.
INTERPOLATION = re.compile(
    r"(?<!\$)\$\{(?P<name>[A-Za-z_][A-Za-z0-9_]*)"
    r"(?:(?P<operator>:-|-|:\?|\?|:\+|\+)(?P<operand>[^}]*))?\}"
)
ASSIGNMENT = re.compile(r"^\s*(?:export\s+)?(?P<name>[A-Za-z_][A-Za-z0-9_]*)=.*$")


def iter_strings(value: object) -> Iterator[str]:
    """Yield all scalar strings inside a parsed Compose service block."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, nested in value.items():
            yield from iter_strings(key)
            yield from iter_strings(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from iter_strings(nested)


def include_paths(document: dict[object, object], parent: Path) -> Iterator[Path]:
    """Yield Compose include paths, resolving them relative to their file."""
    includes = document.get("include", [])
    if isinstance(includes, (str, dict)):
        includes = [includes]
    if not isinstance(includes, list):
        raise ValueError(f"{parent}: include must be a list, mapping, or string")
    for entry in includes:
        paths = entry if isinstance(entry, str) else entry.get("path") if isinstance(entry, dict) else None
        if isinstance(paths, str):
            yield parent.parent / paths
        elif isinstance(paths, list) and all(isinstance(path, str) for path in paths):
            for path in paths:
                yield parent.parent / path
        elif paths is not None:
            raise ValueError(f"{parent}: include path must be a string or list of strings")


def collect_variables(files: list[Path]) -> tuple[dict[str, str], list[str]]:
    """Collect interpolation variables from service blocks in encounter order."""
    variables: dict[str, str] = {}
    conflicts: list[str] = []
    seen: set[Path] = set()

    def visit(compose_file: Path) -> None:
        compose_file = compose_file.resolve()
        if compose_file in seen:
            return
        seen.add(compose_file)
        try:
            document = yaml.safe_load(compose_file.read_text()) or {}
        except OSError as error:
            raise ValueError(f"cannot read {compose_file}: {error}") from error
        except yaml.YAMLError as error:
            raise ValueError(f"cannot parse {compose_file}: {error}") from error

        if not isinstance(document, dict):
            raise ValueError(f"{compose_file}: document must be a mapping")
        for included_file in include_paths(document, compose_file):
            visit(included_file)

        services = document.get("services", {})
        if not isinstance(services, dict):
            raise ValueError(f"{compose_file}: services must be a mapping")
        for service_name, service in services.items():
            if not isinstance(service, dict):
                raise ValueError(f"{compose_file}: service {service_name!r} must be a mapping")
            for text in iter_strings(service):
                for match in INTERPOLATION.finditer(text):
                    name = match.group("name")
                    operator = match.group("operator")
                    default = match.group("operand") if operator in {":-", "-"} else ""
                    if name not in variables:
                        variables[name] = default
                    elif default and variables[name] and default != variables[name]:
                        conflicts.append(
                            f"{name}: keeping first default {variables[name]!r}; "
                            f"also found {default!r} in {compose_file}"
                        )
                    elif default and not variables[name]:
                        variables[name] = default

    for compose_file in files:
        visit(compose_file)
    return variables, conflicts


def merge_env(
    env_file: Path, variables: dict[str, str], keep_overwritten: bool
) -> tuple[str, list[str]]:
    """Keep existing values, remove/comment duplicate declarations, append gaps."""
    lines = env_file.read_text().splitlines(keepends=True) if env_file.exists() else []
    active: dict[str, list[int]] = {}
    for index, line in enumerate(lines):
        match = ASSIGNMENT.match(line.rstrip("\r\n"))
        if match:
            active.setdefault(match.group("name"), []).append(index)

    overwritten: list[str] = []
    for name, indexes in active.items():
        # Compose uses the final declaration. Earlier active duplicates are
        # superseded and are either removed or retained as comments.
        for index in indexes[:-1]:
            overwritten.append(f"{name} (line {index + 1})")
            lines[index] = "# " + lines[index] if keep_overwritten else ""

    missing = [name for name in variables if name not in active]
    if missing:
        if lines and not lines[-1].endswith(("\n", "\r")):
            lines[-1] += "\n"
        if lines and lines[-1].strip():
            lines.append("\n")
        lines.extend(f"{name}={variables[name]}\n" for name in missing)
    return "".join(lines), overwritten


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create or extend a .env file from Compose service interpolation."
    )
    parser.add_argument(
        "compose_files", nargs="+", type=Path, metavar="COMPOSE_FILE",
        help="Compose files to inspect, in any desired combination.",
    )
    parser.add_argument(
        "--env-file", type=Path, default=Path(".env"),
        help="Environment file to create or update (default: .env).",
    )
    parser.add_argument(
        "--keep-overwritten", action="store_true",
        help=("Comment out earlier duplicate active declarations instead of "
              "removing them. Existing final declarations are never replaced."),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        variables, conflicts = collect_variables(args.compose_files)
        content, overwritten = merge_env(
            args.env_file, variables, args.keep_overwritten
        )
        args.env_file.write_text(content)
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    print(f"{args.env_file}: {len(variables)} Compose variable(s) considered")
    if overwritten:
        action = "commented" if args.keep_overwritten else "removed"
        print(f"{args.env_file}: {action} duplicate declaration(s): " + ", ".join(overwritten))
    for conflict in conflicts:
        print(f"warning: {conflict}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
