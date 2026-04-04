from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from Martelo_Orcamentos_V2.app.models import (
    CusteioItem,
    CusteioItemDimensoes,
    DadosDefPecas,
    DadosItemsAcabamento,
    DadosItemsFerragem,
    DadosItemsMaterial,
    DadosItemsModelo,
    DadosItemsModeloItem,
    DadosItemsSistemaCorrer,
    DadosModuloMedidas,
)
from Martelo_Orcamentos_V2.app.services import orcamentos


class _ScalarResult:
    def __init__(self, values):
        self._values = list(values)

    def scalars(self):
        return self

    def all(self):
        return list(self._values)


class OrcamentosDeleteItemTests(unittest.TestCase):
    def test_delete_item_removes_related_rows_before_parent(self) -> None:
        db = MagicMock()
        item = SimpleNamespace(id_orcamento=33, versao="01", item="5")
        db.get.return_value = item

        executed = []

        def _execute_side_effect(statement, *args, **kwargs):
            executed.append(statement)
            if len(executed) == 1:
                return _ScalarResult([701, 702])
            return _ScalarResult([])

        db.execute.side_effect = _execute_side_effect

        with patch.object(orcamentos, "_reindex_items") as reindex_mock:
            deleted = orcamentos.delete_item(db, 515, deleted_by=9)

        self.assertTrue(deleted)
        db.delete.assert_called_once_with(item)
        reindex_mock.assert_called_once_with(db, 33, versao="01", updated_by=9)

        delete_tables = [stmt.table.name for stmt in executed if getattr(stmt, "table", None) is not None]
        self.assertEqual(
            delete_tables,
            [
                DadosItemsModeloItem.__tablename__,
                CusteioItemDimensoes.__tablename__,
                CusteioItem.__tablename__,
                DadosItemsModelo.__tablename__,
                DadosItemsAcabamento.__tablename__,
                DadosItemsSistemaCorrer.__tablename__,
                DadosItemsFerragem.__tablename__,
                DadosItemsMaterial.__tablename__,
                DadosDefPecas.__tablename__,
                DadosModuloMedidas.__tablename__,
            ],
        )

    def test_delete_item_returns_false_when_missing(self) -> None:
        db = MagicMock()
        db.get.return_value = None

        deleted = orcamentos.delete_item(db, 999, deleted_by=4)

        self.assertFalse(deleted)
        db.execute.assert_not_called()
        db.delete.assert_not_called()


if __name__ == "__main__":
    unittest.main()
