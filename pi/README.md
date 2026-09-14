# Pi Coding Agent

This is a persistent terminal container for [Pi Coding Agent](https://pi.dev/).
It runs Pi as `runuser` (UID/GID 1000 by default) and exposes no HTTP port.
Attach using Docker Compose's terminal support instead.

Pi's state is persisted outside this repository by default:

```text
/mnt/work/pi/.pi/agent/
```

This includes its sessions, `auth.json`, model cache, installed packages, and
user-level extensions. Projects under `/mnt/work/projects` are mounted at
`/workspace`. The restricted GitHub automation identity at `/container-ssh` is
available read-only at `/home/runuser/.ssh`.

## Configuration

Optional `.env` settings are:

```dotenv
PI_VERSION=0.85.1
PI_HOME=/mnt/work/pi
PI_WORKSPACE=/mnt/work/projects
```

The image pins `PI_VERSION`; update that value deliberately, then rebuild the
service. `PI_SKIP_VERSION_CHECK=1` and `PI_TELEMETRY=0` prevent background
version checks and telemetry from the running agent.

## Start and attach

```sh
docker compose build pi
docker compose up -d pi
docker compose exec -it -w /workspace pi pi
```

To work in one project:

```sh
docker compose exec -it -w /workspace/amiga-ui pi pi
```

Pi is a terminal coding agent: its shell tool runs as `runuser` and can modify
the mounted workspace. Its developer environment matches the DeepSeek harness:
it includes the same apt-installed build, Python, Qt/X11, diagnostics, and
terminal utilities; `uv`; and passwordless `sudo` for `runuser`. Use `sudo`
only when a task genuinely requires a system-level change inside the container.

## Long-running work

Pi saves each session under `PI_HOME`, but an in-progress terminal session is
still tied to its terminal. Run it inside the included `tmux` when an agent
needs to survive an SSH disconnect:

```sh
docker compose exec -it -w /workspace/amiga-ui pi \
  tmux new-session -A -s pi-amiga-ui
```

Start `pi` in that tmux shell, then detach with `Ctrl-b d`. Reattach later with
the same command. If Pi itself has exited, use `pi -r` to select and resume the
saved session for that project.

Pi already provides the durable mechanisms most useful for long runs: automatic
context compaction, session trees, `/fork`, `/clone`, `/resume`, and `/compact`.
Keep generic project instructions in `AGENTS.md` and project-specific settings
in `.pi/settings.json`, rather than baking a one-size-fits-all prompt or an
unreviewed third-party extension into the image.

## Local providers and models

Pi uses a repository-managed catalogue of every model currently advertised by
each local provider: the GPU and CPU upstream llama.cpp routers, both
GenerelSchwerz MoE routers, and Ollama. The generated catalogue uses Compose
service names, so it works inside the Pi container without publishing another
host port or relying on `localhost`.

Synchronise after changing a router's effective catalogue (for example, after
regenerating and installing a llama.cpp preset). The normal form refreshes any
running provider and retains cached catalogues for intentionally stopped ones:

```sh
./pi/sync-config.py
```

Because the large-model services are not normally safe to run together, the
first catalogue can also be built one provider at a time. Start the provider,
then run one of the following; later runs merge its fresh result into the same
catalogue:

```sh
./pi/sync-config.py --provider llama-cpp
./pi/sync-config.py --provider llama-cpp-cpu
./pi/sync-config.py --provider llama-cpp-moe-16gb
./pi/sync-config.py --provider llama-cpp-moe-32gb
./pi/sync-config.py --provider ollama
```

The script asks each provider's live `/v1/models` endpoint for its model IDs and
effective context sizes. If a provider is deliberately stopped, its catalogue is
preserved from the previous successful run; a previously unseen stopped provider
is skipped until it can be refreshed explicitly. Use `--require-all` to reject
cached or unavailable results, or `--dry-run` to inspect the result without
writing it. `PI_HOME` or `--pi-home` changes the persistent Pi location. The
`PI_*_MODELS_URL` variables at the top of the script permit manual endpoint
overrides when this repository is deployed differently.

The only managed files are:

```text
${PI_HOME}/.pi/agent/models.json
${PI_HOME}/.pi/agent/settings.json
```

`models.json` contains an explicit OpenAI-compatible provider catalogue. A
literal `local` API key is only Pi's availability marker for keyless local
servers; it is not a credential or access control. `settings.json` selects the
Qwen3.8 27B Q6 GPU model by default, allows an hour for a local request/model
load, and derives context-aware compaction reserves for each advertised model.
It keeps the existing long-context Qwen3.8 and Flash Next settings deliberately
larger than the generic model defaults.

Pi sessions, `auth.json`, trust decisions, installed packages, and user
extensions remain under `PI_HOME` but are neither copied nor replaced. To set a
different default for one project, use that project's `.pi/settings.json` or
Pi's `/model` and save it there.

The native `/login llama.cpp` and `/llama` commands remain useful for an ad-hoc
single-router connection. They are not needed for the managed multi-provider
catalogue and do not replace it. Do not use `localhost` for a direct provider
inside the Pi container: it identifies Pi itself, not the llama.cpp service.

## Web search and guarded fetch

Every normal `pi` invocation loads a repository-maintained global extension
that gives the agent two web tools. `web_search` queries the local SearXNG JSON
API for up to eight bounded general-search results. `web_fetch` then sends a
selected public HTTPS URL to the Compose-local `guarded-fetch` service; it
cannot supply HTTP methods, headers, cookies, or a body. The gateway applies
its SSRF, redirect, timeout, and response-size controls before returning
bounded text.

The tools are temporarily disabled by default with
`PI_WEB_EXTENSIONS_ENABLED=0`. Set `PI_WEB_EXTENSIONS_ENABLED=1` in `.env` to
load them again. The gateway and SearXNG dependencies remain in place so that
re-enabling needs only a Pi recreation.

`pi` depends on both `guarded-fetch` and SearXNG becoming healthy and uses
their Compose service names, so no host port or user configuration is needed.
Rebuild Pi and recreate the services after changing the extension wrapper:

```sh
docker compose build pi guarded-fetch
docker compose up -d --force-recreate guarded-fetch pi
```

When enabled, the extension tells Pi to use `web_search` to discover pages and
`web_fetch` to read them, while treating search results and page text as
untrusted. Pi still has normal network access for Git, `uv`, and other
development tools; this is a safer default fetch capability, not enforced
egress isolation. `pi-real` is retained only for image diagnostics and bypasses
the extension.
