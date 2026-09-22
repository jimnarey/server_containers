# llama.cpp service profiles

`compose.ai.yml` provides the shared AI stack, the `llama-gpu-locks` volume,
and four runnable llama.cpp base services: `llama-cpp`, the two pinned
GenerelSchwerz builds, and `llama-cpp-csantiago78`. Each uses the former
`.env`-driven defaults, so it can be started directly. It also supplies the
shared Docker build context, source repository, pin, CUDA setting, image tag,
and default runtime configuration for profile overlays.

`tools/render-compose.py` reads exactly one profile env file and emits a deterministic
Compose file containing one fully materialised service. It loads the selected
source service from this repository's `compose.ai.yml`,
makes a copy, and replaces all profile-owned runtime settings on that copy.
The output contains neither `extends` nor Compose `!override` tags, so a
generated service with a distinct `SERVICE_NAME` does not inherit from or merge
with its source template.

## Launching a profile

For the usual one-profile operation, `tools/launch.py` resolves the literal
`SERVICE_NAME` declared in an env file under `config/`:

```sh
./llama-cpp/tools/launch.py llama-cpp-gpu-0
```

Stop just the selected generated service with `--down`; this deliberately does
not run project-wide `docker compose down`:

```sh
./llama-cpp/tools/launch.py --down llama-cpp-generel-schwerz-16gb-gpu-1
```

Use `--dry-run` to inspect the rendered Compose invocation without executing
Docker. The explicit command remains useful for advanced overrides:

```sh
docker compose -f compose.ai.yml \
  -f "$(./llama-cpp/tools/render-compose.py llama-cpp/config/llama-cpp-16gb/gpu-1.env)" \
  up -d --build llama-cpp-gpu-1
```

By default the renderer writes the YAML to a stable `/tmp/llama-compose-<sha>`
file and prints that path, which is what makes it usable directly after
Compose's `-f`. Diagnostics go to standard error. The renderer has no clock,
random, network, or host-state input, so the same profile and overrides always
produce byte-identical YAML. Inspect YAML before a launch with:

```sh
./llama-cpp/tools/render-compose.py --stdout llama-cpp/config/llama-cpp-16gb/gpu-1.env
```

Set `LLAMA_GPU_IDS` to replace a profile's GPU selection without modifying its
file. It accepts a comma-separated Docker/NVIDIA device-ID list; for example,
this starts the GPU-1 profile on GPU 0 instead:

```sh
LLAMA_GPU_IDS=0 docker compose -f compose.ai.yml \
  -f "$(./llama-cpp/tools/render-compose.py llama-cpp/config/llama-cpp-16gb/gpu-1.env)" \
  up -d --build llama-cpp-gpu-1
```

For less common overrides, set `LLAMA_RENDER_<KEY>` for any key in the profile
(for example `LLAMA_RENDER_PORT=11444`). These explicit names avoid accidental
interpolation from the repository-wide `.env` file. `LLAMA_GPU_IDS` takes
precedence over `LLAMA_RENDER_GPU_IDS`. A CPU profile must keep `GPU_IDS` empty.

Upstream GPU profiles use `gpus.device_ids` to expose only the selected
physical devices. The Schwerz and csantiago profiles retain their established
`gpus: all` plus profile-specific `CUDA_VISIBLE_DEVICES` behaviour. Every GPU
profile mounts the shared lock volume; the entrypoint takes a non-blocking
lifetime lock for each selected physical ID. A collision exits with status 75
and remains visible because GPU profiles use `restart: "no"`.

## Profiles

| Profile env file | Service | Build |
| --- | --- | --- |
| `config/llama-cpp-16gb/gpu-0.env` | `llama-cpp-gpu-0` | upstream CUDA, GPU 0 |
| `config/llama-cpp-16gb/gpu-1.env` | `llama-cpp-gpu-1` | upstream CUDA, GPU 1 |
| `config/llama-cpp-32gb/all-gpus.env` | `llama-cpp-all-gpus` | upstream CUDA, GPUs 0 and 1 |
| `config/llama-cpp-cpu/cpu.env` | `llama-cpp-cpu` | upstream CPU |
| `config/llama-cpp-generel-schwerz-16gb/gpu-0.env` | `llama-cpp-generel-schwerz-16gb-gpu-0` | Schwerz `e69a1d0` GPU 0 |
| `config/llama-cpp-generel-schwerz-16gb/gpu-1.env` | `llama-cpp-generel-schwerz-16gb-gpu-1` | Schwerz `e69a1d0` GPU 1 |
| `config/llama-cpp-generel-schwerz-32gb/all-gpus.env` | `llama-cpp-generel-schwerz-32gb-all-gpus` | Schwerz `0ed73d1`, GPUs 0 and 1 |
| `config/llama-cpp-csantiago78/all-gpus.env` | `llama-cpp-csantiago78-all-gpus` | csantiago78 `bccbacd`, GPUs 0 and 1 |

