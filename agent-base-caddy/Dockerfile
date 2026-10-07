FROM agent-base:latest

ARG CADDY_VERSION=2.8.2

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN wget -q -O /tmp/caddy.tar.gz \
        "https://github.com/caddyserver/caddy/releases/download/v${CADDY_VERSION}/caddy_${CADDY_VERSION}_linux_amd64.tar.gz" && \
    tar -xzf /tmp/caddy.tar.gz -C /usr/local/bin caddy && \
    rm /tmp/caddy.tar.gz && \
    chmod 0755 /usr/local/bin/caddy

EXPOSE 8081

# DeepSeek supplies its own Caddyfile, but Caddy's supervisor program is part
# of the web-harness runtime rather than any individual project environment.
RUN printf '%s\n' \
    '' \
    '[program:caddy]' \
    'priority=1' \
    'command=/usr/local/bin/caddy run --adapter caddyfile --config /etc/Caddyfile' \
    'autorestart=true' \
    'stdout_logfile=/dev/fd/1' \
    'stdout_logfile_maxbytes=0' \
    'redirect_stderr=true' \
    >> /etc/supervisord.conf
