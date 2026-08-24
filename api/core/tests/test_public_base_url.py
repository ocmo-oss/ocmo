"""Tests for public_base_url helper."""

from django.test import RequestFactory, SimpleTestCase, override_settings

from core.shortcuts import public_base_url


class PublicBaseUrlTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @override_settings(OCMO_PUBLIC_URL="http://localhost:8080")
    def test_uses_configured_public_url(self):
        request = self.factory.get("/api/v1/ns/prod/~resolve/app")
        self.assertEqual(public_base_url(request), "http://localhost:8080")

    @override_settings(OCMO_PUBLIC_URL="")
    def test_falls_back_to_request_absolute_uri(self):
        request = self.factory.get("/api/v1/ns/prod/~resolve/app", HTTP_HOST="ocmo.example.com")
        self.assertEqual(public_base_url(request), "http://ocmo.example.com")
