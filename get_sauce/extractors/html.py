"""Extract directly referenced media from ordinary public HTML pages."""
from __future__ import annotations

from html.parser import HTMLParser
from urllib.parse import urljoin

from ..models import Resource
from .base import Extractor


class _MediaParser(HTMLParser):
    def __init__(self, base_url: str):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.urls: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = dict(attrs)
        candidates = []
        if tag in {"video", "audio", "source"}:
            candidates.append(data.get("src"))
        if tag == "meta" and data.get("property", "").lower() in {
            "og:video", "og:video:url", "og:video:secure_url"
        }:
            candidates.append(data.get("content"))
        for value in candidates:
            if not value:
                continue
            absolute = urljoin(self.base_url, value.strip())
            if absolute.startswith(("http://", "https://")):
                self.urls.append(absolute)


class HtmlMediaExtractor(Extractor):
    """Find public media URLs already exposed by HTML; no access-control bypassing."""

    def can_handle(self, url: str, content_type: str = "") -> bool:
        clean = url.lower().split("?", 1)[0]
        return "html" in content_type.lower() or clean.endswith((".html", ".htm", "/"))

    def extract(self, url: str, client) -> list[Resource]:
        response = client.get(url)
        response.raise_for_status()
        parser = _MediaParser(response.url)
        parser.feed(response.text)
        resources = []
        seen = set()
        for media_url in parser.urls:
            if media_url in seen:
                continue
            seen.add(media_url)
            name = media_url.rsplit("/", 1)[-1].split("?", 1)[0] or "download.bin"
            resources.append(Resource(source_url=url, final_url=media_url, filename=name, kind="file"))
        return resources
