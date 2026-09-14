#!/usr/bin/env python3
"""Synchronise repository-owned DeepSeek Harness configuration.

The source tree is copied recursively, so adding a normal configuration file
under ``deepseek/config`` does not require changing this script. Credentials,
sessions, and other Harness state are never read, written, or deleted.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path


DEFAULT_DEEPSEEK_HOME = Path("/mnt/work/deepseek")
CONFIG_SOURCE_ROOT = Path(__file__).resolve().parent / "config"
HARNESS_CONFIG_DIRECTORY = ".dsh"


def target_root(deepseek_home: Path) -> Path:
    return deepseek_home / HARNESS_CONFIG_DIRECTORY


def report(action: str, path: Path) -> None:
    print(f"{action:7} {path}")


def copy_file(source: Path, destination: Path, *, dry_run: bool) -> None:
    if dry_run:
        report("would copy", destination)
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    report("copied", destination)


def source_files() -> list[Path]:
    return sorted(path for path in CONFIG_SOURCE_ROOT.rglob("*") if path.is_file())


def copy_source_tree(destination_root: Path, *, dry_run: bool) -> None:
    for source in source_files():
        copy_file(source, destination_root / source.relative_to(CONFIG_SOURCE_ROOT), dry_run=dry_run)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--deepseek-home",
        type=Path,
        default=Path(os.environ.get("DEEPSEEK_HOME", DEFAULT_DEEPSEEK_HOME)),
        help="Persisted DeepSeek home directory (default: DEEPSEEK_HOME or %(default)s)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Report changes without writing them")
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    if not CONFIG_SOURCE_ROOT.is_dir():
        raise FileNotFoundError(f"Configuration source directory is missing: {CONFIG_SOURCE_ROOT}")

    destination = target_root(arguments.deepseek_home)
    copy_source_tree(destination, dry_run=arguments.dry_run)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except FileNotFoundError as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
