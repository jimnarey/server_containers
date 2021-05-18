FROM ubuntu-wine-base:latest

RUN mkdir -p /usr/share/wine/mono && \
    wget -P /usr/share/wine/mono https://dl.winehq.org/wine/wine-mono/6.1.1/wine-mono-6.1.1-x86.tar.xz

WORKDIR /usr/share/wine/mono

RUN tar -xJf wine-mono-6.1.1-x86.tar.xz && \
    rm -f wine-mono-6.1.1-x86.tar.xz


