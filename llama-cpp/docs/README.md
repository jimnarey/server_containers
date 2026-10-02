# llama.cpp service

`compose.ai.yml` declares one static upstream `llama-cpp` service. It exposes both GPUs, listens on `192.168.50.136:11450`, and mounts the GGUF library read-only at `/models`.

Start or recreate it with:

```sh
docker compose up -d --build llama-cpp
```

The model catalogue is [`config/llama-cpp-unified/models-preset.ini`](../config/llama-cpp-unified/models-preset.ini). Each model ID has a resource suffix (`--cuda0`, `--cuda1`, `--cuda0-cuda1`, or `--cpu`) that selects the placement declared by its preset section. The router autoloads one model at a time, so a model switch unloads the prior model before loading the requested one.

The service has no generated Compose overlays, profile environment files, launch wrapper, or fork-specific configuration. Update the static Compose declaration and unified preset together when changing its runtime behavior.

`config/llama-cpp-unified/vscode-chat-models.json` contains the matching VS Code provider entries. Chat-template overrides live in `config/chat-templates/`; see [chat-template-audit.md](chat-template-audit.md) for their provenance.
