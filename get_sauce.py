#!/usr/bin/env python3
"""Windows-friendly authorized-content downloader."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
import shutil
import subprocess
import sys
import threading
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests

VERSION = "0.1.0"
DEFAULT_TIMEOUT = 30
DEFAULT_WORKERS = 1
CHUNK_SIZE = 1024 * 256
_PRINT_LOCK = threading.Lock()


@dataclass
class ResourceInfo:
    url: str
    final_url: str = ""
    content_type: str = ""
    content_length: int | None = None
    filename: str = ""
    is_hls: bool = False


def safe_filename(name: str, fallback: str = "download") -> str:
    name = unquote(name or "").strip()
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).rstrip(" .")
    return name[:240] or fallback


def filename_from_url(url: str) -> str:
    name = Path(unquote(urlparse(url).path)).name
    return safe_filename(name)


def parse_headers(values: list[str]) -> dict[str, str]:
    headers = {}
    for value in values:
        for line in value.splitlines():
            if ":" not in line:
                continue
            key, val = line.split(":", 1)
            key, val = key.strip(), val.strip()
            if key:
                headers[key] = val
    return headers


def format_bytes(n: int | None) -> str:
    if n is None:
        return "unknown"
    value = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.1f} {unit}"
        value /= 1024
    return str(n)


def print_progress(done: int, total: int | None, label: str) -> None:
    with _PRINT_LOCK:
        if total:
            pct = min(100.0, done * 100.0 / total)
            msg = f"\r{label}: {pct:6.2f}% ({format_bytes(done)}/{format_bytes(total)})"
        else:
            msg = f"\r{label}: {format_bytes(done)}"
        print(msg, end="", flush=True)


class Downloader:
    def __init__(self, output: Path, timeout: int, headers: dict[str, str],
                 truncate: bool = False, quiet: bool = False):
        self.output = output
        self.timeout = timeout
        self.headers = headers
        self.truncate = truncate
        self.quiet = quiet
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "get-sauce.py/0.1"})
        self.session.headers.update(headers)

    def inspect(self, url: str) -> ResourceInfo:
        response = self.session.get(
            url, stream=True, timeout=self.timeout, allow_redirects=True
        )
        response.raise_for_status()
        ctype = response.headers.get("Content-Type", "").lower()
        length = response.headers.get("Content-Length")
        info = ResourceInfo(
            url=url,
            final_url=response.url,
            content_type=ctype,
            content_length=int(length) if length and length.isdigit() else None,
            filename=filename_from_url(response.url) or "download",
            is_hls=("mpegurl" in ctype or ".m3u8" in response.url.lower()),
        )
        response.close()
        return info

    def download_hls(self, url: str, destination: Path) -> None:
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise RuntimeError("FFmpeg is required for HLS (.m3u8) downloads.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        command = [ffmpeg, "-y", "-i", url, "-c", "copy", str(destination)]
        result = subprocess.run(
            command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
        if result.returncode != 0:
            raise RuntimeError("FFmpeg failed to process the HLS stream.")

    def download(self, url: str, filename: str | None = None) -> Path:
        info = self.inspect(url)
        destination = self.output / safe_filename(filename or info.filename)
        destination.parent.mkdir(parents=True, exist_ok=True)

        if info.is_hls:
            if not self.quiet:
                print(f"HLS: {info.final_url}")
            self.download_hls(info.final_url, destination)
            return destination

        existing = 0 if self.truncate else (
            destination.stat().st_size if destination.exists() else 0
        )
        headers = dict(self.headers)
        if existing:
            headers["Range"] = f"bytes={existing}-"

        with self.session.get(
            info.final_url, stream=True, timeout=self.timeout, headers=headers
        ) as response:
            if existing and response.status_code != 206:
                existing = 0
                mode = "wb"
            else:
                response.raise_for_status()
                mode = "ab" if existing else "wb"

            total = info.content_length
            if total is not None and existing and response.status_code == 206:
                total += existing

            if not self.quiet:
                print(f"Downloading: {info.final_url}")

            done = existing
            with open(destination, mode) as output:
                for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                    if not chunk:
                        continue
                    output.write(chunk)
                    done += len(chunk)
                    if not self.quiet:
                        print_progress(done, total, destination.name)

        if not self.quiet:
            print()
        return destination


def read_urls(urls: list[str], file_path: str | None) -> list[str]:
    result = list(urls)
    if file_path:
        result.extend(
            line.strip()
            for line in Path(file_path).read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="get-sauce.py")
    parser.add_argument("urls", nargs="*", help="URL(s) to download")
    parser.add_argument("-F", "--file", dest="url_file")
    parser.add_argument("-i", "--info", action="store_true")
    parser.add_argument("-j", "--json", action="store_true")
    parser.add_argument("-O", "--output", default="downloads")
    parser.add_argument("-o", "--name")
    parser.add_argument("-w", "--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("-T", "--timeout", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument("-h", "--header", action="append", default=[],
                         help="HTTP header such as 'User-Agent: Mozilla/5.0'")
    parser.add_argument("-t", "--truncate", action="store_true")
    parser.add_argument("-q", "--quiet", action="store_true")
    parser.add_argument("-v", "--version", action="version",
                         version=f"%(prog)s {VERSION}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    urls = read_urls(args.urls, args.url_file)

    if not urls:
        print("No URLs supplied. Use --help for usage.", file=sys.stderr)
        return 2
    if args.workers < 1:
        print("--workers must be at least 1.", file=sys.stderr)
        return 2

    downloader = Downloader(
        Path(args.output),
        args.timeout,
        parse_headers(args.header),
        truncate=args.truncate,
        quiet=args.quiet,
    )

    if args.info or args.json:
        results = []
        for url in urls:
            try:
                data = asdict(downloader.inspect(url))
                results.append(data)
                if not args.json:
                    print(f"URL:          {data['url']}")
                    print(f"Final URL:    {data['final_url']}")
                    print(f"Type:         {data['content_type']}")
                    print(f"Size:         {format_bytes(data['content_length'])}")
                    print(f"Filename:     {data['filename']}")
                    print(f"HLS:          {data['is_hls']}")
                    print()
            except requests.RequestException as exc:
                print(f"ERROR: {url}: {exc}", file=sys.stderr)
        if args.json:
            print(json.dumps(results, indent=2))
        return 0

    def download_one(item: tuple[int, str]) -> str:
        index, url = item
        try:
            name = args.name if len(urls) == 1 else None
            path = downloader.download(url, name)
            return f"[{index}] OK: {path}"
        except Exception as exc:
            return f"[{index}] ERROR: {url}: {exc}"

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for result in pool.map(download_one, enumerate(urls, 1)):
            print(result)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
