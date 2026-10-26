"""Reads the REAL Claude usage from the same endpoint the CLI's /usage uses.

Zero token cost: this is a usage query, not a model call. It reads the
account's OAuth access token from ~/.claude/.credentials.json and GETs
https://api.anthropic.com/api/oauth/usage. We never refresh the token
ourselves — the Claude Code CLI keeps it fresh in that file; if it has
expired we just report an 'auth' status until the CLI runs again.

No macOS o CLI guarda as credenciais no Chaveiro, nao no arquivo: sem o
arquivo, lemos o mesmo JSON pelo `security`. O token do Chaveiro fica em cache
na memoria e so e relido apos 401/403 — ler a cada tick poderia abrir o
dialogo de permissao do Chaveiro a cada minuto.
"""
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

ENDPOINT = "https://api.anthropic.com/api/oauth/usage"
HEADERS = {
    "anthropic-beta": "oauth-2025-04-20",
    "anthropic-version": "2023-06-01",
    "Content-Type": "application/json",
    "User-Agent": "claude-token-meter",
}
KEYCHAIN_SERVICE = "Claude Code-credentials"
_PLATFORM = sys.platform  # trocado nos testes
KEYCHAIN_RETRY_SECONDS = 600  # apos falha (item ausente ou "Negar"), espera antes de reler
_keychain_cache: dict = {"token": None, "failed_at": None}


@dataclass
class UsageSnapshot:
    pct: float                      # 0..1 session (5h) utilization
    reset_at: datetime | None       # when the 5h window resets (UTC)
    weekly_pct: float | None        # 0..1 seven-day utilization, if present
    weekly_reset_at: datetime | None
    status: str                     # "ok" | "auth" | "offline" | "error"


def default_credentials_path() -> Path:
    return Path.home() / ".claude" / ".credentials.json"


def _token_from_json(text: str) -> str | None:
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None
    oauth = (data.get("claudeAiOauth") if isinstance(data, dict) else None) or {}
    token = oauth.get("accessToken")
    return token if isinstance(token, str) and token else None


def read_keychain_token(service: str = KEYCHAIN_SERVICE) -> str | None:
    try:
        r = subprocess.run(
            ["security", "find-generic-password", "-s", service, "-w"],
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    raw = (r.stdout or "").strip()
    token = _token_from_json(raw)
    if token is None:
        # o `security -w` devolve em hex quando o valor nao e texto simples
        try:
            token = _token_from_json(bytes.fromhex(raw).decode("utf-8"))
        except ValueError:
            token = None
    return token


def clear_token_cache() -> None:
    _keychain_cache["token"] = None
    _keychain_cache["failed_at"] = None


def read_token(path: Path | None = None) -> str | None:
    """Caminho explicito (config) = so o arquivo. Sem caminho: o arquivo
    padrao e, no macOS, o Chaveiro quando o arquivo nao existe."""
    explicit = path is not None
    path = Path(path) if path else default_credentials_path()
    try:
        return _token_from_json(path.read_text(encoding="utf-8"))
    except OSError:
        pass
    if explicit or _PLATFORM != "darwin":
        return None
    if _keychain_cache["token"] is None:
        failed_at = _keychain_cache["failed_at"]
        if failed_at is not None and time.monotonic() - failed_at < KEYCHAIN_RETRY_SECONDS:
            return None
        _keychain_cache["token"] = read_keychain_token()
        _keychain_cache["failed_at"] = None if _keychain_cache["token"] else time.monotonic()
    return _keychain_cache["token"]


def _parse_iso(s) -> datetime | None:
    if not isinstance(s, str) or not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def parse_usage(data: dict) -> UsageSnapshot:
    fh = data.get("five_hour") or {}
    sd = data.get("seven_day") or {}
    pct = (fh.get("utilization") or 0) / 100.0
    weekly = sd.get("utilization")
    return UsageSnapshot(
        pct=max(0.0, min(1.0, pct)),
        reset_at=_parse_iso(fh.get("resets_at")),
        weekly_pct=(max(0.0, min(1.0, weekly / 100.0)) if weekly is not None else None),
        weekly_reset_at=_parse_iso(sd.get("resets_at")),
        status="ok",
    )


def fetch_usage(token: str, timeout: float = 15.0) -> dict:
    req = urllib.request.Request(
        ENDPOINT, headers={**HEADERS, "Authorization": f"Bearer {token}"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _empty(status: str) -> UsageSnapshot:
    return UsageSnapshot(0.0, None, None, None, status)


def get_snapshot(credentials_path: Path | None = None, timeout: float = 15.0) -> UsageSnapshot:
    token = read_token(credentials_path)
    if not token:
        return _empty("auth")
    try:
        data = fetch_usage(token, timeout)
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            clear_token_cache()  # o CLI pode ter renovado: o proximo tick rele
            return _empty("auth")
        if e.code == 429:
            return _empty("ratelimited")
        return _empty("error")
    except (urllib.error.URLError, TimeoutError, OSError):
        return _empty("offline")
    except (json.JSONDecodeError, ValueError):
        return _empty("error")
    return parse_usage(data)
