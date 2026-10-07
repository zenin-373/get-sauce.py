import re
from pathlib import Path
from urllib.parse import unquote, urlparse

def safe_filename(value, fallback="download"):
    value = unquote(value or "").strip()
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value).rstrip(" .")
    return value[:240] or fallback

def filename_from_url(url):
    return safe_filename(Path(unquote(urlparse(url).path)).name)

def format_bytes(n):
    if n is None:
        return "unknown"
    value=float(n)
    for unit in ("B","KB","MB","GB","TB"):
        if value < 1024 or unit=="TB":
            return f"{value:.1f} {unit}"
        value/=1024
