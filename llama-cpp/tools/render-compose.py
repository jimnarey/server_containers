#!/usr/bin/env python3
"""Render one standalone llama.cpp service from a Compose template service."""

from __future__ import annotations

import hashlib
import os
import re
import sys
from copy import deepcopy
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Callable

import yaml

# The generated service is intentionally tied to this repository's AI Compose
# file. The file is read to materialise the selected source template before the
# standalone service is written below /tmp for use with ``docker compose -f``.
TOOL_DIRECTORY = Path(__file__).resolve().parent
LLAMA_DIRECTORY = TOOL_DIRECTORY.parent
PROJECT_DIRECTORY = LLAMA_DIRECTORY.parent
AI_COMPOSE_FILE = PROJECT_DIRECTORY / "compose.ai.yml"
OVERLAY_DIRECTORY = Path("/tmp")

# Compose/runtime values shared by every renderer path. Keeping these here
# makes the generated Compose contract easy to audit and avoids string drift.
MODELS_TARGET = "/models"
UPSTREAM_PRESET_TARGET = "/models-preset.ini"
FORK_CONFIG_TARGET = "/etc/llama.cpp/config.ini"
FORK_PRESET_TARGET = "/etc/llama.cpp/models-preset.ini"
CHAT_TEMPLATES_DIRECTORY = LLAMA_DIRECTORY / "config" / "chat-templates"
CHAT_TEMPLATES_TARGET = "/opt/llama-cpp/chat-templates"
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
    "NCCL_CUMEM_ENABLE", "IMAGE", "LLAMA_CUDA", "CUDA_VISIBLE_DEVICES",
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
    cuda_visible_devices: str | None


@dataclass(frozen=True)
class SourceTemplate:
    """Runtime details that correspond to one Compose template service."""

    requires_config: bool
    preset_target: str
    command: CommandBuilder
    config_target: str | None = None
    gpu_strategy: str = "device-ids"


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


def bind_source(value: str) -> str:
    """Resolve repository-relative bind sources before writing an overlay in /tmp."""
    path = Path(value)
    return str(path if path.is_absolute() else PROJECT_DIRECTORY / path)


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
    "cuda_visible_devices": FieldSpec("CUDA_VISIBLE_DEVICES", optional, ""),
}


