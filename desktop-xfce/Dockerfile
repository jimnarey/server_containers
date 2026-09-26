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

# Blender from the official release tarball (Ubuntu 24.04's apt package is 4.0).
# Pinned to an LTS point release and verified against the checksum published at
# https://download.blender.org/release/Blender5.2/blender-5.2.2.sha256
ARG BLENDER_VERSION=5.2.2
ARG BLENDER_SHA256=84098912789dc450e95697c4184fb8a90acbe5111c2ba4aede3fecb57806a168
RUN apt-get update && apt-get install -y --no-install-recommends \
        libdecor-0-0 \
        libegl1 \
        libfontconfig1 \
        libgl1 \
        libgl1-mesa-dri \
        libice6 \
        libsm6 \
        libwayland-client0 \
        libwayland-cursor0 \
        libwayland-egl1 \
        libx11-6 \
        libxext6 \
        libxfixes3 \
        libxi6 \
        libxkbcommon0 \
        libxrender1 \
        libxxf86vm1 && \
    apt-get clean && rm -rf /var/lib/apt/lists/* && \
    curl -fsSL -o /tmp/blender.tar.xz \
        "https://download.blender.org/release/Blender${BLENDER_VERSION%.*}/blender-${BLENDER_VERSION}-linux-x64.tar.xz" && \
    echo "${BLENDER_SHA256}  /tmp/blender.tar.xz" | sha256sum -c - && \
    mkdir -p /opt/blender && \
    tar -xJf /tmp/blender.tar.xz -C /opt/blender --strip-components=1 && \
    rm /tmp/blender.tar.xz && \
    ln -s /opt/blender/blender /usr/local/bin/blender && \
    install -Dm644 /opt/blender/blender.desktop /usr/share/applications/blender.desktop && \
    install -Dm644 /opt/blender/blender.svg /usr/share/icons/hicolor/scalable/apps/blender.svg && \
    blender --version

RUN echo 'runuser ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/runuser && \
    chmod 0440 /etc/sudoers.d/runuser && \
    visudo -cf /etc/sudoers.d/runuser

ENV UV_CACHE_DIR=/tmp/uv-cache \
    UV_PYTHON_INSTALL_DIR=/home/runuser/.local/share/uv/python \
    UV_PYTHON_PREFERENCE=managed \
    PATH=/home/runuser/.local/bin:/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin


