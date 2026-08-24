"""ocmo auth — OIDC authentication commands.

login:  Device-authorization flow by default; optional browser PKCE with --browser.
status: Show active context, identity, token expiry.
logout: Remove cached tokens for the context.
"""

from __future__ import annotations

import os
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import click

from .._auth_resolve import ResolvedOidc, auth_entry_from_resolved, resolve_oidc_settings
from .._click_groups import ConfigPathHelpGroup
from .._client import OcmoCtx, _fetch_oidc_from_server, build_ocmo_config
from .._config import AuthEntry, Context, _config_path, load_config
from .._errors import sdk_command
from .._options import output_option
from .._output import as_dict, emit, err, warn

if TYPE_CHECKING:
    from ocmo.config import OcmoConfig

    from .._config import CliConfig

_AUTH_HELP = """\
Authenticate with the OCMO server.

For CI/CD, set OCMO_TOKEN or OCMO_CLIENT_ID + OCMO_CLIENT_SECRET instead of logging in.
"""


@click.group("auth", cls=ConfigPathHelpGroup, help=_AUTH_HELP)
def auth_group() -> None:
    """Authenticate with the OCMO server."""


_LOGIN_HELP = """\
Log in interactively via OIDC (device code by default).

Use --browser for Authorization Code + PKCE on a fixed loopback port.
Tokens are cached in OCMO_CACHE_DIR.
"""

# Loopback PKCE callback (ocmo auth login --browser). Dex must register this URI exactly.
# High port avoids common dev services (8080, 8000, 3000, 9000, …).
CLI_CALLBACK_HOST = "127.0.0.1"
CLI_CALLBACK_PATH = "/callback"
CLI_CALLBACK_PORT = 47291


@auth_group.command("login", help=_LOGIN_HELP)
@click.option(
    "--browser",
    is_flag=True,
    default=False,
    help=f"Use browser PKCE login (loopback callback on port {CLI_CALLBACK_PORT}).",
)
@click.option("--context", default=None, help="Context to authenticate (default: current).")
@click.pass_obj
@sdk_command
def login_cmd(ctx: OcmoCtx, browser: bool, context: str | None) -> None:
    cfg = load_config()
    ctx_name = context or os.environ.get("OCMO_CONTEXT") or cfg.current_context
    active = cfg.contexts.get(ctx_name) if ctx_name else cfg.active_context()

    sdk_cfg = build_ocmo_config(
        skip_version_check=ctx.skip_version_check,
        context_name=ctx_name,
        validate_auth=False,
    )
    if not sdk_cfg.server:
        err("No server configured. Set OCMO_SERVER or run:\n" "  ocmo config set server https://ocmo.example.com")
        raise SystemExit(1)

    use_device = not browser

    try:
        auth_entry = resolve_login_auth(cfg, active, sdk_cfg, device_flow=use_device)
    except ValueError as exc:
        err(str(exc))
        raise SystemExit(1)

    if (
        active
        and active.auth
        and active.auth not in cfg.auths
        and (os.environ.get("OCMO_CLIENT_ID") or os.environ.get("OCMO_OIDC_ISSUER"))
    ):
        warn(
            f"Context references auth {active.auth!r} but no auths.{active.auth} block "
            "exists in the config file; using environment / API OIDC settings."
        )

    if use_device:
        _device_flow(auth_entry, sdk_cfg)
    else:
        _browser_flow(auth_entry, sdk_cfg)


