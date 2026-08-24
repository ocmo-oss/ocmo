from django.http import HttpRequest, QueryDict
from django.test import SimpleTestCase

from ocmoapi.auth import RESOLVER_TOKEN_HEADER, RESOLVER_TOKEN_QUERY_PARAM, resolver_auth


class ResolverAuthKeyExtractionTests(SimpleTestCase):
    def _request(self, *, query_token=None, header_token=None):
        request = HttpRequest()
        request.method = "GET"
        if query_token is not None:
            request.GET = QueryDict(f"{RESOLVER_TOKEN_QUERY_PARAM}={query_token}")
        if header_token is not None:
            request.META[f"HTTP_{RESOLVER_TOKEN_HEADER.upper().replace('-', '_')}"] = header_token
        return request

    def test_reads_query_param(self):
        self.assertEqual(
            resolver_auth._get_key(self._request(query_token="abc123")),
            "abc123",
        )

    def test_reads_header(self):
        self.assertEqual(
            resolver_auth._get_key(self._request(header_token="abc123")),
            "abc123",
        )

    def test_query_param_takes_precedence_over_header(self):
        self.assertEqual(
            resolver_auth._get_key(self._request(query_token="from-query", header_token="from-header")),
            "from-query",
        )
