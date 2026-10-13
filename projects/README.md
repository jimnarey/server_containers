# Coding-agent project environments

`compose.ai.yml` owns template declarations for DeepSeek and Pi: their
common environment, web/search integration, and (for DeepSeek) HTTPS-gateway
registration. Each directory here creates concrete, project-named services
from those templates. They have independent persistent homes and workspaces,
and can run together in the one Compose project.

The aggregate `docker-compose.yml` selects `amiga` to preserve the historical
environment. Choose another environment explicitly from the repository root:

```sh
docker compose -f compose.bases.yml -f compose.ai.yml \
  --profile harness-build build agent-base
docker compose -f compose.bases.yml -f compose.ai.yml \
  --profile harness-build build agent-base-caddy
docker compose -f compose.bases.yml -f compose.ai.yml \
  --profile harness-build build deepseek-core pi-core
docker compose -f compose.bases.yml -f compose.ai.yml \
  -f projects/xbox360/compose.yml build deepseek-xbox360 pi-xbox360
docker compose -f compose.bases.yml -f compose.ai.yml \
  -f projects/xbox360/compose.yml up -d deepseek-xbox360 pi-xbox360
```

The overlay Dockerfiles inherit explicitly tagged local harness core images.
The helper services are behind the `harness-build` profile, so they are build
targets but never part of a normal `up` invocation. The initial build follows
the parent-to-child commands above; subsequent project builds reuse the tags.

## Running projects together

To run both project environments, use the aggregate stack (which supplies the
gateway) and add the Xbox overlay:

```sh
docker compose -f docker-compose.yml -f projects/xbox360/compose.yml \
  up -d https-gateway deepseek-amiga pi-amiga deepseek-xbox360 pi-xbox360
```

The gateway discovers both DeepSeek services through their `caddy` labels and
publishes `https://deepseek-amiga.ai.home.arpa` and
`https://deepseek-xbox360.ai.home.arpa`. The hostnames are explicit because
DeepSeek Harness must trust its exact browser origin. Override them, together
with their matching container environment value, through
`DEEPSEEK_AMIGA_GATEWAY_HOSTNAME` or `DEEPSEEK_XBOX360_GATEWAY_HOSTNAME`.

The aggregate `docker-compose.yml` includes the Amiga services by default.
Existing deployments migrating from the former `deepseek` and `pi` service
names should use `docker compose up -d --remove-orphans deepseek-amiga pi-amiga`
once to replace the legacy containers while retaining their original Amiga
home and workspace paths.
