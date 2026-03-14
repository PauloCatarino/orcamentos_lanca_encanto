import unittest
from types import SimpleNamespace

from Martelo_Orcamentos_V2.ui.pages.producao_table_support import (
    build_producao_table_rows,
    build_search_status_text,
    normalize_filter_text,
)


class ProducaoTableSupportTests(unittest.TestCase):
    def test_normalize_filter_text_maps_todos_to_empty(self):
        self.assertEqual(normalize_filter_text("Todos"), "")
        self.assertEqual(normalize_filter_text(" Paulo "), "Paulo")

    def test_build_search_status_text_only_shows_when_search_has_no_rows(self):
        self.assertEqual(build_search_status_text(search="abc", has_rows=False), "Texto pesquisado nao foi encontrado nos dados registados.")
        self.assertEqual(build_search_status_text(search="", has_rows=False), "")
        self.assertEqual(build_search_status_text(search="abc", has_rows=True), "")

    def test_build_producao_table_rows_collects_sorted_filter_values(self):
        rows = [
            SimpleNamespace(
                id=1,
                ano="2026",
                estado="Planeamento",
                responsavel="Paulo",
                codigo_processo="P1",
                num_enc_phc="001",
                versao_obra="01",
                versao_plano="01",
                nome_cliente="Beta",
                ref_cliente="R1",
                obra="O1",
                data_inicio="2026-01-01",
                data_entrega="2026-01-02",
                qt_artigos=1,
                preco_total=10,
                descricao_producao="D1",
            ),
            SimpleNamespace(
                id=2,
                ano="2026",
                estado="Producao",
                responsavel="Andreia",
                codigo_processo="P2",
                num_enc_phc="002",
                versao_obra="01",
                versao_plano="02",
                nome_cliente="ACME",
                ref_cliente="R2",
                obra="O2",
                data_inicio="2026-01-03",
                data_entrega="2026-01-04",
                qt_artigos=2,
                preco_total=20,
                descricao_producao="D2",
            ),
        ]

        data, clientes, responsaveis = build_producao_table_rows(rows)

        self.assertEqual(len(data), 2)
        self.assertEqual(clientes, ["ACME", "Beta"])
        self.assertEqual(responsaveis, ["Andreia", "Paulo"])


if __name__ == "__main__":
    unittest.main()
