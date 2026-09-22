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

The Compose host environment must also provide `HOSTNAME`, normally supplied
by the operating system. The gateway passes that machine hostname into Caddy
and derives its local CA name from it. For example, a host named `ai` creates
the `Caddy ai Local Authority` CA. This makes roots from different gateway
machines distinguishable in Chrome/NSS even though they are all Caddy internal
CAs. Do not set `HOSTNAME` to a Docker container ID or an ephemeral value.

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

### Temporary client download

For a short, one-client transfer from the gateway host, first extract the root
as below, then run the standard-library HTTP exporter:

```sh
python3 serve-root-cert.py ./caddy-ai-local-root.crt \
  --port 8080
```

It exposes only `GET /root.crt`, prints the SHA-256 fingerprint, and exits
after one successful download. It also prints a one-line Bash/Zsh command that
downloads `install-root-cert.py` from this repository's GitHub `master` branch
and invokes it with the detected gateway endpoint and exact fingerprint. The
server detects its routed `192.168.*.*` address and uses it both for listening
and in that command. Pass `--address 192.168.x.y` to override detection. Send
that command, or at least the fingerprint, to the client through a trusted
channel. Use `--installer-url` when testing an unpublished branch or another
repository fork.

The installer updates the Debian/Ubuntu system trust bundle and both legacy
and current Chrome/Chromium NSS database locations. It creates or replaces
only a fingerprint-derived NSS nickname, leaving unrelated certificates in
place. Fully restart Chrome after it completes. If `certutil` is absent,
install `libnss3-tools` first.

The root CA certificate is public, but HTTP does not authenticate its content.
Always provide `--sha256` from a trusted channel; without it, the installer
requires an interactive confirmation of the displayed fingerprint.

After the gateway has started, extract Caddy's root certificate from the
container:

```sh
docker compose cp \
  https-gateway:/data/caddy/pki/authorities/local/root.crt \
  ./caddy-HOST-local-root.crt
```

The CA keypair is persisted in the gateway's Docker volume. Therefore, after
changing the CA name, perform an explicit, controlled CA rotation on the
gateway host so Caddy creates a root and leaf/intermediate chain with the new
name. Extract and install that new root after the rotation; keep the prior
root trusted until every client has been migrated. Do not delete the gateway
CA data volume until the replacement root has been distributed.

Keep the resulting file private enough to avoid accidental replacement, but it
is the public CA certificate: the sensitive CA private key remains in the
named Docker volume and must never be copied or shared.

Replace `HOST` with the gateway host, for example `ai` or `nas`. Install every
gateway's distinct root certificate on each client that uses it. Do not replace
one gateway's file with another under the same filename.

### Debian/Ubuntu Linux

```sh
ca_file=caddy-nas-local-root.crt
sudo install -m 0644 "$ca_file" \
  "/usr/local/share/ca-certificates/$(basename "$ca_file")"
sudo update-ca-certificates --fresh
```

Restart the browser.  Firefox on Linux may use its own certificate store; if
so, import the file through Firefox's certificate settings, or enable its use
of the operating system trust store.

### Chrome/Chromium on Linux

Current Chrome and Chromium releases use an NSS shared certificate database in
addition to the system CA bundle. If Chrome still reports
`net::ERR_CERT_AUTHORITY_INVALID` after the Debian/Ubuntu installation above,
import the same root certificate into that database as the normal desktop user
(not with `sudo`). Close every Chrome window first, then define and use this
helper. It accepts any `.crt` file and an optional unique name; use a different
name for each gateway CA.

```sh
sudo apt install libnss3-tools

trust_chrome_ca() {
  ca_file=${1:?usage: trust_chrome_ca /path/to/root.crt [certificate-name]}
  ca_name=${2:-"$(basename "${ca_file%.crt}")"}
  if [ -d "$HOME/.pki/nssdb" ]; then
    nss_db="$HOME/.pki/nssdb"
  else
    nss_db="$HOME/.local/share/pki/nssdb"
  fi
  mkdir -p "$nss_db"
  if [ ! -f "$nss_db/cert9.db" ]; then
    certutil -d "sql:$nss_db" -N --empty-password
  fi
  certutil -d "sql:$nss_db" -D -n "$ca_name" 2>/dev/null || true
  certutil -d "sql:$nss_db" -A -n "$ca_name" -t "C,," -i "$ca_file"
  certutil -d "sql:$nss_db" -L -n "$ca_name"
}

trust_chrome_ca /usr/local/share/ca-certificates/caddy-nas-local-root.crt \
  "Caddy NAS Local CA"
```

`C,,` trusts this root CA for TLS server certificates. Chrome/Chromium 146 and
newer normally use `~/.local/share/pki/nssdb`; an existing legacy
`~/.pki/nssdb` takes precedence, which is why the commands select it first.
Restart Chrome afterwards. The certificate file itself is all that is needed
on the client; the repository is not required there.

### macOS

```sh
sudo security add-trusted-cert -d -r trustRoot \
  -k /Library/Keychains/System.keychain caddy-nas-local-root.crt
```

### Windows (Administrator PowerShell)

```powershell
certutil -addstore -f Root .\caddy-nas-local-root.crt
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
