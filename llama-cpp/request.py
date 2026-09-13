#!/usr/bin/env python3
"""Send one benchmarkable chat request to a llama.cpp server.

The server's OpenAI-compatible chat endpoint returns its own prompt and decode
timings.  This script prints them alongside the end-to-end request time.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Any


DEFAULT_HOST = os.environ.get("LLAMA_HOST", "192.168.50.136")


def request_json(url: str, *, body: dict[str, Any] | None, timeout: float) -> Any:
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="GET" if body is None else "POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {error.code} from {url}: {detail}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Could not connect to {url}: {error.reason}") from error


def delta_text(delta: dict[str, Any]) -> str:
    """Return printable text from an OpenAI-compatible streamed chat delta."""
    parts: list[str] = []
    for field in ("reasoning_content", "content"):
        value = delta.get(field)
        if isinstance(value, str):
            parts.append(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict) and isinstance(item.get("text"), str):
                    parts.append(item["text"])
    return "".join(parts)


def stream_chat(
    url: str, *, body: dict[str, Any], timeout: float, started: float
) -> dict[str, Any]:
    """Print an SSE chat stream and return its final request measurements."""
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "text/event-stream"},
        method="POST",
    )
    timings: dict[str, Any] = {}
    usage: dict[str, Any] = {}
    finish_reason: Any = None
    first_output_at: float | None = None
    output_seen = False

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            for raw_line in response:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line.startswith("data:"):
                    continue
                data = line.removeprefix("data:").strip()
                if data == "[DONE]":
                    break
                try:
                    event = json.loads(data)
                except json.JSONDecodeError as error:
                    raise RuntimeError(f"Invalid SSE event from {url}: {data!r}") from error

                if isinstance(event.get("timings"), dict):
                    timings = event["timings"]
                if isinstance(event.get("usage"), dict):
                    usage = event["usage"]

                choices = event.get("choices")
                if not isinstance(choices, list):
                    continue
                for choice in choices:
                    if not isinstance(choice, dict):
                        continue
                    if choice.get("finish_reason") is not None:
                        finish_reason = choice["finish_reason"]
                    delta = choice.get("delta")
                    if not isinstance(delta, dict):
                        continue
                    text = delta_text(delta)
                    if not text:
                        continue
                    now = time.monotonic()
                    if first_output_at is None:
                        first_output_at = now
                    print(text, end="", flush=True)
                    output_seen = True
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {error.code} from {url}: {detail}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Could not connect to {url}: {error.reason}") from error

    if output_seen:
        print()
    finished = time.monotonic()
    return {
        "timings": timings,
        "usage": usage,
        "finish_reason": finish_reason,
        "elapsed": finished - started,
        "ttft": None if first_output_at is None else first_output_at - started,
        "stream_duration": None
        if first_output_at is None
        else finished - first_output_at,
    }


def available_models(base_url: str, timeout: float) -> list[str]:
    response = request_json(f"{base_url}/v1/models", body=None, timeout=timeout)
    models = response.get("data", [])
    return [model["id"] for model in models if isinstance(model.get("id"), str)]


def choose_model(requested: str | None, models: list[str]) -> str:
    if not models:
        raise RuntimeError("The server returned no models from /v1/models.")

    if requested is None:
        if len(models) == 1:
            return models[0]
        choices = "\n  ".join(models)
        raise RuntimeError(
            "This router has multiple models. Select one with --model.\n"
            f"Available models:\n  {choices}"
        )

    if requested in models:
        return requested

    matches = [model for model in models if requested.lower() in model.lower()]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise RuntimeError(f"No model matches {requested!r}. Use --list-models to inspect IDs.")
    raise RuntimeError(
        f"Model selector {requested!r} is ambiguous; use an exact ID.\n"
        f"Matches:\n  {'\n  '.join(matches)}"
    )


def value(data: dict[str, Any], key: str) -> Any:
    result = data.get(key)
    return "n/a" if result is None else result


def print_metrics(
    *,
    model: str,
    finish_reason: Any,
    elapsed: float,
    usage: dict[str, Any],
    timings: dict[str, Any],
    ttft: float | None = None,
    stream_duration: float | None = None,
) -> None:
    print("\n--- request metrics ---")
    print(f"model:              {model}")
    print(f"finish reason:      {'n/a' if finish_reason is None else finish_reason}")
    print(f"end-to-end:         {elapsed:.2f} s (includes any model-load delay)")
    if ttft is not None:
        print(f"time to first text: {ttft:.2f} s (includes prompt evaluation)")
    if stream_duration is not None:
        print(f"stream duration:    {stream_duration:.2f} s (first text to completion)")
    print(f"prompt tokens:      {value(usage, 'prompt_tokens')}")
    print(f"completion tokens:  {value(usage, 'completion_tokens')}")
    print(f"cached prompt:      {value(timings, 'cache_n')} tokens")
    print(
        "prompt eval:        "
        f"{value(timings, 'prompt_n')} tokens in {value(timings, 'prompt_ms')} ms "
        f"({value(timings, 'prompt_per_second')} t/s)"
    )
    print(
        "generation:         "
        f"{value(timings, 'predicted_n')} tokens in {value(timings, 'predicted_ms')} ms "
        f"({value(timings, 'predicted_per_second')} t/s)"
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Send a chat request to a llama.cpp server and print timing metrics."
    )
    parser.add_argument("prompt", nargs="?", help="Quoted prompt to send")
    parser.add_argument("port", type=int, help="Host port published by llama.cpp")
    parser.add_argument(
        "--model",
        help="Exact model ID, or a unique case-insensitive substring; required for a multi-model router",
    )
    parser.add_argument(
        "--host",
        default=DEFAULT_HOST,
        help=f"llama.cpp host (default: {DEFAULT_HOST}; override with LLAMA_HOST)",
    )
    parser.add_argument("--max-tokens", type=int, default=-1, help="Maximum completion tokens")
    parser.add_argument("--temperature", type=float, default=0.0, help="Sampling temperature")
    parser.add_argument("--seed", type=int, default=42, help="Sampling seed")
    parser.add_argument("--timeout", type=float, default=1800.0, help="HTTP timeout in seconds")
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Print generated text as it arrives and report TTFT plus final server timings",
    )
    parser.add_argument("--list-models", action="store_true", help="List server model IDs and exit")
    args = parser.parse_args()

    if not args.list_models and not args.prompt:
        parser.error("prompt is required unless --list-models is used")

    base_url = f"http://{args.host}:{args.port}"
    try:
        models = available_models(base_url, args.timeout)
        if args.list_models:
            print("\n".join(models))
            return 0
        model = choose_model(args.model, models)

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": args.prompt}],
            "max_tokens": args.max_tokens,
            "temperature": args.temperature,
            "seed": args.seed,
            "stream": args.stream,
        }
        if args.stream:
            payload.update(
                {
                    "stream_options": {"include_usage": True},
                    "timings_per_token": True,
                    "return_progress": True,
                }
            )
        print(f"Model: {model}", file=sys.stderr)
        print(f"Request: {base_url}/v1/chat/completions", file=sys.stderr)
        started = time.monotonic()
        if args.stream:
            response = stream_chat(
                f"{base_url}/v1/chat/completions",
                body=payload,
                timeout=args.timeout,
                started=started,
            )
            print_metrics(
                model=model,
                finish_reason=response["finish_reason"],
                elapsed=response["elapsed"],
                usage=response["usage"],
                timings=response["timings"],
                ttft=response["ttft"],
                stream_duration=response["stream_duration"],
            )
            return 0

        response = request_json(
            f"{base_url}/v1/chat/completions", body=payload, timeout=args.timeout
        )
        elapsed = time.monotonic() - started
    except RuntimeError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    choices = response.get("choices", [])
    choice = choices[0] if choices else {}
    message = choice.get("message", {})
    content = message.get("content") or ""
    print(content)

    timings = response.get("timings", {})
    usage = response.get("usage", {})
    print_metrics(
        model=model,
        finish_reason=choice.get("finish_reason"),
        elapsed=elapsed,
        usage=usage,
        timings=timings,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
