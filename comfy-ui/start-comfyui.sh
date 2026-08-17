#!/bin/sh
set -eu

mkdir -p /data/input /data/output /data/temp /data/user /opt/ComfyUI/custom_nodes

# COMFYUI_EXTRA_ARGS is intentionally word-split so normal CLI switches can be
# supplied from .env, for example: --reserve-vram 1.0 --preview-method auto
# shellcheck disable=SC2086
exec /opt/comfyui-venv/bin/python /opt/ComfyUI/main.py \
    --listen 127.0.0.1 \
    --port 8080 \
    --models-directory /models \
    --input-directory /data/input \
    --output-directory /data/output \
    --temp-directory /data \
    --user-directory /data/user \
    --enable-manager \
    --log-stdout \
    ${COMFYUI_EXTRA_ARGS:-}
