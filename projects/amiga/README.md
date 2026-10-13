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
  -f projects/amiga/compose.yml build deepseek-amiga pi-amiga
docker compose -f compose.bases.yml -f compose.ai.yml \
  -f projects/amiga/compose.yml up -d deepseek-amiga pi-amiga
```

DeepSeek is available through the automatically registered gateway route at
`https://deepseek-amiga.ai.home.arpa`. Its default DSH home and workspace
remain `/mnt/work/deepseek` and `/mnt/work/projects`, preserving the existing
Amiga Harness state. Set `DEEPSEEK_AMIGA_HOME`,
`DEEPSEEK_AMIGA_WORKSPACE`, `PI_AMIGA_HOME`, or `PI_AMIGA_WORKSPACE` only when
an alternative location is wanted.