def upstream_command(profile: Profile) -> list[str]:
    command = [
        "--models-preset", UPSTREAM_PRESET_TARGET,
        *COMMON_SERVER_ARGS,
        "--parallel", profile.parallel or "1",
    ]
    if profile.gpu_ids:
        command.extend(("--flash-attn", "on"))
    else:
        # Only the no-GPU (CPU) profile needs a system-wide --n-gpu-layers:
        # there is no device to offload to regardless of any per-model
        # preset value. For GPU profiles this must NOT be set here -- a
        # router-level --n-gpu-layers (even "all") overrides every
        # per-model `n-gpu-layers = ...` value in models-preset.ini, which
        # silently broke `n-gpu-layers = auto` (the partial-CPU-offload
        # setting the two dense 70B-class entries depend on): the spawned
        # instance's own args showed the literal string "all", not "auto",
        # and `--fit` then aborted with "n_gpu_layers already set by user
        # to -2" before it could reduce anything, producing an immediate
        # CUDA OOM trying to force all layers onto one card. Leaving this
        # unset lets each model's own preset value win, and falls back to
        # llama-server's own built-in default (`auto`) for anything that
        # doesn't set one at all -- which already behaves like "all" for a
        # model that fits, so this is not a behavior change for every
        # model that isn't relying on partial offload.
        command.extend(("--n-gpu-layers", "0"))
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
        True, FORK_PRESET_TARGET, fork_command, FORK_CONFIG_TARGET, "cuda-visible",
    ),
    "llama-cpp-generel-schwerz-32gb": SourceTemplate(
        True, FORK_PRESET_TARGET, fork_command, FORK_CONFIG_TARGET, "cuda-visible",
    ),
    "llama-cpp-csantiago78": SourceTemplate(
        True, FORK_PRESET_TARGET, fork_command, FORK_CONFIG_TARGET, "cuda-visible",
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
    "new_service": Rule(
        lambda context: context["profile"].service_name != context["profile"].source_service,
        "SERVICE_NAME must differ from SOURCE_SERVICE for a generated service",
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
    "cuda_visibility": Rule(
        lambda context: context["template"] is None
        or context["template"].gpu_strategy != "cuda-visible"
        or context["profile"].cuda_visible_devices == ",".join(context["profile"].gpu_ids),
        "CUDA_VISIBLE_DEVICES must match GPU_IDS for this source service",
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
    profile = Profile(**{
        attribute: spec.parser(values.get(spec.env_name, spec.default or ""))
        for attribute, spec in PROFILE_FIELDS.items()
    })
    return replace(
        profile,
        models_preset=bind_source(profile.models_preset),
        config_file=bind_source(profile.config_file) if profile.config_file else None,
    )


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


def source_service(profile: Profile) -> dict[str, Any]:
    """Load and copy the named Compose service used as this profile's base."""
    try:
        compose = yaml.safe_load(Path(AI_COMPOSE_FILE).read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        fail(f"cannot read {AI_COMPOSE_FILE}: {error}")
    services = compose.get("services") if isinstance(compose, dict) else None
    service = services.get(profile.source_service) if isinstance(services, dict) else None
    if not isinstance(service, dict):
        fail(f"{AI_COMPOSE_FILE}: missing service {profile.source_service}")
    return deepcopy(service)


def gpu_configuration(profile: Profile, template: SourceTemplate) -> object | None:
    if not profile.gpu_ids:
        return None
    if template.gpu_strategy == "cuda-visible":
        return "all"
    return [{
        "driver": "nvidia",
        "device_ids": profile.gpu_ids,
        "capabilities": ["gpu"],
    }]


def render(profile: Profile) -> str:
    """Materialise a source service, then replace every profile-owned setting."""
    template = validate(profile)
    service = source_service(profile)

    build = service.setdefault("build", {})
    if not isinstance(build, dict):
        fail(f"{AI_COMPOSE_FILE}: {profile.source_service}.build must be a mapping")
    build_args = build.setdefault("args", {})
    if not isinstance(build_args, dict):
        fail(f"{AI_COMPOSE_FILE}: {profile.source_service}.build.args must be a mapping")
    build_args["LLAMA_SERVICE_NAME"] = profile.service_name
    build_args["LLAMA_CUDA"] = profile.llama_cuda

    if profile.image:
        service["image"] = profile.image
    service["container_name"] = f"{profile.service_name}-c"
    service["restart"] = profile.restart_policy

    environment: dict[str, str] = {}
    if template.gpu_strategy == "cuda-visible" and profile.cuda_visible_devices:
        environment["CUDA_VISIBLE_DEVICES"] = profile.cuda_visible_devices
    if profile.gpu_ids:
        environment["LLAMA_GPU_LOCK_IDS"] = ",".join(profile.gpu_ids)
    if profile.nccl_cumem_enable:
        environment["NCCL_CUMEM_ENABLE"] = profile.nccl_cumem_enable
    service["environment"] = environment

    volumes = [
        f"{profile.models_dir}:{MODELS_TARGET}:ro",
        f"{CHAT_TEMPLATES_DIRECTORY}:{CHAT_TEMPLATES_TARGET}:ro",
    ]
    if template.requires_config:
        assert template.config_target is not None
        volumes.extend((
            GPU_LOCK_MOUNT,
            f"{profile.config_file}:{template.config_target}:ro",
        ))
    volumes.append(f"{profile.models_preset}:{template.preset_target}:ro")
    if profile.gpu_ids and not template.requires_config:
        volumes.append(GPU_LOCK_MOUNT)
    service["volumes"] = volumes
    service["command"] = template.command(profile)

    gpus = gpu_configuration(profile, template)
    if gpus is None:
        service.pop("gpus", None)
    else:
        service["gpus"] = gpus
    if profile.network_alias:
        service["networks"] = {"default": {"aliases": [profile.network_alias]}}
    else:
        service.pop("networks", None)
    service["ports"] = [f"{profile.bind_address}:{profile.port}:8080"]

    return yaml.safe_dump(
        {"services": {profile.service_name: service}},
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
    )


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
