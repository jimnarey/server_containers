#!/usr/bin/env python3
"""Synchronise Pi's local-provider catalogue and settings.

The catalogue is discovered from each provider's live ``/v1/models`` endpoint,
not from model directories or preset files.  This makes the model IDs and the
effective per-model context settings agree with the router Pi will actually
use.  A provider intentionally stopped for resource management retains its
last successfully discovered catalogue.

Only ``models.json`` and ``settings.json`` below ``$PI_HOME/.pi/agent`` are
managed.  Pi's credentials, sessions, trust decisions, packages, extensions,
and every other persistent file are left untouched.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any
import urllib.error
import urllib.request


# These defaults describe this Compose installation.  They can all be changed
# without editing the program: PI_HOME moves Pi state, while the per-provider
# *_MODELS_URL variables bypass Docker's published-port discovery.
DEFAULT_PI_HOME = Path("/mnt/work/pi")
PROJECT_DIRECTORY = Path(__file__).resolve().parent.parent
CONFIG_DIRECTORY = Path(__file__).resolve().parent / "config"
SETTINGS_TEMPLATE = CONFIG_DIRECTORY / "settings.base.json"
PI_AGENT_DIRECTORY = Path(".pi/agent")

DEFAULT_CONTEXT_WINDOW = 65536
DEFAULT_MAX_TOKENS = 16384
MINIMUM_OUTPUT_TOKENS = 1024


@dataclass(frozen=True)
class Provider:
    """A Compose-local API Pi can use, plus its host-side discovery details."""

    identifier: str
    service: str
    container_port: int
    base_url: str
    models_url_environment: str


PROVIDERS = (
    Provider(
        "llama-cpp",
        "llama-cpp",
        8080,
        "http://llama-cpp:8080/v1",
        "PI_LLAMA_CPP_MODELS_URL",
    ),
    Provider(
        "llama-cpp-cpu",
        "llama-cpp-cpu",
        8080,
        "http://llama-cpp-cpu:8080/v1",
        "PI_LLAMA_CPP_CPU_MODELS_URL",
    ),
    Provider(
        "llama-cpp-moe-16gb",
        "llama-cpp-generel-schwerz-16gb",
        8080,
        "http://llama-cpp-generel-schwerz-16gb:8080/v1",
        "PI_LLAMA_CPP_MOE_16GB_MODELS_URL",
    ),
    Provider(
        "llama-cpp-moe-32gb",
        "llama-cpp-generel-schwerz-32gb",
        8080,
        "http://llama-cpp-generel-schwerz-32gb:8080/v1",
        "PI_LLAMA_CPP_MOE_32GB_MODELS_URL",
    ),
    Provider(
        "ollama",
        "ollama",
        11434,
        "http://ollama:11434/v1",
        "PI_OLLAMA_MODELS_URL",
    ),
)


def report(action: str, message: str) -> None:
    print(f"{action:9} {message}")


def read_json(path: Path, *, default: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.exists():
        return {} if default is None else default
    try:
        content = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid JSON in {path}: {error}") from error
    if not isinstance(content, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return content


def docker_published_models_url(provider: Provider) -> str:
    """Return a host-reachable models URL for a running Compose service."""
    command = [
        "docker",
        "compose",
        "-f",
        str(PROJECT_DIRECTORY / "docker-compose.yml"),
        "port",
        provider.service,
        str(provider.container_port),
    ]
    try:
        result = subprocess.run(
            command,
            cwd=PROJECT_DIRECTORY,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError as error:
        raise RuntimeError("docker is required to discover Compose service ports") from error
    except subprocess.CalledProcessError as error:
        detail = error.stderr.strip() or error.stdout.strip() or "no published port"
        raise RuntimeError(detail) from error

    endpoint = next((line.strip() for line in result.stdout.splitlines() if line.strip()), "")
    if not endpoint:
        raise RuntimeError("Compose did not report a published port")

    # A wildcard bind is reachable through loopback; preserve explicit LAN and
    # loopback addresses because the server may deliberately not bind 127.0.0.1.
    if endpoint.startswith("0.0.0.0:"):
        endpoint = f"127.0.0.1:{endpoint.rsplit(':', 1)[1]}"
    elif endpoint.startswith("[::]:"):
        endpoint = f"[::1]:{endpoint.rsplit(':', 1)[1]}"
    return f"http://{endpoint}/v1/models"


def discovery_url(provider: Provider) -> str:
    configured = os.environ.get(provider.models_url_environment)
    return configured if configured else docker_published_models_url(provider)


def request_models(url: str) -> list[dict[str, Any]]:
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = json.load(response)
    except (urllib.error.URLError, OSError, TimeoutError, json.JSONDecodeError) as error:
        raise RuntimeError(str(error)) from error

    if not isinstance(payload, dict):
        raise RuntimeError("response was not a JSON object")
    entries = payload.get("data")
    if not isinstance(entries, list):
        # The native Ollama endpoint has a `models` array.  Its OpenAI endpoint
        # normally has `data`, but accepting both makes the override URL useful.
        entries = payload.get("models")
    if not isinstance(entries, list):
        raise RuntimeError("response did not contain a models/data array")

    models: list[dict[str, Any]] = []
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        identifier = entry.get("id", entry.get("name", entry.get("model")))
        if not isinstance(identifier, str) or not identifier:
            continue
        if identifier in seen:
            raise RuntimeError(f"response included duplicate model ID {identifier!r}")
        seen.add(identifier)
        models.append(entry)
    if not models:
        raise RuntimeError("response did not contain any usable model IDs")
    return sorted(models, key=lambda item: str(item.get("id", item.get("name", ""))).casefold())


def argument_value(arguments: Any, name: str) -> str | None:
    if not isinstance(arguments, list):
        return None
    for index, value in enumerate(arguments):
        if not isinstance(value, str):
            continue
        if value == name and index + 1 < len(arguments) and isinstance(arguments[index + 1], str):
            return arguments[index + 1]
        if value.startswith(f"{name}="):
            return value.partition("=")[2]
    return None


def positive_integer(value: str | None, default: int) -> int:
    try:
        parsed = int(value) if value is not None else default
    except ValueError:
        return default
    return parsed if parsed > 0 else default


def model_context(entry: dict[str, Any]) -> int:
    status = entry.get("status")
    arguments = status.get("args") if isinstance(status, dict) else None
    return positive_integer(argument_value(arguments, "--ctx-size"), DEFAULT_CONTEXT_WINDOW)


def model_reasoning(entry: dict[str, Any]) -> bool:
    status = entry.get("status")
    arguments = status.get("args") if isinstance(status, dict) else None
    effort = argument_value(arguments, "--reasoning-effort")
    return effort is not None and effort.lower() not in {"", "off", "none", "false", "0"}


def model_identifier(entry: dict[str, Any]) -> str:
    identifier = entry.get("id", entry.get("name", entry.get("model")))
    if not isinstance(identifier, str) or not identifier:
        raise ValueError("Model entry has no identifier")
    return identifier


def output_token_limit(identifier: str, context_window: int) -> int:
    """Keep Pi's advertised output cap within small model context windows."""
    if identifier == "Qwen3.8-27B-UD-Q6_K_M":
        return 24576
    if identifier == "Qwen3.8-Flash-Next-UD-Q3_K_XL":
        return 12288
    return min(DEFAULT_MAX_TOKENS, max(MINIMUM_OUTPUT_TOKENS, context_window // 4))


def pi_model(entry: dict[str, Any]) -> dict[str, Any]:
    context_window = model_context(entry)
    identifier = model_identifier(entry)
    model: dict[str, Any] = {
        "id": identifier,
        "contextWindow": context_window,
        "maxTokens": output_token_limit(identifier, context_window),
    }
    if model_reasoning(entry):
        model["reasoning"] = True
    return model


def provider_config(provider: Provider, models: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "baseUrl": provider.base_url,
        "api": "openai-completions",
        # Pi requires configured auth for a custom provider to be selectable.
        # These Compose-local APIs do not authenticate, so this is a harmless
        # availability marker rather than a secret or access control mechanism.
        "apiKey": "local",
        "compat": {
            "supportsDeveloperRole": False,
            "supportsReasoningEffort": False,
            "maxTokensField": "max_tokens",
        },
        "models": [pi_model(model) for model in models],
    }


def cached_provider(existing: dict[str, Any], identifier: str) -> dict[str, Any] | None:
    providers = existing.get("providers")
    if not isinstance(providers, dict):
        return None
    candidate = providers.get(identifier)
    if not isinstance(candidate, dict) or not isinstance(candidate.get("models"), list):
        return None
    return candidate


def compaction_override(provider: str, model: dict[str, Any]) -> dict[str, int]:
    context_window = int(model["contextWindow"])
    reserve = min(DEFAULT_MAX_TOKENS, max(MINIMUM_OUTPUT_TOKENS, context_window // 8))
    recent = min(32768, max(2048, context_window // 3))

    # These two models have deliberately selected long-context settings.
    if provider == "llama-cpp" and model["id"] == "Qwen3.8-27B-UD-Q6_K_M":
        reserve, recent = 24576, 65536
    elif model["id"] == "Qwen3.8-Flash-Next-UD-Q3_K_XL":
        reserve, recent = 12288, 32768
    return {"reserveTokens": reserve, "keepRecentTokens": recent}


def generated_settings(provider_catalogues: dict[str, dict[str, Any]]) -> dict[str, Any]:
    settings = read_json(SETTINGS_TEMPLATE)
    compaction = settings.setdefault("compaction", {})
    if not isinstance(compaction, dict):
        raise ValueError(f"Expected compaction object in {SETTINGS_TEMPLATE}")
    overrides: dict[str, dict[str, int]] = {}
    for provider, provider_data in provider_catalogues.items():
        models = provider_data.get("models")
        if not isinstance(models, list):
            continue
        for model in models:
            if isinstance(model, dict) and isinstance(model.get("id"), str):
                overrides[f"{provider}/{model['id']}"] = compaction_override(provider, model)
    compaction["modelOverrides"] = dict(sorted(overrides.items(), key=lambda item: item[0].casefold()))
    return settings


def write_json(path: Path, payload: dict[str, Any], *, dry_run: bool) -> None:
    if dry_run:
        report("would write", str(path))
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)
    report("wrote", str(path))


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pi-home",
        type=Path,
        default=Path(os.environ.get("PI_HOME", DEFAULT_PI_HOME)),
        help="Persistent Pi home (default: PI_HOME or %(default)s)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Discover and report without writing files")
    parser.add_argument(
        "--provider",
        action="append",
        choices=[provider.identifier for provider in PROVIDERS],
        help=(
            "Refresh only this provider (repeatable). Existing catalogues for "
            "other providers are retained, so providers can be refreshed one "
            "at a time as resources permit."
        ),
    )
    parser.add_argument(
        "--require-all",
        action="store_true",
        help="Fail if any provider cannot be queried, even when a cached catalogue exists",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    if not SETTINGS_TEMPLATE.is_file():
        raise FileNotFoundError(f"Settings template is missing: {SETTINGS_TEMPLATE}")

    target = arguments.pi_home / PI_AGENT_DIRECTORY
    models_target = target / "models.json"
    existing = read_json(models_target)
    selected = set(arguments.provider or (provider.identifier for provider in PROVIDERS))
    catalogue: dict[str, dict[str, Any]] = {
        provider.identifier: cached
        for provider in PROVIDERS
        if (cached := cached_provider(existing, provider.identifier)) is not None
    }
    unavailable: list[str] = []

    for provider in PROVIDERS:
        if provider.identifier not in selected:
            continue
        try:
            url = discovery_url(provider)
            models = request_models(url)
        except RuntimeError as error:
            cached = cached_provider(existing, provider.identifier)
            if arguments.require_all or (cached is None and arguments.provider):
                unavailable.append(f"{provider.identifier}: {error}")
                continue
            if cached is None:
                report("skipped", f"{provider.identifier} (endpoint unavailable: {error})")
            else:
                catalogue[provider.identifier] = cached
                report("cached", f"{provider.identifier} (endpoint unavailable: {error})")
        else:
            catalogue[provider.identifier] = provider_config(provider, models)
            report("discovered", f"{provider.identifier}: {len(models)} models from {url}")

    if unavailable:
        raise RuntimeError(
            "Unable to refresh the requested Pi provider catalogue. Start the "
            "listed services and run this command again:\n  - "
            + "\n  - ".join(unavailable)
        )

    if not catalogue:
        raise RuntimeError("No provider catalogue is available. Start a provider and refresh it with --provider.")

    ordered_catalogue = dict(sorted(catalogue.items(), key=lambda item: item[0]))
    write_json(models_target, {"providers": ordered_catalogue}, dry_run=arguments.dry_run)
    write_json(target / "settings.json", generated_settings(ordered_catalogue), dry_run=arguments.dry_run)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
