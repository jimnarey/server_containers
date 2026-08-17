# Goose

This service runs the Goose desktop application in the browser and installs the
Goose command-line interface alongside it.

Start the service with:

```sh
docker compose up -d goose
```

Open the desktop at `http://<docker-host>:9031`.

## CLI Access

Run the CLI directly through Compose as the desktop user:

```sh
docker compose exec --user runuser goose goose-cli
```

Running it as `runuser` is important: Goose configuration and credentials are
stored under `/home/runuser`, which is persisted by the `goose-home` volume.

To open a shell first and then run commands interactively:

```sh
docker compose exec --user runuser goose bash
goose-cli
```

The command is named `goose-cli` in this image because the desktop package owns
the `/usr/bin/goose` executable. Both the CLI binary and `uv` are available on
the container's system-wide `PATH`.

## Workspace

The container starts in `/workspace`. By default, Compose mounts `/mnt` from the
host there. Override the host directory in `.env` if required:

```dotenv
GOOSE_WORKSPACE=/mnt/data/projects
```

After changing it, recreate the service:

```sh
docker compose up -d --force-recreate goose
```

### Run the CLI in a Project Directory

The installed Goose CLI does not provide a working-directory option. Use
Compose's `--workdir` (or `-w`) option to start it in a project under the mounted
workspace:

```sh
docker compose exec \
  --user runuser \
  --workdir /workspace/amiga-ui \
  goose \
  goose-cli run --text "Your task"
```

The equivalent short form is:

```sh
docker compose exec -u runuser -w /workspace/amiga-ui goose goose-cli run
```

Alternatively, open a shell and change directory before starting Goose:

```sh
docker compose exec --user runuser goose bash
cd /workspace/amiga-ui
goose-cli run
```

The selected directory must exist inside `/workspace`. Goose's `--path` option
is a legacy session-path argument; it does not set the working directory.

## Using the Compose Ollama Service

From inside the Goose container, `localhost` refers to Goose itself. To connect
to the Ollama service in this Compose project, use:

```text
http://ollama:11434
```

Do not use `http://localhost:11434` unless Ollama is running inside the Goose
container.
