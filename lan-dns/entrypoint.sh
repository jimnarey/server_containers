#!/bin/sh
set -eu

require_ip_literal() {
    value=$1
    name=$2
    case "$value" in
        ''|*[!0-9A-Fa-f:.]*)
            echo "$name must be an IPv4 or IPv6 literal" >&2
            exit 64
            ;;
    esac
}

: "${LAN_DNS_GATEWAY_ADDRESS:?LAN_DNS_GATEWAY_ADDRESS is required}"
: "${LAN_DNS_UPSTREAM_SERVER:?LAN_DNS_UPSTREAM_SERVER is required}"
require_ip_literal "$LAN_DNS_GATEWAY_ADDRESS" LAN_DNS_GATEWAY_ADDRESS
require_ip_literal "$LAN_DNS_UPSTREAM_SERVER" LAN_DNS_UPSTREAM_SERVER

sed \
    -e "s|@LAN_DNS_GATEWAY_ADDRESS@|${LAN_DNS_GATEWAY_ADDRESS}|g" \
    -e "s|@LAN_DNS_UPSTREAM_SERVER@|${LAN_DNS_UPSTREAM_SERVER}|g" \
    /etc/dnsmasq.conf.template > /tmp/dnsmasq.conf

exec dnsmasq --keep-in-foreground --conf-file=/tmp/dnsmasq.conf
