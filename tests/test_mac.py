"""Suporte ao macOS: pasta de dados, token do Chaveiro, LaunchAgent e trava de
instancia unica. Roda no Windows tambem: a plataforma e injetada e o `security`
e sempre simulado (nunca chamamos o Chaveiro de verdade nos testes)."""

import json
import plistlib
import subprocess
import sys
import urllib.error
from pathlib import Path

import pytest

from claude_token_meter import autostart
from claude_token_meter import config as cfg
from claude_token_meter import hooks
from claude_token_meter import status as st
from claude_token_meter import usage_client as uc

CREDS = {"claudeAiOauth": {"accessToken": "sk-ant-oat-mac"}}


# --- pasta de dados -------------------------------------------------------

def test_data_dir_windows_usa_appdata(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert cfg.data_dir("win32") == tmp_path / "claude-token-meter"


def test_data_dir_mac_application_support(monkeypatch, tmp_path):
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    expected = tmp_path / "Library" / "Application Support" / "claude-token-meter"
    assert cfg.data_dir("darwin") == expected


def test_data_dir_linux_cai_na_home(monkeypatch, tmp_path):
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    assert cfg.data_dir("linux") == tmp_path / "claude-token-meter"


@pytest.mark.parametrize("platform", ["darwin", "win32", "linux"])
def test_hooks_e_status_apontam_pro_mesmo_arquivo(monkeypatch, tmp_path, platform):
    # hooks.py duplica a regra (e standalone); se divergir, as bolinhas nunca acendem
    monkeypatch.delenv("APPDATA", raising=False)
    if platform == "win32":
        monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    assert hooks.status_path(platform) == st.default_status_path(platform)


# --- token do Chaveiro ----------------------------------------------------

class _Run:
    """Simula subprocess.run do `security` e conta as chamadas."""

    def __init__(self, stdout="", returncode=0):
        self.stdout = stdout
        self.returncode = returncode
        self.calls = []

    def __call__(self, args, **kwargs):
        self.calls.append(args)
        return subprocess.CompletedProcess(args, self.returncode, self.stdout, "")


@pytest.fixture
def mac(monkeypatch, tmp_path):
    """macOS sem ~/.claude/.credentials.json, cache do Chaveiro zerado."""
    monkeypatch.setattr(uc, "_PLATFORM", "darwin")
    monkeypatch.setattr(uc, "default_credentials_path", lambda: tmp_path / "nope.json")
    uc.clear_token_cache()
    yield
    uc.clear_token_cache()


def test_keychain_le_json_do_security(mac, monkeypatch):
    run = _Run(json.dumps(CREDS) + "\n")
    monkeypatch.setattr(uc.subprocess, "run", run)
    assert uc.read_token() == "sk-ant-oat-mac"
    assert run.calls[0][:4] == ["security", "find-generic-password", "-s", uc.KEYCHAIN_SERVICE]


def test_keychain_aceita_valor_em_hex(mac, monkeypatch):
    run = _Run(json.dumps(CREDS).encode("utf-8").hex())
    monkeypatch.setattr(uc.subprocess, "run", run)
    assert uc.read_token() == "sk-ant-oat-mac"


def test_keychain_item_ausente_da_none(mac, monkeypatch):
    monkeypatch.setattr(uc.subprocess, "run", _Run("", returncode=44))
    assert uc.read_token() is None


def test_keychain_sem_comando_security_da_none(mac, monkeypatch):
    def boom(*a, **k):
        raise FileNotFoundError("security")
    monkeypatch.setattr(uc.subprocess, "run", boom)
    assert uc.read_token() is None


def test_keychain_fica_em_cache_entre_ticks(mac, monkeypatch):
    # ler o Chaveiro a cada tick pode abrir o dialogo de permissao a cada minuto
    run = _Run(json.dumps(CREDS))
    monkeypatch.setattr(uc.subprocess, "run", run)
    uc.read_token()
    uc.read_token()
    assert len(run.calls) == 1


def test_falha_no_chaveiro_espera_antes_de_tentar_de_novo(mac, monkeypatch):
    # se a pessoa clicar "Negar", nao reabrir o dialogo a cada minuto
    now = [1000.0]
    monkeypatch.setattr(uc.time, "monotonic", lambda: now[0])
    run = _Run("", returncode=51)
    monkeypatch.setattr(uc.subprocess, "run", run)
    assert uc.read_token() is None
    now[0] += 60
    assert uc.read_token() is None
    assert len(run.calls) == 1
    now[0] += uc.KEYCHAIN_RETRY_SECONDS
    uc.read_token()
    assert len(run.calls) == 2


def test_401_limpa_o_cache_e_o_proximo_tick_rele(mac, monkeypatch):
    run = _Run(json.dumps(CREDS))
    monkeypatch.setattr(uc.subprocess, "run", run)

    def boom(token, timeout=15.0):
        raise urllib.error.HTTPError(uc.ENDPOINT, 401, "Unauthorized", {}, None)

    monkeypatch.setattr(uc, "fetch_usage", boom)
    assert uc.get_snapshot().status == "auth"
    uc.get_snapshot()
    assert len(run.calls) == 2


def test_arquivo_de_credenciais_vence_o_chaveiro(mac, monkeypatch, tmp_path):
    creds = tmp_path / ".credentials.json"
    creds.write_text(json.dumps({"claudeAiOauth": {"accessToken": "do-arquivo"}}),
                     encoding="utf-8")
    monkeypatch.setattr(uc, "default_credentials_path", lambda: creds)
    run = _Run(json.dumps(CREDS))
    monkeypatch.setattr(uc.subprocess, "run", run)
    assert uc.read_token() == "do-arquivo"
    assert run.calls == []


def test_arquivo_sem_login_cai_no_chaveiro(mac, monkeypatch, tmp_path):
    # arquivo so com mcpOAuth (formato real) nao pode esconder o Chaveiro
    creds = tmp_path / ".credentials.json"
    creds.write_text(json.dumps({"mcpOAuth": {}}), encoding="utf-8")
    monkeypatch.setattr(uc, "default_credentials_path", lambda: creds)
    monkeypatch.setattr(uc.subprocess, "run", _Run(json.dumps(CREDS)))
    assert uc.read_token() == "sk-ant-oat-mac"


def test_caminho_explicito_nao_cai_no_chaveiro(mac, monkeypatch, tmp_path):
    run = _Run(json.dumps(CREDS))
    monkeypatch.setattr(uc.subprocess, "run", run)
    assert uc.read_token(tmp_path / "configurado.json") is None
    assert run.calls == []


def test_windows_nunca_chama_security(monkeypatch, tmp_path):
    monkeypatch.setattr(uc, "_PLATFORM", "win32")
    monkeypatch.setattr(uc, "default_credentials_path", lambda: tmp_path / "nope.json")
    run = _Run(json.dumps(CREDS))
    monkeypatch.setattr(uc.subprocess, "run", run)
    assert uc.read_token() is None
    assert run.calls == []


# --- autostart: LaunchAgent -----------------------------------------------

def test_launchagent_path(tmp_path):
    p = autostart.shortcut_path(tmp_path, platform="darwin")
    assert p == tmp_path / "com.crtng.claude-token-meter.plist"


def test_launchagent_enable_grava_plist(tmp_path):
    autostart.enable(tmp_path, platform="darwin")
    p = tmp_path / "com.crtng.claude-token-meter.plist"
    data = plistlib.loads(p.read_bytes())
    assert data["Label"] == "com.crtng.claude-token-meter"
    assert data["ProgramArguments"] == [sys.executable, "-m", "claude_token_meter.main"]
    assert data["RunAtLoad"] is True
    assert Path(data["WorkingDirectory"]) == Path(autostart.__file__).resolve().parent.parent
    assert autostart.is_enabled(tmp_path, platform="darwin") is True


def test_launchagent_disable_remove(tmp_path):
    autostart.enable(tmp_path, platform="darwin")
    autostart.disable(tmp_path, platform="darwin")
    assert autostart.is_enabled(tmp_path, platform="darwin") is False


def test_texto_do_menu_por_plataforma():
    assert autostart.menu_label("win32") == "Iniciar com o Windows"
    assert autostart.menu_label("darwin") == "Iniciar com o Mac"


# --- instancia unica fora do Windows -------------------------------------

def test_trava_posix_recusa_segunda_instancia(tmp_path):
    pytest.importorskip("fcntl")
    from claude_token_meter import singleton
    lock = tmp_path / "instance.lock"
    first = singleton.acquire_posix(lock)
    assert first is not None
    assert singleton.acquire_posix(lock) is None
    singleton.release_posix(first)
    assert singleton.acquire_posix(lock) is not None
