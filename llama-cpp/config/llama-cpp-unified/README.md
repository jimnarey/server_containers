# Unified upstream llama.cpp router

`models-preset.ini` is the sole model catalogue for the unified upstream
`llama-cpp` service.  It materialises the settings from the former upstream
16GB, 32GB, and CPU catalogues so that every router worker has complete,
per-model placement.

## Variant IDs and resources

Every model ID ends in exactly one resource suffix:

| Suffix | llama.cpp placement | Broker resource claim |
| --- | --- | --- |
| `--cuda0` | `device = CUDA0`, `split-mode = none` | GPU 0 |
| `--cuda1` | `device = CUDA1`, `split-mode = none` | GPU 1 |
| `--cuda0-cuda1` | `device = CUDA0,CUDA1` | GPUs 0 and 1 |
| `--cpu` | `device = none`, `n-gpu-layers = 0` | CPU only |

The CUDA names are llama.cpp device names, not a second Docker-level device
selection.  Validate that `CUDA0` and `CUDA1` match the intended physical
cards with `llama-server --list-devices` in the built image before deployment.

The broker must treat the suffix as an exclusive resource claim: it may run a
`--cuda0` and a `--cuda1` worker together, including Flash Next on `--cuda1`,
but must not overlap either with a `--cuda0-cuda1` worker.  Models with
`n-cpu-moe` and `--cpu` models also require a broker-level CPU budget; llama.cpp
does not provide that admission control.

## Router settings

Compose deliberately keeps only router-wide settings on the service command.
In particular, it must not pass `--device`, `--split-mode`, or
`--n-gpu-layers`, because router command-line arguments take precedence over
model-preset settings.  The service disables autoload so that the broker is the
only component that loads or unloads workers.

The catalogue uses explicit model paths only.  Do not add `--models-dir` or
discovery to the unified service: it would make unclassified models selectable
without a resource suffix or broker policy.
