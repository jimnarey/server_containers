# Server Containers

Dockerfiles and Compose definitions for a home-server toolkit of browser-accessible desktops, GUI apps, file tools, media utilities, and a few network services.

Most GUI containers follow the same pattern:

- Ubuntu base image
- `supervisord` for process management
- `caddy` for HTTP access and basic auth
- TigerVNC + noVNC/websockify for browser-based remote desktop
- a non-root `runuser` account with configurable UID/GID

This repo contains both reusable base images and app-specific images built on top of them.

## Scope And Portability

This is a personal repository built for one server and its owner's workflows. It is published in the hope that parts of it are useful to other people, but it is not currently a portable, turnkey distribution. The Compose file and supporting configuration retain traces of the local installation, including host paths, LAN addresses, port choices, UID/GID assumptions, model names, and hardware expectations.

Anyone reusing it should review the complete effective configuration before starting services:

```bash
docker compose config
```

In particular, do not assume that paths below `/mnt`, the address `192.168.50.136`, UID/GID 1000, GPU settings, or the agent credential path `/container-ssh` are appropriate on another host.

## Structure

The repository is organised in layers:

- `base-ubuntu-*`: minimal Ubuntu base images with shared tooling
- `base-ubuntu-caddy-*`: adds Caddy and authenticated web access
- `base-ubuntu-gui-*`, `base-ubuntu-xfce-*`, `base-ubuntu-kde-*`: adds desktop/UI stacks
- `base-ubuntu-wine-*`, `base-ubuntu-kde-wine-24`: adds Wine for Windows GUI apps
- app folders such as `calibre/`, `double-commander/`, `inkscape/`, `lightburn/`, `transmission/`, `webdav/`
- `docker-compose.yml`: main build/run definitions
- `transmission-vpn.yml`: runs `transmission` through the `expressvpn` container network
- `Makefile`: older convenience targets for building and running individual images

## Prerequisites

- Docker
- Docker Compose v2
- A Linux host if you need device passthrough such as `/dev/net/tun`, `/dev/ttyUSB0`, or `/dev`
- Host directories such as `/mnt` or `/media` if you plan to use the containers that mount them

## Configuration

Copy `.env_template` to `.env` and fill in the values you need:

```bash
cp .env_template .env
```

Common variables:

- `CADDY_HASH`: bcrypt hash used by Caddy basic auth
- `TRANSMISSION_PASSWORD`: build-time password for the Transmission image
- `DROPBOX_FOLDER`, `CALIBRE_LIBRARY`, `CALIBRE_SOURCE`, `WEBDAV_ROOT`, `LASER_CUTTING_ROOT`, `MEGANZ_LOCAL`: host paths mounted into specific services
- `WEBDAV_USERNAME`, `WEBDAV_PASSWORD`: build args for `webdav-apache`

To generate a Caddy bcrypt hash:

```bash
docker compose build base-ubuntu-caddy-24
docker run --rm -it base-ubuntu-caddy-24:latest \
  caddy hash-password --algorithm bcrypt
```

The Compose file reads `.env`. Some older `Makefile` targets expect an `env.sh` file that can be sourced in the shell; if you use those targets, create a compatible file locally.

Environment-variable coverage is incomplete. Newer services generally expose their important paths and ports through `.env`, but a number of older services and some recently added integration mounts still contain literal host paths and addresses in `docker-compose.yml`. Moving those remaining values into `.env` is intentional future cleanup. Until then, inspect and edit both files when adapting the repository to another machine.

## HTTP And Network Security

The browser services currently operate over HTTP. There is not yet a shared TLS termination layer or general-purpose HTTPS gateway in front of the Compose stack. Services described as using Caddy generally use it for HTTP reverse proxying and basic authentication; that does not encrypt credentials or traffic.

Treat LAN-published ports as trusted-network services. Use SSH port forwarding for host-loopback services, especially DeepSeek Harness, and do not expose the current endpoints directly to the internet. A central authenticated Caddy HTTPS gateway is planned, but its trust boundaries, hostnames, certificates, and per-service access policy have not yet been settled.

DeepSeek is more complicated than the other HTTP applications: its privileged configuration APIs deliberately trust loopback, the application binds inside the container to loopback, and the Compose service publishes only host loopback. A supervised TCP relay bridges those two boundaries so an SSH tunnel can reach the UI. See [`deepseek/README.md`](./deepseek/README.md) before changing that binding or placing a proxy in front of it.

## Quick Start

Build the current base images:

```bash
./build_bases.sh
```

Or with Compose profiles:

```bash
docker compose --profile base build
```

Build and start a service:

```bash
docker compose build calibre
docker compose up -d calibre
```

For a GUI container, open the mapped host port in your browser and sign in with the Caddy credentials you configured.

Stop a service:

```bash
docker compose down
```

## Common Workflows

Build one app image:

```bash
docker compose build double-commander
```

Run a desktop-style container:

```bash
docker compose up -d desktop-kde
```

Run Transmission behind ExpressVPN:

```bash
docker compose -f transmission-vpn.yml up -d
```

Tear down the VPN stack:

```bash
docker compose -f transmission-vpn.yml down
```

## Services

These are the main services currently defined in `docker-compose.yml`:

- Desktop environments: `desktop-kde`, `desktop-xfce`, `desktop-dropbox`
- File and sync tools: `double-commander`, `filezilla`, `webdav`, `webdav-apache`, `meganz`
- Media/library tools: `calibre`, `clrmamepro`, `nkit`, `jrom-manager`, `simple-arcade-multifilter`
- Design / maker tools: `inkscape`, `laserweb`, `lightburn`, `lightburn-win`, `lightburn-win-install`, `lasergrbl`, `lasergrbl-install`
- Network / download tools: `transmission`, `expressvpn`
- Local AI inference: `ollama`, `ollama-cpu`, `llama-cpp`
- Coding agents and development: `deepseek`, `goose`, `openhands`, `opencode`, `vscode`
- Generative media: `comfyui`
- Other utilities: `hexchat`, `retroarch-web`, `octoprint`, `exodos`

Not every folder in the repo is currently wired into Compose; some are templates, experiments, or older variants kept for reuse.

## Base Image Stack

The current Ubuntu 24 flow looks like this:

```text
base-ubuntu-24
  -> base-ubuntu-caddy-24
    -> base-ubuntu-gui-24 / base-ubuntu-kde-24 / base-ubuntu-wine-24 / base-ubuntu-xfce-24
      -> app-specific images
```

This makes it easier to share:

- user and permission setup
- Caddy config
- `supervisord` process handling
- VNC/noVNC browser access
- desktop session startup

## Notes On Access And Permissions

- Many GUI services expose port `8081` inside the container and map it to a host port in Compose.
- Most services accept `USERID` and `GROUPID` so files written to mounted volumes match the host user.
- Some containers require `privileged: true` or device access for USB hardware and VPN networking.
- Several services mount `/mnt` and `/media` directly from the host; adjust those paths if your server layout differs.

## Makefile

The `Makefile` contains per-service `build-*` and `run-*` shortcuts. They are useful as examples, but they are less consistent than the Compose file and rely on local shell variables from `env.sh`.

Prefer `docker compose` for day-to-day use unless you specifically want the older one-off commands.

## Repository Notes

- The older root [`readme.md`](./readme.md) is still present for historical context.
- Some subdirectories also include their own notes, such as [`expressvpn/README.md`](./expressvpn/README.md) and [`lasergrbl-install/README.md`](./lasergrbl-install/README.md).
- A few paths referenced by the `Makefile` are not present in this checkout, so treat it as a helper rather than the canonical source of truth.
