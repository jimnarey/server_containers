# Local llama.cpp performance findings

Durable record of every real performance measurement taken across the local
llama.cpp deployments (`llama-cpp-all-gpus`, the GenerelSchwerz MoE-cache forks,
and standalone comparison runs), what was done to get each number, and what
conclusions are and are not supported by them. Host: 2x RTX 5060 Ti (16 GiB
each, no peer access -- `nvidia-smi topo -p2p r` reports `CNS`), 60 GiB system
RAM (confirmed via `free -h`; earlier planning assumed 64 GiB and was wrong),
8 GiB swap.

Update this file when a new benchmark is run, rather than letting numbers
live only in chat history. Distinguish a *measured* result (real load, real
request, numbers recorded here) from an *estimate* (parameter-count or
published-config derived) -- both appear below, but never presented as the
same kind of evidence.

## Service roles

Each service has an established, evidenced role -- not an arbitrary
assignment. New models should be placed according to these roles, and a
model that doesn't fit any of them cleanly is worth flagging rather than
shoehorning in.

- **`llama-cpp-cpu`** (no GPU passthrough -- architecturally cannot see a
  GPU, not just configured not to use one). Two real use cases: (a) small
  dense chat models, comfortably under 10 GiB, kept here deliberately and
  never added to a GPU preset (`gemma-3n-E2B-it`, `gemma-3n-E4B-it`,
  `NVIDIA-Nemotron-3-Nano-4B`, `Qwen3.5-9B`, `Ornith-1.5-9B`); (b) MoE
  models too large to fit combined 32 GiB VRAM even with `n-cpu-moe`/
  tensor-split, where CPU-only sparse-expert-activation decode is still
  genuinely usable (`Qwen3-Coder-Next`, `Qwen3-Next-80B-A3B-Instruct`, both
  ~45 GiB, 9-13 tok/s decode -- a real, working option, not a fallback of
  last resort). `Devstral-Small` breaks this pattern slightly: it's dense,
  not oversized-MoE, added here not because it's too big but because
  single-GPU placement couldn't give it a useful context size -- CPU is
  the RAM-unconstrained alternative to the dual-GPU tensor-split path for
  that specific problem, a different reason from every other CPU entry.
- **`llama-cpp-gpu-0` / `llama-cpp-gpu-1`** ("the 16GB service" -- one
  physical GPU each via Docker's own `gpus.device_ids`, confirmed only one
  GPU is visible inside either container; shared curated preset
  `llama-cpp-16gb`). Single-card placement for models that are either (a)
  small/dense enough to sit fully GPU-resident (`qwen2.5-coder-7b/14b`,
  the Qwen3.8-27B 3-bit quants, `gpt-oss-20b-F16`), or (b) MoE models
  17-20 GiB that need `n-cpu-moe` partial expert offload to fit one card
  (eight such entries as of 2026-09-18). Explicitly **not** used for
  models that need dual-GPU bandwidth-doubling, or models too large to fit
  even with offload -- those belong on `llama-cpp-all-gpus` instead.
- **`llama-cpp-all-gpus`** ("the 32GB service" -- both cards, `gpus: all`,
  keeps the `llama-cpp` DSH-compatibility alias). Two real, distinct
  reasons a model lands here, not one blanket "big models" rule: (a)
  models too large for one card even with offload (dense 70B-class
  quants, the full dense Qwen3.8-27B ladder); (b) a deliberate choice to
  force smaller models that already fit one card onto both GPUs anyway
  via `split-mode=tensor`, because dense decode is memory-bandwidth-bound
  and real A/B testing confirmed splitting roughly doubles effective
  bandwidth -- `gpt-oss-20b-F16` went from 63.76 to 141+ tok/s, the
  Qwen3.8-27B 3-bit quants from ~28-30 to 45-47 tok/s. This is a real,
  *evidenced* choice for dense architectures specifically, not a "run
  everything under 16 GiB on both GPUs" policy -- whether it helps a MoE
  model (sparse activation, a different bandwidth profile entirely) is
  genuinely untested and shouldn't be assumed to transfer either way.
  **Real tension worth naming explicitly (2026-09-18)**: forcing a small
  model onto both GPUs for a per-job speed win directly trades away
  *concurrency* -- it occupies the entire host's GPU capacity for one job,
  where the same model on a single `llama-cpp-gpu-0`/`gpu-1` card leaves
  the other card free for a second, independent job. Real numbers make
  the tradeoff concrete: `qwen2.5-coder-7b-instruct-q8_0` single-GPU
  (52.91-53.06 tok/s) vs. forced dual-GPU (90.27-90.62 tok/s) is a real
  ~1.7x speedup for *one* job, but running it single-GPU on each card
  simultaneously gets two independent ~53 tok/s jobs running at once --
  more aggregate throughput *and* more concurrency than the dual-GPU
  choice, if the workload is "run several agentic sessions," not "make
  one session as fast as possible." Which one is right depends entirely
  on whether the goal is minimum single-job latency or maximum
  simultaneous jobs -- this document records both real numbers so that
  choice can be made deliberately, not defaults to "both GPUs is always
  better."
