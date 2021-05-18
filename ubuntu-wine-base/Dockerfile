FROM ubuntu-gui-base-auth:latest


RUN dpkg --add-architecture i386 && \
    apt-get update

RUN apt-get install -y --install-recommends gnupg2 software-properties-common && \
    wget -qO- https://dl.winehq.org/wine-builds/winehq.key | apt-key add - && \
    apt-add-repository 'deb http://dl.winehq.org/wine-builds/ubuntu/ focal main' && \
    wget -qO- https://download.opensuse.org/repositories/Emulators:/Wine:/Debian/xUbuntu_20.04/Release.key | apt-key add - && \
    sh -c 'echo "deb https://download.opensuse.org/repositories/Emulators:/Wine:/Debian/xUbuntu_20.04/ ./" > /etc/apt/sources.list.d/obs.list'

RUN apt-get update && \
    apt-get install -y --install-recommends winehq-stable && \
    rm -rf /var/lib/apt/lists

RUN wine --version


# RUN dpkg --add-architecture i386 && \
#     apt-get update && \
#     apt-get install -y --no-install-recommends wine32 wine32-preloader && \
#     rm -rf /var/lib/apt/lists


