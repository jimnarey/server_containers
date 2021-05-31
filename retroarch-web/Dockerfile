FROM ubuntu-headless-base:latest

RUN apt-get update -y && \
    apt-get install -y --no-install-recommends nodejs npm && \
    apt-get clean && \
    apt-get autoremove && \
    rm -rf /var/lib/apt/lists

RUN npm install --global coffeescript

COPY --from=build-retroarch-emscripten /build /var/www

RUN chmod +x /var/www/indexer

WORKDIR /var/www/assets/frontend/bundle
RUN ../../../indexer > .index-xhr
WORKDIR /var/www/assets/cores
RUN ../../indexer > .index-xhr

COPY Caddyfile /etc/