- **`llama-cpp-generel-schwerz-16gb` / `-16gb-gpu-0`/`-gpu-1`** (fork, single
  physical GPU, a custom `moe-cache` expert-caching subsystem layered on
  the same mmap/lazy-loading mechanism the plain services also have by
  default -- see the correction above). Role: last resort for MoE models
  too large for the plain 32 GiB dual-GPU split. Got a real, deliberate
  tuning pass for exactly one model (`Qwen3.8-Flash-Next`: +125% prefill/
  +9% decode from batch/ubatch tuning) that hasn't been repeated for any
  other model on this service. Known real failure mode: two wide-attention
  architectures (`Llama-4-Scout`, `GLM-4.5-Air`) hit a genuine CUDA OOM in
  the `moe-cache` subsystem's own graph-compute buffer -- not yet
  root-caused, may be an architecture-specific interaction with
  `moe-cache` rather than a property of either model on its own.
  **Real, physical-GPU-specific constraint (2026-09-18): this service
  must run on physical GPU 1, not GPU 0** -- see the dated section below.
  The two cards are not symmetric (GPU 0: PCIe Gen3, 4 lanes negotiated;
  GPU 1: PCIe Gen4, 8 lanes), and `moe-expert-cache-size`'s constant
  host-to-GPU expert streaming is directly PCIe-bandwidth-bound. Real
  measured impact: Flash Next decode drops from 18.87 tok/s (GPU 1,
  matching this document's historical tuned range) to 6.34-6.6 tok/s
  (GPU 0) for the identical image, config, and model -- a ~3x real
  regression from card choice alone, not a software problem.
- **`llama-cpp-generel-schwerz-32gb`** (fork, `codex/moe-grouped-
  multigpu`). Established **not viable** for large models on this host:
  its `load-mode=none` requirement disables mmap entirely, so any model
  exceeding physical RAM (`gpt-oss-120b`, `GLM-4.5-Air`, both real
  failures) has no fallback but swap, producing disk-I/O-speed decode
  (2-3 tok/s), not real model performance. No established positive role
  on this host yet -- the one thing it might still offer (genuine
  cross-GPU MoE dispatch/caching for a model that *does* fit in RAM) has
  never been cleanly measured; see the test plan below.
- **`llama-cpp-csantiago78`** -- another fork variant referenced in DSH
  `settings.yaml`. Not characterized by this session's testing; no
  established role documented here.

## Resource usage by model/service (summary table)

One row per model/service combination actually run. Resource columns show
what running *this model* costs, not standing host overhead -- GPU columns
are VRAM actually allocated by the model process (not the ~13-98 MiB the
desktop compositor always holds); RAM is the `free -h` **used** figure
(non-reclaimable), reported separately from mmap'd page cache where that
distinction matters (see footnotes); CPU is whether the CPU is actually
doing inference compute or just orchestration. "Not exposed" means the
container has no access to that GPU at all (`llama-cpp-cpu` has no `gpus:`
passthrough in `compose.ai.yml` -- it's not "0% used", it architecturally
cannot see a GPU); "not used" means the GPU is visible to the container but
the model didn't touch it.

Rows are grouped by model, so a model with several tested resource
combinations appears as consecutive rows rather than scattered by service.

| Model | Service | GPU 1 | GPU 2 | RAM | CPU | Prefill | Decode |
|---|---|---|---|---|---|---|---|
| gpt-oss-20b-F16 | standalone, 1 GPU pinned | ~13.3 GiB | not exposed | baseline only | idle | 3,802 tok/s | 63.76 tok/s |
| gpt-oss-20b-F16 | `llama-cpp-gpu-1` (MoE, single physical GPU)¹⁴ | 14.1 GiB | not exposed | baseline only | idle | 580.26 tok/s | 94.34 tok/s cold, 94.39 tok/s warm |
| gpt-oss-20b-F16 | `llama-cpp-all-gpus` (forced dual-GPU tensor-split)⁹ | 7.4 GiB | 7.5 GiB | baseline only | idle | 557.97 tok/s (cold) | 141.38 tok/s cold, 142.33 tok/s warm |
| gpt-oss-20b-F16 | CPU-only (`llama-cpp-cpu`) | not exposed | not exposed | 19 GiB | **compute (8 threads)** | 68.06 tok/s | 10.42-10.43 tok/s |
| Qwen3.8-27B-UD-Q4_K_M | `llama-cpp-all-gpus` (dense, tensor-split)⁷ | 10.6 GiB (97-98% util) | 10.6 GiB (97% util) | baseline only | idle | 68.13 tok/s⁷ | 39.11-40.62 tok/s⁷ |
| Qwen3.8-27B-UD-Q5_K_M | `llama-cpp-all-gpus` (dense, tensor-split) | 12.0 GiB | 12.0 GiB | baseline only | idle | -- | 34.92 tok/s cold, 34.94 tok/s warm |
| Qwen3.8-27B-UD-Q6_K_M | `llama-cpp-all-gpus` (dense, tensor-split) | 14.3 GiB | 14.3 GiB | baseline only | idle | 184.80 tok/s⁶ | 30.16-31.05 tok/s |
| Qwen3.8-27B-UD-IQ3_S | `llama-cpp-gpu-1` (dense, single physical GPU)⁸ | 14.5 GiB | not exposed | baseline only | idle | -- | 30.64 tok/s cold, 30.69 tok/s warm |
| Qwen3.8-27B-UD-IQ3_S | `llama-cpp-all-gpus` (dense, forced dual-GPU tensor-split)⁹ | 9.1 GiB | 9.2 GiB | baseline only | idle | 202.25 tok/s (cold) | 47.50 tok/s cold, 47.55 tok/s warm |
| Qwen3.8-27B-UD-Q3_K_XL | `llama-cpp-gpu-1` (dense, single physical GPU)⁸ | 14.3 GiB | not exposed | baseline only | idle | -- | 28.92 tok/s cold, 28.91 tok/s warm |
| Qwen3.8-27B-UD-Q3_K_XL | `llama-cpp-all-gpus` (dense, forced dual-GPU tensor-split)⁹ | 9.6 GiB | 9.7 GiB | baseline only | idle | 236.89 tok/s (cold) | 45.53 tok/s cold, 45.63 tok/s warm |
| Qwen3.6-27B-Q6_K | `llama-cpp-all-gpus` (dense, forced dual-GPU tensor-split, new model)¹⁵ | 14.0 GiB | 14.0 GiB | baseline only | idle | 167.97 tok/s | 31.47 tok/s cold, 31.50 tok/s warm |
| qwen2.5-coder-7b-instruct-q4_k_m | `llama-cpp-gpu-1` (dense, single physical GPU)¹¹ | 5.4 GiB | not exposed | baseline only | idle | 1,797.27 tok/s | 80.81 tok/s cold, 81.04 tok/s warm |
| qwen2.5-coder-7b-instruct-q8_0 | `llama-cpp-gpu-1` (dense, single physical GPU)¹⁶ | 8.3 GiB | not exposed | baseline only | idle | 1,870.13 tok/s | 52.91 tok/s cold, 53.06 tok/s warm |
| qwen2.5-coder-7b-instruct-q8_0 | `llama-cpp-all-gpus` (dense, forced dual-GPU tensor-split)¹⁶ | 4.4 GiB | 4.5 GiB | baseline only | idle | 1,342.20 tok/s | 90.27 tok/s cold, 90.62 tok/s warm |
| qwen2.5-coder-14b-instruct-q4_k_m | `llama-cpp-gpu-1` (dense, single physical GPU)¹¹ | 11.6 GiB | not exposed | baseline only | idle | 1,300.84 tok/s | 40.92 tok/s cold, 41.02 tok/s warm |
| qwen2.5-coder-14b-instruct-q5_k_m | `llama-cpp-gpu-1` (dense, single physical GPU)¹⁶ | 12.9 GiB | not exposed | baseline only | idle | 1,140.48 tok/s | 38.09 tok/s cold, 38.14 tok/s warm |
| qwen2.5-coder-14b-instruct-q5_k_m | `llama-cpp-all-gpus` (dense, forced dual-GPU tensor-split)¹⁶ | 6.8 GiB | 6.8 GiB | baseline only | idle | 761.79 tok/s | 62.99 tok/s cold, 63.41 tok/s warm |
| qwen2.5-coder-14b-instruct-q6_k | `llama-cpp-gpu-1` (dense, single physical GPU)¹⁶ | 14.3 GiB | not exposed | baseline only | idle | 1,182.33 tok/s | 33.06 tok/s cold, 33.07 tok/s warm |
| qwen2.5-coder-14b-instruct-q6_k | `llama-cpp-all-gpus` (dense, forced dual-GPU tensor-split)¹⁶ | 7.5 GiB | 7.5 GiB | baseline only | idle | 627.89 tok/s | 55.47 tok/s cold, 56.49 tok/s warm |
| Devstral-Small-2-24B-Instruct-2512-Q4_K_M | `llama-cpp-all-gpus` (dense, forced dual-GPU tensor-split)¹⁷ | 12.8 GiB | 12.9 GiB | baseline only | idle | 784.07 tok/s | 42.49 tok/s cold, 42.53 tok/s warm |
| Devstral-Small-2-24B-Instruct-2512-Q5_K_M | `llama-cpp-all-gpus` (dense, forced dual-GPU tensor-split)¹⁷ | 13.9 GiB | 14.0 GiB | baseline only | idle | 981.03 tok/s | 39.44 tok/s cold, 39.53 tok/s warm |
| Devstral-Small-2-24B-Instruct-2512-Q6_K | `llama-cpp-all-gpus` (dense, forced dual-GPU tensor-split)¹⁷ | 15.1 GiB | 15.1 GiB | baseline only | idle | 913.35 tok/s | 33.97 tok/s cold, 35.22 tok/s warm |
| Devstral-Small-2-24B-Instruct-2512-Q4_K_M | CPU-only (`llama-cpp-cpu`)¹⁸ | not exposed | not exposed | baseline only | **compute (8 threads)** | 15.998 tok/s | 2.76 tok/s cold, 2.76 tok/s warm |
| Devstral-Small-2505-Q4_K_M | `llama-cpp-all-gpus` (dense, forced dual-GPU tensor-split)¹⁷ | 12.8 GiB | 12.9 GiB | baseline only | idle | 1,040.28 tok/s | 47.02 tok/s cold, 47.06 tok/s warm |
| Devstral-Small-2505-Q5_K_M | `llama-cpp-all-gpus` (dense, forced dual-GPU tensor-split)¹⁷ | 13.9 GiB | 14.0 GiB | baseline only | idle | 1,020.88 tok/s | 43.14 tok/s cold, 43.30 tok/s warm |
| Devstral-Small-2505-Q6_K | `llama-cpp-all-gpus` (dense, forced dual-GPU tensor-split)¹⁷ | 15.1 GiB | 15.1 GiB | baseline only | idle | 950.21 tok/s | 37.26 tok/s cold, 38.13 tok/s warm |
| Devstral-Small-2505-Q4_K_M | CPU-only (`llama-cpp-cpu`)¹⁸ | not exposed | not exposed | baseline only | **compute (8 threads)** | 15.316 tok/s | 2.69 tok/s cold, 2.69 tok/s warm |
| DeepSeek-Coder-V2-Lite-Instruct-Q4_K_M | `llama-cpp-gpu-1` (MoE, single physical GPU, `ctx-size=32768`)¹⁹ | 14.3 GiB | not exposed | baseline only | idle | 168.44 tok/s | -- (load-confirmed only) |
| DeepSeek-Coder-V2-Lite-Instruct-Q4_K_M | `llama-cpp-all-gpus` (MoE, forced dual-GPU layer-split)¹⁹ | 10.6 GiB | 9.1 GiB | baseline only | idle | 170.51 tok/s | 51.20 tok/s cold, 52.35 tok/s warm |
| Qwen3-Coder-30B-A3B-Instruct-Q4_K_M | `llama-cpp-gpu-1` (MoE, `n-cpu-moe` offload)¹¹ | 12.3 GiB | not exposed | baseline only | idle | 115.57 tok/s | 59.74 tok/s cold, 60.17 tok/s warm |
| Qwen3-Coder-30B-A3B-Instruct-Q4_K_M | `llama-cpp-all-gpus` (MoE, full GPU-resident, dual-GPU)²⁵ | 13.4 GiB | 12.8 GiB | baseline only | idle | 84.69 tok/s | 139.09 tok/s cold, 139.63 tok/s warm |
| Qwen3.6-35B-A3B-Q4_K_M | `llama-cpp-gpu-1` (MoE, `n-cpu-moe` offload)¹¹ | 11.7 GiB | not exposed | baseline only | idle | 125.48 tok/s¹³ | 68.39 tok/s cold, 68.18 tok/s warm¹³ |
| Qwen3.6-35B-A3B-Q4_K_M | `llama-cpp-all-gpus` (MoE, full GPU-resident, dual-GPU)²⁵ | 12.0 GiB | 11.5 GiB | baseline only | idle | 78.67 tok/s | 122.55 tok/s cold, 123.44 tok/s warm |
| Qwen3.5-35B-A3B-Q4_K_M | `llama-cpp-gpu-1` (MoE, `n-cpu-moe` offload)¹¹ | 11.7 GiB | not exposed | baseline only | idle | 129.14 tok/s | 60.60 tok/s cold, 60.62 tok/s warm |
| Qwen3.5-35B-A3B-Q4_K_M | `llama-cpp-all-gpus` (MoE, full GPU-resident, dual-GPU)²⁵ | 12.3 GiB | 11.8 GiB | baseline only | idle | 71.10 tok/s | 101.96 tok/s cold, 102.30 tok/s warm |
| Ornith-1.5-35B-Q4_K_M | `llama-cpp-gpu-1` (MoE, `n-cpu-moe` offload)¹¹ | 11.2 GiB | not exposed | baseline only | idle | 92.14 tok/s | 65.11 tok/s cold, 66.52 tok/s warm |
| Ornith-1.5-35B-Q4_K_M | `llama-cpp-all-gpus` (MoE, full GPU-resident, dual-GPU)²⁵ | 12.4 GiB | 11.1 GiB | baseline only | idle | 105.04 tok/s | 122.96 tok/s cold, 123.21 tok/s warm |
| Ornith-1.5-35B-A3B | CPU-only (`llama-cpp-cpu`) | not exposed | not exposed | 22 GiB | **compute (8 threads)** | 82.26 tok/s | 16.09-16.22 tok/s |
| NVIDIA-Nemotron-3.5-Lightning-30B-A3B-Q4_0-Expert-Offload | `llama-cpp-gpu-1` (MoE, `n-cpu-moe` offload)²⁰ | 12.7 GiB | not exposed | baseline only | idle | 122.90 tok/s | 69.32 tok/s cold, 69.59 tok/s warm |
| Laguna-XS-2.1-Q4_K_M-Expert-Offload | `llama-cpp-gpu-1` (MoE, `n-cpu-moe` offload)²⁰ | 13.0 GiB | not exposed | baseline only | idle | 144.99 tok/s | 80.42 tok/s cold, 80.56 tok/s warm |
| Laguna-XS-2.1-Q4_K_M | `llama-cpp-all-gpus` (MoE, full GPU-resident, dual-GPU)²⁵ | 12.7 GiB | 12.0 GiB | baseline only | idle | 145.35 tok/s | 128.71 tok/s cold, 128.06 tok/s warm |
| North-Mini-Code-1.0-UD-Q4_K_M-Expert-Offload | `llama-cpp-gpu-1` (MoE, `n-cpu-moe` offload)²⁰ | 13.0 GiB | not exposed | baseline only | idle | 147.28 tok/s | 55.45 tok/s cold, 55.41 tok/s warm |
| North-Mini-Code-1.0-UD-Q4_K_M | `llama-cpp-all-gpus` (MoE, full GPU-resident, dual-GPU)²⁵ | 11.4 GiB | 11.2 GiB | baseline only | idle | 446.31 tok/s | 105.02 tok/s cold, 105.16 tok/s warm |
| granite-4.0-h-small-Q4_K_M-Expert-Offload | `llama-cpp-gpu-1` (MoE, `n-cpu-moe` offload)²⁰ | 13.3 GiB | not exposed | baseline only | idle | 92.40 tok/s | 27.16 tok/s cold, 27.49 tok/s warm |
| granite-4.0-h-small-Q4_K_M | `llama-cpp-all-gpus` (MoE, full GPU-resident, dual-GPU)²⁵ | 11.5 GiB | 11.0 GiB | baseline only | idle | 85.92 tok/s | 57.28 tok/s cold, 57.32 tok/s warm |
| NVIDIA-Nemotron-3.5-Lightning-30B-A3B-Q4_0 | `llama-cpp-all-gpus` (MoE, dual-GPU, MTP speculative decode)²¹ | 10.3 GiB | 13.3 GiB | baseline only | idle | 275.30 tok/s | 166.62 tok/s cold, 167.64 tok/s warm |
| GLM-4.7-Flash-Q4_K_M | `llama-cpp-all-gpus` (MoE, forced dual-GPU layer-split)²² | 12.8 GiB | 12.2 GiB | baseline only | idle | 279.26 tok/s | 103.98 tok/s cold, 104.16 tok/s warm |
| Qwen3.8-Flash-Next (tuned cfg) | 16GB schwerz, physical GPU 1²⁴ | 13.4 GiB¹ | not exposed | 4.8 GiB + 56 GiB mmap cache¹ | idle | 196.00 tok/s² | 12.67-18.38 tok/s⁵ |
| Qwen3.8-Flash-Next (tuned cfg) | 16GB schwerz, physical GPU 0²⁴ | 13.0 GiB | not exposed | baseline only | idle | -- | 6.34 tok/s cold, 6.60 tok/s warm |
| Qwen3-Coder-Next | 16GB schwerz | 7.5 GiB | not exposed | 49 GiB + 52 GiB mmap cache³ | idle | 58.72 tok/s | 31.12-31.29 tok/s |
| Qwen3-Coder-Next | 32GB schwerz (grouped-multigpu) | 2.7 GiB | 2.8 GiB | 48 GiB (partial swap) | some (swap I/O) | 19.87 tok/s | 7.43-7.44 tok/s |
| Qwen3-Coder-Next | CPU-only (`llama-cpp-cpu`) | not exposed | not exposed | 37 GiB | **compute (8 threads)** | 11.18 tok/s | 9.17-13.33 tok/s |
| Qwen3-Next-80B-A3B-Instruct | 16GB schwerz | 7.5 GiB | not exposed | 49 GiB + 55 GiB mmap cache³ | idle | 62.98 tok/s | 31.81-32.00 tok/s |
| Qwen3-Next-80B-A3B-Instruct | CPU-only (`llama-cpp-cpu`) | not exposed | not exposed | 37 GiB | **compute (8 threads)** | 9.23 tok/s | 9.98-13.24 tok/s |
| gpt-oss-120b | 16GB schwerz | 7.1 GiB | not exposed | 4.0 GiB + 54 GiB mmap cache | idle | 11.06 tok/s | 8.11-8.80 tok/s |
| gpt-oss-120b | 32GB schwerz (grouped-multigpu) | 3.8 GiB | 4.0 GiB | 60/60 GiB (swap-maxed) | some (swap I/O) | 2.20 tok/s⁴ | 2.36-3.01 tok/s⁴ |
| Llama-4-Scout-17B-16E | 16GB schwerz | **CUDA OOM** | not exposed | -- | -- | failed to load | failed to load |
| GLM-4.5-Air | 16GB schwerz | **CUDA OOM** | not exposed | -- | -- | failed to load | failed to load |
| GLM-4.5-Air | 32GB schwerz (grouped-multigpu) | 10.1 GiB | 10.1 GiB | 60/60 GiB (swap-maxed) | some (swap I/O), 0% GPU compute | 1.68 tok/s⁴ | 1.01-1.39 tok/s⁴ |
| gemma-3n-E2B-it | CPU-only (`llama-cpp-cpu`)¹⁰ | not exposed | not exposed | 5.1 GiB | **compute (8 threads)** | 145.26 tok/s | 21.72-21.85 tok/s |
| gemma-3n-E4B-it | CPU-only (`llama-cpp-cpu`)¹⁰ | not exposed | not exposed | 6.0 GiB | **compute (8 threads)** | 77.51 tok/s | 12.72-12.73 tok/s |
| NVIDIA-Nemotron-3-Nano-4B | CPU-only (`llama-cpp-cpu`)¹⁰ | not exposed | not exposed | 4.5-4.8 GiB | **compute (8 threads)** | 55.47 tok/s | 12.67-12.71 tok/s |
| Qwen3.5-9B | CPU-only (`llama-cpp-cpu`)¹⁰ | not exposed | not exposed | 7.0-7.1 GiB | **compute (8 threads)** | 42.23 tok/s | 7.29-7.30 tok/s |
| Ornith-1.5-9B | CPU-only (`llama-cpp-cpu`)¹⁰ | not exposed | not exposed | 7.4-7.5 GiB | **compute (8 threads)** | 45.29 tok/s | 7.36-7.35 tok/s |

¹ From this session's six-model 16GB run (same deployed config as the tuned
benchmark, different prompt) -- see footnote 2.
² Prefill/decode figures here are from the dedicated tuning pass's large
(~43K-token) benchmark prompt, not the small five-topic prompt used
elsewhere in this table; small-request prefill is not comparable (a
131-token prompt against this same config measured only 10.35-16.07 tok/s
prefill -- see the Flash Next section below). VRAM figure (¹) is from a
different, later run of the identical deployed config, reused because
nothing about the model/config differs between the two observations.
³ `buff/cache` is host-wide and cumulative across whatever else has touched
the page cache this session (including other models tested earlier) -- not
cleanly attributable to this row alone, included for completeness rather
than as a precise per-model figure.
⁴ Not a real measurement of the model or the grouped-multigpu cache --
disk-swap-thrashing artifact, see "32GB schwerz service ... failed batch"
below for the full explanation.
⁵ Not a range from run-to-run noise -- these are decode speed at two
different KV-cache depths, and the direction is exactly what's expected:
12.67 tok/s is decode after the tuning pass's ~43,252-token prompt (decode
attends over the whole resident context, so a deeper cache costs more per
generated token); 18.38 tok/s (14.61 cold) is decode after only ~130-260
tokens, from this session's six-model run. Both are real; neither is "the"
number without saying which context depth it's at.
⁶ 2026-09-17: added a real small-prompt (119-token) benchmark for Q6_K_M,
matching the Q4_K_M treatment -- cold prefill 184.80 tok/s, decode
30.16 tok/s; warm decode 31.05 tok/s. Notably faster prefill than Q4_K_M's
56.78 tok/s despite being the larger quant -- not yet explained, worth
comparing against the 43K-token stress test once run (see below) rather
than assumed to be quant-size-inversely-correlated from one data point.
Cold run showed a striking asymmetry worth flagging: GPU 1 sat at 0% util
while GPU 0 ran the 119-token prefill at 98% -- by the warm run both cards
were at 97-98%. **Resolved, 2026-09-18, repeat run**: a clean repeat
(256-token five-topic prompt, cold/warm 31.07/31.12 tok/s decode -- in
line with this footnote's original 30.16-31.05 tok/s) showed both cards
at 98% utilization on *both* the cold and warm run, no asymmetry at all.
Confirms the original snapshot was a small-prompt timing artifact (the
prefill likely finished on one card before the `nvidia-smi` snapshot
caught the other doing its share), not a real placement problem. The
session-derived step-duration figure previously
here (model-only step median 24.6s->18.0s, mean 91.5s->45.1s,
`split-mode=tensor` before/after) is still the only *real-session* data
point and remains in the "`llama-cpp-all-gpus` service" section below -- it
also confounds `reasoning-effort=low` going live in the same window, so
it's a different kind of evidence from the clean benchmark figures here,
not a contradiction of them.
⁷ Re-run 2026-09-17 to replace the dated/accidental 2026-09-14 test (see the
"`llama-cpp-all-gpus` service" section below) with a properly current figure --
cold prefill 68.13 tok/s, decode 39.11 tok/s, warm decode 40.62 tok/s. Closely
corroborates the 09-14 numbers (56.78 prefill, 40.50-40.66 decode) rather
than contradicting them: same VRAM footprint (10555/10640 MiB, 97-98% both
cards), decode essentially identical, prefill within normal run-to-run
variance. Nothing material changed for this quant's dense dual-GPU
performance between the two dates. Table figures above are the 09-17
re-run; the original 09-14 numbers are kept in the detailed section below
as corroborating evidence, not superseded/wrong. Reconfirmed again
2026-09-18, after the service refactor's NCCL break was fixed
(`NCCL_CUMEM_ENABLE=0` -- see "Real incident: split-mode=tensor broken by
the service refactor, fixed" below) and now running via llama.cpp's own
non-NCCL AllReduce fallback path rather than real NCCL, with a real
256-token cold/warm benchmark: 39.89-40.51 tok/s cold, 39.96 tok/s warm,
10,655+10,740 MiB combined VRAM. Consistent with the figures above to
within normal run-to-run variance -- not given its own table row, since
the difference between the two reduce mechanisms is marginal to
nonexistent for this workload; forced dual-GPU tensor-split is just how
this deployment runs these models now, regardless of which AllReduce path
NCCL ends up taking underneath.
⁸ Single physical GPU (`llama-cpp-gpu-1`, one card exposed to the
container by Docker's own `gpus.device_ids`), from the same 2026-09-18
clean 256-token cold/warm benchmark as the dual-GPU forced-tensor-split
rows below. See "Qwen3.8-27B, single GPU, real 3-bit quants" below for how
these ctx-size values (98304/65536 respectively) were reached.
⁹ Each of these three models fits solo on one 16 GiB card already;
`split-mode=tensor` was forced explicitly anyway because dense/GPU-resident
decode at batch=1 is memory-bandwidth-bound, and splitting doubles
effective VRAM bandwidth even when capacity isn't the constraint -- see
"Both 3-bit quants forced onto dual-GPU tensor-split despite fitting on
one card" below for the full reasoning and the single-GPU-vs-dual-GPU
comparison. 2026-09-18 clean 256-token cold/warm benchmark, user-run.
¹⁰ First real cold/warm figures for these five small models, user-run,
same 256-token five-topic prompt as every other row in this table.
`nvidia-smi` confirmed 0% utilization and no model process on either GPU
for all five (genuinely CPU-only, matching this service's architectural
`llama-cpp-cpu` -- has no `gpus:` passthrough). Host swap held flat at
3.6/8 GiB across all ten requests (cold+warm x5) -- pre-existing from
something else running earlier in the session, not caused by or growing
during any of these runs, unlike the real near-misses recorded elsewhere
in this document. RAM ranges shown are cold->warm; decode speed here
tracks parameter count reasonably closely (gemma-3n-E2B-it, the smallest,
fastest at 21.72-21.85 tok/s; the two 9B models, Qwen3.5-9B and
Ornith-1.5-9B, slowest at 7.29-7.36 tok/s), unlike the MoE-vs-dense
comparison recorded under "Practical implications" below, where a larger
MoE model outdecoded smaller dense ones -- these five are a same-family
(dense) size comparison, not a MoE one, so a roughly monotonic
size-to-speed relationship here isn't a contradiction of that finding.
¹¹ 2026-09-18, real 256-token cold/warm five-topic benchmark on
`llama-cpp-gpu-1`, user-run -- first proper benchmark figures for
qwen2.5-coder-7b/14b (previously smoke-tested only, no decode figure on
record) and the four `n-cpu-moe`-offloaded 30-35B MoE models (previously
load+request-confirmed in the "real-request audit" pass, also no decode
figure on record). GPU column is total card usage from `nvidia-smi`
(process + ~13-98 MiB compositor baseline), not process-only.
¹² 2026-09-18, later the same day: moved from `llama-cpp-16gb`
(`llama-cpp-gpu-1`) to `llama-cpp-all-gpus`, `split-mode=tensor`,
`ctx-size=131072`. See "Real incident: Devstral-Small ctx-size failure,
fixed" below for why -- single-GPU testing found `ctx-size=32768` fails a
real CUDA OOM and the working fallback (16384) was judged too small to
be useful, making this a real dual-GPU model on this hardware despite
fitting on one card by weight size alone. Both quants confirmed working
at 131072 by a real load + request: near-equal weight split across both
cards (12.8-12.9 GiB each, ~3.1-3.2 GiB real headroom per card), the
prefill figures shown are from that same real request. Decode figures
are marked load-confirmed only, not a benchmark number -- this was a
short smoke test (load + a handful of tokens), not the standard 256-token
five-topic benchmark used elsewhere in this table. A proper cold/warm
benchmark run is still pending.
¹³ **Resolved, 2026-09-18, repeat run**: the original run showed cold
prefill 12.69 tok/s and a 41.60->67.24 tok/s cold-to-warm decode jump, far
outside every other `n-cpu-moe` model's range, with ~20 s of apparent
pure model-load time before any compute started. A clean repeat run
(figures now in the table above) landed squarely in line with its three
peers: 125.48 tok/s prefill, 68.39/68.18 tok/s cold/warm decode -- no
unusual cold-to-warm gap at all. Confirms the original run was a one-off
slow load, not a real property of this model. The original figures are
kept here for the record: cold prefill 12.69 tok/s, cold decode 41.60
tok/s, warm decode 67.24 tok/s, `time to first text` 27.10 s despite
prefill compute itself only taking 7.01 s of that.
¹⁴ 2026-09-18, real test on the *current* single-GPU architecture
(`llama-cpp-gpu-1`) -- fills a gap the earlier "standalone, 1 GPU pinned"
row couldn't, since that predates this deployment's per-GPU-locked
refactor. 14.1 GiB used, real headroom (~2.2 GiB) on the 16,311 MiB card.
¹⁵ 2026-09-18, new model (Qwen3.6-generation dense 27B). Confirmed working
at the projected `ctx-size=163840`: 14,299/14,384 MiB, ~2.0/1.9 GiB real
headroom per card -- within ~50 MiB of this document's own pre-download
projection (~28.08 GiB combined, ~3.8 GiB headroom; actual 28,683 MiB
combined, ~3.85 GiB headroom). `split-mode=tensor` confirmed working for
this architecture.
¹⁶ 2026-09-18, higher quants of the two Qwen2.5-Coder models, both
single-GPU and forced dual-GPU tensor-split. Real, direct confirmation of
the same bandwidth-doubling effect already established for other dense
models: `q8_0` (7b) 52.91->90.27 tok/s (~1.71x), `q5_k_m` (14b)
38.09->62.99 tok/s (~1.65x), `q6_k` (14b) 33.06->55.47 tok/s (~1.68x) --
closely consistent multipliers across three different quants/sizes of the
same architecture family.
¹⁷ 2026-09-18, real cold/warm benchmark for all six Devstral dual-GPU
entries (both quants existing and new). Real, notable: `Devstral-Small-
2505` decodes faster than `Devstral-Small-2-24B-Instruct-2512` at every
matching quant level (Q4_K_M: 47.0 vs 42.5 tok/s; Q5_K_M: 43.1 vs 39.4
tok/s; Q6_K: 37.3-38.1 vs 34.0-35.2 tok/s) despite identical file sizes
and VRAM footprints -- a real difference between the two Devstral
releases, architecture/weights, not a measurement artifact (both tested
back-to-back, same service, same context). `Q6_K` cold runs show VRAM
right at the projected ceiling (894-1,006 MiB headroom per card, matching
the ~1.5 GiB combined projection) -- the tightest fit of anything
successfully tested in this document.
¹⁸ 2026-09-18, real CPU-only benchmark -- dramatically slower than
predicted. This document's own prediction (before testing) was "the same
ballpark as gpt-oss-20b-F16's CPU figure (10.42-10.43 tok/s) adjusted for
size" -- the real figure, 2.69-2.76 tok/s, is roughly 3.8x slower than
that prediction, not just a smaller adjustment. Root cause is architectural,
not a bug: gpt-oss-20b-F16 is MoE (sparse activation lets CPU inference
skip most experts most tokens); Devstral is dense, so every one of its
~24B parameters must be read from RAM on every token, with no sparsity to
exploit. Real end-to-end times reflect this: cold requests took 152-200 s
end-to-end (vs. single-digit seconds for every GPU-resident entry in this
table). **Practical conclusion: CPU is not a viable path for dense
20B+-class models on this host**, unlike the genuinely-useful MoE CPU
entries elsewhere in this table -- despite fitting comfortably in RAM,
throughput this low rules out agentic use.
¹⁹ **Diagnosed and fixed, 2026-09-18, later the same day.** The original
failure was real, but the two hypotheses recorded here at the time were
both wrong -- a live reproduction with real container logs found the
actual cause: `ctx-size=65536`'s KV buffer request (9,180 MiB / 8.97 GiB,
confirmed in the logs) plus the 9.65 GiB weight file exceeds one 16,311
MiB card outright (18.62 GiB combined). Not a `deepseek2`/single-device
architecture problem, not a `split-mode` gap -- a plain, untested
capacity shortfall, the same class of gap this document has hit many
times before. Backed off to `ctx-size=32768`; confirmed working (real
load + request, 14.3 GiB used, 168.44 tok/s prefill). This also
undermines the framing below it originally carried -- see "Real incident:
`parameterise-llama` refactor investigation" for the full corrected story
and what it means for the layer-split MoE-bandwidth question.
²⁰ 2026-09-18, first real load tests for all four new `n-cpu-moe`
expert-offload entries -- all four load and answer correctly, confirming
the computed `n-cpu-moe` values (19/16/18/15 respectively) were right on
the first attempt, unlike the *existing* four-model cluster's real
first-guess failure. `granite-4.0-h-small`'s real decode (27.16-27.49
tok/s) is noticeably the slowest of the eight `n-cpu-moe` models tested
in this document (next-slowest is 38-41 tok/s) -- consistent with the
prediction that its 9B active-parameter count (vs. ~3B for every other
model in this cluster) would mean proportionally heavier CPU-offloaded
expert compute per token. A real, confirmed architectural cost, not
noise.
²¹ 2026-09-18, first standardized cold/warm benchmark for this model on
`llama-cpp-all-gpus` (previously only real DSH session data existed:
42.2-101.2 tok/s across three agentic sessions). The standardized
256-token five-topic benchmark shows *much* higher throughput
(166.62-167.64 tok/s) than the real agentic sessions did -- both are
real, valid measurements of different things, not a contradiction: the
DSH sessions ran with far deeper context and real tool-call overhead
between generations, while this benchmark is a single short-context
request. Uneven VRAM split (10.3/13.3 GiB) confirms this model does not
use `split-mode=tensor` (no `split-mode` set in its preset entry,
consistent with its MTP speculative-decode sidecar's own placement needs).
²² 2026-09-18, first standardized cold/warm benchmark for this model
(previously only load+request confirmed, with real headroom noted but no
throughput figure). 103.98-104.16 tok/s, a real, solid number -- among
the faster MoE entries in this table, consistent with `deepseek2`'s
layer-split placement still giving good throughput despite not
benefiting from tensor-split's bandwidth-doubling.
²³ **Diagnosed and fixed, 2026-09-18, later the same day.** Real root
cause, confirmed via live reproduction with container logs: a genuine bug
in the new `render-compose.py` refactor's `upstream_command()`, which
unconditionally passed a router-level `--n-gpu-layers all` for every
GPU-enabled profile -- silently overriding both models' preset-level
`n-gpu-layers = auto` (the partial-CPU-offload setting they depend on to
fit at all). Real log line: `"failed to fit params to free device
memory: n_gpu_layers already set by user to -2, abort"`, then an
immediate `cudaMalloc` OOM trying to force the entire model onto one
GPU -- not a RAM issue, not proof the models don't fit, just the router
taking away the one setting that would have made them fit. Fixed by
removing the unconditional flag (GPU profiles now pass no system-level
`--n-gpu-layers`, letting each model's own preset value, or
`llama-server`'s own `auto` default, apply). Confirmed working with real
requests and live RAM monitoring (swap flat at ~3.1 GiB throughout, no
growth): both models load and answer correctly, 4.78/4.57 tok/s decode --
the GPU/RAM columns to the left show "partial (auto)"/"some" because
that's what a correctly-working partial-offload placement actually looks
like, not a placeholder. See "Real incident: `parameterise-llama`
refactor investigation" below for the full trace, including why 23 other
entries were unaffected by the same bug.
²⁴ 2026-09-18, real, direct A/B confirmation that physical GPU 0 and
GPU 1 are not symmetric on this host -- GPU 0: PCIe Gen3 max, 4 lanes
negotiated; GPU 1: PCIe Gen4 max, 8 lanes. `moe-expert-cache-size`'s
constant host-to-GPU expert streaming is directly PCIe-bandwidth-bound,
so this hits Flash Next especially hard. Identical image, config, model,
and request on both cards -- the only variable is which physical GPU.
See "Real incident: `parameterise-llama` refactor investigation" below
for the full topology data and why this isn't a software problem.
²⁵ 2026-09-19, real 256-token cold/warm benchmark (same prompt shape as
every other row in this table), `llama-cpp-all-gpus`, no `n-cpu-moe` (full
GPU residency, both cards, no `split-mode` forced -- matching
`NVIDIA-Nemotron-3.5-Lightning-30B-A3B-Q4_0`'s already-working entry
rather than assuming tensor-split support). Closes "outstanding MoE
performance questions" item 14 below, for all seven `n-cpu-moe`-offloaded
30-35B models in the fleet, not just the one (Ornith) it was originally
raised for. Real speedup range: 1.6x (Laguna-XS-2.1, smallest gain) to
2.3x (Qwen3-Coder-30B-A3B-Instruct, largest gain) over the single-GPU
`n-cpu-moe`-offloaded figure for the same model/quant/context. All seven
fit with real headroom (11.0-13.4 GiB per card of 16.3 GiB). Three of the
seven needed a new model ID distinct from their `llama-cpp-16gb`
`-Expert-Offload` sibling (`Laguna-XS-2.1-Q4_K_M`, `North-Mini-Code-1.0-
UD-Q4_K_M`, `granite-4.0-h-small-Q4_K_M`), since `n-cpu-moe` isn't set
here and the suffix would misdescribe the config; the other four
(`Qwen3-Coder-30B-A3B-Instruct-Q4_K_M`, `Qwen3.6-35B-A3B-Q4_K_M`,
`Qwen3.5-35B-A3B-Q4_K_M`, `Ornith-1.5-35B-Q4_K_M`) reuse their existing
ID, matching the convention already used for the qwen2.5-coder pairs
above (same ID, different service, config differs by placement).

## Rejected models

Models removed entirely from the deployment -- weight files deleted from
disk, not just unlisted from a preset. Kept here as a record of what was
tried and why it didn't earn a place, not as an active comparison target.

| Model | Service tried | Decode | Reason rejected |
|---|---|---|---|
| Llama-3.3-70B-Instruct-Q3_K_M | `llama-cpp-all-gpus`, `n-gpu-layers=auto` partial offload | 4.78 tok/s (small ctx, load-confirmed only) -> 2.09-2.75 tok/s (ctx-size 65536-131072)²⁶ | Structurally bottlenecked on this hardware: doesn't fit 32 GiB combined VRAM with real margin at any useful context, so every token touches host RAM/PCIe transfer. An order of magnitude slower than the fleet's MoE models of similar or larger total size (Qwen3.6-35B-A3B, Ornith-1.5-35B, etc.), which only activate a few billion parameters per token. Removed 2026-09-19, ~32 GiB freed. |
| Qwen2.5-72B-Instruct-Q3_K_S | `llama-cpp-all-gpus`, `n-gpu-layers=auto` partial offload | 4.57 tok/s (small ctx, load-confirmed only) -> 2.14-2.57 tok/s (ctx-size 65536-131072)²⁶ | Same as above -- same partial-offload bottleneck, same order-of-magnitude gap to the fleet's MoE models. Removed 2026-09-19, ~32 GiB freed. |

²⁶ The two figures per model are real measurements from two different
sessions, not a range or noise: 4.78/4.57 tok/s was the original
load-confirmed-only smoke test right after the `render-compose.py`
`n-gpu-layers` bug was fixed (see footnote 23 above), at whatever smaller
`ctx-size` was configured then; 2.09-2.75/2.14-2.57 tok/s are real
256-token-request-equivalent decode figures from the 2026-09-19 session
that raised both models to `ctx-size=65536` then `131072` before removing
them -- decode drops as KV-cache depth grows, so the lower figures at
higher context are expected, not a regression. Both data points are real;
neither supersedes the other, they're at different context depths.

## GPU-resident, single card, no host offload

| Model | Setup | Prefill | Decode |
|---|---|---|---|
| gpt-oss-20b-F16 | standalone container, idle GPU, fully resident, no MoE offload | 3,802.08 tok/s | 63.76 tok/s |

Baseline for "what this hardware does with nothing offloaded to host." Every
other number in this document is slower because it's carrying MoE-cache
overhead, genuine memory pressure, or both. Real request against
`gpt-oss-20b-F16`, non-reasoning-effort request, prompt built from concatenated
session logs (~40K tokens) matching the corpus used for the 16GB tuning work
below.

## 16GB schwerz service (single GPU, host-offloaded experts, `qwen4exp-mtp` pin)

Real, deliberate tuning pass -- one variable changed per run, each verified
with an actual model load and a large (~43K-token) real prompt built from
session logs, not a synthetic one-liner (small-request probes were shown not
to predict large-request VRAM/throughput: a `ubatch-size=1536` config passed a
5-token probe and then crashed with a genuine CUDA OOM on the real prompt).

| Model | Config | Prefill | Decode |
|---|---|---|---|
| Flash Next (UD-Q3_K_XL) | baseline: batch=512, ubatch=256, cache=32 | 87.03 tok/s | 11.66 tok/s |
| Flash Next (UD-Q3_K_XL) | interim: cache=64 (more VRAM, less headroom) | -- | +14% vs baseline |
| Flash Next (UD-Q3_K_XL) | **deployed: batch=2048, ubatch=1024, cache=48** | **196.00 tok/s (+125%)** | **12.67 tok/s (+9%)** |

`batch-size` alone was originally (wrongly) credited as "the single biggest
lever" for prefill; isolating it later showed batch=512 and batch=2048 were
statistically indistinguishable at the same cache size (87.03 vs 85.89-90.37
tok/s) -- `ubatch-size` was the real lever (+121.7% prefill from ubatch=1024
alone). Recorded here as a methodology note: an earlier recommendation in this
same tuning pass was corrected once actually isolated.

Reasoning-effort fix, applied here and to every other reasoning-capable model
in this deployment: this model's own chat template defaults to `xhigh`
whenever a request omits `reasoning_effort`; DSH was never sending the field
for this provider, so every session before the fix silently ran at `xhigh`.
`reasoning: true` + `thinkingLevelMap` in `settings.yaml` fixed it --
confirmed via direct curl A/B, ~60% reduction in reasoning length on a
debugging-style prompt.

`gpt-oss-120b`, `GLM-4.5-Air` and `Llama-4-Scout` are now also catalogued
here (after a real bug: all three were initially added inheriting this
service's `load-mode = none` default, which is fine for models that fit in
RAM but caused the exact swap-thrashing failure recorded below for the 32GB
service once discovered; all three were corrected to `load-mode = mmap` +
`lazy-mode = on`, matching Flash Next's own pattern -- see "What actually
causes the RAM ceiling" below).

2026-09-17, full six-model run (three new downloads + Flash
Next/Coder-Next/Next-80B-Instruct), same prompt/methodology as the CPU round
below (real ~150-token five-topic prompt, cold+warm pairs, `free -h` /
`swapon --show` / `nvidia-smi` after each):

| Model | Run | Prefill | Decode | RAM used | buff/cache | Swap |
|---|---|---|---|---|---|---|
| Qwen3-Coder-Next-Q4_K_M | cold | 58.72 tok/s | 31.12 tok/s | 49 GiB | 52 GiB | 4.3 GiB |
| Qwen3-Coder-Next-Q4_K_M | warm | -- | 31.29 tok/s | 49 GiB | 52 GiB | 4.3 GiB |
| Qwen3-Next-80B-A3B-Instruct | cold | 62.98 tok/s | 31.81 tok/s | 49 GiB | 55 GiB | 4.2 GiB |
| Qwen3-Next-80B-A3B-Instruct | warm | -- | 32.00 tok/s | 49 GiB | 55 GiB | 4.2 GiB |
| gpt-oss-120b-Q4_K_M | cold | 11.06 tok/s | 8.11 tok/s | **4.0 GiB** | 54 GiB | 4.9 GiB |
| gpt-oss-120b-Q4_K_M | warm | -- | 8.80 tok/s | 4.0 GiB | 54 GiB | 4.9 GiB |
| Qwen3.8-Flash-Next-UD-Q3_K_XL | cold | 10.35 tok/s* | 14.61 tok/s | 4.8 GiB | 56 GiB | 4.7 GiB |
| Qwen3.8-Flash-Next-UD-Q3_K_XL | warm | -- | 18.38 tok/s | 4.8 GiB | 56 GiB | 4.7 GiB |
| Llama-4-Scout-17B-16E-Instruct | -- | **failed to load** | -- | -- | -- | -- |
| GLM-4.5-Air-UD-Q4_K_XL | -- | **failed to load** | -- | -- | -- | -- |

\*Flash Next's prefill here is far below the 196 tok/s from the dedicated
tuning pass above -- expected, not a regression: this run used a 131-token
prompt, and this project's own established lesson (from that same tuning
pass) is that small-request probes don't predict large-request throughput.
Not a comparable number to the tuned figure.

The mmap fix is now confirmed working, not just sanity-checked: gpt-oss-120b
used only 4.0 GiB RAM with 54 GiB in reclaimable `buff/cache`, nothing like
the 32GB service's full-swap failure for the same model. Coder-Next and
Next-80B-Instruct are also a clean, direct GPU-vs-CPU comparison against the
CPU-only figures below for the identical two models: ~31 tok/s decode here
vs. 9-13 tok/s CPU-only -- a real ~2.4-3.4x GPU speedup for models that fit
either way.

**Two genuine failures, root-caused from the container logs, not the RAM
issue above**: both `Llama-4-Scout` and `GLM-4.5-Air` hit
`CUDA error: out of memory` **on GPU 0** --

```
moe-cache: cudaMalloc(70778880 bytes) failed: out of memory      (Llama-4-Scout, allocating cache slots)
moe-cache: cudaMalloc(51904512 bytes) failed: out of memory      (GLM-4.5-Air, during first decode's graph compute)
```

This service exposes only physical GPU 0, and both models use
`n-gpu-layers = all` / `fit = off` -- the same pattern Coder-Next and
gpt-oss-120b use successfully. For these two specifically (Llama-4-Scout has
`hidden_size=5120`, wider than anything else in this catalogue), forcing the
entire dense/attention core plus a 65536-token KV cache onto one 16 GiB card
leaves no room for even a handful of cache slots. Not yet fixed -- candidates
are lowering `ctx-size` for just these two entries, or switching them from
`fit=off` to `fit=on` so llama.cpp auto-reduces GPU layer count instead of
all-or-nothing.

## `llama-cpp-all-gpus` service (dense, both GPUs via `split-mode=tensor`)

| Model | Metric | Before tensor-split | After tensor-split |
|---|---|---|---|
| Qwen3.8-27B-UD-Q6_K_M | real-session model-only step, median | 24.6s | 18.0s |
| Qwen3.8-27B-UD-Q6_K_M | real-session model-only step, mean | 91.5s | 45.1s |

A direct benchmark-style figure exists for the Q4_K_M variant (not Q6_K_M
above), now measured twice:

| Date | Prefill (cold) | Decode (cold) | Decode (warm) | GPU 1 | GPU 2 |
|---|---|---|---|---|---|
| 2026-09-14 | 56.78 tok/s | 40.50 tok/s | 40.66 tok/s | 10.6 GiB, 98% | 10.6 GiB, 97% |
| 2026-09-17 | 68.13 tok/s | 39.11 tok/s | 40.62 tok/s | 10.6 GiB, 97-98% | 10.6 GiB, 97% |

The 09-14 run was, by the user's own account, an accident -- they intended
to test Q6_K_M and ran Q4_K_M instead, run directly against the API rather
than through DSH, and caught only because the `nvidia-smi` banner's
timestamp didn't match this session's timeline. Rather than discard it, it
was re-run properly on the 17th to check whether anything had changed in
between -- it hadn't: both dates agree closely (decode essentially
identical, prefill within normal run-to-run variance, identical VRAM
footprint), so the accidental run is kept as corroborating evidence, not
superseded. Both confirm real dual-GPU compute engagement (97-98% util both
cards), not just balanced memory placement, and confirm `split-mode=tensor`
was already active in the deployed config by the 14th -- separate from
when a DSH session first exercised it (the 16th; those are different
claims). Small prompt (20 tokens) in both runs -- a genuine
prefill-throughput figure for this quant would still need the same
large-prompt treatment the 16GB service's Flash Next tuning got.

Not a benchmark-harness number -- derived from `session_analysis.py` against
two real completed DSH sessions (before/after the config change), so it's
real-world confirmed but confounds two simultaneous changes:
`split-mode=tensor` going live and `reasoning-effort=low` being confirmed
active for the same model in the same window. The two contributions were not
separated.

`reasoning-effort=low` was independently verified by direct request, not just
inferred from session behaviour: a request with no `reasoning_effort` field
produced byte-identical output (2338 reasoning chars / 938 text chars,
temperature=0) to an explicit `"low"`; explicit `"high"` on the same loaded
model produced a visibly longer response. Confirms the setting is genuinely
applied, not silently overridden by the model's own template default.

`split-mode=tensor` was confirmed active (not just configured) via the
spawned process's own args (`"--split-mode", "tensor"` present) and via
near-equal VRAM split across both cards when loaded.

## 32GB schwerz service (two GPUs, `codex/moe-grouped-multigpu` pin) -- failed batch, root-caused

| Model | Run | Prefill | Decode | RAM / swap |
|---|---|---|---|---|
| gpt-oss-120b | cold | 2.20 tok/s | 2.36 tok/s | 60/60 GiB RAM, 8/8 GiB swap (maxed) |
| gpt-oss-120b | warm (cached prompt) | 1.87 tok/s* | 3.01 tok/s | maxed |
| GLM-4.5-Air | cold | 1.68 tok/s | 1.01 tok/s | maxed; **0% GPU util, both cards** |
| GLM-4.5-Air | warm | 0.70 tok/s* | 1.39 tok/s | maxed |
| Qwen3-Coder-Next | cold | 19.87 tok/s | 7.43 tok/s | 48/60 GiB RAM, 5.1/8 GiB swap (partial) |
| Qwen3-Coder-Next | warm | 5.67 tok/s* | 7.44 tok/s | partial |

\*"warm" prefill figures are a 1-token cached-prompt continuation, not a real
prefill measurement -- included for completeness, not to be read as prefill
throughput.

**These are not real performance numbers for the models or for the
grouped-multigpu cache mechanism.** They are swap-thrashing artifacts.

### What actually causes the RAM ceiling

`codex/moe-grouped-multigpu` requires `load-mode = none` -- its own doc
(`docs/moe-grouped-multigpu.md` in that source tree) states mmap-based
pinning is rejected before inference ("read-only auxiliary registration is
unsupported"). `load-mode = mmap` is what let Flash Next's 84 GiB file run in
~53.5 GiB of *actual* RAM on the 16GB service (lazy page-fault + reclaimable
page cache, not full eager residency). Remove mmap and a model that exceeds
physical RAM has no fallback but swap.

**Correction, 2026-09-18: `load-mode`/`lazy-mode` are stock llama.cpp
flags, not a schwerz-fork-exclusive feature.** Verified directly against
`llama-server --help` on the same plain build `llama-cpp-16gb`/`32gb`/`cpu`
run: `--load-mode` defaults to `auto` (mmap, unless a device doesn't
support it) and `--lazy-mode` defaults to `auto` (on, for tensors larger
than 4 GiB) -- i.e. the plain services already get mmap+lazy loading by
default, with no special config needed. What's genuinely schwerz-specific
is its separate `moe-cache` expert-caching subsystem layered on top of
this shared mechanism, and `codex/moe-grouped-multigpu`'s own requirement
to *disable* mmap (`load-mode=none`) for its grouped cross-GPU dispatch to
work at all -- that's the real, fork-specific cause of the RAM ceiling
below, not an absence of mmap capability elsewhere in this deployment.
This matters for `## Currently untested / no data exists` below: Flash
Next's exclusion from the 32GB catalogue was reasoned as "mmap is
fundamental to its viability and this branch forbids it" -- true for the
*schwerz* 32GB (`codex/moe-grouped-multigpu`) branch specifically, not
necessarily for the plain `llama-cpp-all-gpus` service, which was never
actually tested against this model.

gpt-oss-120b (58.44 GiB real binary size -- corrected 2026-09-18 from an
earlier "62.8 GiB" figure that was actually decimal GB mislabeled as
GiB, found while checking real GGUF metadata: 36 layers, 128 experts/4
active) and GLM-4.5-Air (63.07 GiB real binary size, corrected from
"67.7 GiB" the same way; 47 layers, 128 experts/8 active) both exceed or
nearly exceed this host's 60 GiB RAM on file size alone, before KV cache
or the cache mechanism's own bookkeeping. Under `load-mode=none` there was never
a scenario where either fits -- the 2-3 tok/s figures above are disk-swap
I/O speed, not model or cache speed. Qwen3-Coder-Next (46 GiB) partially
avoided full catastrophe because it's small enough to mostly fit even
without mmap's elasticity, and its numbers are the least broken of the
three -- but it was still touching swap and its GPU utilization was
asymmetric between two otherwise-identical cards (59% vs 12%), which is
itself unexplained (see "Still open" below).

**Fix applied**: Flash Next is deliberately excluded from the *schwerz*
32GB catalogue's model list entirely (mmap is fundamental to its
viability and that specific branch forbids it; even if it somehow fit,
that branch's benefit is decode-only and Flash Next's dominant cost has
always been prefill). The two other oversized models were moved to the
16GB schwerz service instead, where mmap is available, with
`load-mode=mmap`/`lazy-mode=on` added per-model. Whether Flash Next, and
whether gpt-oss-120b/GLM-4.5-Air via plain `--n-cpu-moe` rather than
schwerz's `moe-cache`, would fare differently on the plain, mmap-capable
`llama-cpp-32gb`/`llama-cpp-16gb` services is a real, currently open
question -- see the test plan below.

### Deployment bugs found and fixed along the way (not performance findings, but real, and cost real time)

- Splitting the shared `models-preset.ini` into `models-preset-16gb.ini` /
  `models-preset-32gb.ini` updated the repo templates and `docker-compose.yml`
  but the new files were never actually deployed to their runtime paths (the
  `install -D` step was skipped). Docker's bind-mount-of-a-nonexistent-file
  behaviour silently created an empty directory at each path instead of
  erroring, and llama.cpp's router failed with `basic_filebuf::underflow
  error reading the file: Is a directory` -- symptomatically indistinguishable
  from "the service just isn't publishing ports" (a crashed/restarting
  container shows no port bindings). Happened independently on *both*
  services (32GB caught first, then found again on 16GB while adding the
  three new models -- worth checking for on any future split/rename of a
  mounted config file).
- A `stop`+`up` after fixing a bad bind mount is not enough -- Docker bakes
  the mount resolution into the container at creation time. Fixing the host
  path requires `--force-recreate`, not just a restart.

## CPU-only (`llama-cpp-cpu`, port 11437, no GPU offload at all)

First real CPU-only numbers in this deployment's history (the "prior testing"
`settings.yaml` referenced never left any recoverable figures -- see below).
Same prompt/methodology as the GPU tuning work: a real ~150-token five-topic
prompt (not a one-liner), `max-tokens=128`, cold request immediately followed
by a warm (cached-prompt) request, `free -h`/`swapon --show`/`nvidia-smi`
after each. `nvidia-smi` confirmed 0% utilization and no model process on
either GPU for every run below -- genuinely CPU-only, not inferred.

Deliberately excluded Flash Next (84 GiB) from this round: it exceeds even
this host's 60 GiB RAM on file size alone (see the 32GB-service section
above for what that does), so a CPU run would hit the same swap-thrashing
wall, not produce a useful CPU-speed number.

| Model | Size | Run | Prefill | Decode | RAM used | Swap used |
|---|---|---|---|---|---|---|
| gpt-oss-20b-F16 | 13 GiB | cold | 68.06 tok/s | 10.42 tok/s | 19 GiB | 0 B |
| gpt-oss-20b-F16 | 13 GiB | warm | -- | 10.43 tok/s | 19 GiB | 0 B |
| Ornith-1.5-35B-A3B | 21 GiB | cold | 82.26 tok/s | **16.22 tok/s** | 22 GiB | 930 MiB |
| Ornith-1.5-35B-A3B | 21 GiB | warm | -- | 16.09 tok/s | 22 GiB | 969 MiB |
| Qwen3-Coder-Next-Q4_K_M | 46 GiB | cold | 11.18 tok/s | 9.17 tok/s | 37 GiB | 6.3 GiB |
| Qwen3-Coder-Next-Q4_K_M | 46 GiB | warm | -- | 13.33 tok/s | 37 GiB | 6.3 GiB |
| Qwen3-Next-80B-A3B-Instruct | 46 GiB | cold | 9.23 tok/s | 9.98 tok/s | 37 GiB | 6.1 GiB |
| Qwen3-Next-80B-A3B-Instruct | 46 GiB | warm | -- | 13.24 tok/s | 37 GiB | 6.1 GiB |

### Practical implications

- **CPU-only is a genuinely viable path for MoE models that fit in RAM but
  not VRAM, not merely a slow fallback.** All four models produced coherent,
  respectable output at 9-16 tok/s decode. Contrast this directly with the
  32GB GPU service's 1-3 tok/s on gpt-oss-120b/GLM-4.5-Air: those were
  memory-*exhausted* (RAM and swap both maxed). The two 46 GiB models here
  touched real swap (6.1-6.3 GiB) without exhausting it (8 GiB ceiling) and
  still ran at a usable speed. The determining factor isn't "CPU vs GPU" so
  much as "does the working set actually fit" -- CPU inference with real
  headroom clearly beats GPU inference without it.
- **Decode speed does not scale monotonically with model size.** Ornith
  (21 GiB) decoded faster than every other model here, including the
  smaller gpt-oss-20b (16.2 vs 10.4 tok/s) and both larger 46 GiB models
  (16.2 vs ~9-13 tok/s). Total file size is a poor predictor of CPU decode
  speed on its own -- active-parameter count and per-expert compute shape
  (256 experts/8 active for Ornith vs 32/4 for gpt-oss) matter more than
  raw weight volume once everything fits in RAM.
- **Cold-vs-warm reveals a real first-touch penalty, but only for the two
  46 GiB models.** Their decode speed rose ~40-45% warm over cold
  (9.17->13.33, 9.98->13.24 tok/s) -- consistent with mmap still
  page-faulting in weight data during the first run's decode phase, not
  just its prefill. gpt-oss-20b and Ornith showed no such gap (cold and
  warm decode essentially identical), consistent with both fitting
  comfortably enough that the cold run never had to fault in anything
  decode actually touches. The size of this gap is itself a useful signal:
  a model with no cold/warm decode difference has real headroom; one with a
  large gap is closer to its ceiling.
- gpt-oss-20b's CPU decode (10.42 tok/s) against its own GPU-resident figure
  (63.76 tok/s, see above) gives a real same-model CPU/GPU ratio for this
  host: **~6.1x slower on CPU** for this specific model. Not assumed to
  generalize to the other models -- Ornith's relative CPU/GPU gap is
  unmeasured (no clean GPU-only number exists for it yet).

## Single-GPU-pinned variants and Nemotron dual-GPU context (2026-09-17)

`split-mode=none` + `main-gpu=N` is the real mechanism for pinning a model
to exactly one specific GPU on the `llama-cpp-all-gpus` service, which exposes
both cards (`gpus: all`) -- without it, an un-pinned entry's default
split-mode spreads the model across every visible GPU regardless of whether
that's obvious from the section name. Goal was running a model alongside
the 16GB schwerz service without VRAM contention.

- **gpt-oss-20b-F16, pinned to GPU 1, ctx-size=131072: works** (as tested
  that day). Real load + request confirmed. GPU 0 stayed idle (149 MiB),
  GPU 1 used 14,444 MiB of 16,311 MiB -- comfortable headroom at the time.
  Deployed as `gpt-oss-20b-F16-1gpu`.
  **2026-09-17, corrected later the same day: the pin target was wrong.**
  This test (and every other "-1gpu"/single-GPU entry added afterward) was
  pinned to GPU 1 on the assumption that the 16GB schwerz service occupies
  GPU 0 -- that's only the compose file's *default* for
  `GS_LLAMA_CPP_16GB_CUDA_VISIBLE_DEVICES`; this deployment's untracked
  `.env` actually overrides it to `1`. The test above happened not to
  observe any contention only because schwerz had no model resident at that
  moment -- real contention surfaced later when an orphaned schwerz
  subprocess (a stuck Qwen3-Coder-Next instance from a disrupted session)
  sat on GPU 1 for 28 minutes after its own session ended and blocked
  unrelated GPU-1-pinned loads from this service. All single-GPU pins
  (`gpt-oss-20b-F16-1gpu` and the four MoE entries below) were moved to GPU
  0 -- verify the *running container's own environment*
  (`docker exec <container> env`) before pinning anything "to avoid" a
  service again, not the compose file's default.
- **Qwen3.8-27B-UD-Q4_K_M, pinned to GPU 1: does not fit on one 16 GiB card
  at any usable context.** Tried ctx-size=131072 first: CUDA OOM allocating
  the KV buffer (`cudaMalloc failed: out of memory` allocating 4352 MiB on
  device 1, "failed to allocate buffer for kv cache"). Reduced to
  ctx-size=32768 on the theory that the KV buffer itself was the problem --
  same failure class recurred, just smaller (OOM allocating only 1088 MiB
  this time). A ~1 GiB KV buffer failing to allocate means the dense weights
  alone are consuming at least ~15.2 GiB of the 16,311 MiB card before any
  context is allocated at all -- this is a hard capacity ceiling, not a
  context-size tuning problem. Q4_K_M is the smallest of the three 27B
  quants on this host; Q5_K_M and Q6_K_M are larger still, so no quant of
  this model family fits solo on one 16 GiB card here. Removed the failed
  `-1gpu` entry from the preset rather than leave a config that can never
  load; the three existing dual-GPU (`split-mode=tensor`) entries remain the
  only way to run this model family on this host.
- **NVIDIA-Nemotron-3.5-Lightning-30B-A3B-Q4_0, both GPUs, ctx-size=262144:
  works, tested.** GPU 0: 10,495/16,311 MiB. GPU 1: 13,538/16,311 MiB --
  GPU 1's ~2.7 GiB headroom is the binding constraint on pushing this
  further; not tested beyond this figure. Uses the model's own published MTP
  sidecar for speculative decode (`spec-draft-model`/`spec-type=draft-mtp`).

## Real decode speed under an agentic DSH workload (2026-09-17)

Seven DSH code-review sessions (see `code-review-performance.md` in this
same directory for the full comparison) give real, measured decode tok/s for
three of this service's routes under genuine agentic tool-calling load, not
a synthetic benchmark prompt -- tok/s = total output tokens / model-only
compute time (step/start to the model's last output chunk before any tool
executes), summed across each session:

- `Qwen3.8-27B-UD-Q6_K_M` (dual-GPU, tensor-split): **22.5 tok/s**, 78,725
  output tokens over 3494 s of real model compute (one 191.9-minute session).
- `NVIDIA-Nemotron-3.5-Lightning-30B-A3B-Q4_0` (dual-GPU): **42.2-101.2
  tok/s** across three sessions (average of the per-session ratios,
  ~80 tok/s) -- confirms the MTP speculative-decode sidecar and the cheap
  hybrid-SSM architecture both pay off in practice, not just in theory.
- `gpt-oss-20b-F16-1gpu` (single GPU, pinned to GPU 0): **52.5-60.8 tok/s**
  across three sessions.

**2026-09-17, later the same day, batch 2:** two more routes, measured the
same way, via the 16GB MoE-cache service (`llama-cpp-moe-16gb`, physical
GPU 1 -- see the correction below):

- `Qwen3.8-Flash-Next-UD-Q3_K_XL` (MoE-cache, single GPU): **9.9-10.8 tok/s**
  across three sessions -- consistent and slow-but-steady, matching this
  service's host-offloaded-expert architecture rather than a GPU-resident
  dense model's speed. Despite the low tok/s, this model produced the best
  code reviews of any session in either batch (see
  `code-review-performance.md`) when given a long enough run to finish --
  raw decode speed and review quality are unrelated findings here.
- `Qwen3-Coder-Next-Q4_K_M` (MoE-cache, single GPU): **3.3-10.5 tok/s**
  across two sessions -- the 3.3 tok/s outlier (`e845f1c7`) coincides with
  the same session later found to have left an orphaned subprocess running
  on this service (see below), so may reflect early symptoms of whatever
  caused that hang rather than steady-state throughput; not conclusive from
  one data point.

Nemotron decoding 2-4x faster than Qwen3.8-27B-UD-Q6_K_M here is the
clearest real evidence yet that its dual-GPU config (above) is worth using
for throughput-sensitive work -- but see `code-review-performance.md`:
decode speed did not correlate with review quality in this same batch of
sessions, so this is a throughput finding only, not a capability one.

One of the three Nemotron sessions (`339a2bed`, 13:03 UTC) also caught a
real DSH config bug in the act: at that time, `settings.yaml` still had the
stale `contextWindow: 65536` for this model (the dual-GPU ctx-size above is
actually 262144) and no `modelPolicies` compaction override, so DSH began
`compaction/prune`-ing the session after just 8 turns / 66 s of model time
-- pruning against roughly a quarter of the model's real window. The session
produced almost no output as a direct result. Both gaps were fixed the same
day (`settings.yaml` contextWindow corrected, a Q6_K_M/GLM-style
`modelPolicies` entry added to `agent.cordis.yml`) before this note was
written; a retest under the corrected config would be needed to know
whether Nemotron's compaction behaviour is otherwise sound at this window
size, since no session here exercised the fixed config.

## `models-preset.ini` split into GPU and CPU templates (2026-09-17)

The GPU (`llama-cpp`) and CPU (`llama-cpp-cpu`) services had shared one
"sparse override" source file for the GPU router, with the CPU router's
deployed preset generated from it ad hoc and never subsequently kept in
sync -- confirmed stale (still had `split-mode=tensor` on the 27B Qwen
entries, meaningless with no CUDA devices passed through, and predated the
reasoning-budget fix). Split into two real, independently tracked repo
sources, mirroring the schwerz 16GB/32GB split pattern from earlier this
project:

- the then-shared GPU source (subsequently split into
  `llama-cpp/config/llama-cpp-16gb/models-preset.ini` and
  `llama-cpp/config/llama-cpp-32gb/models-preset.ini`) -- unchanged in shape
  at that time except for removing the failed Qwen `-1gpu` entry above.
- `llama-cpp/config/llama-cpp-cpu/models-preset.ini` -- new. Strips every GPU-only directive
  (`split-mode`, `main-gpu`, `n-gpu-layers=auto` partial offload) and adds a
  CPU-specific Nemotron entry (see below). `llama-cpp-cpu` was not actually
  running on this host at the time of this change (absent from `docker
  compose ps -a`), so the new deployed preset is untested against a real
  load -- verify before relying on it.
  (They now live under `llama-cpp/config/<service>/`, alongside every other
  service's template.)

CPU-specific Nemotron entry, deliberately different from the GPU one, not a
copy of it:

- No MTP speculative-decode sidecar. The draft model gives a GPU with spare
  compute a second forward pass essentially for free; on CPU that pass has
  real cost, and there's no measurement yet of its acceptance rate for this
  hybrid SSM/attention architecture (`nemotron_h_moe`) under CPU threading.
  Starts without it; revisit as a follow-up experiment once the base config
  is confirmed working.
- `ctx-size = 131072` is a reasoned starting point, **not yet tested** (the
  service wasn't running to test against). Reasoning: the weight file is
  only ~18 GiB (`du -h` confirmed) against ~55 GiB free RAM at the time
  (`free -h`), and most of this architecture's layers are Mamba/SSM with
  fixed-size state rather than growing KV cache, so it should scale with
  context more cheaply than a comparable dense transformer. Native context
  is 1,048,576 -- raise incrementally from 131072 once verified, don't jump
  straight to max on an untested config.

## Real reliability gap: orphaned GPU subprocess on the 16GB schwerz service (2026-09-17)

Found while reviewing DSH logs and re-confirmed while debugging unrelated
failed loads on the `llama-cpp-all-gpus` service: a `Qwen3-Coder-Next-Q4_K_M`
`llama-server` subprocess under the `llama-cpp-generel-schwerz-16gb-c`
container was still running and holding 7.5 GiB of VRAM **28 minutes**
after the DSH session that had loaded it (`e845f1c7`) had already ended.
Its own session's final request, and a concurrent `Qwen3.8-Flash-Next`
session's final request (`dd01b4f8`), both went unanswered at the same
timestamp -- consistent with the router being wedged behind this stuck
subprocess rather than a clean restart, contrary to the working assumption
mid-session that "the llama service was restarted". The subprocess was
confirmed via `nvidia-smi`'s process list (`ps` showed 27:58 elapsed) and
cleared only by restarting the whole `llama-cpp-generel-schwerz-16gb`
container -- nothing in this deployment currently detects or kills a hung
per-model subprocess on its own. This blocked unrelated loads on the same
physical GPU too (see the GPU-pin correction below), not just this
service's own requests. Not yet root-caused *why* the subprocess hung in
the first place -- worth investigating if it recurs, since a fix would need
either a router-level health check/reaper or a request-level timeout that
kills and restarts the stuck instance.

## Correction: the 16GB schwerz service's real GPU pin (2026-09-17)

Every "GPU 0 occupied by schwerz" assumption in this repo -- including the
`gpt-oss-20b-F16-1gpu` pin above and every single-GPU-pinned entry added
after it -- was based on the compose file's *default* for
`GS_LLAMA_CPP_16GB_CUDA_VISIBLE_DEVICES` (`0`), never checked against the
actually-running container. This deployment's untracked `.env` overrides it
to `1`: the 16GB schwerz service really runs on **physical GPU 1**,
confirmed via `docker exec llama-cpp-generel-schwerz-16gb-c env`. The
earlier `gpt-oss-20b-F16-1gpu` test didn't reveal this because schwerz had
no model resident at that moment -- real contention only surfaced once both
services had a model loaded at the same time (compounded by the orphaned
subprocess above). All single-GPU-pinned entries in the then-shared upstream
GPU preset were moved from `main-gpu=1` to `main-gpu=0` and re-verified with
a real load. That source has since been split into the 16GB and 32GB presets.
Lesson for next time: check the *running container's* environment,
not the compose file's default, before pinning anything "to avoid"
contention with another service.

## Real incident: split-mode=tensor broken by the service refactor, fixed (2026-09-18)

`llama-cpp-all-gpus` started failing a real load for all three
`Qwen3.8-27B` quants (`Q4_K_M`, `Q5_K_M` by extension, `Q6_K_M` confirmed)
under `split-mode=tensor` -- **not** an OOM. Real error:
`ggml_backend_cuda_comm_allreduce_nccl` -> `ncclGroupEnd()` -> `CUDA error:
unhandled cuda error`. Diagnosed with `NCCL_DEBUG=INFO`: NCCL negotiates a
working transport fine (tried and ruled out both `NCCL_P2P_DISABLE=1`,
forcing SHM, and `NCCL_SHM_DISABLE=1`, forcing pure `NET/Socket` -- same
failure either way), then a CUDA kernel launch inside NCCL itself fails
with `Cuda failure 1 'invalid argument'` (`enqueue.cc:1500`), independent
of transport. This points at an NCCL 2.25.1 / RTX 5060 Ti (a very recent
GPU generation) compatibility gap introduced by the service refactor's
rebuild-from-source (the pre-refactor image apparently didn't hit this).

**Fix: `NCCL_CUMEM_ENABLE=0`** on `llama-cpp-all-gpus` in `compose.ai.yml`.
This does not make NCCL itself succeed -- the log still shows `NCCL init
failed (unhandled system error); falling back to internal AllReduce` --
its real effect is letting llama.cpp catch that failure and use its own
non-NCCL AllReduce path instead of crashing. Confirmed by a real load +
request for both `Q4_K_M` and `Q6_K_M` (HTTP 200, real completions).
Decode speed on the fallback path (8-token samples, not a clean
benchmark -- 34.97 tok/s `Q4_K_M`, 29.15 tok/s `Q6_K_M`) lands close to
the original NCCL-based tensor-split figures earlier in this document
(~39-40 / ~30-31 tok/s) -- close enough that tensor-split remains clearly
worth keeping over `split-mode=layer` (tried, works, confirmed much
slower for this workload -- the user's explicit call: "We need split mode
tensor. It is much faster."). Worth a clean cold/warm re-benchmark at some
point to get a real, non-8-token number for the fallback path specifically.

**2026-09-18, later the same day: the clean re-benchmark, real 256-token
cold/warm runs for all five Qwen3.8-27B configurations, user-run:**

| Config | Placement | VRAM | Cold decode | Warm decode |
|---|---|---|---|---|
| `Q4_K_M` | dual-GPU tensor-split (fallback AllReduce) | 10,655 + 10,740 MiB (~21.4 GiB combined) | 39.89-40.51 tok/s | 39.96 tok/s |
| `Q5_K_M` | dual-GPU tensor-split (fallback AllReduce) | 12,231 + 12,316 MiB (~24.5 GiB combined) | 34.92 tok/s | 34.94 tok/s |
| `Q6_K_M` | dual-GPU tensor-split (fallback AllReduce) | (not captured -- output truncated) | ~29-31 tok/s (prior 8-token sample + historical NCCL-based figure, not re-confirmed cleanly this round) | -- |
| `Qwen3.8-27B-UD-IQ3_S` | single GPU (`llama-cpp-gpu-1`) | 14,858 MiB (one card) | 30.64 tok/s | 30.69 tok/s |
| `Qwen3.8-27B-UD-Q3_K_XL` | single GPU (`llama-cpp-gpu-1`) | 14,664 MiB (one card) | 28.92 tok/s | 28.91 tok/s |

Both GPUs sat at 97-99% utilization in every case (dual and single alike)
-- none of these are idle-waiting on something else, all genuinely
compute/bandwidth-saturated.

**The user's real observation: the single-GPU Q3 quants (smaller, lower-bit)
decode slower than the dual-GPU Q4_K_M (larger, higher-bit).** This is a
real, explicable effect, not a fluke or a sign of something wrong:

Dense-model decode at batch=1 is memory-bandwidth-bound, not
compute-bound -- every generated token requires streaming the *entire*
weight set from VRAM through the GPU once. Tensor-split across two GPUs
doesn't just divide the memory footprint; it divides that per-token
streaming work across two GPUs' memory buses in parallel, roughly
doubling the effective bandwidth available to decode (at the cost of a
small per-layer cross-GPU reduce). A smaller/lower-bit quant on a single
GPU reduces the bytes that GPU must stream per token, but nowhere near
enough to make up for only having one card's bandwidth instead of two.

The numbers here are consistent with that explanation, not just
qualitatively but quantitatively: `Q4_K_M` split across two GPUs streams
roughly half its ~15.3 GiB weight set per card per token-pass (~7.6 GiB/
card-equivalent), while `IQ3_S` streams its entire ~11.2 GiB alone on one
card. That's a predicted ratio of about 1.46x more data through the single
bottleneck GPU for `IQ3_S` versus what each GPU handles in the `Q4_K_M`
split -- and the observed decode ratio is 40/30.6 ≈ 1.3x, 40/28.9 ≈ 1.38x.
Close enough, given real-world overhead (the cross-GPU reduce cost eating
into the dual-GPU side's theoretical 2x) to treat memory bandwidth as the
real, dominant explanation rather than coincidence.

**Practical implication**: for this dense model family on this hardware,
dual-GPU tensor-split will essentially always out-decode a single-GPU
placement, regardless of quant size, because it's fundamentally adding a
second memory bus, not just splitting work. The single-GPU Q3 configs are
still genuinely useful -- they're the only way to run this model *and*
have the other physical GPU free for something else (schwerz, a second
session) at the same time -- but that's a concurrency/exclusivity trade,
not a speed one, and shouldn't be expected to compete with dual-GPU on
raw decode throughput.

## Qwen3.8-27B, single GPU, real 3-bit quants (2026-09-18)

The llama.cpp services were rebuilt from source with a per-GPU-locked
architecture since the last note above (see `llama-cpp/README.md`):
`llama-cpp-gpu-0`/`llama-cpp-gpu-1` each reserve exactly one physical GPU at
the Docker level (`gpus.device_ids`), confirmed via `docker exec ...
nvidia-smi` inside `llama-cpp-gpu-1-c` -- only one GPU is visible at all, so
`split-mode`/`main-gpu` pinning (needed on `llama-cpp-all-gpus`, which still
sees both cards) is unnecessary for models deployed on these two services.

User downloaded two real 3-bit Unsloth Dynamic v3.0 quants of Qwen3.8-27B
(no literal "Q3_K_M" exists for this model -- the real ladder is
`UD-IQ3_XXS`/`UD-IQ3_S`/`UD-Q3_K_XL`). Both load and respond on
`llama-cpp-gpu-1` (physical GPU 1), confirmed with real requests, at
`ctx-size=65536`:

- `Qwen3.8-27B-UD-IQ3_S` (11.2 GiB on disk): **13,610 MiB** VRAM, 30.2 tok/s
  decode. ~2.7 GiB headroom on the 16,311 MiB card at 65536.
- `Qwen3.8-27B-UD-Q3_K_XL` (12.2 GiB on disk): **14,664 MiB** VRAM, 27.7
  tok/s decode. ~1.6 GiB headroom at 65536 -- tighter, matches the earlier
  estimate that this quant would have less margin than `IQ3_S`.

**2026-09-18, same day, largest real context per quant:** extrapolated a
target ctx-size from the real measured KV rate for this model family
(34.0 KiB/token combined K+V at q8/q8, from the earlier Q4_K_M single-GPU
OOM test) -- 131072 for `IQ3_S`, 98304 for `Q3_K_XL`. **Both first attempts
failed a real load**, each by a small margin late in loading (`allocating
720.28 MiB on device 0: cudaMalloc failed: out of memory` for `IQ3_S` at
131072; `560.28 MiB` for `Q3_K_XL` at 98304) -- the flat ~600 MiB overhead
assumed on top of the KV-rate extrapolation undercounted something, likely
a compute/graph buffer with its own context-dependent cost beyond raw KV
cache. Backed off by a full 32768 tokens rather than guess again narrowly,
and both were then confirmed working by a real load:

- `Qwen3.8-27B-UD-IQ3_S`: **ctx-size=98304 works**, 14,858 MiB VRAM, 1,453
  MiB headroom. (131072 does not fit.)
- `Qwen3.8-27B-UD-Q3_K_XL`: **ctx-size=65536 works** (unchanged from the
  original test, re-confirmed), 14,664 MiB VRAM, 1,647 MiB headroom. (98304
  does not fit.)

There is likely real headroom between each quant's working value and its
failed one (e.g. `IQ3_S` somewhere in 98304-131072), but that gap is
untested -- the lesson here is that a KV-rate-only extrapolation is not
sufficient for predicting the real ceiling on this build; treat any
extrapolated ctx-size as a starting point to verify, not a target to trust,
even when the KV-rate itself was measured rather than guessed.

Both are real, working single-GPU options for this model family that
`Qwen3.8-27B-UD-Q4_K_M` (the previous smallest quant on disk) could not
achieve solo on one 16 GiB card at any context (see the entry above).

## Both 3-bit quants forced onto dual-GPU tensor-split despite fitting on one card (2026-09-18)

Following the bandwidth analysis above (dense-model decode at batch=1 is
memory-bandwidth-bound, so dual-GPU tensor-split roughly doubles effective
bandwidth regardless of whether the model needed to split for capacity
reasons): added both `Qwen3.8-27B-UD-IQ3_S` and `Qwen3.8-27B-UD-Q3_K_XL`
to `llama-cpp-32gb`'s preset too, with `split-mode=tensor` forced
explicitly, `ctx-size=163840` (matching `Q6_K_M`, the largest of the three
already-working dual-GPU quants, as a known-good starting point). Both
confirmed working with a real load + request:

| Config | VRAM/card | Decode (8-token sample) | Decode (clean 256-token cold/warm) |
|---|---|---|---|
| `IQ3_S`, single GPU (`llama-cpp-gpu-1`) | 14,858 MiB | 30.64-30.69 tok/s | 30.64-30.69 tok/s (this *was* the clean run) |
| `IQ3_S`, forced dual-GPU tensor-split | 9,331 + 9,416 MiB | 39.54 tok/s | **47.50 / 47.55 tok/s** |
| `Q3_K_XL`, single GPU (`llama-cpp-gpu-1`) | 14,664 MiB | 28.91-28.92 tok/s | 28.91-28.92 tok/s (this *was* the clean run) |
| `Q3_K_XL`, forced dual-GPU tensor-split | 9,857 + 9,942 MiB | 38.41 tok/s | **45.53 / 45.63 tok/s** |

The clean 256-token cold/warm numbers (user-run) came in noticeably higher
than the earlier 8-token samples suggested, and higher than `Q4_K_M`'s own
dual-GPU decode speed (~40 tok/s) despite `Q4_K_M` being the larger quant
-- consistent with a smaller quant needing proportionally less bandwidth
per token even after the dual-GPU doubling. Both use *less* VRAM per card
than their own single-GPU placement (weights are split, not duplicated)
-- ~6.4-7 GiB free per card at this context, real headroom to raise
`ctx-size` further that hasn't been tested yet. Confirms forcing
tensor-split is a genuine, worthwhile throughput win even for a model
that fits on one card, not just a capacity mechanism -- the trade-off is
occupying both physical GPUs instead of leaving one free for something
else (schwerz, a second session).

**Same change applied to `gpt-oss-20b-F16` (2026-09-18, same day).** This
entry had no `split-mode` set at all -- silently inheriting llama.cpp's
own default (layer split, not tensor) rather than an intentional choice.
Forced `split-mode=tensor` explicitly. Confirmed working by a real load +
request, then re-confirmed with a clean 256-token cold/warm run (user-run):
7,621 + 7,706 MiB combined VRAM (vs. ~13.3 GiB solo on one card in the
GPU-resident baseline earlier in this document -- little more than half,
since weights split rather than duplicate) and **141.38 / 142.33 tok/s**
decode cold/warm -- well above the initial 114.8 tok/s 8-token estimate,
and about 2.2x the recorded 63.76 tok/s single-GPU baseline (slightly
better than a flat doubling -- plausibly because this is the F16-weight
entry, so the per-token bytes streamed are larger than a quantized model's,
making the bandwidth-bound effect even more pronounced). Unlike
`GLM-4.7-Flash` (`deepseek2` architecture, confirmed NOT to support
`split-mode=tensor` on this build), `gpt-oss`'s architecture does support
it here.

## Real incident: `llama-cpp-cpu` RAM audit, one near-miss on host stability (2026-09-18)

Auditing `llama-cpp-cpu`'s preset for models that can't fit in this host's
RAM (60 GiB total, no GPU passthrough at all on this service -- everything
must fit in RAM alone, unlike the schwerz MoE-cache services which page
experts through VRAM). Five small chat models added for CPU testing
(`gemma-3n-E2B-it`/`E4B-it`, `NVIDIA-Nemotron-3-Nano-4B`, `Qwen3.5-9B`,
`Ornith-1.5-9B` -- 2.8-5.4 GiB each, no real RAM risk, `gemma-3n-E2B-it`
confirmed working with a real request). Three real findings from the audit
itself:

1. **`Qwen3.8-Flash-Next-UD-Q3_K_XL` (84 GiB) was actually selectable
   despite the file's own header comment claiming it was "deliberately
   absent."** The comment was wrong in practice: omitting a model from the
   sparse override source does not stop `generate-models-preset.py`'s
   full-discovery mode from adding it anyway as a basic catch-all entry --
   confirmed present in the deployed file under its raw discovered ID
   (`unsloth--Qwen3.8-Flash-Next--UD-Q3_K_XL`) at `[*]` defaults. The tool
   has no exclude mechanism; switching this service to `--preset-only`
   mode (like the schwerz/csantiago78 fork services) would fix it but also
   remove auto-discovery for every small model in this file, a bigger
   trade-off than asked for. Fixed by adding an explicit entry under the
   correct friendly name with `load-mode=mmap`/`lazy-mode=on` (the same
   safety net the schwerz services use for oversized models) -- this
   replaces the confusing raw-ID duplicate and gives it the best-available
   graceful degradation, but is explicitly **not** a claim that it will
   actually work; the realistic failure mode if selected is prolonged
   swap-thrashing, not a clean fast error.

2. **`DeepSeek-R1-Distill-Llama-70B-Q4_K_M` at `ctx-size=65536` FAILED a
   real load test -- a genuine near-miss on host stability, not a
   theoretical risk.** The entry's own prior justification ("Q8 K/V cache
   is about 10 GiB" against 39.6 GiB weights, should have left ~6 GiB free
   on a ~56 GiB-available host) turned out to be wrong or incomplete in
   practice. Real load: swap climbed steadily from a baseline 2.9 GiB to
   7.7 GiB of the 8 GiB ceiling before the container was stopped manually
   to avoid risking wider host instability (other things run on this host
   besides these services); the in-flight request then failed with an
   empty reply, consistent with the server being killed under memory
   pressure. The host recovered fully within seconds of stopping the
   container (swap back to ~3.5 GiB, ~55-57 GiB available again) -- this
   was contained, not a system-wide event, but real memory pressure that
   a different (more loaded) moment on this host could have handled worse.
   Backed off to `ctx-size=8192`, matching the already-conservative
   `Qwen2.5-72B-Instruct-Q3_K_S` entry -- **not yet re-verified with a real
   load**, deliberately, given the risk just observed; the exact cause
   (compute/scratch buffers, mmap page-cache duplication during active
   load, or the original KV estimate itself) was not isolated before
   backing off, so treat 8192 as an emergency reduction to verify when
   convenient, not a confirmed-safe value.

3. **`Llama-3.3-70B-Instruct-Q3_K_M` (32 GiB) was sitting as an
   undiscovered catch-all entry with an even more expensive cache config
   than the DeepSeek entry that just failed** (`[*]` defaults are
   `cache-type-k/v` both `q8_0`, vs. DeepSeek's `q8_0`/`q4_0` mix) at the
   same `ctx-size=65536` default. Close enough in profile (dense, 70B
   class) to the just-demonstrated failure that it was promoted to an
   explicit entry with `ctx-size=8192` as a preemptive fix, by reasoning
   from the DeepSeek result rather than by repeating the same live-load
   risk a second time in one sitting. Also **not yet re-verified with a
   real load**.

General lesson, consistent with several earlier findings in this document:
a documented intent ("this model doesn't fit, so it's absent") is not the
same as a verified runtime guarantee, especially on a service using full
discovery mode -- the two dense-70B-class entries here had *looked* safe
on paper (weights + a plausible KV estimate, under the available RAM
figure) and one of them demonstrably was not, in practice, at the context
size it had been configured for.

**Resolution (2026-09-18, same day): `llama-cpp-cpu` switched from
full-discovery to `--preset-only`, and trimmed to just what's actually
verified.** This closes the root cause behind finding 1 above (the tool
having no way to exclude a discovered model) rather than continuing to
patch around it per-model. Final curated catalogue: the five small models
(same as before) plus only the two real, CPU-tested >32 GiB MoE models
(`Qwen3-Coder-Next-Q4_K_M`, `Qwen3-Next-80B-A3B-Instruct-Q4_K_M`) --
`Qwen2.5-72B-Instruct-Q3_K_S`, `Llama-3.3-70B-Instruct-Q3_K_M`,
`DeepSeek-R1-Distill-Llama-70B-Q4_K_M` (the one that actually failed),
the untested Nemotron 3.5 Lightning CPU entry, the non-MoE
`gpt-oss-20b-F16` entry, and the CPU-unsafe `Qwen3.8-Flash-Next-UD-Q3_K_XL`
entry are all removed rather than kept with caveats -- confirmed via a
real deployed-catalogue check (`/v1/models` after restart): exactly 7
models, matching intent precisely. `llama-cpp-gpu-0`/`llama-cpp-gpu-1`
(via the shared `llama-cpp-16gb` preset) were also switched to
`--preset-only` at the same time, so `llama-cpp-all-gpus` (`llama-cpp-32gb`)
is now the *only* service still using full-discovery mode -- this was
already the documented intent in `llama-cpp/README.md`, which had gotten
ahead of the actual deployed state until this pass caught it up. Note:
`llama-cpp-16gb`'s own model list still has the same class of
oversized/unverified entries as the CPU file did (e.g.
`DeepSeek-R1-Distill-Llama-70B-Q4_K_M`, which cannot fit on one 16 GiB
card at all) -- not audited or changed in this pass, since preset-only
mode only stops *undiscovered* models from appearing, not explicitly
curated ones that don't actually fit their service.

## `llama-cpp-16gb` pruned to proven/known-safe entries (2026-09-18)

Follow-up to the note at the end of the previous section: `llama-cpp-16gb`
(the shared preset for the single-GPU-locked `llama-cpp-gpu-0`/
`llama-cpp-gpu-1` services) still had the same class of oversized entries
the CPU file did, just not yet exercised by a live incident. Audited and
pruned directly rather than waiting for one.

**Six entries removed, each for a distinct, unambiguous reason -- no
genuine borderline cases:**

- `Llama-3.3-70B-Instruct-Q3_K_M` (32 GiB), `Qwen2.5-72B-Instruct-Q3_K_S`
  (32.12 GiB), `DeepSeek-R1-Distill-Llama-70B-Q4_K_M` (39.60 GiB) -- dense
  models, nowhere close to fitting a 16,311 MiB card. The DeepSeek entry is
  also the exact model that just failed a real CPU-service load test this
  same day (previous section) -- independent confirmation this size class
  is a real risk, not just a paper estimate.
- `Qwen3-Coder-Next-Q4_K_M`, `Qwen3-Next-80B-A3B-Instruct-Q4_K_M` (45.09
  GiB each) -- real, CPU-tested MoE models correctly present in
  `llama-cpp-cpu`'s catalogue, but their entries here had `n-gpu-layers = 0`,
  meaning they ran fully CPU-bound even under a GPU-locked service. Wrong
  service for what they actually do at runtime; removed here, not
  duplicated.
- `NVIDIA-Nemotron-3.5-Lightning-30B-A3B-Q4_0` -- real on-disk weight size
  17.60 GiB, confirmed via `stat`, already exceeding one card's 16,311 MiB
  (~15.93 GiB) capacity before any KV cache is allocated. Never tested
  single-GPU (only proven on `llama-cpp-all-gpus`, both cards). Same
  failure signature already proven for `Qwen3.8-27B-UD-Q4_K_M` (weight
  alone left under 1 GiB free, real CUDA OOM on the KV buffer) -- not a
  judgement call, a direct size comparison.

**Sixteen entries kept**, all either real-load-confirmed this session on a
single GPU (`gpt-oss-20b-F16`, both `Qwen3.8-27B` 3-bit quants, and the
four `n-cpu-moe`-offloaded 30-35B MoE models) or small enough that fit was
never genuinely in question: two tiny embedding models (0.31-0.60 GiB),
and the older CodeLlama/Magicoder/WizardCoder/StarCoder2/Qwen2.5-Coder
models (3.56-8.44 GiB, real on-disk sizes verified via `stat` this pass) --
downloaded before the second GPU existed, never individually re-tested
this session, but each under half a 16 GiB card leaves no real doubt.

Redeployed via `generate-models-preset.py --preset-only --force`; the
generator validated every explicit `/models/...` path in the pruned file
and added nothing else, consistent with `--preset-only` semantics.
Live `/v1/models` verification against a running `gpu-0`/`gpu-1` container
still pending -- neither was running at the time of this prune (only
`llama-cpp-cpu` was up); the new catalogue takes effect the next time
either starts.

## `llama-cpp-32gb` pruned of CPU-only-in-a-GPU-service entries (2026-09-18)

Follow-up to the `llama-cpp-16gb` prune above, same day, at the user's
request: two entries removed from `llama-cpp-32gb`
(`llama-cpp-all-gpus`'s preset) --  `Qwen3-Coder-Next-Q4_K_M` and
`Qwen3-Next-80B-A3B-Instruct-Q4_K_M`. Both carried `n-gpu-layers = 0`,
meaning they never touched either GPU even on this dual-GPU-locked
service -- pure CPU pass-through. An explicit curated entry for a
CPU-only config on a GPU-locked service implies a GPU-resident capability
that was never actually being exercised; both models are properly homed
and tested elsewhere (CPU-only figures in `llama-cpp-cpu`'s preset, MoE
host-offload figures in the 16GB schwerz service's table above).

This service stays in full-discovery mode (the one exception, per
`llama-cpp/README.md`), so both models remain selectable here via their
raw directory-based catch-all IDs -- that's intentional and accepted by
the user; only the curated entry (and the misleading "this works here"
implication it carried) was removed. Confirmed via redeploy:
`generate-models-preset.py` reported "Discovered 35 models; added
defaults for 28 models," consistent with both names no longer being
explicit template entries.

Audited the rest of the file against the same "GPU-resident vs. host-only"
criterion before deciding not to touch it further:
`NVIDIA-Nemotron-3.5-Lightning-30B-A3B-Q4_0` (real dual-GPU-resident
DSH sessions at 42-101 tok/s, MTP speculative decode, GPU 0/1: 10.5/13.5
GiB), `gpt-oss-20b-F16` (real dual-GPU-resident 141+ tok/s), and
`GLM-4.7-Flash-Q4_K_M` (real `split-mode=layer` dual-GPU placement, the
supported mechanism for its deepseek2 architecture on this build) are all
MoE-architecture models too, but each is independently verified
GPU-resident on this exact service -- none is a duplicate of a
host-offload-only test the way the two removed entries were. No further
removals identified.

Live `/v1/models` verification against a running `llama-cpp-all-gpus`
container still pending -- it was not running at the time of this prune
(only `llama-cpp-cpu` was up); the new catalogue takes effect the next
time it starts.

## Real-request audit of both pruned presets finds three genuine bugs (2026-09-18)

Follow-up, same day, prompted by "confirm all of the updated configs work"
-- rather than trust the size/architecture reasoning behind the two prunes
above, sent a real request (chat completion or, for the two embedding
models, `/v1/embeddings`) to every curated entry in `llama-cpp-16gb` and
spot-checked `llama-cpp-32gb`. This is the same lesson this document has
recorded before ("a documented intent is not the same as a verified
runtime guarantee") applied to the *kept* entries this time, not just the
removed ones -- and it found three real problems, all in the "older,
small, never individually tested but size makes it obviously safe" group
that the 16GB prune had waved through on size alone:

1. **`magicoder-s-ds-6.7b.Q4_0` cannot load on this build at all.** Real
   error: `error loading model vocabulary: unknown tokenizer:
   'deepseek_coder'`. This llama.cpp build doesn't support this old GGUF's
   tokenizer format -- not a config problem, not fixable by any preset
   setting. Removed from `llama-cpp-16gb` entirely. (The other five
   TheBloke/bartowski/Qwen2.5-Coder "older" entries all loaded and
   answered correctly -- this was specific to this one file, not the
   category.)
2. **`Qwen3-Embedding-0.6B-Q8_0` rejected every embeddings request**:
   `"This server does not support embeddings. Start it with
   --embeddings"`. The preset entry never set the `--embeddings` flag, so
   the router loaded it in default generative mode -- selectable, even
   answered on `/v1/models`, but functionally useless for its one actual
   purpose.
3. **`embeddinggemma-300M-Q8_0` crashed outright** on load:
   `GGML_ASSERT(n_outputs_max <= cparams.n_outputs_max) failed` inside
   `llama_context::encode`, a hard process abort, not a clean error --
   same root cause as #2 (no `--embeddings`), worse failure mode.

**Fix**: `embeddings = true` added to both embedding entries; confirmed
working afterward with real `/v1/embeddings` calls (1024-dim and 768-dim
vectors returned respectively).

**A fourth, separate problem was also found and fixed while investigating
these**: the repo source file for `llama-cpp-16gb` was itself missing
both embedding-model sections entirely -- a real transcription error made
when that file was rewritten earlier the same day (the "16 entries kept"
count in that pass's own summary included both embedding models, but the
actual file written did not). The only reason this stayed invisible was
that the *previously deployed* copy at `/mnt/work/llama/llama-cpp-16gb/`
still had them from before that rewrite, so `/v1/models` kept reporting
them as present even though the checked-in template no longer would have
regenerated them on any future redeploy. Caught by diffing the repo file
against the live-deployed file after the live-request audit surfaced the
embeddings bug and prompted a closer look. Both embedding sections restored
(with the `embeddings = true` fix applied) and the file redeployed;
repo and deployed copies now match exactly.

`llama-cpp-32gb` was only edited with a targeted removal (not a full
rewrite), so the transcription-error risk was lower; spot-checked
`gpt-oss-20b-F16` (unrelated to the edit, confirms the router itself is
still healthy) and `NVIDIA-Nemotron-3.5-Lightning-30B-A3B-Q4_0`
(immediately adjacent to the removed lines, confirms the edit didn't
corrupt that section) -- both answered correctly. The three dense
70B-class entries in that file (`Llama-3.3-70B-Instruct-Q3_K_M`,
`Qwen2.5-72B-Instruct-Q3_K_S`, `DeepSeek-R1-Distill-Llama-70B-Q4_K_M`) were
**not** live-tested in this pass -- each relies on partial CPU offload via
this service's `--fit`/`n-gpu-layers=auto` (DeepSeek's file size, 39.60
GiB, exceeds the ~31.85 GiB combined VRAM of both cards outright, so it
must be offloading layers to host RAM to run at all), a real load would
take minutes and significant host resources, and none of the three has a
recorded real-load confirmation anywhere in this document's history
either. Flagged here as a genuine open gap, not claimed as verified.

**General lesson, worth restating**: a size or architecture argument
("small enough, must be fine") is a necessary check, not a sufficient
one. The two prunes above were correct on capacity; the real bugs they
missed were both a missing CLI flag and a codebase-level incompatibility,
neither of which any file-size or VRAM reasoning could have caught. Live
request testing is what actually confirms a preset entry works.

## Real incident: Devstral-Small ctx-size failure, fixed (2026-09-18)

`Devstral-Small-2-24B-Instruct-2512-Q4_K_M` and `Devstral-Small-2505-Q4_K_M`
were added to `llama-cpp-16gb` (13.35 GiB each) with `ctx-size = 32768` --
deliberately conservative versus a KV-rate extrapolation to 65536, given
this document's own repeated lesson that such extrapolations undercount
something. Conservative wasn't conservative enough: a real load on
`llama-cpp-gpu-1` failed for **both** quants, identically:

```
ggml_backend_cuda_buffer_type_alloc_buffer: allocating 2720.00 MiB on device 0: cudaMalloc failed: out of memory
alloc_tensor_range: failed to allocate CUDA0 buffer of size 2852126720
llama_init_from_model: failed to initialize the context: failed to allocate buffer for kv cache
```

Not an architecture or config bug -- a real, close-margin capacity
shortfall. The weight file alone (13.35 GiB = 13,670 MiB) left only
~2,641 MiB free on the 16,311 MiB card, a hair under the 2,720 MiB the
KV buffer needed at `ctx-size=32768`. Root-caused directly from container
logs (`docker logs llama-cpp-gpu-1-c`) rather than guessed -- the
`failed to fit params to free device memory: n_gpu_layers already set by
user to -2, abort` warning immediately above it is a red herring (an
informational note about `--fit` not running because `n-gpu-layers` was
already resolved, unrelated to the actual OOM two lines later).

**First fix**: backed off to `ctx-size = 16384` (half) for both entries,
redeployed, restarted `llama-cpp-gpu-1`, confirmed working by a real load
+ request for both quants. `Devstral-Small-2505-Q4_K_M` (the model
resident at capture time): **15,180 MiB** used, 1,131 MiB headroom on the
16,311 MiB card -- tighter than either Qwen3.8-27B 3-bit quant at their
own working ctx-size (1.45-1.65 GiB headroom), consistent with Devstral's
larger weight file leaving less room to begin with.

**User judgement call, same day**: 16384 was too small a context to be
useful in practice, and probing intermediate values one restart at a time
(24576 was queued next) was too slow a way to find the real ceiling.
Since this model genuinely needs the combination of weight-splitting
*and* a second card's worth of headroom to reach a worthwhile context on
this hardware -- not a capacity requirement, a context one -- it was
moved off `llama-cpp-16gb` entirely and onto `llama-cpp-all-gpus`
(`split-mode=tensor`, matching the same bandwidth-doubling pattern
already established for `gpt-oss-20b-F16` and the Qwen3.8-27B quants)
and `llama-cpp-cpu` (dense CPU inference, RAM not the constraint a 13.35
GiB weight + 65536-ctx KV would face on one card). `ctx-size=131072`
(Devstral's published native ceiling) confirmed working on
`llama-cpp-all-gpus` for both quants on the first try: 12.8-12.9 GiB per
card, ~3.1-3.2 GiB real headroom each, near-equal weight split confirming
real tensor-split (not just balanced placement). The `llama-cpp-cpu`
entries (`ctx-size=65536`) are not yet load-tested. Real decode/prefill
benchmark figures for the dual-GPU config are also not yet captured (see
the main table's footnote ¹²) -- this pass only confirmed load + a real
response, not throughput.

## Context-size review across every preset: `Qwen3.8-Flash-Next` raised to 131072 (2026-09-18)

Full review of every `ctx-size` in every preset file, at the user's
request (64K treated as the real floor for coding use). Real result for
the one item specifically flagged: `Qwen3.8-Flash-Next-UD-Q3_K_XL` on
`llama-cpp-generel-schwerz-16gb`, raised from 98304 to **131072**. Real
native context is 262144 (confirmed via GGUF metadata: `qwen4exp`
architecture) -- 98304 was only 37% of it. Confirmed working on physical
GPU 1 (the correct card -- see the PCIe finding above): cold run showed a
slower decode (11.16 tok/s) that looked like a real cost at first, but
the warm run resolved it -- **19.17 tok/s, actually faster than the old
98304 setting's 18.87 tok/s** -- confirming the cold figure was normal
first-touch/mmap noise, not a real ongoing cost of the larger context.
Real VRAM: 14,212 MiB used, ~2.05 GiB headroom remaining (down from
~2.9-3.3 GiB at 98304) -- less room than before, but real room still
exists if this gets pushed further later. See the full model-by-model
review below for every other preset entry checked the same pass.

## Real incident: `parameterise-llama` refactor investigation -- three real problems found and fixed (2026-09-18)

The user refactored how llama.cpp services are brought up: one `render-
compose.py` script now generates a per-service Compose overlay from a
`.env` profile per service (`SOURCE_SERVICE` names a template block still
defined in `compose.ai.yml`; `GPU_IDS`/`CONFIG_FILE`/etc. parameterize
it). This replaced ~370 lines of hand-duplicated service blocks. Reported
symptom: `Qwen3.8-Flash-Next` on the 16GB schwerz service dropped to ~6
tok/s decode, far below this document's historical tuned range
(12.67-18.38 tok/s). Investigation found **three separate real problems**,
only one of which was actually a refactor bug -- the other two were a
real hardware constraint and a real pre-existing untested config, both
just newly exposed by testing more thoroughly than before.

### Problem 1: physical GPU 0 has a materially weaker PCIe link than GPU 1 (hardware, not a bug)

The historically-tuned schwerz-16gb service has always run on **physical
GPU 1** (its real default in this deployment's own `.env`, confirmed
earlier this session -- see "Correction: the 16GB schwerz service's real
GPU pin"). The new refactor makes it trivial to instead run the
`-gpu-0` profile, which nothing before today had actually load-tested
with a MoE-cache-heavy model like Flash Next. Real topology check:

```
index, pcie.link.gen.max, pcie.link.gen.current, pcie.link.width.max, pcie.link.width.current
0, 3, 1, 8, 4
1, 4, 1, 8, 8
```

GPU 0 maxes out at PCIe Gen3 with only 4 lanes currently negotiated; GPU
1 is Gen4-capable at the full 8 lanes -- **the cards are not symmetric**,
despite being identical RTX 5060 Ti units. `moe-expert-cache-size`'s
entire mechanism streams "cold" experts from CPU-pinned host memory to
the GPU over PCIe on every cache miss, which is directly bandwidth-bound
on exactly this link. Real, direct A/B confirmation, identical image
(`llama-cpp:generel-schwerz-qwen4exp-mtp-e69a1d0`), identical
`config.ini`/`models-preset.ini`, same model, same request:

| Card | Decode |
|---|---|
| GPU 0 (`-gpu-0` profile) | 6.34-6.60 tok/s |
| GPU 1 (`-gpu-1` profile) | 18.87 tok/s |

GPU 1's figure lands squarely in this document's historical tuned range;
GPU 0's is a real ~3x regression from card choice alone. Confirmed not a
software issue: container command, environment, config file content, and
RAM/VRAM usage were all checked and matched expectations exactly on both
cards -- only the PCIe link differs. **Fix: route the schwerz-16gb
service (and likely any other PCIe-transfer-heavy workload, e.g.
`n-cpu-moe` offload) to the `-gpu-1` profile, not `-gpu-0`.** This isn't
fixable in software; GPU 0 is a real, permanently weaker slot on this
host for this class of workload. Plain GPU-resident workloads (the bulk
of what `llama-cpp-gpu-0`/`gpu-1` serve) are far less exposed to this,
since they stream weights once at load time rather than continuously
during decode -- today's earlier `qwen2.5-coder`/`Expert-Offload` tests
all happened to run on physical GPU 1 already (port 11442's `GPU_IDS=1`),
so none of those real numbers need revisiting.

### Problem 2: `render-compose.py` silently overrode `n-gpu-layers = auto` (real refactor bug, fixed)

While reproducing two of the test-plan failures from earlier today
(`Llama-3.3-70B-Instruct-Q3_K_M`, `Qwen2.5-72B-Instruct-Q3_K_S`, both on
`llama-cpp-all-gpus`) with real container logs this time, the actual
spawned command showed `--n-gpu-layers all`, not `auto` -- despite both
models' preset entries explicitly setting `n-gpu-layers = auto` (the
partial-CPU-offload setting they depend on to fit at all). Root cause,
confirmed directly in `render-compose.py`'s `upstream_command()`:

```python
"--n-gpu-layers", "all" if profile.gpu_ids else "0",
```

This unconditionally set a router-level `--n-gpu-layers` for every
GPU-enabled profile, which overrode the per-model preset value entirely.
Real failure signature: `--fit` (which is supposed to auto-reduce layer
count to fit available memory) aborted immediately --
`"failed to fit params to free device memory: n_gpu_layers already set
by user to -2, abort"` -- then tried to force the *entire* 70B-class
model onto one GPU and hit a real, immediate `cudaMalloc` OOM. This is
why only these two entries failed while 23 other real tests the same day
succeeded: every other curated entry either fits fully in VRAM (where
`all` was already correct) or doesn't set `n-gpu-layers` in its own
preset at all -- only these two actually needed `auto`'s partial-offload
behavior, and the router was silently taking that choice away from them.

**Fix**: removed the unconditional flag. GPU-enabled profiles now pass no
system-level `--n-gpu-layers` at all, letting each model's own preset
value win, and falling back to `llama-server`'s own built-in default
(confirmed via `--help`: `default: auto`) for anything that doesn't set
one -- which already behaves like `all` for a model that fits, so this
is not a behavior change for the 23 already-working entries. The
no-GPU (CPU) profile still gets an explicit `--n-gpu-layers 0`, since
there's no device to offload to regardless of any preset value.

**Verified with real requests, live RAM monitoring throughout (swap held
flat at ~3.1 GiB the entire time on both, no growth, no near-miss)**:

| Model | Decode |
|---|---|
| `Llama-3.3-70B-Instruct-Q3_K_M` | 4.78 tok/s |
| `Qwen2.5-72B-Instruct-Q3_K_S` | 4.57 tok/s |

Both slow (expected for dense 70B-class models under partial CPU
offload) but both genuinely working now, for the first time in this
document's history -- neither had ever been real-load-tested before
today, on any version of this deployment.

### Problem 3: `DeepSeek-Coder-V2-Lite-Instruct-Q4_K_M`'s single-GPU `ctx-size` was never actually tested (pre-existing gap, not a refactor bug)

The third test-plan failure from earlier today, reproduced with real
logs: weights (9.65 GiB) loaded fine, then the `ctx-size=65536` KV buffer
request (a real, confirmed 9,180 MiB / 8.97 GiB allocation) failed --
combined, 18.62 GiB, over one 16,311 MiB (15.93 GiB usable) card outright.
This is unrelated to either problem above: this entry never set
`n-gpu-layers` at all (so it was unaffected by problem 2), and it's a
genuine capacity shortfall, not a PCIe issue. It was simply never real-
load-tested before today (added and curated the same day it was first
tried) -- the same "curated but never verified" gap this document has
hit many times before. **Fix**: backed off to `ctx-size=32768` using the
real KV rate this failure exposed (~143.5 KiB/token). Confirmed working
by a real load + request: 14,688 MiB used, 1,623 MiB headroom. The
dual-GPU entry on `llama-cpp-32gb` (same 65536 context) is unaffected --
it already has 10.6+9.1 GiB combined there, comfortable headroom on two
cards.

### What this means for the earlier layer-split MoE-bandwidth question

The "outstanding MoE performance question" this document raised earlier
today -- does layer-split give a real MoE model any bandwidth benefit the
way tensor-split does for dense ones -- assumed `DeepSeek-Coder-V2-
Lite-Instruct-Q4_K_M`'s single-GPU *failure* was itself the interesting
result. It wasn't -- it was just an untested `ctx-size`, same as problem
3 above. With both entries now working (16GB: `ctx-size=32768`; 32GB:
`ctx-size=65536`, different contexts now, so no longer a perfectly clean
comparison), a real single-vs-dual comparison for this model is still
open, just needs a fresh pair of runs rather than reusing today's
numbers.

## Higher quants downloaded, curated, and real-load-tested (2026-09-18)

Eight real downloads this session, added to `llama-cpp-32gb` (all eight)
and `llama-cpp-16gb` (the three that fit solo on one card), then
real-load-tested via `run-remaining-tests.sh` the same day -- **all
eleven new entries loaded and answered correctly**, no failures, no
ctx-size surprises. Real figures now in the summary table above and
footnotes ¹⁴-¹⁷. `DeepSeek-Coder-V2-Lite-Instruct-Q4_K_M` predates today's
downloads (already on disk, already curated in an earlier pass) but was
tested in the same run -- see the real single-GPU failure documented in
footnote ¹⁹, a genuinely surprising result.

## Test plan results (2026-09-18): 26 tests run via `run-remaining-tests.sh`

23 succeeded, 3 failed (all three cleanly -- no RAM/swap pressure, no
VRAM OOM, just an immediate "failed to load"). Real per-item outcomes:

### `llama-cpp-gpu-0` / `llama-cpp-gpu-1` (16GB service) -- 10/10 attempted, 9 succeeded

- ~~The four new `n-cpu-moe` expert-offload entries~~ -- **all four
  succeeded on the first attempt**, computed `n-cpu-moe` values (19/16/18/
  15) all correct without a second pass. See footnote ²⁰.
- ~~`gpt-oss-20b-F16` on the current single-GPU architecture~~ -- **done**,
  94.34-94.39 tok/s, see footnote ¹⁴.
- ~~`DeepSeek-Coder-V2-Lite-Instruct-Q4_K_M`~~ -- **diagnosed and fixed**,
  real `ctx-size` capacity shortfall (not a code/architecture problem),
  backed off to 32768, confirmed working. See footnote ¹⁹.
- ~~`qwen2.5-coder-7b-instruct-q8_0`, `qwen2.5-coder-14b-instruct-q5_k_m`/
  `-q6_k`~~ -- **all three succeeded**, see footnote ¹⁶.
- ~~`Qwen3.6-35B-A3B-Q4_K_M` anomaly repeat~~ -- **resolved**, confirmed a
  one-off slow load, see footnote ¹³.

### `llama-cpp-all-gpus` (32GB service) -- 16/16 attempted, 14 succeeded

- ~~`Llama-3.3-70B-Instruct-Q3_K_M` and `Qwen2.5-72B-Instruct-Q3_K_S`~~ --
  **diagnosed and fixed**, a real `render-compose.py` bug (silently
  overrode `n-gpu-layers=auto`), not a RAM/capacity problem. Both now load
  and answer correctly (4.78/4.57 tok/s). See footnote ²³ and "Real
  incident: `parameterise-llama` refactor investigation" below.
- ~~Devstral, real cold/warm benchmark~~ -- **done for all six entries**
  (both quants x three quant levels), see footnote ¹⁷.
- ~~`NVIDIA-Nemotron-3.5-Lightning-30B-A3B-Q4_0`, clean benchmark~~ --
  **done**, 166.62-167.64 tok/s, see footnote ²¹.
- ~~`GLM-4.7-Flash-Q4_K_M`, same gap~~ -- **done**, 103.98-104.16 tok/s,
  see footnote ²².
- ~~`DeepSeek-Coder-V2-Lite-Instruct-Q4_K_M`~~ -- **succeeded** here
  (unlike its single-GPU failure above), 51.20-52.35 tok/s, see footnote
  ¹⁹.
- ~~`Qwen3.8-27B-UD-Q6_K_M` anomaly repeat~~ -- **resolved**, confirmed a
  small-prompt timing artifact, both cards at 98% this time.
- ~~`qwen2.5-coder-7b-instruct-q8_0`/`14b-q5_k_m`/`14b-q6_k` dual-GPU~~ --
  **all three succeeded**, real ~1.65-1.71x speedup over single-GPU, see
  footnote ¹⁶.
- ~~`Qwen3.6-27B-Q6_K`~~ -- **succeeded**, ctx-size projection landed
  within ~50 MiB of the real measurement, see footnote ¹⁵.
- **`gpt-oss-120b` / `GLM-4.5-Air` / `Llama-4-Scout-17B-16E`** -- still not
  curated on this service, excluded from this test run for that reason
  (testing via raw discovery wouldn't exercise `--n-cpu-moe` at all). Real
  GGUF metadata already in hand (`gpt-oss-120b`: 36 layers/128 experts/4
  active/58.44 GiB; `GLM-4.5-Air`: 47 layers/128/8/63.07 GiB;
  `Llama-4-Scout`: 48 layers/16/**1**/60.87 GiB) -- adding curated
  `n-cpu-moe` entries is the real remaining prerequisite, not a test gap.
- **`Qwen3.8-Flash-Next-UD-Q3_K_XL` on the plain 32GB service** -- same
  situation, not curated, not tested this round.

### `llama-cpp-cpu` -- 2/2 attempted, both succeeded (but dramatically slow)

- ~~Devstral, both quants~~ -- **done**, real result far worse than
  predicted: 2.69-2.76 tok/s decode, not the "10.42-10.43 tok/s adjusted
  for size" this document predicted before testing. See footnote ¹⁸ for
  the real architectural reason (dense vs. MoE sparsity) and the practical
  conclusion: **CPU is not viable for these models in agentic use**,
  despite technically working.

### `llama-cpp-generel-schwerz-32gb` -- out of scope this pass

- **The grouped-multigpu cache's real decode benefit** -- still no clean
  number; still the same real path to resolution (`--experimental-logs
  --verbosity 4`, `Ornith-1.5-35B-A3B` as the priority retest) whenever
  this service is revisited. Intentionally excluded from today's run at
  the user's request, not resolved.

### Outstanding questions about MoE performance -- one resolved, two open, one reframed

13. ~~Does dual-GPU placement help a *fully GPU-resident* MoE model the way
    it helps dense models?~~ -- **Resolved earlier this session**:
    `gpt-oss-20b-F16` real single-vs-dual numbers (63.76 -> 141+ tok/s)
    already answered this for tensor-split. Today's `DeepSeek-Coder-V2-
    Lite-Instruct-Q4_K_M` test was meant to answer the *layer-split*
    version of this same question -- but the real result reframes the
    question entirely: layer-split single-GPU didn't just underperform,
    it **failed to load at all** (footnote ¹⁹). So the real finding isn't
    a bandwidth comparison, it's that this specific model/config combination
    has a hard single-GPU placement problem, cause not yet confirmed.
14. ~~Does dual-GPU placement help an `n-cpu-moe`-*offloaded* model?~~ --
    **Resolved 2026-09-19.** Yes, substantially -- and not just for
    Ornith, the answer generalizes across all seven `n-cpu-moe`-offloaded
    30-35B models in the fleet (all fit fully GPU-resident, no offload,
    18-21 GiB weight-only). Real speedup range 1.6x-2.3x over the
    single-GPU `n-cpu-moe`-offloaded figure; Ornith itself went
    65.11-66.52 -> 122.96-123.21 tok/s. See the main table (footnote ²⁵)
    for all seven real cold/warm pairs.
15. **Does schwerz's `moe-cache` actually outperform plain `--n-cpu-moe`
    for the same large (>32 GiB) model? -- Still genuinely untested.**
    Blocked on the same prerequisite as the `gpt-oss-120b` test above --
    needs a curated `n-cpu-moe` entry on a plain service before the real
    comparison against its existing 16GB-schwerz figures
    (8.11-8.80 tok/s) can happen.

### Quant-ladder check: are the underutilized dual-GPU entries missing a
### better download, or is the current quant already the right choice?

Checked at the user's request -- several dual-GPU entries leave real
headroom per card (`Qwen3.8-27B-UD-IQ3_S`: 9.1/9.2 GiB used of 16.3 GiB;
`Qwen3.8-27B-UD-Q3_K_XL`: 9.6/9.7 GiB; both Devstral quants: 12.8/12.9
GiB). Real research against each model's actual published quant ladder,
not assumed:

- **`gpt-oss-20b-F16`** -- no higher quant exists to move to. `F16` is
  already this model's ceiling (its MXFP4-native experts aren't
  re-quantized upward by going to F16; there's nothing above it in the
  published ladder).
- **`Qwen3.8-27B` family** -- not actually a "missing download" case. The
  real quant ladder (unsloth's Dynamic v3.0 release) runs UD-IQ1_S (6.2
  GB) through UD-Q2_K_XL (10.7 GB), Q4_K_M (~17 GB), Q5_K_M, Q6_K_M
  (already all three downloaded and curated), then jumps straight to
  UD-Q8_K_XL (~29-31.5 GB) and BF16 (~54.7 GB) -- both far too large to
  fit this host's 31.85 GiB combined VRAM with any real KV/context
  headroom. The real fix for `IQ3_S`/`Q3_K_XL`'s underutilization on
  *this* service isn't a new download -- `Q4_K_M`/`Q5_K_M`/`Q6_K_M`
  already exist, are already curated and tested here, and use the
  available headroom far better for meaningfully better quality. The
  3-bit quants only earn their place on `llama-cpp-gpu-0`/`gpu-1`, where
  they're the smallest quants that still fit solo on one card -- keeping
  them on the 32GB service too is arguably just redundant with the better
  quants already there.
- **Devstral** -- checked the real published ladder (`Q2_K` 8.89 GiB,
  `IQ4_XS` 12.8 GiB, `IQ4_NL` 13.5 GiB, `Q4_K_M` 13.35 GiB (downloaded),
  `UD-Q8_K_XL` ~27 GiB, `BF16` ~44 GiB) -- no `Q5_K_M`/`Q6_K_M` confirmed
  to exist in this release's ladder. Same gap pattern as `Qwen3.8-27B`:
  the next real step up (`UD-Q8_K_XL`) is roughly double the current
  file, and wouldn't fit in the ~6.5-6.8 GiB combined headroom this pair
  currently has at `ctx-size=131072` without a substantial context cut.
  No clean win available here either -- flagging the real tradeoff
  (meaningfully lower context for meaningfully higher quality) rather
  than picking one for you.

### Anomalies

- ~~`Qwen3.6-35B-A3B-Q4_K_M`'s cold-run slowdown~~ -- **resolved
  2026-09-18**, repeat run confirmed a one-off slow load, see footnote
  ¹³.
- ~~`Qwen3.8-27B-UD-Q6_K_M`'s asymmetric cold-run GPU utilization~~ --
  **resolved 2026-09-18**, repeat run showed both cards at 98%, confirmed
  a small-prompt timing artifact.
- **`Qwen3-Coder-Next`'s 59% vs. 12% asymmetry on 32GB-schwerz** -- still
  open, out of scope this pass (32GB-schwerz excluded). Real path to
  resolution unchanged: `--experimental-logs --verbosity 4`, above.

~~CPU-only decode rates~~ -- resolved 2026-09-17, see the "CPU-only"
section above.

## Still open (noticed, not explained)

Both entries here are also listed under "Anomalies worth a repeat run" in
the test plan above, since resolving them is now a scheduled test, not
just an open observation:

- Qwen3-Coder-Next's 59% vs 12% GPU utilization asymmetry between two
  identical RTX 5060 Tis on the 32GB service. Could be genuine grouped-layer
  imbalance, could be an artifact of the memory pressure it was also under.
  Not resolved -- needs the experimental-logs telemetry, not another
  utilization snapshot.
- Qwen3.8-27B-UD-Q6_K_M's asymmetric cold-run GPU utilization on
  `llama-cpp-all-gpus` (GPU 1 at 0% while GPU 0 ran the small prefill at
  98%, resolved by the warm run) -- plausibly a small-prompt timing
  artifact, not confirmed.

## Full 64K context-floor sweep + DeepSeek-Coder-V2-Lite migration (2026-09-18)

User request: treat 64K (65536) as the coding-use context floor across
every curated model, migrate anything that no longer fits one 16 GiB
card at that floor to the 32GB service, and separately move
`DeepSeek-Coder-V2-Lite-Instruct-Q4_K_M` off `llama-cpp-16gb` entirely
(one card was never comfortable for it) onto `llama-cpp-32gb` with its
real native context ceiling.

### DeepSeek-Coder-V2-Lite-Instruct-Q4_K_M

Removed from `llama-cpp-16gb` (real single-card testing this session
already found 65536 fails outright and 32768 was the safe fallback --
below the 64K floor). Raised on `llama-cpp-32gb` from 65536 to **163840**,
this model's real native context ceiling (`deepseek2` architecture,
`context_length=163840` per GGUF metadata). Real load test confirmed it
fits: 14,751/16,311 MiB (GPU0) and 14,832/16,311 MiB (GPU1), ~1.5 GiB
headroom per card.

Quant ladder researched (bartowski, via the HF API tree endpoint) --
current `Q4_K_M` is 9.65 GiB; real higher quants exist: `Q5_K_M` 11.85 GB,
`Q6_K` 14.07 GB, `Q8_0` 16.70 GB. **Recommendation: `Q8_0`** -- near-
lossless and comfortably within this service's real headroom (the prior
65536-context footprint left 12+ GiB free combined). Not yet downloaded
or switched -- still `Q4_K_M` as of this note.

### 5 CPU models raised to 65536

`gemma-3n-E2B-it`, `gemma-3n-E4B-it`, `NVIDIA-Nemotron-3-Nano-4B`,
`Qwen3.5-9B`, `Ornith-1.5-9B` on `llama-cpp-cpu`, raised from 32768. All
five real-load-tested individually with live `free -h` monitoring
throughout each load: RAM available never dropped below 52 GiB, swap
stayed flat at its pre-existing 3.9-4.1 GiB baseline (unrelated residual
from prior sessions, not caused by these loads). No near-miss, unlike
the earlier DeepSeek-70B CPU incident this document already records.

### Full 64K sweep results -- every candidate fits, zero migrations needed

Every remaining model below 65536 across all three services was raised
and real-load-tested (chat completion request + `nvidia-smi`/`free -h`
check). **Every single one fit with real headroom -- no model needed to
move from `llama-cpp-16gb` to `llama-cpp-32gb`.**

`llama-cpp-16gb` (single 16.3 GiB card, tested via `llama-cpp-gpu-0`),
32768/16384 -> 65536:

| Model | VRAM used | Headroom |
|---|---|---|
| qwen2.5-coder-7b-instruct-q4_k_m | 6.46 GiB | ~9.8 GiB |
| qwen2.5-coder-14b-instruct-q4_k_m | 14.75 GiB | ~1.5 GiB |
| qwen2.5-coder-7b-instruct-q8_0 | 9.46 GiB | ~6.8 GiB |
| qwen2.5-coder-14b-instruct-q5_k_m | 14.77 GiB | ~1.5 GiB |
| qwen2.5-coder-14b-instruct-q6_k | 14.65 GiB | ~1.7 GiB |
| Qwen3-Coder-30B-A3B-Instruct-Q4_K_M | 14.91 GiB | ~1.4 GiB |
| Qwen3.6-35B-A3B-Q4_K_M | 12.59 GiB | ~3.7 GiB |
| Qwen3.5-35B-A3B-Q4_K_M | 12.61 GiB | ~3.7 GiB |
| Ornith-1.5-35B-Q4_K_M | 12.09 GiB | ~4.2 GiB |
| NVIDIA-Nemotron-3.5-Lightning-...-Expert-Offload | 13.09 GiB | ~3.2 GiB |
| Laguna-XS-2.1-...-Expert-Offload | 14.30 GiB | ~2.0 GiB |
| North-Mini-Code-1.0-...-Expert-Offload | 14.07 GiB | ~2.2 GiB |
| granite-4.0-h-small-...-Expert-Offload | 14.10 GiB | ~2.2 GiB |

None of the 8 `n-cpu-moe`/Expert-Offload models needed their `n-cpu-moe`
value raised to keep fitting at 65536 -- real headroom absorbed the
larger KV cache at every one without adjustment. (`Qwen3.8-27B-UD-Q3_K_XL`
was already exactly at 65536 from earlier work this session; not
retested here.)

`llama-cpp-32gb` (dual 16.3 GiB cards, tested via `llama-cpp-all-gpus`),
8192/32768 -> 65536:

| Model | GPU0 | GPU1 |
|---|---|---|
| qwen2.5-coder-7b-instruct-q8_0 | 5.07 GiB | 5.15 GiB |
| qwen2.5-coder-14b-instruct-q5_k_m | 8.69 GiB | 8.78 GiB |
| qwen2.5-coder-14b-instruct-q6_k | 9.41 GiB | 9.50 GiB |
| **Llama-3.3-70B-Instruct-Q3_K_M** | 14.48 GiB | 14.64 GiB |
| **Qwen2.5-72B-Instruct-Q3_K_S** | 14.45 GiB | 14.83 GiB |

The two 70B-class dense models (partial CPU offload, `n-gpu-layers=auto`)
were the real risk case here, given this document's existing DeepSeek-70B
near-miss precedent. Both were tested individually with live `free -h`
polling every 8s through the full load+generate cycle: RAM available
bottomed out at 2.2 GiB free (Llama-3.3-70B) and 629 MiB free
(Qwen2.5-72B) mid-load before settling back up as loading completed --
real pressure, but no swap growth beyond the pre-existing 3.9-4.1 GiB
baseline, and no OOM. Both now sit at 65536, up from 8192, and stay on
`llama-cpp-32gb` (never fit one 16 GiB card to begin with, so no
migration question applied to them).

### Tooling: `generate-models-preset.py` full-discovery mode still broken

Confirmed again this session -- `llama-cpp-32gb`'s repo-source preset
edits (the two 70B `ctx-size` bumps, the three `qwen2.5-coder` dual-GPU
bumps) were deployed to `/mnt/work/llama/llama-cpp-32gb/models-preset.ini`
by direct `sed` patch, not `generate-models-preset.py --force`, because
that tool's full-discovery mode still targets the now-removed
`llama-cpp-all-gpus` compose service (see the `render-compose.py`
refactor investigation earlier in this document). Not fixed -- flagged
again as the same known gap.

### Also noticed, not fixed: stale DSH entries under the `llama-cpp` (32gb) provider

`settings.yaml`'s `llama-cpp` provider block lists
`qwen2.5-coder-7b-instruct-q4_k_m`, `qwen2.5-coder-14b-instruct-q4_k_m`,
`Qwen3-Coder-Next-Q4_K_M`, and `Qwen3-Next-80B-A3B-Instruct-Q4_K_M` --
none of the four appear as explicit sections in
`llama-cpp-32gb/models-preset.ini` (confirmed by grep). The latter two
are real CPU-only MoE models correctly declared on `llama-cpp-cpu`
instead (per that file's own header comment), so their presence here
looks like leftover drift, not a real route -- unverified whether the
32gb service's full-discovery mode happens to expose them anyway. Not
investigated further this session (out of scope for this pass); worth a
follow-up if `llama-cpp` (32gb) is ever used as a route for these models.

## 128K assessment, YaRN correctness fix, Q8 DeepSeek-Coder-V2-Lite, tooling fix (2026-09-19)

### Real native-context finding: qwen2.5-coder family and Qwen2.5-72B were running past their trained window unscaled

The GGUF's own `context_length` metadata for the qwen2.5-coder quants reports
131072 -- **not authoritative**. Confirmed via the real upstream HF
`config.json` (Qwen2.5-Coder-14B-Instruct): `max_position_embeddings=32768`,
no `rope_scaling` block. `Qwen2.5-72B-Instruct-Q3_K_S`'s own GGUF metadata
independently confirms the same real 32768 native window
(`qwen2.context_length=32768`, no `rope.scaling.*` fields). Both had been
running at 65536 (2x native) with no `rope-scaling` configured -- the load
tests that passed only ever sent trivial short prompts, which say nothing
about coherence once real usage passes position 32768.

Contrast: `Llama-3.3-70B-Instruct-Q3_K_M`'s own GGUF metadata genuinely
reports `context_length=131072` -- real Llama-3.1+ native long-context
training, not extrapolated. No fix needed there.

**Fix applied**: `rope-scaling = yarn` + `yarn-orig-ctx = 32768` added
explicitly to every qwen2.5-coder entry (both `llama-cpp-16gb` and
`llama-cpp-32gb`) and to `Qwen2.5-72B-Instruct-Q3_K_S`. **Verified with a
real needle-in-haystack test**, not just a load check: a 42,777-token
prompt (30% past the 32768 native boundary) with a fact planted near the
start correctly retrieved the fact at the end
(`qwen2.5-coder-14b-instruct-q4_k_m`, temperature 0). Real evidence the
YaRN fix works, not an assumption.

Not yet independently re-verified at the deeper 4x-native extrapolation
depth now in use (131072, see below) -- the needle test only covered 1.3x.
Worth a repeat at the new depth if this matters for real long-context use
of this specific model family.

### 128K assessment: every 64K-capped model tested, only two needed adjustment, none needed to migrate

User's question: would raising 64K-capped models to 131072 (their new
preferred default) push any of them from one 16 GiB card to needing both.
**Answer: no** -- every single model tested fits solo where it already ran
solo. Real per-model results:

`llama-cpp-16gb` (tested via `llama-cpp-gpu-0`), 65536 -> 131072:

| Model | Fit | VRAM used | Headroom | Notes |
|---|---|---|---|---|
| qwen2.5-coder-7b-instruct-q4_k_m | yes | 8.56 GiB | ~7.7 GiB | |
| qwen2.5-coder-14b-instruct-q4_k_m | yes | 14.60 GiB | ~1.7 GiB | |
| qwen2.5-coder-7b-instruct-q8_0 | yes | 11.56 GiB | ~4.6 GiB | |
| qwen2.5-coder-14b-instruct-q5_k_m | yes | 14.55 GiB | ~1.7 GiB | |
| qwen2.5-coder-14b-instruct-q6_k | yes | 14.42 GiB | ~1.8 GiB | |
| Qwen3.8-27B-UD-Q3_K_XL | yes | 14.61 GiB | ~1.7 GiB | |
| Qwen3-Coder-30B-A3B-Instruct-Q4_K_M | yes, after adjustment | 15.65 GiB | ~0.64 GiB | first attempt CUDA OOM at n-cpu-moe=18; raised to 26 -- fits but very tight |
| Qwen3.6-35B-A3B-Q4_K_M | yes | 13.38 GiB | ~2.9 GiB | |
| Qwen3.5-35B-A3B-Q4_K_M | yes | 13.44 GiB | ~2.9 GiB | |
| Ornith-1.5-35B-Q4_K_M | yes | 12.89 GiB | ~3.4 GiB | |
| NVIDIA-Nemotron-3.5-Lightning-...-Expert-Offload | yes | 13.36 GiB | ~2.9 GiB | |
| Laguna-XS-2.1-...-Expert-Offload | yes, after adjustment | 13.25 GiB | ~3.1 GiB | first attempt CUDA OOM at n-cpu-moe=16; raised to 22 |
| North-Mini-Code-1.0-...-Expert-Offload | yes | 15.14 GiB | ~1.16 GiB | tight |
| granite-4.0-h-small-...-Expert-Offload | yes | 14.97 GiB | ~1.3 GiB | tight |

`llama-cpp-32gb` (tested via `llama-cpp-all-gpus`), 65536 -> 131072:

| Model | GPU0 | GPU1 |
|---|---|---|
| qwen2.5-coder-7b-instruct-q8_0 | 6.21 GiB | 6.29 GiB |
| qwen2.5-coder-14b-instruct-q5_k_m | 12.28 GiB | 12.36 GiB |
| qwen2.5-coder-14b-instruct-q6_k | 13.00 GiB | 13.08 GiB |
| Llama-3.3-70B-Instruct-Q3_K_M | 14.56 GiB | 14.38 GiB |
| Qwen2.5-72B-Instruct-Q3_K_S | 14.45 GiB | 14.56 GiB |

Both 70B dense models were already dual-GPU only (never fit one 16 GiB
card), so "push to both GPUs" didn't apply to them -- tested anyway with
live `free -h` polling every 8s through the full load, matching this
document's established near-miss precedent. RAM stayed stable at both
65536 and 131072 (no swap growth beyond the pre-existing baseline).

**These changes are now the deployed defaults** (both preset files and
DSH `settings.yaml` updated and synced) -- not left as an untested
proposal, since every candidate passed.

### Two 70B dense models: real case against keeping them

User asked for the practical value of `Llama-3.3-70B-Instruct-Q3_K_M` and
`Qwen2.5-72B-Instruct-Q3_K_S` given this hardware. Real decode figures from
this session's own tests: **2.09-2.75 tok/s** (Llama-3.3-70B),
**2.14-2.57 tok/s** (Qwen2.5-72B) -- both `n-gpu-layers=auto` (partial CPU
offload), since neither fits 32 GiB combined VRAM with real margin at any
useful context. This is a structural hardware bottleneck (host RAM/PCIe
transfer on every token for the CPU-resident layers), not a config or
quantization problem. By contrast, the fleet's MoE models of similar or
larger total size (Qwen3.6-35B-A3B, Ornith-1.5-35B, Laguna-XS-2.1,
NVIDIA-Nemotron-3.5-Lightning) only activate a few billion parameters per
token and run at GPU-native speeds, an order of magnitude faster.
Recommendation given, not yet acted on: no clear case remains for keeping
either dense 70B model on this hardware for interactive/agentic use.

### Q8_0 quant of DeepSeek-Coder-V2-Lite-Instruct: downloaded, curated, tested

Downloaded via `hf download bartowski/DeepSeek-Coder-V2-Lite-Instruct-GGUF
--include "DeepSeek-Coder-V2-Lite-Instruct-Q8_0.gguf"` (16.70 GB, matches
the size predicted from the HF API tree listing exactly). Added as a new
`DeepSeek-Coder-V2-Lite-Instruct-Q8_0` entry on `llama-cpp-32gb` alongside
the existing `Q4_K_M` entry (kept, not replaced -- DSH `settings.yaml`
still points at the `Q4_K_M` id specifically; switching is the user's call).

Real GGUF metadata confirms this model's YaRN scaling is genuinely baked
in (`deepseek2.rope.scaling.type`/`factor=40.0`/
`original_context_length=4096`, 4096*40=163840 matching
`context_length` exactly) -- unlike the qwen2.5-coder finding above, no
manual `rope-scaling`/`yarn-orig-ctx` override was needed here.

Real load test at `ctx-size=163840`: 14,727/16,311 MiB (GPU0) and
14,720/16,311 MiB (GPU1) -- ~1.55 GiB headroom per card, essentially
identical to the `Q4_K_M` entry's footprint despite the 1.73x larger file
(KV cache at this context size dominates VRAM usage more than the weight
quant difference, at this model's small total size). A simple coding
prompt (memoized Fibonacci) produced near-identical, both-correct output
from both quants -- expected for a trivial task, not a meaningful quality
differentiator; a harder real task would be needed to show the quality
gap Q8_0 is expected to close.

### Tooling: `generate-models-preset.py` full-discovery mode fixed

Root cause found: the `render-compose.py` refactor consolidated the old
dedicated `llama-cpp-all-gpus` discovery service into the plain `llama-cpp`
template service in `compose.ai.yml` (the same one every profile renders
FROM) -- it already reads the exact `LLAMA_CPP_MODELS`/
`LLAMA_CPP_32GB_CONFIG` env vars `discover_models()` sets, just under a
different service name. Fixed with a two-line change: `COMPOSE_FILE` now
points at `compose.ai.yml` directly (not the six-file `docker-compose.yml`
includes-file), and the service name in the `docker compose run` command
changed from `llama-cpp-all-gpus` to `llama-cpp`. **Verified working**:
a real `--force` (non-`--preset-only`) run against `llama-cpp-32gb`
discovered 28 models and wrote the preset correctly, no more manual `sed`
patching needed going forward.

### DSH `settings.yaml` cleanup

Removed four dead entries under the `llama-cpp` (32gb) provider block that
referenced model IDs unreachable on that service (confirmed against a real
full-discovery listing): `qwen2.5-coder-7b-instruct-q4_k_m`,
`qwen2.5-coder-14b-instruct-q4_k_m` (only exist as curated entries on
`llama-cpp-16gb`), `Qwen3-Coder-Next-Q4_K_M`,
`Qwen3-Next-80B-A3B-Instruct-Q4_K_M` (genuinely CPU-only, real homes are
`llama-cpp-cpu` and the 16GB schwerz service). Also found and fixed the
inverse gap: `qwen2.5-coder-7b-instruct-q4_k_m`/`-14b-instruct-q4_k_m` are
real, working entries on `llama-cpp-16gb`'s own preset (confirmed via live
load) but had no DSH route on `llama-cpp-gpu-0`/`llama-cpp-gpu-1` at all --
added. All `contextWindow` values updated to match today's 128K changes.
Synced via `sync-config.py`.

## Two 70B dense models removed (2026-09-19)

`Llama-3.3-70B-Instruct-Q3_K_M` and `Qwen2.5-72B-Instruct-Q3_K_S` removed
entirely -- entries deleted from `llama-cpp-32gb/models-preset.ini` (repo
source and deployed), weight files deleted from disk (~64 GiB freed),
`settings.yaml` entries removed and synced. Rationale (from this session's
own real measurements): 2.09-2.75 tok/s and 2.14-2.57 tok/s decode
respectively, both `n-gpu-layers=auto` (partial CPU offload) -- neither
fits 32 GiB combined VRAM with real margin at any useful context, so every
token touches host RAM/PCIe transfer, a structural bottleneck this hardware
can't quantize its way out of. An order of magnitude slower than the
fleet's MoE models of similar or larger total size. No migration needed --
this is a deletion, not a move.
