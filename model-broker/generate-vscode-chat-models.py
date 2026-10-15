#!/usr/bin/env python3
"""Regenerate vscode-chat-models.json from the two presets the model broker serves.

Reads the llama.cpp preset (ctx-size) and the Strata preset (env.STRATA_CONTEXT), and writes
one entry per model, llama.cpp's first, in each file's own order. The apiKey placeholder is
kept from the existing file, so VS Code's saved secret for it still applies.

    ./model-broker/generate-vscode-chat-models.py
"""

import argparse
import json
import re
import secrets
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
# Each model's output limit; its input limit is the rest of its context window.
MAX_OUTPUT_TOKENS = 8192


def read_contexts(path: Path, key: str) -> list[tuple[str, int]]:
    """Return (model ID, context size) for each section of a preset, in file order."""
    found: list[tuple[str, int]] = []
    name: str | None = None
    context: str | None = None

    def finish() -> None:
        if name is None:
            return
        if context is None or not re.fullmatch(r"[1-9][0-9]*", context):
            sys.exit(f"{path}: [{name}] has no valid {key}")
        found.append((name, int(context)))

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith(";"):
            continue
        section = re.fullmatch(r"\[(.+)\]", line)
        if section:
            finish()
            name, context = section.group(1), None
            continue
        setting, separator, value = line.partition("=")
        if name is not None and separator and setting.strip() == key:
            context = value.strip()
    finish()
    if not found:
        sys.exit(f"{path}: no model sections")
    return found


def existing_key(path: Path) -> str:
    try:
        return str(json.loads(path.read_text(encoding="utf-8"))["apiKey"])
    except (OSError, ValueError, KeyError):
        return f"${{input:chat.lm.secret.-{secrets.token_hex(4)}}}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--llama-preset", type=Path, default=ROOT / "llama-cpp/config/models-preset.ini")
    parser.add_argument("--strata-preset", type=Path, default=ROOT / "strata/config/models-preset.ini")
    parser.add_argument("--output", type=Path, default=HERE / "vscode-chat-models.json")
    parser.add_argument(
        "--url",
        default="http://192.168.50.136:11460/v1/chat/completions",
        help="the broker's published chat completions URL",
    )
    arguments = parser.parse_args()

    models = read_contexts(arguments.llama_preset, "ctx-size") + read_contexts(
        arguments.strata_preset, "env.STRATA_CONTEXT"
    )
    ids = [model_id for model_id, _ in models]
    if len(set(ids)) != len(ids):
        sys.exit("a model ID appears in both presets")
    entries = [
        {
            "id": model_id,
            "name": model_id,
            "url": arguments.url,
            "toolCalling": True,
            "vision": False,
            "maxInputTokens": context - MAX_OUTPUT_TOKENS,
            "maxOutputTokens": MAX_OUTPUT_TOKENS,
        }
        for model_id, context in models
    ]
    if any(entry["maxInputTokens"] <= 0 for entry in entries):
        sys.exit("a context size is not larger than the output limit")
    lines = ",\n".join(f"    {json.dumps(entry)}" for entry in entries)
    arguments.output.write_text(
        '{\n  "name": "ai-ubuntu-model-broker",\n  "vendor": "customendpoint",\n'
        f'  "apiKey": {json.dumps(existing_key(arguments.output))},\n'
        '  "apiType": "chat-completions",\n  "models": [\n' + lines + "\n  ]\n}\n",
        encoding="utf-8",
    )
    print(f"wrote {len(entries)} models to {arguments.output}")


if __name__ == "__main__":
    main()
