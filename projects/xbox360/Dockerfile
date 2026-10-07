ARG HARNESS_IMAGE=deepseek-harness:core
FROM ${HARNESS_IMAGE}

ARG XENIA_CANARY_RELEASE=cc4981a
ARG XENIA_CANARY_LINUX_SHA256=82914b57c0f673e39e7e43ffe4a0222088520f35e2a05b20ad43a586f811455c
ARG XENIA_CANARY_WINDOWS_SHA256=46d531e3cdc5ab0144509a780005f4736df62264150c49e52bcd2545ef6bf2fc

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Xenia's Windows executable is x86-64. Install the 64-bit Ubuntu Wine runtime
# only; do not enable i386 globally unless a separate project tool actually
# needs to execute 32-bit Windows code.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        binutils-powerpc-linux-gnu \
        binutils-powerpc64-linux-gnu \
        bsdiff \
        cabextract \
        cmake \
        file \
        g++-powerpc-linux-gnu \
        g++-powerpc64-linux-gnu \
        gcc-powerpc-linux-gnu \
        gcc-powerpc64-linux-gnu \
        imagemagick \
        libvulkan1 \
        mesa-vulkan-drivers \
        ninja-build \
        patch \
        vulkan-tools \
        wine64 \
        winbind \
        x11-apps \
        x11-utils \
        xauth \
        xdelta3 \
        xvfb \
        xxd && \
    apt-get clean && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

# Pin both upstream artifacts and verify their release-provided SHA-256 values
# rather than downloading mutable `latest` links during every image build.
RUN install -d /opt/xenia-canary/linux /opt/xenia-canary/windows /tmp/xenia && \
    curl --fail --location --retry 3 \
        --output /tmp/xenia/xenia_canary_linux.AppImage \
        "https://github.com/xenia-canary/xenia-canary/releases/download/${XENIA_CANARY_RELEASE}/xenia_canary_linux.AppImage" && \
    echo "${XENIA_CANARY_LINUX_SHA256}  /tmp/xenia/xenia_canary_linux.AppImage" | sha256sum --check --strict && \
    install -m 0755 /tmp/xenia/xenia_canary_linux.AppImage /opt/xenia-canary/linux/xenia_canary_linux.AppImage && \
    curl --fail --location --retry 3 \
        --output /tmp/xenia/xenia_canary_windows.7z \
        "https://github.com/xenia-canary/xenia-canary/releases/download/${XENIA_CANARY_RELEASE}/xenia_canary_windows.7z" && \
    echo "${XENIA_CANARY_WINDOWS_SHA256}  /tmp/xenia/xenia_canary_windows.7z" | sha256sum --check --strict && \
    7z x -y -o/opt/xenia-canary/windows /tmp/xenia/xenia_canary_windows.7z && \
    rm -rf /tmp/xenia

COPY projects/xbox360/bin/ /usr/local/bin/
RUN chmod 0755 /usr/local/bin/xenia-canary-native \
    /usr/local/bin/xenia-canary-wine \
    /usr/local/bin/capture-xvfb
