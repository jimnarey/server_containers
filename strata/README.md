# Strata

Wraps [Niko1221/Strata](https://github.com/Niko1221/Strata) — an OpenAI/Anthropic-compatible
server for Qwen3.8-Flash-Next (an 80B-class MoE model), distributing experts across GPU, RAM
and SSD so it runs on a single consumer card. Strata is not Docker-native: it is its own Python
installer/launcher (`setup.py`) that manages a venv, downloads a ready-made engine build and the
GGUF model shards, and starts the server. This image just clones that tool at a pinned commit;
the *first container start* is Strata's own "first run" (engine + model download, potentially
tens of GB), and every later start is its own fast "just start it" path — nothing already done
is repeated.

This was built mostly from reading Strata's source (`setup.py`, `setup.sh`, the `MODELS`/
`FAMILIES` tables). The image has been built and its toolchain and GPU detection verified against
real hardware in this environment (`docker run --entrypoint ./setup.sh strata --check --yes`),
but a full first-run model download/engine compile has not been — watch `docker compose logs -f
strata` closely on first real start and adjust `entrypoint.sh` if its behaviour differs from
what's documented here.

As of the pinned commit, **Niko1221/Strata has no published GitHub release**, so the
"ready-made engine" `setup.py` tries first 404s and it always falls back to compiling the engine
from source. That path matters here specifically because the user's cards are RTX 50-series
(sm_120), which `setup.py` requires CUDA 13.0 for (its own comment: "an engine built with 12.8
crashed in the prompt path on Linux"). Compiling also unconditionally calls `sudo apt-get
install ...` the first time it needs a missing compiler/toolkit, which has no chance of working
in a container with no `sudo` binary. Rather than add `sudo` and let it apt-get 8-10 GB into the
container's writable layer on every first run, the image is built on `nvidia/cuda:13.0.2-devel-
ubuntu24.04` with `build-essential` installed, so `setup.py`'s own `install_build_tools()` check
(for `g++` and `nvcc`) finds both already present and skips straight to compiling — no `sudo`
involved. If Strata later publishes a release, `update_installed_engine()` will prefer the
ready-made download instead and this toolchain simply goes unused.

## Prerequisites

- NVIDIA driver ≥ 580 (CUDA 13.0) — the compiled engine and its pip-installed CUDA runtime
  libraries need this. Check with `nvidia-smi` on the host.
- Free disk space under `/mnt/data/models/strata`: each quant is a separate ~60-85 GB download,
  kept in its own subfolder, plus a one-time ~5 GB MTP draft layer shared across them.
- Free RAM: the largest quant here (`IQ3_S`) wants ~62 GB RAM by default (Strata copies every
  expert into RAM). There's a lower-RAM fallback — see "RAM and the low-RAM mode" below before
  picking a default on a RAM-constrained host.
- Time: with no engine prebuilt for download (see below), first start compiles the engine from
  source (setup.py's own estimate: 15-40 minutes) in addition to downloading the model. The
  healthcheck's `start_period` is set generously (45 minutes) so this isn't mistaken for a crash
  loop, but a plain `docker compose up -d` will look idle for a while — use `docker compose logs
  -f strata` to watch it actually working.

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
- **Context**: `STRATA_CONTEXT` (default `131072`). Strata's suggested values are `8192, 32768,
  65536, 131072, 262144`; it's a fixed ceiling set at model-load time, not a per-request
  parameter — see the context/compaction note below.
- **API key**: `STRATA_API_KEY` in `.env`, optional. Unset means no auth, same trust model as
  this repo's `ollama`/`llama-cpp` services (LAN-only, not internet-exposed).
- **RAM mode**: `STRATA_LOW_RAM` (default `auto`, matching Strata's own default) — `on` forces
  experts to be read from the model files on `/mnt/data/models/strata` through the OS file cache
  instead of copied into RAM; `off` disables that fallback outright. See below.

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

## RAM and the low-RAM mode

The `~RAM` figures above (`ram_gb` in Strata's source) are for the *default* mode, where every
expert is copied fully into RAM; the GPU just holds a copy of the busiest ones. Strata also has a
`--low-ram` mode (`low_ram_needed`/`low_ram_fits`/`low_ram_gpu_share` in `setup.py`) where experts
are instead read from the GGUF files under `/mnt/data/models/strata` through the OS file cache,
with the GPU holding whatever share of the model's "arena" (`arena_gb`, a smaller figure than
`ram_gb`) fits in VRAM. `auto` only turns this on when RAM is clearly short — specifically when
available RAM is less than `arena_gb + 10 GB`.

Measured against this host (verified with `--check`, which reported 61 GB RAM, a 15.9 GB-VRAM
RTX 5060 Ti): `IQ3_S` sits just above that auto-threshold (needs 60.3 GB to trigger low-RAM, this
host has 61 GB), so by default it stays in the full RAM-resident mode — which `--check` reports
as **"tight"** (within 8 GB of its 62 GB requirement), leaving little headroom for anything else
running on this shared host. Forcing `STRATA_LOW_RAM=on` for `IQ3_S` here would only put ~22% of
its experts in VRAM (Strata's own threshold for its "expect it to be much slower" warning is
60%), so it isn't a free way to buy back headroom for this particular quant/GPU combination —
it's a real speed-for-RAM trade here, not a no-cost one.

Practical options, in order of how little they change:
- **Leave it as installed** (`IQ3_S`, `STRATA_LOW_RAM=auto`): works, but RAM is genuinely tight
  if other services on this host are also active. Worth watching `free -h` under load.
- **Force `STRATA_LOW_RAM=on`**: trades real inference speed (most experts read from NVMe-backed
  file cache) for RAM headroom. Reasonable if this host is otherwise idle while Strata runs.
- **Switch `STRATA_MODEL` to `IQ3_XXS` or `IQ2_XS`**: both report "fits" cleanly in RAM at ~60 GB
  and ~48 GB respectively, no low-RAM trade-off needed, one tier down in quality from `IQ3_S`.

This is a judgment call about how much of this host's RAM is actually free when Strata is
serving, which isn't something to decide from source alone — check `free -h` in practice once
other services are running their normal workloads.

## Build and first start

```bash
docker compose build strata
docker compose up -d strata
docker compose logs -f strata
```

## Downloading additional quants ahead of time

The running service only serves whatever `STRATA_MODEL`/`STRATA_FAMILY` are set to, but you can
pre-download others into the same shared `/models` volume by overriding the entrypoint for a
one-off run (`--setup` = "install another model", `--no-start` = don't launch the server).

**Run these one at a time, never concurrently with each other or with the main `strata` service.**
The MTP draft layer (~5 GB, shared across all qwen-family quants) is staged under
`/data/mtp/tensors` with no file-locking; two `setup.sh` invocations preparing it at the same time
will interleave their writes and corrupt it (`size X != Y` on one of the tensor files, caught by
Strata's own sanity check, both processes exit 1). This actually happened when this README was
first written and tested: fixed by `docker stop strata`, deleting `/mnt/work/strata/mtp` (cheap to
regenerate - it's a separate ~5 GB fetch, not the 60-85 GB model downloads, which are untouched
and resumable), then re-running the quants one at a time before restarting `strata`. If you ever
see this error, that's the fix.

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
- Compiling from source means every image rebuild (`docker compose build strata`, e.g. to move
  to a newer pinned commit) throws away the previously compiled engine binary, since it lives
  under `/app` inside the image/container layer, not on a mounted volume. Expect the next
  container start after a rebuild to recompile (15-40 minutes), not just restart.
- Strata always passes `--open` to try to open a browser on start; there is no `--no-open` flag
  as of the pinned commit. In this headless container that should just fail silently, but if
  logs show it blocking startup, that's the place to look.
