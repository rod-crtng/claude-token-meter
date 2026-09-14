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
