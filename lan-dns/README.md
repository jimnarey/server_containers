# LAN DNS

`lan-dns` is a small dnsmasq resolver for the home-server namespace. It maps
`ai.home.arpa` and every name below it to the HTTPS gateway address, while
forwarding all other DNS queries to the configured upstream resolver.

## Configure the router and service

Give the AI server a fixed LAN address, then set the following values in the
ignored `.env` file:

```dotenv
LAN_DNS_BIND_ADDRESS=192.168.50.136
LAN_DNS_GATEWAY_ADDRESS=192.168.50.136
LAN_DNS_UPSTREAM_SERVER=192.168.50.1
```

`LAN_DNS_BIND_ADDRESS` is where Docker publishes TCP and UDP port 53.
`LAN_DNS_GATEWAY_ADDRESS` is the address returned for all `ai.home.arpa`
names. `LAN_DNS_UPSTREAM_SERVER` is normally the router, which resolves names
outside this local domain.

In the router's **LAN / DHCP Server** settings, set **DNS Server 1** to the AI
server's fixed IP (`192.168.50.136` in this example). This distributes the
resolver to all DHCP clients. The DNS field on the AI server's individual
static-IP reservation affects only that one client and is not sufficient.

Start the resolver:

```sh
docker compose up -d lan-dns
```

Renew the DHCP lease or reconnect clients after changing the router setting.
Verify from a client:

```sh
nslookup deepseek.ai.home.arpa 192.168.50.136
nslookup xfce.ai.home.arpa 192.168.50.136
```

Both should return `LAN_DNS_GATEWAY_ADDRESS`. The same wildcard-style domain
mapping covers future gateway routes without adding a DNS record per service.

## Availability

Clients using this resolver cannot resolve ordinary names while the AI server
is down. Run the same resolver configuration on a second always-on machine if
DNS availability during AI-server maintenance matters.
