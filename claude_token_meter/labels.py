"""Textos e decisoes de exibicao do medidor (sem PySide6, pra ser testavel).

O widget (popup) e o icone da bandeja so desenham o que sai daqui.
"""
from datetime import datetime, timedelta, tzinfo

# weekday(): 0 = segunda
_DIAS = ("seg", "ter", "qua", "qui", "sex", "sáb", "dom")


def format_remaining(delta: timedelta) -> str:
    """Tempo ate o reset: 1d22h / 22h15 / 40m (arredonda pra baixo)."""
    mins = max(0, int(delta.total_seconds() // 60))
    if mins >= 24 * 60:
        return f"{mins // 1440}d{(mins % 1440) // 60}h"
    if mins >= 60:
        return f"{mins // 60}h{mins % 60:02d}"
    return f"{mins}m"


def reset_moment(dt: datetime, tz: tzinfo | None = None) -> str:
    """Momento do reset no fuso do PC (ou no tz dado): 'qua 16/09 07:00'.

    Nao usa zoneinfo: no Windows ele depende do pacote tzdata, que nao e
    dependencia do projeto. astimezone() sem tz usa o fuso do sistema.
    """
    local = dt.astimezone(tz)
    return f"{_DIAS[local.weekday()]} {local:%d/%m %H:%M}"


GREEN = "#3FB950"
AMBER = "#D29922"
RED = "#F85149"
MUTED = "#8B949E"

STATUS_WORD = {
    "auth": "expirado",
    "offline": "offline",
    "error": "erro",
    "ratelimited": "aguardando",
}
STATUS_TIP = {
    "auth": "Token expirado — rode o Claude Code pra renovar",
    "offline": "Sem conexao com a API de uso",
    "error": "Erro ao consultar o uso",
    "ratelimited": "A API limitou as consultas — tentando de novo em breve",
}

REOPEN_GUARD_MS = 300


def pct_int(pct: float) -> int:
    """0..1 -> inteiro de %. O epsilon evita int(0.29 * 100) == 28."""
    return int(pct * 100 + 1e-9)


def color_for(pct: float, thresholds: dict) -> str:
    if pct >= thresholds["red"]:
        return RED
    if pct >= thresholds["amber"]:
        return AMBER
    return GREEN


def bar_label(snap, now: datetime) -> str:
    """Linha de cima do popup: '4%  reset 4h28 · sem 72% 1d22h'."""
    if snap is None:
        return "--"
    if snap.status != "ok":
        return STATUS_WORD.get(snap.status, "--")
    sessao = f"{pct_int(snap.pct)}%"
    if snap.reset_at is not None:
        sessao += f"  reset {format_remaining(snap.reset_at - now)}"
    partes = [sessao]
    if snap.weekly_pct is not None:
        semana = f"sem {pct_int(snap.weekly_pct)}%"
        if snap.weekly_reset_at is not None:
            semana += f" {format_remaining(snap.weekly_reset_at - now)}"
        partes.append(semana)
    return " · ".join(partes)


def tooltip_text(snap, now: datetime, tz: tzinfo | None = None) -> str:
    """Texto do mouse sobre o icone (limite do Windows: 127 caracteres)."""
    if snap is None:
        return ""
    if snap.status != "ok":
        return STATUS_TIP.get(snap.status, STATUS_TIP["error"])
    sessao = f"Sessão {pct_int(snap.pct)}%"
    if snap.reset_at is not None:
        sessao += f" · reset {format_remaining(snap.reset_at - now)}"
    linhas = [sessao]
    if snap.weekly_pct is not None:
        semana = f"Semanal {pct_int(snap.weekly_pct)}%"
        if snap.weekly_reset_at is not None:
            semana += (
                f" · reset {format_remaining(snap.weekly_reset_at - now)}"
                f" ({reset_moment(snap.weekly_reset_at, tz)})"
            )
        linhas.append(semana)
    return "\n".join(linhas)


def icon_spec(snap, thresholds: dict) -> tuple[str, str]:
    """(texto, cor hex) do icone da bandeja. 3 digitos nao cabem em 16 px."""
    if snap is None or snap.status != "ok":
        return "--", MUTED
    if snap.pct >= 1.0:
        return "!!", RED
    return str(pct_int(snap.pct)), color_for(snap.pct, thresholds)


def should_open(now_ms: int, hidden_at_ms: int | None,
                guard_ms: int = REOPEN_GUARD_MS) -> bool:
    """Clique no icone com o popup aberto chega primeiro como 'clique fora'
    (o Qt.Popup fecha) e logo depois como Trigger: sem esta guarda, reabriria."""
    return hidden_at_ms is None or now_ms - hidden_at_ms >= guard_ms
