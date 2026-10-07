FROM node:24.19.0-bookworm-slim AS node-runtime

FROM base-ubuntu-24:latest

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# This is the deliberately small common developer environment for every
# coding-agent image. Target-specific runtimes and SDKs belong under
# projects/, not here.
COPY --from=node-runtime /usr/local/ /usr/local/

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        fd-find \
        git \
        jq \
        pkg-config \
        procps \
        ripgrep \
        socat \
        sudo \
        tmux \
        zstd && \
    ln -sf /usr/bin/fdfind /usr/local/bin/fd && \
    apt-get clean && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | \
        env UV_INSTALL_DIR=/usr/local/bin sh && \
    uv --version

RUN echo 'runuser ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/runuser && \
    chmod 0440 /etc/sudoers.d/runuser && \
    visudo -cf /etc/sudoers.d/runuser && \
    usermod -aG sudo runuser && \
    mkdir -p /workspace && \
    chown runuser:runuser /workspace

ENV UV_CACHE_DIR=/tmp/uv-cache \
    UV_PYTHON_INSTALL_DIR=/home/runuser/.local/share/uv/python \
    UV_PYTHON_PREFERENCE=managed \
    PATH=/home/runuser/.local/bin:/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin

WORKDIR /workspace
