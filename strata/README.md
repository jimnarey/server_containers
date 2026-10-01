# Strata

Wraps [Niko1221/Strata](https://github.com/Niko1221/Strata) — an OpenAI/Anthropic-compatible
server for Qwen3.8-Flash-Next (an 80B-class MoE model), distributing experts across GPU, RAM
and SSD so it runs on a single consumer card. Strata is not Docker-native: it is its own Python
installer/launcher (`setup.py`) that manages a venv, downloads a ready-made engine build and the
GGUF model shards, and starts the server. This image just clones that tool at a pinned commit;
the *first container start* is Strata's own "first run" (engine + model download, potentially
tens of GB), and every later start is its own fast "just start it" path — nothing already done
is repeated.

This was built entirely from reading Strata's source (`setup.py`, `setup.sh`, the `MODELS`/
`FAMILIES` tables), not from a live run in this environment — watch `docker compose logs -f
strata` closely on first start and adjust `entrypoint.sh` if its behaviour differs from what's
documented here.

## Prerequisites

- NVIDIA driver ≥ 580 (CUDA 13.0) — Strata's prebuilt engine and its pip-installed CUDA runtime
  libraries need this. Check with `nvidia-smi` on the host.
- Free disk space under `/mnt/data/models/strata`: each quant is a separate ~60-85 GB download,
  kept in its own subfolder, plus a one-time ~5 GB MTP draft layer shared across them.
- Free RAM: the largest quant here (`IQ3_S`) wants ~62 GB RAM in addition to the GPU. See the
  table below before picking a default.

## What's fixed vs configurable

- **GPU: defaults to GPU 1 only.** `compose.ai.yml` restricts the container to physical GPU 1
  via `device_ids`, so Strata only ever sees one card (always index 0 from its own point of
  view — `entrypoint.sh` always passes `--gpu 0`). Change `STRATA_GPU_DEVICE_ID` in `.env` to
  move it. It also acquires the same GPU lock file (`llama-gpu-locks` volume) that
  `llama-cpp-generel-schwerz-16gb` uses on GPU 1, so the two won't silently collide — whichever
  starts first keeps the card until it stops.
- **Models: always under `/mnt/data/models/strata`.** Override with `STRATA_MODELS` in `.env`
  if you want them elsewhere. Engine/venv/config state (small) lives separately under
  `STRATA_HOME` (default `/mnt/work/strata`), matching this repo's `/mnt/data` = bulk assets,
  `/mnt/work` = app state convention.
- **Active model**: `STRATA_FAMILY` / `STRATA_MODEL` in `.env` select what the running service
  actually serves (default `qwen` / `IQ3_S`). Switching is a restart, not a re-download, once
  the quant you want is already on disk (see below).
- **Context**: `STRATA_CONTEXT` (default `65536`). Strata's suggested values are `8192, 32768,
  65536, 131072, 262144`; it's a fixed ceiling set at model-load time, not a per-request
  parameter — see the context/compaction note below.
- **API key**: `STRATA_API_KEY` in `.env`, optional. Unset means no auth, same trust model as
  this repo's `ollama`/`llama-cpp` services (LAN-only, not internet-exposed).

## Quant sizes (from Strata's own `MODELS` table)

| Family | Model | Download | RAM | Notes |
|---|---|---|---|---|
| qwen | `IQ3_S` | 83.6 GB | ~62 GB | Best quality (matches full BF16 on Strata's published benchmarks); qwen only, no Swift equivalent |
| qwen | `IQ2_XS` | 68.0 GB | ~48 GB | 2-bit i-quant, close in speed to `Q2_0`, noticeably better quality |
| qwen | `Q2_0` | 66.4 GB | ~48 GB | Fastest, lowest quality; qwen only |
| qwen | `IQ3_XXS` | 75.8 GB | ~60 GB | 3-bit i-quant, between `IQ2_XS` and `IQ3_S` |
| swift | `IQ3_XXS` | ~76 GB | ~60 GB | Swift 1.5's best available quant — it has no `IQ3_S` |
| swift | `IQ2_XS` | ~68 GB | ~48 GB | |
| coder | `IQ1_M` | 58.4 GB | ~32 GB | Half the experts pruned for code/tools/vision; weaker elsewhere |

Swift 1.5 is UkisAI's fine-tune ("thinks ~63% fewer tokens, answers ~1.8x sooner" per its
authors) — same architecture and GSQ-RCO quant scheme, different weights, own HuggingFace repo.

## Build and first start

```bash
docker compose build strata
docker compose up -d strata
docker compose logs -f strata
```

## Downloading additional quants ahead of time

The running service only serves whatever `STRATA_MODEL`/`STRATA_FAMILY` are set to, but you can
pre-download others into the same shared `/models` volume by overriding the entrypoint for a
one-off run (`--setup` = "install another model", `--no-start` = don't launch the server):

```bash
# IQ3_S (qwen) - the default this service already installs on first start
docker compose run --rm --entrypoint ./setup.sh strata \
  --yes --setup --no-start \
  --family qwen --model IQ3_S \
  --data-dir /data --models-dir /models

