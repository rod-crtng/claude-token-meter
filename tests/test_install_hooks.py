import json

from claude_token_meter import install_hooks as ih

PY = "/Users/x/claude-token-meter/.venv/bin/python"
HOOKS_PY = "/Users/x/claude-token-meter/claude_token_meter/hooks.py"


def _commands(settings, event):
    return [h["command"] for e in settings["hooks"].get(event, []) for h in e["hooks"]]


def test_merge_em_settings_vazio_cria_os_quatro_eventos():
    out = ih.merge_hooks({}, PY, HOOKS_PY)
    assert _commands(out, "UserPromptSubmit") == [f'"{PY}" "{HOOKS_PY}" working']
    assert _commands(out, "PreToolUse") == [f'"{PY}" "{HOOKS_PY}" working']
    assert out["hooks"]["PreToolUse"][0]["matcher"] == "*"
    assert _commands(out, "Notification") == [f'"{PY}" "{HOOKS_PY}" waiting']
    assert _commands(out, "Stop") == [f'"{PY}" "{HOOKS_PY}" free']


def test_merge_preserva_o_que_ja_existe():
    settings = {
        "model": "opus",
        "hooks": {"SessionStart": [{"hooks": [{"type": "command", "command": "echo oi"}]}],
                  "Stop": [{"hooks": [{"type": "command", "command": "echo fim"}]}]},
    }
    out = ih.merge_hooks(settings, PY, HOOKS_PY)
    assert out["model"] == "opus"
    assert _commands(out, "SessionStart") == ["echo oi"]
    assert _commands(out, "Stop") == ["echo fim", f'"{PY}" "{HOOKS_PY}" free']


def test_merge_e_idempotente():
    once = ih.merge_hooks({}, PY, HOOKS_PY)
    twice = ih.merge_hooks(json.loads(json.dumps(once)), PY, HOOKS_PY)
    assert twice == once


def test_install_faz_backup_e_grava(tmp_path):
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"model": "opus"}), encoding="utf-8")
    ih.install(settings, PY, HOOKS_PY)
    assert json.loads((tmp_path / "settings.json.bak-tokenmeter").read_text(encoding="utf-8")) == {"model": "opus"}
    data = json.loads(settings.read_text(encoding="utf-8"))
    assert data["model"] == "opus"
    assert _commands(data, "Stop") == [f'"{PY}" "{HOOKS_PY}" free']


def test_install_sem_settings_cria_o_arquivo(tmp_path):
    settings = tmp_path / ".claude" / "settings.json"
    ih.install(settings, PY, HOOKS_PY)
    assert _commands(json.loads(settings.read_text(encoding="utf-8")), "Notification")
