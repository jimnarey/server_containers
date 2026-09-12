# GenerelSchwerz llama.cpp MoE-cache services

`llama-cpp-generel-schwerz-16gb` is the one-GPU profile and
`llama-cpp-generel-schwerz-32gb` is the two-GPU profile. They are separate
from the ordinary `llama-cpp` service and use the experimental CUDA MoE expert
cache in [GenerelSchwerz/llama.cpp](https://github.com/GenerelSchwerz/llama.cpp).

The image is built at the Dockerfile's pinned revision:

```text
branch: moe-cache
commit: b46f7f7a436f990932d3da3ec53380e2b9effc89
CUDA:   12.8.1, compiled for CUDA architecture 120
```

The build context is respectively:

```text
/mnt/work/generel-schwerz-llama-cpp/16gb/source
/mnt/work/generel-schwerz-llama-cpp/32gb/source
```

Docker copies the selected context into the build and detaches that copy at the
pinned commit. It never checks out or otherwise mutates either host source
tree. Both host checkouts must contain the pinned commit (the supplied
checkouts do). To use another fork revision, edit the `LLAMA_FORK_BRANCH` and
`LLAMA_FORK_COMMIT` arguments at the top of `Dockerfile`, then ensure that
commit exists in both local source checkouts.

## Runtime configuration

Create the separate runtime configurations before first start:

```sh
install -D -m 0644 generel-schwerz-llama-cpp/config/16gb.ini \
  /mnt/work/generel-schwerz-llama-cpp/16gb/config/config.ini
install -D -m 0644 generel-schwerz-llama-cpp/config/32gb.ini \
  /mnt/work/generel-schwerz-llama-cpp/32gb/config/config.ini
```

The config files are mounted at `/etc/llama.cpp/config.ini` and are deliberately
outside this repository. They configure all models selected through the router.
Both services mount the shared model library, `/mnt/data/models/gguf`, read-only
at `/models`. Keep a model GGUF (or its shards) at the root or in an immediate,
flat model directory below that root.

The 16GB service is exposed on port 11438 and limits CUDA visibility to physical
GPU 0. The 32GB service is on port 11439 and uses both GPUs with a layer split.
Run only one of these profiles at a time. In particular, stop ordinary
`llama-cpp` before the 32GB profile; it is otherwise also free to allocate both
cards.

The templates start at 64K context, Q8 KV, 8 physical CPU threads, and an MoE
expert cache of 32 or 64 slots. Expert-cache size is per cached expert tensor
on its CUDA device. Treat 64 slots as the first 32GB experiment, not a promise
that every model will fit; reduce it if either GPU runs out of memory.

## Build and run

```sh
docker compose build llama-cpp-generel-schwerz-16gb
docker compose up -d llama-cpp-generel-schwerz-16gb

# Stop the one-GPU profile before the two-GPU profile.
docker compose stop llama-cpp-generel-schwerz-16gb llama-cpp
docker compose build llama-cpp-generel-schwerz-32gb
docker compose up -d llama-cpp-generel-schwerz-32gb
```

Use `/v1/models` and the returned model ID to select a GGUF in a request:

```sh
curl http://192.168.50.136:11438/v1/models
curl http://192.168.50.136:11439/v1/models
```

For containers on this Compose network, the corresponding API bases are
`http://llama-cpp-generel-schwerz-16gb:8080/v1` and
`http://llama-cpp-generel-schwerz-32gb:8080/v1`.
