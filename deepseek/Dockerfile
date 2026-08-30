FROM node:24.19.0-bookworm-slim AS node-runtime

FROM base-ubuntu-24:latest

ARG DEEPSEEK_VERSION=0.1.1-rc.2
ARG PNPM_VERSION=11.24.0

COPY --from=node-runtime /usr/local/ /usr/local/

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        git \
        jq \
        procps \
        python3 \
        ripgrep \
        socat \
        sudo \
        tmux && \
    apt-get clean && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

RUN npm install --global \
        --allow-scripts=@deepseek-ai/dsh-subprocess-local,koffi,node-pty,@google/genai,protobufjs \
        "@deepseek-ai/dsh@${DEEPSEEK_VERSION}" \
        "pnpm@${PNPM_VERSION}" && \
    npm cache clean --force

RUN echo 'runuser ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/runuser && \
    chmod 0440 /etc/sudoers.d/runuser && \
    mkdir -p /workspace && \
    chown runuser:runuser /workspace

COPY supervisord.conf /etc/supervisord.conf

WORKDIR /workspace
