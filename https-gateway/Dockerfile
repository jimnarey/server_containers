# caddy-docker-proxy is intentionally a shell-less image. Keep its pinned Caddy
# binary/plugin, but place it in a tiny Alpine wrapper so the gateway can retain
# the existing behaviour of deriving the local CA name from the host hostname.
FROM lucaslorentz/caddy-docker-proxy:2.13.1 AS caddy-docker-proxy

FROM alpine:3.21.3

COPY --from=caddy-docker-proxy /bin/caddy /usr/bin/caddy

# Match the upstream image's Caddy storage locations so the mounted volumes
# retain the existing local CA and all issued certificates across the wrapper.
ENV XDG_DATA_HOME=/data \
    XDG_CONFIG_HOME=/config

ENTRYPOINT ["/bin/sh", "-ec", "export HOSTNAME=\"$(cat /run/host-hostname)\"; exec /usr/bin/caddy docker-proxy"]
