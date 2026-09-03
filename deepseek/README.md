# DeepSeek Harness

This service runs the official DeepSeek Harness (`dsh`) developer preview. It provides the browser workbench and the one-shot headless command-line profile, runs as `runuser` (UID/GID 1000 by default), and has passwordless `sudo` inside the container.

Harness profiles, settings, credentials, sessions, and installed plugins are persisted in `/mnt/work/deepseek` on the host by default. The shared agent workspace defaults to `/mnt/work/projects` on the host and is mounted at `/workspace`.

DeepSeek Harness is a developer preview and may make compatibility-breaking changes. The image therefore pins its npm package version rather than installing `latest` on every build.

The image includes the common tools needed by the local coding-agent workflow:
`uv`, Python 3.12 development headers, build tools, `Xvfb`, `xauth`, `7z`,
`zstd`, `fd`, `jq`, `git`, `openssh-client`, `ripgrep`, and the GLib/Qt/XCB
runtime libraries needed by PySide6 under Xvfb. `uv` uses persistent cache and
managed-Python directories under `/home/runuser`, so Python downloads and package
caches survive container recreation.

Passwordless `sudo` is available as a fallback for small missing dependency
installs and diagnostics when entering the container with `docker compose exec`.
DSH's normal `workspace-write` bash sandbox may still prevent in-agent `sudo`
with a `no_new_privileges` error, so dependencies that become part of the normal
workflow should be added to this image instead.

## Configuration

Optional settings in `.env` are:

```dotenv
DEEPSEEK_VERSION=0.1.1-rc.2
DEEPSEEK_HOME=/mnt/work/deepseek
DEEPSEEK_WORKSPACE=/mnt/work/projects
DEEPSEEK_BIND_ADDRESS=127.0.0.1
DEEPSEEK_PORT=9035
```

Two integration values are still literal Compose configuration rather than `.env` settings:

- `/container-ssh` is mounted read-only at `/home/runuser/.ssh` for the
  restricted GitHub automation identity.
- `SSH_CONNECTION` is set to a synthetic non-empty value so the Harness's
  automatic picker selects its browser-based remote directory picker. It does
  not describe a real SSH connection or grant SSH access.

These should eventually become explicit configurable settings rather than local assumptions embedded in `docker-compose.yml`.

Keep `DEEPSEEK_BIND_ADDRESS` set to `127.0.0.1` while using an SSH tunnel. The web interface has control over the mounted workspace and must not be exposed directly to the LAN or internet.

## Start the service

```bash
docker compose build deepseek
docker compose up -d deepseek
docker compose logs -f deepseek
```

The startup log prints the listening URL and any startup errors. In the pinned release, a loopback launch does not add a token to that URL; the host-loopback binding is therefore the primary access boundary.

## Access the web interface through SSH

From the workstation, keep this command running:

```bash
ssh -N -L 9035:127.0.0.1:9035 ai@ai-ubuntu
```

Open this URL on the workstation:

```text
http://localhost:9035/
```

If a future pinned release prints a URL containing `?token=...`, use that full URL for the first browser connection.

The Compose port is published on host loopback only. Internally, `dsh` retains its own loopback listener and a TCP relay makes that listener available to the published port. This leaves a network target that a future Caddy service can proxy deliberately. Caddy must add strong authentication before exposing it, because traffic through the relay reaches `dsh` from container loopback.

This arrangement exists because the current deployment uses HTTP while Harness reserves privileged configuration operations for loopback clients. The relay cannot distinguish a genuine local Harness client from traffic forwarded to it; host-loopback publication plus the SSH tunnel is therefore part of the security boundary, not merely a convenience. Do not change `DEEPSEEK_BIND_ADDRESS` to a LAN address as a substitute for the planned authenticated HTTPS gateway.

The browser is only a client of the long-running Harness host. Closing the tab, closing the SSH tunnel, or disconnecting the workstation does not normally stop an active turn; reconnect and reopen the persisted session later. A turn may still wait indefinitely for a tool approval or user answer, and an interrupted container/model process is not guaranteed to resume the exact in-flight turn.

## Configure the local llama.cpp model

In Settings -> Models, add a custom provider with:

