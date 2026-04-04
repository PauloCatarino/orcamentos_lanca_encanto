from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from Martelo_Orcamentos_V2.app.services import modulos_referencia


class ModulosReferenciaTests(unittest.TestCase):
    def test_listar_modulos_referencia_returns_three_named_modules(self) -> None:
        modulos = modulos_referencia.listar_modulos_referencia()

        self.assertEqual(len(modulos), 3)
        self.assertEqual(
            [item["nome"] for item in modulos],
            [
                "REF | 1 Porta + 5 Prateleiras",
                "REF | 2 Portas + 5 Prateleiras",
                "REF | Sistema de Correr",
            ],
        )

    def test_ensure_reference_modules_skips_when_version_already_seeded(self) -> None:
        session = MagicMock()

        with patch.object(
            modulos_referencia,
            "get_setting",
            return_value=modulos_referencia.MODULOS_REFERENCIA_SEED_VERSION,
        ), patch.object(modulos_referencia.svc_modulos, "listar_modulos_por_scope") as list_mock, patch.object(
            modulos_referencia.svc_modulos,
            "guardar_modulo",
        ) as save_mock, patch.object(modulos_referencia, "set_setting") as set_mock:
            created = modulos_referencia.ensure_reference_modules(session)

        self.assertEqual(created, 0)
        list_mock.assert_not_called()
        save_mock.assert_not_called()
        set_mock.assert_not_called()

    def test_ensure_reference_modules_creates_missing_globals_and_marks_version(self) -> None:
        session = MagicMock()
        saved_modules: list[dict] = []

        def _save_side_effect(_db, **kwargs):
            saved_modules.append(kwargs)
            return SimpleNamespace(extras=None)

        with patch.object(modulos_referencia, "get_setting", return_value=""), patch.object(
            modulos_referencia.svc_modulos,
            "listar_modulos_por_scope",
            return_value=[],
        ), patch.object(
            modulos_referencia.svc_modulos,
            "guardar_modulo",
            side_effect=_save_side_effect,
        ), patch.object(modulos_referencia, "set_setting") as set_mock:
            created = modulos_referencia.ensure_reference_modules(session)

        self.assertEqual(created, 3)
        self.assertEqual(len(saved_modules), 3)
        self.assertTrue(all(item["is_global"] is True for item in saved_modules))
        self.assertTrue(all(item["user_id"] is None for item in saved_modules))
        set_mock.assert_called_once_with(
            session,
            modulos_referencia.KEY_MODULOS_REFERENCIA_SEED_VERSION,
            modulos_referencia.MODULOS_REFERENCIA_SEED_VERSION,
        )

    def test_ensure_reference_modules_only_creates_names_not_already_present(self) -> None:
        session = MagicMock()
        saved_modules: list[dict] = []

        existing = [{"nome": "REF | 1 Porta + 5 Prateleiras"}]

        def _save_side_effect(_db, **kwargs):
            saved_modules.append(kwargs)
            return SimpleNamespace(extras=None)

        with patch.object(modulos_referencia, "get_setting", return_value=""), patch.object(
            modulos_referencia.svc_modulos,
            "listar_modulos_por_scope",
            return_value=existing,
        ), patch.object(
            modulos_referencia.svc_modulos,
            "guardar_modulo",
            side_effect=_save_side_effect,
        ), patch.object(modulos_referencia, "set_setting"):
            created = modulos_referencia.ensure_reference_modules(session)

        self.assertEqual(created, 2)
        self.assertEqual(
            [item["nome"] for item in saved_modules],
            [
                "REF | 2 Portas + 5 Prateleiras",
                "REF | Sistema de Correr",
            ],
        )


if __name__ == "__main__":
    unittest.main()
