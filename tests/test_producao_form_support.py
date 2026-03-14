import unittest
from types import SimpleNamespace

from Martelo_Orcamentos_V2.ui.pages.producao_form_support import (
    build_empty_form_state,
    build_form_state_from_processo,
    build_processo_codigo_display,
    build_processo_form_payload,
)


class ProducaoFormSupportTests(unittest.TestCase):
    def test_build_processo_codigo_display_appends_suffix_when_needed(self):
        proc = SimpleNamespace(codigo_processo="PRC001", nome_cliente_simplex="CLIENTE_A", nome_cliente=None, ref_cliente=None)
        self.assertEqual(build_processo_codigo_display(proc), "PRC001_CLIENTE_A")

    def test_build_empty_form_state_sets_defaults(self):
        state = build_empty_form_state(current_year="2026", default_tipo_pasta="Encomenda", default_estado="Planeamento")
        self.assertEqual(state.ano, "2026")
        self.assertEqual(state.versao_obra, "01")
        self.assertEqual(state.tipo_pasta, "Encomenda")
        self.assertEqual(state.estado, "Planeamento")

    def test_build_form_state_from_processo_maps_fields(self):
        proc = SimpleNamespace(
            codigo_processo="P001",
            nome_cliente_simplex="CLI",
            nome_cliente="Cliente",
            ref_cliente="REF",
            ano="2026",
            num_enc_phc="123",
            versao_obra="01",
            versao_plano="02",
            responsavel="Paulo",
            estado="Planeamento",
            num_cliente_phc="1",
            num_orcamento="260001",
            versao_orc="01",
            obra="Obra",
            localizacao="Loc",
            descricao_orcamento="Desc",
            data_inicio="2026-01-01",
            data_entrega="2026-01-02",
            preco_total=10.5,
            qt_artigos=2,
            descricao_artigos="Artigos",
            descricao_producao="Prod",
            materias_usados="Mat",
            notas1="N1",
            notas2="N2",
            notas3="N3",
            pasta_servidor="C:\\Temp",
            tipo_pasta="Encomenda",
            imagem_path="img.png",
        )
        state = build_form_state_from_processo(proc, default_tipo_pasta="Default")
        self.assertEqual(state.codigo_display, "P001_CLI")
        self.assertEqual(state.qt_artigos_text, "2")
        self.assertEqual(state.pasta_servidor, "C:\\Temp")

    def test_build_processo_form_payload_parses_qt_artigos(self):
        payload = build_processo_form_payload(
            ano="2026",
            num_enc_phc="123",
            versao_obra="01",
            versao_plano="01",
            responsavel="Paulo",
            estado="Planeamento",
            nome_cliente="Cliente",
            nome_cliente_simplex="CLI",
            num_cliente_phc="1",
            ref_cliente="R",
            num_orcamento="260001",
            versao_orc="01",
            obra="Obra",
            localizacao="Loc",
            data_inicio="2026-01-01",
            data_entrega="2026-01-02",
            preco_total=11.2,
            qt_artigos_text="3",
            descricao_artigos="Desc",
            materias_usados="Mat",
            descricao_producao="Prod",
            notas1="A",
            notas2="B",
            notas3="C",
            pasta_servidor="P",
            tipo_pasta="Tipo",
            imagem_path=None,
        )
        self.assertEqual(payload["qt_artigos"], 3)
        self.assertEqual(payload["preco_total"], 11.2)


if __name__ == "__main__":
    unittest.main()