```text
Provider ID: llama-cpp
Base URL: http://llama-cpp:8080/v1
API protocol: OpenAI Completions
Model: Qwen3.8-27B-UD-Q6_K_M
```

Use a non-secret placeholder if the form requires an API key; the current llama.cpp service does not validate one. `localhost` is wrong here because it would refer to the DeepSeek container, not the llama.cpp service.

Model discovery can query llama.cpp's `/v1/models` endpoint. Selecting the model sets it as the default for new sessions; existing sessions retain their saved model selection.

At present, the provider form can save the catalogue without saving a default for the headless profile. Check `/home/runuser/.dsh/settings.yaml` and add this shared selection if `agent-default-model` is absent:

```yaml
agent-default-model:
  provider: llama-cpp
  model: Qwen3.8-27B-UD-Q6_K_M
```

Without that section, `dsh --profile headless` falls back to the shipped `deepseek-official` / `deepseek-v4-flash` deployment default and asks for a `DEEPSEEK_API_KEY`, even though the custom llama.cpp catalogue is valid.

### Local Qwen coding preset backup

This repository keeps deployment examples for a long-running local coding-agent
setup under [`deepseek/config-examples`](./config-examples/). These files are not
baked into the image yet; after a fresh deployment, copy the preset and settings
into the persisted `DEEPSEEK_HOME` volume before starting a new session:

```bash
install -d /mnt/work/deepseek/.dsh/.agent-presets/local-qwen-coder
cp deepseek/config-examples/presets/local-qwen-coder/agent.cordis.yml \
  /mnt/work/deepseek/.dsh/.agent-presets/local-qwen-coder/agent.cordis.yml
cp deepseek/config-examples/settings/llama-cpp-qwen.yaml \
  /mnt/work/deepseek/.dsh/settings.yaml
```

The saved `local-qwen-coder` preset is intended for local autonomous coding runs
using Qwen through llama.cpp. It enables DSH compaction with a larger 160K-class
context in mind: it starts compaction at 75% context, keeps 16,384 recent tokens
verbatim, and caps the generated compaction summary at 12,288 tokens. This is
intended to avoid the observed loop where retaining too much recent history
caused compaction to finish still close to the next compaction threshold.

Review `llama-cpp-qwen.yaml` before copying it onto an existing deployment,
because it contains provider/model selections as well as context-window metadata.

## Command-line use over SSH

SSH to the server, change to this Compose repository, and open a container shell:

```bash
docker compose exec --user runuser -w /workspace deepseek bash
```

The official command-line surface is a one-shot headless agent, not an interactive TUI. Run a task against a specific repository with:

```bash
docker compose exec --user runuser \
  -w /workspace/amiga-ui \
  deepseek \
  dsh --profile headless "Inspect this repository and summarize how to run its tests."
```

The headless profile intentionally emits no live trajectory. It waits for the fresh agent to become idle, prints the final non-empty assistant message, and exits. For a job that must survive an SSH disconnection, run the Compose command inside `tmux` on the host. Use the web profile when reconnectable trajectory inspection is more important than terminal output.

The web and headless profiles share `/home/runuser/.dsh`, including provider configuration and credentials, but create their own profile definitions.

Inspect the installed version and configuration with:

```bash
docker compose exec --user runuser deepseek dsh --version
docker compose exec --user runuser deepseek dsh --profile web --dump-config
```

Because the workspace is a host bind mount and the agent has passwordless `sudo`, treat both web and CLI sessions as trusted administrative tooling.

## GitHub SSH access

The Compose service mounts `/container-ssh` read-only as `/home/runuser/.ssh`. This installation uses that directory for a restricted GitHub automation account; it must not contain personal or employer credentials. The same key is currently shared with Goose.

Test the mounted identity with:

```bash
docker compose exec --user runuser deepseek ssh -T github.com
```

Configure commit authorship separately in each repository because an SSH key controls push authentication, not `user.name` or `user.email`:

```bash
docker compose exec --user runuser -w /workspace/amiga-ui deepseek \
  git config user.name 'jimnarey-llm'
docker compose exec --user runuser -w /workspace/amiga-ui deepseek \
  git config user.email 'jimnarey+llm@me.com'
```
