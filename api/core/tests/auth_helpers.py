"""Shared helpers for API authentication in tests."""

from contextlib import contextmanager

from ocmoapi import testing_auth


@contextmanager
def deny_authentication():
    testing_auth._test_auth_deny = True
    try:
        yield
    finally:
        testing_auth._test_auth_deny = False


@contextmanager
def authenticated_as(user=None):
    testing_auth._test_auth_user = user if user is not None else testing_auth.default_test_user_claims()
    try:
        yield
    finally:
        testing_auth._test_auth_user = None
