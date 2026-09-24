# Unified upstream llama.cpp router

`models-preset.ini` is the sole model catalogue for the unified upstream
`llama-cpp` service.  It materialises the settings from the former upstream
16GB, 32GB, and CPU catalogues so that every router worker has complete,
per-model placement.

## Variant IDs and resources

Every model ID ends in exactly one resource suffix:

| Suffix | llama.cpp placement | Resources used |
| --- | --- | --- |
| `--cuda0` | `device = CUDA0`, `split-mode = none` | GPU 0 |
| `--cuda1` | `device = CUDA1`, `split-mode = none` | GPU 1 |
| `--cuda0-cuda1` | `device = CUDA0,CUDA1` | GPUs 0 and 1 |
| `--cpu` | `device = none`, `n-gpu-layers = 0` | CPU only |

The CUDA names are llama.cpp device names, not a second Docker-level device
selection.  Validate that `CUDA0` and `CUDA1` match the intended physical
cards with `llama-server --list-devices` in the built image before deployment.

The suffix only selects placement.  Nothing enforces it as a resource claim:
there is no separate scheduler, and llama.cpp does not track which GPU or how
much host RAM a model occupies.  Models with `n-cpu-moe` and `--cpu` models
also use host RAM that nothing budgets.

## Router settings

`render-compose.py` starts the router with `--models-max 1 --models-autoload`,
so exactly one model is resident at a time and llama.cpp loads and unloads
models itself.  It also passes `--flash-attn on`, `--fit on` and
`--fit-target`.  The router command line deliberately omits `--device`,
`--split-mode`, and `--n-gpu-layers`, because router command-line arguments
take precedence over model-preset settings.

### Switching models

A request for a model that is not loaded joins a first-in-first-out queue.
llama.cpp then evicts the least recently used model that is ready and has no
request in flight, waits for its worker process to exit (which frees its VRAM),
and starts the requested model.  A model is never evicted while it is
mid-request or still loading, or while another queued request wants it; in
that case the new request waits until the busy model's last request finishes.
A client that disconnects while waiting leaves the queue.

There is no idle timeout, so an idle model stays loaded until another model is
requested.  Because of `--models-max 1`, the `--cuda0` and `--cuda1` variants
cannot run at the same time, even though they use different GPUs.  Every
switch is a full unload and reload, which is slow for the 60-84 GiB models.
Lifting that limit would need a higher `--models-max` (which evicts on count
alone, without knowing which GPU a model uses) or an external scheduler that
does not exist today.

## Catalogue rules

The catalogue uses explicit model paths only.  Do not add `--models-dir` or
discovery to the unified service: it would make unclassified models selectable
without a resource suffix.

## Clients

`vscode-chat-models.json` is a ready-made provider entry for VS Code's
`chatLanguageModels.json`, generated from the model sections in
`models-preset.ini` (regenerate it when models are added or context sizes
change).  Clients must use the full suffixed ID as the model name.
