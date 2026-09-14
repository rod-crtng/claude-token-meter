import time
from datetime import datetime, timezone

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QPainter, QBrush, QFont
from PySide6.QtWidgets import QWidget

from claude_token_meter import geometry as geo
from claude_token_meter import labels

WIDTH, HEIGHT = 300, 42
GREEN = QColor(labels.GREEN)
AMBER = QColor(labels.AMBER)
RED = QColor(labels.RED)
BG = QColor(20, 22, 26, 235)
TRACK = QColor(255, 255, 255, 28)
TEXT = QColor("#E6EDF3")
MUTED = QColor(labels.MUTED)

# bolinhas de estado da sessao (estilo controles de janela do macOS):
# vermelho=trabalhando, amarelo=aguardando confirmacao, verde=livre.
_DOT_R = 3.5           # raio
_DOT_GAP = 11.0        # distancia entre centros
_DOT_RIGHT = 10.0      # margem a direita ate o centro do ultimo dot
_DOT_DIM_ALPHA = 60    # alpha dos dots inativos
_STATE_COLOR = {"working": RED, "waiting": AMBER, "free": GREEN}


class MeterWidget(QWidget):
    """A barra do medidor como popup do icone da bandeja: abre por clique no
    icone e some sozinha ao clicar fora (Qt.Popup). Sem logica: textos e cores
    vem de labels."""

    def __init__(self, config):
        super().__init__()
        self._config = config
        self._snapshot = None
        self._status = None  # "working" | "waiting" | "free" | None
        self.hidden_at_ms = None  # monotonic (ms) do ultimo hide; ver labels.should_open

        self.setWindowFlags(
            Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(WIDTH, HEIGHT)
        self.setWindowOpacity(config["window"].get("opacity", 0.92))

    def update_snapshot(self, snapshot):
        self._snapshot = snapshot
        self.update()  # trigger repaint

    def update_status(self, state):
        if state != self._status:
            self._status = state
            self.update()

    def show_near(self, anchor, screen_rect):
        x, y = geo.popup_pos(anchor, self.width(), self.height(), screen_rect)
        self.move(x, y)
        self.show()

    def hideEvent(self, e):
        self.hidden_at_ms = int(time.monotonic() * 1000)
        super().hideEvent(e)

    def _color(self, pct):
        return QColor(labels.color_for(pct, self._config["thresholds"]))

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(0, 0, WIDTH, HEIGHT)
        p.setBrush(QBrush(BG))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(rect, 8, 8)

        snap = self._snapshot
        now = datetime.now(timezone.utc)
        ok = bool(snap and snap.status == "ok")
        pct = snap.pct if ok else 0.0
        weekly = snap.weekly_pct if ok else None

        # barra da sessao (5px) + barra da semana (3.5px, mais fina de proposito)
        bar = QRectF(8, HEIGHT - 19, WIDTH - 16, 5)
        p.setBrush(QBrush(TRACK))
        p.drawRoundedRect(bar, 2.5, 2.5)
        if pct > 0:
            fill = QRectF(bar.x(), bar.y(), bar.width() * pct, bar.height())
            p.setBrush(QBrush(self._color(pct)))
            p.drawRoundedRect(fill, 2.5, 2.5)

        wbar = QRectF(8, HEIGHT - 10, WIDTH - 16, 3.5)
        p.setBrush(QBrush(TRACK))
        p.drawRoundedRect(wbar, 1.75, 1.75)
        if weekly:
            wfill = QRectF(wbar.x(), wbar.y(), wbar.width() * weekly, wbar.height())
            p.setBrush(QBrush(self._color(weekly)))
            p.drawRoundedRect(wfill, 1.75, 1.75)

        p.setPen(TEXT if ok else MUTED)
        p.setFont(QFont("Segoe UI", 9, QFont.DemiBold))
        # reserva a faixa da direita pras 3 bolinhas
        dots_span = _DOT_GAP * 2 + _DOT_R * 2 + _DOT_RIGHT + 6
        p.drawText(
            QRectF(10, 3, WIDTH - 10 - dots_span, 16),
            Qt.AlignLeft | Qt.AlignVCenter,
            labels.bar_label(snap, now),
        )
        self._draw_status_dots(p)

    def _draw_status_dots(self, p):
        cy = 10.5
        # da direita pra esquerda: verde, amarelo, vermelho (ordem macOS invertida)
        cx_right = WIDTH - _DOT_RIGHT
        order = ("working", "waiting", "free")  # esquerda -> direita
        cxs = [cx_right - _DOT_GAP * (2 - i) for i in range(3)]
        p.setPen(Qt.NoPen)
        for state, cx in zip(order, cxs):
            base = _STATE_COLOR[state]
            if state == self._status:
                col = base
            else:
                col = QColor(base)
                col.setAlpha(_DOT_DIM_ALPHA)
            p.setBrush(QBrush(col))
            p.drawEllipse(QRectF(cx - _DOT_R, cy - _DOT_R, _DOT_R * 2, _DOT_R * 2))
