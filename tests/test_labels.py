from datetime import datetime, timedelta, timezone

from claude_token_meter import labels

BRT = timezone(timedelta(hours=-3))


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
