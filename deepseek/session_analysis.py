#!/usr/bin/env python3
"""Analyse DeepSeek Harness session logs: reasoning length, tool use, retries, compaction.

Reads every session.jsonl.zstd under a workspace's session directory and emits
one row per assistant turn (reasoning/text length, tool calls by name), plus
separate summaries for llm/retry and compaction events.

Session logs do NOT record the reasoning_effort value actually sent with a
request -- checked directly: neither `request/header.config` (only carries
provider/model/maxTokens) nor `assistant/message...source.replayState` (only
carries response metadata: API kind, response id, stop reason, content-block
shape) includes it. That transformation happens inside the pi-ai provider
adapter, below the layer DSH logs. So this tool cannot read the setting off
a row directly.

What it can do: label each row with an "era" you supply from known
configuration-change timestamps (e.g. from `git log` on the relevant
agent.cordis.yml / settings.yaml, or from a noted container-restart time), so
behaviour can be compared across a change even though the setting itself
isn't logged per-request.

Examples:

    # Per-turn CSV for one model, unfiltered
    ./session_analysis.py --model Qwen3.8-Flash-Next-UD-Q3_K_XL --out /tmp/flash_next.csv

    # Compare reasoning length before/after the reasoning:true fix took effect
    # (deepseek-c restart confirmed at 2026-09-14T16:10:05Z)
    ./session_analysis.py --model Qwen3.8-Flash-Next-UD-Q3_K_XL \\
        --era 2026-09-14T16:10:05=reasoning-low-default

    # Everything, grouped by provider/model with no era labels
    ./session_analysis.py
"""

from __future__ import annotations

import argparse
import datetime
import glob
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

DEFAULT_SESSIONS_ROOT = Path("/mnt/work/deepseek/.dsh/sessions")


