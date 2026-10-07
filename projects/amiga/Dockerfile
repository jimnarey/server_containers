ARG HARNESS_IMAGE=deepseek-harness:core
FROM ${HARNESS_IMAGE}

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# The existing Amiga reverse-engineering environment. Keep these packages out
# of the harness core: they are requirements of this project, not of DSH/Pi.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libasound2t64 \
        libatk-bridge2.0-0t64 \
        libatk1.0-0t64 \
        libcups2t64 \
        libdbus-1-3 \
        libegl1 \
        libfontconfig1 \
        libglib2.0-0t64 \
        libgtk-3-0t64 \
        libnss3 \
        libopengl0 \
        libxcomposite1 \
        libxdamage1 \
        libxfixes3 \
        libxkbcommon-x11-0 \
        libxkbcommon0 \
        libxtst6 \
        libxcb-cursor0 \
        libxcb-icccm4 \
        libxcb-image0 \
        libxcb-keysyms1 \
        libxcb-render-util0 \
        libxcb-shape0 \
        libxcb-xinerama0 \
        libxcb-xinput0 \
        libxcb-xkb1 \
        python-is-python3 \
        python3 \
        python3-capstone \
        python3.12-dev \
        xauth \
        xvfb && \
    apt-get clean && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*
