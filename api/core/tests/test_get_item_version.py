from django.test import Client, TestCase

from core.tests.namespace_helpers import create_test_namespace


class GetItemVersionTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.ns = create_test_namespace("get-item-version")
        self.client.post(
            f"/api/v1/ns/{self.ns.name}/~config/~create/app/cfg",
            data=b"key: one\n",
            content_type="application/yaml",
        )
        self.client.put(
            f"/api/v1/ns/{self.ns.name}/~config/~update/app/cfg",
            data=b"key: two\n",
            content_type="application/yaml",
        )

    def test_get_item_returns_requested_numeric_version(self):
        base = f"/api/v1/ns/{self.ns.name}/~get/app/cfg"
        v1 = self.client.get(base, {"version": "1"})
        v2 = self.client.get(base, {"version": "2"})

        self.assertEqual(v1.status_code, 200, v1.content)
        self.assertEqual(v2.status_code, 200, v2.content)
        self.assertEqual(v1.json()["version_data"]["data"], "key: one\n")
        self.assertEqual(v2.json()["version_data"]["data"], "key: two\n")
        self.assertEqual(v1.json()["version_data"]["version"], 1)
        self.assertEqual(v2.json()["version_data"]["version"], 2)
