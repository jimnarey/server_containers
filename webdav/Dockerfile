FROM base-ubuntu-caddy-24:latest

RUN caddy add-package github.com/mholt/caddy-webdav

COPY Caddyfile /etc/

RUN mkdir /webdav && \
    chown -R runuser:runuser /webdav
