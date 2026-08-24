"""Tests for namespace creation validation."""

from django.test import TestCase

from core.models import Namespace


class TestNamespaceCreateValidation(TestCase):
    def test_full_clean_allows_empty_description(self) -> None:
        ns = Namespace(name="empty-desc-ns", description="")
        ns.full_clean()
