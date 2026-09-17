# Local llama.cpp performance findings

Durable record of every real performance measurement taken across the local
llama.cpp deployments (plain `llama-cpp`, the GenerelSchwerz MoE-cache forks,
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

| Model | Service | GPU 1 | GPU 2 | RAM | CPU | Prefill | Decode |
|---|---|---|---|---|---|---|---|
| gpt-oss-20b-F16 | standalone, 1 GPU pinned | ~13.3 GiB | not exposed | baseline only | idle | 3,802 tok/s | 63.76 tok/s |
| Qwen3.8-Flash-Next (tuned cfg) | 16GB schwerz | 13.4 GiB¹ | not exposed | 4.8 GiB + 56 GiB mmap cache¹ | idle | 196.00 tok/s² | 12.67-18.38 tok/s⁵ |
| Qwen3-Coder-Next | 16GB schwerz | 7.5 GiB | not exposed | 49 GiB + 52 GiB mmap cache³ | idle | 58.72 tok/s | 31.12-31.29 tok/s |
| Qwen3-Next-80B-A3B-Instruct | 16GB schwerz | 7.5 GiB | not exposed | 49 GiB + 55 GiB mmap cache³ | idle | 62.98 tok/s | 31.81-32.00 tok/s |
| gpt-oss-120b | 16GB schwerz | 7.1 GiB | not exposed | 4.0 GiB + 54 GiB mmap cache | idle | 11.06 tok/s | 8.11-8.80 tok/s |
| Llama-4-Scout-17B-16E | 16GB schwerz | **CUDA OOM** | not exposed | -- | -- | failed to load | failed to load |
| GLM-4.5-Air | 16GB schwerz | **CUDA OOM** | not exposed | -- | -- | failed to load | failed to load |
| gpt-oss-120b | 32GB schwerz (grouped-multigpu) | 3.8 GiB | 4.0 GiB | 60/60 GiB (swap-maxed) | some (swap I/O) | 2.20 tok/s⁴ | 2.36-3.01 tok/s⁴ |
| GLM-4.5-Air | 32GB schwerz (grouped-multigpu) | 10.1 GiB | 10.1 GiB | 60/60 GiB (swap-maxed) | some (swap I/O), 0% GPU compute | 1.68 tok/s⁴ | 1.01-1.39 tok/s⁴ |
| Qwen3-Coder-Next | 32GB schwerz (grouped-multigpu) | 2.7 GiB | 2.8 GiB | 48 GiB (partial swap) | some (swap I/O) | 19.87 tok/s | 7.43-7.44 tok/s |
| Qwen3.8-27B-UD-Q4_K_M | plain llama-cpp (dense, tensor-split) | 10.6 GiB (97-98% util) | 10.6 GiB (97% util) | baseline only | idle | 68.13 tok/s⁷ | 39.11-40.62 tok/s⁷ |
| Qwen3.8-27B-UD-Q6_K_M | plain llama-cpp (dense, tensor-split) | 14.3 GiB | 14.3 GiB | baseline only | idle | 184.80 tok/s⁶ | 30.16-31.05 tok/s |
| gpt-oss-20b-F16 | CPU-only (`llama-cpp-cpu`) | not exposed | not exposed | 19 GiB | **compute (8 threads)** | 68.06 tok/s | 10.42-10.43 tok/s |
| Ornith-1.5-35B-A3B | CPU-only (`llama-cpp-cpu`) | not exposed | not exposed | 22 GiB | **compute (8 threads)** | 82.26 tok/s | 16.09-16.22 tok/s |
| Qwen3-Coder-Next | CPU-only (`llama-cpp-cpu`) | not exposed | not exposed | 37 GiB | **compute (8 threads)** | 11.18 tok/s | 9.17-13.33 tok/s |
| Qwen3-Next-80B-A3B-Instruct | CPU-only (`llama-cpp-cpu`) | not exposed | not exposed | 37 GiB | **compute (8 threads)** | 9.23 tok/s | 9.98-13.24 tok/s |

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
were at 97-98%. Plausibly the small prompt finished before the snapshot
caught GPU 1 doing its share, not necessarily a real placement problem, but
unconfirmed either way. The session-derived step-duration figure previously
here (model-only step median 24.6s->18.0s, mean 91.5s->45.1s,
`split-mode=tensor` before/after) is still the only *real-session* data
point and remains in the "Plain `llama-cpp` service" section below -- it
also confounds `reasoning-effort=low` going live in the same window, so
it's a different kind of evidence from the clean benchmark figures here,
not a contradiction of them.
⁷ Re-run 2026-09-17 to replace the dated/accidental 2026-09-14 test (see the
"Plain `llama-cpp` service" section below) with a properly current figure --
cold prefill 68.13 tok/s, decode 39.11 tok/s, warm decode 40.62 tok/s. Closely
corroborates the 09-14 numbers (56.78 prefill, 40.50-40.66 decode) rather
than contradicting them: same VRAM footprint (10555/10640 MiB, 97-98% both
cards), decode essentially identical, prefill within normal run-to-run
variance. Nothing material changed for this quant's dense dual-GPU
performance between the two dates. Table figures above are the 09-17
re-run; the original 09-14 numbers are kept in the detailed section below
as corroborating evidence, not superseded/wrong.

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

## Plain `llama-cpp` service (dense, both GPUs via `split-mode=tensor`)

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

gpt-oss-120b (62.8 GiB) and GLM-4.5-Air (67.7 GiB) both exceed this host's
60 GiB RAM on file size alone, before KV cache or the cache mechanism's own
bookkeeping. Under `load-mode=none` there was never a scenario where either
fits -- the 2-3 tok/s figures above are disk-swap I/O speed, not model or
cache speed. Qwen3-Coder-Next (46 GiB) partially avoided full catastrophe
because it's small enough to mostly fit even without mmap's elasticity, and
its numbers are the least broken of the three -- but it was still touching
swap and its GPU utilization was asymmetric between two otherwise-identical
cards (59% vs 12%), which is itself unexplained (see "Still open" below).

**Fix applied**: Flash Next is deliberately excluded from the 32GB
catalogue's model list entirely (mmap is fundamental to its viability and
this branch forbids it; even if it somehow fit, this branch's benefit is
decode-only and Flash Next's dominant cost has always been prefill). The two
other oversized models were moved to the 16GB service instead, where mmap is
available, with `load-mode=mmap`/`lazy-mode=on` added per-model.

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

## Currently untested / no data exists

- **The grouped-multigpu cache's real decode benefit** -- no clean number
  exists yet; every 32GB run so far was memory-bound, not compute-bound.
  `Ornith-1.5-35B-A3B` is the priority retest: it's the one model with a real
  external reference point (the fork's own validation reported 39.6 tok/s
  equal-split / 38.8 tok/s at an uneven split, on different GPU hardware, not
  directly comparable but a real number to check against). `--experimental-
  logs --verbosity 4` should be enabled in `32gb.ini` before that retest --
  not done yet -- so the fork's own `moe-grouped-owner`/`moe-grouped-plan`
  telemetry can confirm genuine cross-GPU dispatch rather than inferring it
  from `nvidia-smi` utilization snapshots (which is how Coder-Next's
  59%-vs-12% asymmetry was noticed but not explained).
- ~~CPU-only decode rates~~ -- resolved 2026-09-17, see the "CPU-only" section
  above. (`settings.yaml`'s comment referencing "prior testing" never left
  any recoverable figures; the numbers above are a fresh measurement, not a
  recovered one -- the `llama-cpp-cpu` service had never actually been
  started on this host before this round.)
- gpt-oss-120b / Llama-4-Scout / GLM-4.5-Air on the 16GB service, properly
  isolated prefill/decode from a clean memory state (the mmap fix above was
  only sanity-checked, not benchmarked).

## Still open (noticed, not explained)

- Qwen3-Coder-Next's 59% vs 12% GPU utilization asymmetry between two
  identical RTX 5060 Tis on the 32GB service. Could be genuine grouped-layer
  imbalance, could be an artifact of the memory pressure it was also under.
  Not resolved -- needs the experimental-logs telemetry, not another
  utilization snapshot.
