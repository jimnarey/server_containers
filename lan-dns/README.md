# LAN DNS

`lan-dns` is a small dnsmasq resolver for the home-server namespaces. It
forwards ordinary DNS queries to the router and maps every service name below
each server domain to that server's HTTPS gateway:

```text
*.ai.home.arpa       -> 192.168.50.136  (AI gateway)
*.nas.home.arpa      -> 192.168.50.214  (NAS gateway and planned DNS host)
*.hardware.home.arpa -> 192.168.50.146  (shed-inspiron gateway)
```

For example, `deepseek.ai.home.arpa` reaches the AI gateway and
`xfce.nas.home.arpa` reaches the NAS gateway. DNS chooses the server; that
server's Caddy gateway chooses the individual service. No per-service DNS
records are necessary.

## Configure the resolver

Give all three hosts fixed LAN addresses. The intended permanent deployment is
on `nas-mini`; set the following values in that host's ignored `.env` file:

```dotenv
LAN_DNS_BIND_ADDRESS=192.168.50.214
LAN_DNS_AI_GATEWAY_ADDRESS=192.168.50.136
LAN_DNS_NAS_GATEWAY_ADDRESS=192.168.50.214
LAN_DNS_HARDWARE_GATEWAY_ADDRESS=192.168.50.146
LAN_DNS_UPSTREAM_SERVER=192.168.50.1
```

`LAN_DNS_BIND_ADDRESS` is only the address on which Docker publishes TCP and
UDP port 53; change it when moving the resolver between hosts. The three
`*_GATEWAY_ADDRESS` values are the destinations returned for their respective
wildcard namespace and remain the same regardless of the resolver's host.

Start it on the NAS with the network Compose file:

```sh
docker compose -f compose.network.yml up -d lan-dns
```

Then set the router's **LAN / DHCP Server → DNS Server 1** to
`192.168.50.214`. Renew DHCP leases or reconnect clients afterwards. Do this
only once the NAS resolver is running, otherwise clients will lose name
resolution.

Verify from a LAN client:

```sh
nslookup deepseek.ai.home.arpa 192.168.50.214
nslookup xfce.nas.home.arpa 192.168.50.214
nslookup any-service.hardware.home.arpa 192.168.50.214
```

They should return `192.168.50.136`, `192.168.50.214`, and
`192.168.50.146`, respectively.

## Availability

One shared resolver is a DNS dependency for the LAN. If its NAS host is down,
clients configured to use it cannot resolve ordinary names either. For higher
availability, run a second resolver with the same three zone rules and publish
both addresses through DHCP.
