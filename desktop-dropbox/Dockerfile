FROM base-ubuntu-xfce-24:latest

WORKDIR /home/runuser

RUN wget https://www.dropbox.com/download?dl=packages/ubuntu/dropbox_2026.05.06_amd64.deb -O dropbox_2026.05.06_amd64.deb

RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libglapi-mesa \
    libxext-dev \
    libxdamage-dev \
    libxcb-glx0-dev \
    libxcb-dri2-0-dev \
    libxcb-dri3-dev \
    libxcb-present-dev \
    libxshmfence-dev \
    libxxf86vm-dev \
    libqt5x11extras5 \
    gir1.2-gtk-3.0 \
    python3-gi \
    libgtk-3-0 \
    nautilus \
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
    zstd

RUN apt-get install -y ./dropbox_2026.05.06_amd64.deb

RUN apt-get clean \
    && apt-get autoremove \
    && rm -rf /var/lib/apt/lists/*
