# Ollama

This service uses the official `ollama/ollama` image and exposes the API on the
LAN address `192.168.50.136:11434`.

Each service has a named volume for its Ollama home directory. The model
directory is then mounted from the host at the official image's default model
storage path:

```sh
ollama-home:/root/.ollama
/mnt/data/models/ollama:/root/.ollama/models
```

The GPU service uses `ollama-home`, while the CPU service uses the separate
`ollama-cpu-home` volume. This persists keys and other non-model state without
sharing mutable configuration between the services. Both services share the
existing host model store; the CPU service mounts it read-only.

The official image normally runs as root, so make sure the host directory is
readable and writable by the container:

```sh
sudo chown -R root:root /mnt/data/models/ollama
```

If you later choose to run the container as a non-root uid/gid, change the
directory ownership to match that uid/gid and add a `user:` entry to the compose
service.

The default context length remains configurable with `OLLAMA_CONTEXT_LENGTH` in
`.env`.

Run with:

```sh
docker compose up -d ollama
```

## Command-Line Access Through Compose

Pull, inspect, or run models through the Compose service:

```sh
docker compose exec ollama ollama list
docker compose exec ollama ollama pull gpt-oss-128k:latest
docker compose exec ollama ollama show gpt-oss-128k:latest
docker compose exec ollama ollama run --verbose gpt-oss-128k:latest "Explain matrix multiplication"
```

The CPU-only service uses the same model store read-only and is exposed on a
separate host port:

```sh
docker compose up -d ollama-cpu
docker compose exec ollama-cpu ollama list
```

## Local HTTP Requests

The compose file currently binds the GPU service to `192.168.50.136:11434` and
the CPU service to `192.168.50.136:11435`. If you want these examples to use
literal `localhost`, either bind the service to `127.0.0.1` in
`docker-compose.yml` or forward the port with SSH.

Set the URL once:

```sh
OLLAMA_URL=http://192.168.50.136:11434
# OLLAMA_URL=http://localhost:11434
```

List locally available models:

```sh
curl "$OLLAMA_URL/api/tags"
```

Generate a non-streaming response with the native Ollama API:

```sh
curl "$OLLAMA_URL/api/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-oss-128k:latest",
    "prompt": "Write a one-line haiku about Amiga windows.",
    "stream": false
  }'
```

Use the native chat API:

```sh
curl "$OLLAMA_URL/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-oss-128k:latest",
    "messages": [
      {"role": "system", "content": "Answer concisely."},
      {"role": "user", "content": "What is Workbench?"}
    ],
    "stream": false
  }'
```

Use the OpenAI-compatible API:

```sh
curl "$OLLAMA_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-oss-128k:latest",
    "messages": [
      {"role": "system", "content": "Answer concisely."},
      {"role": "user", "content": "What is Workbench?"}
    ]
  }'
```

Query the OpenAI-compatible model list:

```sh
curl "$OLLAMA_URL/v1/models"
```

Check whether the last request was handled on the GPU/CPU/split:

```sh
docker compose exec ollama ollama ps
```