def resolve_login_auth(
    cfg: CliConfig,
    active: Context | None,
    sdk_cfg: OcmoConfig,
    *,
    device_flow: bool = False,
) -> AuthEntry:
    """Resolve OIDC client settings for login from env, config file, and API hints."""
    file_entry: AuthEntry | None = None
    if active and active.auth:
        file_entry = cfg.auths.get(active.auth)

    server = os.environ.get("OCMO_SERVER") or (active.server if active else "") or cfg.server() or sdk_cfg.server or ""
    resolved = resolve_oidc_settings(
        server=server or None,
        entry=file_entry,
        fetch_server_oidc=_fetch_oidc_from_server,
    )
    issuer = sdk_cfg.oidc_issuer or resolved.issuer
    client_id = sdk_cfg.client_id or resolved.client_id
    client_secret = sdk_cfg.client_secret or resolved.client_secret

    if not issuer or not client_id:
        config_path = _config_path()
        auth_name = active.auth if active else None
        if device_flow:
            lines = [
                "Could not discover OIDC settings for device login.",
                "",
                "Set the server URL:",
                "  ocmo config set server https://ocmo.example.com",
                "  # or OCMO_SERVER",
            ]
        else:
            lines = [
                "OIDC issuer and client_id are required for login.",
                "",
                "Set environment variables:",
                "  OCMO_OIDC_ISSUER, OCMO_CLIENT_ID",
                "  OCMO_CLIENT_SECRET (when the client requires a secret)",
                "",
                f"Or add an auths: entry to {config_path}:",
                "  ocmo config set-auth <auth-name> --issuer <url> --client-id <id>",
                "  # or ocmo config set-context <ctx> --auth <auth-name> (creates mode: oidc)",
            ]
        if auth_name and auth_name not in cfg.auths:
            lines.append(f"\nContext references auth {auth_name!r} but that entry is missing.")
        raise ValueError("\n".join(lines))

    return auth_entry_from_resolved(ResolvedOidc(issuer=issuer, client_id=client_id, client_secret=client_secret))


def _pkce_redirect_uri(port: int = CLI_CALLBACK_PORT) -> str:
    return f"http://{CLI_CALLBACK_HOST}:{port}{CLI_CALLBACK_PATH}"


def _ensure_callback_port_available(port: int = CLI_CALLBACK_PORT) -> int:
    """Verify the fixed PKCE callback port is free before opening the browser."""
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((CLI_CALLBACK_HOST, port))
        except OSError as exc:
            raise RuntimeError(
                f"Cannot bind OAuth callback on {_pkce_redirect_uri(port)} ({exc}). "
                "Stop the process using that port, or run without --browser "
                "(default device-code login)."
            ) from exc
    return port


def _wait_for_authorization_code(port: int, state: str, *, timeout: float = 300.0) -> str:
    """Run a one-shot loopback HTTP server and return the OAuth authorization code."""
    import threading
    import time
    from http.server import BaseHTTPRequestHandler, HTTPServer
    from urllib.parse import parse_qs, urlparse

    result: dict[str, str] = {}
    done = threading.Event()

    class _CallbackHandler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
            return

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path != CLI_CALLBACK_PATH:
                self.send_response(404)
                self.end_headers()
                return

            params = parse_qs(parsed.query)
            if params.get("state", [""])[0] != state:
                result["error"] = "OAuth state mismatch (possible CSRF). Try login again."
                self._respond(400, "Invalid state. Return to the CLI and try again.")
                done.set()
                return

            if oauth_error := params.get("error", [""])[0]:
                desc = params.get("error_description", [oauth_error])[0]
                result["error"] = str(desc)
                self._respond(400, f"Authorization failed: {desc}")
                done.set()
                return

            code = params.get("code", [""])[0]
            if not code:
                result["error"] = "Authorization response missing code."
                self._respond(400, "Missing authorization code.")
                done.set()
                return

            result["code"] = code
            self._respond(200, "Login successful. You can close this tab and return to the CLI.")
            done.set()

        def _respond(self, status: int, message: str) -> None:
            body = ("<!DOCTYPE html><html><body>" f"<p>{message}</p>" "</body></html>").encode()
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = HTTPServer((CLI_CALLBACK_HOST, port), _CallbackHandler)
    server.timeout = 1.0

    def _serve() -> None:
        deadline = time.monotonic() + timeout
        while not done.is_set() and time.monotonic() < deadline:
            server.handle_request()
        server.server_close()

    thread = threading.Thread(target=_serve, daemon=True)
    thread.start()
    done.wait(timeout=timeout)
    thread.join(timeout=2)

    if "error" in result:
        raise RuntimeError(result["error"])
    if "code" not in result:
        raise RuntimeError("Timed out waiting for browser authorization.")
    return result["code"]


def _exchange_pkce_code(
    token_endpoint: str,
    *,
    code: str,
    redirect_uri: str,
    client_id: str,
    code_verifier: str,
    client_secret: str = "",
) -> tuple[str, int]:
    import httpx

    token_data: dict[str, str] = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "code_verifier": code_verifier,
    }
    if client_secret:
        token_data["client_secret"] = client_secret

    resp = httpx.post(str(token_endpoint), data=token_data, timeout=30)
    if resp.status_code != 200:
        body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
        detail = body.get("error_description") or body.get("error") or resp.text
        raise RuntimeError(f"Token exchange failed: {detail}")
    payload = resp.json()
    access_token = payload.get("access_token")
    if not access_token:
        raise RuntimeError("Token endpoint returned no access_token.")
    return str(access_token), int(payload.get("expires_in", 3600))


