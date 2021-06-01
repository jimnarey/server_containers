FROM base-ubuntu

RUN mkdir /download
WORKDIR /download
RUN wget https://buildbot.libretro.com/nightly/emscripten/RetroArch.7z --no-check-certificate && \
    7z x RetroArch.7z && \
    mv ./retroarch/* . && \
    rmdir retroarch
