FROM base-ubuntu-gui-24:latest

ARG GOOSE_VERSION=1.46.0

ENV PATH="/usr/local/lib/goose-cli:${PATH}"

RUN apt-get update && \
    apt-get install -y --no-install-recommends git build-essential xvfb 7zip && \
    apt-get clean && \
    apt-get autoremove && \
    rm -rf /var/lib/apt/lists

# Install uv system-wide for Goose desktop and CLI sessions.
RUN curl -LsSf https://astral.sh/uv/install.sh | \
    env UV_INSTALL_DIR=/usr/local/bin sh

# Install the Goose desktop package and the separately distributed CLI. Keep the
# CLI under its own name because the desktop package owns /usr/bin/goose.
RUN curl -fsSL \
        "https://github.com/aaif-goose/goose/releases/download/v${GOOSE_VERSION}/goose_${GOOSE_VERSION}_amd64.deb" \
        -o /tmp/goose-desktop.deb && \
    apt-get update && \
    apt-get install -y --no-install-recommends /tmp/goose-desktop.deb && \
    rm -f /tmp/goose-desktop.deb && \
    apt-get clean && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/* && \
    curl -fsSL \
        "https://github.com/aaif-goose/goose/releases/download/v${GOOSE_VERSION}/download_cli.sh" \
        -o /tmp/download-goose-cli.sh && \
    GOOSE_BIN_DIR=/usr/local/lib/goose-cli \
        GOOSE_VERSION="${GOOSE_VERSION}" \
        CONFIGURE=false \
        bash /tmp/download-goose-cli.sh && \
    rm -f /tmp/download-goose-cli.sh && \
    ln -s /usr/local/lib/goose-cli/goose /usr/local/bin/goose-cli

RUN echo 'runuser ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/runuser && \
    chmod 0440 /etc/sudoers.d/runuser

RUN echo \
'\n[program:goose]\n\
priority=1\n\
environment=DISPLAY=:0,\n\
            HOME=/home/runuser,\n\
            USER=runuser,\n\
            LOGNAME=runuser\n\
# Chromium's namespace sandbox cannot initialize in a standard Docker container.
command=/usr/lib/goose/Goose --no-sandbox\n\
autorestart=true\n\
stdout_logfile=/dev/fd/1\n\
stdout_logfile_maxbytes=0\n\
redirect_stderr=true\n'\
>> /etc/supervisord.conf

RUN mkdir /workspace && \
    chown runuser:runuser /workspace && \
    sed -i 's/Ubuntu GUI App Base Img/Goose/g' /etc/supervisord.conf

WORKDIR /workspace
