"""
Unit tests for the endpoint URL checks.

@testCovers plugins/inference-endpoints/src/pte_plugin_inference_endpoints/url_policy.py
"""

import ipaddress
import unittest
from unittest.mock import patch

from pte_plugin_inference_endpoints.url_policy import ALLOWED_HOSTS_ENV_VAR, EndpointURLError, check_url, normalize_base_url


def _resolving_to(*addresses: str):
    return patch(
        "pte_plugin_inference_endpoints.url_policy._resolve",
        return_value=[ipaddress.ip_address(a) for a in addresses],
    )


class TestNormalizeBaseUrl(unittest.TestCase):
    def test_strips_trailing_slash(self):
        self.assertEqual(normalize_base_url(" http://localhost:11434/v1/ "), "http://localhost:11434/v1")

    def test_rejects_other_schemes(self):
        for url in ("ftp://host/v1", "file:///etc/passwd", "localhost:11434"):
            with self.subTest(url=url), self.assertRaises(EndpointURLError):
                normalize_base_url(url)

    def test_rejects_credentials_query_and_fragment(self):
        for url in ("http://user:pw@host/v1", "http://host/v1?x=1", "http://host/v1#a"):
            with self.subTest(url=url), self.assertRaises(EndpointURLError):
                normalize_base_url(url)

    def test_rejects_invalid_port(self):
        with self.assertRaises(EndpointURLError):
            normalize_base_url("http://host:99999/v1")


class TestCheckUrl(unittest.TestCase):
    def setUp(self):
        patcher = patch.dict("os.environ", {ALLOWED_HOSTS_ENV_VAR: ""})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_allows_loopback_and_private_addresses(self):
        for address in ("127.0.0.1", "::1", "10.1.2.3", "192.168.0.5", "100.101.102.103"):
            with self.subTest(address=address), _resolving_to(address):
                check_url("http://ollama:11434/v1")

    def test_rejects_link_local_metadata_address(self):
        for address in ("169.254.169.254", "fe80::1", "::ffff:169.254.169.254", "0.0.0.0", "224.0.0.1"):
            with self.subTest(address=address), _resolving_to(address), self.assertRaises(EndpointURLError):
                check_url("http://metadata/v1")

    def test_rejects_if_any_resolved_address_is_forbidden(self):
        with _resolving_to("10.0.0.1", "169.254.169.254"), self.assertRaises(EndpointURLError):
            check_url("http://mixed/v1")

    def test_allowlist_by_name(self):
        with patch.dict("os.environ", {ALLOWED_HOSTS_ENV_VAR: "ollama.example.org, *.ts.net"}), _resolving_to("100.64.0.1"):
            check_url("https://ollama.example.org/v1")
            check_url("http://laptop.tail1234.ts.net:11434/v1")
            with self.assertRaises(EndpointURLError):
                check_url("http://other.example.org/v1")

    def test_allowlist_by_network(self):
        with patch.dict("os.environ", {ALLOWED_HOSTS_ENV_VAR: "127.0.0.1/32,10.0.0.0/8"}):
            with _resolving_to("127.0.0.1"):
                check_url("http://localhost:11434/v1")
            with _resolving_to("10.0.0.1", "192.168.1.1"), self.assertRaises(EndpointURLError):
                check_url("http://partly-outside/v1")

    def test_unresolvable_host(self):
        with self.assertRaises(EndpointURLError):
            check_url("http://does-not-exist.invalid/v1")


if __name__ == "__main__":
    unittest.main()
