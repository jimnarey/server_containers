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

## Local llama.cpp

Pi has native llama.cpp-router support. From an interactive Pi session, run
`/login llama.cpp`, use the in-container API URL below when prompted, then use
`/llama` to manage the router's loaded model and `/model` to select it:

```text
http://llama-cpp:8080/v1
```

Use `http://llama-cpp-cpu:8080/v1` for the CPU router. Do not use `localhost`:
inside the Pi container it identifies Pi itself, not the llama.cpp service.

Pi's provider settings and credentials are user state under `PI_HOME`; they are
not committed to this repository.
