FROM ubuntu-gui-base-auth:latest

RUN dpkg --add-architecture i386 && \
    apt-get update && \
    apt-get install -y --no-install-recommends wine32 wine32-preloader && \
    rm -rf /var/lib/apt/lists

RUN apt-get update -y && \
    apt-get install -y --no-install-recommends playonlinux && \
    rm -rf /var/lib/apt/lists

