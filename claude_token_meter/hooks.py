"""Escreve o estado da sessao pro medidor, chamado pelos hooks do Claude Code.

Standalone de proposito: NAO importa o pacote, pra rodar por caminho absoluto
a partir de qualquer cwd (o Claude Code invoca o hook fora do repo).

Uso:  py hooks.py working|waiting|free
Os hooks passam JSON no stdin; ignoramos. So o argv importa. Sai rapido e
silencioso (nunca falha o hook) pra nao segurar a sessao.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

STATES = ("working", "waiting", "free")


def status_path(platform=None) -> Path:
    # mesma regra de config.data_dir, duplicada de proposito (sem import do pacote)
    appdata = os.environ.get("APPDATA")
    if appdata:
        base = Path(appdata) / "claude-token-meter"
    elif (platform or sys.platform) == "darwin":
        base = Path.home() / "Library" / "Application Support" / "claude-token-meter"
    else:
        base = Path.home() / "claude-token-meter"
    return base / "status.json"


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in STATES:
        return 0  # nada a fazer; nunca quebra o hook
    state = sys.argv[1]
    try:
        path = status_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"state": state, "ts": datetime.now(timezone.utc).isoformat()}
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload), encoding="utf-8")
        os.replace(tmp, path)
    except Exception:
        pass  # hook nunca deve falhar por causa disso
    return 0


if __name__ == "__main__":
    sys.exit(main())
