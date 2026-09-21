#!/usr/bin/env python3
"""Derive per-provider/model token throughput from DeepSeek Harness session logs.

Each session under ``$DEEPSEEK_HOME/.dsh/sessions`` is a zstd-compressed
JSONL event stream. Every agent step carries enough detail to reconstruct
prefill and decode timing without needing a live benchmark request:

- ``step/start`` / ``step/end`` bound the step's wall-clock time.
- ``reasoning-chunks`` / ``text-chunks`` / ``tool-call-chunks`` each carry a
  ``dt`` array of millisecond deltas between generated chunks -- summing
  these gives the decode-only span, the same split ``llama-cpp/tools/request.py``
  reports as "stream duration" versus "time to first text".
- ``assistant/message`` carries ``usage.outputTokens`` and
  ``source.{provider,model}``, so every step is already tagged with which
  backend served it.

This reads only session logs; it never touches credentials or writes
anything back into DEEPSEEK_HOME.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_DEEPSEEK_HOME = Path("/mnt/work/deepseek")
CHUNK_TYPES = {"reasoning-chunks", "text-chunks", "tool-call-chunks"}


@dataclass
class StepMetrics:
    session_id: str
    workspace: str
    turn: int
    step: int
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    prefill_ms: float
    decode_ms: float
    step_time: int  # epoch ms, for --since filtering

    @property
    def decode_tps(self) -> float | None:
        return self.output_tokens / (self.decode_ms / 1000) if self.decode_ms > 0 else None

    @property
    def overall_tps(self) -> float | None:
        total_ms = self.prefill_ms + self.decode_ms
        return self.output_tokens / (total_ms / 1000) if total_ms > 0 else None


def decompress(path: Path) -> list[dict]:
    result = subprocess.run(["zstd", "-dc", str(path)], capture_output=True, check=True)
    return [json.loads(line) for line in result.stdout.decode("utf-8").splitlines() if line.strip()]


def workspace_name(session_file: Path) -> str:
    return session_file.parent.parent.name.strip("-")


def step_metrics_for_session(session_file: Path) -> list[StepMetrics]:
    events = decompress(session_file)
    if not events:
        return []

    session_id = events[0].get("data", {}).get("id") or events[0].get("id") or session_file.parent.name
    workspace = workspace_name(session_file)

    # Accumulate per (turn, step): start time, chunk dt values (with the
    # earliest chunk time for prefill latency), and usage/source from the
    # step's assistant/message event(s).
    starts: dict[tuple[int, int], int] = {}
    dts: dict[tuple[int, int], list[int]] = defaultdict(list)
    first_chunk_time: dict[tuple[int, int], int] = {}
    usage: dict[tuple[int, int], dict] = {}
    source: dict[tuple[int, int], dict] = {}
    times: dict[tuple[int, int], int] = {}

    for event in events:
        etype = event.get("type")
        data = event.get("data", {})
        turn, step = data.get("turn"), data.get("step")
        if turn is None or step is None:
            continue
        key = (turn, step)

        if etype == "step/start":
            starts[key] = event["time"]
        elif etype in CHUNK_TYPES:
            chunk_dts = data.get("dt")
            if chunk_dts:
                dts[key].extend(chunk_dts)
                chunk_time = event.get("time0", event.get("time"))
                if key not in first_chunk_time:
                    first_chunk_time[key] = chunk_time
        elif etype == "assistant/message":
            step_usage = data.get("usage")
            if step_usage:
                accumulated = usage.setdefault(key, {"inputTokens": 0, "outputTokens": 0, "cacheReadTokens": 0})
                accumulated["inputTokens"] = max(accumulated["inputTokens"], step_usage.get("inputTokens", 0))
                accumulated["outputTokens"] += step_usage.get("outputTokens", 0)
                accumulated["cacheReadTokens"] = max(accumulated["cacheReadTokens"], step_usage.get("cacheReadTokens", 0))
            if key not in source:
                source[key] = data.get("message", {}).get("source", {})
            times[key] = event["time"]

    results = []
    for key, step_usage in usage.items():
        start = starts.get(key)
        chunk_time = first_chunk_time.get(key)
        if start is None or chunk_time is None:
            continue
        model_source = source.get(key, {})
        if model_source.get("kind") != "model":
            continue
        results.append(
            StepMetrics(
                session_id=session_id,
                workspace=workspace,
                turn=key[0],
                step=key[1],
                provider=model_source.get("provider", "unknown"),
                model=model_source.get("model", "unknown"),
                input_tokens=step_usage["inputTokens"],
                output_tokens=step_usage["outputTokens"],
                cache_read_tokens=step_usage["cacheReadTokens"],
                prefill_ms=max(chunk_time - start, 0),
                decode_ms=sum(dts.get(key, [])),
                step_time=times[key],
            )
        )
    return results


def find_session_files(sessions_root: Path) -> list[Path]:
    return sorted(sessions_root.rglob("session.jsonl.zstd"))


def collect_metrics(sessions_root: Path) -> list[StepMetrics]:
    metrics = []
    for session_file in find_session_files(sessions_root):
        try:
            metrics.extend(step_metrics_for_session(session_file))
        except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError) as error:
            print(f"warning: skipping {session_file}: {error}", file=sys.stderr)
    return metrics


def apply_filters(
    metrics: list[StepMetrics],
    *,
    provider: str | None,
    model: str | None,
    workspace: str | None,
    since: datetime | None,
) -> list[StepMetrics]:
    filtered = metrics
    if provider:
        filtered = [m for m in filtered if m.provider == provider]
    if model:
        filtered = [m for m in filtered if m.model == model]
    if workspace:
        filtered = [m for m in filtered if m.workspace == workspace]
    if since:
        since_ms = since.timestamp() * 1000
        filtered = [m for m in filtered if m.step_time >= since_ms]
    return filtered


def median_or_none(values: list[float]) -> float | None:
    return statistics.median(values) if values else None


def print_summary_table(metrics: list[StepMetrics]) -> None:
    groups: dict[tuple[str, str], list[StepMetrics]] = defaultdict(list)
    for m in metrics:
        groups[(m.provider, m.model)].append(m)

    rows = []
    for (provider, model), group in groups.items():
        decode_tps_values = [m.decode_tps for m in group if m.decode_tps is not None]
        overall_tps_values = [m.overall_tps for m in group if m.overall_tps is not None]
        rows.append(
            {
                "provider": provider,
                "model": model,
                "steps": len(group),
                "output_tokens": sum(m.output_tokens for m in group),
                "decode_tps_median": median_or_none(decode_tps_values),
                "decode_tps_min": min(decode_tps_values) if decode_tps_values else None,
                "decode_tps_max": max(decode_tps_values) if decode_tps_values else None,
                "overall_tps_median": median_or_none(overall_tps_values),
            }
        )
    rows.sort(key=lambda r: r["output_tokens"], reverse=True)

    def fmt(value: float | None) -> str:
        return f"{value:.1f}" if value is not None else "n/a"

    header = f"{'provider':<28} {'model':<34} {'steps':>6} {'out tok':>9} {'decode t/s (med)':>16} {'decode t/s (range)':>22} {'overall t/s (med)':>18}"
    print(header)
    print("-" * len(header))
    for row in rows:
        decode_range = (
            f"{row['decode_tps_min']:.1f}-{row['decode_tps_max']:.1f}"
            if row["decode_tps_min"] is not None
            else "n/a"
        )
        print(
            f"{row['provider']:<28} {row['model']:<34} {row['steps']:>6} {row['output_tokens']:>9} "
            f"{fmt(row['decode_tps_median']):>16} "
            f"{decode_range:>22} "
            f"{fmt(row['overall_tps_median']):>18}"
        )


def print_raw_rows(metrics: list[StepMetrics]) -> None:
    for m in sorted(metrics, key=lambda m: m.step_time):
        when = datetime.fromtimestamp(m.step_time / 1000, tz=timezone.utc).isoformat()
        print(
            f"{when}  {m.workspace:<20} {m.provider:<24} {m.model:<32} "
            f"out={m.output_tokens:<5} decode_t/s={m.decode_tps or 0:.1f} overall_t/s={m.overall_tps or 0:.1f} "
            f"session={m.session_id}"
        )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--deepseek-home",
        type=Path,
        default=Path(os.environ.get("DEEPSEEK_HOME", DEFAULT_DEEPSEEK_HOME)),
        help="Persisted DeepSeek home directory (default: DEEPSEEK_HOME or %(default)s)",
    )
    parser.add_argument("--provider", help="Only include this provider (e.g. llama-cpp-csantiago78)")
    parser.add_argument("--model", help="Only include this model id")
    parser.add_argument("--workspace", help="Only include this workspace (session directory name, dashes stripped)")
    parser.add_argument("--since", type=datetime.fromisoformat, help="Only include steps at/after this ISO timestamp")
    parser.add_argument("--raw", action="store_true", help="Print one row per step instead of the aggregated table")
    parser.add_argument("--json", action="store_true", help="Print matching step rows as JSON instead of a table")
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    sessions_root = arguments.deepseek_home / ".dsh" / "sessions"
    if not sessions_root.is_dir():
        raise FileNotFoundError(f"Sessions directory is missing: {sessions_root}")

    metrics = collect_metrics(sessions_root)
    metrics = apply_filters(
        metrics,
        provider=arguments.provider,
        model=arguments.model,
        workspace=arguments.workspace,
        since=arguments.since,
    )

    if not metrics:
        print("No matching steps found.", file=sys.stderr)
        return 1

    if arguments.json:
        rows = [dict(m.__dict__, decode_tps=m.decode_tps, overall_tps=m.overall_tps) for m in metrics]
        print(json.dumps(rows, indent=2))
    elif arguments.raw:
        print_raw_rows(metrics)
    else:
        print_summary_table(metrics)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except FileNotFoundError as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
