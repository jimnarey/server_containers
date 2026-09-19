#!/usr/bin/env python3
"""Benchmark long-context prefill and decode for the performance-table matrix.

The matrix is read from ``performance-findings.md`` so a model/service row is
not silently lost when the table changes.  Tests are grouped by Compose profile
to keep container start-up and GPU-lock churn to a minimum.  The runner starts
one generated service at a time, waits for Docker health *and* the HTTP health
endpoint, then lets the router load and test each model in that profile.

All detailed output is written to one log file.  The terminal receives only
timestamped progress and the final summary, which are mirrored in that log.
The runner stops and removes every generated service it starts, including after
an exception.  It deliberately does not build images.
"""

from __future__ import annotations

import argparse
import configparser
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, TextIO


ROOT = Path(__file__).resolve().parent.parent
COMPOSE_FILE = ROOT / "compose.ai.yml"
RENDERER = ROOT / "llama-cpp" / "render-compose.py"
PERFORMANCE_TABLE = ROOT / "llama-cpp" / "performance-findings.md"
DEFAULT_OUTPUT_DIRECTORY = ROOT / "llama-cpp"

HEALTH_TIMEOUT_SECONDS = 180
REQUEST_TIMEOUT_SECONDS = 7_200
POLL_INTERVAL_SECONDS = 2
COMPLETION_TOKENS = 128
MIN_INPUT_TOKENS = 4_096
MAX_INPUT_TOKENS = 8_192
CONTEXT_FRACTION = 8
MINIMUM_LOW_CONTEXT_DECODE_TOKENS_PER_SECOND = 10.0
TOKENS_PER_SECOND_PATTERN = re.compile(
    r"(?<![\d.,])(\d[\d,]*(?:\.\d+)?)(?=\s*(?:-\s*\d[\d,]*(?:\.\d+)?\s*)?tok/s)"
)


@dataclass(frozen=True)
class Profile:
    """One generated Compose service and its source profile file."""

    name: str
    env_file: Path


@dataclass(frozen=True)
class ProfileSettings:
    """Values needed to launch and address a rendered service."""

    service: str
    bind_address: str
    port: int
    models_preset: Path


@dataclass(frozen=True)
class TableRow:
    model: str
    service_description: str
    decode: str


@dataclass(frozen=True)
class Test:
    row: TableRow
    profile: Profile


@dataclass
class Failure:
    test: str
    reason: str


# This mapping deliberately identifies only current, generated services.  A
# "standalone" row in the historical table cannot be reproduced faithfully by
# a profile and is reported as a skipped failure instead of being silently
# tested under materially different settings.
PROFILES = {
    "cpu": Profile("cpu", ROOT / "llama-cpp/config/llama-cpp-cpu/cpu.env"),
    "upstream-gpu-1": Profile(
        "upstream-gpu-1", ROOT / "llama-cpp/config/llama-cpp-16gb/gpu-1.env"
    ),
    "upstream-all-gpus": Profile(
        "upstream-all-gpus",
        ROOT / "llama-cpp/config/llama-cpp-32gb/all-gpus.env",
    ),
    "schwerz-gpu-1": Profile(
        "schwerz-gpu-1",
        ROOT / "llama-cpp/config/llama-cpp-generel-schwerz-16gb/gpu-1.env",
    ),
    "csantiago-all-gpus": Profile(
        "csantiago-all-gpus",
        ROOT / "llama-cpp/config/llama-cpp-csantiago78/all-gpus.env",
    ),
}

# Order avoids GPU lock collisions and leaves the two card profiles adjacent.
PROFILE_ORDER = (
    "cpu",
    "upstream-gpu-1",
    "upstream-all-gpus",
    "schwerz-gpu-1",
    "csantiago-all-gpus",
)


class Logger:
    """Mirror progress to tmux while preserving all detail in one log file."""

    def __init__(self, output: TextIO) -> None:
        self.output = output

    def write(self, message: str, *, terminal: bool = True) -> None:
        timestamped = f"{datetime.now().astimezone().isoformat(timespec='seconds')} {message}"
        print(timestamped, file=self.output, flush=True)
        if terminal:
            print(timestamped, flush=True)

    def detail(self, message: str) -> None:
        self.write(message, terminal=False)


def parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"{path}:{number}: expected KEY=VALUE")
        key, value = line.split("=", 1)
        values[key] = value
    return values


def profile_settings(profile: Profile) -> ProfileSettings:
    values = parse_env(profile.env_file)
    try:
        return ProfileSettings(
            service=values["SERVICE_NAME"],
            bind_address=values["BIND_ADDRESS"],
            port=int(values["PORT"]),
            models_preset=Path(values["MODELS_PRESET"]),
        )
    except KeyError as error:
        raise ValueError(f"{profile.env_file}: missing {error.args[0]}") from error


def table_rows(path: Path) -> list[TableRow]:
    """Read only the main resource-usage table, not historical sub-tables."""
    lines = path.read_text(encoding="utf-8").splitlines()
    header_index = next(
        index for index, line in enumerate(lines) if line.startswith("| Model | Service |")
    )
    rows: list[TableRow] = []
    for line in lines[header_index + 2 :]:
        if not line.startswith("|"):
            break
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 8:
            continue
        rows.append(TableRow(strip_markdown(cells[0]), cells[1], cells[7]))
    return rows


def strip_markdown(value: str) -> str:
    """Remove display-only emphasis, code delimiters, and numeric footnotes."""
    without_marks = value.replace("`", "").replace("**", "")
    return re.sub(r"[¹²³⁴⁵⁶⁷⁸⁹⁰]+$", "", without_marks).strip()


def profile_for(service_description: str) -> Profile | None:
    description = service_description.casefold()
    if "standalone" in description:
        return None
    if "llama-cpp-cpu" in description or description.startswith("cpu-only"):
        return PROFILES["cpu"]
    if "llama-cpp-gpu-1" in description:
        return PROFILES["upstream-gpu-1"]
    if "llama-cpp-all-gpus" in description:
        return PROFILES["upstream-all-gpus"]
    if "16gb schwerz" in description:
        return PROFILES["schwerz-gpu-1"]
    if "csantiago" in description:
        return PROFILES["csantiago-all-gpus"]
    return None


def low_context_decode_below_threshold(decode: str) -> bool:
    """Return whether a measured ordinary Decode result is below the suite floor."""
    return any(
        float(match.group(1).replace(",", ""))
        < MINIMUM_LOW_CONTEXT_DECODE_TOKENS_PER_SECOND
        for match in TOKENS_PER_SECOND_PATTERN.finditer(decode)
    )


def excluded_from_suite(row: TableRow) -> bool:
    """Apply the documented scope exclusions to one performance-table row."""
    description = row.service_description.casefold()
    model = row.model.casefold()
    return (
        "32gb schwerz" in description
        or (
            "qwen3.8-flash-next" in model
            and "physical gpu 0" in description
        )
        or low_context_decode_below_threshold(row.decode)
    )


def build_tests(rows: Iterable[TableRow]) -> tuple[dict[str, list[Test]], list[Failure]]:
    groups: dict[str, list[Test]] = defaultdict(list)
    failures: list[Failure] = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        if excluded_from_suite(row):
            continue
        profile = profile_for(row.service_description)
        if profile is None:
            failures.append(Failure(f"{row.model} | {row.service_description}", "no reproducible generated Compose profile"))
            continue
        key = (profile.name, row.model.casefold())
        if key in seen:
            continue
        seen.add(key)
        groups[profile.name].append(Test(row, profile))
    return groups, failures


def command_output(command: list[str], logger: Logger, *, check: bool = True) -> str:
    logger.detail("$ " + " ".join(command))
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    if completed.stdout:
        logger.detail("stdout:\n" + completed.stdout.rstrip())
    if completed.stderr:
        logger.detail("stderr:\n" + completed.stderr.rstrip())
    if check and completed.returncode:
        raise RuntimeError(f"command exited {completed.returncode}: {' '.join(command)}")
    return completed.stdout.strip()


