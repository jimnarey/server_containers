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

## Single-GPU-pinned variants and Nemotron dual-GPU context (2026-09-17)

`split-mode=none` + `main-gpu=N` is the real mechanism for pinning a model
to exactly one specific GPU on the plain `llama-cpp` service, which exposes
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
failed loads on the plain GPU service: a `Qwen3-Coder-Next-Q4_K_M`
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
