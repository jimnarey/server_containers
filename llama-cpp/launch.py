#!/usr/bin/env python3
"""Start or stop one rendered llama.cpp profile by its literal service name.

Examples:

    ./llama-cpp/launch.py llama-cpp-gpu-1
    ./llama-cpp/launch.py --down llama-cpp-generel-schwerz-16gb-gpu-1

The supplied service name must match ``SERVICE_NAME`` in exactly one env file
under ``llama-cpp/config``.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys


SCRIPT_DIRECTORY = Path(__file__).resolve().parent
PROJECT_DIRECTORY = SCRIPT_DIRECTORY.parent
CONFIG_DIRECTORY = SCRIPT_DIRECTORY / "config"
RENDERER = SCRIPT_DIRECTORY / "render-compose.py"
COMPOSE_FILE = PROJECT_DIRECTORY / "compose.ai.yml"


def profile_files() -> list[Path]:
    if not CONFIG_DIRECTORY.is_dir():
        raise ValueError(f"configuration directory is missing: {CONFIG_DIRECTORY}")
    files = sorted(path for path in CONFIG_DIRECTORY.glob("*/*.env") if path.is_file())
    if not files:
        raise ValueError(f"no .env files exist below {CONFIG_DIRECTORY}")
    return files


def service_name(profile: Path) -> str:
    """Read the renderer-required SERVICE_NAME field without evaluating the env file."""
    for raw_line in profile.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        key, separator, value = line.partition("=")
        if separator and key.strip() == "SERVICE_NAME":
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            if value:
                return value
    raise ValueError(f"{profile} has no non-empty SERVICE_NAME")


def resolve_service(name: str) -> Path:
    """Return the one profile whose declared service name exactly matches name."""
    matches = [profile for profile in profile_files() if service_name(profile) == name]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        paths = ", ".join(str(profile.relative_to(CONFIG_DIRECTORY)) for profile in matches)
        raise ValueError(f"service name {name!r} is declared by multiple env files: {paths}")
    available = ", ".join(service_name(profile) for profile in profile_files())
    raise ValueError(f"unknown service {name!r}; choose one of: {available}")


def render(profile: Path) -> Path:
    result = subprocess.run(
        [sys.executable, os.fspath(RENDERER), os.fspath(profile)],
        cwd=PROJECT_DIRECTORY,
        text=True,
        stdout=subprocess.PIPE,
    )
    if result.returncode:
        raise RuntimeError(f"renderer failed with exit status {result.returncode}")
    output = result.stdout.strip()
    if not output:
        raise RuntimeError("renderer did not print a Compose file path")
    rendered = Path(output)
    if not rendered.is_file():
        raise RuntimeError(f"renderer printed a missing Compose file: {rendered}")
    return rendered


def compose_command(profile: Path, rendered: Path, *, down: bool) -> list[str]:
    command = [
        "docker", "compose",
        "-f", os.fspath(COMPOSE_FILE),
        "-f", os.fspath(rendered),
    ]
    name = service_name(profile)
    if down:
        # Deliberately do not use project-wide `compose down`: it would affect
        # unrelated services in the shared Compose project.
        return [*command, "stop", name]
    return [*command, "up", "-d", "--build", "--no-deps", name]


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("service", help="literal SERVICE_NAME declared by a config env file")
    parser.add_argument("--down", action="store_true", help="stop the selected service instead of starting it")
    parser.add_argument("--dry-run", action="store_true", help="resolve and render, then print the Compose command")
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    try:
        profile = resolve_service(arguments.service)
        rendered = render(profile)
        command = compose_command(profile, rendered, down=arguments.down)
    except (OSError, RuntimeError, ValueError) as error:
        print(f"launch.py: {error}", file=sys.stderr)
        return 2

    action = "stopping" if arguments.down else "starting"
    print(f"{action} {service_name(profile)} from {profile.relative_to(PROJECT_DIRECTORY)}", file=sys.stderr)
    if arguments.dry_run:
        print(" ".join(command))
        return 0
    return subprocess.run(command, cwd=PROJECT_DIRECTORY).returncode


if __name__ == "__main__":
    raise SystemExit(main())
