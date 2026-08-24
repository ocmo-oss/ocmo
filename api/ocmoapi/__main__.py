"""Allow `python -m ocmoapi` to invoke the management CLI."""

from ocmoapi.cli import cli

if __name__ == "__main__":
    cli()
