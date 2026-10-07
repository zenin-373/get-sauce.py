def is_dash(url, content_type=""):
    return "dash+xml" in content_type.lower() or ".mpd" in url.lower()
