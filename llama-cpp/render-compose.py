#!/usr/bin/env python3
"""Render one deterministic llama.cpp Docker Compose overlay from a .env file."""

from __future__ import annotations

import json
import hashlib
import os
import re
import sys
from pathlib import Path


REQUIRED = {
    "SERVICE_NAME", "SOURCE_SERVICE", "PORT", "BIND_ADDRESS", "IMAGE",
    "LLAMA_REPOSITORY", "LLAMA_SOURCE_NAME", "LLAMA_BRANCH", "LLAMA_COMMIT",
    "LLAMA_CUDA", "MODELS_DIR", "MODELS_PRESET", "GPU_IDS", "RESTART_POLICY",
}
OPTIONAL = {"CONFIG_FILE", "NETWORK_ALIAS", "PARALLEL", "FIT_TARGET", "NCCL_CUMEM_ENABLE"}
SOURCES = {"upstream", "generel-schwerz", "csantiago78"}
SERVICE_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]*$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


def fail(message: str) -> None:
    print(f"render-compose.py: {message}", file=sys.stderr)
    raise SystemExit(2)


def parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        fail(f"cannot read {path}: {error}")
    for number, raw_line in enumerate(lines, 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            fail(f"{path}:{number}: expected KEY=VALUE")
        key, value = line.split("=", 1)
        key = key.strip()
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", key):
            fail(f"{path}:{number}: invalid key {key!r}")
        if key in values:
            fail(f"{path}:{number}: duplicate key {key}")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if "\n" in value or "\r" in value:
            fail(f"{path}:{number}: multiline values are not supported")
        values[key] = value
    unknown = values.keys() - REQUIRED - OPTIONAL
    if unknown:
        fail(f"{path}: unknown key(s): {', '.join(sorted(unknown))}")
    missing = REQUIRED - values.keys()
    if missing:
        fail(f"{path}: missing required key(s): {', '.join(sorted(missing))}")
    # Only deliberate renderer-prefixed variables override an env file.  This
    # avoids accidental interpolation from Compose's project-wide .env file.
    for key in values:
        override = os.environ.get(f"LLAMA_RENDER_{key}")
        if override is not None:
            values[key] = override
    # Short form for the common one-card switch, retained as the documented
    # operator interface.  It wins over LLAMA_RENDER_GPU_IDS.
    if "LLAMA_GPU_IDS" in os.environ:
        values["GPU_IDS"] = os.environ["LLAMA_GPU_IDS"]
    return values


def quoted(value: object) -> str:
    """JSON strings are valid, unambiguous YAML double-quoted scalars."""
    return json.dumps(str(value), ensure_ascii=False)


def emit_scalar_list(lines: list[str], indent: str, key: str, values: list[str]) -> None:
    lines.append(f"{indent}{key}:")
    lines.extend(f"{indent}  - {quoted(value)}" for value in values)


def validate(values: dict[str, str]) -> list[str]:
    for key, value in values.items():
        if not value and key not in {"CONFIG_FILE", "NETWORK_ALIAS", "GPU_IDS"}:
            fail(f"{key} must not be empty")
    if values["SOURCE_SERVICE"] not in SOURCES:
        fail("SOURCE_SERVICE must be one of: " + ", ".join(sorted(SOURCES)))
    if not SERVICE_RE.fullmatch(values["SERVICE_NAME"]):
        fail("SERVICE_NAME is not a valid Compose service name")
    if not values["PORT"].isdigit() or not 1 <= int(values["PORT"]) <= 65535:
        fail("PORT must be an integer from 1 to 65535")
    if values["LLAMA_CUDA"] not in {"ON", "OFF"}:
        fail("LLAMA_CUDA must be ON or OFF")
    if values["RESTART_POLICY"] not in {"no", "unless-stopped"}:
        fail("RESTART_POLICY must be no or unless-stopped")
    if not COMMIT_RE.fullmatch(values["LLAMA_COMMIT"]):
        fail("LLAMA_COMMIT must be a 40-character lowercase SHA")
    gpu_ids = [] if not values["GPU_IDS"] else values["GPU_IDS"].split(",")
    if any(not item or " " in item for item in gpu_ids):
        fail("GPU_IDS must be a comma-separated list without spaces")
    if values["LLAMA_CUDA"] == "OFF" and gpu_ids:
        fail("a CPU build must have an empty GPU_IDS value")
    if values["LLAMA_CUDA"] == "ON" and not gpu_ids:
        fail("a CUDA build must specify GPU_IDS")
    if values["SOURCE_SERVICE"] == "upstream" and bool(values.get("CONFIG_FILE")):
        fail("upstream profiles do not use CONFIG_FILE")
    if values["SOURCE_SERVICE"] != "upstream" and not values.get("CONFIG_FILE"):
        fail("fork profiles require CONFIG_FILE")
    return gpu_ids


def render(values: dict[str, str]) -> str:
    gpu_ids = validate(values)
    service = values["SERVICE_NAME"]
    lines = ["services:", f"  {service}:", "    build:", "      context: ./llama-cpp", "      target: server", "      args:"]
    for key in ("LLAMA_REPOSITORY", "LLAMA_SOURCE_NAME", "LLAMA_SERVICE_NAME", "LLAMA_BRANCH", "LLAMA_COMMIT", "LLAMA_CUDA"):
        value = service if key == "LLAMA_SERVICE_NAME" else values[key]
        lines.append(f"        {key}: {quoted(value)}")
    lines += [f"    image: {quoted(values['IMAGE'])}", f"    container_name: {quoted(service + '-c')}", f"    restart: {quoted(values['RESTART_POLICY'])}"]

    environment: list[tuple[str, str]] = []
    if gpu_ids:
        environment.append(("LLAMA_GPU_LOCK_IDS", ",".join(gpu_ids)))
    if values.get("NCCL_CUMEM_ENABLE"):
        environment.append(("NCCL_CUMEM_ENABLE", values["NCCL_CUMEM_ENABLE"]))
    if environment:
        lines.append("    environment:")
        lines.extend(f"      {key}: {quoted(value)}" for key, value in environment)

    lines.append("    volumes:")
    lines.append(f"      - {quoted(values['MODELS_DIR'] + ':/models:ro')}")
    if values["SOURCE_SERVICE"] == "upstream":
        lines.append(f"      - {quoted(values['MODELS_PRESET'] + ':/models-preset.ini:ro')}")
    else:
        lines.append("      - \"llama-gpu-locks:/var/lock/llama-gpu\"")
        lines.append(f"      - {quoted(values['CONFIG_FILE'] + ':/etc/llama.cpp/config.ini:ro')}")
        lines.append(f"      - {quoted(values['MODELS_PRESET'] + ':/etc/llama.cpp/models-preset.ini:ro')}")
    if gpu_ids and values["SOURCE_SERVICE"] == "upstream":
        lines.append("      - \"llama-gpu-locks:/var/lock/llama-gpu\"")

    if values["SOURCE_SERVICE"] == "upstream":
        command = ["--models-preset", "/models-preset.ini", "--reasoning-format", "deepseek", "--models-max", "1", "--models-autoload", "--host", "0.0.0.0", "--port", "8080", "--parallel", values.get("PARALLEL", "1"), "--n-gpu-layers", "all" if gpu_ids else "0"]
        if gpu_ids:
            command += ["--flash-attn", "on"]
        command += ["--fit", "on", "--fit-target", values.get("FIT_TARGET", "1024"), "--no-webui", "--metrics"]
    else:
        command = ["--models-preset", "/etc/llama.cpp/models-preset.ini", "--models-max", "1", "--models-autoload", "--host", "0.0.0.0", "--port", "8080", "--no-webui", "--metrics"]
    emit_scalar_list(lines, "    ", "command", command)

    if gpu_ids:
        lines += ["    gpus:", "      - driver: nvidia", "        device_ids:"]
        lines.extend(f"          - {quoted(gpu_id)}" for gpu_id in gpu_ids)
        lines.append("        capabilities: [gpu]")
    if values.get("NETWORK_ALIAS"):
        lines += ["    networks:", "      default:", "        aliases:", f"          - {quoted(values['NETWORK_ALIAS'])}"]
    lines += ["    ports:", f"      - {quoted(values['BIND_ADDRESS'] + ':' + values['PORT'] + ':8080')}", ""]
    return "\n".join(lines)


def main() -> None:
    arguments = sys.argv[1:]
    stdout = arguments[:1] == ["--stdout"]
    if stdout:
        arguments = arguments[1:]
    if len(arguments) != 1:
        fail("usage: render-compose.py [--stdout] PATH/TO/PROFILE.env")
    content = render(parse_env(Path(arguments[0])))
    if stdout:
        print(content, end="")
        return
    # Compose's -f flag takes a path, not a YAML stream.  Hashing the exact
    # generated content gives each distinct overlay a stable, reusable path.
    output = Path("/tmp") / f"llama-compose-{hashlib.sha256(content.encode()).hexdigest()}.yml"
    try:
        if not output.exists() or output.read_text(encoding="utf-8") != content:
            output.write_text(content, encoding="utf-8")
    except OSError as error:
        fail(f"cannot write {output}: {error}")
    print(output)


if __name__ == "__main__":
    main()
