FROM base-ubuntu-gui-24:latest

ENV DEBIAN_FRONTEND=noninteractive

# Install Visual Studio Code from Microsoft's Debian repository. git and the
# compiler toolchain are useful from both Code's terminal and agent extensions.
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential git gpg gvfs libglib2.0-bin && \
    curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | \
        gpg --dearmor -o /usr/share/keyrings/microsoft.gpg && \
    printf '%s\n' \
        'Types: deb' \
        'URIs: https://packages.microsoft.com/repos/code' \
        'Suites: stable' \
        'Components: main' \
        'Architectures: amd64 arm64 armhf' \
        'Signed-By: /usr/share/keyrings/microsoft.gpg' \
        > /etc/apt/sources.list.d/vscode.sources && \
    apt-get update && \
    apt-get install -y --no-install-recommends code && \
    apt-get clean && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

RUN echo \
'\n[program:vscode]\n\
priority=1\n\
environment=DISPLAY=:0,\n\
            HOME=/home/runuser,\n\
            USER=runuser,\n\
            LOGNAME=runuser\n\
# Chromium's namespace sandbox cannot initialize in a standard Docker container.\n\
command=/usr/bin/code --no-sandbox /workspace\n\
autorestart=true\n\
stdout_logfile=/dev/fd/1\n\
stdout_logfile_maxbytes=0\n\
redirect_stderr=true\n'\
>> /etc/supervisord.conf

RUN mkdir /workspace && \
    chown runuser:runuser /workspace && \
    sed -i 's/Ubuntu GUI App Base Img/Visual Studio Code/g' /etc/supervisord.conf

WORKDIR /workspace