# IQ2_XS (qwen)
docker compose run --rm --entrypoint ./setup.sh strata \
  --yes --setup --no-start \
  --family qwen --model IQ2_XS \
  --data-dir /data --models-dir /models

# Swift 1.5 - it has no IQ3_S, so IQ3_XXS is its best available quant
docker compose run --rm --entrypoint ./setup.sh strata \
  --yes --setup --no-start \
  --family swift --model IQ3_XXS \
  --data-dir /data --models-dir /models
```

Each command downloads into its own subfolder under `/models` (mapped to
`/mnt/data/models/strata`) without touching files from a different family/quant. To actually
serve one, set `STRATA_FAMILY`/`STRATA_MODEL` in `.env` to match and restart:

```bash
docker compose up -d strata
```

## Hardware check / calibration

Strata's Windows `START-HERE.bat --calibrate` has a direct Linux equivalent — `setup.sh` is a
thin wrapper that forwards all arguments to the same `setup.py`, so both flags exist here too:

```bash
# quick compatibility check, no changes
docker compose run --rm --entrypoint ./setup.sh strata --check --yes

# 5-10 minute tuning pass for whichever model is currently installed, then starts it
docker compose run --rm --entrypoint ./setup.sh strata --calibrate --yes
```

## Context and compaction — read before pointing an autonomous agent at this

Strata has no auto-compaction/truncation: exceeding the context you set is a hard error ("the
conversation is longer than the context you chose... start a new chat, or run `SETUP.bat` and
pick more context"). It also can't be changed per-request — `STRATA_CONTEXT` is fixed for the
life of the running config. If you point an autonomous client (e.g. deepseek) at this backend,
its own compaction needs to keep requests comfortably under `STRATA_CONTEXT`, since Strata
itself won't help if that's exceeded.

## Known caveats

- Strata's model-quant files here are ISTA-DASLab's own GSQ-RCO quantization, packaged as two
  GGUF shards with a specific naming convention. They are a different quantization method from,
  and not interchangeable with, GGUF files you already have for `ollama`/`llama-cpp` (e.g.
  Unsloth's UD-quants) — expect a fresh download per quant, not reuse.
  <!-- unsloth quality vs GSQ-RCO quality on the same evals is unverified; check before relying
       on Strata's own self-reported benchmark numbers as a comparison point. -->
- `setup.py` starts the actual server with `subprocess.call()`, so it's a grandchild of the
  container's PID 1, not PID 1 itself — `init: true` in `compose.ai.yml` is there so `docker
  compose stop` forwards `SIGTERM` to the whole process group instead of just the outer
  `setup.py` process.
- Strata always passes `--open` to try to open a browser on start; there is no `--no-open` flag
  as of the pinned commit. In this headless container that should just fail silently, but if
  logs show it blocking startup, that's the place to look.