def _browser_flow(auth_entry: AuthEntry, sdk_cfg: OcmoConfig) -> None:
    """Authorization Code + PKCE via browser and a local loopback callback server."""
    try:
        import base64
        import hashlib
        import secrets
        import urllib.parse
        import webbrowser

        from ocmo.auth import fetch_oidc_discovery, store_oidc_access_token

        port = _ensure_callback_port_available()
        redirect_uri = _pkce_redirect_uri(port)
        state = secrets.token_urlsafe(16)

        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()
        code_challenge = base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest()).rstrip(b"=").decode()

        discovery = fetch_oidc_discovery(auth_entry.issuer)
        auth_endpoint = discovery.get("authorization_endpoint")
        token_endpoint = discovery.get("token_endpoint")
        if not auth_endpoint or not token_endpoint:
            err(f"OIDC provider at {auth_entry.issuer!r} is missing " "authorization_endpoint or token_endpoint.")
            raise SystemExit(1)

        scope = sdk_cfg.oidc_scope or "openid"
        client_secret = sdk_cfg.client_secret or auth_entry.client_secret

        auth_url = (
            str(auth_endpoint)
            + "?"
            + urllib.parse.urlencode(
                {
                    "response_type": "code",
                    "client_id": auth_entry.client_id,
                    "redirect_uri": redirect_uri,
                    "scope": scope,
                    "state": state,
                    "code_challenge": code_challenge,
                    "code_challenge_method": "S256",
                }
            )
        )

        print(f"Listening for OAuth callback on {redirect_uri}")
        print("Opening browser for login...")
        if not webbrowser.open(auth_url):
            print(f"If the browser did not open, visit:\n  {auth_url}")

        code = _wait_for_authorization_code(port, state)
        access_token, expires_in = _exchange_pkce_code(
            str(token_endpoint),
            code=code,
            redirect_uri=redirect_uri,
            client_id=auth_entry.client_id,
            code_verifier=code_verifier,
            client_secret=client_secret,
        )
        store_oidc_access_token(sdk_cfg, access_token, expires_in)
        _remove_legacy_token_file(sdk_cfg.cache_dir)
        print("Logged in successfully.")
    except SystemExit:
        raise
    except Exception as exc:
        err(f"Browser login error: {exc}")
        raise SystemExit(1)


def _device_flow(auth_entry: AuthEntry, sdk_cfg: OcmoConfig) -> None:
    """Device Authorization Grant (RFC 8628) via OIDC discovery."""
    try:
        import time

        import httpx
        from ocmo.auth import fetch_oidc_discovery, store_oidc_access_token

        discovery = fetch_oidc_discovery(auth_entry.issuer)
        device_endpoint = discovery.get("device_authorization_endpoint")
        token_endpoint = discovery.get("token_endpoint")
        if not device_endpoint or not token_endpoint:
            err(
                f"OIDC provider at {auth_entry.issuer!r} does not support the device flow "
                "(missing device_authorization_endpoint or token_endpoint)."
            )
            raise SystemExit(1)

        client_secret = sdk_cfg.client_secret or auth_entry.client_secret
        scope = sdk_cfg.oidc_scope or "openid"

        device_data: dict[str, str] = {
            "client_id": auth_entry.client_id,
            "scope": scope,
        }
        if client_secret:
            device_data["client_secret"] = client_secret

        resp = httpx.post(str(device_endpoint), data=device_data, timeout=30)
        resp.raise_for_status()
        device_resp = resp.json()

        uri = device_resp.get("verification_uri_complete") or device_resp.get("verification_uri")
        user_code = device_resp.get("user_code", "")
        device_code = device_resp["device_code"]
        interval = int(device_resp.get("interval", 5))
        expires_in = int(device_resp.get("expires_in", 300))

        print(f"\nOpen this URL in a browser:\n  {uri}")
        if user_code:
            print(f"Enter code: {user_code}")
        print(
            "\nLog in when prompted, then return to this terminal. "
            "The browser should show a Dex confirmation page (not the OCMO app)."
        )
        print("Waiting for authorization...")

        deadline = time.monotonic() + expires_in
        while time.monotonic() < deadline:
            time.sleep(interval)
            token_data: dict[str, str] = {
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "device_code": device_code,
                "client_id": auth_entry.client_id,
            }
            if client_secret:
                token_data["client_secret"] = client_secret

            token_resp = httpx.post(str(token_endpoint), data=token_data, timeout=30)
            if token_resp.status_code == 200:
                tokens = token_resp.json()
                access_token = tokens.get("access_token")
                if not access_token:
                    err("Token endpoint returned no access_token.")
                    raise SystemExit(1)
                store_oidc_access_token(
                    sdk_cfg,
                    str(access_token),
                    int(tokens.get("expires_in", 3600)),
                )
                _remove_legacy_token_file(sdk_cfg.cache_dir)
                print("Logged in successfully.")
                return

            body = token_resp.json()
            error = body.get("error", "")
            if error == "authorization_pending":
                continue
            if error == "slow_down":
                interval += 5
                continue
            if error == "unsupported_grant_type":
                err(
                    "Device flow is not enabled for this OIDC client. "
                    "Ask your IdP admin to allow grant type "
                    "'urn:ietf:params:oauth:grant-type:device_code' "
                    "(for local Dex, add it under oauth2.grantTypes in dex-config.yaml and restart Dex)."
                )
                raise SystemExit(1)
            err(f"Device flow error: {body.get('error_description', error)}")
            raise SystemExit(1)

        err("Device authorization timed out.")
        raise SystemExit(1)

    except SystemExit:
        raise
    except Exception as exc:
        err(f"Device flow error: {exc}")
        raise SystemExit(1)


