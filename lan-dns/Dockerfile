FROM alpine:3.21

RUN apk add --no-cache dnsmasq

COPY dnsmasq.conf.template /etc/dnsmasq.conf.template
COPY entrypoint.sh /usr/local/bin/lan-dns
RUN chmod 0555 /usr/local/bin/lan-dns

# dnsmasq listens on an unprivileged container port. Docker maps the LAN's
# standard DNS port 53 to it, so this service needs no extra capabilities.
USER 65534:65534

ENTRYPOINT ["/usr/local/bin/lan-dns"]
