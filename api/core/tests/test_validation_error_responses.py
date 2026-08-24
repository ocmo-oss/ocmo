"""Integration tests for API validation error responses."""

import json

from django.test import TestCase

from core.tests.auth_helpers import authenticated_as


class TestValidationErrorResponses(TestCase):
    def test_namespace_create_returns_field_specific_messages(self) -> None:
        with authenticated_as():
            response = self.client.post(
                "/api/v1/ns/",
                data=json.dumps({"name": "bad name!", "description": ""}),
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 422, response.content)
        payload = response.json()
        self.assertIn("error", payload)
        self.assertIsInstance(payload["error"], list)
        self.assertEqual(payload["errors"], payload["error"])
        self.assertTrue(
            any("name:" in message for message in payload["error"]),
            payload["error"],
        )

    def test_can_i_rejects_invalid_operation_with_field_message(self) -> None:
        with authenticated_as():
            response = self.client.post(
                "/api/v1/auth/can-i/",
                data=json.dumps({"operations": ["not-an-operation"]}),
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 422, response.content)
        payload = response.json()
        self.assertIsInstance(payload["error"], list)
        self.assertTrue(
            any("operations" in message for message in payload["error"]),
            payload["error"],
        )