def render_overlay(profile: Profile, logger: Logger) -> Path:
    rendered = command_output([sys.executable, str(RENDERER), str(profile.env_file)], logger)
    path = Path(rendered)
    if not path.is_file():
        raise RuntimeError(f"renderer did not produce a readable Compose file: {rendered}")
    return path


def compose_command(overlay: Path) -> list[str]:
    return ["docker", "compose", "-f", str(COMPOSE_FILE), "-f", str(overlay)]


def http_json(url: str, *, body: dict[str, Any] | None, timeout: int) -> dict[str, Any]:
    encoded = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=encoded,
        headers={"Content-Type": "application/json"},
        method="GET" if encoded is None else "POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {error.code}: {detail}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"connection error: {error.reason}") from error


def base_url(settings: ProfileSettings) -> str:
    return f"http://{settings.bind_address}:{settings.port}"


def wait_until_ready(compose: list[str], settings: ProfileSettings, logger: Logger, timeout: int) -> None:
    deadline = time.monotonic() + timeout
    health_url = f"{base_url(settings)}/health"
    last_status = "container has not appeared"
    while time.monotonic() < deadline:
        container = command_output(
            [*compose, "ps", "-q", settings.service], logger, check=False
        )
        if container:
            last_status = command_output(
                [
                    "docker",
                    "inspect",
                    "--format",
                    "{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}",
                    container,
                ],
                logger,
                check=False,
            )
            if last_status == "healthy":
                try:
                    http_json(health_url, body=None, timeout=POLL_INTERVAL_SECONDS)
                    http_json(
                        f"{base_url(settings)}/v1/models",
                        body=None,
                        timeout=POLL_INTERVAL_SECONDS,
                    )
                    return
                except RuntimeError as error:
                    last_status = f"healthy but HTTP not ready: {error}"
        time.sleep(POLL_INTERVAL_SECONDS)
    raise RuntimeError(f"service was not fully ready after {timeout}s ({last_status})")


def available_models(server_url: str, timeout: int) -> list[str]:
    response = http_json(f"{server_url}/v1/models", body=None, timeout=timeout)
    data = response.get("data", [])
    return [item["id"] for item in data if isinstance(item, dict) and isinstance(item.get("id"), str)]


def resolve_model(label: str, models: list[str]) -> str:
    # Table labels sometimes add an explanatory suffix (for example
    # "Qwen3.8-Flash-Next (tuned cfg)") that is not part of the router ID.
    canonical = re.sub(r"\s*\([^)]*\)$", "", label).strip()
    if canonical in models:
        return canonical
    folded = canonical.casefold()
    exact = [model for model in models if model.casefold() == folded]
    if len(exact) == 1:
        return exact[0]
    prefix = [model for model in models if model.casefold().startswith(f"{folded}-")]
    if len(prefix) == 1:
        return prefix[0]
    raise RuntimeError(f"model {label!r} is unavailable; router offers: {', '.join(models)}")


def configured_context_size(preset: Path, model: str) -> int:
    """Return the model's configured context; use a safe common fallback."""
    if not preset.is_file():
        return 65_536
    config = configparser.ConfigParser(interpolation=None)
    config.optionxform = str
    try:
        # llama.cpp accepts top-level metadata such as ``version = 1`` before
        # its first [section].  configparser does not, so give only that
        # preamble a synthetic private section while preserving every actual
        # model section and its inheritance semantics.
        config.read_string("[__llama_preamble__]\n" + preset.read_text(encoding="utf-8"))
    except (OSError, configparser.Error):
        return 65_536
    for section in (model, "*"):
        if config.has_option(section, "ctx-size"):
            value = config.get(section, "ctx-size")
            if value.isdigit():
                return int(value)
    return 65_536


