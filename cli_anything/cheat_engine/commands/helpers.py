"""Shared CLI helpers: context, output formatting."""

from __future__ import annotations

import json
from typing import Any

import click


class CLIContext:
    """Shared context passed between Click commands."""

    def __init__(self, json_mode: bool = False) -> None:
        self.json_mode = json_mode
        self._session = None
        self._bridge = None

    @property
    def session(self):  # type: ignore[no-untyped-def]
        if self._session is None:
            from ..core.session import SessionManager
            self._session = SessionManager()
        return self._session


pass_ctx = click.make_pass_decorator(CLIContext, ensure=True)


def output(data: Any, ctx: CLIContext, text: str = "") -> None:
    """Print output in JSON or human-readable form."""
    if ctx.json_mode:
        click.echo(json.dumps(data, indent=2, ensure_ascii=False, default=str))
    else:
        click.echo(text or json.dumps(data, indent=2, ensure_ascii=False, default=str))


def error_output(message: str, ctx: CLIContext) -> None:
    """Print an error message."""
    if ctx.json_mode:
        click.echo(json.dumps({"success": False, "error": message}))
    else:
        click.echo(f"Error: {message}", err=True)
