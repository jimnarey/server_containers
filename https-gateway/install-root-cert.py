#!/usr/bin/env python3
"""Download a Caddy root and trust it in Linux and Chrome/Chromium NSS."""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import ssl
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path


def normalized_fingerprint(value: str) -> str:
    fingerprint = value.replace(":", "").replace(" ", "").upper()
    if len(fingerprint) != 64 or any(character not in "0123456789ABCDEF" for character in fingerprint):
        raise argparse.ArgumentTypeError("SHA-256 fingerprint must be 64 hexadecimal characters")
    return fingerprint


def download_certificate(url: str) -> tuple[bytes, str]:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "http" or not parsed.netloc:
        raise SystemExit("The endpoint must be an http:// URL.")
    request = urllib.request.Request(url, headers={"Accept": "application/x-x509-ca-cert"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            if response.status != 200:
                raise SystemExit(f"Server returned HTTP {response.status}.")
            certificate = response.read()
    except OSError as error:
        raise SystemExit(f"Could not download certificate: {error}") from error

    try:
        der = ssl.PEM_cert_to_DER_cert(certificate.decode("ascii"))
    except (UnicodeDecodeError, ValueError) as error:
        raise SystemExit(f"Downloaded content is not a PEM certificate: {error}") from error
    return certificate, hashlib.sha256(der).hexdigest().upper()


def run(command: list[str]) -> None:
    print("+", " ".join(command))
    subprocess.run(command, check=True)


def install_system_certificate(certificate_path: Path, fingerprint: str) -> Path:
    destination = Path("/usr/local/share/ca-certificates") / f"caddy-gateway-{fingerprint.lower()}.crt"
    run(["sudo", "install", "-m", "0644", str(certificate_path), str(destination)])
    run(["sudo", "update-ca-certificates"])
    return destination


def nss_databases() -> list[Path]:
    home = Path.home()
    candidates = [home / ".pki" / "nssdb", home / ".local" / "share" / "pki" / "nssdb"]
    # Install into both locations: older Chrome may select the legacy database,
    # while recent Chrome normally selects the XDG location.
    return candidates


def install_nss_certificate(certificate_path: Path, fingerprint: str) -> None:
    certutil = shutil.which("certutil")
    if certutil is None:
        raise SystemExit("certutil is required for Chrome/Chromium. Install libnss3-tools and rerun.")

    nickname = f"Caddy Gateway Root {fingerprint[:16]}"
    for database in nss_databases():
        database.mkdir(parents=True, exist_ok=True)
        database_spec = f"sql:{database}"
        if not (database / "cert9.db").exists():
            run([certutil, "-d", database_spec, "-N", "--empty-password"])
        # Only this fingerprint-derived nickname is replaced; unrelated roots remain intact.
        subprocess.run([certutil, "-d", database_spec, "-D", "-n", nickname], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        run([certutil, "-d", database_spec, "-A", "-n", nickname, "-t", "C,,", "-i", str(certificate_path)])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("endpoint", help="URL of the temporary /root.crt endpoint")
    parser.add_argument("--sha256", type=normalized_fingerprint, help="expected certificate SHA-256 fingerprint")
    parser.add_argument("--yes", action="store_true", help="install without an interactive confirmation")
    arguments = parser.parse_args()

    certificate, fingerprint = download_certificate(arguments.endpoint)
    print(f"Downloaded root SHA-256 fingerprint: {fingerprint}")
    if arguments.sha256 and arguments.sha256 != fingerprint:
        raise SystemExit("Fingerprint mismatch; refusing to install the downloaded certificate.")
    if not arguments.sha256 and not arguments.yes:
        response = input("Verify this fingerprint out of band, then type 'install' to continue: ")
        if response != "install":
            raise SystemExit("Not installed.")
    if arguments.yes and not arguments.sha256:
        print("Warning: installing an unauthenticated HTTP download because --yes was supplied.", file=sys.stderr)

    temporary_file = tempfile.NamedTemporaryFile(prefix="caddy-root-", suffix=".crt", delete=False)
    try:
        temporary_file.write(certificate)
        temporary_file.close()
        certificate_path = Path(temporary_file.name)
        destination = install_system_certificate(certificate_path, fingerprint)
        install_nss_certificate(certificate_path, fingerprint)
    finally:
        temporary_file.close()
        Path(temporary_file.name).unlink(missing_ok=True)

    print(f"Installed system certificate: {destination}")
    print("Installed Chrome/Chromium NSS trust entries. Fully restart Chrome to reload them.")


if __name__ == "__main__":
    main()
