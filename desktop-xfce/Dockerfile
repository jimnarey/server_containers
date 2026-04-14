FROM base-ubuntu-xfce-24:latest

RUN apt-get update && apt-get install -y --no-install-recommends \
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
    && apt-get clean \
    && apt-get autoremove \
    && rm -rf /var/lib/apt/lists/*


