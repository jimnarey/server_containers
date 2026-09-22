#!/usr/bin/env python3
"""Temporarily publish one Caddy root certificate over HTTP.

The certificate is public, but HTTP does not authenticate it. Give clients the
SHA-256 fingerprint printed at startup through a separate trusted channel.
"""

from __future__ import annotations

import argparse
import hashlib
import http.server
import ipaddress
import shlex
import socket
import ssl
import threading
from pathlib import Path


DEFAULT_INSTALLER_URL = (
    "https://raw.githubusercontent.com/jimnarey/server_containers/master/"
    "https-gateway/install-root-cert.py"
)


class RootCertificateHandler(http.server.BaseHTTPRequestHandler):
    certificate: bytes
    single_use: bool

    def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        if self.path != "/root.crt":
            self.send_error(404, "Only /root.crt is available")
            return

        self.send_response(200)
        self.send_header("Content-Type", "application/x-x509-ca-cert")
        self.send_header("Content-Length", str(len(self.certificate)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(self.certificate)

        if self.single_use:
            threading.Thread(target=self.server.shutdown, daemon=True).start()

    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.client_address[0]} - {format % args}")


def read_certificate(path: Path) -> tuple[bytes, str]:
    certificate = path.read_bytes()
    try:
        der = ssl.PEM_cert_to_DER_cert(certificate.decode("ascii"))
    except (UnicodeDecodeError, ValueError) as error:
        raise SystemExit(f"{path} is not a PEM-encoded certificate: {error}") from error
    return certificate, hashlib.sha256(der).hexdigest().upper()


def lan_address() -> str:
    """Return this host's routed 192.168/16 IPv4 address without external tools."""
    candidates: list[str] = []
    # UDP connect selects the address used for the LAN route without sending data.
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as connection:
            connection.connect(("192.168.0.1", 9))
            candidates.append(connection.getsockname()[0])
    except OSError:
        pass

    try:
        candidates.extend(address[4][0] for address in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET))
    except socket.gaierror:
        pass

    for candidate in candidates:
        if ipaddress.ip_address(candidate) in ipaddress.ip_network("192.168.0.0/16"):
            return candidate
    raise SystemExit("Could not detect a 192.168.*.* LAN address; pass --address explicitly.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("certificate", type=Path, help="path to Caddy root.crt")
    parser.add_argument(
        "--address",
        help="192.168.*.* address to bind and advertise (autodetected when omitted)",
    )
    parser.add_argument("--port", type=int, default=8080, help="TCP port to listen on")
    parser.add_argument(
        "--installer-url",
        default=DEFAULT_INSTALLER_URL,
        help="raw GitHub URL of install-root-cert.py",
    )
    parser.add_argument(
        "--keep-serving",
        action="store_true",
        help="serve more than one successful /root.crt request",
    )
    arguments = parser.parse_args()
    address = arguments.address or lan_address()
    try:
        if ipaddress.ip_address(address) not in ipaddress.ip_network("192.168.0.0/16"):
            parser.error("--address must be a 192.168.*.* IPv4 address")
    except ValueError:
        parser.error("--address must be a valid IPv4 address")

    certificate, fingerprint = read_certificate(arguments.certificate)
    RootCertificateHandler.certificate = certificate
    RootCertificateHandler.single_use = not arguments.keep_serving

    server = http.server.ThreadingHTTPServer((address, arguments.port), RootCertificateHandler)
    endpoint = f"http://{address}:{arguments.port}/root.crt"
    print(f"Serving {endpoint}")
    print(f"SHA-256 fingerprint: {fingerprint}")
    print("Run this on the Linux client (Bash or Zsh):")
    print(
        "set -o pipefail; "
        f"curl -fsSL {shlex.quote(arguments.installer_url)} | "
        f"python3 - {shlex.quote(endpoint)} --sha256 {fingerprint}"
    )
    print("The server stops after one successful download; use --keep-serving to override.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
