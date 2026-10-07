# Xbox 360 agent environment

This is a Compose overlay for Xbox 360 executable analysis. It retains the
shared agent environment and adds:

- PowerPC and PowerPC64 GNU binutils/cross-compilers;
- `cmake`, Ninja, binary-diff/patch tools (`bsdiff`, `xdelta3`), `xxd`, and
  file identification;
- Xvfb, X11 diagnostics, and `capture-xvfb` for PNG screenshots of the Xvfb
  root framebuffer;
- pinned, checksum-verified Xenia Canary Linux AppImage and Windows x64 builds;
- native 64-bit Wine for the Windows Xenia fallback; and
- Vulkan userspace diagnostics and Mesa Vulkan drivers.

The image intentionally does **not** enable `i386` or install Wine's 32-bit
runtime. Xenia Canary's Windows executable is x86-64. Add a separate project
layer if another selected analysis program is 32-bit.

Capstone is intentionally not installed by APT here. Add it to the target
project's Python dependencies and let `uv` manage the project environment.

## Build and start

Run these from the repository root:

```sh
docker compose -f compose.bases.yml -f compose.ai.yml \
  --profile harness-build build agent-base
docker compose -f compose.bases.yml -f compose.ai.yml \
  --profile harness-build build agent-base-caddy
docker compose -f compose.bases.yml -f compose.ai.yml \
  --profile harness-build build deepseek-core pi-core
docker compose -f compose.bases.yml -f compose.ai.yml \
  -f projects/xbox360/compose.yml build deepseek pi
docker compose -f compose.bases.yml -f compose.ai.yml \
  -f projects/xbox360/compose.yml up -d deepseek pi
```

The overlay Dockerfile inherits the matching tagged harness core image. The
first build follows the parent-to-child commands above; subsequent builds reuse
the core image tags.

## Xenia commands

Start a headless display before launching a GUI build:

```sh
Xvfb :99 -screen 0 1920x1080x24 &
export DISPLAY=:99
xenia-canary-native /workspace/game/default.xex
capture-xvfb /workspace/xenia.png
```

The native AppImage wrapper uses `--appimage-extract-and-run`, so it does not
need FUSE inside the container. To use the Windows fallback instead:

```sh
xenia-canary-wine /workspace/game/default.xex
```

Xenia needs real Vulkan GPU access for useful emulation. The coding-agent
services do not request a GPU by default; add a deliberate Compose GPU/device
overlay before attempting GPU-backed execution.

## Updating Xenia

Set all three variables together in `.env` after obtaining them from the
upstream Xenia Canary release assets:

```dotenv
XENIA_CANARY_RELEASE=cc4981a
XENIA_CANARY_LINUX_SHA256=82914b57c0f673e39e7e43ffe4a0222088520f35e2a05b20ad43a586f811455c
XENIA_CANARY_WINDOWS_SHA256=46d531e3cdc5ab0144509a780005f4736df62264150c49e52bcd2545ef6bf2fc
```

Then rebuild the selected harness images. Do not substitute an unchecked
mutable `latest` URL.
