# Amiga agent environment

This Compose overlay preserves the former DeepSeek/Pi developer environment:
Python 3.12 development headers, Debian's Capstone bindings, PySide/X11
runtime libraries, and a headless X server (`Xvfb`). These are intentionally
project dependencies rather than part of either coding-agent harness.

From the repository root, select it with:

```sh
docker compose -f compose.bases.yml -f compose.ai.yml \
  --profile harness-build build agent-base
docker compose -f compose.bases.yml -f compose.ai.yml \
  --profile harness-build build agent-base-caddy
docker compose -f compose.bases.yml -f compose.ai.yml \
  --profile harness-build build deepseek-core pi-core
docker compose -f compose.bases.yml -f compose.ai.yml \
  -f projects/amiga/compose.yml build deepseek pi
docker compose -f compose.bases.yml -f compose.ai.yml \
  -f projects/amiga/compose.yml up -d deepseek pi
```
