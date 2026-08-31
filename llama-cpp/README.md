# llama.cpp

This service runs the official CUDA 13 `llama-server` image in router mode. It does not select a model at container startup. Instead, it scans `/models`, advertises the discovered GGUF files through the OpenAI-compatible API, and loads the model named in each request.

Only one model may be loaded at once. Switching models therefore unloads the least-recently-used model before loading the requested one, preventing multiple large models from competing for the two GPUs.

## Configuration

The default model directory is the current Unsloth Qwen 3.8 repository:

```text
/mnt/data/models/gguf/unsloth/Qwen3.8-27B-GGUF
```

Override it in `.env` when serving a different directory:

```dotenv
LLAMA_CPP_MODELS=/absolute/path/to/gguf/models
LLAMA_CPP_BIND_ADDRESS=192.168.50.136
LLAMA_CPP_PORT=11436
LLAMA_CPP_CONTEXT_LENGTH=131072
LLAMA_CPP_PARALLEL=1
LLAMA_CPP_FIT_TARGET=1024
```

The current 131,072-token context is shared by the configured number of server slots; `LLAMA_CPP_PARALLEL=1` gives the single slot the full context. KV-cache allocation occurs when a model is loaded and materially increases GPU memory use compared with the earlier 65,536-token setting.

`--models-dir` discovers GGUF files at the directory root and treats each immediate subdirectory as a possible multi-file model. It does not reliably scan arbitrary publisher/repository directory depths. Point `LLAMA_CPP_MODELS` at a repository leaf, or later provide a curated flat model directory or a llama.cpp model-preset file when serving multiple repositories.

The mounted directory is read-only. Download and manage GGUF files on the host rather than from this container.

## Start and inspect

```sh
docker compose up -d llama-cpp
docker compose logs -f llama-cpp
```

List the models and use the returned `id` exactly as shown:

```sh
curl http://192.168.50.136:11436/v1/models
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

The first request after a model switch includes its loading delay. Subsequent requests use the resident model. Do not keep a large Ollama model resident while loading a large llama.cpp model, because both services share the same GPUs.

DeepSeek Harness and Pi should use this in-container API URL:

```text
http://llama-cpp:8080/v1
```