def iter_events(path: Path):
    try:
        out = subprocess.run(["zstd", "-d", "--stdout", str(path)], capture_output=True, check=True).stdout
    except subprocess.CalledProcessError:
        return
    for line in out.decode("utf-8", "replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            yield json.loads(line)
        except json.JSONDecodeError:
            continue


def parse_era(spec: str) -> tuple[datetime.datetime, str]:
    ts, _, label = spec.partition("=")
    dt = datetime.datetime.fromisoformat(ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt, label


def era_label(eras: list[tuple[datetime.datetime, str]], ts_ms: float | None) -> str:
    if not eras or ts_ms is None:
        return ""
    dt = datetime.datetime.fromtimestamp(ts_ms / 1000, tz=datetime.timezone.utc)
    label = "(before first era)"
    for boundary, name in eras:
        if dt >= boundary:
            label = name
    return label


def collect(sessions_root: Path, workspace: str, model_filter: str | None, eras):
    sess_dir = sessions_root / workspace
    turn_rows = []
    retry_rows = []
    compaction_rows = []
    step_rows = []

    for f in sorted(sess_dir.glob("*/session.jsonl.zstd")):
        session_name = f.parent.name
        # step/start doesn't carry a model, but the *next* assistant/message in
        # the same (turn, step) does; track it forward so a step's duration can
        # still be attributed to a model/provider for grouping.
        open_steps: dict[tuple, float] = {}
        step_model: dict[tuple, tuple] = {}
        # last assistant/chunk seen for each open step: this is when the model
        # actually finished producing output, as distinct from step/end (which
        # only fires once any tool calls in the step -- including a blocking
        # one like ask_user_question -- have also returned a result). The gap
        # between them can be human response latency or tool execution time,
        # not model compute, and conflating the two produced a wrong causal
        # claim once already (a 13.6-hour "step" that was ~4 minutes of real
        # generation followed by an overnight wait on ask_user_question).
        last_chunk_ts: dict[tuple, float] = {}
        step_tool_names: dict[tuple, list] = {}

        for d in iter_events(f):
            t = d.get("type")
            ts = d.get("time")
            data = d.get("data", {})

            if t == "step/start":
                key = (data.get("turn"), data.get("step"))
                open_steps[key] = ts

            elif t == "assistant/chunk":
                # No (turn, step) on the chunk event itself; attribute it to
                # whichever step is currently open (there is at most one).
                if open_steps:
                    key = next(iter(open_steps))
                    if ts is not None:
                        last_chunk_ts[key] = ts

            elif t == "step/end":
                key = (data.get("turn"), data.get("step"))
                start_ts = open_steps.pop(key, None)
                if start_ts is not None and ts is not None:
                    provider, model = step_model.pop(key, (None, None))
                    tool_names = step_tool_names.pop(key, [])
                    chunk_ts = last_chunk_ts.pop(key, None)
                    step_rows.append({
                        "time_ms": start_ts,
                        "session": session_name,
                        "provider": provider,
                        "model": model,
                        "duration_s": (ts - start_ts) / 1000,
                        "llm_duration_s": (chunk_ts - start_ts) / 1000 if chunk_ts is not None else None,
                        "blocked_on_user": "ask_user_question" in tool_names,
                        "era": era_label(eras, start_ts),
                    })
                last_chunk_ts.pop(key, None)

            elif t == "assistant/message":
                msg = data.get("message", {})
                src = msg.get("source", {}) or {}
                model = src.get("model")
                provider = src.get("provider")
                key = (data.get("turn"), data.get("step"))
                tool_names_here = [c.get("name", "?") for c in msg.get("content", []) if c.get("type") == "tool-call"]
                if key in open_steps:
                    step_model[key] = (provider, model)
                    step_tool_names.setdefault(key, []).extend(tool_names_here)
                if model_filter and model != model_filter:
                    continue
                content = msg.get("content", [])
                reasoning_chars = sum(len(c.get("text", "")) for c in content if c.get("type") == "reasoning")
                text_chars = sum(len(c.get("text", "")) for c in content if c.get("type") == "text")
                tool_names = [c.get("name", "?") for c in content if c.get("type") == "tool-call"]
                turn_rows.append({
                    "time_ms": ts,
                    "session": session_name,
                    "provider": provider,
                    "model": model,
                    "turn": data.get("turn"),
                    "step": data.get("step"),
                    "reasoning_chars": reasoning_chars,
                    "text_chars": text_chars,
                    "tool_call_count": len(tool_names),
                    "tool_call_names": tool_names,
                    "era": era_label(eras, ts),
                })

            elif t == "llm/retry":
                failure = data.get("failure", {})
                retry_rows.append({
                    "time_ms": ts,
                    "session": session_name,
                    "provider": data.get("provider"),
                    "retry": data.get("retry"),
                    "message": failure.get("message"),
                    "code": failure.get("code"),
                    "era": era_label(eras, ts),
                })

            elif t in ("compaction/start", "compaction/end", "compaction/summary"):
                compaction_rows.append({
                    "time_ms": ts,
                    "session": session_name,
                    "event": t,
                    "data": data,
                    "era": era_label(eras, ts),
                    # only compaction/summary (success) carries provider/model
                    "provider": data.get("provider"),
                    "model": data.get("model"),
                })

    return turn_rows, retry_rows, compaction_rows, step_rows


def write_csv(rows, path):
    import csv

    fieldnames = ["time", "session", "provider", "model", "turn", "step",
                  "reasoning_chars", "text_chars", "tool_call_count", "tool_call_names", "era"]
    with open(path, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            dt = datetime.datetime.fromtimestamp(r["time_ms"] / 1000, tz=datetime.timezone.utc) if r["time_ms"] else None
            writer.writerow({
                "time": dt.isoformat() if dt else "",
                "session": r["session"],
                "provider": r["provider"],
                "model": r["model"],
                "turn": r["turn"],
                "step": r["step"],
                "reasoning_chars": r["reasoning_chars"],
                "text_chars": r["text_chars"],
                "tool_call_count": r["tool_call_count"],
                "tool_call_names": ";".join(r["tool_call_names"]),
                "era": r["era"],
            })


def print_summary(turn_rows, retry_rows, compaction_rows, step_rows, eras, args_model_filter):
    print(f"Total assistant turns: {len(turn_rows)}")
    if not turn_rows:
        return

    # Era labels sort chronologically by the order they were passed on the
    # command line, not alphabetically (an alphabetical sort would, e.g., put
    # "low-committed" before "medium-committed" even though medium came first).
    era_order = {label: i for i, (_, label) in enumerate(eras)}
    era_order["(before first era)"] = -1

    def era_key(era):
        return era_order.get(era, 0)

    groups = defaultdict(list)
    for r in turn_rows:
        key = (r["provider"], r["model"], r["era"])
        groups[key].append(r)

    print("\nReasoning/text length by provider/model" + (" (and era)" if eras else "") + ":")
    print(f"{'provider':22} {'model':28} {'era':22} {'n':>5} {'reason.mean':>12} {'reason.median':>14} {'reason.max':>11} {'text.mean':>10}")
    for (provider, model, era), rs in sorted(groups.items(), key=lambda kv: (kv[0][0] or "", kv[0][1] or "", era_key(kv[0][2]))):
        n = len(rs)
        reasoning = sorted(x["reasoning_chars"] for x in rs)
        text = [x["text_chars"] for x in rs]
        print(f"{str(provider):22} {str(model):28} {era:22} {n:5d} {sum(reasoning)/n:12.0f} {reasoning[n//2]:14d} {max(reasoning):11d} {sum(text)/n:10.0f}")

    tool_counts = defaultdict(int)
    for r in turn_rows:
        for name in r["tool_call_names"]:
            tool_counts[name] += 1
    print("\nTool call counts (all matching rows):")
    for name, count in sorted(tool_counts.items(), key=lambda kv: -kv[1]):
        print(f"  {name:20} {count}")

    if step_rows:
        blocked = [r for r in step_rows if r["blocked_on_user"]]
        unblocked = [r for r in step_rows if not r["blocked_on_user"]]
        print(f"\n{len(blocked)} of {len(step_rows)} steps included an ask_user_question call "
              f"(their total duration includes however long the human took to answer -- "
              f"NOT model compute time). Two tables follow: total wall-clock (the old, confounded "
              f"metric) and llm_duration (step/start to the model's own last output chunk, before "
              f"any tool call executes) -- the latter is the fairer proxy for model compute time.")

        def print_table(title, value_key, rows):
            print(f"\n{title}, by provider/model" + (" and era" if eras else "") + ":")
            print(f"{'provider':22} {'model':28} {'era':22} {'n':>5} {'secs.mean':>10} {'secs.median':>12} {'secs.max':>9}")
            groups = defaultdict(list)
            for r in rows:
                v = r[value_key]
                if v is None:
                    continue
                groups[(r["provider"], r["model"], r["era"])].append(v)
            for (provider, model, era), vals in sorted(groups.items(), key=lambda kv: (kv[0][0] or "", kv[0][1] or "", era_key(kv[0][2]))):
                vals_sorted = sorted(vals)
                n = len(vals)
                print(f"{str(provider):22} {str(model):28} {era:22} {n:5d} {sum(vals)/n:10.1f} {vals_sorted[n//2]:12.1f} {max(vals):9.1f}")

        print_table("Total wall-clock seconds per step (ALL steps, confounded by tool/human wait time)", "duration_s", step_rows)
        print_table("Model-only duration per step, excluding ask_user_question steps", "llm_duration_s", unblocked)
        if blocked:
            print(f"\n{len(blocked)} step(s) blocked on ask_user_question -- excluded from the "
                  f"model-only table above, shown separately (total wall-clock, i.e. includes human latency):")
            for r in sorted(blocked, key=lambda r: -r["duration_s"])[:10]:
                print(f"  session={r['session']:24} provider={str(r['provider']):20} total_wall_clock_s={r['duration_s']:.1f}")

    # llm/retry has no `model` field, only `provider` -- but provider reliably
    # identifies which model family it belongs to in this deployment, so retries
    # ARE grouped below (by provider + era), just not directly by --model.
    # compaction/end (failure) has neither provider nor model, so failures stay
    # ungrouped; compaction/summary (success) has both and is grouped.
    print("\nllm/retry events by provider" + (" and era" if eras else "") + ":")
    retry_groups = defaultdict(lambda: [0, 0])
    for r in retry_rows:
        key = (r["provider"], r["era"])
        retry_groups[key][0] += 1
        if "idle timeout" in (r["message"] or ""):
            retry_groups[key][1] += 1
    for (provider, era), (total, timeouts) in sorted(retry_groups.items(), key=lambda kv: (kv[0][0] or "", era_key(kv[0][1]))):
        print(f"  {str(provider):22} {era:22} total={total:4d} stream-idle-timeout={timeouts}")

    comp_summary = [r for r in compaction_rows if r["event"] == "compaction/summary"]
    comp_ends_error = [r for r in compaction_rows if r["event"] == "compaction/end" and "error" in r["data"]]
    print(f"\ncompaction/summary (successful) by provider/model:")
    comp_ok_groups = defaultdict(int)
    for r in comp_summary:
        comp_ok_groups[(r["provider"], r["model"], r["era"])] += 1
    for (provider, model, era), count in sorted(comp_ok_groups.items(), key=lambda kv: (kv[0][0] or "", kv[0][1] or "", era_key(kv[0][2]))):
        print(f"  {str(provider):22} {str(model):28} {era:22} {count}")
    print(f"compaction/end with error (failed), workspace-wide (no provider/model on this event): {len(comp_ends_error)}")
    err_by_era = defaultdict(int)
    for r in comp_ends_error:
        err_by_era[r["era"]] += 1
    for era, count in sorted(err_by_era.items(), key=lambda kv: era_key(kv[0])):
        print(f"  era={era:22} {count}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workspace", default="--workspace-amiga-ui--",
                     help="session directory name under the sessions root (default: %(default)s)")
    ap.add_argument("--sessions-root", type=Path, default=DEFAULT_SESSIONS_ROOT)
    ap.add_argument("--model", help="only include assistant turns from this model id")
    ap.add_argument("--era", action="append", default=[], metavar="TIMESTAMP=LABEL",
                     help="UTC ISO timestamp boundary + label, repeatable, sorted automatically; "
                          "rows are labelled with the most recent boundary at or before their own time")
    ap.add_argument("--out", type=Path, help="write per-turn CSV here instead of printing a summary")
    args = ap.parse_args()

    eras = sorted((parse_era(e) for e in args.era), key=lambda x: x[0])

    turn_rows, retry_rows, compaction_rows, step_rows = collect(args.sessions_root, args.workspace, args.model, eras)

    if args.out:
        write_csv(turn_rows, args.out)
        print(f"wrote {len(turn_rows)} rows to {args.out}")
        return 0

    print_summary(turn_rows, retry_rows, compaction_rows, step_rows, eras, args.model)
    return 0


if __name__ == "__main__":
    sys.exit(main())
