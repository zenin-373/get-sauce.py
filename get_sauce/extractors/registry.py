"""Extractor registry for safe, generic public-media extraction."""
from .direct import DirectExtractor
from .html import HtmlMediaExtractor

EXTRACTORS = (DirectExtractor(), HtmlMediaExtractor())


def find_extractor(url: str, content_type: str = ""):
    for extractor in EXTRACTORS:
        if extractor.can_handle(url, content_type):
            return extractor
    return None
