FROM base-ubuntu-gui:latest

RUN dpkg --add-architecture i386 && \
    apt-get update && \
    apt-get clean && \
    apt-get autoremove && \
    rm -rf /var/lib/apt/lists

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --install-recommends gnupg2 software-properties-common && \
    wget -qO- https://dl.winehq.org/wine-builds/winehq.key | apt-key add - && \
    apt-add-repository 'deb http://dl.winehq.org/wine-builds/ubuntu/ focal main' && \
    wget -qO- https://download.opensuse.org/repositories/Emulators:/Wine:/Debian/xUbuntu_20.04/Release.key | apt-key add - && \
    sh -c 'echo "deb https://download.opensuse.org/repositories/Emulators:/Wine:/Debian/xUbuntu_20.04/ ./" > /etc/apt/sources.list.d/obs.list' && \
    apt-get clean && \
    apt-get autoremove && \
    rm -rf /var/lib/apt/lists

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --install-recommends winehq-stable winetricks && \
    apt-get clean && \
    apt-get autoremove && \
    rm -rf /var/lib/apt/lists
