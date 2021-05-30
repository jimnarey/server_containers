FROM ubuntu-headless-base:latest

WORKDIR /var/www
RUN wget https://buildbot.libretro.com/nightly/emscripten/RetroArch.7z && \
    7z x RetroArch.7z && \
    mv ./retroarch/* . && \
    rmdir retroarch

RUN chmod +x /var/www/indexer

RUN apt-get update -y && \
    apt-get install -y --no-install-recommends nodejs npm && \
    apt-get clean && \
    apt-get autoremove && \
    rm -rf /var/lib/apt/lists

RUN npm install --global coffeescript

WORKDIR /var/www/assets/frontend/bundle
RUN ../../../indexer > .index-xhr
WORKDIR /var/www/assets/cores
RUN ../../indexer > .index-xhr

COPY Caddyfile /etc/