def _remove_legacy_token_file(cache_dir: Path) -> bool:
    legacy = cache_dir / "token.json"
    if legacy.exists():
        legacy.unlink(missing_ok=True)
        return True
    return False


_STATUS_HELP = """\
Show the current authentication status and identity.

Each setting shows whether it comes from an environment variable or the config file.
Never prints secret or token values.
"""


@auth_group.command("status", help=_STATUS_HELP)
@output_option("auth status")
@click.pass_obj
@sdk_command
def status_cmd(ctx: OcmoCtx, output_fmt: str | None) -> None:
    report = _build_auth_status(ctx)
    fmt = output_fmt or ctx.output
    if fmt in ("json", "yaml"):
        emit(report, fmt)
        return
    _print_auth_status(report)


_LOGOUT_HELP = """\
Remove cached OIDC tokens for the current configuration.

Does not revoke tokens at the OIDC provider. Environment-provided OCMO_TOKEN is not cleared.
"""


@auth_group.command("logout", help=_LOGOUT_HELP)
@click.option("--context", default=None, help="Context to log out (default: current).")
@click.option("--all", "clear_all", is_flag=True, default=False, help="Clear every OIDC cache file in OCMO_CACHE_DIR.")
@click.pass_obj
@sdk_command
def logout_cmd(ctx: OcmoCtx, context: str | None, clear_all: bool) -> None:
    from ocmo.auth import clear_oidc_token_cache_dir, invalidate_oidc_token_cache

    cfg = load_config()
    ctx_name = context or os.environ.get("OCMO_CONTEXT") or cfg.current_context
    sdk_cfg = build_ocmo_config(
        skip_version_check=ctx.skip_version_check,
        context_name=ctx_name,
        validate_auth=False,
    )
    removed = 0

    if clear_all:
        removed += clear_oidc_token_cache_dir(sdk_cfg.cache_dir)
    elif sdk_cfg.auth_mode == "oidc":
        if invalidate_oidc_token_cache(sdk_cfg):
            removed += 1

    removed += int(_remove_legacy_token_file(sdk_cfg.cache_dir) or 0)

    if removed:
        print(f"Logged out: removed {removed} cached token entr{'y' if removed == 1 else 'ies'}.")
    else:
        print("No cached OIDC tokens found for the current configuration.")


def _sourced(env_var: str, config_value: str | None) -> dict[str, Any]:
    env_val = os.environ.get(env_var)
    if env_val is not None and env_val != "":
        return {"value": env_val, "source": "environment"}
    if config_value:
        return {"value": config_value, "source": "config"}
    return {"value": None, "source": "unset"}


def _masked_sourced(env_var: str, config_value: str | None, *, kind: str) -> dict[str, Any]:
    row = _sourced(env_var, config_value)
    if row["value"]:
        row["value"] = f"({kind}, set)"
    return row


