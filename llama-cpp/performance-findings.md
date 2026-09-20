# Local llama.cpp performance findings

Durable record of real performance measurements across the local llama.cpp
deployments (`llama-cpp-all-gpus`, the GenerelSchwerz MoE-cache forks, and
standalone comparison runs) and the conclusions they support. Host: 2x RTX
5060 Ti (16 GiB each, no peer access -- `nvidia-smi topo -p2p r` reports
`CNS`), 60 GiB system RAM, 8 GiB swap.

Distinguish a *measured* result (real load, real request) from an
*estimate* (parameter-count or published-config derived) -- both appear
below, never presented as the same kind of evidence.

## Service roles

- **`llama-cpp-cpu`** (no GPU passthrough). Two real use cases: (a) small
  dense chat models, comfortably under 10 GiB (`gemma-3n-E2B-it`,
  `gemma-3n-E4B-it`, `NVIDIA-Nemotron-3-Nano-4B`, `Qwen3.5-9B`,
  `Ornith-1.5-9B`); (b) MoE models too large to fit 32 GiB combined VRAM
  even with `n-cpu-moe`/tensor-split, where sparse-expert CPU decode is
  still genuinely usable (`Qwen3-Coder-Next`, `Qwen3-Next-80B-A3B-Instruct`,
  ~45 GiB each, 9-13 tok/s -- a real working option, not a last resort).
  `Devstral-Small` is here for a different reason: dense, not oversized,
  but single-GPU placement couldn't give it a useful context, and CPU is
  the RAM-unconstrained alternative to dual-GPU tensor-split for that.
- **`llama-cpp-gpu-0` / `llama-cpp-gpu-1`** ("the 16GB service" -- one
  physical GPU each via Docker's `gpus.device_ids`; shared preset
  `llama-cpp-16gb`). Single-card placement for models either small/dense
  enough to sit fully GPU-resident, or MoE models 17-20 GiB needing
  `n-cpu-moe` partial offload to fit one card. Not used for models needing
  dual-GPU bandwidth-doubling or too large even with offload -- those go
  on `llama-cpp-all-gpus`.
- **`llama-cpp-all-gpus`** ("the 32GB service", `gpus: all`, keeps the
  `llama-cpp` DSH-compatibility alias). Two distinct reasons a model lands
  here: (a) too large for one card even with offload (dense 70B-class,
  full dense Qwen3.8-27B ladder); (b) a deliberate choice to force smaller
  models onto both GPUs via `split-mode=tensor`, because dense decode at
  batch=1 is memory-bandwidth-bound and splitting roughly doubles
  effective bandwidth -- confirmed for several dense models (`gpt-oss-20b-F16`
  63.76 -> 141+ tok/s; Qwen3.8-27B 3-bit quants ~28-30 -> 45-47 tok/s).
  Evidenced for dense architectures specifically; untested and not assumed
  to transfer to MoE models (sparse activation, different bandwidth
  profile). **Real tension**: forcing a small model onto both GPUs for a
  per-job speed win trades away concurrency -- it occupies the whole
  host's GPU capacity for one job, where the same model on a single
  `gpu-0`/`gpu-1` card leaves the other free for a second job.
  `qwen2.5-coder-7b-instruct-q8_0` single-GPU (52.91-53.06 tok/s) vs.
  forced dual-GPU (90.27-90.62 tok/s) is a ~1.7x speedup for one job, but
  running it single-GPU on each card simultaneously gets two independent
  ~53 tok/s jobs at once -- more aggregate throughput and concurrency, if
  the goal is several simultaneous sessions rather than one fast one.
- **`llama-cpp-generel-schwerz-16gb` / `-gpu-0`/`-gpu-1`** (fork, single
  physical GPU, `moe-cache` expert-caching layered on the same mmap/lazy
  loading the plain services already have by default). Role: last resort
  for MoE models too large for the plain 32 GiB dual-GPU split. Got a real
  tuning pass for `Qwen3.8-Flash-Next` only (+125% prefill/+9% decode from
  batch/ubatch tuning). Known failure mode: `Llama-4-Scout` and
  `GLM-4.5-Air` hit a genuine CUDA OOM in `moe-cache`'s own graph-compute
  buffer, not yet root-caused. **Must run on physical GPU 1, not GPU 0**:
  the two cards are not symmetric (GPU 0: PCIe Gen3 x4; GPU 1: PCIe Gen4
  x8), and `moe-expert-cache-size`'s constant host-to-GPU streaming is
  PCIe-bandwidth-bound -- Flash Next drops from 18.87 tok/s (GPU 1) to
  6.34-6.6 tok/s (GPU 0) for the identical config, a ~3x regression from
  card choice alone.
- **`llama-cpp-generel-schwerz-32gb`** (fork, `codex/moe-grouped-multigpu`).
  Not viable for large models on this host: its `load-mode=none`
  requirement disables mmap, so any model exceeding physical RAM
  (`gpt-oss-120b`, `GLM-4.5-Air`, both real failures) has no fallback but
  swap -- disk-I/O-speed decode (2-3 tok/s), not real model performance.
  No established positive role yet.
- **`llama-cpp-csantiago78`** -- another fork variant referenced in DSH
  `settings.yaml`. Not characterized by testing; no established role.

## Resource usage by model/service (summary table)

One row per model/service combination actually run. GPU columns are VRAM
allocated by the model process; RAM is `free -h` **used** (non-reclaimable);
CPU is whether it's doing inference compute or just orchestration. "Not
exposed" = the container architecturally cannot see that GPU (`llama-cpp-cpu`
has no `gpus:` passthrough); "not used" = visible but untouched.

