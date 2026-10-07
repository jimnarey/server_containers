# Coding-agent project environments

`compose.ai.yml` owns the stable DeepSeek and Pi service declarations: their
persistent homes, workspaces, web/search integration, and DeepSeek gateway.
Each directory here is an overlay that changes only the image built for those
same services. Starting an overlay never creates a second `deepseek` or `pi`
container.

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
  -f projects/xbox360/compose.yml build deepseek pi
docker compose -f compose.bases.yml -f compose.ai.yml \
  -f projects/xbox360/compose.yml up -d deepseek pi
```

The overlay Dockerfiles inherit explicitly tagged local harness core images.
The helper services are behind the `harness-build` profile, so they are build
targets but never part of a normal `up` invocation. The initial build follows
the parent-to-child commands above; subsequent project builds reuse the tags.
