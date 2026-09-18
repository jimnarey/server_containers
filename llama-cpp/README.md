# llama.cpp services

All seven llama.cpp services use the single `llama-cpp/Dockerfile`. Their build definitions in `compose.ai.yml` name a repository, branch, commit, and service name. The source stage maintains one neutral clone for each of the three repositories at `LLAMA_SOURCES=/mnt/work/llama-cpp/sources`; the build stage copies that clone to a sibling directory whose suffix is the service name, checks out the requested commit, and builds that copy. The workspace is inside Docker build layers, so it is cacheable but does not modify the host.

| Service | Repository | Commit |
| --- | --- | --- |
| `llama-cpp-gpu-0` | `ggml-org/llama.cpp` | `eafe15a5e3d87dd68ae33acf6a7cbd9415a0ac5e` |
| `llama-cpp-gpu-1` | `ggml-org/llama.cpp` | `eafe15a5e3d87dd68ae33acf6a7cbd9415a0ac5e` |
| `llama-cpp-all-gpus` | `ggml-org/llama.cpp` | `eafe15a5e3d87dd68ae33acf6a7cbd9415a0ac5e` |
| `llama-cpp-cpu` | `ggml-org/llama.cpp` | `eafe15a5e3d87dd68ae33acf6a7cbd9415a0ac5e` |
| `llama-cpp-generel-schwerz-16gb` | `GenerelSchwerz/llama.cpp` | `e69a1d0be5f8ae0080593865b38b175223059199` |
| `llama-cpp-generel-schwerz-32gb` | `GenerelSchwerz/llama.cpp` | `0ed73d1c9e26587cc41b73f77e9e058a0da55368` |
| `llama-cpp-csantiago78` | `csantiago78/llama.cpp` | `bccbacdb8945680f1cfc7e6bffd1e59014705750` |

Docker therefore caches three neutral source clones and makes seven isolated, pinned source copies during builds. The branch is descriptive provenance; the build fetches and verifies the immutable commit directly, so a deleted branch cannot break it. Changing a pin belongs in the service's `build.args`, not in a checkout on the host.

## Runtime configuration

Every host-side llama.cpp setting is below `/mnt/work/llama`:

```text
/mnt/work/llama/
  llama-cpp/models-preset.ini  (shared by gpu-0, gpu-1, and all-gpus)
  llama-cpp-cpu/models-preset.ini
  llama-cpp-generel-schwerz-16gb/{config.ini,models-preset.ini}
  llama-cpp-generel-schwerz-32gb/{config.ini,models-preset.ini}
  llama-cpp-csantiago78/{config.ini,models-preset.ini}
```

Tracked templates live in matching `llama-cpp/config/<service>/` directories. Compose mounts the `/mnt/work/llama` copies read-only, so runtime changes never alter the checkout.

The three upstream GPU services share the ordinary full-catalogue workflow: it validates every explicit template path, discovers the model library, and adds missing models with the `[*]` defaults.

```sh
./llama-cpp/generate-models-preset.py \
  --preset llama-cpp/config/llama-cpp/models-preset.ini \
  --force /mnt/work/llama/llama-cpp
```

The other four services are deliberately preset-only. This validates the paths named in their own template but neither scans the model library nor adds models to their catalogue:

```sh
./llama-cpp/generate-models-preset.py --preset-only --force \
  --preset llama-cpp/config/llama-cpp-cpu/models-preset.ini \
  /mnt/work/llama/llama-cpp-cpu

./llama-cpp/generate-models-preset.py --preset-only --force \
  --preset llama-cpp/config/llama-cpp-generel-schwerz-16gb/models-preset.ini \
  /mnt/work/llama/llama-cpp-generel-schwerz-16gb

./llama-cpp/generate-models-preset.py --preset-only --force \
  --preset llama-cpp/config/llama-cpp-generel-schwerz-32gb/models-preset.ini \
  /mnt/work/llama/llama-cpp-generel-schwerz-32gb

./llama-cpp/generate-models-preset.py --preset-only --force \
  --preset llama-cpp/config/llama-cpp-csantiago78/models-preset.ini \
  /mnt/work/llama/llama-cpp-csantiago78
```

Copy each fork's `config.ini` template to the equivalent `/mnt/work/llama` directory before starting it. The repository templates are mounted only through these generated/copied host paths.

## GPU allocation and start

`llama-cpp-gpu-0` can use only physical GPU 0 and `llama-cpp-gpu-1` only
physical GPU 1. They are the only pair of GPU-enabled llama services that can
run together. `llama-cpp-all-gpus` locks both cards, as do the two-GPU fork
services. The 16GB fork locks the GPU named by its existing
`GS_LLAMA_CPP_16GB_CUDA_VISIBLE_DEVICES` setting.

Start these services with ordinary Compose commands:

```sh
docker compose -f compose.ai.yml up -d llama-cpp-gpu-0 llama-cpp-gpu-1
docker compose -f compose.ai.yml up -d llama-cpp-all-gpus
```

The image takes non-blocking lifetime locks in a shared Docker volume before
starting `llama-server`. If any assigned GPU is already locked, the container
exits with status 75 and a `GPU allocation conflict` error. These GPU-profile
services use `restart: "no"`, so the conflict remains visible rather than
entering a restart loop. With detached Compose the creation command has
already succeeded, so inspect the error with `docker compose ps` and
`docker compose logs SERVICE`; run without `-d` if the shell exit status is
needed. The locks apply only to llama services; they intentionally do not
reserve an idle GPU against ComfyUI or another non-llama workload.

`LLAMA_CPP_GPU_0_DEVICE_ID` and `LLAMA_CPP_GPU_1_DEVICE_ID` default to `0` and
`1`. Set them to stable NVIDIA GPU UUIDs if host GPU numbering may change.
Keep `LLAMA_CPP_ALL_GPU_LOCK_IDS` aligned with every GPU accessible to the
all-GPU service.

`llama-cpp-all-gpus` retains the `llama-cpp` network alias, so existing
DeepSeek and Pi configuration using `http://llama-cpp:8080/v1` remains valid.

## Ports

```sh
docker compose -f compose.ai.yml logs -f llama-cpp-all-gpus
```

`llama-cpp-all-gpus` remains at `192.168.50.136:11436`; the single-GPU
services use 11441 (GPU 0) and 11442 (GPU 1). The CPU service uses 11437 and
the fork services use 11438–11440. Inside Compose, DeepSeek and Pi use
`http://llama-cpp:8080/v1` when the all-GPU service is active.

The shared GGUF library defaults to `/mnt/data/models/gguf` and is mounted read-only at `/models`. Download and manage models on the host.

See [GenerelSchwerz build notes](generel-schwerz-README.md) for the two MoE profiles' runtime constraints.
