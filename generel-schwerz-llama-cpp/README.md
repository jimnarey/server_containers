# GenerelSchwerz llama.cpp MoE-cache services

`llama-cpp-generel-schwerz-16gb` is the one-GPU profile and
`llama-cpp-generel-schwerz-32gb` is the two-GPU profile. They are separate
from the ordinary `llama-cpp` service and use the experimental CUDA MoE expert
cache in [GenerelSchwerz/llama.cpp](https://github.com/GenerelSchwerz/llama.cpp).

The image is built at the Dockerfile's pinned revision:

```text
branch: moe-cache
commit: b46f7f7a436f990932d3da3ec53380e2b9effc89
CUDA:   12.8.1, compiled for CUDA architecture 120
```

The build context is respectively:

```text
/mnt/work/generel-schwerz-llama-cpp/16gb/source
/mnt/work/generel-schwerz-llama-cpp/32gb/source
```

Docker copies the selected context into the build and detaches that copy at the
pinned commit. It never checks out or otherwise mutates either host source
tree. Both host checkouts must contain the pinned commit (the supplied
checkouts do). To use another fork revision, edit the `LLAMA_FORK_BRANCH` and
`LLAMA_FORK_COMMIT` arguments at the top of `Dockerfile`, then ensure that
commit exists in both local source checkouts.

## Runtime configuration

Create the separate runtime configurations before first start:

```sh
install -D -m 0644 generel-schwerz-llama-cpp/config/16gb.ini \
  /mnt/work/generel-schwerz-llama-cpp/16gb/config/config.ini
install -D -m 0644 generel-schwerz-llama-cpp/config/32gb.ini \
  /mnt/work/generel-schwerz-llama-cpp/32gb/config/config.ini
```

The config files are mounted at `/etc/llama.cpp/config.ini` and are deliberately
outside this repository. They configure all models selected through the router.
Both services mount the shared model library, `/mnt/data/models/gguf`, read-only
at `/models`. Keep a model GGUF (or its shards) at the root or in an immediate,
flat model directory below that root.

The 16GB service is exposed on port 11438 and limits CUDA visibility to physical
GPU 0. The 32GB service is on port 11439 and uses both GPUs with a layer split.
Run only one of these profiles at a time. In particular, stop ordinary
`llama-cpp` before the 32GB profile; it is otherwise also free to allocate both
cards.

The templates start at 64K context, Q8 KV, 8 physical CPU threads, and an MoE
expert cache of 32 or 64 slots. Expert-cache size is per cached expert tensor
on its CUDA device. Treat 64 slots as the first 32GB experiment, not a promise
that every model will fit; reduce it if either GPU runs out of memory.

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

Keep this setting for the initial MoE-cache tests. It permits the fork's
grouped decode path. Changing to `mmap` is a different, slower experiment and
should not be compared directly with the supplied profile.

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

The 32GB service starts with the conservative two-card layer split. Leave the
experimental tensor split for a measured follow-up: on cards connected only by
PCIe it can improve some workloads but adds inter-GPU traffic.

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

The router discovers GGUFs at `/models` and in its immediate model
directories. Keep each model in one flat, model-specific directory under
`/mnt/data/models/gguf`. A shard set such as
`MODEL-00001-of-00003.gguf` through `MODEL-00003-of-00003.gguf` is one model,
not three alternatives: every shard is required. Point llama.cpp at (or select)
the first shard and it automatically opens its siblings. The Qwen3.8 download
command creates links to its three shards in the model directory specifically
to keep that set discoverable without duplicating the files.

## Build and run

```sh
docker compose build llama-cpp-generel-schwerz-16gb
docker compose up -d llama-cpp-generel-schwerz-16gb

# Stop the one-GPU profile before the two-GPU profile.
docker compose stop llama-cpp-generel-schwerz-16gb llama-cpp
docker compose build llama-cpp-generel-schwerz-32gb
docker compose up -d llama-cpp-generel-schwerz-32gb
```

Use `/v1/models` and the returned model ID to select a GGUF in a request:

```sh
curl http://192.168.50.136:11438/v1/models
curl http://192.168.50.136:11439/v1/models
```

For containers on this Compose network, the corresponding API bases are
`http://llama-cpp-generel-schwerz-16gb:8080/v1` and
`http://llama-cpp-generel-schwerz-32gb:8080/v1`.