`SERVICE_NAME` must differ from `SOURCE_SERVICE`: the source is already a
service in `compose.ai.yml`, while the generated document adds a second
service. The fork profiles retain their previous source service names as
`NETWORK_ALIAS` values, so existing DeepSeek and Pi provider URLs continue to
work. Their source templates remain directly runnable with their former `.env`
defaults.

Every profile explicitly supplies its service name, source service, port,
bind address, GPU IDs, restart policy, and repository-relative model/config
sources. The renderer resolves those sources to absolute paths before writing
its `/tmp` overlay, so Compose never interprets them relative to that overlay.
The
source service supplies the reproducible build arguments and image, which are
copied into the generated service before profile values replace their matching
runtime settings. The Dockerfile still verifies the pinned immutable commit
directly. The CPU profile
uses `llama-cpp` while overriding CUDA and image, retaining its
original `unless-stopped` restart policy rather than needing a handwritten
Compose service.

All model presets and fork `config.ini` files are mounted read-only directly
from `llama-cpp/config/`. There is no runtime copy to synchronise. Edit the
tracked source, validate the rendered profile, and recreate the affected
service for a change to take effect. The renderer also mounts
`config/chat-templates/` read-only at `/opt/llama-cpp/chat-templates`.
Use a per-model `chat-template-file` only when the GGUF's embedded template
has a demonstrated compatibility fault. Vendor the publisher's template at a
specific upstream revision, record that revision in the preset comment, and
do not substitute a generic family template: tool-call syntax is model
specific.

`devstral-small-2-24b-instruct-2512.jinja` is Mistral's template from
`55c5b41e98c2dbd21b0c8afffc540dcfc9eb5128`. It corrects the embedded GGUF
template's rejection of valid assistant-tool-result-user sequences used by
agent clients. The override is applied to every declared 2512 Devstral quant
in the upstream 32GB and CPU presets; it intentionally does not cover the
older `Devstral-Small-2505` family.

See [chat-template-audit.md](chat-template-audit.md) for the evidence and
follow-up priority across the models evaluated for coding quality and review.

`llama-cpp-all-gpus` retains the `llama-cpp` network alias, preserving the
existing DeepSeek and Pi endpoint `http://llama-cpp:8080/v1` when that profile
is launched. The profile files use host ports 11436 through 11443; see the
comment at the top of `compose.ai.yml`.

The GGUF library defaults to `/mnt/data/models/gguf` and is mounted read-only
at `/models`. See [GenerelSchwerz build notes](generel-schwerz-README.md) for
the fork-specific runtime constraints.

## Long-context benchmark matrix

`tools/benchmark-long-context.py` reads the main resource-usage table in
`docs/performance-findings.md`, then tests every reproducible model/profile row
except the GenerelSchwerz 32GB service, Qwen3.8-Flash-Next on physical GPU 0,
and rows whose ordinary low-context `Decode` result is below 10 tok/s. The
upstream 32GB service is included.
It starts one generated service at a time, waits for both Docker health and the
router HTTP endpoint, tests every model available through that profile, then
stops and removes that generated service before moving to the next profile.
It does not build images.

Run it from `tmux` as follows:

```sh
./llama-cpp/tools/benchmark-long-context.py
```

The runner writes detailed command output, request timings, JSON result lines,
and its final failure summary to one timestamped
`llama-cpp/long-context-*.log` file. The terminal shows only timestamped
profile/test progress plus a concise final failure count and log path. A
supplied `--output PATH` selects the one log file explicitly.

The input target is one eighth of the model's configured context window,
clamped to approximately 4,096--8,192 tokens; the request records the
server's actual prompt-token count, so tokenizer differences remain visible.
Every request has a deterministic neutral context and a 128-token completion
cap. This gives a useful 4K point for 32K-context models and a common 8K point
for 64K-and-larger models without approaching capacity or making CPU and
expert-cache runs unnecessarily long.

The script removes profile services that it starts, including an already
running service with the same name. Do not run it while DeepSeek, Pi, or another
client needs one of those llama endpoints. Historical `standalone` table rows
without a current generated Compose profile are not substituted with a different
configuration; they appear in the final failure summary. Use `--dry-run` to
inspect the derived matrix without Docker, or repeat `--profile` to test only
named profile groups (for example `--profile upstream-gpu-1`).
