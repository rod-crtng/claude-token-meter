from claude_token_meter.geometry import fallback_pos, popup_pos, rect_visible

PRIMARY = (0, 0, 1920, 1040)          # availableGeometry da tela primaria
SECOND_LEFT = (-1920, 0, 1920, 1040)  # monitor secundario a esquerda (coords negativas)


def test_rect_dentro_da_primaria_e_visivel():
    assert rect_visible((100, 100, 300, 34), [PRIMARY]) is True


def test_rect_no_monitor_negativo_e_visivel():
    # posicao real do widget do Rod: x=-695 (monitor da esquerda)
    assert rect_visible((-695, 596, 300, 34), [PRIMARY, SECOND_LEFT]) is True


def test_rect_no_monitor_negativo_some_quando_monitor_desliga():
    # mesmo rect, mas so a primaria presente -> fora de tela
    assert rect_visible((-695, 596, 300, 34), [PRIMARY]) is False


def test_rect_totalmente_fora_e_invisivel():
    assert rect_visible((5000, 5000, 300, 34), [PRIMARY]) is False


def test_sliver_menor_que_minimo_nao_conta_como_visivel():
    # so 4px dentro da tela (min_px default = 8)
    assert rect_visible((-296, 100, 300, 34), [PRIMARY]) is False


def test_borda_com_sobreposicao_suficiente_e_visivel():
    # 20px dentro da tela
    assert rect_visible((-280, 100, 300, 34), [PRIMARY]) is True


def test_fallback_cai_dentro_da_primeira_tela():
    x, y = fallback_pos([PRIMARY, SECOND_LEFT], 300, 34)
    assert rect_visible((x, y, 300, 34), [PRIMARY]) is True
    # canto superior direito, com margem
    assert x + 300 <= PRIMARY[0] + PRIMARY[2]
    assert y >= PRIMARY[1]


TELA_RODRIGO = (0, 0, 1920, 1032)  # availableGeometry real: barra de tarefas de 48 px embaixo


def test_popup_abre_acima_do_clique_e_centralizado():
    # clique no icone (y 1050, dentro da barra de tarefas): popup fica colado no limite util
    assert popup_pos((1650, 1050), 300, 42, TELA_RODRIGO) == (1500, 990)


def test_popup_nao_passa_da_borda_direita():
    x, _ = popup_pos((1910, 1050), 300, 42, TELA_RODRIGO)
    assert x == 1620


def test_popup_abre_abaixo_quando_a_barra_esta_em_cima():
    tela = (0, 48, 1920, 1032)
    assert popup_pos((1650, 20), 300, 42, tela) == (1500, 48)


def test_popup_em_monitor_de_coordenada_negativa():
    tela = (-1440, 0, 1440, 2512)
    assert popup_pos((-100, 2530), 300, 42, tela) == (-300, 2470)
