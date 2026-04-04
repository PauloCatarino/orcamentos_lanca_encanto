from __future__ import annotations

import unittest

from Martelo_Orcamentos_V2.app.services import modulos


class ModulosTraceTests(unittest.TestCase):
    def test_construir_registos_importacao_modulos_normaliza_campos(self) -> None:
        timestamp = "2026-04-03T12:30:00+01:00"

        registos = modulos.construir_registos_importacao_modulos(
            [
                {
                    "modulo_id": "7",
                    "nome": "REF | 1 Porta + 5 Prateleiras",
                    "scope": "global",
                    "linhas_importadas": "5",
                }
            ],
            imported_at=timestamp,
        )

        self.assertEqual(
            registos,
            [
                {
                    "modulo_id": 7,
                    "nome": "REF | 1 Porta + 5 Prateleiras",
                    "scope": "global",
                    "linhas_importadas": 5,
                    "importado_em": timestamp,
                }
            ],
        )

    def test_anexar_registos_importacao_modulos_preserva_outros_extras(self) -> None:
        timestamp_1 = "2026-04-01T09:15:00+01:00"
        timestamp_2 = "2026-04-03T12:30:00+01:00"
        extras = {
            "outra": "info",
            "modulos_importados": [
                {
                    "modulo_id": 1,
                    "nome": "REF | Base",
                    "scope": "global",
                    "linhas_importadas": 4,
                    "importado_em": timestamp_1,
                }
            ],
        }

        merged = modulos.anexar_registos_importacao_modulos(
            extras,
            [
                {
                    "modulo_id": 2,
                    "nome": "REF | Complemento",
                    "scope": "user",
                    "linhas_importadas": 2,
                    "importado_em": timestamp_2,
                }
            ],
        )

        self.assertEqual(merged["outra"], "info")
        self.assertEqual(len(merged["modulos_importados"]), 2)
        self.assertEqual(merged["modulos_importados"][0]["importado_em"], timestamp_1)
        self.assertEqual(merged["modulos_importados"][1]["importado_em"], timestamp_2)

    def test_resumo_e_tooltip_agregam_importacoes_repetidas(self) -> None:
        registos = [
            {
                "modulo_id": 1,
                "nome": "REF | 1 Porta + 5 Prateleiras",
                "scope": "global",
                "linhas_importadas": 5,
                "importado_em": "2026-04-03T12:30:00+01:00",
            },
            {
                "modulo_id": 1,
                "nome": "REF | 1 Porta + 5 Prateleiras",
                "scope": "global",
                "linhas_importadas": 5,
                "importado_em": "2026-04-03T12:45:00+01:00",
            },
            {
                "modulo_id": 2,
                "nome": "REF | Sistema de Correr",
                "scope": "user",
                "linhas_importadas": 4,
                "importado_em": "2026-04-03T13:00:00+01:00",
            },
        ]

        resumo = modulos.resumir_registos_importacao_modulos(registos, max_names=3)
        tooltip = modulos.formatar_registos_importacao_modulos_tooltip(registos)

        self.assertEqual(resumo, "REF | 1 Porta + 5 Prateleiras (2x), REF | Sistema de Correr")
        self.assertIn("Global", tooltip)
        self.assertIn("Utilizador", tooltip)
        self.assertIn("03-04-2026 12:30", tooltip)


if __name__ == "__main__":
    unittest.main()
