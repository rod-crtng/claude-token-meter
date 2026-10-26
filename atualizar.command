#!/bin/bash
# Duplo clique no Finder: baixa a versao nova do medidor (git pull) e reinstala.
cd "$(dirname "$0")"
echo "== Baixando a versao nova"
if git pull --ff-only; then
  bash instalar_mac.sh
else
  echo
  echo "Nao consegui atualizar (veja a mensagem acima). Nada foi mudado."
fi
echo
read -n 1 -s -r -p "Pressione qualquer tecla para fechar..."
echo
