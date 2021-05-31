FROM ubuntu:20.04

ENV TZ=Europe/London
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt-get update -y && \
    apt-get install -y --no-install-recommends wget p7zip-full && \
    apt-get clean && \
    apt-get autoremove && \
    rm -rf /var/lib/apt/lists

RUN mkdir /build
WORKDIR /build
RUN wget https://buildbot.libretro.com/nightly/emscripten/RetroArch.7z --no-check-certificate && \
    7z x RetroArch.7z && \
    mv ./retroarch/* . && \
    rmdir retroarch