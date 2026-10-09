# DeepSeek Harness

This service runs the official DeepSeek Harness (`dsh`) developer preview. It provides the browser workbench and the one-shot headless command-line profile, runs as `runuser` (UID/GID 1000 by default), and has passwordless `sudo` inside the container.

Harness profiles, settings, credentials, sessions, and installed plugins are persisted in `/mnt/work/deepseek` on the host by default. The shared agent workspace defaults to `/mnt/work/projects` on the host and is mounted at `/workspace`.

DeepSeek Harness is a developer preview and may make compatibility-breaking changes. The image therefore pins its npm package version rather than installing `latest` on every build. The repository also bind-mounts a version-matched copy of the shipped Standard agent composition to apply local compaction policies; review that copy whenever `DEEPSEEK_VERSION` changes.

The harness core includes Node, `uv`, build tools, `fd`, `jq`, `git`,
`openssh-client`, `ripgrep`, `tmux`, `zstd`, and passwordless `sudo`. Operating
system requirements for a target project live in [`projects`](../projects/):
the default aggregate Compose stack selects the Amiga layer, while Xbox 360 is
an explicit alternative overlay. `uv` uses persistent cache and managed-Python
directories under `/home/runuser`, so Python downloads and package caches
survive container recreation.

Passwordless `sudo` is available as a fallback for small missing dependency
installs and diagnostics when entering the container with `docker compose exec`.
DSH's normal `workspace-write` bash sandbox may still prevent in-agent `sudo`
with a `no_new_privileges` error, so dependencies that become part of the normal
workflow should be added to this image instead.

## Configuration

Optional settings in `.env` are:

```dotenv
DEEPSEEK_VERSION=0.2.0-rc.2
DEEPSEEK_HOME=/mnt/work/deepseek
DEEPSEEK_WORKSPACE=/mnt/work/projects
DEEPSEEK_GATEWAY_HOSTNAME=deepseek.ai.home.arpa
# Non-secret activation value for the local llama.cpp provider.
LLAMA_CPP_API_KEY=local
```

Two integration values are still literal Compose configuration rather than `.env` settings:

- `/container-ssh` is mounted read-only at `/home/runuser/.ssh` for the
  restricted GitHub automation identity.
- `SSH_CONNECTION` is set to a synthetic non-empty value so the Harness's
  automatic picker selects its browser-based remote directory picker. It does
  not describe a real SSH connection or grant SSH access.

The web interface has control over the mounted workspace and must not be
published directly on the LAN or internet. Its relay is attached only to the
private `https-gateway` Docker network.

## Start the service

```bash
docker compose build deepseek
docker compose up -d https-gateway deepseek
docker compose logs -f https-gateway deepseek
```

Before starting the services, configure local DNS for
`DEEPSEEK_GATEWAY_HOSTNAME` and trust the Caddy local CA as described in
[`https-gateway/README.md`](../https-gateway/README.md). DeepSeek's own
in-container Caddy obtains its username and bcrypt password hash from
`CADDY_USER` and `CADDY_HASH`, the same variables used by the existing
browser/VNC containers.

## Access the web interface through HTTPS

Open the configured hostname, for example:

```text
https://deepseek.ai.home.arpa/
```

The browser first reaches the shared gateway over HTTPS, which routes to
DeepSeek's own Caddy instance. That in-container Caddy prompts for the Basic
Auth credentials before it reaches DeepSeek. The service is not published on a
host port and is reachable only from the shared gateway on the private Compose
network.

Internally, `dsh` retains its loopback listener. DeepSeek's in-container Caddy
proxies directly to that loopback listener after authentication, so its
successful Basic Auth check is part of the security boundary.

DSH also uses a one-time, per-process launch token to establish its own
browser-session cookie. After a DeepSeek restart, obtain the token from the
startup log without sharing it, then replace the loopback base URL with the
HTTPS gateway hostname:

```bash
docker compose logs --tail=50 deepseek | rg 'dsh web:'
# Open https://deepseek.ai.home.arpa/?token=... using the printed token.
```

After that one request, DSH redirects to the clean HTTPS URL and uses its
HTTP-only cookie for subsequent requests (normally valid for 30 days). Repeat
the handoff only after clearing browser cookies, changing the hostname, or
when the DSH browser-session credential is reset.

The container passes `DEEPSEEK_GATEWAY_HOSTNAME` to DSH as its trusted browser
authority. Keep it identical to DeepSeek's `caddy` route label in
`compose.ai.yml`. This permits same-origin browser API requests (including
workspace and session access) without relaxing DSH's trust fence for other
hostnames.

The browser is only a client of the long-running Harness host. Closing the tab
or disconnecting the workstation does not normally stop an active turn;
reconnect and reopen the persisted session later. A turn may still wait
indefinitely for a tool approval or user answer, and an interrupted
container/model process is not guaranteed to resume the exact in-flight turn.

