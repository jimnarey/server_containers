# Guarded Fetch Gateway

`guarded-fetch` is a small, private HTTP gateway for a coding-agent extension
or other Compose service that needs to retrieve public web pages. It is based on
[Vercel's `guarded-fetch`](https://github.com/vercel-labs/guarded-fetch), which
checks every URL and redirect, rejects private/link-local/loopback targets,
pins the DNS result used for the connection, sanitises request headers, and
bounds the request chain. This service adds a deliberately narrow API around
that library.

The image is pinned to `guarded-fetch` 0.1.4 by default. Change
`GUARDED_FETCH_VERSION` deliberately when updating it, then rebuild the image.

It is not published to the host. Other services on this Compose project can
use `http://guarded-fetch:8080`; no service is configured to use it by default.
In particular, Pi will need a small extension that calls this API before it has
a `web_fetch` tool.

## Build and start

The base image must exist first, as with the other services based on it:

```sh
docker compose build base-ubuntu-24 guarded-fetch
docker compose up -d guarded-fetch
```

Check it without exposing a host port:

```sh
docker compose exec guarded-fetch \
  node -e "fetch('http://127.0.0.1:8080/healthz').then(async r => { console.log(await r.text()); process.exit(r.ok ? 0 : 1) })"
```

## API

Only `POST /v1/fetch` is available. It accepts exactly a JSON object with a
`url` string; it does not accept caller-controlled headers, cookies, methods,
or request bodies.

```sh
curl --fail --silent --show-error \
  --request POST http://guarded-fetch:8080/v1/fetch \
  --header 'content-type: application/json' \
  --data '{"url":"https://example.com/"}'
```

The response is JSON containing the final `url`, HTTP `status`, `contentType`,
text `body`, and a `truncated` flag. It permits only HTTPS and textual response
types. By default it limits the upstream response to 1 MiB, returns at most
100,000 characters to the caller, follows at most five redirects, and gives the
full fetch-and-body-read chain 15 seconds. Non-2xx upstream responses are
returned with their bounded textual body so an agent can handle ordinary web
errors; unsafe or failed destinations receive a generic gateway error.

Set these optional Compose environment values to make limits smaller or to
restrict destinations:

```dotenv
GUARDED_FETCH_TIMEOUT_MS=15000
GUARDED_FETCH_MAX_REDIRECTS=5
GUARDED_FETCH_MAX_RESPONSE_BYTES=1048576
GUARDED_FETCH_MAX_BODY_CHARS=100000
GUARDED_FETCH_ALLOWED_HOSTS=docs.example.com,api.example.com
```

An empty `GUARDED_FETCH_ALLOWED_HOSTS` permits public HTTPS hosts. An allowlist
narrows that set; it does not bypass the library's private-address checks.

## Security boundary

This is a safer fetch path, not yet a complete network egress boundary. Pi and
the existing agent containers remain on the ordinary Compose network and still
have their normal shell/network capabilities, so they can bypass this gateway
until they are moved to an internal-only network and all required egress is
routed through a dedicated proxy. Treat fetched pages as untrusted input: a
gateway can prevent SSRF-style destinations and resource abuse, but cannot make
web-page instructions trustworthy.
