"""Icone da bandeja: 'Sair' encerra o app (regressao do bug antigo em que o
Sair nao encerrava), checkmark do autostart, clique abre/fecha o popup e a
guarda que impede reabrir no mesmo clique que fechou.
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import time

import pytest
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QSystemTrayIcon

from claude_token_meter.tray import MeterTray, render_icon
from claude_token_meter.widget import MeterWidget

CONFIG = {
    "thresholds": {"amber": 0.6, "red": 0.85},
    "window": {"opacity": 0.92},
}


@pytest.fixture
def app():
    a = QApplication.instance() or QApplication([])
    a.setQuitOnLastWindowClosed(False)
    return a


def _action(tray, prefix):
    return next(a for a in tray.contextMenu().actions() if a.text().startswith(prefix))


def test_sair_encerra_o_app(app):
    tray = MeterTray(CONFIG, MeterWidget(CONFIG), app.quit, lambda: None)
    QTimer.singleShot(10, _action(tray, "Sair").trigger)
    # rede de seguranca: se travar (bug), forca saida com codigo != 0
    QTimer.singleShot(2000, lambda: app.exit(99))
    assert app.exec() == 0, "o 'Sair' nao encerrou o app"


def test_autostart_item_reflete_estado(app):
    estado = {"on": True}
    tray = MeterTray(
        CONFIG, MeterWidget(CONFIG), app.quit, lambda: None,
        is_autostart_enabled=lambda: estado["on"],
    )
    act = _action(tray, "Iniciar")
    tray.contextMenu().aboutToShow.emit()
    assert act.isCheckable() is True
    assert act.isChecked() is True
    estado["on"] = False
    tray.contextMenu().aboutToShow.emit()
    assert act.isChecked() is False


def test_clique_abre_e_fecha_o_popup(app):
    popup = MeterWidget(CONFIG)
    tray = MeterTray(CONFIG, popup, app.quit, lambda: None)
    tray._on_activated(QSystemTrayIcon.Trigger)
    assert popup.isVisible()
    tray._on_activated(QSystemTrayIcon.Trigger)
    assert not popup.isVisible()


def test_clique_logo_apos_fechar_nao_reabre(app):
    popup = MeterWidget(CONFIG)
    tray = MeterTray(CONFIG, popup, app.quit, lambda: None)
    popup.hidden_at_ms = int(time.monotonic() * 1000)  # acabou de fechar por clique fora
    tray._on_activated(QSystemTrayIcon.Trigger)
    assert not popup.isVisible()


def test_render_icon_tem_os_tamanhos_da_bandeja(app):
    icon = render_icon("72", "#D29922")
    tamanhos = {(s.width(), s.height()) for s in icon.availableSizes()}
    assert {(16, 16), (20, 20), (24, 24), (32, 32)} <= tamanhos
