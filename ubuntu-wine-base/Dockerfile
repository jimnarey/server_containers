FROM ubuntu-gui-base:latest


RUN dpkg --add-architecture i386 && \
    apt-get update

RUN apt-get update && \
    apt-get install -y --install-recommends gnupg2 software-properties-common && \
    wget -qO- https://dl.winehq.org/wine-builds/winehq.key | apt-key add - && \
    apt-add-repository 'deb http://dl.winehq.org/wine-builds/ubuntu/ focal main' && \
    wget -qO- https://download.opensuse.org/repositories/Emulators:/Wine:/Debian/xUbuntu_20.04/Release.key | apt-key add - && \
    sh -c 'echo "deb https://download.opensuse.org/repositories/Emulators:/Wine:/Debian/xUbuntu_20.04/ ./" > /etc/apt/sources.list.d/obs.list'

RUN apt-get update && \
    apt-get install -y --install-recommends winehq-stable && \
    rm -rf /var/lib/apt/lists

RUN mkdir -p /usr/share/wine/mono && \
    wget -P /usr/share/wine/mono https://dl.winehq.org/wine/wine-mono/6.1.1/wine-mono-6.1.1-x86.tar.xz

WORKDIR /usr/share/wine/mono
RUN tar -xJf wine-mono-6.1.1-x86.tar.xz && \
    rm -f wine-mono-6.1.1-x86.tar.xz && \   
    ls -la && \
    wine --version && \
    chown -R root:root /usr/share/wine/mono



