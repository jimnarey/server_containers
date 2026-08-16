# OpenCode

This service runs the OpenCode web interface and server in an Ubuntu container.
It runs as `runuser` (UID/GID 1000 by default), has passwordless `sudo` inside
the container, and persists its configuration, credentials, and sessions in the
`opencode-home` volume.

## Configuration

Set a web password in the repository's `.env` file before using Compose:

```dotenv
OPENCODE_SERVER_PASSWORD=replace-with-a-long-random-password
```

Optional settings are:

```dotenv
OPENCODE_SERVER_USERNAME=opencode
OPENCODE_VERSION=1.18.9
OPENCODE_WORKSPACE=/mnt/data/projects
```

The workspace defaults to `/mnt/data/projects` on the host and is available as
`/workspace` in the container. OpenCode configuration is stored under
`/home/runuser/.config/opencode`, while credentials and session data are stored
under `/home/runuser/.local/share/opencode`; both persist in `opencode-home`.

## Start and access the web interface

```bash
docker compose build opencode
docker compose up -d opencode
```

Open `http://192.168.50.136:9032` and sign in with the configured username and
password.

For Ollama, use `http://ollama:11434`, not `localhost:11434`, because Ollama is
a separate container on the Compose network.

## Attach the TUI

Attach the terminal UI to the same server and sessions:

```bash
docker compose exec opencode \
  opencode attach http://localhost:4096 --dir /workspace
```

To open a specific repository, change `--dir`, for example:

```bash
docker compose exec opencode \
  opencode attach http://localhost:4096 \
  --dir /workspace/amiga-ui
```

If the host workspace is `/mnt/work/projects` instead, set
`OPENCODE_WORKSPACE=/mnt/work/projects` in `.env`; `amiga-ui` will still appear
at `/workspace/amiga-ui` inside the container.

## Shell and one-shot commands

Open a shell:

```bash
docker compose exec opencode bash
```

Run a one-shot task:

```bash
docker compose exec -w /workspace/amiga-ui opencode \
  opencode run "Review this repository and explain how to run its checks."
```
