# SearXNG

A self-hosted metasearch engine, run from the official `searxng/searxng` image with no local image customisation, alongside a small `valkey` cache/rate-limiting backend (also the official image). This mirrors the `ollama` / `llama-cpp` pattern of declaring an upstream image directly in `docker-compose.yml` rather than building one.

`searxng/settings.yml` is mounted read-only over the image's default config and merges onto it (`use_default_settings: true`). It currently only:

- enables the JSON result format alongside the default `html` format, so the instance can later be queried as a search API
- points the `valkey` setting at the `searxng-valkey` service

DeepSeek Harness uses this service as its built-in `web_search` provider via the
Compose-internal URL `http://searxng:8080/`. Its separate `web_fetch` provider
retrieves result URLs directly; SearXNG is search only.

## Configuration

Required and optional settings in `.env`:

```dotenv
SEARXNG_TAG=latest
SEARXNG_BIND_ADDRESS=192.168.50.136
SEARXNG_PORT=9036
SEARXNG_SECRET=
```

`SEARXNG_SECRET` is required and overrides the placeholder `secret_key` in `settings.yml` at container start. Generate one with:

```bash
openssl rand -hex 32
```

`SEARXNG_BIND_ADDRESS` and `SEARXNG_PORT` control only the published host port; the container always listens on `8080` internally.

## Start the service

```bash
docker compose up -d searxng
docker compose logs -f searxng
```

Open `http://<SEARXNG_BIND_ADDRESS>:<SEARXNG_PORT>/` in a browser, or query the JSON API directly, e.g.:

```bash
curl "http://192.168.50.136:9036/search?q=test&format=json"
```

Like `ollama` and `llama-cpp`, this is published on the LAN without Caddy/basic auth in front of it; treat it as a trusted-network service per the top-level [README](../README.md#http-and-network-security).
