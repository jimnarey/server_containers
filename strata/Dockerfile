# Strata (https://github.com/Niko1221/Strata) is not Docker-native: it is a
# self-contained Python installer/launcher (setup.py) that manages its own
# venv, downloads a ready-made engine build and the GGUF model shards, and
# starts an OpenAI/Anthropic-compatible server.
#
# As of the pinned commit there is no published GitHub release, so the
# "ready-made engine" download 404s and setup.py always falls back to
# compiling from source. That path calls `sudo apt-get install ...`
# unconditionally to fetch build-essential and the CUDA Toolkit, which fails
# outright in a container with no sudo. Rather than add sudo and let it
# apt-get 8-10 GB of toolchain into the container's writable layer on every
# first run, this image starts from a CUDA 13.0 *devel* base (13.0.2, matching
# the exact minor version setup.py pins its nvidia-cublas wheel to) with
# build-essential also installed: setup.py's own install_build_tools() checks
# for g++ and nvcc before ever touching sudo, finds both already present, and
# skips straight to compiling - see its build_engine()/cmake_build(). RTX 50
# series (sm_120) specifically needs CUDA >= 13.0 for this (setup.py's own
# comment: "an engine built with 12.8 crashed in the prompt path on Linux").
# If/when Niko1221/Strata publishes a release, update_installed_engine() will
# prefer the ready-made download instead and this toolchain goes unused.
ARG CUDA_IMAGE_TAG=13.0.2-devel-ubuntu24.04
FROM docker.io/nvidia/cuda:${CUDA_IMAGE_TAG} AS server

ARG STRATA_REPOSITORY=https://github.com/Niko1221/Strata.git
ARG STRATA_COMMIT=d6708a4aae15b4860000d54c8af9e84d684bce09

LABEL org.opencontainers.image.source="${STRATA_REPOSITORY}" \
      org.opencontainers.image.revision="${STRATA_COMMIT}"

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# python3-venv provides ensurepip, which setup.sh checks for before reusing
# a venv; util-linux provides flock for with-gpu-lock; libgomp1 is the
# OpenMP runtime the compiled engine links against; build-essential is the
# C++ compiler setup.py looks for (g++) before compiling the engine.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git ca-certificates curl bash libgomp1 util-linux build-essential \
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
# server is up. A long start_period covers a first run that both compiles the
# engine (setup.py's own estimate: 15-40 minutes) and downloads the model
# (tens of GB), so neither is ever mistaken for a crash loop.
HEALTHCHECK --start-period=2700s --interval=30s --timeout=5s --retries=5 \
    CMD curl --fail --silent --output /dev/null http://127.0.0.1:8080/ || exit 1

ENTRYPOINT ["/app/with-gpu-lock", "/app/entrypoint.sh"]
