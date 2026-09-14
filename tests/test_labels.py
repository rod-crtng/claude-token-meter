from datetime import datetime, timedelta, timezone

from claude_token_meter import labels
from claude_token_meter.usage_client import UsageSnapshot

BRT = timezone(timedelta(hours=-3))
NOW = datetime(2026, 9, 14, 11, 44, tzinfo=timezone.utc)
TH = {"amber": 0.6, "red": 0.85}


def snap(pct=0.04, reset_min=268, weekly=0.72, weekly_min=2776, status="ok"):
    # 268 min = 4h28 · 2776 min depois de NOW = qua 16/09 10:00 UTC = 07:00 BRT
    return UsageSnapshot(
        pct=pct,
        reset_at=None if reset_min is None else NOW + timedelta(minutes=reset_min),
        weekly_pct=weekly,
        weekly_reset_at=None if weekly_min is None else NOW + timedelta(minutes=weekly_min),
        status=status,
    )


def sem_dado(status):
    return UsageSnapshot(0.0, None, None, None, status)


def test_remaining_zero_e_segundos_viram_0m():
    assert labels.format_remaining(timedelta(0)) == "0m"
    assert labels.format_remaining(timedelta(seconds=59)) == "0m"


def test_remaining_negativo_vira_0m():
    assert labels.format_remaining(timedelta(minutes=-5)) == "0m"


def test_remaining_abaixo_de_1h_em_minutos():
    assert labels.format_remaining(timedelta(minutes=59)) == "59m"


def test_remaining_horas_com_minutos_em_dois_digitos():
    assert labels.format_remaining(timedelta(minutes=60)) == "1h00"
    assert labels.format_remaining(timedelta(minutes=268)) == "4h28"
    assert labels.format_remaining(timedelta(hours=23, minutes=59)) == "23h59"


def test_remaining_24h_ou_mais_em_dias_e_horas():
    assert labels.format_remaining(timedelta(hours=24)) == "1d0h"
    assert labels.format_remaining(timedelta(minutes=2776)) == "1d22h"
    assert labels.format_remaining(timedelta(days=6, hours=23, minutes=59)) == "6d23h"


def test_reset_moment_dia_da_semana_em_portugues_no_fuso_dado():
    utc = timezone.utc
    assert labels.reset_moment(datetime(2026, 9, 16, 10, 0, tzinfo=utc), BRT) == "qua 16/09 07:00"
    assert labels.reset_moment(datetime(2026, 9, 20, 2, 30, tzinfo=utc), BRT) == "sáb 19/09 23:30"
    assert labels.reset_moment(datetime(2026, 9, 20, 12, 0, tzinfo=utc), BRT) == "dom 20/09 09:00"


def test_pct_nao_perde_1_ponto_por_float():
    # int(0.29 * 100) == 28 no Python; o medidor precisa mostrar 29
    assert labels.pct_int(0.29) == 29
    assert labels.pct_int(0.57) == 57
    assert labels.pct_int(1.0) == 100


def test_color_for_segue_a_regua():
    assert labels.color_for(0.59, TH) == labels.GREEN
    assert labels.color_for(0.60, TH) == labels.AMBER
    assert labels.color_for(0.85, TH) == labels.RED


def test_bar_label_completo():
    assert labels.bar_label(snap(), NOW) == "4%  reset 4h28 · sem 72% 1d22h"


def test_bar_label_sem_semanal():
    assert labels.bar_label(snap(weekly=None, weekly_min=None), NOW) == "4%  reset 4h28"


def test_bar_label_sem_reset_da_sessao():
    assert labels.bar_label(snap(reset_min=None), NOW) == "4% · sem 72% 1d22h"


def test_bar_label_semanal_sem_data_de_reset():
    assert labels.bar_label(snap(weekly_min=None), NOW) == "4%  reset 4h28 · sem 72%"


def test_bar_label_sem_dado():
    assert labels.bar_label(None, NOW) == "--"
    assert labels.bar_label(sem_dado("auth"), NOW) == "expirado"
    assert labels.bar_label(sem_dado("ratelimited"), NOW) == "aguardando"
    assert labels.bar_label(sem_dado("xyz"), NOW) == "--"


def test_tooltip_completo():
    assert labels.tooltip_text(snap(), NOW, BRT) == (
        "Sessão 4% · reset 4h28\nSemanal 72% · reset 1d22h (qua 16/09 07:00)"
    )


def test_tooltip_sem_semanal():
    assert labels.tooltip_text(snap(weekly=None, weekly_min=None), NOW, BRT) == "Sessão 4% · reset 4h28"


def test_tooltip_sem_dado():
    assert labels.tooltip_text(None, NOW, BRT) == ""
    assert labels.tooltip_text(sem_dado("auth"), NOW, BRT) == (
        "Token expirado — rode o Claude Code pra renovar"
    )
    assert labels.tooltip_text(sem_dado("xyz"), NOW, BRT) == "Erro ao consultar o uso"


def test_tooltip_cabe_no_limite_do_windows():
    pior = snap(pct=1.0, reset_min=299, weekly=1.0, weekly_min=6 * 1440 + 23 * 60 + 59)
    assert len(labels.tooltip_text(pior, NOW, BRT)) <= 127


def test_icon_spec_numero_na_cor_da_regua():
    assert labels.icon_spec(snap(pct=0.04), TH) == ("4", labels.GREEN)
    assert labels.icon_spec(snap(pct=0.29), TH) == ("29", labels.GREEN)
    assert labels.icon_spec(snap(pct=0.60), TH) == ("60", labels.AMBER)
    assert labels.icon_spec(snap(pct=0.85), TH) == ("85", labels.RED)
    assert labels.icon_spec(snap(pct=0.999), TH) == ("99", labels.RED)


def test_icon_spec_100_e_sem_dado():
    assert labels.icon_spec(snap(pct=1.0), TH) == ("!!", labels.RED)
    assert labels.icon_spec(sem_dado("offline"), TH) == ("--", labels.MUTED)
    assert labels.icon_spec(None, TH) == ("--", labels.MUTED)


def test_should_open_guarda_300ms_depois_de_esconder():
    assert labels.should_open(1000, None) is True
    assert labels.should_open(1000, 800) is False
    assert labels.should_open(1100, 800) is True
    assert labels.should_open(5000, 800) is True
