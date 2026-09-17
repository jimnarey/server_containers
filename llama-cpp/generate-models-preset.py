#!/usr/bin/env python3
"""Generate or validate a llama.cpp models-preset.ini override file.

The ordinary llama-cpp router intentionally has no --models-dir argument, so
its /v1/models endpoint only contains models which are already in its preset.
This tool starts a disposable router with --models-dir /models, asks that
router for its generated IDs and resolved model paths, then removes it.  It
never changes the running llama-cpp service or the model library.

With --preset-only it instead validates only the /models paths explicitly
listed in the template and writes that template unchanged.  This is useful for
fork-specific services whose model catalogues must remain deliberately small.
"""

from __future__ import annotations

import argparse
import atexit
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from typing import Iterable


# Change this once for this host, or override it for one invocation with
# LLAMA_CPP_MODEL_ROOT=/another/library.  It is mounted in the discovery
# container as /models, matching docker-compose.yml.
MODEL_ROOT = Path(os.environ.get("LLAMA_CPP_MODEL_ROOT", "/mnt/data/models/gguf"))

PROJECT_DIR = Path(__file__).resolve().parent.parent
COMPOSE_FILE = PROJECT_DIR / "docker-compose.yml"
DEFAULT_CTX_SIZE = "65536"
DEFAULT_PARALLEL = "1"
DISCOVERY_TIMEOUT_SECONDS = 90

