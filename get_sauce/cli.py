"""Command-line interface for get-sauce.py."""
from __future__ import annotations

import argparse
import concurrent.futures
import json
from pathlib import Path

from . import __version__
from .downloader import Downloader
from .utils import format_bytes


def parse_headers(values: list[str]) -> dict[str, str]:
    result = {}
    for value in values:
        for line in value.splitlines():
            if ":" in line:
                key, val = line.split(":", 1)
                if key.strip():
                    result[key.strip()] = val.strip()
    return result


def read_urls(args) -> list[str]:
    urls = list(args.urls)
    if args.file:
        urls.extend(
            line.strip()
            for line in Path(args.file).read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )
    return urls


def inspect_one(url: str, args):
    return Downloader(Path(args.output), args.timeout, parse_headers(args.header), quiet=True).inspect(url)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="get-sauce",
        description="Download publicly accessible HTTP media and HLS/DASH streams.",
    )
    parser.add_argument("urls", nargs="*", help="URL(s) to inspect or download")
    parser.add_argument("-F", "--file", help="Read one URL per line from a text file")
    parser.add_argument("-i", "--info", action="store_true", help="Inspect URLs without downloading")
    parser.add_argument("-j", "--json", action="store_true", help="Print inspection data as JSON")
    parser.add_argument("-O", "--output", default="downloads", help="Output directory")
    parser.add_argument("-o", "--name", help="Output filename when one URL is supplied")
    parser.add_argument("-w", "--workers", type=int, default=1, help="Concurrent downloads")
    parser.add_argument("-T", "--timeout", type=int, default=30, help="HTTP timeout in seconds")
    parser.add_argument("-H", "--header", action="append", default=[], help="HTTP header, e.g. User-Agent: Mozilla/5.0")
    parser.add_argument("-t", "--truncate", action="store_true", help="Do not resume an existing file")
    parser.add_argument("-q", "--quiet", action="store_true", help="Suppress progress output")
    parser.add_argument("-v", "--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    urls = read_urls(args)
    if not urls:
        print("No URLs supplied. Use --help for usage.")
        return 2
    if args.workers < 1:
        print("--workers must be at least 1.")
        return 2
    if args.timeout < 1:
        print("--timeout must be at least 1.")
        return 2

    if args.info or args.json:
        results = []
        for url in urls:
            try:
                r = inspect_one(url, args)
                results.append({
                    "url": r.source_url,
                    "final_url": r.final_url,
                    "content_type": r.content_type,
                    "size": r.size,
                    "filename": r.filename,
                    "kind": r.kind,
                })
            except Exception as exc:
                results.append({"url": url, "error": str(exc)})
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for item in results:
                if "error" in item:
                    print(f"ERROR: {item['url']}: {item['error']}")
                else:
                    print(f"URL:       {item['url']}")
                    print(f"Final URL: {item['final_url']}")
                    print(f"Type:      {item['content_type']}")
                    print(f"Size:      {format_bytes(item['size'])}")
                    print(f"Filename:  {item['filename']}")
                    print(f"Kind:      {item['kind']}")
                    print()
        return 0 if all("error" not in x for x in results) else 1

    def download_one(item: tuple[int, str]) -> str:
        index, url = item
        try:
            downloader = Downloader(
                Path(args.output), args.timeout, parse_headers(args.header), quiet=args.quiet
            )
            name = args.name if len(urls) == 1 else None
            path = downloader.download(url, filename=name, truncate=args.truncate)
            return f"[{index}] OK: {path}"
        except Exception as exc:
            return f"[{index}] ERROR: {url}: {exc}"

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for result in pool.map(download_one, enumerate(urls, 1)):
            print(result)
    return 0
