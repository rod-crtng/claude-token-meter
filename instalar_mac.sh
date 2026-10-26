#!/bin/bash
# Instala o medidor no macOS: Python 3.12 (pelo uv, sem mexer no python do
# sistema, que e 3.9) + venv + dependencias, liga as bolinhas de estado
# (hooks do Claude Code) e abre o medidor na barra de menu.
# Uso:  bash instalar_mac.sh
set -euo pipefail
cd "$(dirname "$0")"
DIR="$(pwd)"

if command -v uv >/dev/null 2>&1; then
  UV="$(command -v uv)"
elif [ -x "$HOME/.local/bin/uv" ]; then
  UV="$HOME/.local/bin/uv"
else
  echo "== Instalando o uv (baixa o Python certo sozinho)"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  UV="$HOME/.local/bin/uv"
fi

# roda de novo a cada atualizacao (atualizar.command): so cria o venv se faltar
if [ ! -x .venv/bin/python ]; then
  echo "== Criando o ambiente Python (.venv)"
  "$UV" venv --python 3.12 .venv
fi
echo "== Instalando as dependencias"
"$UV" pip install --python .venv/bin/python -r requirements.txt

chmod +x iniciar.command atualizar.command
# arquivo baixado pelo navegador vem com quarentena e o duplo clique e barrado
xattr -dr com.apple.quarantine "$DIR" 2>/dev/null || true

echo "== Conferindo a credencial do Claude Code no Chaveiro"
# sem -w: so confere que o item existe, sem ler o segredo (nao abre dialogo)
if security find-generic-password -s "Claude Code-credentials" >/dev/null 2>&1; then
  echo "   ok: credencial encontrada."
else
  echo "   AVISO: credencial nao encontrada. Abra o Terminal, rode 'claude' e faca o login;"
  echo "   depois rode este instalador de novo."
fi

echo "== Ligando as bolinhas de estado (hooks do Claude Code)"
# as bolinhas sao secundarias: falha aqui nao pode impedir o medidor de abrir
.venv/bin/python -m claude_token_meter.install_hooks \
  || echo "   AVISO: bolinhas nao ligadas; o medidor funciona sem elas."

echo "== Abrindo o medidor"
pkill -f "claude_token_meter.main" 2>/dev/null || true
nohup .venv/bin/python -m claude_token_meter.main >/dev/null 2>&1 &
echo
echo "Pronto. O medidor aparece na barra de menu, no alto da tela, perto do relogio."
echo "Na primeira leitura o Mac pode perguntar sobre o Chaveiro: clique em 'Sempre Permitir'."
echo "Ele ja fica configurado pra abrir sozinho quando o Mac ligar."