SECTION_RE = re.compile(r"^\s*\[([^]\r\n]+)]\s*(?:[;#].*)?$")
SETTING_RE = re.compile(r"^\s*([^=;#\s][^=;#]*?)\s*=\s*(.*?)\s*$")
SHARDED_GGUF_RE = re.compile(
    r"^(?P<prefix>.+-)(?P<index>\d+)-of-(?P<total>\d+)(?P<suffix>\.gguf)$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Model:
    """The public ID and /models path reported by llama-server."""

    identifier: str
    path: str


@dataclass(frozen=True)
class PresetPath:
    """A local model-library file reference from an explicit preset section."""

    section: str
    setting: str
    path: str


def parse_preset(text: str) -> tuple[set[str], set[str], bool, bool, list[PresetPath]]:
    """Return section IDs, explicit model paths, global-default flags, and file paths."""
    section_names: set[str] = set()
    model_paths: set[str] = set()
    preset_paths: list[PresetPath] = []
    section: str | None = None
    has_version = False
    has_wildcard = False

    for raw_line in text.splitlines():
        match = SECTION_RE.match(raw_line)
        if match:
            section = match.group(1).strip()
            section_names.add(section)
            has_wildcard |= section == "*"
            continue

        match = SETTING_RE.match(raw_line)
        if not match:
            continue
        key, value = match.group(1).strip().lower(), match.group(2).strip()
        if section is None and key == "version":
            has_version = True
        if section is not None and key == "model":
            model_paths.add(value)
        if section is not None and value.startswith("/models/"):
            preset_paths.append(PresetPath(section, key, value))

    return section_names, model_paths, has_version, has_wildcard, preset_paths


def validate_preset_paths(preset_paths: Iterable[PresetPath]) -> None:
    """Raise a readable error when an explicit model-library file is absent.

    llama.cpp opens sharded GGUFs from the first shard.  Checking just that
    file gives an unhelpful later load failure when a sibling is missing, so
    validate the complete shard set here as well.
    """
    missing: dict[str, list[str]] = {}

    def add_missing(section: str, description: str) -> None:
        missing.setdefault(section, []).append(description)

    for preset_path in preset_paths:
        relative = Path(preset_path.path).relative_to("/models")
        if ".." in relative.parts:
            add_missing(
                preset_path.section,
                f"{preset_path.setting}: {preset_path.path} (path escapes /models)",
            )
            continue

        host_path = MODEL_ROOT.joinpath(*relative.parts)
        if not host_path.is_file():
            add_missing(preset_path.section, f"{preset_path.setting}: {preset_path.path}")
            continue

        shard_match = SHARDED_GGUF_RE.match(host_path.name)
        if not shard_match:
            continue

        index_width = len(shard_match["index"])
        total_width = len(shard_match["total"])
        total = int(shard_match["total"])
        for index in range(1, total + 1):
            sibling = host_path.with_name(
                f"{shard_match['prefix']}{index:0{index_width}d}-of-"
                f"{total:0{total_width}d}{shard_match['suffix']}"
            )
            if not sibling.is_file():
                sibling_path = Path("/models").joinpath(*relative.parent.parts, sibling.name)
                add_missing(preset_path.section, f"{preset_path.setting} shard: {sibling_path}")

    if not missing:
        return

    details = []
    for section, paths in missing.items():
        details.append(f"  [{section}]")
        details.extend(f"    - {path}" for path in paths)
    raise RuntimeError(
        "Preset references missing files under "
        f"{MODEL_ROOT}:\n" + "\n".join(details)
    )


def find_model_path(args: object) -> str | None:
    """Extract --model from llama-server's per-model command line."""
    if not isinstance(args, list):
        return None
    for index, value in enumerate(args):
        if not isinstance(value, str):
            continue
        if value == "--model" and index + 1 < len(args) and isinstance(args[index + 1], str):
            return args[index + 1]
        if value.startswith("--model="):
            return value.partition("=")[2]
    return None


def models_from_response(payload: object) -> list[Model]:
    """Parse IDs and paths from llama-server's OpenAI-compatible response."""
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise RuntimeError("Unexpected /v1/models response: expected an object with a data list.")

    models: list[Model] = []
    for item in payload["data"]:
        if not isinstance(item, dict):
            continue
        identifier = item.get("id")
        status = item.get("status")
        path = find_model_path(status.get("args") if isinstance(status, dict) else None)
        if isinstance(identifier, str) and identifier and isinstance(path, str) and path:
            models.append(Model(identifier, path))

    duplicate_ids = sorted(
        identifier for identifier in {model.identifier for model in models}
        if sum(model.identifier == identifier for model in models) > 1
    )
    if duplicate_ids:
        raise RuntimeError(f"Discovery returned duplicate model IDs: {', '.join(duplicate_ids)}")
    if not models:
        raise RuntimeError("Discovery router returned no model IDs with model paths.")
    return sorted(models, key=lambda model: model.identifier.casefold())


def free_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def run_command(command: list[str], *, env: dict[str, str] | None = None) -> str:
    try:
        result = subprocess.run(
            command,
            cwd=PROJECT_DIR,
            env=env,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError as error:
        raise RuntimeError(f"Required command not found: {command[0]}") from error
    except subprocess.CalledProcessError as error:
        detail = error.stderr.strip() or error.stdout.strip()
        raise RuntimeError(f"Command failed: {' '.join(command)}\n{detail}") from error
    return result.stdout.strip()


def get_json(url: str) -> object:
    try:
        with urllib.request.urlopen(url, timeout=3) as response:
            return json.load(response)
    # During startup the TCP listener can briefly accept and reset a request;
    # treat that like an ordinary not-ready connection and retry it.
    except (urllib.error.URLError, OSError, TimeoutError, json.JSONDecodeError) as error:
        raise RuntimeError(str(error)) from error


def discover_models() -> list[Model]:
    """Start a temporary directory-discovery router and return its model list."""
    if not MODEL_ROOT.is_dir():
        raise RuntimeError(f"MODEL_ROOT does not exist or is not a directory: {MODEL_ROOT}")
    if not COMPOSE_FILE.is_file():
        raise RuntimeError(f"Compose file not found: {COMPOSE_FILE}")

    port = free_loopback_port()
    name = f"llama-cpp-preset-discovery-{uuid.uuid4().hex[:10]}"
    environment = os.environ.copy()
    environment["LLAMA_CPP_MODELS"] = str(MODEL_ROOT)
    compose = ["docker", "compose", "-f", str(COMPOSE_FILE)]
    command = [
        *compose,
        "run",
        "--detach",
        "--no-deps",
        "--name",
        name,
        "--publish",
        f"127.0.0.1:{port}:8080",
        "llama-cpp",
        "--models-dir",
        "/models",
        "--models-max",
        "1",
        "--models-autoload",
        "--host",
        "0.0.0.0",
        "--port",
        "8080",
        "--no-webui",
    ]

    started = False

    def remove_discovery_container() -> None:
        if started:
            subprocess.run(
                ["docker", "rm", "--force", name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )

    try:
        run_command(command, env=environment)
        started = True
        atexit.register(remove_discovery_container)
        url = f"http://127.0.0.1:{port}/v1/models"
        deadline = time.monotonic() + DISCOVERY_TIMEOUT_SECONDS
        last_error = "container has not accepted HTTP connections yet"
        while time.monotonic() < deadline:
            try:
                return models_from_response(get_json(url))
            except RuntimeError as error:
                last_error = str(error)
                time.sleep(1)
        raise RuntimeError(
            f"Discovery router did not become ready within {DISCOVERY_TIMEOUT_SECONDS} seconds: {last_error}"
        )
    finally:
        remove_discovery_container()


def render_preset(overrides: str, models: Iterable[Model]) -> tuple[str, list[Model]]:
    """Keep overrides verbatim and append default entries for undisclosed models."""
    section_names, model_paths, has_version, has_wildcard, _ = parse_preset(overrides)
    missing = [
        model
        for model in models
        if model.identifier not in section_names and model.path not in model_paths
    ]

    parts = [
        "; Generated by generate-models-preset.py. Edit the override input, not this file.",
        "; Model IDs and /models paths were discovered from a temporary llama.cpp router.",
    ]
    if not has_version:
        parts.extend(["version = 1", ""])
    if not has_wildcard:
        parts.extend(
            [
                "[*]",
                f"ctx-size = {DEFAULT_CTX_SIZE}",
                f"parallel = {DEFAULT_PARALLEL}",
                "",
            ]
        )
    if overrides.strip():
        parts.extend([overrides.rstrip(), ""])
    if missing:
        parts.append("; Models with no explicit override use the [*] defaults above.")
        for model in missing:
            parts.extend([f"[{model.identifier}]", f"model = {model.path}", ""])
    return "\n".join(parts).rstrip() + "\n", missing


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "target_dir",
        type=Path,
        help="directory in which to write models-preset.ini",
    )
    parser.add_argument(
        "--preset",
        required=True,
        type=Path,
        metavar="OVERRIDES.ini",
        help="partial preset containing [*] defaults and/or per-model overrides",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="replace an existing target models-preset.ini",
    )
    parser.add_argument(
        "--preset-only",
        action="store_true",
        help="validate explicit template paths only; do not discover or add models",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.preset.is_file():
        raise RuntimeError(f"Override preset does not exist or is not a file: {args.preset}")
    destination = args.target_dir / "models-preset.ini"
    if destination.exists() and not args.force:
        raise RuntimeError(f"Refusing to replace {destination}; pass --force after reviewing it.")

    overrides = args.preset.read_text(encoding="utf-8")
    _, _, _, _, preset_paths = parse_preset(overrides)
    validate_preset_paths(preset_paths)
    if args.preset_only:
        rendered = overrides.rstrip() + "\n"
        models: list[Model] | None = None
        missing: list[Model] = []
    else:
        models = discover_models()
        rendered, missing = render_preset(overrides, models)

    args.target_dir.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.{os.getpid()}.tmp")
    temporary.write_text(rendered, encoding="utf-8")
    temporary.replace(destination)
    print(f"Wrote {destination}")
    if models is None:
        print("Validated explicit template paths; did not discover or add model entries.")
    else:
        print(f"Discovered {len(models)} models; added defaults for {len(missing)} models.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
