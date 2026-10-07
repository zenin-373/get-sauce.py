"""Download and inspect publicly accessible HTTP media resources."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import requests

from .models import Resource
from .parsers.hls import is_hls
from .parsers.mpeg_dash import is_dash
from .utils import filename_from_url, safe_filename

CHUNK_SIZE = 256 * 1024


def is_http_url(url: str) -> bool:
    return urlparse(url).scheme.lower() in {"http", "https"}


class Downloader:
    def __init__(self, output: Path, timeout: int, headers: dict[str, str], quiet: bool = False):
        self.output = output
        self.timeout = timeout
        self.headers = {"User-Agent": "get-sauce.py/0.2", **headers}
        self.quiet = quiet

    def inspect(self, url: str) -> Resource:
        if not is_http_url(url):
            raise ValueError("Only http:// and https:// URLs are supported.")
        with requests.get(url, headers=self.headers, stream=True, timeout=self.timeout, allow_redirects=True) as response:
            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "").lower()
            final_url = response.url
            kind = "hls" if is_hls(final_url, content_type) else "dash" if is_dash(final_url, content_type) else "file"
            length = response.headers.get("Content-Length")
            size = int(length) if length and length.isdigit() else None
            return Resource(source_url=url, final_url=final_url, content_type=content_type, size=size,
                            filename=filename_from_url(final_url) or "download.bin", kind=kind)

    def _ffmpeg(self, url: str, destination: Path) -> None:
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise RuntimeError("FFmpeg is required for HLS/DASH downloads. Add ffmpeg.exe to PATH.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            [ffmpeg, "-y", "-i", url, "-c", "copy", str(destination)],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )
        if result.returncode != 0:
            raise RuntimeError("FFmpeg failed to process the media stream.")

    def download(self, url: str, filename: str | None = None, truncate: bool = False) -> Path:
        info = self.inspect(url)
        name = safe_filename(filename or info.filename)
        if info.kind in {"hls", "dash"}:
            if filename is None or name.lower().endswith((".m3u8", ".mpd")):
                name = Path(name).stem + ".mp4"
            destination = self.output / name
            if not self.quiet:
                print(f"{info.kind.upper()}: {info.final_url}")
            self._ffmpeg(info.final_url, destination)
            return destination

        destination = self.output / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        existing = 0 if truncate or not destination.exists() else destination.stat().st_size
        headers = dict(self.headers)
        if existing:
            headers["Range"] = f"bytes={existing}-"

        with requests.get(info.final_url, headers=headers, stream=True, timeout=self.timeout) as response:
            if existing and response.status_code == 206:
                mode = "ab"
                partial = response.headers.get("Content-Length")
                total = existing + int(partial) if partial and partial.isdigit() else None
            else:
                response.raise_for_status()
                mode = "wb"
                existing = 0
                total = int(response.headers.get("Content-Length", "0") or 0) or info.size

            done = existing
            with open(destination, mode) as output:
                for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                    if not chunk:
                        continue
                    output.write(chunk)
                    done += len(chunk)
                    if not self.quiet:
                        if total:
                            print(f"\r{name}: {done * 100 / total:6.2f}%", end="", flush=True)
                        else:
                            print(f"\r{name}: {done / 1048576:.1f} MB", end="", flush=True)
        if not self.quiet:
            print()
        return destination
