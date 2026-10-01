# Strata (https://github.com/Niko1221/Strata) is not Docker-native: it is a
# self-contained Python installer/launcher (setup.py) that manages its own
# venv, downloads a ready-made engine build and the GGUF model shards, and
# starts an OpenAI/Anthropic-compatible server. None of that is GPU-specific
# at build time, so the image only clones the pinned source; the first
# container start is Strata's own "first run" (engine + model download),
# and every later start is its own fast "just start it" path.
ARG UBUNTU_VERSION=24.04
FROM docker.io/ubuntu:${UBUNTU_VERSION} AS server

ARG STRATA_REPOSITORY=https://github.com/Niko1221/Strata.git
ARG STRATA_COMMIT=d6708a4aae15b4860000d54c8af9e84d684bce09

LABEL org.opencontainers.image.source="${STRATA_REPOSITORY}" \
      org.opencontainers.image.revision="${STRATA_COMMIT}"

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# python3-venv provides ensurepip, which setup.sh checks for before reusing
# a venv; util-linux provides flock for with-gpu-lock; libgomp1 is the
# OpenMP runtime the compiled engine links against.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git ca-certificates curl bash libgomp1 util-linux \
        python3 python3-venv python3-pip && \
    rm -rf /var/lib/apt/lists/*

# Fetch the pinned commit directly. A human-readable branch may later be
# renamed or moved, but it must never determine a reproducible build.
RUN git clone --no-checkout "${STRATA_REPOSITORY}" /app && \
    git -C /app fetch --tags origin "${STRATA_COMMIT}" && \
    git -C /app checkout --detach "${STRATA_COMMIT}" && \
    test "$(git -C /app rev-parse HEAD)" = "${STRATA_COMMIT}"

COPY entrypoint.sh /app/entrypoint.sh
COPY with-gpu-lock /app/with-gpu-lock
RUN chmod 0555 /app/entrypoint.sh /app/with-gpu-lock

WORKDIR /app

# The landing page at "/" is what setup.py's own docs point at to show the
# server is up; a long start_period covers first-run engine/model downloads
# (tens of GB) so they are never mistaken for a crash loop.
HEALTHCHECK --start-period=600s --interval=30s --timeout=5s --retries=5 \
    CMD curl --fail --silent --output /dev/null http://127.0.0.1:8080/ || exit 1

ENTRYPOINT ["/app/with-gpu-lock", "/app/entrypoint.sh"]
