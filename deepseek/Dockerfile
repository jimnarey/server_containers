FROM node:24.19.0-bookworm-slim AS node-runtime

FROM base-ubuntu-24:latest

ARG DEEPSEEK_VERSION=0.1.1-rc.2
ARG PNPM_VERSION=11.24.0

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

COPY --from=node-runtime /usr/local/ /usr/local/

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        fd-find \
        git \
        jq \
        libasound2t64 \
        libatk-bridge2.0-0t64 \
        libatk1.0-0t64 \
        libcups2t64 \
        libdbus-1-3 \
        libegl1 \
        libfontconfig1 \
        libglib2.0-0t64 \
        libgtk-3-0t64 \
        libnss3 \
        libopengl0 \
        libxcomposite1 \
        libxdamage1 \
        libxfixes3 \
        libxkbcommon-x11-0 \
        libxkbcommon0 \
        libxtst6 \
        libxcb-cursor0 \
        libxcb-icccm4 \
        libxcb-image0 \
        libxcb-keysyms1 \
        libxcb-render-util0 \
        libxcb-shape0 \
        libxcb-xinerama0 \
        libxcb-xinput0 \
        libxcb-xkb1 \
        pkg-config \
        procps \
        python-is-python3 \
        python3 \
        python3.12-dev \
        ripgrep \
        socat \
        sudo \
        tmux \
        xauth \
        xvfb \
        zstd && \
    ln -sf /usr/bin/fdfind /usr/local/bin/fd && \
    apt-get clean && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/usr/local/bin sh && \
    uv --version

RUN npm install --global \
        --allow-scripts=@deepseek-ai/dsh-subprocess-local,koffi,node-pty,@google/genai,protobufjs \
        "@deepseek-ai/dsh@${DEEPSEEK_VERSION}" \
        "pnpm@${PNPM_VERSION}" && \
    npm cache clean --force

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

COPY init_chowns.sh /usr/local/bin/init_chowns.sh
RUN chmod 744 /usr/local/bin/init_chowns.sh
COPY supervisord.conf /etc/supervisord.conf

WORKDIR /workspace
