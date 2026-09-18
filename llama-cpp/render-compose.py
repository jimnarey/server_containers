#!/usr/bin/env python3
"""Render one llama.cpp service which extends a Compose template service."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


# The generated overlay is intentionally tied to this repository's AI Compose
# file. Its ``extends.file`` value must stay absolute because the overlay is
# materialised in /tmp for use with ``docker compose -f $(...)``.
AI_COMPOSE_FILE = "/home/ai/server_containers/compose.ai.yml"
OVERLAY_DIRECTORY = Path("/tmp")

# Compose/runtime values shared by every renderer path. Keeping these here
# makes the generated Compose contract easy to audit and avoids string drift.
INDENT_WIDTH = 4
MODELS_TARGET = "/models"
UPSTREAM_PRESET_TARGET = "/models-preset.ini"
FORK_CONFIG_TARGET = "/etc/llama.cpp/config.ini"
FORK_PRESET_TARGET = "/etc/llama.cpp/models-preset.ini"
GPU_LOCK_MOUNT = "llama-gpu-locks:/var/lock/llama-gpu"
SERVER_HOST_PORT_ARGS = ("--host", "0.0.0.0", "--port", "8080")
COMMON_SERVER_ARGS = ("--models-max", "1", "--models-autoload", *SERVER_HOST_PORT_ARGS)
SERVER_TAIL_ARGS = ("--no-webui", "--metrics")

REQUIRED_FIELDS = frozenset({
    "SERVICE_NAME", "SOURCE_SERVICE", "PORT", "BIND_ADDRESS", "GPU_IDS",
    "RESTART_POLICY", "MODELS_DIR", "MODELS_PRESET",
})
OPTIONAL_FIELDS = frozenset({
    "CONFIG_FILE", "NETWORK_ALIAS", "PARALLEL", "FIT_TARGET",
    "NCCL_CUMEM_ENABLE", "IMAGE", "LLAMA_CUDA",
})
EMPTY_ALLOWED_FIELDS = frozenset({"CONFIG_FILE", "NETWORK_ALIAS", "GPU_IDS"})
RESTART_POLICIES = frozenset({"no", "unless-stopped"})
SERVICE_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]*$")
KEY_RE = re.compile(r"[A-Z][A-Z0-9_]*")


RuleContext = dict[str, Any]
RulePredicate = Callable[[RuleContext], bool]
RuleMessage = str | Callable[[RuleContext], str]
ProfileParser = Callable[[str], Any]
CommandBuilder = Callable[["Profile"], list[str]]


@dataclass(frozen=True)
class Rule:
    """One ordered validation expression and the error it reports."""

    passes: RulePredicate
    error: RuleMessage


@dataclass(frozen=True)
class FieldSpec:
    """Map a public env variable to one normalized Profile attribute."""

    env_name: str
    parser: ProfileParser = str
    default: str | None = None


@dataclass(frozen=True)
class Profile:
    service_name: str
    source_service: str
    port: int | None
    bind_address: str
    gpu_ids: list[str]
    restart_policy: str
    models_dir: str
    models_preset: str
    config_file: str | None
    network_alias: str | None
    parallel: str | None
    fit_target: str | None
    nccl_cumem_enable: str | None
    image: str | None
    llama_cuda: str


@dataclass(frozen=True)
class SourceTemplate:
    """Runtime details that correspond to one Compose template service."""

    requires_config: bool
    preset_target: str
    command: CommandBuilder
    config_target: str | None = None


LINE_RULES = {
    "assignment": Rule(
        lambda context: "=" in context["line"],
        "expected KEY=VALUE",
    ),
}

KEY_RULES = {
    "format": Rule(
        lambda context: KEY_RE.fullmatch(context["key"]) is not None,
        "invalid key {key!r}",
    ),
    "unique": Rule(
        lambda context: context["key"] not in context["values"],
        "duplicate key {key}",
    ),
}

ENV_FIELD_RULES = {
    "known": Rule(
        lambda context: not context["unknown"],
        lambda context: "unknown key(s): " + ", ".join(sorted(context["unknown"])),
    ),
    "complete": Rule(
        lambda context: not context["missing"],
        lambda context: "missing required key(s): " + ", ".join(sorted(context["missing"])),
    ),
    "nonempty": Rule(
        lambda context: context["empty_field"] is None,
        lambda context: f"{context['empty_field']} must not be empty",
    ),
}


def optional(value: str) -> str | None:
    return value or None


def port(value: str) -> int | None:
    return int(value) if value.isdigit() else None


def gpu_ids(value: str) -> list[str]:
    return [] if not value else value.split(",")


# Attribute names are internal Python names; env names remain the public,
# documented profile-file interface. This is the one conversion boundary.
PROFILE_FIELDS = {
    "service_name": FieldSpec("SERVICE_NAME"),
    "source_service": FieldSpec("SOURCE_SERVICE"),
    "port": FieldSpec("PORT", port),
    "bind_address": FieldSpec("BIND_ADDRESS"),
    "gpu_ids": FieldSpec("GPU_IDS", gpu_ids),
    "restart_policy": FieldSpec("RESTART_POLICY"),
    "models_dir": FieldSpec("MODELS_DIR"),
    "models_preset": FieldSpec("MODELS_PRESET"),
    "config_file": FieldSpec("CONFIG_FILE", optional, ""),
    "network_alias": FieldSpec("NETWORK_ALIAS", optional, ""),
    "parallel": FieldSpec("PARALLEL", optional, ""),
    "fit_target": FieldSpec("FIT_TARGET", optional, ""),
    "nccl_cumem_enable": FieldSpec("NCCL_CUMEM_ENABLE", optional, ""),
    "image": FieldSpec("IMAGE", optional, ""),
    "llama_cuda": FieldSpec("LLAMA_CUDA", str, "ON"),
}


def upstream_command(profile: Profile) -> list[str]:
    command = [
        "--models-preset", UPSTREAM_PRESET_TARGET,
        "--reasoning-format", "deepseek",
        *COMMON_SERVER_ARGS,
        "--parallel", profile.parallel or "1",
        "--n-gpu-layers", "all" if profile.gpu_ids else "0",
    ]
    if profile.gpu_ids:
        command.extend(("--flash-attn", "on"))
    return [
        *command,
        "--fit", "on", "--fit-target", profile.fit_target or "1024",
        *SERVER_TAIL_ARGS,
    ]


def fork_command(_: Profile) -> list[str]:
    return ["--models-preset", FORK_PRESET_TARGET, *COMMON_SERVER_ARGS, *SERVER_TAIL_ARGS]


# This is the only mapping from user-provided SOURCE_SERVICE to renderer
# behaviour. Build provenance remains in the corresponding Compose template.
SOURCE_TEMPLATES = {
    "llama-cpp": SourceTemplate(False, UPSTREAM_PRESET_TARGET, upstream_command),
    "llama-cpp-generel-schwerz-16gb": SourceTemplate(
        True, FORK_PRESET_TARGET, fork_command, FORK_CONFIG_TARGET,
    ),
    "llama-cpp-generel-schwerz-32gb": SourceTemplate(
        True, FORK_PRESET_TARGET, fork_command, FORK_CONFIG_TARGET,
    ),
    "llama-cpp-csantiago78": SourceTemplate(
        True, FORK_PRESET_TARGET, fork_command, FORK_CONFIG_TARGET,
    ),
}


PROFILE_RULES = {
    "source_template": Rule(
        lambda context: context["template"] is not None,
        "SOURCE_SERVICE must name a llama template in compose.ai.yml",
    ),
    "service_name": Rule(
        lambda context: SERVICE_RE.fullmatch(context["profile"].service_name) is not None,
        "SERVICE_NAME is not a valid Compose service name",
    ),
    "port": Rule(
        lambda context: context["profile"].port is not None
        and 1 <= context["profile"].port <= 65535,
        "PORT must be an integer from 1 to 65535",
    ),
    "restart_policy": Rule(
        lambda context: context["profile"].restart_policy in RESTART_POLICIES,
        "RESTART_POLICY must be no or unless-stopped",
    ),
    "cuda_value": Rule(
        lambda context: context["profile"].llama_cuda in {"ON", "OFF"},
        "LLAMA_CUDA must be ON or OFF",
    ),
    "gpu_ids": Rule(
        lambda context: all(identifier and " " not in identifier for identifier in context["profile"].gpu_ids),
        "GPU_IDS must be a comma-separated list without spaces",
    ),
    "cpu_template": Rule(
        lambda context: context["profile"].llama_cuda != "OFF"
        or (context["profile"].source_service == "llama-cpp" and not context["profile"].gpu_ids),
        "only the upstream CPU profile may use LLAMA_CUDA=OFF with no GPUs",
    ),
    "cuda_devices": Rule(
        lambda context: context["profile"].llama_cuda != "ON" or bool(context["profile"].gpu_ids),
        "a CUDA profile must specify GPU_IDS",
    ),
    "config_file": Rule(
        lambda context: context["requires_config"] == bool(context["profile"].config_file),
        lambda context: f"{context['profile'].source_service} profiles {context['config_requirement']} CONFIG_FILE",
    ),
}


def fail(message: str) -> None:
    print(f"render-compose.py: {message}", file=sys.stderr)
    raise SystemExit(2)


def apply_rules(rules: dict[str, Rule], context: RuleContext, location: str) -> None:
    """Fail at the first rule in a deliberately stable, declaration-order map."""
    for rule in rules.values():
        if rule.passes(context):
            continue
        message = rule.error(context) if callable(rule.error) else rule.error.format(**context)
        fail(f"{location}: {message}")


def parse_env(path: Path) -> Profile:
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
        location = f"{path}:{number}"
        apply_rules(LINE_RULES, {"line": line}, location)
        key, value = line.split("=", 1)
        key = key.strip()
        apply_rules(KEY_RULES, {"key": key, "values": values}, location)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key] = value

    for key in values:
        override = os.environ.get(f"LLAMA_RENDER_{key}")
        if override is not None:
            values[key] = override
    if "LLAMA_GPU_IDS" in os.environ:
        values["GPU_IDS"] = os.environ["LLAMA_GPU_IDS"]

    empty_field = next(
        (key for key, value in values.items() if not value and key not in EMPTY_ALLOWED_FIELDS),
        None,
    )
    apply_rules(
        ENV_FIELD_RULES,
        {
            "unknown": values.keys() - REQUIRED_FIELDS - OPTIONAL_FIELDS,
            "missing": REQUIRED_FIELDS - values.keys(),
            "empty_field": empty_field,
        },
        str(path),
    )
    return Profile(**{
        attribute: spec.parser(values.get(spec.env_name, spec.default or ""))
        for attribute, spec in PROFILE_FIELDS.items()
    })


def validate(profile: Profile) -> SourceTemplate:
    template = SOURCE_TEMPLATES.get(profile.source_service)
    requires_config = template.requires_config if template else False
    apply_rules(
        PROFILE_RULES,
        {
            "profile": profile,
            "template": template,
            "requires_config": requires_config,
            "config_requirement": "require" if requires_config else "do not use",
        },
        "profile",
    )
    assert template is not None
    return template


def indent(level: int) -> str:
    return " " * (INDENT_WIDTH * level)


def quoted(value: object) -> str:
    """JSON strings are valid, unambiguous YAML double-quoted scalars."""
    return json.dumps(str(value), ensure_ascii=False)


def emit_key(lines: list[str], level: int, key: str, tag: str = "") -> None:
    suffix = f" {tag}" if tag else ""
    lines.append(f"{indent(level)}{key}:{suffix}")


def emit_scalar(lines: list[str], level: int, key: str, value: object) -> None:
    lines.append(f"{indent(level)}{key}: {quoted(value)}")


def emit_mapping(
    lines: list[str], level: int, key: str, items: list[tuple[str, object]], tag: str = "",
) -> None:
    emit_key(lines, level, key, tag)
    for item_key, value in items:
        emit_scalar(lines, level + 1, item_key, value)


def emit_sequence(
    lines: list[str], level: int, key: str, values: list[object], tag: str = "",
) -> None:
    emit_key(lines, level, key, tag)
    lines.extend(f"{indent(level + 1)}- {quoted(value)}" for value in values)


def emit_empty_collection(lines: list[str], level: int, key: str, value: str) -> None:
    lines.append(f"{indent(level)}{key}: {value}")


def emit_gpu_request(lines: list[str], gpu_ids: list[str]) -> None:
    item_indent = indent(3)
    mapping_indent = f"{item_indent}  "
    lines.extend((
        f"{indent(2)}gpus: !override",
        f"{item_indent}- driver: nvidia",
        f"{mapping_indent}device_ids:",
    ))
    lines.extend(f"{mapping_indent}  - {quoted(gpu_id)}" for gpu_id in gpu_ids)
    lines.append(f"{mapping_indent}capabilities: [gpu]")


def render(profile: Profile) -> str:
    template = validate(profile)
    lines = ["services:", f"{indent(1)}{profile.service_name}:"]
    if profile.service_name != profile.source_service:
        emit_mapping(lines, 2, "extends", [
            ("file", AI_COMPOSE_FILE),
            ("service", profile.source_service),
        ])
    build_args = [("LLAMA_SERVICE_NAME", profile.service_name)]
    if profile.llama_cuda == "OFF":
        build_args.append(("LLAMA_CUDA", "OFF"))
    emit_key(lines, 2, "build")
    emit_mapping(lines, 3, "args", build_args)
    if profile.image:
        emit_scalar(lines, 2, "image", profile.image)
    emit_scalar(lines, 2, "container_name", f"{profile.service_name}-c")
    emit_scalar(lines, 2, "restart", profile.restart_policy)

    environment = [("LLAMA_GPU_LOCK_IDS", ",".join(profile.gpu_ids))] if profile.gpu_ids else []
    if profile.nccl_cumem_enable:
        environment.append(("NCCL_CUMEM_ENABLE", profile.nccl_cumem_enable))
    if environment:
        emit_mapping(lines, 2, "environment", environment, "!override")
    else:
        emit_empty_collection(lines, 2, "environment", "!override {}")

    volumes = [f"{profile.models_dir}:{MODELS_TARGET}:ro"]
    if template.requires_config:
        assert template.config_target is not None
        volumes.extend((
            GPU_LOCK_MOUNT,
            f"{profile.config_file}:{template.config_target}:ro",
        ))
    volumes.append(f"{profile.models_preset}:{template.preset_target}:ro")
    if profile.gpu_ids and not template.requires_config:
        volumes.append(GPU_LOCK_MOUNT)
    emit_sequence(lines, 2, "volumes", volumes, "!override")
    emit_sequence(lines, 2, "command", template.command(profile), "!override")

    if profile.gpu_ids:
        emit_gpu_request(lines, profile.gpu_ids)
    else:
        emit_empty_collection(lines, 2, "gpus", "!override []")
    if profile.network_alias:
        emit_key(lines, 2, "networks", "!override")
        emit_key(lines, 3, "default")
        emit_sequence(lines, 4, "aliases", [profile.network_alias])
    else:
        emit_empty_collection(lines, 2, "networks", "!override {}")
    emit_sequence(lines, 2, "ports", [f"{profile.bind_address}:{profile.port}:8080"], "!override")
    lines.append("")
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
    output = OVERLAY_DIRECTORY / f"llama-compose-{hashlib.sha256(content.encode()).hexdigest()}.yml"
    try:
        if not output.exists() or output.read_text(encoding="utf-8") != content:
            output.write_text(content, encoding="utf-8")
    except OSError as error:
        fail(f"cannot write {output}: {error}")
    print(output)


if __name__ == "__main__":
    main()
