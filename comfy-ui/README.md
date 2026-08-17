# ComfyUI

This service runs the ComfyUI web application directly behind the repository's
Caddy basic-auth proxy. It uses the NVIDIA GPU and does not need VNC.

## Configure and start

Copy the ComfyUI settings from `.env_template` into `.env` if you want to
override their defaults. In particular, set `COMFYUI_BIND_ADDRESS` to an IP
assigned to the host. The existing `CADDY_HASH` controls the web password.

Create the bind-mount directories as UID/GID 1000, then build and start the
service:

```bash
sudo install -d -o 1000 -g 1000 \
  /mnt/data/models/comfyui \
  /mnt/data/generation/input \
  /mnt/data/generation/output \
  /mnt/work/comfyui/user \
  /mnt/work/comfyui/custom_nodes

docker compose build comfyui
docker compose up -d comfyui
```

Open `http://<COMFYUI_BIND_ADDRESS>:<COMFYUI_PORT>` (port 9034 by default) and
sign in with the Caddy credentials. ComfyUI itself only listens on loopback
inside the container, so it is not exposed without the authenticated proxy.

## Persistent data

The default host paths are:

| Data | Host path |
| --- | --- |
| Models | `/mnt/data/models/comfyui` |
| Uploaded inputs | `/mnt/data/generation/input` |
| Generated output | `/mnt/data/generation/output` |
| Workflows, settings and Manager data | `/mnt/work/comfyui/user` |
| Third-party custom nodes | `/mnt/work/comfyui/custom_nodes` |

Put checkpoints in `models/comfyui/checkpoints`, LoRAs in
`models/comfyui/loras`, VAEs in `models/comfyui/vae`, and so on. ComfyUI-Manager
is enabled and can install models and custom nodes into these mounts. Treat
third-party nodes as executable code and install only sources you trust.

## Security

ComfyUI and ComfyUI-Manager are pinned above the patched versions for
[CVE-2025-67303](https://github.com/Comfy-Org/ComfyUI-Manager/security/advisories/GHSA-95pq-hr8p-f5g7).
That vulnerability allowed remote users of older installations to alter
Manager configuration through an insufficiently protected user-data path. The
fix requires ComfyUI 0.3.76 or later and Manager 3.38 or later; this image uses
ComfyUI 0.29.2 and Manager 4.2.2.

ComfyUI listens only on `127.0.0.1` inside the container. LAN access passes
through Caddy basic authentication on port 8081. Do not publish ComfyUI's
internal port 8080 or remove the proxy authentication when exposing the
service beyond the host.

Custom nodes are executable Python code, not passive workflow data. A custom
node can read or modify every writable path available to ComfyUI, install
Python dependencies, make network connections, and consume system resources.
In this service that includes the model, input, output, user and custom-node
mounts. It does not include a general host workspace, and ComfyUI runs as
UID/GID 1000 rather than host root.

Recommended precautions:

- Keep Manager at its `normal` or `strong` security level.
- Prefer established nodes from the default registry and review their source.
- Avoid arbitrary Git URLs and pip packages unless you trust the publisher.
- Treat workflows from unknown sources cautiously if they request missing
  custom nodes.
- Back up the user and custom-node directories before installing or updating
  several extensions.
- Keep ComfyUI and Manager above their patched minimum versions when changing
  the version pins in `.env`.

## GPU and memory

ComfyUI and Ollama compete for the same 16 GB of VRAM. Before a large image or
video workflow, unload Ollama's resident models:

```bash
docker compose exec ollama ollama stop <model-name>
docker compose exec ollama ollama ps
```

Extra ComfyUI switches can be placed in `.env`, for example:

```dotenv
COMFYUI_EXTRA_ARGS=--reserve-vram 1.0 --preview-method auto
```

Avoid `--highvram` on a 16 GB card unless the entire workflow is known to fit.
The default dynamic VRAM/offload behaviour is a safer starting point.

## Operations and diagnostics

```bash
docker compose ps comfyui
docker compose logs -f comfyui
docker compose exec comfyui nvidia-smi
curl -u admin:<password> http://<COMFYUI_BIND_ADDRESS>:9034/system_stats
```

The image pins ComfyUI and the PyTorch CUDA wheels through `.env`. To upgrade,
change the pinned versions, rebuild, and review the upstream release notes
first. Existing models, workflows, outputs and custom nodes survive rebuilds.
