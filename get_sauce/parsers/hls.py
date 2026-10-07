def is_hls(url, content_type=""):
    return "mpegurl" in content_type.lower() or ".m3u8" in url.lower()
