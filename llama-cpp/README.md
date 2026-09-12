# llama.cpp

These services run the official `llama-server` image in router mode. They do not select a model at container startup. Instead, they scan `/models`, advertise the discovered GGUF files through the OpenAI-compatible API, and load the model named in each request.

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

The model preset is runtime state, not repository state. Before first start, create an independent copy for each service:

```sh
install -D -m 0644 llama-cpp/models-preset.ini /mnt/work/llama-cpp/models-preset.ini
install -D -m 0644 llama-cpp/models-preset.ini /mnt/work/llama-cpp-cpu/models-preset.ini
```

The GPU service mounts only `/mnt/work/llama-cpp/models-preset.ini`; the CPU service mounts only `/mnt/work/llama-cpp-cpu/models-preset.ini`. Editing either therefore cannot modify the checkout or affect the other service. Set `ctx-size` per model in the relevant preset; the context is shared by the configured number of server slots, so `*_PARALLEL=1` gives the sole slot the full configured context. KV-cache allocation occurs when a model is loaded and materially increases memory use.

Both services mount the whole shared library at `/models`, so models added to `/mnt/data/models/gguf` are available to both without another Compose edit. `--models-dir` discovers GGUF files at the directory root and treats immediate subdirectories as possible multi-file models. Keep each model's GGUF file (or its shards) at one of those two levels; use a flat, model-specific directory name when downloading from different publishers.

The mounted directory is read-only. Download and manage GGUF files on the host rather than from this container.

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
