FROM base-ubuntu-24:latest

ARG OPENCODE_VERSION=1.18.9

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        git \
        nodejs \
        npm \
        sudo && \
    apt-get clean && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://opencode.ai/install -o /tmp/install-opencode.sh && \
    VERSION="${OPENCODE_VERSION}" \
        bash /tmp/install-opencode.sh --no-modify-path && \
    install -m 0755 /root/.opencode/bin/opencode /usr/local/bin/opencode && \
    rm -rf /root/.opencode /tmp/install-opencode.sh

RUN curl -LsSf https://astral.sh/uv/install.sh | \
    env UV_INSTALL_DIR=/usr/local/bin sh

RUN echo 'runuser ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/runuser && \
    chmod 0440 /etc/sudoers.d/runuser

RUN mkdir /workspace && \
    chown runuser:runuser /workspace

RUN echo \
'\n[program:opencode]\n\
command=/usr/local/bin/opencode web --hostname 0.0.0.0 --port 4096\n\
directory=/workspace\n\
environment=HOME=/home/runuser,USER=runuser,LOGNAME=runuser\n\
autorestart=true\n\
stdout_logfile=/dev/fd/1\n\
stdout_logfile_maxbytes=0\n\
redirect_stderr=true\n'\
>> /etc/supervisord.conf

WORKDIR /workspace
