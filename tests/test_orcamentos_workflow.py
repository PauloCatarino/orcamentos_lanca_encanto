import datetime
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from Martelo_Orcamentos_V2.app.services import orcamentos_workflow


class _FakeDb:
    def __init__(self, existing=None):
        self._existing = existing
        self._clients = {}

    def get(self, model, current_id):
        if model.__name__ == "Orcamento":
            _ = current_id
            return self._existing
        return self._clients.get(current_id)


class OrcamentosWorkflowTests(unittest.TestCase):
    def test_prepare_orcamento_save_request_formats_identity_and_trims_fields(self):
        cliente_item = SimpleNamespace(id=55, nome="Cliente A", is_temp=False)

        request = orcamentos_workflow.prepare_orcamento_save_request(
            cliente_item=cliente_item,
            consumidor_final_id=2,
            owner_user_id=9,
            year_text="2026",
            seq_text="1",
            version_text="1",
            format_version=lambda value: str(value).zfill(2),
            ref_cliente_text=" 260318 ",
            data_value="2026-03-07",
            status_text="Adjudicado",
            enc_phc="0417",
            obra="Obra Teste",
            preco_val=1120.04,
            descricao_orcamento="Descricao",
            localizacao="Local",
            info_1="Info 1",
            info_2="Info 2",
        )

        self.assertEqual(request.client_id, 55)
        self.assertEqual(request.owner_user_id, 9)
        self.assertEqual(request.ano_txt, "2026")
        self.assertEqual(request.num_orcamento, "260001")
        self.assertEqual(request.versao_txt, "01")
        self.assertEqual(request.ref_cliente_txt, "260318")

    def test_prepare_orcamento_save_request_requires_cliente(self):
        with self.assertRaisesRegex(ValueError, "Selecione um cliente"):
            orcamentos_workflow.prepare_orcamento_save_request(
                cliente_item=None,
                consumidor_final_id=2,
                owner_user_id=9,
                year_text="2026",
                seq_text="1",
                version_text="1",
                format_version=lambda value: str(value).zfill(2),
                ref_cliente_text="",
                data_value="2026-03-07",
                status_text="Adjudicado",
                enc_phc=None,
                obra=None,
                preco_val=None,
                descricao_orcamento=None,
                localizacao=None,
                info_1=None,
                info_2=None,
            )

    def test_check_orcamento_save_conflicts_only_runs_for_new_records(self):
        request = SimpleNamespace(ref_cliente_txt="260318", ano_txt="2026", num_orcamento="260001", versao_txt="01")

        with patch.object(orcamentos_workflow, "find_ref_cliente_matches", return_value=["row"]) as find_mock, \
             patch.object(orcamentos_workflow, "orcamento_identity_exists", return_value=True) as exists_mock:
            matches, exists = orcamentos_workflow.check_orcamento_save_conflicts(
                object(),
                current_id=None,
                request=request,
            )

        self.assertEqual(matches, ["row"])
        self.assertTrue(exists)
        find_mock.assert_called_once()
        exists_mock.assert_called_once()

        with patch.object(orcamentos_workflow, "find_ref_cliente_matches") as find_mock, \
             patch.object(orcamentos_workflow, "orcamento_identity_exists") as exists_mock:
            matches, exists = orcamentos_workflow.check_orcamento_save_conflicts(
                object(),
                current_id=10,
                request=request,
            )

        self.assertEqual(matches, [])
        self.assertFalse(exists)
        find_mock.assert_not_called()
        exists_mock.assert_not_called()

    def test_build_ref_cliente_match_rows_uses_client_name(self):
        orcamento = SimpleNamespace(
            id=10,
            ano="2026",
            num_orcamento="260001",
            versao="01",
            client_id=55,
            ref_cliente="260318",
            data="2026-03-07",
            status="Adjudicado",
            obra="Obra",
        )
        client = SimpleNamespace(id=55, nome="Cliente A")
        db = _FakeDb(existing=orcamento)
        db._clients[55] = client

        rows = orcamentos_workflow.build_ref_cliente_match_rows(db, [orcamento])

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].cliente, "Cliente A")
        self.assertEqual(rows[0].estado, "Adjudicado")

    def test_load_orcamento_with_client_returns_both_records(self):
        orcamento = SimpleNamespace(id=10, client_id=55)
        client = SimpleNamespace(id=55, nome="Cliente")
        db = _FakeDb(existing=orcamento)
        db._clients[55] = client

        loaded_orcamento, loaded_client = orcamentos_workflow.load_orcamento_with_client(db, 10)

        self.assertIs(loaded_orcamento, orcamento)
        self.assertIs(loaded_client, client)

    def test_get_or_create_target_returns_existing_record_for_edit(self):
        existing = SimpleNamespace(id=10, client_id=None)
        db = _FakeDb(existing=existing)

        result, was_new = orcamentos_workflow.get_or_create_orcamento_target(
            db,
            current_id=10,
            ano="2026",
            num_orcamento="260001",
            versao="01",
            cliente_item=SimpleNamespace(nome="Cliente"),
            client_id=55,
            created_by=7,
            owner_user_id=12,
        )

        self.assertIs(result, existing)
        self.assertFalse(was_new)
        self.assertEqual(result.client_id, 55)
        self.assertEqual(result.created_by, 12)

    def test_get_or_create_target_raises_when_existing_record_is_missing(self):
        db = _FakeDb(existing=None)

        with self.assertRaisesRegex(ValueError, "Registo nao encontrado"):
            orcamentos_workflow.get_or_create_orcamento_target(
                db,
                current_id=99,
                ano="2026",
                num_orcamento="260001",
                versao="01",
                cliente_item=SimpleNamespace(nome="Cliente"),
                client_id=55,
                created_by=7,
                owner_user_id=12,
            )

    def test_get_or_create_target_uses_create_service_for_new_record(self):
        created = SimpleNamespace(id=11, client_id=None)
        db = _FakeDb(existing=None)

        with patch.object(orcamentos_workflow, "create_orcamento", return_value=created) as create_mock:
            result, was_new = orcamentos_workflow.get_or_create_orcamento_target(
                db,
                current_id=None,
                ano="2026",
                num_orcamento="260001",
                versao="01",
                cliente_item=SimpleNamespace(nome="Cliente A"),
                client_id=55,
                created_by=7,
                owner_user_id=12,
            )

        self.assertIs(result, created)
        self.assertTrue(was_new)
        self.assertEqual(result.client_id, 55)
        create_mock.assert_called_once_with(
            db,
            ano="2026",
            num_orcamento="260001",
            versao="01",
            cliente_nome="Cliente A",
            client_id=55,
            created_by=12,
        )

    def test_apply_orcamento_form_updates_maps_fields(self):
        target = SimpleNamespace()
        updated_at = datetime.datetime(2026, 3, 7, 10, 30, 0)

        result = orcamentos_workflow.apply_orcamento_form_updates(
            target,
            data_value="2026-03-07",
            status="Adjudicado",
            enc_phc="0417",
            ref_cliente="260318",
            obra="Obra Teste",
            preco_total=1120.04,
            manual_flag=True,
            extras={"manual": True},
            descricao_orcamento="Descricao",
            localizacao="Local",
            info_1="Info 1",
            info_2="Info 2",
            updated_by=7,
            updated_at=updated_at,
        )

        self.assertIs(result, target)
        self.assertEqual(target.data, "2026-03-07")
        self.assertEqual(target.status, "Adjudicado")
        self.assertEqual(target.enc_phc, "0417")
        self.assertEqual(target.ref_cliente, "260318")
        self.assertEqual(target.obra, "Obra Teste")
        self.assertEqual(target.preco_total, 1120.04)
        self.assertEqual(target.preco_total_manual, 1)
        self.assertEqual(target.preco_atualizado_em, updated_at)
        self.assertEqual(target.extras, {"manual": True})
        self.assertEqual(target.descricao_orcamento, "Descricao")
        self.assertEqual(target.localizacao, "Local")
        self.assertEqual(target.info_1, "Info 1")
        self.assertEqual(target.info_2, "Info 2")
        self.assertEqual(target.updated_by, 7)

    def test_save_orcamento_request_builds_manual_and_temp_extras_for_new_record(self):
        session = object()
        target = SimpleNamespace()
        request = orcamentos_workflow.OrcamentoSaveRequest(
            cliente_item=SimpleNamespace(id=2, nome="TEMP_SIMPLEX", is_temp=True, temp_id=99),
            client_id=2,
            owner_user_id=12,
            ano_txt="2026",
            num_orcamento="260001",
            versao_txt="01",
            ref_cliente_txt="260318",
            data_value="2026-03-07",
            status_text="Adjudicado",
            enc_phc="0417",
            obra="Obra",
            preco_val=1120.04,
            descricao_orcamento="Descricao",
            localizacao="Local",
            info_1="Info 1",
            info_2="Info 2",
        )

        with patch.object(orcamentos_workflow, "get_or_create_orcamento_target", return_value=(target, True)) as target_mock:
            result = orcamentos_workflow.save_orcamento_request(
                session,
                current_id=None,
                request=request,
                created_by=7,
                preco_manual_changed=False,
                existing_manual_flag=False,
                existing_extras={"legacy": True},
                preco_manual_key="preco_manual",
                temp_client_id_key="temp_id",
                temp_client_name_key="temp_name",
                updated_at=datetime.datetime(2026, 3, 7, 10, 0, 0),
            )

        self.assertIs(result.orcamento, target)
        self.assertTrue(result.was_new)
        self.assertTrue(result.manual_flag)
        self.assertEqual(target.preco_total_manual, 1)
        self.assertEqual(
            target.extras,
            {"legacy": True, "preco_manual": True, "temp_id": 99, "temp_name": "TEMP_SIMPLEX"},
        )
        self.assertEqual(target.updated_by, 7)
        target_mock.assert_called_once_with(
            session,
            current_id=None,
            ano="2026",
            num_orcamento="260001",
            versao="01",
            cliente_item=request.cliente_item,
            client_id=2,
            created_by=7,
            owner_user_id=12,
        )

    def test_save_orcamento_request_preserves_existing_manual_flag_on_edit(self):
        target = SimpleNamespace()
        request = orcamentos_workflow.OrcamentoSaveRequest(
            cliente_item=SimpleNamespace(id=55, nome="Cliente A", is_temp=False, temp_id=None),
            client_id=55,
            owner_user_id=12,
            ano_txt="2026",
            num_orcamento="260001",
            versao_txt="01",
            ref_cliente_txt=None,
            data_value="2026-03-07",
            status_text="Enviado",
            enc_phc=None,
            obra=None,
            preco_val=None,
            descricao_orcamento=None,
            localizacao=None,
            info_1=None,
            info_2=None,
        )

        with patch.object(orcamentos_workflow, "get_or_create_orcamento_target", return_value=(target, False)):
            result = orcamentos_workflow.save_orcamento_request(
                object(),
                current_id=10,
                request=request,
                created_by=7,
                preco_manual_changed=False,
                existing_manual_flag=True,
                existing_extras={"preco_manual": True, "temp_id": 99},
                preco_manual_key="preco_manual",
                temp_client_id_key="temp_id",
                temp_client_name_key="temp_name",
                updated_at=datetime.datetime(2026, 3, 7, 10, 0, 0),
            )

        self.assertFalse(result.was_new)
        self.assertTrue(result.manual_flag)
        self.assertEqual(target.preco_total_manual, 1)
        self.assertEqual(target.extras, {"preco_manual": True})
        self.assertEqual(target.updated_by, 7)

    def test_create_and_find_orcamento_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            created = orcamentos_workflow.create_orcamento_folder(
                base_path=tmp,
                ano="2026",
                num_orc="260262",
                simplex="CLIENTE",
                versao="1",
                format_version=lambda v: str(v).zfill(2),
            )
            found = orcamentos_workflow.find_existing_orcamento_folder(
                base_path=tmp,
                ano="2026",
                num_orc="260262",
                simplex="CLIENTE",
                versao="1",
                format_version=lambda v: str(v).zfill(2),
            )

        self.assertEqual(found, created)
        self.assertTrue(created.endswith(str(Path("2026") / "260262_CLIENTE" / "01")))

    def test_delete_orcamento_folders_removes_version_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            version_dir = Path(tmp) / "2026" / "260262_CLIENTE" / "01"
            version_dir.mkdir(parents=True)

            removed = orcamentos_workflow.delete_orcamento_folders(
                base_path=tmp,
                ano="2026",
                num_orc="260262",
                simplex="CLIENTE",
                versao="01",
                format_version=lambda v: str(v).zfill(2),
            )

            self.assertEqual(removed, [str(version_dir)])
            self.assertFalse(version_dir.exists())

    def test_delete_orcamento_record_uses_service(self):
        session = object()
        with patch.object(orcamentos_workflow, "delete_orcamento") as delete_mock:
            orcamentos_workflow.delete_orcamento_record(session, 10)
        delete_mock.assert_called_once_with(session, 10)

    def test_duplicate_orcamento_record_uses_service(self):
        session = object()
        duplicated = SimpleNamespace(id=11)
        with patch.object(orcamentos_workflow, "duplicate_orcamento_version", return_value=duplicated) as duplicate_mock:
            result = orcamentos_workflow.duplicate_orcamento_record(session, 10, created_by=7)
        self.assertIs(result, duplicated)
        duplicate_mock.assert_called_once_with(session, 10, created_by=7)


if __name__ == "__main__":
    unittest.main()
