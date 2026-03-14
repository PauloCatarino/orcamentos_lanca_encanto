import unittest
from pathlib import Path

from Martelo_Orcamentos_V2.ui.pages.producao_actions_support import (
    build_lista_material_imos_values,
    build_processo_delete_ui_plan,
    normalize_tipo_pasta_text,
)


class ProducaoActionsSupportTests(unittest.TestCase):
    def test_normalize_tipo_pasta_text_returns_none_for_blank(self):
        self.assertIsNone(normalize_tipo_pasta_text("  "))
        self.assertEqual(normalize_tipo_pasta_text(" Encomenda "), "Encomenda")

    def test_build_lista_material_imos_values_trims_all_fields(self):
        values = build_lista_material_imos_values(
            responsavel=" Paulo ",
            ref_cliente=" REF ",
            obra=" Obra ",
            nome_enc_imos_ix=" ENC ",
            num_cliente_phc=" 123 ",
            nome_cliente=" Cliente ",
            nome_cliente_simplex=" CLI ",
            localizacao=" Local ",
            descricao_producao=" Producao ",
            descricao_artigos=" Artigos ",
            materias=" Mat ",
            qtd=" 4 ",
            plano_corte=" Plano ",
            data_conclusao=" 2026-03-07 ",
            data_inicio=" 2026-03-01 ",
            enc_phc=" 0417 ",
        )

        self.assertEqual(values["RESPONSAVEL"], "Paulo")
        self.assertEqual(values["QTD"], "4")
        self.assertEqual(values["ENC_PHC"], "0417")

    def test_build_processo_delete_ui_plan_includes_folder_messages_when_needed(self):
        plan = build_processo_delete_ui_plan(
            info_text="26.0417_01_01 - CLIENTE",
            folder=Path(r"C:\Obras\26.0417_01_01"),
            delete_folder=True,
            folder_preview_text="ficheiro.pdf",
        )

        self.assertIsNotNone(plan.folder_confirmation_text)
        self.assertIn("ficheiro.pdf", plan.folder_confirmation_text)
        self.assertIn("C:\\Obras\\26.0417_01_01", plan.db_confirmation_text)

    def test_build_processo_delete_ui_plan_skips_folder_section_for_db_only(self):
        plan = build_processo_delete_ui_plan(
            info_text="26.0417_01_01 - CLIENTE",
            folder=None,
            delete_folder=False,
            folder_preview_text="",
        )

        self.assertIsNone(plan.folder_confirmation_text)
        self.assertNotIn("A pasta tambem sera apagada", plan.db_confirmation_text)


if __name__ == "__main__":
    unittest.main()
