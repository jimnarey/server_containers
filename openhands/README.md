# OpenHands with Ollama

This service runs OpenHands Agent Canvas as UID/GID `1000:1000` and can use the
GPU-backed Ollama service from this Compose project. Both containers are on the
same Compose network, so OpenHands reaches Ollama by service name; it must not
use `localhost` for this connection.

## Initial configuration

Set the two OpenHands application secrets in the repository's `.env` file:

```dotenv
OPENHANDS_API_KEY=replace-with-a-long-random-value
OPENHANDS_SECRET_KEY=replace-with-a-different-long-random-value
```

Generate suitable values with:

```sh
openssl rand -hex 32
openssl rand -hex 32
```

These protect the OpenHands application. They are separate from the placeholder
LLM API key entered for Ollama below.

Start Ollama and OpenHands:

```sh
docker compose up -d ollama openhands
```

Open `http://192.168.50.136:9030`.

## Configure the Ollama model

In OpenHands, open **Settings**, select the **LLM** tab, choose the advanced
settings, and enable the **Advanced** switch. Configure:

```text
Custom Model: openai/qwen3-coder:30b
Base URL:     http://ollama:11434/v1
API Key:      local-llm
```

The `openai/` model prefix tells OpenHands/LiteLLM to use Ollama's
OpenAI-compatible API. Ollama does not validate the API key, but OpenHands
requires a non-empty value.

`qwen3-coder:30b` is installed in this repository's Ollama model store and is a
model recommended by OpenHands for local coding tasks. Other installed models
can be selected using the same prefix, for example:

```text
openai/gpt-oss-128k:latest
```

Save the settings and start a new conversation. LLM setting changes apply to
new conversations; restart an older conversation if it should use the new
model.

## Check Ollama and connectivity

List models available to the GPU service:

```sh
docker compose exec ollama ollama list
```

Check the exact network path used by OpenHands:

```sh
docker compose exec openhands \
  curl -fsS --connect-timeout 5 --max-time 15 \
  http://ollama:11434/api/version
```

If this request succeeds but OpenHands cannot call the model, check that the
custom model includes the `openai/` prefix and that the base URL ends in `/v1`.

Do not use these addresses from the OpenHands container:

```text
http://localhost:11434
http://192.168.50.136:11434
```

`localhost` refers to OpenHands itself, while the host-published address is an
unnecessary round trip. The Compose service address is
`http://ollama:11434/v1`.

## Context length and GPU residency

OpenHands requires a large context window for its system prompt and agent
history. Its documentation recommends at least 22,000 tokens for Ollama. This
repository's GPU service defaults to:

```text
OLLAMA_CONTEXT_LENGTH=65536
OLLAMA_KEEP_ALIVE=-1
```

The first setting provides sufficient context. The second asks Ollama to keep
loaded models resident indefinitely, subject to GPU capacity and Ollama's model
scheduling behavior.

After changing `OLLAMA_CONTEXT_LENGTH` or other Ollama environment settings,
recreate that service:

```sh
docker compose up -d --force-recreate ollama
```

## CPU-only alternative

The CPU service shares the same model store read-only and can be selected with:

```text
Base URL: http://ollama-cpu:11434/v1
```

Start it with `docker compose up -d ollama-cpu`. It is considerably slower and
defaults to a 32,768-token context, so the GPU service is preferable for
OpenHands.

## Projects and persistent state

Host projects under `/mnt/data/projects` are mounted at `/projects` in the
OpenHands container. OpenHands state and LLM settings persist under
`/mnt/work/openhands`, mounted at `/home/openhands/.openhands`.

View operational logs with:

```sh
docker compose logs --follow --timestamps openhands ollama
```
