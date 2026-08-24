"""Tests for the ocmo-api management CLI."""

from unittest.mock import patch

from click.testing import CliRunner
from django.test import TestCase

from ocmoapi.cli import _gunicorn_argv, cli


class OcmoApiCliTests(TestCase):
    def test_migrate_applies_migrations(self):
        runner = CliRunner()
        with patch("django.core.management.call_command") as call_command:
            result = runner.invoke(cli, ["migrate", "--noinput"])
        self.assertEqual(result.exit_code, 0, result.output)
        call_command.assert_called_once_with("migrate", interactive=False)

    def test_migrate_interactive_by_default(self):
        runner = CliRunner()
        with patch("django.core.management.call_command") as call_command:
            result = runner.invoke(cli, ["migrate"])
        self.assertEqual(result.exit_code, 0, result.output)
        call_command.assert_called_once_with("migrate", interactive=True)

    def test_gunicorn_argv_uses_wsgi_application(self):
        argv = _gunicorn_argv("127.0.0.1:9000", 2, 60)
        self.assertIn("ocmoapi.wsgi:application", argv)
        self.assertIn("--bind", argv)
        self.assertIn("127.0.0.1:9000", argv)
        self.assertIn("--workers", argv)
        self.assertIn("2", argv)
        self.assertIn("--timeout", argv)
        self.assertIn("60", argv)

    def test_serve_execs_gunicorn(self):
        runner = CliRunner()
        with patch("os.execvp") as execvp:
            result = runner.invoke(cli, ["serve", "--bind", "127.0.0.1:9001", "--workers", "1", "--timeout", "30"])
        self.assertEqual(result.exit_code, 0, result.output)
        argv = execvp.call_args[0][1]
        self.assertIn("ocmoapi.wsgi:application", argv)
        self.assertIn("127.0.0.1:9001", argv)
