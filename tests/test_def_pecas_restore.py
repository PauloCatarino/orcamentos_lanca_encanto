import unittest

from Martelo_Orcamentos_V2.app.services import def_pecas as svc_def_pecas


class DefPecasRestoreTests(unittest.TestCase):
    def test_merge_restores_missing_rows_and_preserves_existing_mat_default(self):
        base_rows = [
            {
                "id": "1",
                "tipo_peca_principal": "COSTAS",
                "subgrupo_peca": None,
                "nome_da_peca": "COSTA CHAPAR [0000]",
                "cp01_sec": "1",
            },
            {
                "id": "2",
                "tipo_peca_principal": "FERRAGENS",
                "subgrupo_peca": "DOBRADICAS",
                "nome_da_peca": "DOBRADICA RETA",
                "cp01_sec": "0",
            },
        ]
        existing_rows = [
            {
                "id": 99,
                "tipo_peca_principal": "FERRAGENS",
                "subgrupo_peca": "DOBRADICAS",
                "nome_da_peca": "DOBRADICA RETA",
                "mat_default_origem": "ferragens",
                "mat_default_grupos": "Dobradica Reta; Dobradica Canto Sego",
                "mat_default_default": "Dobradica Reta",
                "cp01_sec": 3.0,
            }
        ]

        merged = svc_def_pecas.fundir_definicoes_com_base(base_rows, existing_rows)

        self.assertEqual(2, len(merged))
        by_name = {row["nome_da_peca"]: row for row in merged}
        self.assertIn("COSTA CHAPAR [0000]", by_name)
        self.assertIn("DOBRADICA RETA", by_name)
        self.assertEqual("ferragens", by_name["DOBRADICA RETA"]["mat_default_origem"])
        self.assertEqual("Dobradica Reta", by_name["DOBRADICA RETA"]["mat_default_default"])
        self.assertEqual("1", by_name["COSTA CHAPAR [0000]"]["id"])
        self.assertEqual("2", by_name["DOBRADICA RETA"]["id"])

    def test_merge_preserves_extra_existing_rows_not_in_base(self):
        base_rows = [
            {"id": "1", "nome_da_peca": "COSTA CHAPAR [0000]"},
        ]
        existing_rows = [
            {"id": 99, "nome_da_peca": "PECA ESPECIAL UTILIZADOR", "tipo_peca_principal": "SERVICOS"},
        ]

        merged = svc_def_pecas.fundir_definicoes_com_base(base_rows, existing_rows)

        nomes = [row["nome_da_peca"] for row in merged]
        self.assertIn("COSTA CHAPAR [0000]", nomes)
        self.assertIn("PECA ESPECIAL UTILIZADOR", nomes)


if __name__ == "__main__":
    unittest.main()
