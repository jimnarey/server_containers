# HTTPS gateway

`https-gateway` is the dedicated Caddy HTTPS entry point for this host.  It
currently serves only a confirmation page; **no application is proxied through
it yet**.  Caddy uses an internal certificate authority (CA), appropriate for
the LAN-only `home.arpa` names used by this repository.

The service is deliberately attached only to the private `https-gateway`
network.  A future application must be added to that network and receive an
explicit Caddy route before Caddy can reach it.

## Configure and start

Choose a hostname below `home.arpa` and create a matching local-DNS record for
this host.  For example, point `gateway.ai.home.arpa` to the AI server's LAN
address.  Set the values in the host's ignored `.env` file:

```dotenv
HTTPS_GATEWAY_BIND_ADDRESS=192.168.50.136
HTTPS_GATEWAY_HOSTNAME=gateway.ai.home.arpa
```

`HTTPS_GATEWAY_BIND_ADDRESS` defaults to `127.0.0.1` when it is omitted.  This
is intentional: it prevents an incomplete configuration from exposing ports
80 and 443 to the LAN.  Do not forward either port on the internet router.

Start Caddy:

```sh
docker compose up -d https-gateway
docker compose logs -f https-gateway
```

Caddy redirects HTTP to HTTPS.  Once the certificate is trusted as described
below, open `https://gateway.ai.home.arpa/` (substitute your hostname).  The
page confirms that the gateway is running; it is not an application login
page.

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
- Future routes should use subdomains (for example,
  `deepseek.ai.home.arpa`) and their upstream service should opt into the
  `https-gateway` network. Do not expose an application through the gateway
  without adding suitable authentication in its Caddy route.
