import tempfile
import unittest
from pathlib import Path

from get_sauce import format_bytes, safe_filename, parse_headers, read_urls


class CoreTests(unittest.TestCase):
    def test_safe_filename(self):
        self.assertEqual(safe_filename('a<>:"/\\|?*.mp4'), "a_________.mp4")

    def test_format_bytes(self):
        self.assertEqual(format_bytes(1024), "1.0 KB")

    def test_headers(self):
        self.assertEqual(parse_headers(["User-Agent: Test", "Accept: */*"]), {
            "User-Agent": "Test", "Accept": "*/*"
        })

    def test_read_urls(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "urls.txt"
            p.write_text("# comment\nhttps://example.com/a\n\nhttps://example.com/b\n")
            self.assertEqual(read_urls([], str(p)), [
                "https://example.com/a", "https://example.com/b"
            ])


if __name__ == "__main__":
    unittest.main()
