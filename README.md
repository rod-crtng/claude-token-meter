# claude-token-meter

Icone na bandeja do Windows que mostra o consumo da janela de sessao atual do
Claude Code (% + tempo pra resetar) e o uso semanal; um clique abre a barra
completa.

**Le o numero REAL** — a mesma fonte que o comando `/usage` do Claude Code
usa: o endpoint `GET /api/oauth/usage` da Anthropic, autenticado com o token
OAuth que ja esta no seu `~/.claude/.credentials.json`. O `%` bate exato com
o que o app mostra.

**Custo em tokens: zero.** E uma consulta de uso, nao uma chamada de modelo.
Precisa de rede e do seu login do Claude Code; nunca renova o token sozinho
(o proprio CLI mantem ele fresco no arquivo) — se expirar, a barra mostra
"expirado" ate voce rodar o Claude Code de novo.

## Rodar

```
py -3 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
iniciar.bat
```

O medidor mora na **bandeja do sistema** (ao lado do relogio). No Windows 11 o
icone novo nasce escondido na setinha `^` — arraste-o pra barra se quiser ve-lo
sempre. O icone mostra o % da sessao na cor da regua; passar o mouse mostra
sessao e semanal com o tempo pro reset. Clique esquerdo abre a barra completa
logo acima do relogio (some ao clicar fora); clique direito: iniciar com o
Windows, sair.

## O que a barra mostra

- `NN%` + `reset 4h28` — utilizacao da janela de sessao de 5h e quanto falta
  pra resetar (campo `five_hour` do endpoint).
- Cores: verde / ambar (>=60%) / vermelho (>=85%) — thresholds configuraveis.
- Estados sem dado: `expirado` (token venceu), `offline` (sem rede), `erro`.
- `sem NN% 1d22h` — uso semanal (`seven_day`) e quanto falta pro reset
  (dias e horas; abaixo de 24h em horas, abaixo de 1h em minutos).
- Tooltip do icone: sessao + semanal, com dia e hora exatos do reset semanal.
- **3 bolinhas de estado** (direita, estilo controles de janela do macOS):
  vermelho=Claude trabalhando, amarelo=aguardando sua confirmacao, verde=livre.
  A do estado atual fica acesa; as outras duas apagadas.

## Bolinhas de estado (hooks)

O medidor e um processo separado — nao sabe o que o Claude Code esta fazendo.
Quem alimenta o estado sao **hooks do Claude Code** que gravam
`%APPDATA%\claude-token-meter\status.json`; o widget faz poll (`status_poll_seconds`,
default 1s) e pinta a bolinha. O writer e `claude_token_meter/hooks.py`
(standalone, so stdlib — roda por caminho absoluto de qualquer cwd).

Hooks em `~/.claude/settings.json` (mapeamento):

| Evento do Claude Code | Estado | Bolinha |
|---|---|---|
| `UserPromptSubmit`, `PostToolUse` | `working` | vermelho |
| `Notification` | `waiting` | amarelo |
| `Stop` | `free` | verde |

Comando de cada hook: `py -3 "...\claude_token_meter\hooks.py" working|waiting|free`.

**Limitacoes conhecidas:** `PostToolUse` dispara por ferramenta (~150ms de Python
por chamada — e o que devolve o vermelho apos voce aprovar uma permissao); se
uma sessao morrer no meio do trabalho a bolinha fica vermelha ate a proxima
(nao ha heartbeat); varias sessoes simultaneas compartilham o mesmo `status.json`.

## Instancia unica

Uma so instancia por vez: no start, um named mutex do Windows (`ctypes`, em
`main.py`) barra instancias extras — relancar (`iniciar.bat`/autostart) sai em
vez de duplicar. Sem isto elas se acumulavam e cada uma consultava a API de
uso, estourando o rate limit (429 -> "aguardando" em vez do %). O check roda
ANTES do `QApplication` de proposito: um app ja construido segura o processo
vivo mesmo apos o `return`.

**Cada instancia aparece como 2 processos `pythonw.exe`** no Gerenciador de
Tarefas: o `.venv\Scripts\pythonw.exe` e so um lancador que abre o Python real
como filho. Dois processos pai/filho nao sao duas instancias.

Config em `%APPDATA%\claude-token-meter\config.json` (intervalo de refresh,
thresholds de cor, caminho do credentials). `window.x/y` sobra de quando a
barra ficava na tela e nao e mais usado.

## Privacidade

O medidor le o token OAuth de `~/.claude/.credentials.json` e o envia apenas
para `api.anthropic.com` (o mesmo destino do proprio Claude Code), via HTTPS,
so no header Authorization. Nada e gravado nem enviado pra outro lugar.
