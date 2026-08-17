FROM base-ubuntu-caddy-24:latest

ARG CODE_SERVER_VERSION=4.132.0

RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential git sudo && \
    curl -fsSL \
        "https://github.com/coder/code-server/releases/download/v${CODE_SERVER_VERSION}/code-server-${CODE_SERVER_VERSION}-linux-amd64.tar.gz" \
        -o /tmp/code-server.tar.gz && \
    tar -xzf /tmp/code-server.tar.gz -C /opt && \
    ln -s "/opt/code-server-${CODE_SERVER_VERSION}-linux-amd64/bin/code-server" \
        /usr/local/bin/code-server && \
    rm -f /tmp/code-server.tar.gz && \
    apt-get clean && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

RUN echo 'runuser ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/runuser && \
    chmod 0440 /etc/sudoers.d/runuser

RUN mkdir /workspace && \
    chown runuser:runuser /workspace

# Caddy provides authentication and proxies external port 8081 to this
# loopback-only server. No desktop environment, Electron, or VNC is involved.
RUN echo \
'\n[program:vscode]\n\
priority=1\n\
command=/usr/local/bin/code-server --bind-addr 127.0.0.1:8080 --auth none --disable-telemetry /workspace\n\
directory=/workspace\n\
environment=HOME=/home/runuser,USER=runuser,LOGNAME=runuser\n\
autorestart=true\n\
stopasgroup=true\n\
killasgroup=true\n\
stdout_logfile=/dev/fd/1\n\
stdout_logfile_maxbytes=0\n\
redirect_stderr=true\n'\
>> /etc/supervisord.conf

WORKDIR /workspace
