import requests

class HttpClient:
    def __init__(self, timeout=30, headers=None):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "get-sauce.py/0.2"})
        if headers:
            self.session.headers.update(headers)

    def get(self, url, **kwargs):
        kwargs.setdefault("timeout", self.timeout)
        kwargs.setdefault("allow_redirects", True)
        return self.session.get(url, **kwargs)

    def inspect(self, url):
        with self.get(url, stream=True) as r:
            r.raise_for_status()
            return r.url, r.headers.copy()
