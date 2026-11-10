#!/usr/bin/env python3
"""Install an official EasyEDA Linux package or unpack an official archive.

Accepted: .deb, .zip, .tar.gz, .tgz. Redirects are revalidated against the
official host allowlist. Never use this downloader with an untrusted URL.
"""
import os
import subprocess
import sys
import tarfile
import tempfile
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

ALLOWED = ("easyeda.com", "lceda.cn")


def allowed_host(host: str) -> bool:
    host = (host or "").lower().split(":")[0]
    return any(host == domain or host.endswith("." + domain) for domain in ALLOWED)


def safe_extract_zip(archive: str, dest: Path) -> None:
    base = dest.resolve()
    with zipfile.ZipFile(archive) as zf:
        for item in zf.infolist():
            target = (dest / item.filename).resolve()
            if target != base and base not in target.parents:
                raise RuntimeError("Unsafe path in ZIP archive")
        zf.extractall(dest)


def safe_extract_tar(archive: str, dest: Path) -> None:
    base = dest.resolve()
    with tarfile.open(archive, "r:gz") as tf:
        members = tf.getmembers()
        for item in members:
            target = (dest / item.name).resolve()
            if target != base and base not in target.parents:
                raise RuntimeError("Unsafe path in TAR archive")
            if item.issym() or item.islnk() or item.isdev():
                raise RuntimeError("Links and device nodes are not accepted in installer archive")
        tf.extractall(dest, members=members)


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: install_easyeda.py HTTPS_URL DEST_DIR")
    url, dest = sys.argv[1], Path(sys.argv[2])
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or not allowed_host(parsed.hostname or ""):
        raise SystemExit("Installer URL must be HTTPS on an official EasyEDA domain")

    dest.mkdir(parents=True, exist_ok=True)
    suffix = parsed.path.lower()
    fd, tmp = tempfile.mkstemp()
    os.close(fd)
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "EasyEDA-Pro-HF-Workbench"})
        with urllib.request.urlopen(request, timeout=180) as response, open(tmp, "wb") as out:
            final = urllib.parse.urlparse(response.geturl())
            if final.scheme != "https" or not allowed_host(final.hostname or ""):
                raise RuntimeError("Installer redirect left the official HTTPS domain allowlist")
            total = 0
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > 2_000_000_000:
                    raise RuntimeError("Installer exceeds 2 GB safety limit")
                out.write(chunk)

        if suffix.endswith(".zip"):
            safe_extract_zip(tmp, dest)
        elif suffix.endswith(".tar.gz") or suffix.endswith(".tgz"):
            safe_extract_tar(tmp, dest)
        elif suffix.endswith(".deb"):
            subprocess.run(["dpkg", "-i", tmp], check=False)
            subprocess.run(["apt-get", "update"], check=True)
            subprocess.run(["apt-get", "install", "-f", "-y"], check=True)
        else:
            raise RuntimeError("Unsupported package format. Expected .deb, .zip, .tar.gz or .tgz.")

        print(f"EasyEDA installer processed. Search for executable under {dest} and PATH.")
    finally:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass


if __name__ == "__main__":
    main()
