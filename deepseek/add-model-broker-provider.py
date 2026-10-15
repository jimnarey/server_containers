#!/usr/bin/env python3
"""Add the seed's model-broker provider to an existing DSH profile's cordis.patch.yml.

DSH 0.2 reads config/settings.yaml only when it creates a new home. An existing profile keeps
its providers in <DSH home>/.dsh/profiles/<profile>/cordis.patch.yml, so a provider added to the
seed does not reach it. This copies the seed's model-broker provider into that file, in place,
and with --default-to-broker also makes it the provider of the default model (the model ID is
kept). Stop DSH first, since it rewrites the file when settings are changed in its UI, and start
it afterwards. Keep a copy of the file: the script does not.

usage: add-model-broker-provider.py SEED_SETTINGS_YAML PROFILE_PATCH_YML [--default-to-broker]
"""
import re, sys
from pathlib import Path
import yaml

seed, patch = Path(sys.argv[1]), Path(sys.argv[2])
seed_lines = seed.read_text().splitlines()
start = next(i for i, l in enumerate(seed_lines) if l == "    model-broker:")
block = ["  " + l for l in seed_lines[start:]]            # the profile nests 2 spaces deeper
lines = patch.read_text().splitlines()
if any(l == "      model-broker:" for l in lines):
    sys.exit("model-broker is already in the profile; nothing to do")
at = next(i for i, l in enumerate(lines) if l == "- id: agent-default-model")
lines[at:at] = block
if "--default-to-broker" in sys.argv:
    lines = [("    provider: model-broker" if l == "    provider: llama-cpp" else l) for l in lines]
patch.write_text("\n".join(lines) + "\n")
doc = yaml.safe_load(patch.read_text())
providers = next(e for e in doc if e["id"] == "llm-pi-ai")["config"]["providers"]
print({name: len(p["models"]) for name, p in providers.items()})
print(next(e for e in doc if e["id"] == "agent-default-model")["config"])
