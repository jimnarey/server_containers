# Model broker

The model broker is built from its own repository (`MODEL_BROKER_CONTEXT`, default
`/mnt/work/projects/model-broker`); see its README and design for how it works. This
directory holds what is specific to this deployment's clients.

## Clients

The broker serves every model of `llama-cpp` and `strata` under its full suffixed ID, at
`http://192.168.50.136:11460/v1` (`MODEL_BROKER_BIND_ADDRESS` and `MODEL_BROKER_PORT`), or
`http://model-broker:8000/v1` from another container on the Compose network. A request for a
model that is not loaded waits while the broker unloads whatever competes for its GPU or RAM
and loads it, which can take a minute for a large llama.cpp model and most of an hour for the
first Strata start. If the models it would unload are busy, the request waits up to
`MODEL_BROKER_MAX_WAIT_SECONDS`, then gets `503 resource_busy` with `Retry-After`.

`vscode-chat-models.json` is a ready-made provider entry for VS Code's
`chatLanguageModels.json`, with all 85 models declared (82 llama.cpp and 3 Strata). Each
entry's input limit is its context size less the 8192-token output limit, as in
`../llama-cpp/config/vscode-chat-models.json`. It is generated from the two presets:

```bash
./model-broker/generate-vscode-chat-models.py
```

Rerun it when either preset gains or loses a model or changes a context size. It keeps the
file's `apiKey` placeholder so VS Code's saved value still applies; the broker does not
authenticate yet, so any non-empty value works. DeepSeek's provider for the broker is
generated separately, by `../deepseek/generate-web-profile.sh`.
