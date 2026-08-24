"""Click group helpers."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import click

from ._lazy_mixin import ClickLazyMixin


class DefaultCommandGroup(click.Group):
    """Group that routes unknown first tokens to a default subcommand."""

    def __init__(self, *args: Any, default_command: str, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.default_command = default_command

    def parse_args(self, ctx: click.Context, args: list[str]) -> list[str]:
        if args and args[0] not in self.commands and not args[0].startswith("-"):
            args = [self.default_command, *args]
        return super().parse_args(ctx, args)

    def _default_command(self, ctx: click.Context) -> click.Command | None:
        cmd = self.get_command(ctx, self.default_command)
        if cmd is None:
            return None
        return cmd

    def resolve_command(
        self,
        ctx: click.Context,
        args: list[str],
    ) -> tuple[str | None, click.Command | None, list[str]]:
        if not args:
            return None, None, args

        first = args[0]
        if first in self.commands:
            return super().resolve_command(ctx, args)

        if ctx.token_normalize_func is not None:
            normalized = ctx.token_normalize_func(first)
            if normalized in self.commands:
                return super().resolve_command(ctx, args)

        default_cmd = self._default_command(ctx)
        if default_cmd is None:
            return super().resolve_command(ctx, args)

        if first.startswith("-") or first not in self.commands:
            return self.default_command, default_cmd, args

        return super().resolve_command(ctx, args)

    def shell_complete(
        self,
        ctx: click.Context,
        incomplete: str,
    ) -> list[click.shell_completion.CompletionItem]:
        results = super().shell_complete(ctx, incomplete)
        default_cmd = self._default_command(ctx)
        if default_cmd is None:
            return results

        seen = {item.value for item in results}
        for item in default_cmd.shell_complete(ctx, incomplete):
            if item.value not in seen:
                results.append(item)
                seen.add(item.value)
        return results

    def format_help(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        """Include the default subcommand's options in group help."""
        self.format_usage(ctx, formatter)
        self.format_help_text(ctx, formatter)
        default_cmd = self.get_command(ctx, self.default_command)
        if default_cmd is not None:
            with formatter.section("Options"):
                opts: list[tuple[str, str]] = []
                for param in default_cmd.get_params(ctx):
                    record = param.get_help_record(ctx)
                    if record is not None:
                        opts.append(record)
                if opts:
                    formatter.write_dl(opts)
        self.format_commands(ctx, formatter)
        self.format_epilog(ctx, formatter)


class ResourceAliasGroup(click.Group):
    """Group that lists resource aliases on one help line per canonical command."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._alias_to_canonical: dict[str, str] = {}
        self._aliases_for_resource: dict[str, list[str]] = {}

    def add_resource_command(
        self,
        cmd: click.Command,
        *,
        canonical: str,
        aliases: list[str] | None = None,
    ) -> None:
        """Register a command under its canonical name and optional aliases."""
        self.add_command(cmd, name=canonical)
        alias_list = aliases or []
        if alias_list:
            self._aliases_for_resource[canonical] = alias_list
            for alias in alias_list:
                self._alias_to_canonical[alias] = canonical
                self.add_command(cmd, name=alias)

    def format_commands(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        commands: list[tuple[str, click.Command]] = []
        for subcommand in self.list_commands(ctx):
            if subcommand in self._alias_to_canonical:
                continue
            cmd = self.get_command(ctx, subcommand)
            if cmd is None or cmd.hidden:
                continue
            commands.append((subcommand, cmd))

        if not commands:
            return

        limit = formatter.width - 6 - max(len(name) for name, _ in commands)

        rows: list[tuple[str, str]] = []
        for subcommand, cmd in commands:
            help_text = cmd.get_short_help_str(limit=limit)
            aliases = self._aliases_for_resource.get(subcommand, [])
            if aliases:
                suffix = f" (aliases: {', '.join(aliases)})"
                help_text = f"{help_text}{suffix}" if help_text else suffix.strip()
            rows.append((subcommand, help_text))

        with formatter.section("Commands"):
            formatter.write_dl(rows)


def ensure_resource_alias_group(
    root: click.Group,
    name: str,
    *,
    help: str,
) -> ResourceAliasGroup:
    """Return an existing relocate group or create a ``ResourceAliasGroup`` stub."""
    group = root.commands.get(name)
    if isinstance(group, ResourceAliasGroup):
        return group
    if isinstance(group, click.Group):
        return group  # type: ignore[return-value]

    @click.group(name, cls=ResourceAliasGroup, help=help)
    @click.pass_context
    def group_cmd(ctx: click.Context) -> None:
        pass

    root.add_command(group_cmd)
    return group_cmd


def attach_resource_command(
    group: click.Group,
    cmd: click.Command,
    *,
    canonical: str,
    aliases: list[str] | None = None,
) -> None:
    """Register a command on a group, using alias metadata when supported."""
    if isinstance(group, ResourceAliasGroup):
        group.add_resource_command(cmd, canonical=canonical, aliases=aliases)
    elif isinstance(group, click.Group):
        group.add_command(cmd, name=canonical)


class ConfigPathHelpGroup(click.Group):
    """Group that appends the local CLI config file path to help."""

    def format_help(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        super().format_help(ctx, formatter)
        from ._config import format_config_path_note

        formatter.write_paragraph()
        formatter.write_text(format_config_path_note())


class LazyGroup(ClickLazyMixin, click.Group):
    """Group stub that builds the real group on first use."""

    def __init__(
        self,
        name: str,
        *,
        help: str,
        build_fn: Callable[[], click.Group],
    ) -> None:
        super().__init__(name, help=help)
        self._build_fn = build_fn
        self._real: click.Group | None = None

    def _lazy_target(self) -> click.Group:
        return self._ensure()

    def _ensure(self) -> click.Group:
        if self._real is None:
            self._real = self._build_fn()
        return self._real

    def list_commands(self, ctx: click.Context) -> list[str]:
        return self._ensure().list_commands(ctx)

    def get_command(self, ctx: click.Context, cmd_name: str) -> click.Command | None:
        return self._ensure().get_command(ctx, cmd_name)

    def resolve_command(
        self,
        ctx: click.Context,
        args: list[str],
    ) -> tuple[str | None, click.Command | None, list[str]]:
        return self._ensure().resolve_command(ctx, args)

    def format_help(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        self._ensure().format_help(ctx, formatter)