| Model | Service | GPU 1 | GPU 2 | RAM | CPU | Prefill | Decode | Long-context / agent decode |
|---|---|---|---|---|---|---|---|---|
| DeepSeek-Coder-V2-Lite-Instruct-Q4_K_M | `llama-cpp-all-gpus` (MoE, forced dual-GPU layer-split) | 10.6 GiB | 9.1 GiB | baseline only | idle | 170.51 tok/s | 51.20 tok/s cold, 52.35 tok/s warm | 8,253-token prompt: 58.89 / 3.37 tok/s⁵ |
| DeepSeek-Coder-V2-Lite-Instruct-Q4_K_M | `llama-cpp-gpu-1` (MoE, single physical GPU, `ctx-size=32768`) | 14.3 GiB | not exposed | baseline only | idle | 168.44 tok/s | -- (load-confirmed only) | not in current 16GB preset |
| Devstral-Small-2-24B-Instruct-2512-Q4_K_M | CPU-only (`llama-cpp-cpu`)² | not exposed | not exposed | baseline only | **compute (8 threads)** | 15.998 tok/s | 2.76 tok/s cold, 2.76 tok/s warm |
| Devstral-Small-2-24B-Instruct-2512-Q4_K_M | `llama-cpp-all-gpus` (dense, forced dual-GPU tensor-split) | 12.8 GiB | 12.9 GiB | baseline only | idle | 784.07 tok/s | 42.49 tok/s cold, 42.53 tok/s warm | 8,799-token prompt: 1,035.86 / 38.92 tok/s⁵ |
| Devstral-Small-2-24B-Instruct-2512-Q5_K_M | `llama-cpp-all-gpus` (dense, forced dual-GPU tensor-split) | 13.9 GiB | 14.0 GiB | baseline only | idle | 981.03 tok/s | 39.44 tok/s cold, 39.53 tok/s warm | 8,799-token prompt: 1,021.85 / 36.95 tok/s⁵ |
| Devstral-Small-2-24B-Instruct-2512-Q6_K | `llama-cpp-all-gpus` (dense, forced dual-GPU tensor-split) | 15.1 GiB | 15.1 GiB | baseline only | idle | 913.35 tok/s | 33.97 tok/s cold, 35.22 tok/s warm | 8,799-token prompt: 946.79 / 33.15 tok/s⁵ |
| Devstral-Small-2505-Q4_K_M | CPU-only (`llama-cpp-cpu`)² | not exposed | not exposed | baseline only | **compute (8 threads)** | 15.316 tok/s | 2.69 tok/s cold, 2.69 tok/s warm |
| Devstral-Small-2505-Q4_K_M | `llama-cpp-all-gpus` (dense, forced dual-GPU tensor-split) | 12.8 GiB | 12.9 GiB | baseline only | idle | 1,040.28 tok/s | 47.02 tok/s cold, 47.06 tok/s warm | 9,469-token prompt: 1,040.34 / 43.42 tok/s⁵ |
| Devstral-Small-2505-Q5_K_M | `llama-cpp-all-gpus` (dense, forced dual-GPU tensor-split) | 13.9 GiB | 14.0 GiB | baseline only | idle | 1,020.88 tok/s | 43.14 tok/s cold, 43.30 tok/s warm | 9,469-token prompt: 1,022.05 / 40.26 tok/s⁵ |
| Devstral-Small-2505-Q6_K | `llama-cpp-all-gpus` (dense, forced dual-GPU tensor-split) | 15.1 GiB | 15.1 GiB | baseline only | idle | 950.21 tok/s | 37.26 tok/s cold, 38.13 tok/s warm | 9,469-token prompt: 945.72 / 35.90 tok/s⁵ |
| gemma-3n-E2B-it-Q4_K_M | CPU-only (`llama-cpp-cpu`) | not exposed | not exposed | 5.1 GiB | **compute (8 threads)** | 145.26 tok/s | 21.72-21.85 tok/s | 4,160-token prompt: 124.22 / 20.65 tok/s⁵ |
| gemma-3n-E2B-it-Q4_K_M | `llama-cpp-all-gpus` (dense, dual-GPU layer-split) | 1.7 GiB | 1.9 GiB | baseline only | idle | 1,116.95 tok/s | 134.78 tok/s cold, 134.84 tok/s warm | 4,160-token prompt: 3,396.70 / 132.66 tok/s⁵ |
| gemma-3n-E2B-it-Q4_K_M | `llama-cpp-gpu-1` (dense, single physical GPU) | 2.2 GiB | not exposed | baseline only | idle | 1,249.85 tok/s | 148.15 tok/s cold, 148.50 tok/s warm | 4,160-token prompt: 4,795.69 / 145.96 tok/s⁵ |
| gemma-3n-E4B-it-Q4_K_M | CPU-only (`llama-cpp-cpu`) | not exposed | not exposed | 6.0 GiB | **compute (8 threads)** | 77.51 tok/s | 12.72-12.73 tok/s | 4,160-token prompt: 68.52 / 12.23 tok/s⁵ |
| gemma-3n-E4B-it-Q4_K_M | `llama-cpp-all-gpus` (dense, dual-GPU layer-split) | 2.4 GiB | 2.5 GiB | baseline only | idle | 855.86 tok/s | 76.35 tok/s cold, 76.40 tok/s warm | 4,160-token prompt: 2,531.15 / 60.22 tok/s⁵ |
| gemma-3n-E4B-it-Q4_K_M | `llama-cpp-gpu-1` (dense, single physical GPU) | 3.4 GiB | not exposed | baseline only | idle | 914.06 tok/s | 97.65 tok/s cold, 97.80 tok/s warm | 4,160-token prompt: 2,881.20 / 96.51 tok/s⁵ |
| GLM-4.5-Air | 16GB schwerz (`cache-type-k/v=q4_0` fix, 2026-09-20) | not measured | not exposed | not measured | idle | 125.15 tok/s | -- (load-confirmed only) | 8,311-token prompt: 125.15 / 3.12 tok/s⁵ |
| GLM-4.5-Air | 32GB schwerz (grouped-multigpu) | 10.1 GiB | 10.1 GiB | 60/60 GiB (swap-maxed) | some (swap I/O), 0% GPU compute | 1.68 tok/s³ | 1.01-1.39 tok/s³ |
| GLM-4.5-Air-UD-Q4_K_XL | `llama-cpp-gpu-1` (MoE, `n-cpu-moe` offload)⁷ | 11,320 MiB | not exposed | not measured | idle | not measured | 7.15-7.31 tok/s | 49,181-token prompt: not measured / 2.41 tok/s (ctx=131072, `cache-type-k/v=q4_0`) |
| GLM-4.5-Air-UD-Q4_K_XL | `llama-cpp-all-gpus` (MoE, `n-cpu-moe` offload, dual-GPU) | 6,423 MiB | 5,674 MiB | not measured | idle | not measured | 5.73-5.86 tok/s | 49,181-token prompt: not measured / 2.40 tok/s (ctx=131072, `cache-type-k/v=q4_0`) |
| GLM-4.7-Flash-Q4_K_M | `llama-cpp-all-gpus` (MoE, forced dual-GPU layer-split) | 12.8 GiB | 12.2 GiB | baseline only | idle | 279.26 tok/s | 103.98 tok/s cold, 104.16 tok/s warm | 8,247-token prompt: 2,180.16 / 77.74 tok/s⁵ |
| gpt-oss-120b | 16GB schwerz | 7.1 GiB | not exposed | 4.0 GiB + 54 GiB mmap cache | idle | 11.06 tok/s | 8.11-8.80 tok/s | 16,500-token prompt: 470.16 / 9.10 tok/s |
| gpt-oss-120b | 32GB schwerz (grouped-multigpu) | 3.8 GiB | 4.0 GiB | 60/60 GiB (swap-maxed) | some (swap I/O) | 2.20 tok/s³ | 2.36-3.01 tok/s³ |
| gpt-oss-120b-Q4_K_M | `llama-cpp-gpu-1` (MoE, `n-cpu-moe` offload)⁷ | 12,812 MiB (ctx=131072) | not exposed | not measured | idle | 571.84 tok/s | 18.73-20.59 tok/s | 114,779-token prompt: 455.21 / 14.52 tok/s (ctx=131072) |
| gpt-oss-120b-Q4_K_M | `llama-cpp-all-gpus` (MoE, `n-cpu-moe` offload, imbalanced dual-GPU)⁷ | 2,865 MiB | 14,156 MiB (ctx=131072) | not measured | idle | 194.35 tok/s | 14.76-20.16 tok/s | 114,779-token prompt: 199.03 / 14.51 tok/s (ctx=131072) |
| gpt-oss-20b-F16 | CPU-only (`llama-cpp-cpu`) | not exposed | not exposed | 19 GiB | **compute (8 threads)** | 68.06 tok/s | 10.42-10.43 tok/s | not in current CPU preset |
| gpt-oss-20b-F16 | standalone, 1 GPU pinned | ~13.3 GiB | not exposed | baseline only | idle | 3,802 tok/s | 63.76 tok/s |
| gpt-oss-20b-F16 | `llama-cpp-all-gpus` (forced dual-GPU tensor-split) | 7.4 GiB | 7.5 GiB | baseline only | idle | 557.97 tok/s (cold) | 141.38 tok/s cold, 142.33 tok/s warm | 8,308-token prompt: 3,181.87 / 129.36 tok/s⁵ |
| gpt-oss-20b-F16 | `llama-cpp-gpu-1` (MoE, single physical GPU) | 14.1 GiB | not exposed | baseline only | idle | 580.26 tok/s | 94.34 tok/s cold, 94.39 tok/s warm | 8,308-token prompt: 5,530.95 / 84.44 tok/s⁵ |
| granite-4.0-h-small-Q4_K_M | `llama-cpp-all-gpus` (MoE, full GPU-resident, dual-GPU) | 11.5 GiB | 11.0 GiB | baseline only | idle | 85.92 tok/s | 57.28 tok/s cold, 57.32 tok/s warm | 8,272-token prompt: 1,868.29 / 56.07 tok/s⁵ |
| granite-4.0-h-small-Q4_K_M-Expert-Offload | `llama-cpp-gpu-1` (MoE, `n-cpu-moe` offload) | 13.3 GiB | not exposed | baseline only | idle | 92.40 tok/s | 27.16 tok/s cold, 27.49 tok/s warm | 8,272-token prompt: 1,256.08 / 27.28 tok/s⁵ |
| Laguna-XS-2.1-Q4_K_M | `llama-cpp-all-gpus` (MoE, full GPU-resident, dual-GPU) | 12.7 GiB | 12.0 GiB | baseline only | idle | 145.35 tok/s | 128.71 tok/s cold, 128.06 tok/s warm | 8,285-token prompt: 3,273.25 / 104.72 tok/s⁵ |
| Laguna-XS-2.1-Q4_K_M-Expert-Offload | `llama-cpp-gpu-1` (MoE, `n-cpu-moe` offload) | 13.0 GiB | not exposed | baseline only | idle | 144.99 tok/s | 80.42 tok/s cold, 80.56 tok/s warm | 8,285-token prompt: 2,092.61 / 60.94 tok/s⁵ |
| Ling-3.0-flash-Q4_K_M | 16GB schwerz | 5,208 MiB | not exposed | not measured | idle | not measured | 5.68-7.21 tok/s | 49,200-token prompt: not measured / 5.36 tok/s (ctx=131072) |
| Ling-3.0-flash-Q4_K_M | `llama-cpp-gpu-1` (MoE, `n-cpu-moe` offload) | 12,360 MiB | not exposed | not measured | idle | not measured | 11.09-18.36 tok/s | 49,200-token prompt: not measured / 11.12 tok/s (ctx=131072) |
| Ling-3.0-flash-Q4_K_M | `llama-cpp-all-gpus` (MoE, `n-cpu-moe` offload, dual-GPU) | not measured | not measured | not measured | idle | not measured | 11.43-17.17 tok/s | 49,200-token prompt: not measured / 10.53 tok/s (ctx=131072) |
| Llama-4-Scout-17B-16E | 16GB schwerz | **CUDA OOM** | not exposed | -- | -- | failed to load | failed to load | failed to load at 65,536 ctx⁶ |
| Llama-4-Scout-17B-16E-Instruct-Q4_K_M | `llama-cpp-gpu-1` (MoE, `n-cpu-moe` offload) | 12,208 MiB | not exposed | not measured | idle | not measured | 8.42-8.80 tok/s | 49,186-token prompt: not measured / 8.09 tok/s (ctx=131072) |
| Llama-4-Scout-17B-16E-Instruct-Q4_K_M | `llama-cpp-all-gpus` (MoE, `n-cpu-moe` offload, dual-GPU) | 5,221 MiB | 7,576 MiB | not measured | idle | not measured | 7.71-8.03 tok/s | 49,186-token prompt: not measured / 7.57 tok/s (ctx=131072) |
| North-Mini-Code-1.0-UD-Q4_K_M | `llama-cpp-all-gpus` (MoE, full GPU-resident, dual-GPU) | 11.4 GiB | 11.2 GiB | baseline only | idle | 446.31 tok/s | 105.02 tok/s cold, 105.16 tok/s warm | 8,356-token prompt: 5,235.44 / 80.65 tok/s⁵ |
| North-Mini-Code-1.0-UD-Q4_K_M-Expert-Offload | `llama-cpp-gpu-1` (MoE, `n-cpu-moe` offload) | 13.0 GiB | not exposed | baseline only | idle | 147.28 tok/s | 55.45 tok/s cold, 55.41 tok/s warm | 8,356-token prompt: 2,022.82 / 47.78 tok/s⁵ |
| NVIDIA-Nemotron-3-Nano-4B-Q4_K_M | CPU-only (`llama-cpp-cpu`) | not exposed | not exposed | 4.5-4.8 GiB | **compute (8 threads)** | 55.47 tok/s | 12.67-12.71 tok/s | 8,261-token prompt: 49.28 / 10.54 tok/s⁵ |
| NVIDIA-Nemotron-3-Nano-4B-Q4_K_M | `llama-cpp-all-gpus` (dense, dual-GPU layer-split) | 2.2 GiB | 2.6 GiB | baseline only | idle | 551.39 tok/s | 125.61 tok/s cold, 125.73 tok/s warm | 8,261-token prompt: 4,951.84 / 118.90 tok/s⁵ |
| NVIDIA-Nemotron-3-Nano-4B-Q4_K_M | `llama-cpp-gpu-1` (dense, single physical GPU) | 3.7 GiB | not exposed | baseline only | idle | 424.58 tok/s | 127.61 tok/s cold, 127.70 tok/s warm | 8,261-token prompt: 4,848.14 / 120.59 tok/s⁵ |
| NVIDIA-Nemotron-3.5-Lightning-30B-A3B-Q4_0 | `llama-cpp-all-gpus` (MoE, dual-GPU, MTP speculative decode) | 10.3 GiB | 13.3 GiB | baseline only | idle | 275.30 tok/s | 166.62 tok/s cold, 167.64 tok/s warm | 8,260-token prompt: 3,774.70 / 199.36 tok/s⁵ |
| NVIDIA-Nemotron-3.5-Lightning-30B-A3B-Q4_0-Expert-Offload | `llama-cpp-gpu-1` (MoE, `n-cpu-moe` offload) | 12.7 GiB | not exposed | baseline only | idle | 122.90 tok/s | 69.32 tok/s cold, 69.59 tok/s warm | 8,260-token prompt: 2,954.65 / 66.43 tok/s⁵ |
| Ornith-1.5-35B-A3B-Q4_K_M | CPU-only (`llama-cpp-cpu`) | not exposed | not exposed | 22 GiB | **compute (8 threads)** | 82.26 tok/s | 16.09-16.22 tok/s | not in current CPU preset |
| Ornith-1.5-35B-A3B-Q4_K_M | `llama-cpp-all-gpus` (MoE, full GPU-resident, dual-GPU) | 12.4 GiB | 11.1 GiB | baseline only | idle | 105.04 tok/s | 122.96 tok/s cold, 123.21 tok/s warm | 8,256-token prompt: 3,805.68 / 111.89 tok/s⁵ |
| Ornith-1.5-35B-A3B-Q4_K_M | `llama-cpp-gpu-1` (MoE, `n-cpu-moe` offload) | 11.2 GiB | not exposed | baseline only | idle | 92.14 tok/s | 65.11 tok/s cold, 66.52 tok/s warm | 8,256-token prompt: 1,191.33 / 63.19 tok/s⁵ |
| Ornith-1.5-9B-Q4_K_M | CPU-only (`llama-cpp-cpu`) | not exposed | not exposed | 7.4-7.5 GiB | **compute (8 threads)** | 45.29 tok/s | 7.36-7.35 tok/s |
| Ornith-1.5-9B-Q4_K_M | `llama-cpp-all-gpus` (dense, forced dual-GPU tensor-split) | 3.7 GiB | 3.8 GiB | baseline only | idle | 608.19 tok/s | 105.35 tok/s cold, 105.81 tok/s warm | 8,256-token prompt: 1,795.95 / 102.23 tok/s⁵ |
| Ornith-1.5-9B-Q4_K_M | `llama-cpp-gpu-1` (dense, single physical GPU) | 6.6 GiB | not exposed | baseline only | idle | 383.61 tok/s | 69.78 tok/s cold, 69.90 tok/s warm | 8,256-token prompt: 2,986.99 / 67.01 tok/s⁵ |
| qwen2.5-coder-14b-instruct-q4_k_m | `llama-cpp-gpu-1` (dense, single physical GPU) | 11.6 GiB | not exposed | baseline only | idle | 1,300.84 tok/s | 40.92 tok/s cold, 41.02 tok/s warm | 8,273-token prompt: 904.70 / 6.15 tok/s⁵ |
| qwen2.5-coder-14b-instruct-q5_k_m | `llama-cpp-all-gpus` (dense, forced dual-GPU tensor-split) | 6.8 GiB | 6.8 GiB | baseline only | idle | 761.79 tok/s | 62.99 tok/s cold, 63.41 tok/s warm | 8,273-token prompt: 1,019.55 / 52.96 tok/s⁵ |
| qwen2.5-coder-14b-instruct-q5_k_m | `llama-cpp-gpu-1` (dense, single physical GPU) | 12.9 GiB | not exposed | baseline only | idle | 1,140.48 tok/s | 38.09 tok/s cold, 38.14 tok/s warm | 8,273-token prompt: 794.56 / 5.24 tok/s⁵ |
| qwen2.5-coder-14b-instruct-q6_k | `llama-cpp-all-gpus` (dense, forced dual-GPU tensor-split) | 7.5 GiB | 7.5 GiB | baseline only | idle | 627.89 tok/s | 55.47 tok/s cold, 56.49 tok/s warm | 8,273-token prompt: 992.46 / 49.18 tok/s⁵ |
| qwen2.5-coder-14b-instruct-q6_k | `llama-cpp-gpu-1` (dense, single physical GPU) | 14.3 GiB | not exposed | baseline only | idle | 1,182.33 tok/s | 33.06 tok/s cold, 33.07 tok/s warm | 8,273-token prompt: 660.82 / 4.38 tok/s⁵ |
| qwen2.5-coder-7b-instruct-q4_k_m | `llama-cpp-gpu-1` (dense, single physical GPU) | 5.4 GiB | not exposed | baseline only | idle | 1,797.27 tok/s | 80.81 tok/s cold, 81.04 tok/s warm | 8,273-token prompt: 3,667.72 / 68.88 tok/s⁵ |
| qwen2.5-coder-7b-instruct-q8_0 | `llama-cpp-all-gpus` (dense, forced dual-GPU tensor-split) | 4.4 GiB | 4.5 GiB | baseline only | idle | 1,342.20 tok/s | 90.27 tok/s cold, 90.62 tok/s warm | 8,273-token prompt: 2,439.63 / 82.49 tok/s⁵ |
| qwen2.5-coder-7b-instruct-q8_0 | `llama-cpp-gpu-1` (dense, single physical GPU) | 8.3 GiB | not exposed | baseline only | idle | 1,870.13 tok/s | 52.91 tok/s cold, 53.06 tok/s warm | 8,273-token prompt: 3,721.65 / 47.63 tok/s⁵ |
| Qwen3-Coder-30B-A3B-Instruct-Q4_K_M | `llama-cpp-all-gpus` (MoE, full GPU-resident, dual-GPU) | 13.4 GiB | 12.8 GiB | baseline only | idle | 84.69 tok/s | 139.09 tok/s cold, 139.63 tok/s warm | 8,252-token prompt: 3,537.06 / 87.37 tok/s⁵ |
| Qwen3-Coder-30B-A3B-Instruct-Q4_K_M | `llama-cpp-gpu-1` (MoE, `n-cpu-moe` offload) | 12.3 GiB | not exposed | baseline only | idle | 115.57 tok/s | 59.74 tok/s cold, 60.17 tok/s warm | 8,252-token prompt: 1,814.80 / 40.25 tok/s⁵ |
| Qwen3-Coder-Next | 16GB schwerz | 7.5 GiB | not exposed | 49 GiB + 52 GiB mmap cache | idle | 58.72 tok/s | 31.12-31.29 tok/s | 8,252-token prompt: 962.31 / 37.05 tok/s⁵ |
| Qwen3-Coder-Next | 32GB schwerz (grouped-multigpu) | 2.7 GiB | 2.8 GiB | 48 GiB (partial swap) | some (swap I/O) | 19.87 tok/s | 7.43-7.44 tok/s |
| Qwen3-Coder-Next | CPU-only (`llama-cpp-cpu`) | not exposed | not exposed | 37 GiB | **compute (8 threads)** | 11.18 tok/s | 9.17-13.33 tok/s |
| Qwen3-Coder-Next-Q4_K_M | `llama-cpp-gpu-1` (MoE, `n-cpu-moe` offload) | 11,338 MiB | not exposed | not measured | idle | not measured | 35.32-37.19 tok/s | 49,186-token prompt: not measured / 29.94 tok/s (ctx=131072) |
| Qwen3-Coder-Next-Q4_K_M | `llama-cpp-all-gpus` (MoE, `n-cpu-moe` offload, dual-GPU) | not measured | not measured | not measured | idle | not measured | 34.14-36.06 tok/s | 49,186-token prompt: not measured / 30.33 tok/s (ctx=131072) |
| Qwen3-Next-80B-A3B-Instruct | 16GB schwerz | 7.5 GiB | not exposed | 49 GiB + 55 GiB mmap cache | idle | 62.98 tok/s | 31.81-32.00 tok/s | 8,252-token prompt: 1,306.14 / 41.71 tok/s⁵ |
| Qwen3-Next-80B-A3B-Instruct | CPU-only (`llama-cpp-cpu`) | not exposed | not exposed | 37 GiB | **compute (8 threads)** | 9.23 tok/s | 9.98-13.24 tok/s | 16,418-token prompt: 32.57 / 8.46 tok/s |
| Qwen3-Next-80B-A3B-Instruct-Q4_K_M | `llama-cpp-gpu-1` (MoE, `n-cpu-moe` offload) | 11,338 MiB | not exposed | not measured | idle | not measured | 35.21-37.36 tok/s | 49,186-token prompt: not measured / 30.63 tok/s (ctx=131072) |
| Qwen3-Next-80B-A3B-Instruct-Q4_K_M | `llama-cpp-all-gpus` (MoE, `n-cpu-moe` offload, dual-GPU) | not measured | not measured | not measured | idle | not measured | 34.02-35.96 tok/s | 49,186-token prompt: not measured / 30.21 tok/s (ctx=131072) |
| Qwen3.5-35B-A3B-Q4_K_M | `llama-cpp-all-gpus` (MoE, full GPU-resident, dual-GPU) | 12.3 GiB | 11.8 GiB | baseline only | idle | 71.10 tok/s | 101.96 tok/s cold, 102.30 tok/s warm | 8,256-token prompt: 4,329.95 / 94.71 tok/s⁵ |
| Qwen3.5-35B-A3B-Q4_K_M | `llama-cpp-gpu-1` (MoE, `n-cpu-moe` offload) | 11.7 GiB | not exposed | baseline only | idle | 129.14 tok/s | 60.60 tok/s cold, 60.62 tok/s warm | 8,256-token prompt: 1,530.73 / 57.39 tok/s⁵ |
| Qwen3.5-9B-Q4_K_M | CPU-only (`llama-cpp-cpu`) | not exposed | not exposed | 7.0-7.1 GiB | **compute (8 threads)** | 42.23 tok/s | 7.29-7.30 tok/s |
| Qwen3.5-9B-Q4_K_M | `llama-cpp-all-gpus` (dense, forced dual-GPU tensor-split) | 3.7 GiB | 3.8 GiB | baseline only | idle | 578.38 tok/s | 105.11 tok/s cold, 105.76 tok/s warm | 8,256-token prompt: 1,845.76 / 102.16 tok/s⁵ |
| Qwen3.5-9B-Q4_K_M | `llama-cpp-gpu-1` (dense, single physical GPU) | 6.6 GiB | not exposed | baseline only | idle | 930.51 tok/s | 69.48 tok/s cold, 69.50 tok/s warm | 8,256-token prompt: 3,008.76 / 66.69 tok/s⁵ |
| Qwen3.6-27B-Q6_K | `llama-cpp-all-gpus` (dense, forced dual-GPU tensor-split) | 14.0 GiB | 14.0 GiB | baseline only | idle | 167.97 tok/s | 31.47 tok/s cold, 31.50 tok/s warm | 8,256-token prompt: 628.43 / 30.38 tok/s⁵ |
| Qwen3.6-35B-A3B-Q4_K_M | `llama-cpp-all-gpus` (MoE, full GPU-resident, dual-GPU) | 12.0 GiB | 11.5 GiB | baseline only | idle | 78.67 tok/s | 122.55 tok/s cold, 123.44 tok/s warm | 8,256-token prompt: 3,989.07 / 112.98 tok/s⁵ |
| Qwen3.6-35B-A3B-Q4_K_M | `llama-cpp-gpu-1` (MoE, `n-cpu-moe` offload) | 11.7 GiB | not exposed | baseline only | idle | 125.48 tok/s | 68.39 tok/s cold, 68.18 tok/s warm | 8,256-token prompt: 1,242.04 / 63.81 tok/s⁵ |
| Qwen3.8-27B-UD-IQ3_S | `llama-cpp-all-gpus` (dense, forced dual-GPU tensor-split) | 9.1 GiB | 9.2 GiB | baseline only | idle | 202.25 tok/s (cold) | 47.50 tok/s cold, 47.55 tok/s warm | 8,256-token prompt: 679.79 / 45.81 tok/s⁵ |
| Qwen3.8-27B-UD-IQ3_S | `llama-cpp-gpu-1` (dense, single physical GPU)⁷ | 14.5 GiB | not exposed | baseline only | idle | -- | 30.64 tok/s cold, 30.69 tok/s warm | 65,088-token prompt: -- / 20.95 tok/s (ctx=65536) |
| Qwen3.8-27B-UD-Q3_K_XL | `llama-cpp-all-gpus` (dense, forced dual-GPU tensor-split) | 9.6 GiB | 9.7 GiB | baseline only | idle | 236.89 tok/s (cold) | 45.53 tok/s cold, 45.63 tok/s warm | 8,256-token prompt: 689.15 / 43.99 tok/s⁵ |
| Qwen3.8-27B-UD-Q3_K_XL | `llama-cpp-gpu-1` (dense, single physical GPU)⁷ | 14.3 GiB | not exposed | baseline only | idle | -- | 28.92 tok/s cold, 28.91 tok/s warm | 65,024-token prompt: -- / 20.48 tok/s (ctx=65536) |
| Qwen3.8-27B-UD-Q4_K_M | `llama-cpp-all-gpus` (dense, tensor-split) | 10.6 GiB (97-98% util) | 10.6 GiB (97% util) | baseline only | idle | 68.13 tok/s | 39.11-40.62 tok/s | 8,256-token prompt: 685.43 / 38.66 tok/s⁵ |
| Qwen3.8-27B-UD-Q5_K_M | `llama-cpp-all-gpus` (dense, tensor-split) | 12.0 GiB | 12.0 GiB | baseline only | idle | -- | 34.92 tok/s cold, 34.94 tok/s warm | 8,256-token prompt: 666.90 / 33.95 tok/s⁵ |
| Qwen3.8-27B-UD-Q6_K_M | `llama-cpp-all-gpus` (dense, tensor-split) | 14.3 GiB | 14.3 GiB | baseline only | idle | 184.80 tok/s | 30.16-31.05 tok/s | 8,286-token prompt: 641.50 / 30.21 tok/s⁵ |
| Qwen3.8-Flash-Next (tuned cfg) | 16GB schwerz, physical GPU 0 | 13.0 GiB | not exposed | baseline only | idle | -- | 6.34 tok/s cold, 6.60 tok/s warm |
| Qwen3.8-Flash-Next (tuned cfg) | 16GB schwerz, physical GPU 1 | 13.4 GiB | not exposed | 4.8 GiB + 56 GiB mmap cache | idle | 196.00 tok/s | 12.67-18.38 tok/s⁴ | 8,298-token prompt: 241.01 / 14.67 tok/s⁵ |
| Qwen3.8-Flash-Next-UD-Q3_K_XL | `llama-cpp-gpu-1` (MoE, `n-cpu-moe` offload, untuned) | 10,654 MiB | not exposed | not measured | idle | not measured | 14.97-16.06 tok/s | 49,232-token prompt: not measured / 12.11 tok/s (ctx=131072) |
| Qwen3.8-Flash-Next-UD-Q3_K_XL | `llama-cpp-all-gpus` (MoE, `n-cpu-moe` offload, untuned, dual-GPU) | not measured | not measured | not measured | idle | not measured | 15.87-17.66 tok/s | 49,232-token prompt: not measured / 13.64 tok/s (ctx=131072) |
| upstage.Solar-Open-100B.Q4_K_M | 16GB schwerz | 14,588 MiB | not exposed | not measured | idle | not measured | 4.58-4.83 tok/s | 49,249-token prompt: not measured / 2.49 tok/s (ctx=131072, `cache-type-k/v=q4_0`) |
| upstage.Solar-Open-100B.Q4_K_M | `llama-cpp-gpu-1` (MoE, `n-cpu-moe` offload) | 13,158 MiB | not exposed | not measured | idle | not measured | 8.76-9.64 tok/s | 49,249-token prompt: not measured / 3.48 tok/s (ctx=131072, `cache-type-k/v=q4_0`) |
| upstage.Solar-Open-100B.Q4_K_M | `llama-cpp-all-gpus` (MoE, `n-cpu-moe` offload, dual-GPU) | not measured | not measured | not measured | idle | not measured | 8.57-9.22 tok/s | 49,249-token prompt: not measured / 6.23 tok/s (ctx=131072, no cache quant needed) |

