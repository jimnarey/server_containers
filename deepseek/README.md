# DeepSeek Harness

This service runs the official DeepSeek Harness (`dsh`) developer preview. It
provides the browser workbench and the one-shot headless command-line profile,
runs as `runuser` (UID/GID 1000 by default), and has passwordless `sudo` inside
the container.

Harness profiles, settings, credentials, sessions, and installed plugins are
persisted in `/mnt/work/deepseek` on the host by default. The shared agent
workspace defaults to `/mnt/work/projects` on the host and is mounted at
`/workspace`.

DeepSeek Harness is a developer preview and may make compatibility-breaking
changes. The image therefore pins its npm package version rather than installing
`latest` on every build.

## Configuration

Optional settings in `.env` are:

```dotenv
DEEPSEEK_VERSION=0.1.1-rc.2
DEEPSEEK_HOME=/mnt/work/deepseek
DEEPSEEK_WORKSPACE=/mnt/work/projects
DEEPSEEK_BIND_ADDRESS=127.0.0.1
DEEPSEEK_PORT=9035
```

Keep `DEEPSEEK_BIND_ADDRESS` set to `127.0.0.1` while using an SSH tunnel. The
web interface has control over the mounted workspace and must not be exposed
directly to the LAN or internet.

## Start the service

```bash
docker compose build deepseek
docker compose up -d deepseek
docker compose logs -f deepseek
```

The startup log prints the listening URL and any startup errors. In the pinned
release, a loopback launch does not add a token to that URL; the host-loopback
binding is therefore the primary access boundary.

## Access the web interface through SSH

From the workstation, keep this command running:

```bash
ssh -N -L 9035:127.0.0.1:9035 ai@ai-ubuntu
```

Open this URL on the workstation:

```text
http://localhost:9035/
```

If a future pinned release prints a URL containing `?token=...`, use that full
URL for the first browser connection.

The Compose port is published on host loopback only. Internally, `dsh` retains
its own loopback listener and a TCP relay makes that listener available to the
published port. This leaves a network target that a future Caddy service can
proxy deliberately. Caddy must add strong authentication before exposing it,
because traffic through the relay reaches `dsh` from container loopback.

## Configure the local llama.cpp model

In Settings -> Models, add a custom provider with:

```text
Provider ID: llama-cpp
Base URL: http://llama-cpp:8080/v1
API protocol: OpenAI Completions
Model: Qwen3.8-27B-UD-Q6_K_M
```

Use a non-secret placeholder if the form requires an API key; the current
llama.cpp service does not validate one. `localhost` is wrong here because it
would refer to the DeepSeek container, not the llama.cpp service.

Model discovery can query llama.cpp's `/v1/models` endpoint. Selecting the model
sets it as the default for new sessions; existing sessions retain their saved
model selection.

At present, the provider form can save the catalogue without saving a default
for the headless profile. Check `/home/runuser/.dsh/settings.yaml` and add this
shared selection if `agent-default-model` is absent:

```yaml
agent-default-model:
  provider: llama-cpp
  model: Qwen3.8-27B-UD-Q6_K_M
```

Without that section, `dsh --profile headless` falls back to the shipped
`deepseek-official` / `deepseek-v4-flash` deployment default and asks for a
`DEEPSEEK_API_KEY`, even though the custom llama.cpp catalogue is valid.

## Command-line use over SSH

SSH to the server, change to this Compose repository, and open a container shell:

```bash
docker compose exec --user runuser -w /workspace deepseek bash
```

The official command-line surface is a one-shot headless agent, not an
interactive TUI. Run a task against a specific repository with:

```bash
docker compose exec --user runuser \
  -w /workspace/amiga-ui \
  deepseek \
  dsh --profile headless "Inspect this repository and summarize how to run its tests."
```

The web and headless profiles share `/home/runuser/.dsh`, including provider
configuration and credentials, but create their own profile definitions.

Inspect the installed version and configuration with:

```bash
docker compose exec --user runuser deepseek dsh --version
docker compose exec --user runuser deepseek dsh --profile web --dump-config
```

Because the workspace is a host bind mount and the agent has passwordless
`sudo`, treat both web and CLI sessions as trusted administrative tooling.
