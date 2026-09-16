# HTTPS gateway

`https-gateway` is the dedicated Caddy HTTPS entry point for this host. It
serves a confirmation page, DeepSeek Harness, and desktop-XFCE. Caddy uses an
internal certificate authority (CA), appropriate for the LAN-only `home.arpa`
names used by this repository.

The service is deliberately attached only to the private `https-gateway`
network. DeepSeek and desktop-XFCE are the only application services currently
added to that network and the only application services Caddy can reach. Caddy
also joins a separate ingress-only network so Docker can publish ports 80 and
443; no application joins that network.

## Configure and start

Choose a hostname below `home.arpa` and create a matching local-DNS record for
this host.  For example, point `gateway.ai.home.arpa` to the AI server's LAN
address.  Set the values in the host's ignored `.env` file:

```dotenv
HTTPS_GATEWAY_BIND_ADDRESS=192.168.50.136
HTTPS_GATEWAY_HOSTNAME=gateway.ai.home.arpa
DEEPSEEK_GATEWAY_HOSTNAME=deepseek.ai.home.arpa
DESKTOP_XFCE_GATEWAY_HOSTNAME=xfce.ai.home.arpa
```

Use [`lan-dns/README.md`](../lan-dns/README.md) to configure the included
resolver. It returns the gateway address for every `*.ai.home.arpa` name, so
new services do not need separate router DNS records. `deepseek.ai.home.arpa`
and `xfce.ai.home.arpa` are protected by their own in-container Caddy Basic
Auth, using `CADDY_USER` and the bcrypt `CADDY_HASH` already used by the
browser/VNC containers. The shared gateway provides only HTTPS and routing;
neither service is published on a host port.

`HTTPS_GATEWAY_BIND_ADDRESS` defaults to `127.0.0.1` when it is omitted.  This
is intentional: it prevents an incomplete configuration from exposing ports
80 and 443 to the LAN.  Do not forward either port on the internet router.

Start Caddy:

```sh
docker compose up -d lan-dns https-gateway deepseek desktop-xfce
docker compose logs -f lan-dns https-gateway deepseek desktop-xfce
```

Caddy redirects HTTP to HTTPS. Once the certificate is trusted as described
below, `https://gateway.ai.home.arpa/` confirms that the gateway is running.
Open `https://deepseek.ai.home.arpa/` for DeepSeek or
`https://xfce.ai.home.arpa/` for desktop-XFCE, and enter the relevant Caddy
Basic Auth credentials when prompted.

## Trust Caddy's local CA

An internal CA is not automatically trusted by other computers.  Install the
CA *root certificate* on each browser/client that will access this gateway.
Do not install a leaf certificate from a browser warning page.

After the gateway has started, extract Caddy's root certificate from the
container:

```sh
docker compose cp \
  https-gateway:/data/caddy/pki/authorities/local/root.crt \
  ./caddy-local-root.crt
```

Keep the resulting file private enough to avoid accidental replacement, but it
is the public CA certificate: the sensitive CA private key remains in the
named Docker volume and must never be copied or shared.

Install `caddy-local-root.crt` on each client:

### Debian/Ubuntu Linux

```sh
sudo install -m 0644 caddy-local-root.crt /usr/local/share/ca-certificates/caddy-local-root.crt
sudo update-ca-certificates
```

Restart the browser.  Firefox on Linux may use its own certificate store; if
so, import the file through Firefox's certificate settings, or enable its use
of the operating system trust store.

### Chrome/Chromium on Linux

Current Chrome and Chromium releases use an NSS shared certificate database in
addition to the system CA bundle. If Chrome still reports
`net::ERR_CERT_AUTHORITY_INVALID` after the Debian/Ubuntu installation above,
import the same root certificate into that database as the normal desktop user
(not with `sudo`). Close every Chrome window first, then run:

```sh
sudo apt install libnss3-tools

if [ -d "$HOME/.pki/nssdb" ]; then
  nss_db="$HOME/.pki/nssdb"
else
  nss_db="$HOME/.local/share/pki/nssdb"
fi

mkdir -p "$nss_db"
if [ ! -f "$nss_db/cert9.db" ]; then
  certutil -d "sql:$nss_db" -N --empty-password
fi

certutil -d "sql:$nss_db" -D -n "Caddy Local CA" 2>/dev/null || true
certutil -d "sql:$nss_db" -A \
  -n "Caddy Local CA" \
  -t "C,," \
  -i /usr/local/share/ca-certificates/caddy-local-root.crt
certutil -d "sql:$nss_db" -L -n "Caddy Local CA"
```

`C,,` trusts this root CA for TLS server certificates. Chrome/Chromium 146 and
newer normally use `~/.local/share/pki/nssdb`; an existing legacy
`~/.pki/nssdb` takes precedence, which is why the commands select it first.
Restart Chrome afterwards. The certificate file itself is all that is needed
on the client; the repository is not required there.

### macOS

```sh
sudo security add-trusted-cert -d -r trustRoot \
  -k /Library/Keychains/System.keychain caddy-local-root.crt
```

### Windows (Administrator PowerShell)

```powershell
certutil -addstore -f Root .\caddy-local-root.crt
```

Verify that the browser shows a normal trusted HTTPS connection before adding
any authenticated application route.

## Operational notes

- The `https-gateway-data` volume stores the local CA, certificate keys, and
  issued certificates. Do not delete it during ordinary upgrades or container
  recreation. Back it up as protected secret material.
- The gateway has no Caddy admin API and no connection to the default Compose
  network.
- Future routes should use subdomains and their upstream service should opt
  into the `https-gateway` network. Do not expose an application through the
  gateway without adding suitable authentication in its Caddy route.
