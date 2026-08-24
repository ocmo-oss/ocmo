"""Static audit: API route paths follow the trailing-slash URL convention."""

import pathlib
import re

from django.test import SimpleTestCase

_API_DIR = pathlib.Path(__file__).resolve().parent.parent / "api"
_ROUTE_DECORATOR = re.compile(r'@router\.(get|post|put|patch|delete)\(\s*(?:\n\s*)?["\']([^"\']+)["\']')


def _iter_registered_route_paths():
    for path in sorted(_API_DIR.glob("*.py")):
        if path.name.startswith("_"):
            continue
        for match in _ROUTE_DECORATOR.finditer(path.read_text()):
            yield match.group(2)


def _ends_in_path_param(route_path: str) -> bool:
    last_segment = route_path.rstrip("/").split("/")[-1]
    return last_segment.startswith("{") and last_segment.endswith("}")


_NO_TRAILING_SLASH_ROUTES = frozenset(
    {
        "/health",
        "/version",
        "/~config-metadata-schema",
        "/~resolver-configuration-schema",
    }
)


def _should_have_trailing_slash(route_path: str) -> bool:
    if route_path in _NO_TRAILING_SLASH_ROUTES:
        return False
    return not _ends_in_path_param(route_path)


class ApiTrailingSlashConventionTests(SimpleTestCase):
    def test_all_routes_follow_trailing_slash_rule(self):
        violations = []
        for route_path in _iter_registered_route_paths():
            should_have_slash = _should_have_trailing_slash(route_path)
            has_slash = route_path.endswith("/")
            if has_slash != should_have_slash:
                violations.append(f"{route_path!r}: has_trailing_slash={has_slash}, expected={should_have_slash}")
        self.assertEqual(
            violations,
            [],
            "Route paths must end with '/' for collections/actions only:\n" + "\n".join(violations),
        )
