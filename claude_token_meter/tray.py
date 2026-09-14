import time
from datetime import datetime, timezone

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QCursor, QFont, QGuiApplication, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from claude_token_meter import labels

_BG = QColor(20, 22, 26, 235)
_SIZES = (16, 20, 24, 32)  # 100% / 125% / 150% / 200% de escala do Windows


def render_icon(text: str, color: str) -> QIcon:
    """Numero (ou '--'/'!!') sobre fundo escuro arredondado, um pixmap por escala."""
    icon = QIcon()
    for size in _SIZES:
        pm = QPixmap(size, size)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(_BG)
        p.drawRoundedRect(QRectF(0, 0, size, size), size * 0.2, size * 0.2)
        font = QFont("Segoe UI")
        font.setBold(True)
        font.setPixelSize(max(8, round(size * 0.66)))
        p.setFont(font)
        p.setPen(QColor(color))
        p.drawText(QRectF(0, 0, size, size), Qt.AlignCenter, text)
        p.end()
        icon.addPixmap(pm)
    return icon


class MeterTray(QSystemTrayIcon):
    """Icone da bandeja: mostra o % da sessao, tooltip com sessao + semanal,
    clique esquerdo abre/fecha o popup, clique direito abre o menu."""

    def __init__(self, config, popup, on_quit, on_toggle_autostart,
                 is_autostart_enabled=None):
        super().__init__()
        self._config = config
        self._popup = popup
        self._is_autostart_enabled = is_autostart_enabled
        self._last_icon = None

        self._menu = QMenu()
        self._act_autostart = self._menu.addAction(
            "Iniciar com o Windows", on_toggle_autostart
        )
        if is_autostart_enabled is not None:
            # checkable pra dar feedback do estado atual
            self._act_autostart.setCheckable(True)
        self._menu.addSeparator()
        self._menu.addAction("Sair", on_quit)
        self._menu.aboutToShow.connect(self._sync_menu)
        self.setContextMenu(self._menu)

        self.activated.connect(self._on_activated)
        self.update_snapshot(None)

    def _sync_menu(self):
        if self._is_autostart_enabled is not None:
            self._act_autostart.setChecked(bool(self._is_autostart_enabled()))

    def update_snapshot(self, snapshot):
        spec = labels.icon_spec(snapshot, self._config["thresholds"])
        if spec != self._last_icon:
            self.setIcon(render_icon(*spec))
            self._last_icon = spec
        self.setToolTip(labels.tooltip_text(snapshot, datetime.now(timezone.utc)))

    def _on_activated(self, reason):
        if reason != QSystemTrayIcon.Trigger:
            return
        if self._popup.isVisible():
            self._popup.hide()
            return
        if not labels.should_open(int(time.monotonic() * 1000), self._popup.hidden_at_ms):
            return
        pos = QCursor.pos()
        screen = QGuiApplication.screenAt(pos) or QGuiApplication.primaryScreen()
        g = screen.availableGeometry()
        self._popup.show_near((pos.x(), pos.y()), (g.x(), g.y(), g.width(), g.height()))
