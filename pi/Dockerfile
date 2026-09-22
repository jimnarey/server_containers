FROM node:24.19.0-bookworm-slim AS node-runtime

FROM base-ubuntu-24:latest

ARG PI_VERSION=0.85.1

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
        python3-capstone \
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

RUN npm install --global --ignore-scripts \
        "@earendil-works/pi-coding-agent@${PI_VERSION}" && \
    npm cache clean --force

# Keep the trusted global extension in the image, rather than PI_HOME, so a
# fresh persistent Pi home still receives the same guarded web_fetch tool.
RUN mv /usr/local/bin/pi /usr/local/bin/pi-real
COPY extensions/ /opt/pi-extensions/
COPY bin/pi /usr/local/bin/pi
RUN cd /opt/pi-extensions && \
    npm install --omit=dev --ignore-scripts && \
    npm cache clean --force && \
    chmod -R a-w /opt/pi-extensions && \
    chmod 0755 /usr/local/bin/pi

RUN curl -LsSf https://astral.sh/uv/install.sh | \
        env UV_INSTALL_DIR=/usr/local/bin sh && \
    uv --version

RUN echo 'runuser ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/runuser && \
    chmod 0440 /etc/sudoers.d/runuser && \
    visudo -cf /etc/sudoers.d/runuser

RUN mkdir -p /workspace && \
    chown runuser:runuser /workspace

ENV UV_CACHE_DIR=/tmp/uv-cache \
    UV_PYTHON_INSTALL_DIR=/home/runuser/.local/share/uv/python \
    UV_PYTHON_PREFERENCE=managed \
    PATH=/home/runuser/.local/bin:/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin

WORKDIR /workspace
