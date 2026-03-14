import unittest
from types import SimpleNamespace

from Martelo_Orcamentos_V2.app.services import orcamento_tasks as svc


class _FakeDb:
    def __init__(self):
        self._store = {}
        self.added = []
        self.deleted = []

    def get(self, model, obj_id):
        return self._store.get((model.__name__, int(obj_id)))

    def add(self, obj):
        if getattr(obj, "id", None) is None:
            obj.id = 900 + len(self.added) + 1
        self.added.append(obj)
        self._store[(obj.__class__.__name__, int(obj.id))] = obj

    def delete(self, obj):
        self.deleted.append(obj)

    def flush(self):
        return None


class OrcamentoTasksServiceTests(unittest.TestCase):
    def test_create_orcamento_task_validates_and_adds_record(self):
        db = _FakeDb()
        db._store[("Orcamento", 10)] = SimpleNamespace(id=10)
        db._store[("User", 7)] = SimpleNamespace(id=7)

        task = svc.create_orcamento_task(
            db,
            orcamento_id=10,
            texto=" Ligar ao cliente ",
            assigned_user_id=7,
            due_date="2026-03-10",
            created_by=1,
        )

        self.assertEqual(task.texto, "Ligar ao cliente")
        self.assertEqual(task.assigned_user_id, 7)
        self.assertEqual(task.status, svc.TASK_STATUS_PENDING)
        self.assertEqual(task.due_date.isoformat(), "2026-03-10")
        self.assertEqual(len(db.added), 1)

    def test_set_orcamento_task_status_marks_completion(self):
        db = _FakeDb()
        task = SimpleNamespace(id=15, status=svc.TASK_STATUS_PENDING, completed_at=None, updated_by=None)
        db._store[("OrcamentoTask", 15)] = task

        updated = svc.set_orcamento_task_status(
            db,
            task_id=15,
            status=svc.TASK_STATUS_COMPLETED,
            updated_by=9,
        )

        self.assertIs(updated, task)
        self.assertEqual(task.status, svc.TASK_STATUS_COMPLETED)
        self.assertEqual(task.updated_by, 9)
        self.assertIsNotNone(task.completed_at)

    def test_delete_orcamento_task_removes_existing_record(self):
        db = _FakeDb()
        task = SimpleNamespace(id=21)
        db._store[("OrcamentoTask", 21)] = task

        svc.delete_orcamento_task(db, task_id=21)

        self.assertEqual(db.deleted, [task])


if __name__ == "__main__":
    unittest.main()
