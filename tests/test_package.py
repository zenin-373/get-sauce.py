import unittest
from get_sauce.models import Resource
from get_sauce.parsers.hls import is_hls
from get_sauce.parsers.mpeg_dash import is_dash
from get_sauce.extractors.direct import DirectExtractor

class PackageTests(unittest.TestCase):
    def test_resource(self):
        self.assertEqual(Resource("a","b").kind, "file")
    def test_hls(self):
        self.assertTrue(is_hls("https://example.test/video.m3u8"))
    def test_dash(self):
        self.assertTrue(is_dash("https://example.test/video.mpd"))
    def test_direct(self):
        self.assertTrue(DirectExtractor().can_handle("https://example.test/a.mp4"))

if __name__ == "__main__":
    unittest.main()
