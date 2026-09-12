FROM base-ubuntu-xfce-24:latest

RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-client \
    file-roller \
    engrampa \
    unzip \
    zip \
    p7zip-full \
    p7zip-rar \
    unrar \
    rar \
    arj \
    lhasa \
    unace \
    cabextract \
    cpio \
    tar \
    gzip \
    bzip2 \
    xz-utils \
    lrzip \
    lzip \
    lzop \
    zstd \
    f3d \
    evince \
    git \
    build-essential \
    gnupg \
    apt-transport-https \
    && apt-get clean \
    && apt-get autoremove \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /etc/apt/keyrings && \
    wget -qO- https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > /etc/apt/keyrings/packages.microsoft.gpg && \
    chmod 644 /etc/apt/keyrings/packages.microsoft.gpg && \
    echo "deb [arch=amd64,arm64,armhf signed-by=/etc/apt/keyrings/packages.microsoft.gpg] https://packages.microsoft.com/repos/code stable main" > /etc/apt/sources.list.d/vscode.list && \
    apt-get update && apt-get install -y --no-install-recommends code && \
    apt-get clean && apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/usr/local/bin sh && \
    uv --version

RUN echo 'runuser ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/runuser && \
    chmod 0440 /etc/sudoers.d/runuser && \
    visudo -cf /etc/sudoers.d/runuser

ENV UV_CACHE_DIR=/tmp/uv-cache \
    UV_PYTHON_INSTALL_DIR=/home/runuser/.local/share/uv/python \
    UV_PYTHON_PREFERENCE=managed \
    PATH=/home/runuser/.local/bin:/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin


