from .base import Extractor
from ..models import Resource
from ..utils import filename_from_url

class DirectExtractor(Extractor):
    def can_handle(self, url, content_type=""):
        return not url.lower().endswith(".html")

    def extract(self, url):
        return [Resource(url, url, filename=filename_from_url(url) or "download")]
