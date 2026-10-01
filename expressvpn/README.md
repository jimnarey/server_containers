# ExpressVPN proxy

`expressvpn` is an HTTP proxy whose outbound traffic goes through ExpressVPN.
Point an application, another LAN machine or another container at it, and
only that traffic leaves through the VPN. Nothing else on the host changes.

It runs [gluetun](https://github.com/qdm12/gluetun), which connects to
ExpressVPN over OpenVPN. It has no image to build. gluetun's firewall allows
outbound traffic only through the tunnel, so if the VPN drops, proxied requests
fail rather than leak. DNS lookups for proxied requests are made inside the
tunnel (DNS over TLS), so they don't leak either.

It replaces an earlier image that ran the official ExpressVPN Linux client.
That needed a privileged container, `expect`-driven activation and
`network_mode` sharing.

## Configure

Get the OpenVPN credentials from the ExpressVPN account page: **Set up other
devices → Manual configuration → OpenVPN**. They are a generated username and
password, not the activation code. Then set them in `.env`:

```dotenv
EXPRESSVPN_OPENVPN_USER=...
EXPRESSVPN_OPENVPN_PASSWORD=...
EXPRESSVPN_COUNTRY=UK
# Optional, narrows the country to one city, e.g. "New York" for USA.
EXPRESSVPN_CITY=
# The host's LAN address; the loopback default only serves this machine.
EXPRESSVPN_PROXY_BIND_ADDRESS=192.168.50.136
EXPRESSVPN_PROXY_PORT=8888
```

`EXPRESSVPN_COUNTRY` uses gluetun's names for ExpressVPN locations, such as
`UK`, `USA`, `Netherlands`, `Germany` or `Japan`. It also accepts a
comma-separated list. For the full list, including cities:

```sh
docker run --rm -v "$PWD:/out" qmcgaw/gluetun:v3.41.3 \
  format-servers -expressvpn -output /out/expressvpn-servers.md
```

Anyone on the LAN can use the proxy once it is published on a LAN address.
To require a password, set `EXPRESSVPN_PROXY_USER` and
`EXPRESSVPN_PROXY_PASSWORD`; clients then use
`http://user:password@host:8888`.

## Start

The service is in the `vpn` profile, so a plain `docker compose up -d` skips
it on hosts without credentials. Start it by name:

```sh
docker compose -f compose.network.yml up -d expressvpn
docker logs -f expressvpn-c   # wait for "Public IP address is ... (<country>)"
```

After changing the country, run the same `up -d` command again to recreate
the container.

Check from another machine:

```sh
curl -x http://192.168.50.136:8888 https://ipinfo.io
```

## Use from LAN machines

Set the HTTP proxy to `<host>:8888`. Most applications use the same proxy for
HTTPS:

- **Browsers:** in Firefox, Settings → Network Settings → Manual proxy, with
  "Also use this proxy for HTTPS". Chromium-based browsers use the system
  proxy, or `--proxy-server=http://host:8888`.
- **Command-line tools:** `export http_proxy=http://host:8888 https_proxy=http://host:8888`.
  curl, wget, pip, git and apt honour these.

This is an HTTP proxy, not SOCKS. It carries HTTP and HTTPS, which covers
browsers and most applications, but not arbitrary TCP or UDP. BitTorrent is an
example that won't work through it; see Transmission below.

## Use from other services in this repo

Attach the service only to the `expressvpn-proxy` network and set the proxy
environment variables:

```yaml
  some-service:
    environment:
      HTTP_PROXY: http://expressvpn:8888
      HTTPS_PROXY: http://expressvpn:8888
      http_proxy: http://expressvpn:8888
      https_proxy: http://expressvpn:8888
      NO_PROXY: localhost,127.0.0.1
      no_proxy: localhost,127.0.0.1
    networks:
      - expressvpn-proxy
    depends_on:
      expressvpn:
        condition: service_healthy
```

`expressvpn-proxy` is an internal network with no route to the internet, so
the service cannot bypass the VPN. Requests that ignore the proxy fail. To
let a service reach other containers or the LAN directly as well, also attach
it to the relevant network; traffic that skips the proxy will then bypass the
VPN.

The service must run in the same Compose project as `expressvpn`, which is
the case when using `docker-compose.yml` or when `compose.network.yml` is
included with `-f`. A service defined in another `compose.*.yml` file must
also declare the network under its file's top-level `networks:` key, as
`compose.desktop.yml` does for `https-gateway`:

```yaml
networks:
  expressvpn-proxy:
    internal: true
```

## Transmission

BitTorrent can't use an HTTP proxy, so `transmission-vpn.yml` runs Transmission
inside its own gluetun container's network instead (`network_mode`). It reads
the same `EXPRESSVPN_*` settings and publishes the web UI on port 9092.
Docker cannot reattach a container to a recreated network namespace, so
restart Transmission whenever its gateway container is recreated. The
`depends_on: restart: true` setting does this when both are managed through
Compose.
