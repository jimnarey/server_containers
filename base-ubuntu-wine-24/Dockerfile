FROM base-ubuntu-gui-24:latest

ENV DEBIAN_FRONTEND=noninteractive

RUN dpkg --add-architecture i386

RUN wget -O /etc/apt/keyrings/winehq-archive.key https://dl.winehq.org/wine-builds/winehq.key && \ 
    wget -NP /etc/apt/sources.list.d/ https://dl.winehq.org/wine-builds/ubuntu/dists/jammy/winehq-jammy.sources

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --install-recommends winehq-stable winetricks

RUN apt-get clean && \
    apt-get autoremove && \
    rm -rf /var/lib/apt/lists