def input_target(context_size: int) -> int:
    return max(MIN_INPUT_TOKENS, min(MAX_INPUT_TOKENS, context_size // CONTEXT_FRACTION))


def benchmark_prompt(target_tokens: int) -> str:
    """Create a tokenizer-friendly deterministic context without source-code bias."""
    filler = " x" * target_tokens
    return (
        "This is a deterministic inference benchmark. Read the complete context "
        "before replying; it is deliberately semantically neutral.\n"
        "<benchmark-context>"
        f"{filler}\n"
        "</benchmark-context>\n"
        "Reply with the integers 1 through 128 separated by single spaces, with no "
        "other text."
    )


def benchmark_request(
    server_url: str, model: str, target_tokens: int, timeout: int
) -> dict[str, Any]:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": benchmark_prompt(target_tokens)}],
        "max_tokens": COMPLETION_TOKENS,
        "temperature": 0.0,
        "seed": 42,
        "stream": False,
    }
    started = time.monotonic()
    response = http_json(
        f"{server_url}/v1/chat/completions", body=payload, timeout=timeout
    )
    response["client_elapsed_seconds"] = round(time.monotonic() - started, 3)
    return response


def timing_summary(response: dict[str, Any]) -> dict[str, Any]:
    timings = response.get("timings") if isinstance(response.get("timings"), dict) else {}
    usage = response.get("usage") if isinstance(response.get("usage"), dict) else {}
    return {
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "prompt_tokens_timing": timings.get("prompt_n"),
        "prompt_tokens_per_second": timings.get("prompt_per_second"),
        "decode_tokens_timing": timings.get("predicted_n"),
        "decode_tokens_per_second": timings.get("predicted_per_second"),
        "client_elapsed_seconds": response["client_elapsed_seconds"],
    }


def teardown(compose: list[str], service: str, logger: Logger) -> None:
    # rm -sf is scoped to the generated service, avoiding a project-wide down
    # that could tear down unrelated Compose stacks sharing the network.
    command_output([*compose, "rm", "-sf", service], logger, check=False)


def capture_service_logs(compose: list[str], service: str, logger: Logger) -> None:
    """Preserve a setup failure's actual server error before removing it."""
    command_output([*compose, "logs", "--no-color", service], logger, check=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        help="single detailed log file (default: llama-cpp/long-context-<timestamp>.log)",
    )
    parser.add_argument(
        "--health-timeout",
        type=int,
        default=HEALTH_TIMEOUT_SECONDS,
        help=f"seconds to wait for each service (default: {HEALTH_TIMEOUT_SECONDS})",
    )
    parser.add_argument(
        "--request-timeout",
        type=int,
        default=REQUEST_TIMEOUT_SECONDS,
        help=f"seconds allowed for one model request (default: {REQUEST_TIMEOUT_SECONDS})",
    )
    parser.add_argument(
        "--profile",
        choices=PROFILE_ORDER,
        action="append",
        help="run only this profile; repeat to select several",
    )
    parser.add_argument("--dry-run", action="store_true", help="list the derived matrix without Docker")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = args.output or DEFAULT_OUTPUT_DIRECTORY / (
        f"long-context-{datetime.now().strftime('%Y%m%d-%H%M%S')}.log"
    )
    output.parent.mkdir(parents=True, exist_ok=True)

    with output.open("x", encoding="utf-8") as log_file:
        logger = Logger(log_file)
        logger.write(f"long-context benchmark log: {output}")
        logger.write(
            "policy: target input is configured ctx-size / 8, clamped to "
            f"{MIN_INPUT_TOKENS}-{MAX_INPUT_TOKENS}; completion cap is {COMPLETION_TOKENS}"
        )
        logger.write(
            "excluded from this suite: GenerelSchwerz 32GB; Qwen3.8-Flash-Next "
            "on physical GPU 0; rows with ordinary Decode below "
            f"{MINIMUM_LOW_CONTEXT_DECODE_TOKENS_PER_SECOND:g} tok/s"
        )

        groups, unsupported = build_tests(table_rows(PERFORMANCE_TABLE))
        selected_profiles = args.profile or list(PROFILE_ORDER)
        # An explicitly selected profile is a scoped run.  Historical rows
        # outside that profile (notably a standalone benchmark) must not turn
        # an otherwise successful diagnostic subset into a failure.
        failures = unsupported if args.profile is None else []
        tests = [test for profile in selected_profiles for test in groups.get(profile, [])]
        logger.write(f"derived {len(tests)} runnable table rows across {len(selected_profiles)} profile(s)")

        if args.dry_run:
            for test in tests:
                logger.write(f"DRY-RUN {test.profile.name}: {test.row.model} | {test.row.service_description}")
            print_failures(failures, logger)
            return 0 if not failures else 1

        completed = 0
        passed = 0
        for profile_name in selected_profiles:
            profile_tests = groups.get(profile_name, [])
            if not profile_tests:
                continue
            profile = PROFILES[profile_name]
            settings: ProfileSettings | None = None
            overlay: Path | None = None
            compose: list[str] | None = None
            logger.write(f"PROFILE {profile.name}: preparing {len(profile_tests)} test(s)")
            try:
                settings = profile_settings(profile)
                overlay = render_overlay(profile, logger)
                compose = compose_command(overlay)
                teardown(compose, settings.service, logger)
                command_output([*compose, "up", "-d", "--no-build", settings.service], logger)
                wait_until_ready(compose, settings, logger, args.health_timeout)
                logger.write(f"PROFILE {profile.name}: healthy on port {settings.port}")

                models = available_models(base_url(settings), args.health_timeout)
                logger.detail("available models: " + ", ".join(models))
                for test in profile_tests:
                    completed += 1
                    label = f"{test.row.model} | {test.row.service_description}"
                    try:
                        model = resolve_model(test.row.model, models)
                        context_size = configured_context_size(settings.models_preset, model)
                        target = input_target(context_size)
                        logger.write(
                            f"[{completed}/{len(tests)}] TEST {profile.name}: {model} "
                            f"(ctx={context_size}, target-input≈{target})"
                        )
                        response = benchmark_request(
                            base_url(settings), model, target, args.request_timeout
                        )
                        summary = timing_summary(response)
                        logger.write(
                            f"[{completed}/{len(tests)}] OK {profile.name}: {model}; "
                            f"prompt={summary['prompt_tokens']} at {summary['prompt_tokens_per_second']} t/s; "
                            f"decode={summary['decode_tokens_timing']} at "
                            f"{summary['decode_tokens_per_second']} t/s"
                        )
                        passed += 1
                        logger.detail("RESULT " + json.dumps({
                            "profile": profile.name,
                            "table_model": test.row.model,
                            "server_model": model,
                            "service": test.row.service_description,
                            "configured_ctx_size": context_size,
                            "target_input_tokens": target,
                            **summary,
                        }, sort_keys=True))
                    except Exception as error:  # Keep the matrix progressing after every failed model.
                        failures.append(Failure(label, str(error)))
                        logger.write(f"[{completed}/{len(tests)}] FAIL {profile.name}: {label}: {error}")
            except Exception as error:
                reason = f"profile setup failed: {error}"
                logger.write(f"PROFILE {profile.name}: FAIL {reason}")
                if compose is not None and settings is not None:
                    capture_service_logs(compose, settings.service, logger)
                for test in profile_tests:
                    if not any(failure.test == f"{test.row.model} | {test.row.service_description}" for failure in failures):
                        failures.append(Failure(f"{test.row.model} | {test.row.service_description}", reason))
            finally:
                if compose is not None and settings is not None:
                    teardown(compose, settings.service, logger)
                    logger.write(f"PROFILE {profile.name}: stopped and removed {settings.service}")

        print_failures(failures, logger)
        logger.write(f"complete: {passed} passed; {len(failures)} failure(s)")
        return 0 if not failures else 1


def print_failures(failures: list[Failure], logger: Logger) -> None:
    if not failures:
        logger.write("FAILURE SUMMARY: none")
        return
    logger.write(
        f"FAILURE SUMMARY: {len(failures)} item(s); full entries are in {logger.output.name}"
    )
    for failure in failures:
        logger.detail(f"FAILURE | {failure.test} | {failure.reason}")


if __name__ == "__main__":
    raise SystemExit(main())