def _build_auth_status(ctx: OcmoCtx) -> dict[str, Any]:
    cfg = load_config()
    config_path = _config_path()
    ctx_name = os.environ.get("OCMO_CONTEXT") or cfg.current_context or None
    active: Context | None = cfg.contexts.get(ctx_name) if ctx_name else cfg.active_context()
    auth_entry: AuthEntry | None = None
    if active and active.auth:
        auth_entry = cfg.auths.get(active.auth)

    context_source = "environment" if os.environ.get("OCMO_CONTEXT") else ("config" if ctx_name else "unset")

    report: dict[str, Any] = {
        "config_file": {
            "path": str(config_path),
            "exists": config_path.exists(),
        },
        "context": {
            "value": ctx_name,
            "source": context_source,
        },
        "server": _sourced("OCMO_SERVER", active.server if active else None),
        "namespace": _sourced("OCMO_NAMESPACE", active.namespace if active else None),
    }

    try:
        sdk_cfg = build_ocmo_config(
            skip_version_check=ctx.skip_version_check,
            context_name=ctx_name,
            validate_auth=False,
        )
    except Exception as exc:
        report["auth"] = {"error": str(exc)}
        return report

    auth_mode_source = "environment" if os.environ.get("OCMO_AUTH_MODE") else "inferred"
    report["auth_mode"] = {"value": sdk_cfg.auth_mode, "source": auth_mode_source}
    report["oidc_issuer"] = _sourced(
        "OCMO_OIDC_ISSUER",
        auth_entry.issuer if auth_entry else None,
    )
    report["oidc_token_url"] = _sourced(
        "OCMO_OIDC_TOKEN_URL",
        None,
    )
    report["client_id"] = _sourced(
        "OCMO_CLIENT_ID",
        auth_entry.client_id if auth_entry else None,
    )
    report["client_secret"] = _masked_sourced(
        "OCMO_CLIENT_SECRET",
        auth_entry.client_secret if auth_entry else None,
        kind="secret",
    )
    report["token"] = _masked_sourced(
        "OCMO_TOKEN",
        auth_entry.token if auth_entry else None,
        kind="bearer" if sdk_cfg.token and not str(sdk_cfg.token).startswith("ocmort-") else "token",
    )
    report["oidc_grant_type"] = _sourced("OCMO_OIDC_GRANT_TYPE", None)
    report["oidc_scope"] = _sourced("OCMO_OIDC_SCOPE", None)
    report["cache_dir"] = {
        "value": str(sdk_cfg.cache_dir),
        "source": "environment" if os.environ.get("OCMO_CACHE_DIR") else "default",
    }

    cache_info = _oidc_cache_info(sdk_cfg)
    if cache_info:
        report["oidc_cache"] = cache_info

    server = report["server"]["value"]
    if server:
        try:
            whoami = ctx.client().whoami()  # type: ignore[no-untyped-call]
            data = as_dict(whoami)
            report["identity"] = {
                "auth_type": data.get("auth_type"),
                "identifier": data.get("identifier"),
                "display_name": data.get("display_name"),
                "access_scope": data.get("access_scope"),
            }
            if data.get("user_details"):
                report["identity"]["user_details"] = data["user_details"]
            if data.get("resolver_details"):
                report["identity"]["resolver_details"] = data["resolver_details"]
        except Exception as exc:
            report["identity"] = {"error": str(exc)}
    else:
        report["identity"] = {"error": "server not configured"}

    return report


def _human_duration(seconds: float) -> str:
    """Format a positive duration for humans (e.g. '23 minutes', '2 hours')."""
    total = max(0, int(seconds))
    if total < 60:
        return f"{total} second{'s' if total != 1 else ''}"
    minutes, secs = divmod(total, 60)
    if minutes < 60:
        if secs:
            return f"{minutes} minute{'s' if minutes != 1 else ''} {secs}s"
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
    hours, mins = divmod(minutes, 60)
    if hours < 48:
        if mins:
            return f"{hours} hour{'s' if hours != 1 else ''} {mins}m"
        return f"{hours} hour{'s' if hours != 1 else ''}"
    days, hrs = divmod(hours, 24)
    if hrs:
        return f"{days} day{'s' if days != 1 else ''} {hrs}h"
    return f"{days} day{'s' if days != 1 else ''}"


