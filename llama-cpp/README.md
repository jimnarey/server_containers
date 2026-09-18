# llama.cpp service profiles

`compose.ai.yml` provides the shared AI stack and the `llama-gpu-locks`
volume. It deliberately does not declare long-lived llama.cpp services.
`render-compose.py` reads exactly one profile env file and emits one complete,
deterministic Compose service overlay. A service therefore exists only for the
build/profile selected for that invocation.

## Launching a profile

```sh
docker compose -f compose.ai.yml \
  -f "$(./llama-cpp/render-compose.py llama-cpp/config/llama-cpp-16gb/gpu-1.env)" \
  up -d --build llama-cpp-gpu-1
```

By default the renderer writes the YAML to a stable `/tmp/llama-compose-<sha>`
file and prints that path, which is what makes it usable directly after
Compose's `-f`. Diagnostics go to standard error. The renderer has no clock,
random, network, or host-state input, so the same profile and overrides always
produce byte-identical YAML. Inspect YAML before a launch with:

```sh
./llama-cpp/render-compose.py --stdout llama-cpp/config/llama-cpp-16gb/gpu-1.env
```

Set `LLAMA_GPU_IDS` to replace a profile's GPU selection without modifying its
file. It accepts a comma-separated Docker/NVIDIA device-ID list; for example,
this starts the GPU-1 profile on GPU 0 instead:

```sh
LLAMA_GPU_IDS=0 docker compose -f compose.ai.yml \
  -f "$(./llama-cpp/render-compose.py llama-cpp/config/llama-cpp-16gb/gpu-1.env)" \
  up -d --build llama-cpp-gpu-1
```

For less common overrides, set `LLAMA_RENDER_<KEY>` for any key in the profile
(for example `LLAMA_RENDER_PORT=11444`). These explicit names avoid accidental
interpolation from the repository-wide `.env` file. `LLAMA_GPU_IDS` takes
precedence over `LLAMA_RENDER_GPU_IDS`. A CPU profile must keep `GPU_IDS` empty.

The rendered GPU service uses `gpus.device_ids` to expose only the selected
physical devices and mounts the shared lock volume. The entrypoint takes a
non-blocking lifetime lock for each selected physical ID. A collision exits
with status 75 and remains visible because GPU profiles use `restart: "no"`.

## Profiles

| Profile env file | Service | Build |
| --- | --- | --- |
| `config/llama-cpp-16gb/gpu-0.env` | `llama-cpp-gpu-0` | upstream CUDA, GPU 0 |
| `config/llama-cpp-16gb/gpu-1.env` | `llama-cpp-gpu-1` | upstream CUDA, GPU 1 |
| `config/llama-cpp-32gb/all-gpus.env` | `llama-cpp-all-gpus` | upstream CUDA, GPUs 0 and 1 |
| `config/llama-cpp-cpu/cpu.env` | `llama-cpp-cpu` | upstream CPU |
| `config/llama-cpp-generel-schwerz-16gb/gpu-0.env` | `llama-cpp-generel-schwerz-16gb-gpu-0` | Schwerz `e69a1d0` GPU 0 |
| `config/llama-cpp-generel-schwerz-16gb/gpu-1.env` | `llama-cpp-generel-schwerz-16gb` | Schwerz `e69a1d0` GPU 1 |
| `config/llama-cpp-generel-schwerz-32gb/all-gpus.env` | `llama-cpp-generel-schwerz-32gb` | Schwerz `0ed73d1`, GPUs 0 and 1 |
| `config/llama-cpp-csantiago78/all-gpus.env` | `llama-cpp-csantiago78` | csantiago78 `bccbacd`, GPUs 0 and 1 |

Every profile explicitly supplies its service name, source-service family,
port, bind address, GPU IDs, reproducible build arguments, image tag, and
runtime model/config mounts. The source service family selects the upstream or
fork command/mount layout; the Dockerfile still verifies the pinned immutable
commit directly. The CPU profile uses the same upstream family and renderer
with `LLAMA_CUDA=OFF` and its original `unless-stopped` restart policy, rather
than a separate handwritten Compose service.

The tracked runtime templates remain below `config/`. Copy fork `config.ini`
files to the matching `/mnt/work/llama/...` directory before launch, and
generate the model presets as before:

```sh
./llama-cpp/generate-models-preset.py --preset-only --force \
  --preset llama-cpp/config/llama-cpp-16gb/models-preset.ini \
  /mnt/work/llama/llama-cpp-16gb
```

`llama-cpp-all-gpus` retains the `llama-cpp` network alias, preserving the
existing DeepSeek and Pi endpoint `http://llama-cpp:8080/v1` when that profile
is launched. The profile files use host ports 11436 through 11443; see the
comment at the top of `compose.ai.yml`.

The GGUF library defaults to `/mnt/data/models/gguf` and is mounted read-only
at `/models`. See [GenerelSchwerz build notes](generel-schwerz-README.md) for
the fork-specific runtime constraints.
