FROM agent-base-caddy:latest

ARG DEEPSEEK_VERSION=0.1.1-rc.2
ARG PNPM_VERSION=11.24.0

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN npm install --global \
        --allow-scripts=@deepseek-ai/dsh-subprocess-local,koffi,node-pty,@google/genai,protobufjs \
        "@deepseek-ai/dsh@${DEEPSEEK_VERSION}" \
        "pnpm@${PNPM_VERSION}"

# DSH loads capability providers from its own node_modules tree. Both deployed
# providers are local: SearXNG search and a guarded-fetch adapter for fetch.
COPY plugins/dsh-web-search-searxng /opt/dsh-web-search-searxng
COPY plugins/dsh-web-fetch-guarded /opt/dsh-web-fetch-guarded
# Local-directory installs below are symlinks back to /opt. Install the search
# plugin's locked runtime dependencies at that physical path so Node resolves
# its bare `guarded-fetch` import after following the symlink.
RUN npm ci --omit=dev --prefix /opt/dsh-web-search-searxng && \
    npm install --omit=dev \
        --prefix /usr/local/lib/node_modules/@deepseek-ai/dsh \
        /opt/dsh-web-search-searxng \
        /opt/dsh-web-fetch-guarded && \
    npm cache clean --force

COPY init_chowns.sh /usr/local/bin/init_chowns.sh
RUN chmod 744 /usr/local/bin/init_chowns.sh
COPY Caddyfile /etc/Caddyfile

# agent-base-caddy owns the Caddy supervisor program; append DSH alongside it.
RUN printf '%s\n' \
    '' \
    '[program:deepseek]' \
    'command=/usr/local/bin/dsh web --port 3080 --no-open --trusted-host %(ENV_DEEPSEEK_GATEWAY_HOSTNAME)s' \
    'directory=/workspace' \
    'environment=HOME="/home/runuser",USER="runuser",LOGNAME="runuser",DSH_HOME="/home/runuser/.dsh",SSH_CONNECTION="container 0 container 0"' \
    'autostart=true' \
    'autorestart=true' \
    'startsecs=5' \
    'stopasgroup=true' \
    'killasgroup=true' \
    'stdout_logfile=/dev/fd/1' \
    'stdout_logfile_maxbytes=0' \
    'redirect_stderr=true' \
    >> /etc/supervisord.conf

WORKDIR /workspace
