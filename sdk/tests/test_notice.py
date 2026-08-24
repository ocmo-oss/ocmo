"""Tests for bundled product NOTICE."""

from ocmo.notice import LICENSE_SPDX, PRODUCT, load_notice_text, product_version_info


def test_load_notice_text_contains_statement() -> None:
    text = load_notice_text()
    assert "STATEMENT ON RUSSIAN WAR CRIMES IN UKRAINE" in text
    assert "OCMO" in text


def test_product_version_info_with_notice() -> None:
    info = product_version_info(include_notice=True)
    assert info["product"] == PRODUCT
    assert info["license"] == LICENSE_SPDX
    assert "notice" in info
    assert "OCMO" in info["notice"]
