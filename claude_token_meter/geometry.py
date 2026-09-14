"""Geometria pura da janela vs telas (sem PySide6, pra ser testavel).

rect_visible/fallback_pos existiram pro vigia da barra flutuante (widget que
sumia por WM_CLOSE de terceiros ou monitor desligado). Desde a bandeja a barra
e um popup e o vigia saiu; popup_pos posiciona o popup junto do clique.
"""

Rect = tuple[int, int, int, int]  # x, y, w, h


def rect_visible(rect: Rect, screens: list[Rect], min_px: int = 8) -> bool:
    """True se ao menos min_px x min_px do rect intersecta alguma tela."""
    x, y, w, h = rect
    for sx, sy, sw, sh in screens:
        ix = min(x + w, sx + sw) - max(x, sx)
        iy = min(y + h, sy + sh) - max(y, sy)
        if ix >= min_px and iy >= min_px:
            return True
    return False


def fallback_pos(screens: list[Rect], w: int, h: int, margin: int = 16) -> tuple[int, int]:
    """Posicao segura: canto superior direito da primeira tela (primaria)."""
    sx, sy, sw, sh = screens[0]
    return sx + sw - w - margin, sy + margin


def popup_pos(anchor: tuple[int, int], w: int, h: int, screen: Rect,
              gap: int = 8) -> tuple[int, int]:
    """Popup centrado no x do clique, acima dele (ou abaixo, se a barra de
    tarefas estiver em cima) e sempre inteiro dentro da area util da tela."""
    ax, ay = anchor
    sx, sy, sw, sh = screen
    x = ax - w // 2
    y = ay - gap - h
    if y < sy:
        y = ay + gap
    x = max(sx, min(x, sx + sw - w))
    y = max(sy, min(y, sy + sh - h))
    return x, y
