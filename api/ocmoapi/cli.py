"""Management CLI for the OCMO API service (`ocmo-api` console script)."""

from __future__ import annotations

import os
import sys

import click


def _django_setup() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ocmoapi.settings")
    import django

    django.setup()


def _gunicorn_argv(bind: str, workers: int, timeout: int) -> list[str]:
    return [
        sys.executable,
        "-m",
        "gunicorn",
        "ocmoapi.wsgi:application",
        "--bind",
        bind,
        "--workers",
        str(workers),
        "--timeout",
        str(timeout),
        "--access-logfile",
        "-",
        "--error-logfile",
        "-",
    ]


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(package_name="ocmo-api", prog_name="ocmo-api")
def cli() -> None:
    """OCMO API service management."""


@cli.command()
@click.option(
    "--noinput",
    is_flag=True,
    default=False,
    help="Run non-interactively (recommended in containers).",
)
def migrate(noinput: bool) -> None:
    """Apply database migrations."""
    _django_setup()
    from django.core.management import call_command

    call_command("migrate", interactive=not noinput)


@cli.command()
@click.option(
    "--bind",
    default="0.0.0.0:8000",
    show_default=True,
    envvar="GUNICORN_BIND",
    help="Bind address (HOST:PORT).",
)
@click.option(
    "--workers",
    default=None,
    type=int,
    envvar="GUNICORN_WORKERS",
    help="Number of worker processes.",
)
@click.option(
    "--timeout",
    default=None,
    type=int,
    envvar="GUNICORN_TIMEOUT",
    help="Worker timeout in seconds.",
)
def serve(bind: str, workers: int | None, timeout: int | None) -> None:
    """Start the production WSGI server (gunicorn)."""
    worker_count = workers if workers is not None else int(os.environ.get("GUNICORN_WORKERS", "4"))
    worker_timeout = timeout if timeout is not None else int(os.environ.get("GUNICORN_TIMEOUT", "120"))
    argv = _gunicorn_argv(bind, worker_count, worker_timeout)
    os.execvp(argv[0], argv)
