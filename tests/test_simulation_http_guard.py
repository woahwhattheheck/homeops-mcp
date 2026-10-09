"""A single focused boundary contract for the fictional local demo."""
import unittest
from homeops_relay.simulation_http_guard import allow_local_request


class LocalBoundary(unittest.TestCase):
    def test_same_origin_and_intentional_cli(self):
        self.assertTrue(allow_local_request(["127.0.0.1:8765"], ["http://127.0.0.1:8765"], 8765,
                                            require_json=True, content_type="application/json; charset=utf-8"))
        self.assertTrue(allow_local_request(["localhost:8765"], [], 8765,
                                            require_json=True, content_type="application/json"))
        self.assertTrue(allow_local_request(["[::1]:8765"], ["http://[::1]:8765"], 8765,
                                            require_json=True, content_type="application/json"))
        self.assertTrue(allow_local_request(["localhost:8765"], [], 8765))

    def test_cross_site_or_opaque_origin_rejected(self):
        for origin in ["https://evil.example", "http://evil.example:8765", "null", "http://localhost:8765"]:
            self.assertFalse(allow_local_request(["127.0.0.1:8765"], [origin], 8765,
                                                 require_json=True, content_type="application/json"))
        self.assertFalse(allow_local_request(["localhost:8765"], ["http://localhost:8765", "http://localhost:8765"], 8765))

    def test_rebind_and_duplicate_hosts_rejected(self):
        for host in ["evil.example:8765", "127.0.0.1:8888", "127.0.0.2:8765", "localhost", "localhost:8765.evil.example"]:
            self.assertFalse(allow_local_request([host], [], 8765))
        self.assertFalse(allow_local_request(["localhost:8765", "localhost:8765"], [], 8765))
        self.assertFalse(allow_local_request([], [], 8765))

    def test_non_json_simple_browser_posts_rejected(self):
        for ct in ["text/plain", "application/x-www-form-urlencoded", "multipart/form-data", None, "application/jsonp"]:
            self.assertFalse(allow_local_request(["localhost:8765"], ["http://localhost:8765"], 8765,
                                                 require_json=True, content_type=ct))
        self.assertFalse(allow_local_request(["localhost:8765"], [], True))


if __name__ == "__main__":
    unittest.main()
