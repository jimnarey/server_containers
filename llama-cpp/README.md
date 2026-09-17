# llama.cpp

These services run the official `llama-server` image in router mode. They do not select a model at container startup. Instead, they advertise only the explicit entries in their mounted `models-preset.ini` files and load the model named in each request.

Only one model may be loaded at once. Switching models therefore unloads the least-recently-used model before loading the requested one, preventing multiple large models from competing for GPU or system memory.

`llama-cpp` uses CUDA 13 and the available GPUs. `llama-cpp-cpu` uses the CPU-only image, explicitly offloads zero layers, and is independent of the GPU service. It is exposed at `192.168.50.136:11437` by default (the GPU service remains on port 11436).

## Configuration

The default model directory is the shared GGUF library:

```text
/mnt/data/models/gguf
```

Override it in `.env` when serving a different directory:

```dotenv
LLAMA_CPP_MODELS=/absolute/path/to/gguf/models
LLAMA_CPP_CONFIG=/mnt/work/llama-cpp/models-preset.ini
LLAMA_CPP_BIND_ADDRESS=192.168.50.136
LLAMA_CPP_PORT=11436
LLAMA_CPP_PARALLEL=1
LLAMA_CPP_FIT_TARGET=1024

LLAMA_CPP_CPU_MODELS=/absolute/path/to/gguf/models
LLAMA_CPP_CPU_CONFIG=/mnt/work/llama-cpp-cpu/models-preset.ini
LLAMA_CPP_CPU_BIND_ADDRESS=192.168.50.136
LLAMA_CPP_CPU_PORT=11437
LLAMA_CPP_CPU_PARALLEL=1
LLAMA_CPP_CPU_FIT_TARGET=1024
```

`llama-cpp/models-preset-gpu.ini` and `llama-cpp/models-preset-cpu.ini` are sparse override sources, not complete catalogues -- one per service, tracked independently side by side (same pattern as `generel-schwerz-llama-cpp/config`'s `models-preset-16gb.ini`/`models-preset-32gb.ini` pair). Each contains only models with an intentional setting different from its own `[*]`; each such section retains its `model = /models/...` path so the generator can preserve its friendly ID. GPU-only directives (`split-mode`, `main-gpu`, `n-gpu-layers=auto` partial offload) belong only in the GPU source. Generate each service's complete runtime preset before first start, and repeat after downloading models or changing overrides:

```sh
./llama-cpp/generate-models-preset.py \
  --preset llama-cpp/models-preset-gpu.ini \
  --force /mnt/work/llama-cpp

./llama-cpp/generate-models-preset.py \
  --preset llama-cpp/models-preset-cpu.ini \
  --force /mnt/work/llama-cpp-cpu
```

The GPU service mounts only `/mnt/work/llama-cpp/models-preset.ini`; the CPU service mounts only `/mnt/work/llama-cpp-cpu/models-preset.ini`. Editing either deployed file therefore cannot modify the checkout or affect the other service. Set `ctx-size` per model in the sparse source; the context is shared by the configured number of server slots, so `*_PARALLEL=1` gives the sole slot the full configured context. KV-cache allocation occurs when a model is loaded and materially increases memory use.

Both services mount the whole shared library at `/models`, but deliberately omit `--models-dir`. This prevents an automatically discovered directory name from becoming a second, unconfigured model ID. The generated runtime files contain one explicit entry for every discovered model. Add a source section only when a new model requires a non-default setting, then regenerate both runtime files.

The mounted directory is read-only. Download and manage GGUF files on the host rather than from this container.

## Generate a complete preset from sparse overrides

[`generate-models-preset.py`](generate-models-preset.py) is for maintaining a runtime preset whose input file contains only a `[*]` default section and the models needing exceptions. `MODEL_ROOT` near the top of the script defaults to `/mnt/data/models/gguf`; `LLAMA_CPP_MODEL_ROOT` can override it for one run.

Before starting discovery, the script validates every explicit `/models/...` path in an override block, including speculative-decoding sidecars and all siblings of a sharded GGUF. It stops with a grouped error naming the preset and missing file(s), without modifying a target file. It then starts a temporary, loopback-only `llama-cpp` router with `--models-dir /models`, reads its generated IDs and resolved paths from `/v1/models`, then removes that router. It does not restart or modify the normal service. It preserves the override file verbatim and writes `models-preset.ini` to the positional target directory, adding a basic entry for every discovered model that is not already named or referenced by path.

```sh
./llama-cpp/generate-models-preset.py \
  --preset /path/to/models-preset-overrides.ini \
  /mnt/work/llama-cpp
```

The command refuses to overwrite an existing runtime preset. Review the generated file and pass `--force` only when replacing it deliberately.

## Start and inspect

```sh
docker compose up -d llama-cpp llama-cpp-cpu
docker compose logs -f llama-cpp
docker compose logs -f llama-cpp-cpu
```

List the models and use the returned `id` exactly as shown:

```sh
curl http://192.168.50.136:11436/v1/models
curl http://192.168.50.136:11437/v1/models
```

Send a request that selects a model dynamically:

```sh
curl http://192.168.50.136:11436/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "MODEL_ID_FROM_V1_MODELS",
    "messages": [
      {"role": "user", "content": "Reply with OK"}
    ]
  }'
```

The first request after a model switch includes its loading delay. Subsequent requests use the resident model. Do not keep a large Ollama model resident while loading a large GPU llama.cpp model, because both services share the same GPUs.

DeepSeek Harness and Pi should use this in-container API URL:

```text
http://llama-cpp:8080/v1
```

The CPU equivalent is:

```text
http://llama-cpp-cpu:8080/v1
```
