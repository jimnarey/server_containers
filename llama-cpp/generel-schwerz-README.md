# GenerelSchwerz llama.cpp MoE-cache services

`llama-cpp-generel-schwerz-16gb` is the one-GPU profile and
`llama-cpp-generel-schwerz-32gb` is the two-GPU profile. They are separate
from the ordinary `llama-cpp` service and use the experimental CUDA MoE expert
cache in [GenerelSchwerz/llama.cpp](https://github.com/GenerelSchwerz/llama.cpp).

The shared `llama-cpp/Dockerfile` receives this pin from the 16GB service's
Compose build arguments:

```text
branch: qwen4exp-mtp
commit: e69a1d0be5f8ae0080593865b38b175223059199
CUDA:   12.8.1, compiled for CUDA architecture 120
```

The 32GB service has separate `build.args` and pins a different commit:

```text
branch: codex/moe-grouped-multigpu
commit: 0ed73d1c9e26587cc41b73f77e9e058a0da55368
CUDA:   12.8.1, compiled for CUDA architecture 120
```

The two services deliberately build from different commits now. `qwen4exp-mtp`'s
MoE cache is hardcoded to CUDA device 0
([GenerelSchwerz/llama.cpp#90](https://github.com/GenerelSchwerz/llama.cpp/issues/90))
and cannot use a second GPU -- confirmed still true as of this pin (0 commits
of drift on that branch). `codex/moe-grouped-multigpu` branches directly off
the 16GB service's exact pin and adds a real, physically-validated two-GPU
expert cache (its own `docs/moe-grouped-multigpu.md`, in the source tree,
records design, evidence and known gaps in detail) -- not yet merged upstream
into `qwen4exp-mtp`. See `models-preset-32gb.ini`'s header comment for the
real constraints this pin imposes on model configuration, and
`docker-compose.yml`'s comment on `llama-cpp-generel-schwerz-32gb` for the
full rationale.

Docker maintains one neutral `GenerelSchwerz/llama.cpp` clone in its build
cache at `/mnt/work/llama-cpp/sources/generel-schwerz-llama-cpp`. Each service
then copies it to a service-suffixed sibling, fetches and verifies its own pin,
and builds that copy. The path is within the build image, not the host. To use
another revision, edit that service's `LLAMA_BRANCH` and `LLAMA_COMMIT` in
`compose.ai.yml`.

## Runtime configuration

Create the separate runtime configurations before first start:

```sh
install -D -m 0644 llama-cpp/config/llama-cpp-generel-schwerz-16gb/config.ini \
  /mnt/work/llama/llama-cpp-generel-schwerz-16gb/config.ini
install -D -m 0644 llama-cpp/config/llama-cpp-generel-schwerz-32gb/config.ini \
  /mnt/work/llama/llama-cpp-generel-schwerz-32gb/config.ini

./llama-cpp/generate-models-preset.py --preset-only --force \
  --preset llama-cpp/config/llama-cpp-generel-schwerz-16gb/models-preset.ini \
  /mnt/work/llama/llama-cpp-generel-schwerz-16gb
./llama-cpp/generate-models-preset.py --preset-only --force \
  --preset llama-cpp/config/llama-cpp-generel-schwerz-32gb/models-preset.ini \
  /mnt/work/llama/llama-cpp-generel-schwerz-32gb
```

2026-09-16: these are now two genuinely different files, not one shared
template installed twice. The two services build from different fork commits
(see below) with different real constraints, so their catalogues differ --
notably, Flash Next is only in the 16GB one.

The config files are mounted at `/etc/llama.cpp/config.ini` and are deliberately
outside this repository. The separate `models-preset.ini` copies are mounted at
`/etc/llama.cpp/models-preset.ini`. Both services mount the shared model
library, `/mnt/data/models/gguf`, read-only at `/models`.

The router deliberately has no `--models-dir`. It exposes only the explicit,
large-MoE entries in its model preset, so a raw publisher/directory ID cannot
appear as a duplicate or bypass a profile. Add a direct `model = /models/...`
section to the repository template, install it to each runtime location, then
recreate the service when deliberately making another model available.

The 16GB service is exposed on port 11438 and limits CUDA visibility to physical
GPU 0. The 32GB service is on port 11439 and exposes both GPUs.

2026-09-16: the 32GB service's model placement is now genuinely different
from the 16GB one, not just "the same idea across two cards." Because
`codex/moe-grouped-multigpu`'s cache is layer-split (each GPU gets its own
local cache for the layers assigned to it), every model there uses
`n-gpu-layers = all` / `fit = off` / `cpu-moe = true` globally in
`config.ini` -- whole layers, not the 16GB service's per-model mix of
fully-host-resident (`n-gpu-layers = 0`) and dense-core-on-GPU
(`n-gpu-layers = all`) placements. `split-mode = layer` / `tensor-split =
1,1` are no longer an unused placeholder here; they're load-bearing.

Run only one of these profiles at a time. In particular, stop ordinary
`llama-cpp` before either profile; it is otherwise also free to allocate both
cards.

The 16GB template starts at 64K context, Q8 KV, 8 physical CPU threads, and a
flat MoE expert cache of 48 slots (tuned specifically for Flash Next's real
workload; see the dated comments in `16gb.ini`, not assumed correct for the
other models sharing that service). The 32GB template also starts at 64K
context and Q8 KV, but sets `moe-expert-cache-size` per model in
`models-preset-32gb.ini` instead of one flat value -- expert_used_count
varies from 4 to 10 across that catalogue, and the fork's own reference
example scales cache size with active-expert count, not a single constant.
None of the 32GB values have been benchmarked; they're a starting point sized
by that same ratio, nothing more. Expert-cache size is per cached expert tensor
on its CUDA device. Treat 64 slots as the first 32GB experiment, not a promise
that every model will fit; reduce it if either GPU runs out of memory.

Most preset entries deliberately set `n-gpu-layers = 0`. The fork's
expert-cache override still places routed MoE experts behind a CUDA cache, but
this keeps ordinary model tensors on the host. Qwen3.8 Flash Next is the
intentional exception: its preset uses `n-gpu-layers = all` and
`override-tensor = per_layer_token_embd=CPU`. This places its reusable dense
core on the selected GPU(s), while its large phrase/PLE table remains lazy,
file-backed on the host. Its routed experts are placed by the fork's CUDA cache
override, not by the ordinary layer offload.

### Verifying a config.ini change actually took effect

`config.ini`'s `[*]` settings (`batch-size`, `moe-expert-cache-size`,
`reasoning-budget`, and everything else in that section) do **not** appear in
the spawned per-model process's command line. Checking `ps aux`, `docker
inspect`, or the router's own `/v1/models` `status.args` field for one of
these keys after a restart will not find it — those all report only the
explicit CLI args the router passes when it spawns a model instance (the
alias, ctx-size, model path, and whatever is in that model's
`models-preset.ini` section). It is easy to read that absence as "the setting
was never applied" — it wasn't dropped, it just isn't visible there.

Each spawned instance reads `/etc/llama.cpp/config.ini` itself, directly, at
its own startup — confirmed by `using config file: /etc/llama.cpp/config.ini`
in `docker logs`, once per spawned instance. That line proves the file was
read, but not that any individual key inside it parsed as intended (a typo'd
key name would fail silently the same way). To actually confirm a change
took effect, exercise it: watch `nvidia-smi` VRAM before/after a `moe-expert-cache-size`
change, or send a request that would exhaust `reasoning-budget` and check the
response actually contains the injected message. Restarting the container and
seeing it come up healthy only proves the router started; it proves nothing
about what the per-model instance itself picked up.

## How these profiles are intended to work

This fork is most useful for sparse MoE models. At each token, an MoE model
activates only a small subset of its experts. The fork keeps recently used
experts in a CUDA LRU cache and serves cold experts from CPU-side pinned memory.
It therefore trades system RAM, PCIe transfers, and a little VRAM for much
better decode speed than repeatedly moving the same hot experts. A dense model
has no experts to cache: use the ordinary `llama-cpp` service for dense-model
experiments rather than expecting a speed-up from this service.

Qwen3.8 Flash Next is an unusually favourable but demanding case. Its large
lookup/phrase table is accessed sparsely and can remain file-backed on fast
local storage, so its GGUF can be larger than installed RAM. That is not a
general rule for GGUF models: CPU-resident MoE experts and the KV cache still
need substantial RAM. The video test behind this setup found that prompt
processing was much more RAM-sensitive than decode. Keep the models on the
local SSD/NVMe, not a network mount, and leave headroom for the host, Docker,
and any desktop container.

For the 64 GiB host, regard the Qwen3.8 UD-Q3_K_XL profile as a near-capacity
experiment. A short request in the fork's published 64K/Q8-KV configuration
used roughly 53.5 GiB of host memory. Do not combine it with a resident
CPU-heavy workload, an XFCE desktop container, or another large RAM model
without measuring first. Swap activity is a failure signal, not useful extra
capacity for interactive inference.

### Important settings

**`load-mode = none`**

Keep this setting for the normal MoE-cache tests. Qwen3.8 Flash Next is the
intentional exception: it uses `mmap` and `lazy-mode = on`, allowing its large
phrase/PLE table to stay file-backed. Do not use the Flash Next result to judge
the normal `load-mode = none` profiles.

**`moe-expert-cache-size`**

This is the number of expert slabs retained **per expert tensor on each CUDA
device**, not a total cache size for the process. More slots generally raise
the hit rate but consume more VRAM. Start with 32 on the one-card profile and
64 on the two-card profile. If a load or first long request exhausts VRAM,
reduce this before reducing the 64K context; if decode is slow while VRAM
headroom remains, try a modest increase and benchmark it.

**`ctx-size = 65536`, `parallel = 1`, and Q8 KV**

64K is the baseline for coding work here. The context is shared between server
slots, so `parallel = 1` gives the request all 64K tokens. Q8 K/V is a
deliberate quality/memory compromise; KV allocation grows materially with
context. Do not raise context, parallelism, cache quantization, and
expert-cache size at the same time. Establish a stable 64K single-user run
first.

**`threads = 8` and `threads-batch = 8`**

Start with the 5700X's eight physical cores, not all 16 SMT threads. The video
observed substantial spin-waiting and a large throughput improvement when
reducing a six-core CPU from 12 logical threads to six physical threads.
Benchmark 6, 8, and 12 on this host, changing only these two settings; the
best value is workload- and model-dependent.

**`batch-size = 8192` and `ubatch-size = 512`**

These favour prompt ingestion. Lower them if prefill causes a VRAM or RAM peak,
or if the machine becomes unresponsive. They are not the first knobs to turn
when only decode is slow.

**`split-mode = layer`, `tensor-split = 1,1`**

These settings matter only for a later experiment that offloads one or more
ordinary model layers. Keep `n-gpu-layers = 0` for the Qwen3.8 Flash Next
baseline: its roughly 29 GiB non-expert tensor cannot be placed on either 16
GiB GPU. Leave the experimental tensor split for a measured follow-up: on
cards connected only by PCIe it can improve some workloads but adds inter-GPU
traffic.

### GPU and host-memory discipline

The 16GB profile makes only physical GPU 0 visible. The 32GB profile makes both
cards visible, so the normal `llama-cpp` service must be stopped first. The
ordinary service currently requests all GPUs too; stop it before the 16GB
profile as well unless it has separately been configured to expose only GPU 1.
Do not rely on “unused” VRAM reported before a model load—leave at least 1–2
GiB free on every participating card for CUDA workspaces and transient peaks.

Use these host-side commands while loading and running a first request:

```sh
watch -n 1 nvidia-smi
watch -n 1 free -h
docker stats llama-cpp-generel-schwerz-16gb-c
# or: docker stats llama-cpp-generel-schwerz-32gb-c
```

Start with a short request, then a representative coding prompt at 64K. Watch
for OOM kills, host-memory exhaustion, or swap use before making the prompt
larger. Change one setting per run and record prompt-evaluation and decode
tokens/second separately: the fork primarily improves decode through expert
reuse, while RAM and batch sizing strongly affect prompt evaluation.

## Model layout and sharded GGUFs

Keep each model in one flat, model-specific directory under
`/mnt/data/models/gguf`, then refer to its file directly from the preset. A
shard set such as
`MODEL-00001-of-00003.gguf` through `MODEL-00003-of-00003.gguf` is one model,
not three alternatives: every shard is required. Point llama.cpp at (or select)
the first shard and it automatically opens its siblings.

## Build and run

```sh
docker compose build llama-cpp-generel-schwerz-16gb
docker compose up -d llama-cpp-generel-schwerz-16gb

# Stop the one-GPU profile before the two-GPU profile.
docker compose stop llama-cpp-generel-schwerz-16gb \
  llama-cpp-gpu-0 llama-cpp-gpu-1 llama-cpp-all-gpus
docker compose build llama-cpp-generel-schwerz-32gb
docker compose up -d llama-cpp-generel-schwerz-32gb
```

Use `/v1/models` and the returned preset ID to select a GGUF in a request:

```sh
curl http://192.168.50.136:11438/v1/models
curl http://192.168.50.136:11439/v1/models
```

For containers on this Compose network, the corresponding API bases are
`http://llama-cpp-generel-schwerz-16gb:8080/v1` and
`http://llama-cpp-generel-schwerz-32gb:8080/v1`.
