FROM ubuntu-headless-base:latest

WORKDIR /var/www
RUN wget https://buildbot.libretro.com/nightly/emscripten/RetroArch.7z && \
    7z x RetroArch.7z && \
    mv ./retroarch/* . && \
    rmdir retroarch

COPY Caddyfile /etc/