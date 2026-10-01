#!/bin/sh
# gluetun connects to the IP addresses recorded in its built-in server list,
# which go stale as ExpressVPN renumbers servers, and its updater aborts on
# retired hostnames. Resolve the chosen server's current address here, before
# gluetun's firewall blocks DNS, and pass it as gluetun's endpoint override.
set -eu

hostname="${SERVER_HOSTNAMES:?set EXPRESSVPN_SERVER_HOSTNAME in .env}"

# DNS may not be ready yet at host boot (lan-dns can run on this same host).
attempt=0
until addresses="$(getent ahostsv4 "$hostname" | awk '{ print $1 }' | sort -u)" \
    && [ -n "$addresses" ]; do
  attempt=$((attempt + 1))
  if [ "$attempt" -ge 30 ]; then
    echo "resolve-endpoint: cannot resolve $hostname" >&2
    exit 1
  fi
  sleep 2
done

# ExpressVPN returns several addresses per server; spread connections over them.
VPN_ENDPOINT_IP="$(echo "$addresses" | shuf -n 1)"
export VPN_ENDPOINT_IP
echo "resolve-endpoint: $hostname -> $VPN_ENDPOINT_IP"

exec /gluetun-entrypoint "$@"
