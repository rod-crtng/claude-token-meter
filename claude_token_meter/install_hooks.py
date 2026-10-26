"""Liga as bolinhas de estado: soma os hooks do medidor ao ~/.claude/settings.json.

Junta (nunca substitui) o que ja existe, faz backup em settings.json.bak-tokenmeter
e pode rodar de novo sem duplicar. Usado pelo instalar_mac.sh:

    .venv/bin/python -m claude_token_meter.install_hooks
"""

import json
import shutil
import sys
from copy import deepcopy
from pathlib import Path

# evento do Claude Code -> (estado, matcher)
EVENTS = (
    ("UserPromptSubmit", "working", None),
    ("PreToolUse", "working", "*"),
    ("Notification", "waiting", None),
    ("Stop", "free", None),
)


def merge_hooks(settings: dict, python: str, hooks_py: str) -> dict:
    out = deepcopy(settings)
    hooks = out.setdefault("hooks", {})
    for event, state, matcher in EVENTS:
        command = f'"{python}" "{hooks_py}" {state}'
        entries = hooks.setdefault(event, [])
        present = any(h.get("command") == command
                      for e in entries for h in e.get("hooks", []))
        if present:
            continue
        entry = {"hooks": [{"type": "command", "command": command}]}
        if matcher:
            entry = {"matcher": matcher, **entry}
        entries.append(entry)
    return out


def install(settings_path: Path, python: str, hooks_py: str) -> None:
    settings_path = Path(settings_path)
    if settings_path.exists():
        current = json.loads(settings_path.read_text(encoding="utf-8"))
        shutil.copy2(settings_path, settings_path.with_name(settings_path.name + ".bak-tokenmeter"))
    else:
        current = {}
        settings_path.parent.mkdir(parents=True, exist_ok=True)
    merged = merge_hooks(current, python, hooks_py)
    settings_path.write_text(json.dumps(merged, indent=2, ensure_ascii=False) + "\n",
                             encoding="utf-8")


def main() -> int:
    settings = Path.home() / ".claude" / "settings.json"
    hooks_py = str(Path(__file__).resolve().parent / "hooks.py")
    try:
        install(settings, sys.executable, hooks_py)
    except json.JSONDecodeError:
        print(f"{settings} nao e JSON valido — nada foi alterado. Corrija e rode de novo.")
        return 1
    print(f"Hooks do medidor ligados em {settings}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
