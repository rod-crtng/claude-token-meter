#!/bin/bash
# Duplo clique no Finder abre o medidor (equivalente ao iniciar.bat do Windows).
cd "$(dirname "$0")"
nohup .venv/bin/python -m claude_token_meter.main >/dev/null 2>&1 &
# fecha a janela do Terminal que o Finder abriu
osascript -e 'tell application "Terminal" to close front window' >/dev/null 2>&1 &
exit 0
