#!/bin/sh
# setup.py treats an explicit --family/--model as "the full, idempotent
# install-or-start path" (never the bare "start whatever is already
# installed" shortcut), and skips whatever step is already done - so it is
# safe to pass the same flags on every container start: the first start
# downloads the engine and model, every later one just starts them.
set -eu

: "${STRATA_FAMILY:=qwen}"
: "${STRATA_MODEL:=IQ3_S}"
: "${STRATA_CONTEXT:=65536}"
: "${STRATA_KV:=int8}"
: "${STRATA_VISION:=no}"
: "${STRATA_DATA_DIR:=/data}"
: "${STRATA_MODELS_DIR:=/models}"

# Compose restricts this container to exactly one physical GPU (device_ids),
# so it is always index 0 from Strata's point of view. The physical id only
# matters to with-gpu-lock, which acquires the shared lock before exec'ing
# this script.
set -- --yes \
    --family "$STRATA_FAMILY" \
    --model "$STRATA_MODEL" \
    --context "$STRATA_CONTEXT" \
    --kv "$STRATA_KV" \
    --vision "$STRATA_VISION" \
    --gpu 0 \
    --host 0.0.0.0 \
    --port 8080 \
    --data-dir "$STRATA_DATA_DIR" \
    --models-dir "$STRATA_MODELS_DIR"

if [ -n "${STRATA_API_KEY:-}" ]; then
    set -- "$@" --api-key "$STRATA_API_KEY"
fi

exec ./setup.sh "$@"
