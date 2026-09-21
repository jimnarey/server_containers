#!/usr/bin/env python3
"""Print a GPU's effective PCIe link capability as ``pcie-genN-xM``.

The argument is the NVIDIA GPU index used by ``nvidia-smi`` and the Compose
``device_ids`` setting. For example, ``gpu-pcie-link.py 1`` may print
``pcie-gen4-x8``. ``N`` is the maximum generation supported by the active
GPU-to-host path; ``M`` is the currently negotiated lane width. Link speed can
drop while idle, but lane width normally remains fixed, so this captures
motherboard lane sharing such as an M.2 slot reducing a GPU from x8 to x4.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys


LINK_INFO_RE = re.compile(
    r"GPU Link Info\s*"
    r"PCIe Generation\s*Max\s*:\s*(?P<generation>\d+)\s*"
    r"Current\s*:.*?"
    r"Link Width\s*Max\s*:\s*\d+x\s*Current\s*:\s*(?P<width>\d+)x",
    re.DOTALL,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("gpu_index", type=int, help="NVIDIA GPU index from nvidia-smi")
    args = parser.parse_args()
    if args.gpu_index < 0:
        parser.error("gpu_index must be non-negative")
    return args


def main() -> int:
    args = parse_args()
    try:
        result = subprocess.run(
            ["nvidia-smi", "-q", "-i", str(args.gpu_index)],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError:
        print("error: nvidia-smi was not found", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as error:
        detail = error.stderr.strip() or error.stdout.strip()
        print(f"error: nvidia-smi could not inspect GPU {args.gpu_index}: {detail}", file=sys.stderr)
        return 1

    match = LINK_INFO_RE.search(result.stdout)
    if match is None:
        print(
            f"error: could not parse PCIe link information for GPU {args.gpu_index}",
            file=sys.stderr,
        )
        return 1

    print(f"pcie-gen{match['generation']}-x{match['width']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
