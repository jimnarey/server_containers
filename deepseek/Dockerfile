FROM agent-base-caddy:latest

# Keep the resolved npm latest release explicit; do not float on an npm tag.
ARG DEEPSEEK_VERSION=0.2.0-rc.2
ARG PNPM_VERSION=11.24.0

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN npm install --global \
        --allow-scripts=@deepseek-ai/dsh-subprocess-local,koffi,node-pty,@google/genai,protobufjs \
        "@deepseek-ai/dsh@${DEEPSEEK_VERSION}" \
        "pnpm@${PNPM_VERSION}"

# DSH 0.2 stores user settings in the writable profile patch. Keep this
# repository-owned web capability overlay separate and apply it through DSH's
# supported --patch option rather than masking that writable profile file.
COPY profile-patches/web.cordis.patch.yml /opt/dsh/profile-patches/web.cordis.patch.yml
# A pre-0.2 settings document is a one-time seed for a brand-new persisted
# DSH home. init_chowns.sh copies it only before DSH has created/imported any
# settings, then DSH migrates it into the writable web profile.
COPY config/settings.yaml /opt/dsh/default-settings.yaml

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
    'command=/usr/local/bin/dsh web --patch /opt/dsh/profile-patches/web.cordis.patch.yml --port 3080 --no-open --trusted-host %(ENV_DEEPSEEK_GATEWAY_HOSTNAME)s' \
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