¹ Real DSH coding turn, live `llama-server` timing, not the standard
short-prompt benchmark: 4,501 input tokens, 1,205 generated, 5.33 tok/s
decode. Decode drops as populated context grows (was 19.91 tok/s after a
945-token prompt) -- the 51-52 tok/s row above is a valid short-context
result, not a realistic expectation for a multi-thousand-token turn.

² CPU decode (2.69-2.76 tok/s) is ~3.8x slower than this document's own
pre-test prediction (extrapolated from gpt-oss-20b-F16's CPU figure) --
architectural, not a bug: gpt-oss is MoE (sparse activation skips most
experts most tokens on CPU too); Devstral is dense, every parameter read
from RAM every token. **CPU is not a viable path for dense 20B+-class
models on this host**, unlike the genuinely-useful MoE CPU entries above.

³ Disk-swap-thrashing artifact (RAM and swap both maxed), not a real
measurement of the model or the grouped-multigpu cache -- see "32GB schwerz
service" below.

⁴ Not run-to-run noise -- two different KV-cache depths: 12.67 tok/s is
decode after a ~43,252-token prompt; 18.38 tok/s (14.61 cold) is after only
~130-260 tokens. Decode cost grows with populated context, so both are
real, at different depths.

⁵ Controlled long-context sweep (2026-09-19): deterministic 128-token
completion; input target = configured context / 8, clamped to 4,096--8,192
tokens. Each cell reports actual prompt tokens, then prefill / decode. This
is a comparable 4K/8K point, not a maximum-context result.

⁶ The 500 response is the router's presentation of the existing CUDA-OOM
load failure; the entry uses `ctx-size=65536`, `n-gpu-layers=all`, and
`fit=off` on one 16 GiB GPU. (`GLM-4.5-Air` was fixed 2026-09-20 -- see the
"16GB schwerz service" section below; this footnote now applies to
`Llama-4-Scout` only.)

⁷ This row's figures depend on specific tuned settings, not just the
model/service pairing -- the same model at this service's older or default
settings performs markedly worse or fails outright. `Qwen3.8-27B-UD-IQ3_S`/
`-Q3_K_XL`: only reached at `ctx-size=65536` (see "Maximising performance
on a single card" below); both regressed badly at their original larger
ctx-size values. `gpt-oss-120b-Q4_K_M` on the upstream services: only
reached with an explicit `n-cpu-moe` value tuned per service (31 on
`llama-cpp-gpu-1`, 29 on `llama-cpp-all-gpus`) -- see "gpt-oss-120b: plain
n-cpu-moe vs. schwerz expert-cache" below for the full tuning history and
why the two services need different values. `GLM-4.5-Air-UD-Q4_K_XL` and
`upstage.Solar-Open-100B.Q4_K_M` at 128K: `n-cpu-moe` alone was never
enough, no matter how high -- both models' KV cache alone exceeds one
card's capacity at `ctx-size=131072`, an entirely separate problem from
expert placement, only fixed by adding `cache-type-k/v=q4_0` (not needed
for either model at `ctx-size=65536`, and not needed for Solar-Open-100B on
`llama-cpp-all-gpus`, where the second card's headroom covers the gap
instead) -- see "Second batch" and "Two new downloads" below for the full
figures and the models this did and didn't affect.

## Long-context sweep (2026-09-19)

The generated-service sweep completed 58 requests. The final column above
records them without replacing the short-context figures, which remain useful
for comparison with rows not included in this sweep.

Six reported failures did not produce new throughput results:

- The historical standalone `gpt-oss-20b-F16` setup has no generated Compose
  profile. Either create an equivalent dedicated profile before benchmarking
  it again, or retain it as a standalone-only historical result.
- `gpt-oss-20b-F16` and `Ornith-1.5-35B-A3B-Q4_K_M` are no longer in the CPU
  preset, and DeepSeek-Coder-V2-Lite is no longer in the 16GB preset. Restore
  an entry only if that service/model pairing remains a supported deployment;
  otherwise remove or mark the historical pairing as retired rather than
  testing it under different settings.
- GLM-4.5-Air and Llama-4-Scout could not load on the 16GB schwerz profile at
  sweep time. **Resolved for GLM-4.5-Air 2026-09-20** via `cache-type-k/v
  = q4_0` in its own `models-preset.ini` section (see "16GB schwerz service"
  below) -- real 8,311-token completion, 3.12 tok/s decode, full
  `ctx-size=65536` retained. Llama-4-Scout still cannot load; four
  conditions tested (V-only quant, K+V quant, reduced `ctx-size`, and the
  two combined) all hit the same `moe-cache` graph-compute OOM. `fit=on`
  remains untried for Llama-4-Scout.

## Rejected models

Models removed entirely -- weight files deleted from disk, not just
unlisted. Kept as a record of what was tried and why it didn't earn a
place.

| Model | Service tried | Decode | Reason rejected |
|---|---|---|---|
| Llama-3.3-70B-Instruct-Q3_K_M | `llama-cpp-all-gpus`, `n-gpu-layers=auto` partial offload | 4.78 tok/s (small ctx) -> 2.09-2.75 tok/s (ctx-size 65536-131072) | Doesn't fit 32 GiB combined VRAM with real margin, so every token touches host RAM/PCIe -- a structural bottleneck. An order of magnitude slower than the fleet's MoE models of similar or larger total size, which only activate a few billion parameters per token. ~32 GiB freed. |
| Qwen2.5-72B-Instruct-Q3_K_S | `llama-cpp-all-gpus`, `n-gpu-layers=auto` partial offload | 4.57 tok/s (small ctx) -> 2.14-2.57 tok/s (ctx-size 65536-131072) | Same partial-offload bottleneck, same order-of-magnitude gap to the fleet's MoE models. ~32 GiB freed. |

## GPU-resident, single card, no host offload

| Model | Setup | Prefill | Decode |
|---|---|---|---|
| gpt-oss-20b-F16 | standalone container, idle GPU, fully resident, no MoE offload | 3,802.08 tok/s | 63.76 tok/s |

Baseline for "what this hardware does with nothing offloaded to host."
Every other number in this document is slower because it's carrying
MoE-cache overhead, memory pressure, or both.

## 16GB schwerz service (single GPU, host-offloaded experts, `qwen4exp-mtp` pin)

Real tuning pass, one variable at a time, verified against a large
(~43K-token) prompt built from session logs -- small-request probes don't
predict large-request VRAM/throughput (a `ubatch-size=1536` config passed
a 5-token probe, then OOM'd on the real prompt).

| Model | Config | Prefill | Decode |
|---|---|---|---|
| Flash Next (UD-Q3_K_XL) | baseline: batch=512, ubatch=256, cache=32 | 87.03 tok/s | 11.66 tok/s |
| Flash Next (UD-Q3_K_XL) | interim: cache=64 (more VRAM, less headroom) | -- | +14% vs baseline |
| Flash Next (UD-Q3_K_XL) | **deployed: batch=2048, ubatch=1024, cache=48** | **196.00 tok/s (+125%)** | **12.67 tok/s (+9%)** |

`ubatch-size`, not `batch-size`, was the real prefill lever (+121.7% from
`ubatch=1024` alone; `batch=512` vs `2048` at the same cache size was
statistically indistinguishable).

Reasoning-effort fix, applied here and to every other reasoning-capable
model in this deployment: this model's chat template defaults to `xhigh`
whenever a request omits `reasoning_effort`, and DSH was never sending the
field for this provider. `reasoning: true` + `thinkingLevelMap` in
`settings.yaml` fixed it -- ~60% reduction in reasoning length confirmed
by direct A/B.

`gpt-oss-120b`, `GLM-4.5-Air`, `Llama-4-Scout` are also catalogued here
with `load-mode=mmap`/`lazy-mode=on` (all three exceed physical RAM on
file size alone: 58.44 GiB, 63.07 GiB, 65.4 GiB), matching Flash Next's
own pattern rather than inheriting the service's `load-mode=none` default,
which caused the swap-thrashing failure recorded for the 32GB service.

Six-model run, same prompt/methodology as the CPU round below:

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

\*Small prompt (131 tokens) here, not comparable to the 196 tok/s tuned
figure above (large-prompt only).

mmap fix confirmed: `gpt-oss-120b` used only 4.0 GiB RAM (54 GiB in
reclaimable `buff/cache`), unlike the 32GB service's full-swap failure for
the same model. Coder-Next/Next-80B-Instruct: ~31 tok/s here vs. 9-13 tok/s
CPU-only -- a real ~2.4-3.4x GPU speedup for models that fit either way.

`Llama-4-Scout` and `GLM-4.5-Air` both hit `CUDA error: out of memory` on
GPU 0 (this service's only exposed card): `cudaMalloc` failures allocating
cache slots / during first-decode graph compute. Both use `n-gpu-layers =
all`/`fit = off`, the same pattern that works for the other three models
here -- but forcing the entire dense/attention core plus a 65536-token KV
cache onto one 16 GiB card leaves no room for cache slots (Llama-4-Scout's
`hidden_size=5120` is wider than anything else in this catalogue).

**2026-09-20: `GLM-4.5-Air` fixed, `Llama-4-Scout` still not.** Four
conditions tested against real containers for each model: V-only KV quant
(`cache-type-v=q4_0`, K unchanged), symmetric K+V quant (both `q4_0`),
`ctx-size` alone reduced, and the two combined.

`GLM-4.5-Air`: symmetric K+V `q4_0` **and** `ctx-size` reduction each
independently fixed it (real 8,256-token completions: 3.25 tok/s decode at
full `ctx-size=65536` with K+V quant; 2.71 tok/s at `ctx-size=32768` with
KV unchanged). Deployed: `cache-type-k`/`cache-type-v = q4_0` added to this
model's own `models-preset.ini` section, keeping full `ctx-size` (better
decode, no context lost) -- confirmed this per-model override actually
takes effect on this fork, contrary to `config.ini`'s own header comment
claiming service-level settings always win. V-only alone is **not** a real
fix -- see the FlashAttention-kernel note below; it loads and survives a
trivial request but still OOMs on a real long-context one.

`Llama-4-Scout`: none of the four conditions helped, including the most
aggressive combination tried (`ctx-size=8192` + K+V `q4_0` together) --
identical failure signature throughout (`moe-cache` OOM allocating a fixed
~67.5 MiB buffer during the MoE routing matmul, not the KV cache at all).
This is a different bottleneck than `GLM-4.5-Air` hit, insensitive to both
levers tested here. Still not fixed; `fit=on` (auto-reducing GPU layer
count) remains untried.

**Real deployment bug found along the way: no compiled CUDA FlashAttention
kernel for asymmetric K/V quant on this build.** `cache-type-k=q8_0` +
`cache-type-v=q4_0` produced this build's own warning: `no FlashAttention
vector kernel compiled for K/V types q8_0-q4_0, converting K and V to f16
instead (slow)` -- silently falling back to f16 math, which needs *more*
memory than the untouched q8_0/q8_0 baseline, not less, so it OOM'd anyway
on both models. This is why the asymmetric pattern already used
successfully on `llama-cpp-cpu` (`Qwen3-Coder-Next`/`Qwen3-Next-80B`'s
`cache-type-v=q4_0` with K left at `q8_0`) doesn't transfer to any GPU
service here -- CPU attention has no such kernel-compilation restriction.
Fix path, not yet applied: add `-DGGML_CUDA_FA_QUANTS="q8_0-q4_0"` (or
whatever combination is wanted) to the `cmake_args` in `llama-cpp/Dockerfile`
and rebuild -- the flag isn't set today, so only the build's default kernel
set is compiled. Requires a real rebuild of whichever image(s) need it, not
just a config change; not done as part of this finding.

## `llama-cpp-all-gpus` service (dense, both GPUs via `split-mode=tensor`)

| Model | Metric | Before tensor-split | After tensor-split |
|---|---|---|---|
| Qwen3.8-27B-UD-Q6_K_M | real-session model-only step, median | 24.6s | 18.0s |
| Qwen3.8-27B-UD-Q6_K_M | real-session model-only step, mean | 91.5s | 45.1s |

Confounds two simultaneous changes (`split-mode=tensor` going live and
`reasoning-effort=low` in the same window) -- not separated.

| Date | Prefill (cold) | Decode (cold) | Decode (warm) | GPU 1 | GPU 2 |
|---|---|---|---|---|---|
| 2026-09-14 | 56.78 tok/s | 40.50 tok/s | 40.66 tok/s | 10.6 GiB, 98% | 10.6 GiB, 97% |
| 2026-09-17 | 68.13 tok/s | 39.11 tok/s | 40.62 tok/s | 10.6 GiB, 97-98% | 10.6 GiB, 97% |

Both runs (Q4_K_M) agree closely -- decode essentially identical, prefill
within normal variance, confirming real dual-GPU compute engagement
(97-98% util both cards), not just balanced memory placement.
`reasoning-effort=low` and `split-mode=tensor` were each independently
confirmed active (byte-identical output vs. an explicit `"low"` request;
near-equal VRAM split across cards).

## 32GB schwerz service (two GPUs, `codex/moe-grouped-multigpu` pin) -- failed batch, root-caused

| Model | Run | Prefill | Decode | RAM / swap |
|---|---|---|---|---|
| gpt-oss-120b | cold | 2.20 tok/s | 2.36 tok/s | 60/60 GiB RAM, 8/8 GiB swap (maxed) |
| gpt-oss-120b | warm (cached prompt) | 1.87 tok/s* | 3.01 tok/s | maxed |
| GLM-4.5-Air | cold | 1.68 tok/s | 1.01 tok/s | maxed; **0% GPU util, both cards** |
| GLM-4.5-Air | warm | 0.70 tok/s* | 1.39 tok/s | maxed |
| Qwen3-Coder-Next | cold | 19.87 tok/s | 7.43 tok/s | 48/60 GiB RAM, 5.1/8 GiB swap (partial) |
| Qwen3-Coder-Next | warm | 5.67 tok/s* | 7.44 tok/s | partial |

\*"warm" prefill is a 1-token cached-prompt continuation, not a real
prefill measurement.

**Not real performance numbers for the models or the grouped-multigpu
cache -- swap-thrashing artifacts.**

### What actually causes the RAM ceiling

`codex/moe-grouped-multigpu` requires `load-mode = none` (its own doc:
mmap-based pinning is "rejected before inference" because read-only
auxiliary registration is unsupported). Without mmap, a model exceeding
physical RAM has no fallback but swap. `load-mode`/`lazy-mode` are stock
llama.cpp flags (default `auto`), not schwerz-exclusive -- the plain
services already get mmap+lazy loading by default; what's fork-specific is
`moe-cache` itself, and `codex/moe-grouped-multigpu`'s requirement to
*disable* mmap for its cross-GPU dispatch. This means Flash Next's
exclusion from the 32GB schwerz catalogue is specific to that branch, not
necessarily the plain `llama-cpp-all-gpus` service (never actually tested
against it).

`gpt-oss-120b` (58.44 GiB) and `GLM-4.5-Air` (63.07 GiB) both exceed or
nearly exceed this host's 60 GiB RAM on file size alone -- under
`load-mode=none` neither ever fits. `Qwen3-Coder-Next` (46 GiB) partially
avoided catastrophe by being small enough to mostly fit even without
mmap's elasticity, but still touched swap and showed unexplained
asymmetric GPU utilization (59% vs 12% on otherwise-identical cards -- see
"Still open" below).

**Fix**: Flash Next excluded from the schwerz 32GB catalogue entirely
(mmap is fundamental to its viability, and its dominant cost is prefill
anyway, which this branch's benefit doesn't help). `gpt-oss-120b` and
`GLM-4.5-Air` moved to the 16GB schwerz service instead, where mmap is
available. Whether these would fare differently via plain `--n-cpu-moe` on
the mmap-capable `llama-cpp-32gb`/`llama-cpp-16gb` services is untested.

### Deployment bugs found along the way

- Splitting the shared `models-preset.ini` into 16GB/32GB templates
  updated the repo files but skipped the actual deploy step -- Docker
  silently created an empty directory at the bind-mount path instead of
  erroring, and llama.cpp's router failed with a filebuf error
  symptomatically identical to "the service isn't publishing ports."
  Happened independently on both services.
- A `stop`+`up` after fixing a bad bind mount is not enough -- Docker
  bakes mount resolution in at container creation. Needs
  `--force-recreate`.

## CPU-only (`llama-cpp-cpu`, port 11437, no GPU offload at all)

Real ~150-token five-topic prompt, cold immediately followed by warm
(cached-prompt), `free -h`/`swapon --show`/`nvidia-smi` after each --
0% GPU utilization confirmed for every run. Flash Next (84 GiB) excluded
from this round: exceeds even 60 GiB RAM on file size alone, would hit the
same swap-thrashing wall rather than produce a useful CPU number.

| Model | Size | Run | Prefill | Decode | RAM used | Swap used |
|---|---|---|---|---|---|---|
| gpt-oss-20b-F16 | 13 GiB | cold | 68.06 tok/s | 10.42 tok/s | 19 GiB | 0 B |
| gpt-oss-20b-F16 | 13 GiB | warm | -- | 10.43 tok/s | 19 GiB | 0 B |
| Ornith-1.5-35B-A3B-Q4_K_M | 21 GiB | cold | 82.26 tok/s | **16.22 tok/s** | 22 GiB | 930 MiB |
| Ornith-1.5-35B-A3B-Q4_K_M | 21 GiB | warm | -- | 16.09 tok/s | 22 GiB | 969 MiB |
| Qwen3-Coder-Next-Q4_K_M | 46 GiB | cold | 11.18 tok/s | 9.17 tok/s | 37 GiB | 6.3 GiB |
| Qwen3-Coder-Next-Q4_K_M | 46 GiB | warm | -- | 13.33 tok/s | 37 GiB | 6.3 GiB |
| Qwen3-Next-80B-A3B-Instruct | 46 GiB | cold | 9.23 tok/s | 9.98 tok/s | 37 GiB | 6.1 GiB |
| Qwen3-Next-80B-A3B-Instruct | 46 GiB | warm | -- | 13.24 tok/s | 37 GiB | 6.1 GiB |

### Practical implications

- **CPU-only is genuinely viable for MoE models that fit in RAM but not
  VRAM**, not merely a slow fallback -- all four produced coherent output
  at 9-16 tok/s. Contrast the 32GB GPU service's 1-3 tok/s on
  gpt-oss-120b/GLM-4.5-Air (memory-*exhausted*, RAM and swap both maxed).
  The determining factor is whether the working set actually fits, not
  CPU-vs-GPU as such.
- **Decode speed does not scale monotonically with model size.** Ornith
  (21 GiB) decoded faster than every other model here, including smaller
  gpt-oss-20b -- active-parameter count and per-expert compute shape
  (256 experts/8 active vs 32/4) matter more than raw weight volume once
  everything fits in RAM.
- **Cold-vs-warm reveals a real first-touch penalty, only for the two
  46 GiB models** (~40-45% decode uplift warm vs cold) -- consistent with
  mmap page-faulting weight data during the first run's decode, not just
  prefill. gpt-oss-20b and Ornith showed no such gap, consistent with
  fitting comfortably enough to never fault in anything decode touches.
- gpt-oss-20b's CPU decode (10.42 tok/s) vs. its GPU-resident figure
  (63.76 tok/s): **~6.1x slower on CPU** for this model -- not assumed to
  generalize (no clean GPU-only figure exists for Ornith).

## Single-GPU-pinned variants and Nemotron dual-GPU context

`split-mode=none` + `main-gpu=N` pins a model to one specific GPU on
`llama-cpp-all-gpus` (which exposes both cards by default).

- `gpt-oss-20b-F16` pinned to GPU 1, `ctx-size=131072`: confirmed working,
  14,444/16,311 MiB. (The pin target assumption behind this -- "GPU 1 is
  free because schwerz uses GPU 0" -- was later found backwards: this
  deployment's `.env` actually puts schwerz on GPU 1. All single-GPU pins
  were moved to GPU 0 once real contention surfaced; verify the *running
  container's* environment, not the compose default, before pinning
  anything to avoid a collision.)
- `Qwen3.8-27B-UD-Q4_K_M` pinned to GPU 1: **does not fit on one 16 GiB
  card at any usable context.** `ctx-size=131072` and `32768` both OOM
  allocating the KV buffer -- even a ~1 GiB KV buffer fails, meaning dense
  weights alone consume at least ~15.2 GiB of the 16,311 MiB card. A hard
  capacity ceiling, not a context-tuning problem; no quant of this family
  fits solo on one card. Removed the failed single-GPU entry; the three
  dual-GPU (`split-mode=tensor`) entries remain the only way to run it.
- `NVIDIA-Nemotron-3.5-Lightning-30B-A3B-Q4_0`, both GPUs,
  `ctx-size=262144`: confirmed working. GPU 0: 10,495/16,311 MiB; GPU 1:
  13,538/16,311 MiB (the binding constraint on pushing further). Uses its
  own published MTP sidecar for speculative decode.

## Real decode speed under an agentic DSH workload

Seven DSH code-review sessions (see `code-review-performance.md`) give
real decode tok/s under genuine agentic tool-calling load, not a synthetic
benchmark prompt (tok/s = total output tokens / model-only compute time):

- `Qwen3.8-27B-UD-Q6_K_M` (dual-GPU, tensor-split): **22.5 tok/s**, one
  191.9-minute session.
- `NVIDIA-Nemotron-3.5-Lightning-30B-A3B-Q4_0` (dual-GPU): **42.2-101.2
  tok/s** across three sessions (~80 tok/s average) -- the MTP sidecar and
  cheap hybrid-SSM architecture both pay off in practice.
- `gpt-oss-20b-F16-1gpu` (single GPU): **52.5-60.8 tok/s** across three
  sessions.
- `Qwen3.8-Flash-Next-UD-Q3_K_XL` (MoE-cache, single GPU): **9.9-10.8
  tok/s** across three sessions -- slow but steady. Despite the low tok/s,
  this model produced the best code reviews of any session in either
  batch when given a long enough run to finish (`code-review-performance.md`)
  -- decode speed and review quality are unrelated findings here.
- `Qwen3-Coder-Next-Q4_K_M` (MoE-cache, single GPU): **3.3-10.5 tok/s**
  across two sessions -- the 3.3 tok/s outlier coincides with a session
  later found to have left an orphaned subprocess on this service (below);
  not conclusive from one data point.

One Nemotron session (13:03 UTC) also caught a real DSH config bug in the
act: `settings.yaml` still had a stale `contextWindow: 65536` (real
dual-GPU ctx-size is 262144) with no compaction override, so DSH began
pruning the session after just 8 turns -- against roughly a quarter of the
model's real window. Fixed the same day (`contextWindow` corrected, a
`modelPolicies` entry added); not retested under the corrected config.

## `models-preset.ini` split into GPU and CPU templates

The GPU and CPU services shared one override source, generated ad hoc for
CPU and never kept in sync (confirmed stale: `split-mode=tensor` on
entries with no CUDA devices passed through). Split into independently
tracked sources, mirroring the schwerz 16GB/32GB split pattern -- the GPU
source later split further into `llama-cpp-16gb`/`llama-cpp-32gb`.
`llama-cpp-cpu`'s new preset strips every GPU-only directive and adds a
CPU-specific Nemotron entry: no MTP speculative-decode sidecar (untested
acceptance rate on CPU threading for this architecture), `ctx-size=131072`
as a reasoned but untested starting point (18 GiB weight file against
~55 GiB free RAM; mostly Mamba/SSM layers with fixed-size state, so should
scale with context more cheaply than a comparable dense transformer;
native context is 1,048,576).

## Real reliability gap: orphaned GPU subprocess on the 16GB schwerz service

A `Qwen3-Coder-Next-Q4_K_M` subprocess under the schwerz-16gb container
kept running and holding 7.5 GiB VRAM **28 minutes** after the DSH session
that loaded it had ended -- its own session's final request, and a
concurrent Flash Next session's, both went unanswered at the same
timestamp, consistent with the router being wedged behind the stuck
subprocess. Confirmed via `nvidia-smi`'s process list; cleared only by
restarting the container. Nothing in this deployment currently detects or
kills a hung per-model subprocess. Blocked unrelated loads on the same
physical GPU too. Root cause of the hang itself not established.

## Correction: the 16GB schwerz service's real GPU pin

Every "GPU 0 occupied by schwerz" assumption in this repo was based on the
compose file's *default*, never checked against the running container.
This deployment's `.env` overrides it: schwerz really runs on **physical
GPU 1**, confirmed via `docker exec ... env`. All single-GPU-pinned
entries were moved from `main-gpu=1` to `main-gpu=0` and re-verified.
Lesson: check the running container's environment, not the compose
default, before pinning anything to avoid contention.

## Real incident: split-mode=tensor broken by the service refactor, fixed

`llama-cpp-all-gpus` started failing real loads for all three Qwen3.8-27B
quants under `split-mode=tensor` -- not an OOM. Root cause: an NCCL 2.25.1
/ RTX 5060 Ti compatibility gap (`ncclGroupEnd()` -> CUDA kernel launch
fails with `Cuda failure 1 'invalid argument'`, independent of transport),
introduced by the refactor's rebuild-from-source.

**Fix: `NCCL_CUMEM_ENABLE=0`** in `compose.ai.yml` -- doesn't make NCCL
itself succeed, but lets llama.cpp catch the failure and fall back to its
own non-NCCL AllReduce path. Confirmed working; decode on the fallback
path lands close to the original NCCL-based figures, close enough that
tensor-split remains clearly worth keeping over layer-split (tried,
confirmed much slower for this workload).

Clean 256-token cold/warm re-benchmark, all five Qwen3.8-27B configs:

| Config | Placement | VRAM | Cold decode | Warm decode |
|---|---|---|---|---|
| `Q4_K_M` | dual-GPU tensor-split (fallback AllReduce) | 10,655 + 10,740 MiB (~21.4 GiB combined) | 39.89-40.51 tok/s | 39.96 tok/s |
| `Q5_K_M` | dual-GPU tensor-split (fallback AllReduce) | 12,231 + 12,316 MiB (~24.5 GiB combined) | 34.92 tok/s | 34.94 tok/s |
| `Q6_K_M` | dual-GPU tensor-split (fallback AllReduce) | (not captured) | ~29-31 tok/s | -- |
| `Qwen3.8-27B-UD-IQ3_S` | single GPU (`llama-cpp-gpu-1`) | 14,858 MiB | 30.64 tok/s | 30.69 tok/s |
| `Qwen3.8-27B-UD-Q3_K_XL` | single GPU (`llama-cpp-gpu-1`) | 14,664 MiB | 28.92 tok/s | 28.91 tok/s |

Both GPUs sat at 97-99% utilization in every case -- genuinely
compute/bandwidth-saturated, not idle-waiting.

**Why single-GPU 3-bit quants decode slower than dual-GPU Q4_K_M despite
being smaller/lower-bit**: dense decode at batch=1 is memory-bandwidth-
bound -- every token streams the entire weight set from VRAM once.
Tensor-split across two GPUs divides that per-token streaming across two
memory buses in parallel, roughly doubling effective bandwidth. A
smaller/lower-bit quant on one GPU reduces bytes streamed per token, but
not enough to make up for having only one card's bandwidth. The numbers
fit this quantitatively (predicted ~1.46x more data through the single
bottleneck GPU for IQ3_S vs. each GPU's share in the Q4_K_M split;
observed decode ratio ~1.3-1.38x, consistent given real-world cross-GPU
reduce overhead). **Practical implication**: for this dense family on this
hardware, dual-GPU tensor-split will essentially always out-decode
single-GPU regardless of quant size. Single-GPU Q3 configs remain useful
for keeping the other physical GPU free for something else -- a
concurrency trade, not a speed one.

## Qwen3.8-27B, single GPU, real 3-bit quants

Per-GPU-locked architecture since the refactor: `llama-cpp-gpu-0`/`gpu-1`
each reserve exactly one physical GPU at the Docker level, so
`split-mode`/`main-gpu` pinning is unnecessary on these two services.

Two real 3-bit Unsloth Dynamic v3.0 quants (no literal "Q3_K_M" exists for
this model -- the real ladder is `UD-IQ3_XXS`/`UD-IQ3_S`/`UD-Q3_K_XL`),
both confirmed working on `llama-cpp-gpu-1` at `ctx-size=65536`:

- `Qwen3.8-27B-UD-IQ3_S` (11.2 GiB): 13,610 MiB VRAM, 30.2 tok/s decode,
  ~2.7 GiB headroom.
- `Qwen3.8-27B-UD-Q3_K_XL` (12.2 GiB): 14,664 MiB VRAM, 27.7 tok/s decode,
  ~1.6 GiB headroom.

Extrapolating a target ctx-size from the measured KV rate (131072 for
IQ3_S, 98304 for Q3_K_XL) **both failed** a real load by a small margin
late in loading -- the flat overhead assumed on top of the KV-rate
extrapolation undercounted a context-dependent compute/graph buffer.
Backed off a full 32768 tokens and both then confirmed working:

- `Qwen3.8-27B-UD-IQ3_S`: **ctx-size=98304 works**, 14,858 MiB, 1,453 MiB
  headroom (131072 does not fit).
- `Qwen3.8-27B-UD-Q3_K_XL`: **ctx-size=65536 works** (unchanged, re-
  confirmed), 14,664 MiB, 1,647 MiB headroom (98304 does not fit).

Real headroom likely exists between each working value and its failed
one, untested -- lesson: a KV-rate-only extrapolation isn't sufficient to
predict the real ceiling on this build; treat any extrapolated ctx-size as
a starting point to verify.

## Both 3-bit quants forced onto dual-GPU tensor-split despite fitting on one card

Following the bandwidth analysis above: added both quants to
`llama-cpp-32gb` too, `split-mode=tensor` forced, `ctx-size=163840`
(matching Q6_K_M as a known-good starting point). Both confirmed working:

| Config | VRAM/card | Decode (8-token sample) | Decode (clean 256-token) |
|---|---|---|---|
| `IQ3_S`, single GPU | 14,858 MiB | 30.64-30.69 tok/s | 30.64-30.69 tok/s |
| `IQ3_S`, forced dual-GPU tensor-split | 9,331 + 9,416 MiB | 39.54 tok/s | **47.50 / 47.55 tok/s** |
| `Q3_K_XL`, single GPU | 14,664 MiB | 28.91-28.92 tok/s | 28.91-28.92 tok/s |
| `Q3_K_XL`, forced dual-GPU tensor-split | 9,857 + 9,942 MiB | 38.41 tok/s | **45.53 / 45.63 tok/s** |

Both use *less* VRAM per card than single-GPU placement (weights split,
not duplicated) -- ~6.4-7 GiB free per card, real untested headroom to
raise `ctx-size` further. Confirms forcing tensor-split is a genuine
throughput win even for a model that fits on one card.

Same change applied to `gpt-oss-20b-F16` (no `split-mode` was set at all,
silently inheriting layer-split): forced tensor-split, confirmed working,
7,621 + 7,706 MiB combined (vs. ~13.3 GiB solo) and **141.38 / 142.33
tok/s** -- ~2.2x the 63.76 tok/s single-GPU baseline. `GLM-4.7-Flash`
(`deepseek2` architecture) is confirmed NOT to support `split-mode=tensor`
on this build, unlike gpt-oss.

## Real incident: `llama-cpp-cpu` RAM audit, one near-miss on host stability

Auditing `llama-cpp-cpu` for models that can't fit 60 GiB RAM (no GPU
passthrough, everything must fit in RAM alone). Five small chat models
added (2.8-5.4 GiB each, no real risk). Three real findings:

1. **`Qwen3.8-Flash-Next-UD-Q3_K_XL` (84 GiB) was selectable despite a
   comment claiming it was absent** -- omitting a model from the override
   source doesn't stop full-discovery mode adding it back as a catch-all;
   the tool has no exclude mechanism. Fixed by adding an explicit entry
   with `load-mode=mmap`/`lazy-mode=on`, not a claim it will work -- the
   realistic failure mode if selected is prolonged swap-thrashing.
2. **`DeepSeek-R1-Distill-Llama-70B-Q4_K_M` at `ctx-size=65536` FAILED a
   real load -- a genuine near-miss, not theoretical.** Swap climbed from
   2.9 GiB to 7.7 GiB of the 8 GiB ceiling before the container was
   stopped manually; the host recovered within seconds. The entry's own
   prior "should leave ~6 GiB free" estimate was wrong in practice. Backed
   off to `ctx-size=8192` (not re-verified -- deliberate, given the risk
   just observed).
3. **`Llama-3.3-70B-Instruct-Q3_K_M` (32 GiB) was an undiscovered
   catch-all with an even more expensive cache config** than the entry
   that just failed. Promoted to an explicit `ctx-size=8192` entry by
   reasoning from the DeepSeek result rather than repeating the live-load
   risk. Also not re-verified.

**Resolution**: `llama-cpp-cpu` switched from full-discovery to
`--preset-only`, trimmed to the five small models plus the two real,
CPU-tested >32 GiB MoE models. `llama-cpp-gpu-0`/`gpu-1` switched to
`--preset-only` the same day; `llama-cpp-all-gpus` is now the only service
still on full-discovery (documented intent, previously undeployed).

## `llama-cpp-16gb` pruned to proven/known-safe entries

Six entries removed, each for a distinct, unambiguous reason:

- `Llama-3.3-70B-Instruct-Q3_K_M`, `Qwen2.5-72B-Instruct-Q3_K_S`,
  `DeepSeek-R1-Distill-Llama-70B-Q4_K_M` -- dense, 32-40 GiB, nowhere
  close to fitting a 16,311 MiB card (the DeepSeek entry is the exact
  model that just failed a real CPU-service load test).
- `Qwen3-Coder-Next-Q4_K_M`, `Qwen3-Next-80B-A3B-Instruct-Q4_K_M` -- real
  CPU-tested MoE models, but `n-gpu-layers = 0` here meant fully CPU-bound
  even on this GPU-locked service. Wrong service for what they do at
  runtime.
- `NVIDIA-Nemotron-3.5-Lightning-30B-A3B-Q4_0` -- 17.60 GiB weight alone
  already exceeds one card's 16,311 MiB before any KV cache. Never tested
  single-GPU.

Sixteen entries kept: real-load-confirmed on a single GPU this session
(`gpt-oss-20b-F16`, both Qwen3.8-27B 3-bit quants, four `n-cpu-moe`-
offloaded 30-35B models), or small enough (two tiny embedding models,
several older coding models 3.56-8.44 GiB) that fit was never genuinely
in question.

## `llama-cpp-32gb` pruned of CPU-only-in-a-GPU-service entries

Same day: removed `Qwen3-Coder-Next-Q4_K_M` and
`Qwen3-Next-80B-A3B-Instruct-Q4_K_M` from `llama-cpp-32gb` -- both carried
`n-gpu-layers = 0`, never touching either GPU even here. Properly homed
elsewhere (CPU-only figures on `llama-cpp-cpu`, MoE host-offload figures
on the 16GB schwerz service). This service stays in full-discovery mode,
so both remain selectable via their raw catch-all IDs -- accepted; only
the misleading curated entry was removed. Audited the rest of the file
against the same criterion: `NVIDIA-Nemotron-3.5-Lightning`, `gpt-oss-20b-F16`,
`GLM-4.7-Flash-Q4_K_M` are all independently verified GPU-resident here --
no further removals identified.

## Real-request audit of both pruned presets finds three genuine bugs

Rather than trust the size/architecture reasoning behind the prunes above,
sent a real request to every curated entry. Found three real problems in
the "older, small, obviously safe by size" group:

1. **`magicoder-s-ds-6.7b.Q4_0` cannot load on this build at all** --
   `unknown tokenizer: 'deepseek_coder'`, not fixable by config. Removed.
2. **`Qwen3-Embedding-0.6B-Q8_0` rejected every embeddings request** --
   the preset never set `--embeddings`, so the router loaded it in default
   generative mode.
3. **`embeddinggemma-300M-Q8_0` crashed outright on load** -- same root
   cause as #2, worse failure mode (`GGML_ASSERT` process abort).

**Fix**: `embeddings = true` added to both embedding entries; confirmed
working with real `/v1/embeddings` calls afterward.

A fourth, separate problem found while investigating: the repo source for
`llama-cpp-16gb` was itself missing both embedding-model sections (a
transcription error from an earlier same-day rewrite), invisible only
because the previously-deployed copy still had them. Caught by diffing
repo source against the live-deployed file.

## Real incident: Devstral-Small ctx-size failure, fixed

Devstral-Small single-GPU: `ctx-size=32768` fails a real CUDA OOM
allocating the KV buffer (13.35 GiB weight leaves only ~2.6 GiB free on
one 16,311 MiB card); the working fallback, `16384`, was judged too small
to be useful. Moved to `llama-cpp-32gb` (`split-mode=tensor`,
`ctx-size=131072`, matching the bandwidth-doubling pattern already
established for dense models) and to `llama-cpp-cpu`. Both quants
confirmed working dual-GPU: near-equal weight split, 12.8-12.9 GiB/card,
~3.1-3.2 GiB real headroom each.

## Context-size review across every preset: `Qwen3.8-Flash-Next` raised to 131072

Raised from 98304 -- confirmed working on physical GPU 1: 18.87 tok/s
decode, ~2.9-3.3 GiB headroom on the 16,311 MiB card. Native context is
262144 (GGUF metadata: qwen4exp architecture), so 98304 was using only 37%
of it; untested above 131072.

## Real incident: `parameterise-llama` refactor investigation -- three real problems

Investigating a real "Flash Next runs at 6 tok/s" regression found three
distinct, unrelated causes:

**1. Physical GPU 0 has a materially weaker PCIe link than GPU 1** --
hardware, not a bug. GPU 0: PCIe Gen3, 4 lanes negotiated; GPU 1: PCIe
Gen4, 8 lanes (confirmed via `nvidia-smi -q` / `lspci`). `moe-expert-cache-size`'s
constant host-to-GPU streaming is directly PCIe-bandwidth-bound, so this
hits Flash Next especially hard (6.34-6.6 vs 18.87 tok/s, same config,
only the physical GPU differs). See the schwerz-16gb service-role note
above.

**2. `render-compose.py` silently overrode `n-gpu-layers = auto` (real
refactor bug, fixed).** The new refactor's `upstream_command()`
unconditionally passed a router-level `--n-gpu-layers all` for every
GPU-enabled profile, overriding preset-level `n-gpu-layers = auto` -- the
partial-CPU-offload setting the two dense 70B-class entries depend on to
fit at all. Real failure: `"n_gpu_layers already set by user to -2,
abort"`, then an immediate CUDA OOM trying to force the whole model onto
one GPU. Fixed by removing the unconditional flag; GPU profiles now pass
no system-level `--n-gpu-layers`, letting each model's own preset value
apply. Confirmed working: both 70B models load and answer, 4.78/4.57 tok/s
decode, swap flat throughout.

**3. `DeepSeek-Coder-V2-Lite-Instruct-Q4_K_M`'s single-GPU `ctx-size` was
never actually tested (pre-existing gap, not a refactor bug).** The
original failure's two hypotheses were both wrong -- the real cause: at
`ctx-size=65536`, the KV buffer request (8.97 GiB) plus the 9.65 GiB
weight file exceeds one 16,311 MiB card outright. A plain, untested
capacity shortfall. Backed off to `ctx-size=32768`, confirmed working.

## Higher quants downloaded, curated, and real-load-tested

Higher quants of several dense models (qwen2.5-coder 7b/14b, Devstral x2)
downloaded to use real headroom their Q4_K_M entries left, and real-load-
tested on both single- and dual-GPU placements -- see the summary table
above for every resulting figure. Real, notable: `Devstral-Small-2505`
decodes faster than `Devstral-Small-2-24B-Instruct-2512` at every matching
quant level despite identical file sizes/VRAM footprints -- a real
difference between the two releases, not measurement noise.

## Test plan results: 26 tests run via `run-remaining-tests.sh`

- **`llama-cpp-gpu-0`/`gpu-1` (16GB service)** -- 10/10 attempted, 9
  succeeded. One real failure: `Qwen3.8-27B-UD-Q4_K_M` doesn't fit solo
  (see "Single-GPU-pinned variants" above).
- **`llama-cpp-all-gpus` (32GB service)** -- 16/16 attempted, 14
  succeeded. Two real near-misses handled via the RAM-audit/prune passes
  above.
- **`llama-cpp-cpu`** -- 2/2 attempted, both succeeded but dramatically
  slow (Devstral, see footnote ² above: dense-vs-MoE sparsity is the real
  architectural reason). **CPU is not viable for these models in agentic
  use**, despite technically working.
- **`llama-cpp-generel-schwerz-32gb`** -- out of scope this pass,
  intentionally excluded at the user's request.

### Outstanding MoE performance questions

1. ~~Does dual-GPU placement help a *fully GPU-resident* MoE model the way
   it helps dense models?~~ **Resolved**: `gpt-oss-20b-F16` real
   single-vs-dual numbers (63.76 -> 141+ tok/s) answered this for
   tensor-split. `DeepSeek-Coder-V2-Lite-Instruct-Q4_K_M`'s layer-split
   single-GPU test reframed the question: it failed to load at all (see
   footnote ¹ context above), a hard single-GPU placement problem, not a
   bandwidth comparison.
2. ~~Does dual-GPU placement help an `n-cpu-moe`-*offloaded* model?~~
   **Resolved**: yes, substantially, and it generalizes across all seven
   `n-cpu-moe`-offloaded 30-35B models in the fleet (all fit fully
   GPU-resident, no offload). Real speedup range 1.6x-2.3x over the
   single-GPU offloaded figure -- see the summary table above for all
   seven pairs.
3. **Does schwerz's `moe-cache` actually outperform plain `--n-cpu-moe`
   for the same large (>32 GiB) model?** Still genuinely untested --
   blocked on a curated `n-cpu-moe` entry for a model this large existing
   on a plain service to compare against the existing 16GB-schwerz
   figures (8.11-8.80 tok/s for gpt-oss-120b).

### Quant-ladder check: underutilized dual-GPU entries

Checked whether the underutilized dual-GPU entries (real headroom left
over) are missing a better download or already at the right quant --
findings folded into each model's own preset comment where a real ladder
gap exists (e.g. `DeepSeek-Coder-V2-Lite-Instruct`'s Q8_0 upgrade,
downloaded and curated).

### Anomalies (all resolved)

- `Qwen3.6-35B-A3B-Q4_K_M`'s cold-run slowdown and `Qwen3.8-27B-UD-Q6_K_M`'s
  asymmetric cold-run GPU utilization were both one-off timing artifacts,
  not real placement problems -- clean repeat runs landed in line with
  every peer figure and showed no asymmetry.

## Still open (noticed, not explained)

- `Qwen3-Coder-Next`'s 59% vs 12% GPU utilization asymmetry between two
  identical RTX 5060 Tis on the 32GB schwerz service. Could be genuine
  grouped-layer imbalance or a memory-pressure artifact (that service was
  swap-thrashing at the time) -- needs `--experimental-logs --verbosity 4`
  telemetry to resolve, not another utilization snapshot. Out of scope
  while the 32GB schwerz service itself is excluded.

## Full 64K context-floor sweep + DeepSeek-Coder-V2-Lite migration

User policy: 64K (65536) is the coding-use context floor across every
curated model.

**DeepSeek-Coder-V2-Lite-Instruct-Q4_K_M**: removed from `llama-cpp-16gb`
(65536 fails outright single-card; 32768 was the safe fallback, under the
floor). Raised to 163840 on `llama-cpp-32gb` (its real native ceiling,
GGUF metadata) -- confirmed working, ~1.5 GiB headroom/card. Real quant
ladder (bartowski): Q5_K_M 11.85 GB, Q6_K 14.07 GB, Q8_0 16.70 GB --
**Q8_0 recommended**, near-lossless and fits real headroom easily.

**Five CPU models raised to 65536** (`gemma-3n-E2B-it`/`E4B-it`,
`NVIDIA-Nemotron-3-Nano-4B`, `Qwen3.5-9B`, `Ornith-1.5-9B`) -- all
confirmed working individually with live RAM monitoring, no pressure.

**Full sweep**: every other model below 65536 across `llama-cpp-16gb` and
`llama-cpp-32gb` (18 models total, including the two 70B dense models with
partial CPU offload) raised and live-tested. **Every one fit with real
headroom -- zero migrations needed.** Full per-model VRAM/RAM figures
folded into the summary table above.

Flagged, not fixed: `generate-models-preset.py`'s full-discovery mode
targeted the pre-refactor `llama-cpp-all-gpus` compose service and was
broken until the later tooling fix below. `settings.yaml`'s `llama-cpp`
(32gb) provider block had four stale entries referencing model IDs
unreachable on that service -- also fixed below.

## 128K assessment, YaRN correctness fix, Q8 DeepSeek-Coder-V2-Lite, tooling fix

**Real native-context finding**: the qwen2.5-coder family's GGUF
`context_length=131072` metadata is not authoritative -- the real upstream
HF config confirms native training context is **32768**, no RoPE scaling
defined. Same confirmed independently for `Qwen2.5-72B-Instruct-Q3_K_S`.
Both had been running 2-4x past their native window with no scaling
configured; the load tests that passed only sent trivial short prompts,
which says nothing about coherence past position 32768. Fixed with
explicit `rope-scaling=yarn` + `yarn-orig-ctx=32768`, verified with a real
needle-in-haystack test (43K-token prompt, correct retrieval past the
boundary). `Llama-3.3-70B` is unaffected (genuinely native 131072, real
Llama-3.1+ long-context training).

**128K assessment**: every 64K-capped model live-tested at 131072. All fit
-- zero needed to move from one GPU to both. Two needed a higher
`n-cpu-moe` to fit (`Qwen3-Coder-30B-A3B` 18->26, `Laguna-XS-2.1` 16->22);
two others fit but are tight (`North-Mini-Code-1.0`, `granite-4.0-h-small`,
~1.2-1.3 GiB free). Now the deployed defaults.

**Two 70B dense models**: real decode 2-2.75 tok/s, a structural hardware
bottleneck (CPU offload on every token), an order of magnitude slower than
the fleet's MoE alternatives. Removed (see "Rejected models" above).

**Q8_0 DeepSeek-Coder-V2-Lite**: downloaded (16.70 GB), curated alongside
Q4_K_M (not replacing it), confirmed fitting at `ctx=163840` with
near-identical VRAM footprint to Q4_K_M. Genuine baked-in YaRN metadata
(`deepseek2.rope.scaling.*`), no manual scaling needed.

**Tooling fix**: `generate-models-preset.py`'s full-discovery mode was
targeting the removed `llama-cpp-all-gpus` compose service. The
`render-compose.py` refactor had consolidated it into the plain
`llama-cpp` template service in `compose.ai.yml`, which already reads the
same env vars the discovery function sets, just under a different name.
Fixed with a two-line change (point at `compose.ai.yml` directly; use the
`llama-cpp` service name); verified with a real `--force` run.

**`settings.yaml` cleanup**: removed four dead entries referencing
unreachable model IDs on the `llama-cpp` (32gb) provider; added two real
entries that were missing (`qwen2.5-coder-7b/14b-instruct-q4_k_m` exist on
`llama-cpp-16gb` but had no DSH route). All `contextWindow` values updated
to match the 128K changes.

## Seven full-GPU-resident MoE counterparts added and tested

Closed the "does dual-GPU help an n-cpu-moe-offloaded model" question for
all seven models it applied to (not just Ornith, which originally raised
it) -- see the summary table above and footnote ⁵ context for each pair
and the real 1.6x-2.3x speedup range.

## Maximising performance on a single card: Qwen3.8-27B 3-bit quants (2026-09-20)

A single-GPU 3-bit quant (`Qwen3.8-27B-UD-IQ3_S` / `-UD-Q3_K_XL` on
`llama-cpp-gpu-1`) only earns its keep if the second physical GPU is free
for something else -- otherwise forcing the same quant onto both cards, or
running `Qwen3.8-27B-UD-Q6_K_M` dual-GPU instead, is strictly better.

### The three-way tradeoff

| Config | Decode, short context | Decode, ~8,256 populated tokens | Second card |
|---|---|---|---|
| IQ3_S, single GPU | 30.64-30.69 tok/s | 28.46 tok/s | free |
| IQ3_S, forced dual-GPU (`split-mode=tensor`) | 47.50-47.55 tok/s | 45.81 tok/s | occupied |
| Q3_K_XL, single GPU | 28.91-28.92 tok/s | 27.07 tok/s | free |
| Q3_K_XL, forced dual-GPU (`split-mode=tensor`) | 45.53-45.63 tok/s | 43.99 tok/s | occupied |
| Q6_K_M, forced dual-GPU (`split-mode=tensor`) | 30.16-31.05 tok/s | 30.21 tok/s | occupied |

If the second card is genuinely idle, the choice isn't automatically
Q6_K_M: Q3 dual-GPU is ~35% faster than Q6_K_M dual-GPU and holds decode
flat with context depth just as well, at the cost of 3-bit rather than
6-bit weights. Single-GPU placement is only worth its real throughput cost
when the second card's other use is worth more than that gap.

### `ctx-size` tuning: not a gradual tradeoff

Decode at a fixed ~8,256-token prompt, single GPU, varying only
`Qwen3.8-27B-UD-Q3_K_XL`'s `ctx-size`:

| `ctx-size` | Decode @ 8,256 populated tokens |
|---|---|
| 32768 | 27.49 tok/s |
| 65536 | 27.07 tok/s |
| 73728 | 17.20 tok/s |
| 81920 | 12.06 tok/s |
| 94208 | 8.29-8.45 tok/s (reproduced) |
| 131072 (original) | 9.25 tok/s |

There's a real cliff between 65536 and 73728, not a smooth falloff --
94208 is statistically indistinguishable from the original, unfixed
131072 ceiling. A smaller `ctx-size` only helps up to the cliff; past it,
you're paying for context you can't actually use at a useful decode speed.

### Full depth sweep at the deployed `ctx-size=65536`

Both models, single GPU, `ctx-size=65536` (the deployed value as of
2026-09-20):

| Populated tokens | IQ3_S decode | Q3_K_XL decode |
|---|---|---|
| 8,256 | 28.46 tok/s | 27.07 tok/s |
| 16,448 | 27.09 tok/s | 26.20 tok/s |
| 32,832 | 24.69 tok/s | 23.98 tok/s |
| 49,216 | 22.60 tok/s | 22.06 tok/s |
| 65,088 | 20.95 tok/s | 20.48 tok/s |

Both models decline gradually and almost identically once `ctx-size` is
capped at the real ceiling -- no remaining cliff, and the two models track
each other closely despite Q3_K_XL's larger file size.

**Deployed**: both models' `ctx-size` lowered to 65536 on `llama-cpp-16gb`
(from 98304 for IQ3_S, 131072 for Q3_K_XL).

## gpt-oss-120b: plain n-cpu-moe vs. schwerz expert-cache (2026-09-20)

`gpt-oss-120b` (58.44 GiB) previously only ran on `llama-cpp-generel-
schwerz-16gb`, using that fork's own CUDA expert-cache to manage the
host/GPU split. It had never been tried on the plain upstream services
via the stock `--n-cpu-moe` offload flag already used for the eight-model
MoE cluster on `llama-cpp-16gb`.

### schwerz's own expert-cache vs. plain n-cpu-moe, matched depths

| Service | Decode @ ~2K tokens | Decode @ ~16K tokens |
|---|---|---|
| `llama-cpp-generel-schwerz-16gb` (expert-cache) | -- | 9.10 tok/s |
| `llama-cpp-gpu-1` (`n-cpu-moe=29`, ctx-size=65536) | 18.73 tok/s | 20.59 tok/s |

Plain `n-cpu-moe` more than doubles schwerz's own decode for this model,
at matched context depths, and shows no degradation with depth (if
anything a slight improvement, consistent with fixed per-request overhead
amortizing over more tokens). Not a general verdict on the fork -- Flash
Next's own tuned schwerz config is real and separately verified -- but
true for this specific model on this build.

### 128K context validated on both upstream services

`ctx-size=65536`'s `n-cpu-moe=29` (14,758 MiB used, ~1.5 GiB headroom on
one 16 GiB card) was not enough headroom for `ctx-size=131072` -- failed a
real load short by ~731 MiB, the same small-late-buffer OOM class seen
elsewhere in this document. Raised to `n-cpu-moe=31` for the 16GB service;
the 32GB service still worked at `n-cpu-moe=29` (the second card absorbs
some of the extra headroom demand even though the model's weights
themselves don't actually spread across it -- see below).

| Service | `n-cpu-moe` | VRAM @ ctx=131072 | Decode @ ~49K tokens | Decode @ ~115K tokens |
|---|---|---|---|---|
| `llama-cpp-gpu-1` (single GPU) | 31 | 12,812 MiB (~3.5 GiB headroom) | 15.61 tok/s | 14.52 tok/s |
| `llama-cpp-all-gpus` (dual GPU) | 29 | GPU0: 2,865 MiB, GPU1: 14,156 MiB | 14.76 tok/s | 14.51 tok/s |

Gradual decline in both cases, no cliff -- 128K is safe to deploy on
either service at these `n-cpu-moe` values.

### Dual-GPU does not meaningfully help this model

Tried to get the 32GB service to spread `gpt-oss-120b`'s non-offloaded
weight across both cards for more real capacity: `n-gpu-layers=auto`
(instead of `all`), explicit `split-mode=layer`, and an explicit even
`tensor-split=1,1`. All three produced the byte-identical failure --
`--fit` refuses to run at all once `n-cpu-moe` sets tensor overrides
(`tensor_buft_overrides already set by user, abort`), and without `--fit`,
the model's entire non-offloaded weight lands as one non-splittable
~27.7 GiB buffer targeting a single device, regardless of any of those
three flags. The only way to make it fit at all is the same lever as
single-GPU: raise `n-cpu-moe` until that one chunk fits on whichever
device it lands on.

Real cost of using the second card anyway (for the modest extra headroom):
decode is statistically unchanged from single-GPU (14.51-14.76 tok/s vs.
14.52-15.61 tok/s at matched depths), but prefill is substantially worse
(194-199 tok/s vs. 455-572 tok/s at matched depths) -- the same
layer-split cross-device prefill penalty already documented elsewhere in
this file for dense models under `split-mode=tensor` comparisons.
**Recommendation: use the 16GB service for this model, not the 32GB one**
-- no decode benefit, real prefill cost, and the 32GB service's second
card is better spent on a model that can actually use it.

### Worth testing next, in light of this result

Plain `n-cpu-moe` beating a purpose-built expert-cache fork by 2x+ is
surprising enough to be worth checking against the fork's other
last-resort models, none of which have been tried this way:

- **`Llama-4-Scout-17B-16E`**: currently fails to load under every
  condition tested on schwerz-16gb (see "16GB schwerz service" above) --
  never tried via plain `n-cpu-moe` on the upstream services. Highest-value
  untested candidate: it's completely non-functional today, so there's
  nothing to lose.
- **`GLM-4.5-Air-UD-Q4_K_XL`**: currently works on schwerz-16gb only via
  the `cache-type-k/v=q4_0` fix, at 2.69-3.25 tok/s -- slow enough that a
  2x+ win from plain `n-cpu-moe` (matching gpt-oss-120b's pattern) would be
  a large practical difference, not a marginal one.
- **`Qwen3-Coder-Next-Q4_K_M`** and **`Qwen3-Next-80B-A3B-Instruct-Q4_K_M`**:
  currently only run on schwerz-16gb (~31 tok/s) or CPU (9-13 tok/s) --
  never tried on a plain GPU service via `n-cpu-moe`. Real potential
  upside given the pattern above, though these are large enough (46 GiB
  each) that the achievable `n-cpu-moe` value needs real testing, not an
  assumption it'll be as favorable as gpt-oss-120b's ratio.
- **`Qwen3.8-Flash-Next-UD-Q3_K_XL`** is the lower-priority comparison of
  the four -- it already has a real, specifically-tuned schwerz config
  (batch/ubatch tuning, +125% prefill/+9% decode documented above), unlike
  the other three which are running on untuned defaults. Still worth one
  real comparison point given how large gpt-oss-120b's gap turned out to
  be, but don't expect the same magnitude of win.
- **New downloads**: this result changes what's practical to consider.
  Before today, a ~58 GiB MoE model looked like a last-resort, single-
  digit-tok/s proposition on this hardware (schwerz's own 8-9 tok/s). At
  14-20 tok/s via plain `n-cpu-moe`, models in that same rough weight
  class are now a real, usable option, not just a capacity curiosity --
  worth factoring into future download decisions, though no specific new
  model is recommended here without the same real load-and-decode testing
  this finding is itself built on.

## Qwen3-Next-80B-A3B-Instruct: CPU long-context check (2026-09-20)

Real long-context figure for the existing CPU deployment, requested
alongside the gpt-oss-120b work above:

| Populated tokens | Prefill | Decode |
|---|---|---|
| 2,082 | 46.76 tok/s | 9.33 tok/s |
| 16,418 | 32.57 tok/s | 8.46 tok/s |

A real but gentle decline, not a cliff -- consistent with ordinary
memory-bandwidth-bound CPU decode. No config change made; the existing
`ctx-size=65536` CPU entry already covers this range.

## Second batch: five more models via plain n-cpu-moe, all validated to 128K (2026-09-21)

Following the gpt-oss-120b result above, the same five models flagged as
"worth testing next" were tested via plain `--n-cpu-moe` on both
`llama-cpp-gpu-1` and `llama-cpp-all-gpus`, at low (~2K), high (~16K), and
128K (~49K populated tokens) depth. All five now have deployed entries on
both plain services (see those files' own headers).

| Model | Service | `n-cpu-moe` @ 65536 | Decode low/high @ 65536 | `n-cpu-moe` @ 131072 | Decode @ 128K/~49K |
|---|---|---|---|---|---|
| Llama-4-Scout-17B-16E | `llama-cpp-gpu-1` | 46 | 8.80 / 8.42 tok/s | 46 | 8.09 tok/s |
| Llama-4-Scout-17B-16E | `llama-cpp-all-gpus` | 46 | 7.71 / 8.03 tok/s | 46 | 7.57 tok/s |
| GLM-4.5-Air | `llama-cpp-gpu-1` | 46 | 7.31 / 7.15 tok/s | 46 + `cache-type-k/v=q4_0`¹ | 2.41 tok/s |
| GLM-4.5-Air | `llama-cpp-all-gpus` | 46 | 5.73 / 5.86 tok/s | 46 + `cache-type-k/v=q4_0`¹ | 2.40 tok/s |
| Qwen3-Coder-Next | `llama-cpp-gpu-1` | 40 | 37.19 / 35.32 tok/s | 42 | 29.94 tok/s |
| Qwen3-Coder-Next | `llama-cpp-all-gpus` | 40 | 36.06 / 34.14 tok/s | 40 | 30.33 tok/s |
| Qwen3-Next-80B-A3B-Instruct | `llama-cpp-gpu-1` | 40 | 37.36 / 35.21 tok/s | 42 | 30.63 tok/s |
| Qwen3-Next-80B-A3B-Instruct | `llama-cpp-all-gpus` | 40 | 35.96 / 34.02 tok/s | 40 | 30.21 tok/s |
| Qwen3.8-Flash-Next | `llama-cpp-gpu-1` | 46 | 14.97 / 16.06 tok/s | 50 | 12.11 tok/s |
| Qwen3.8-Flash-Next | `llama-cpp-all-gpus` | 46 | 17.66 / 15.87 tok/s | 46 | 13.64 tok/s |

¹ Not an expert-offload problem -- `n-cpu-moe` alone (up to 54 tried) never
fixed this; the real cause is GLM-4.5-Air's KV cache alone wanting ~12.5
GiB at `ctx-size=131072` (confirmed via a real "failed to allocate buffer
for kv cache" OOM), independent of expert placement entirely. KV
quantization was the only lever that helped, same fix already deployed on
`llama-cpp-generel-schwerz-16gb` for this model.

Four of five beat their existing schwerz-16gb/CPU placements decisively;
Flash Next roughly ties its own already-tuned schwerz entry rather than
beating it (12.11-17.66 here vs. schwerz's 12.67-18.38 tok/s) -- expected,
since it's the one model in this batch with real prior tuning work behind
its schwerz config. Dual-GPU (`llama-cpp-all-gpus`) is a wash or a real
loss for decode in four of five cases here, consistent with the earlier
gpt-oss-120b finding -- Flash Next is the one exception, decoding slightly
*faster* dual-GPU than single (a genuine, if small, real difference, not
noise: consistent across both the 65536 and 131072 conditions).

## Two new downloads: Ling-3.0-Flash and Solar-Open-100B (2026-09-21)

Downloaded specifically because of the active-parameter pattern the
gpt-oss-120b result established (large total size, small active-parameter
count is what this hardware handles well) -- see the recommendation this
document doesn't itself carry, made directly to the user, for the research
behind picking these two. Real-tested on all three services that can host
a model this size: both plain upstream services and schwerz-16gb.

| Model | Service | `n-cpu-moe`/cache @ 65536 | Decode low/high @ 65536 | @ 131072 | Decode @ 128K/~49K |
|---|---|---|---|---|---|
| Ling-3.0-flash (127B/5.1B active) | `llama-cpp-gpu-1` | `n-cpu-moe`=38 | 11.09 / 18.36 tok/s | `n-cpu-moe`=40 | 11.12 tok/s |
| Ling-3.0-flash | `llama-cpp-all-gpus` | `n-cpu-moe`=38 | 11.43 / 17.17 tok/s | `n-cpu-moe`=38 | 10.53 tok/s |
| Ling-3.0-flash | schwerz-16gb | `moe-expert-cache-size`=10 | 5.68 / 7.21 tok/s | `moe-expert-cache-size`=10 | 5.36 tok/s |
| Solar-Open-100B (102B/12B active) | `llama-cpp-gpu-1` | `n-cpu-moe`=46 | 9.64 / 8.76 tok/s | `n-cpu-moe`=54 + `cache-type-k/v=q4_0`¹ | 3.48 tok/s |
| Solar-Open-100B | `llama-cpp-all-gpus` | `n-cpu-moe`=46 | 9.22 / 8.57 tok/s | `n-cpu-moe`=54, no KV quant needed | 6.23 tok/s |
| Solar-Open-100B | schwerz-16gb | `moe-expert-cache-size`=8 | 4.83 / 4.58 tok/s | `moe-expert-cache-size`=8 + `cache-type-k/v=q4_0`¹ | 2.49 tok/s |

¹ Same large-KV-cache issue as GLM-4.5-Air above -- Solar-Open-100B is in
the same 12B-active-parameter class and hits the same wall on the
single-GPU service. Notably, `llama-cpp-all-gpus` does NOT need the quant
for this model -- the second card's extra headroom covers the gap that
forced the quant single-GPU, the one case in either batch where dual-GPU
measurably helps reach 128K rather than just adding a wash.

Both confirm the pattern: plain `n-cpu-moe` on the upstream services beats
schwerz-16gb's own expert-cache by roughly 2x for both new models, same as
every model in the first batch except Flash Next. Ling-3.0-flash's own
decode-vs-depth shape is real and non-monotonic (11.09 -> 18.36 -> 11.12
tok/s), the clearest single example of the pattern discussed below.

## Does decode really improve at higher context for some offloaded models?

A real, reproducible pattern across several models in both batches: decode
at ~16K populated tokens is *higher* than at ~2K, before declining again
by 128K. Clearest example, Ling-3.0-flash on `llama-cpp-gpu-1`: 11.09 tok/s
(2K) -> 18.36 tok/s (16K) -> 11.12 tok/s (128K/49K). Also visible, smaller:
gpt-oss-120b (18.73 -> 20.59 tok/s, 2K->16K, in the first-batch table
above), Llama-4-Scout (7.71 -> 8.03 tok/s dual-GPU).

This is not "more compute time per token reduces expert-swap rate" --
MoE routing re-selects experts fresh at every generated token regardless
of how much context precedes it, so a longer prior context doesn't reduce
how often experts get swapped for the *next* token. The more likely
explanation, consistent with a pattern already documented elsewhere in
this file (prefill throughput measured on short vs. long prompts): a short
request's decode/request-timing figure is measured over relatively few
output tokens against a large fixed per-request overhead (connection
setup, initial cache/graph work), which depresses the computed tok/s more
at low depth than the real steady-state rate. Once through that overhead,
decode reflects the real rate more accurately -- until populated context
grows enough that the attention-over-cached-tokens cost genuinely starts
to dominate, which is the decline back down by 128K. Not confirmed by a
controlled test isolating request overhead from steady-state decode
specifically -- a real next step if this shape matters for scheduling
real workloads, not just benchmark interpretation.

## PCIe generation as a real factor in dual-GPU MoE-offload decode

Already documented elsewhere in this file: physical GPU 0 is PCIe Gen3 x4,
GPU 1 is PCIe Gen4 x8, and `moe-expert-cache-size`'s constant host-to-GPU
streaming on schwerz-16gb is directly bandwidth-bound by whichever card it
runs on (Flash Next: 18.87 tok/s on GPU 1 vs. 6.34-6.6 tok/s on GPU 0,
same config, ~3x regression from card choice alone).

This is a real, plausible explanation for part of why `llama-cpp-all-gpus`
(dual-GPU, plain `n-cpu-moe`) underperforms single-GPU decode in most of
the models tested in both batches above, and for why the 32GB schwerz
service (`codex/moe-grouped-multigpu`, genuinely relying on both cards for
placement rather than mostly parking weight on one) has never produced a
usable result on this host at all -- though that service's own failures
are dominated by a separate, already-diagnosed cause (`load-mode=none`
forcing full swap-thrashing on anything over physical RAM, see "32GB
schwerz service" above), so PCIe asymmetry has not been isolated as a
distinct contributor there specifically. For `llama-cpp-all-gpus`
specifically, the already-documented cause is more direct: this session's
own gpt-oss-120b investigation found the non-offloaded weight lands as one
non-splittable buffer on a single device (confirmed unchanged across
`split-mode` and `tensor-split`), so the real question isn't "how is
traffic balanced between two cards" so much as "which one card got
picked" -- and if that automatic choice isn't already preferring the
faster card, PCIe asymmetry would show up exactly as a decode regression
without any obvious per-model cause, matching what's observed.

**Is there a way to prioritize the faster card for offloaded experts?**
Not a documented one in stock llama.cpp as far as this investigation
found. `--main-gpu` affects which device handles certain single-device
operations, and `--tensor-split`/`split-mode` control how *resident*
layers are divided across visible devices -- neither controls which
physical device `--n-cpu-moe`'s host-to-GPU expert streaming lands on
per-layer; that appears to follow the same general layer-placement/device
order as everything else, confirmed by this session's own real test
finding `tensor-split=1,1` had zero effect on gpt-oss-120b's placement.
The one real lever available is `CUDA_VISIBLE_DEVICES` ordering, already
used deliberately elsewhere in this deployment (schwerz-16gb's whole "must
run on physical GPU 1" finding) -- for a *single*-GPU service, listing
only the faster card guarantees it's used; this doesn't generalize to
making a *dual*-GPU service prefer one card over the other for MoE
placement specifically. This remains genuinely open -- the schwerz-16gb
GPU-0-vs-GPU-1 finding is the closest this deployment has to a real
measurement of the effect, not a demonstrated fix for the dual-GPU case.