## Local web search and fetch

`web_search` and `web_fetch` are temporarily disabled in both DeepSeek
profiles. The local provider definitions remain in the profile overlays so they
can be re-enabled deliberately by removing the `tool-web` `disabled: true`
entries from both patch files.

When enabled, the `web_search` tool uses the Compose-local SearXNG API at
`http://searxng:8080/`; it does not use DeepSeek's cloud search or require a
DeepSeek API key. Both the browser (`web`) and `headless` profiles explicitly
select this provider, so adding a future provider cannot silently change where
search requests go.

When enabled, `web_fetch` uses the local `dsh-web-fetch-guarded` provider. It
only forwards a URL to the Compose-local `guarded-fetch` gateway, which permits
public HTTPS text retrieval and applies destination/DNS validation, redirect,
timeout, and response-size limits. The provider cannot forward browser cookies,
stored credentials, HTTP methods, headers, or a request body.

The optional integrations use Compose service names internally; neither needs
a host-published port. If they are re-enabled, restore the commented
health-based `depends_on` entries in `compose.ai.yml` so DeepSeek waits for
them before it starts.

This prevents DeepSeek's `web_fetch` tool from reaching Compose-local services
or private-network addresses. It is not a complete egress boundary: an agent
with shell access can still use its normal network tools, so keep the UI within
its authenticated HTTPS-gateway boundary and treat fetched page text as
untrusted.

The shipped capability modes retain their own `tool-web` configuration; set
`fetch: true` and `fetchTimeoutMs: 30000` in the relevant mode composition to
enable fetch there as well.

## Configure the local llama.cpp model

In Settings -> Models, add a custom provider with:

```text
Provider ID: llama-cpp
Base URL: http://llama-cpp:8080/v1
API protocol: OpenAI Completions
Model: Qwen3.8-27B-UD-Q6_K_M--cuda0-cuda1
```

Use a non-secret placeholder if the form requires an API key; the current llama.cpp service does not validate one. `localhost` is wrong here because it would refer to the DeepSeek container, not the llama.cpp service.

Model discovery can query llama.cpp's `/v1/models` endpoint. Selecting the model sets it as the default for new sessions; existing sessions retain their saved model selection.

The first DSH 0.2 boot migrates the legacy model catalogue into the persistent
web profile and retains its source as `settings.yaml.imported` in
`DEEPSEEK_HOME`. Use the Models page to manage the migrated web-profile
catalogue. The headless profile has a separate settings scope; pass an
explicit model when using it until its own configuration is set.

### Persistent local model configuration

[`config/settings.yaml`](./config/settings.yaml) is a one-time seed for a
brand-new DSH home. It is not bind-mounted: DSH 0.2 migrates it into the
writable web-profile patch, where providers and models can survive upgrades
without a repository overlay masking them. The persistent `DEEPSEEK_HOME`
therefore contains credentials, sessions, package state, and web model
configuration; back it up as one unit.

This installation keeps every session on the built-in `standard` preset, with
model-specific policy (including compaction) expressed as `modelPolicies` in
[`agent-preset-overrides/standard/agent.cordis.yml`](./agent-preset-overrides/standard/agent.cordis.yml)
rather than as separate named presets. An earlier setup tried per-model
repository-owned presets (with a `.agent-presets` sync/prune mechanism and a
`migrate-agent-preset.py` tool to reattach old sessions when one was retired);
that approach was rejected in favor of the single-preset design above, and the
now-unused machinery has been removed. Since `standard` is a built-in preset
this synchroniser cannot delete, there is no retirement/migration scenario to
plan for.

The **mode** menu selects an agent capability composition (Standard, Code,
Minimal, and Cordis). It is not a model selector. This installation deliberately
uses `standard` by default. Its repository-owned, version-matched composition
adds exact model policies to `compaction-basic` without adding any model-named
modes:

- `llama-cpp` / `Qwen3.8-27B-UD-Q6_K_M--cuda0-cuda1`: compact at 75% of its 163,840-token
  route, retain 16,384 recent tokens, and allow a 12,288-token checkpoint.
- `llama-cpp` / Flash Next resource variants: compact at
  80% of its 98,304-token route, retain 16,384 tokens, and use the same
  checkpoint cap.

All other Standard routes retain Harness's normal context-relative defaults.
The local Standard composition is bind-mounted into the pinned Harness package,
so revisit it as part of every `DEEPSEEK_VERSION` upgrade.

The **Select Model** control chooses a provider/model independently. New
sessions default to `llama-cpp` / `Qwen3.8-Flash-Next-UD-Q3_K_XL--cuda1`
through the migrated `agent-default-model` profile setting. To use the same model on the
other physical GPU, keep Standard mode selected and choose
`llama-cpp` with `Qwen3.8-Flash-Next-UD-Q3_K_XL--cuda0`. A session's existing model selection remains
durable when its capability mode changes.

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
