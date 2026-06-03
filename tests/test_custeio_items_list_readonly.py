from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from Martelo_Orcamentos_V2.app.services import custeio_items


class _ScalarResult:
    def __init__(self, values):
        self._values = list(values)

    def scalars(self):
        return self

    def all(self):
        return list(self._values)


class CusteioItemsListReadonlyTests(unittest.TestCase):
    def test_listar_custeio_items_does_not_persist_recalculos(self) -> None:
        session = MagicMock()
        registro = SimpleNamespace(
            id=190028,
            def_peca="LATERAL ACABAMENTO [2222]",
            orl_c1=1,
            orl_c2=1,
            orl_l1=1,
            orl_l2=1,
            ml_orl_c1=None,
            ml_orl_c2=None,
            ml_orl_l1=None,
            ml_orl_l2=None,
            custo_orl_c1=None,
            custo_orl_c2=None,
            custo_orl_l1=None,
            custo_orl_l2=None,
            custo_total_orla=0,
            soma_total_ml_orla=0,
            acabamento_sup="ACB",
            acabamento_inf=None,
            soma_custo_acb=None,
        )
        session.execute.return_value = _ScalarResult([registro])

        with (
            patch.object(custeio_items, "atualizar_orlas_custeio") as atualizar_orlas,
            patch.object(custeio_items, "_recalcular_custos_acabamento") as recalcular_acabamento,
            patch.object(custeio_items, "_build_orla_lookup", return_value={}),
            patch.object(custeio_items.svc_def_pecas, "mapa_por_nome", return_value={}),
            patch.object(custeio_items, "preencher_info_orlas_linha"),
            patch.object(
                custeio_items,
                "aplicar_definicao_cp_linha",
                side_effect=lambda _session, _linha, cache, **_kwargs: cache,
            ),
        ):
            linhas = custeio_items.listar_custeio_items(session, 737, 810)

        self.assertEqual(len(linhas), 1)
        atualizar_orlas.assert_not_called()
        recalcular_acabamento.assert_not_called()
        session.flush.assert_not_called()


if __name__ == "__main__":
    unittest.main()