def _describe_token_expiry(expires_at: Any) -> dict[str, Any]:
    """Turn a cache expiry timestamp into display-friendly fields."""
    if expires_at is None:
        return {
            "status": "unknown",
            "valid": False,
            "expires_at": None,
            "expires_in": None,
        }
    if not isinstance(expires_at, int | float | str):
        return {
            "status": "unknown",
            "valid": False,
            "expires_at": None,
            "expires_in": None,
        }
    try:
        ts = float(expires_at)
    except (TypeError, ValueError):
        return {
            "status": "unknown",
            "valid": False,
            "expires_at": str(expires_at),
            "expires_in": None,
        }

    remaining = ts - time.time()
    local_dt = datetime.fromtimestamp(ts, tz=UTC).astimezone()
    formatted = local_dt.strftime("%Y-%m-%d %H:%M:%S %Z")

    if remaining > 0:
        return {
            "status": "valid",
            "valid": True,
            "expires_at": formatted,
            "expires_at_unix": ts,
            "expires_in": f"in {_human_duration(remaining)}",
            "expires_in_seconds": int(remaining),
        }
    return {
        "status": "expired",
        "valid": False,
        "expires_at": formatted,
        "expires_at_unix": ts,
        "expires_in": f"expired {_human_duration(-remaining)} ago",
        "expires_in_seconds": int(remaining),
    }


def _oidc_cache_info(sdk_cfg: OcmoConfig) -> dict[str, Any] | None:
    if sdk_cfg.auth_mode != "oidc" or not sdk_cfg.client_id:
        return None
    try:
        from ocmo.auth import oidc_cache_status

        info = oidc_cache_status(sdk_cfg)
        if not info.get("cached"):
            return {"cached": False, "status": "none"}
        expiry = _describe_token_expiry(info.get("expires_at"))
        return {"cached": True, **expiry}
    except Exception:
        return {"cached": False, "status": "none"}


def _print_auth_status(report: dict[str, Any]) -> None:
    cfg = report["config_file"]
    print(f"Config file: {cfg['path']}" + ("" if cfg["exists"] else " (not created yet)"))

    def _line(label: str, row: dict[str, Any]) -> None:
        value = row.get("value")
        source = row.get("source", "unset")
        if value is None:
            display = "(not set)"
        else:
            display = str(value)
        print(f"{label:16} {display:40}  [{source}]")

    ctx_row = report["context"]
    print(f"{'Context':16} {str(ctx_row.get('value') or '(none)'):40}  [{ctx_row.get('source')}]")
    _line("Server", report["server"])
    _line("Namespace", report["namespace"])

    auth = report.get("auth")
    if auth and "error" in auth:
        print(f"\nAuth config: (unavailable: {auth['error']})")
        return

    print()
    _line("Auth mode", report["auth_mode"])
    _line("OIDC issuer", report["oidc_issuer"])
    if report["oidc_token_url"]["value"]:
        _line("OIDC token URL", report["oidc_token_url"])
    _line("Client ID", report["client_id"])
    _line("Client secret", report["client_secret"])
    _line("Token", report["token"])
    if report["oidc_grant_type"]["value"]:
        _line("OIDC grant", report["oidc_grant_type"])
    if report["oidc_scope"]["value"]:
        _line("OIDC scope", report["oidc_scope"])
    _line("Cache dir", report["cache_dir"])

    cache = report.get("oidc_cache")
    if cache:
        if cache.get("cached"):
            expires_at = cache.get("expires_at") or "unknown time"
            expires_in = cache.get("expires_in") or ""
            status = cache.get("status", "valid")
            if status == "expired":
                print(f"{'OIDC token':16} cached, expired")
                print(f"{'Expired at':16} {expires_at}")
                if expires_in:
                    print(f"{'':16} ({expires_in})")
            else:
                print(f"{'OIDC token':16} cached, valid")
                print(f"{'Expires at':16} {expires_at}")
                if expires_in:
                    print(f"{'':16} ({expires_in})")
        else:
            print(f"{'OIDC token':16} (not cached)")

    print()
    identity = report.get("identity") or {}
    if identity.get("error"):
        print(f"Identity:  ({identity['error']})")
        return
    ident = identity.get("identifier") or "(unknown)"
    display = identity.get("display_name")
    email = (identity.get("user_details") or {}).get("email")
    suffix = ""
    if display and display != ident:
        suffix = f" ({display})"
    if email:
        suffix += f" <{email}>"
    print(f"Identity:  {ident}{suffix}")
