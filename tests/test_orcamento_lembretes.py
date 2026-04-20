from __future__ import annotations

import json
import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from Martelo_Orcamentos_V2.app.services import orcamento_lembretes as svc
from Martelo_Orcamentos_V2.app.utils import date_utils


class _DummyResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return list(self._rows)


class _FakeDB:
    def __init__(self, rows):
        self._rows = rows

    def execute(self, _stmt):
        return _DummyResult(self._rows)


class ReminderServiceTests(unittest.TestCase):
    def test_analyze_field_detects_actionable_follow_up(self):
        field = svc._analyze_field("Info 2", "DESENHOS ENVIADOS PARA VALIDAR 12-01-2026")
        self.assertIsNotNone(field)
        self.assertTrue(field.actionable)
        self.assertIn("validar", field.matched_keywords)
        self.assertEqual(field.mentioned_dates[0].isoformat(), "2026-01-12")

    def test_analyze_field_ignores_non_actionable_cliente_temporario(self):
        field = svc._analyze_field("Info 1", "CLIENTE TEMPORARIO")
        self.assertIsNotNone(field)
        self.assertFalse(field.actionable)
        self.assertTrue(field.ignored)

    def test_build_daily_summary_respects_hidden_items(self):
        row = (
            SimpleNamespace(
                id=101,
                ano="2026",
                num_orcamento="260101",
                versao="01",
                status="Enviado",
                data="2026-03-05",
                ref_cliente="REF-101",
                descricao_orcamento="Roupeiro 4 portas",
                localizacao="Porto",
                info_1="",
                info_2="DESENHOS ENVIADOS PARA VALIDAR 05-03-2026",
                notas="",
                created_by=10,
                updated_by=10,
            ),
            SimpleNamespace(nome="CLIENTE TESTE"),
        )
        db = _FakeDB([row])
        with patch.object(svc, "resolve_orcamento_cliente_nome", return_value="CLIENTE TESTE"), patch.object(
            svc, "get_hidden_orcamento_ids", return_value={101}
        ), patch.object(svc.svc_tasks, "list_open_task_reminders", return_value=[]):
            summary_hidden = svc.build_daily_summary(db, user_id=10, username="Paulo")
            self.assertEqual(summary_hidden.hidden_count, 1)
            self.assertEqual(summary_hidden.items, [])

            summary_all = svc.build_daily_summary(db, user_id=10, username="Paulo", include_hidden=True)
            self.assertEqual(len(summary_all.items), 1)
            self.assertTrue(summary_all.items[0].hidden)
            self.assertEqual(summary_all.legacy_count, 1)
            self.assertEqual(summary_all.task_count, 0)
            self.assertEqual(summary_all.items[0].ref_cliente, "REF-101")

    def test_build_daily_summary_prefers_formal_tasks_over_legacy_for_same_orcamento(self):
        row = (
            SimpleNamespace(
                id=101,
                ano="2026",
                num_orcamento="260101",
                versao="01",
                status="Enviado",
                data="2026-03-05",
                ref_cliente="REF-101",
                descricao_orcamento="Roupeiro 4 portas",
                localizacao="Porto",
                info_1="",
                info_2="DESENHOS ENVIADOS PARA VALIDAR 05-03-2026",
                notas="",
                created_by=10,
                updated_by=10,
            ),
            SimpleNamespace(nome="CLIENTE TESTE"),
        )
        db = _FakeDB([row])
        task = SimpleNamespace(id=501, orcamento_id=101, texto="Ligar ao cliente", due_date=date(2026, 3, 8), status="Pendente")
        orcamento = row[0]
        client = row[1]
        task_row = SimpleNamespace(task=task, orcamento=orcamento, client=client, assigned_username="Paulo")

        with patch.object(svc, "resolve_orcamento_cliente_nome", return_value="CLIENTE TESTE"), patch.object(
            svc, "get_hidden_orcamento_ids", return_value=set()
        ), patch.object(svc.svc_tasks, "list_open_task_reminders", return_value=[task_row]):
            summary = svc.build_daily_summary(db, user_id=10, username="Paulo", today=date(2026, 3, 8))

        self.assertEqual(len(summary.items), 1)
        self.assertEqual(summary.task_count, 1)
        self.assertEqual(summary.legacy_count, 0)
        self.assertEqual(summary.items[0].entry_kind, "task")
        self.assertEqual(summary.items[0].task_id, 501)
        self.assertEqual(summary.items[0].details_text, "Ligar ao cliente")
        self.assertEqual(summary.items[0].ref_cliente, "REF-101")

    def test_set_orcamento_hidden_updates_json_setting(self):
        store: dict[str, str] = {}

        def fake_get_setting(_db, key, default=None):
            return store.get(key, default)

        def fake_set_setting(_db, key, value):
            store[key] = value

        with patch.object(svc, "get_setting", side_effect=fake_get_setting), patch.object(
            svc, "set_setting", side_effect=fake_set_setting
        ):
            svc.set_orcamento_hidden(object(), user_id=7, orcamento_id=55, hidden=True)
            self.assertEqual(json.loads(store["daily_orcamento_hidden_7"]), [55])
            svc.set_orcamento_hidden(object(), user_id=7, orcamento_id=55, hidden=False)
            self.assertEqual(json.loads(store["daily_orcamento_hidden_7"]), [])


class DateUtilsTests(unittest.TestCase):
    def test_parse_date_value_accepts_multiple_formats(self):
        self.assertEqual(date_utils.parse_date_value("2026-03-06").isoformat(), "2026-03-06")
        self.assertEqual(date_utils.parse_date_value("06-03-2026").isoformat(), "2026-03-06")
        self.assertEqual(date_utils.parse_date_value("06/03/2026").isoformat(), "2026-03-06")

    def test_format_date_helpers(self):
        self.assertEqual(date_utils.format_date_storage("06-03-2026"), "2026-03-06")
        self.assertEqual(date_utils.format_date_display("2026-03-06"), "06-03-2026")


if __name__ == "__main__":
    unittest.main()
