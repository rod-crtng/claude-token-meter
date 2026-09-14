# Medidor na bandeja do Windows + reset semanal — design

**Data:** 2026-09-14 · **Decisões do Rod:** barra some e abre por clique no ícone · ícone mostra o
% da sessão colorido · reset semanal em dias e horas · PR pro upstream só depois de uso real.
Caminho escolhido: **A — a barra atual vira o popup do ícone** (descartados: barra dentro do menu
da bandeja; janela nova só pro popup).

## O que

1. O medidor passa a morar na **bandeja do sistema** (área de notificação, ao lado do relógio).
   No Windows 11 ícone novo cai na área recolhida da setinha `^` por padrão; o usuário pode
   arrastá-lo pra área sempre visível.
2. A barra flutuante **deixa de ficar sempre na tela**: vira um popup que abre com clique esquerdo
   no ícone e some ao clicar fora.
3. O **reset semanal** (`seven_day.resets_at`, que o `usage_client` já traz em
   `weekly_reset_at`) passa a aparecer — hoje só o % semanal aparece.

## Base

Antes de tudo, integrar o commit `d090efc` do upstream (instância única via named mutex). Em
14/09 havia duas instâncias rodando — exatamente o defeito que ele corrige.

## Componentes

### `labels.py` (novo · lógica pura · testado)

- `format_remaining(delta: timedelta) -> str`
  - `>= 24h` → `1d22h` (dias + horas, horas sem zero à esquerda)
  - `>= 1h` → `22h15` (minutos com dois dígitos)
  - `< 1h` → `40m` · negativo → `0m`
  - arredonda pra baixo (minutos inteiros), como o `_reset_label` atual
- `reset_moment(dt_utc: datetime) -> str` → `qua 16/09 07:00` no fuso local do PC
  (`astimezone()`), dia da semana abreviado em português (`seg ter qua qui sex sáb dom`).
  Não usa o `timezone` do config: `zoneinfo` no Windows depende do pacote `tzdata`, que não é
  dependência do projeto.
- `bar_label(snap, now) -> str` → texto do popup:
  - ok com semanal: `4%  reset 4h28 · sem 72% 1d22h`
  - ok sem semanal: `4%  reset 4h28`
  - ok sem `reset_at`: omite o trecho `reset …` correspondente
  - sem dado: a palavra de estado atual (`expirado`, `offline`, `erro`, `aguardando`) ou `--`
- `tooltip_text(snap, now) -> str` → texto do mouse sobre o ícone:
  - `Sessão 4% · reset 4h28` + quebra + `Semanal 72% · reset 1d22h (qua 16/09 07:00)`
  - sem dado: a frase de estado atual (`Token expirado — rode o Claude Code pra renovar` etc.)
  - cabe no limite de 127 caracteres do tooltip de bandeja do Windows
- `icon_spec(snap, thresholds) -> (texto, cor)`:
  - ok: `str(int(pct*100))` na cor da régua — `RED` se `pct >= red`, senão `AMBER` se
    `pct >= amber`, senão `GREEN` (mesma regra do `_color` atual)
  - ok com `pct >= 1.0`: `!!` em `RED` (três dígitos não cabem em 16 px)
  - sem dado ou `None`: `--` em `MUTED`
  - as cores são strings hex; o Qt só entra na camada de apresentação

- `pct_int(pct) -> int`: `int(pct * 100 + 1e-9)`. Corrige um defeito que já existe: `int(0.29 * 100)`
  dá `28` no Python, então o medidor mostrava 1 ponto a menos em alguns valores.
- `tooltip_text(None, …)` → `""` (antes do primeiro tick).

As constantes de palavra/frase de estado (`_STATUS_WORD`, `_STATUS_TIP`) e as cores migram do
`widget.py` pra cá, pra lógica e apresentação lerem da mesma fonte.

### `tray.py` (novo · apresentação fina · sem teste unitário)

- `render_icon(texto, cor) -> QIcon`: pixmaps 16, 20, 24 e 32 px, fundo escuro arredondado (`BG`),
  número em Segoe UI Bold na cor dada, centralizado.
- `MeterTray(QSystemTrayIcon)`:
  - `update_snapshot(snap)` → ícone + tooltip via `labels`
  - clique esquerdo (`Trigger`) → alterna o popup, posicionado pela posição do cursor
  - **anti-reabertura:** com o popup aberto, o clique no ícone chega primeiro como "clique fora"
    (o `Qt.Popup` se fecha) e logo depois como `Trigger`. Sem guarda, o popup reabriria na hora.
    O widget registra o instante em que se escondeu; `Trigger` a menos de 300 ms disso não reabre.
    A decisão (`should_open(agora, escondido_em)`) mora em `labels.py` e é testada.
  - clique direito → menu: `Iniciar com o Windows` (checável, como hoje) · separador · `Sair`

### `widget.py` (vira o popup)

- Flags `Qt.Popup | Qt.FramelessWindowHint`: some sozinho ao clicar fora.
- Sai o arraste, o menu de contexto e a imunidade a `closeEvent` (o que é persistente agora é o
  ícone, não a janela).
- Texto da linha de cima via `labels.bar_label`; barras e bolinhas iguais.
- Largura: `WIDTH` sobe só se o texto com semanal não couber na faixa à esquerda das bolinhas —
  medido com `QFontMetrics` no teste visual.
- `show_near(pos, screen_rect)`: canto inferior do popup 8 px acima do ponto, centralizado no x,
  preso dentro de `availableGeometry` da tela do cursor.

### `main.py`

- `_acquire_singleton()` do upstream mantido.
- Cria `MeterWidget` (escondido) e `MeterTray`; `tick()` atualiza os dois.
- `status_tick()` só lê o `status.json` e atualiza as bolinhas; **sai o vigia** de janela sumida e
  fora da tela — escondido passa a ser o estado normal. O Qt reinsere o ícone sozinho se o
  Explorer reiniciar (mensagem `TaskbarCreated`).
- `window.x/y` do config deixa de ser lido ou gravado (fica no arquivo, sem efeito, sem migração).

## Dados e erros

Igual a hoje: uma consulta a cada `refresh_seconds` (60), mantendo o último valor bom em
`offline`/`ratelimited`. Cada consulta atualiza ícone, tooltip e popup juntos. Zero chamada extra.

## Testes

- `tests/test_labels.py` (TDD, antes do código): os formatos de `format_remaining` nas fronteiras
  (0, 59 min, 60 min, 23h59, 24h, 1d22h15), `reset_moment` com dia da semana e fuso fixado no
  teste, `bar_label` e `tooltip_text` nos estados ok / sem semanal / sem dado, `icon_spec` nas
  fronteiras da régua e em 100%.
- `tests/test_widget_quit.py` → o "Sair" e o checkmark do autostart passam a ser testados no menu
  do `MeterTray` (offscreen), mantendo a regressão do bug do "Sair" que não encerrava.
- Suíte inteira verde.
- Verificação visual: relançar e tirar print da bandeja aberta (ícone legível em 16 px) e do
  popup (texto com semanal inteiro, barras e bolinhas intactas).

## O que NÃO muda

`usage_client.py`, `status.py`, `hooks.py`, `config.py`, `autostart.py`, os hooks do Claude Code
e o atalho da Inicialização (mesmo ponto de entrada `-m claude_token_meter.main`).

## Entrega

Commits pequenos na `main` local → push no fork `rod-crtng`. PR pro `angelolmcorrea` só depois de
o Rod usar alguns dias. README ganha a seção da bandeja no mesmo PR.
