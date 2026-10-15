# DeepSeek Harness

This service runs the official DeepSeek Harness (`dsh`) developer preview. It provides the browser workbench and the one-shot headless command-line profile, runs as `runuser` (UID/GID 1000 by default), and has passwordless `sudo` inside the container.

Harness profiles, settings, credentials, sessions, and installed plugins are
persisted outside the image. The Amiga instance keeps the historic defaults of
`/mnt/work/deepseek` and `/mnt/work/projects`; the Xbox 360 instance uses
`/mnt/work/deepseek-xbox360` and `/mnt/work/projects-xbox360`. This keeps
separately named Harness containers independent when they run concurrently.

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
DEEPSEEK_AMIGA_HOME=/mnt/work/deepseek
DEEPSEEK_AMIGA_WORKSPACE=/mnt/work/projects
DEEPSEEK_AMIGA_GATEWAY_HOSTNAME=deepseek-amiga.ai.home.arpa
DEEPSEEK_XBOX360_HOME=/mnt/work/deepseek-xbox360
DEEPSEEK_XBOX360_WORKSPACE=/mnt/work/projects-xbox360
DEEPSEEK_XBOX360_GATEWAY_HOSTNAME=deepseek-xbox360.ai.home.arpa
# Non-secret activation value for the local llama.cpp provider.
LLAMA_CPP_API_KEY=local
# Optional server-side authentication for Strata. Leave empty when Strata is
# unauthenticated; DSH then uses a harmless local placeholder.
STRATA_API_KEY=
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
docker compose build deepseek-amiga
docker compose up -d https-gateway deepseek-amiga
docker compose logs -f https-gateway deepseek-amiga
```

Before starting the services, configure local DNS for each project-specific
gateway hostname and trust the Caddy local CA as described in
[`https-gateway/README.md`](../https-gateway/README.md). DeepSeek's own
in-container Caddy obtains its username and bcrypt password hash from
`CADDY_USER` and `CADDY_HASH`, the same variables used by the existing
browser/VNC containers.

## Access the web interface through HTTPS

Open the configured hostname, for example:

```text
https://deepseek-amiga.ai.home.arpa/
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
docker compose logs --tail=50 deepseek-amiga | rg 'dsh web:'
# Open https://deepseek-amiga.ai.home.arpa/?token=... using the printed token.
```

After that one request, DSH redirects to the clean HTTPS URL and uses its
HTTP-only cookie for subsequent requests (normally valid for 30 days). Repeat
the handoff only after clearing browser cookies, changing the hostname, or
when the DSH browser-session credential is reset.

Each project container passes its `DEEPSEEK_*_GATEWAY_HOSTNAME` setting to DSH
as its trusted browser authority. Keep it identical to that project's `caddy`
route label in `projects/*/compose.yml`. This permits same-origin browser API
requests (including workspace and session access) without relaxing DSH's trust
fence for other hostnames.

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

### DSH upgrade compatibility

The local providers are compatible with the pinned DSH `0.2.0-rc.2` release:
they use its current `ctx.web.registerSearchProvider()` and
`ctx.web.registerFetchProvider()` interfaces. The upgrade does not require a
provider rewrite, though the tools remain deliberately disabled pending an
end-to-end smoke test.

Keep the tools disabled until they are deliberately smoke-tested after any DSH
upgrade. DSH is a developer preview and its plugin API is not a stable external
contract. For an upgrade, rebuild the core image, start `searxng` and
`guarded-fetch`, re-enable the two `tool-web` patch entries and the commented
health-based `depends_on` entries, then test one public search and one public
HTTPS fetch in a disposable session. Confirm that a private or loopback URL is
still rejected by `guarded-fetch` before enabling the capability for routine
use.

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

## Local providers

The web profile is seeded with three local OpenAI-compatible routes:

- `llama-cpp` at `http://llama-cpp:8080/v1`, with every model section from
  [`../llama-cpp/config/models-preset.ini`](../llama-cpp/config/models-preset.ini).
- `strata` at `http://strata:8080/v1`, with the one model currently served by
  Strata. It is labelled `loaded-model` in the picker, so changing Strata's
  command-line-selected quant does not require changing DSH configuration.
  The context window remains a configured value (currently 131,072 tokens).

- `model-broker` at `http://model-broker:8000/v1`, with every model of both of the
  above under its full suffixed ID (the llama.cpp sections plus the Strata ones from
  [`../strata/config/models-preset.ini`](../strata/config/models-preset.ini)). The broker
  loads the model a request names, unloading whatever competes for its GPU or RAM, so it
  is the route to use now that `llama-cpp` no longer loads models by itself. A request for
  a model that is not loaded waits for the load; for a Strata model that can take most of
  an hour, so this provider's idle timeout is longer than the others.

The `llama-cpp` and `strata` addresses use the Compose-network service port (`8080`), not a
host-published port. `localhost` would refer to the DeepSeek container.
`LLAMA_CPP_API_KEY` is only a non-secret activation value because llama.cpp
does not validate it. If `STRATA_API_KEY` is set, it protects Strata and DSH
uses the same value; when it is unset, DSH uses a harmless local placeholder. The model
broker has no authentication yet, so `MODEL_BROKER_API_KEY` is likewise only an activation
value.

The first DSH 0.2 boot migrates the legacy model catalogue into the persistent
web profile and retains its source as `settings.yaml.imported` in the
persistent DSH home. Use the Models page to manage the migrated web-profile
catalogue. The headless profile has a separate settings scope; pass an
explicit model when using it until its own configuration is set.

### Persistent local model configuration

[`config/settings.yaml`](./config/settings.yaml) is a one-time seed for a
brand-new DSH home. It is not bind-mounted: DSH 0.2 migrates it into the
writable web-profile patch, where providers and models can survive upgrades
without a repository overlay masking them. The persistent DSH home therefore
contains credentials, sessions, package state, and web model
configuration; back it up as one unit.

The seed's llama.cpp and model broker model lists are generated, not hand-maintained.
After changing `llama-cpp/config/models-preset.ini` or `strata/config/models-preset.ini`, run:

```bash
./deepseek/generate-default-settings.sh
```

The generated seed is used only by a new DSH home. Synchronise an existing
web profile using the Models UI or DSH's settings API; do not delete the
profile merely to re-run migration.
To add the model broker provider (or refresh its model list) in an existing home without the
UI, stop the container, copy and update the profile's patch file, and start it again:

```bash
docker stop deepseek-c
cp /mnt/work/deepseek/.dsh/profiles/web/cordis.patch.yml /mnt/work/deepseek/cordis.patch.yml.bak
./deepseek/add-model-broker-provider.py deepseek/config/settings.yaml \
  /mnt/work/deepseek/.dsh/profiles/web/cordis.patch.yml --default-to-broker
docker start deepseek-c
```

The script refuses to run if the profile already has a `model-broker` provider; to refresh
the list, delete that provider's block from the patch file first.
 When Strata is switched, rerun the
generator only if its context changes, using its live `/v1/models` `meta.n_ctx`:

```bash
STRATA_DSH_CONTEXT=131072 ./deepseek/generate-default-settings.sh
```

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
sessions default to the currently configured `strata` model; pick any
`llama-cpp` model and placement from the same control. A session's existing
model selection remains durable when its capability mode changes.

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
