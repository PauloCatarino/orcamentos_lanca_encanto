import unittest
import tempfile
from pathlib import Path
from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from Martelo_Orcamentos_V2.app.services import producao_workflow


class ProducaoWorkflowTests(unittest.TestCase):
    def test_validate_processo_payload_requires_ano_and_num_enc(self):
        with self.assertRaisesRegex(ValueError, "Ano e Num Enc PHC sao obrigatorios"):
            producao_workflow.validate_processo_payload({"ano": "", "num_enc_phc": ""})

    def test_validate_processo_payload_normalizes_required_fields(self):
        payload = producao_workflow.validate_processo_payload({"ano": " 2026 ", "num_enc_phc": " 0417 "})
        self.assertEqual(payload["ano"], "2026")
        self.assertEqual(payload["num_enc_phc"], "0417")

    def test_save_processo_creates_new_record(self):
        created = SimpleNamespace(codigo_processo="26.0417_01_01")
        data = {
            "ano": "2026",
            "num_enc_phc": "0417",
            "versao_obra": "01",
            "versao_plano": "01",
            "estado": "Planeamento",
        }

        with patch.object(producao_workflow.svc_producao, "criar_processo", return_value=created) as create_mock:
            result = producao_workflow.save_processo(
                session=object(),
                current_id=None,
                data=data,
                current_user_id=7,
            )

        self.assertTrue(result.was_created)
        self.assertEqual(result.message_title, "Criado")
        self.assertIn("26.0417_01_01", result.message_text)
        create_mock.assert_called_once()

    def test_save_processo_updates_existing_record(self):
        updated = SimpleNamespace(codigo_processo="26.0417_02_01")
        session = object()
        data = {
            "ano": "2026",
            "num_enc_phc": "0417",
            "versao_obra": "02",
            "versao_plano": "01",
            "estado": "Producao",
        }

        with patch.object(producao_workflow.svc_producao, "atualizar_processo", return_value=updated) as update_mock:
            result = producao_workflow.save_processo(
                session=session,
                current_id=11,
                data=data,
                current_user_id=7,
            )

        self.assertFalse(result.was_created)
        self.assertEqual(result.message_title, "Guardado")
        self.assertIn("26.0417_02_01", result.message_text)
        update_mock.assert_called_once_with(
            session,
            11,
            data={
                "ano": "2026",
                "num_enc_phc": "0417",
                "versao_obra": "02",
                "versao_plano": "01",
                "estado": "Producao",
            },
            current_user_id=7,
        )

    def test_build_processo_action_context_exposes_info_and_folder(self):
        processo = SimpleNamespace(
            codigo_processo="26.0417_01_01",
            nome_cliente_simplex="CLIENTE_A",
            nome_cliente="Cliente A",
            pasta_servidor=r"C:\Obras\Proc",
        )

        with patch.object(producao_workflow.svc_producao, "obter_processo", return_value=processo):
            context = producao_workflow.build_processo_action_context(session=object(), current_id=10)

        self.assertEqual(context.info_text, "26.0417_01_01 - CLIENTE_A")
        self.assertEqual(context.folder_path, Path(r"C:\Obras\Proc"))

    def test_create_processo_folder_returns_resolved_base_and_path(self):
        processo = SimpleNamespace(codigo_processo="26.0417_01_01")
        with patch.object(producao_workflow.svc_producao, "obter_processo", return_value=processo), \
             patch.object(producao_workflow, "get_setting", return_value=r"D:\Base"), \
             patch.object(producao_workflow.svc_producao, "criar_pasta_para_processo", return_value=r"D:\Base\2026\Proc") as create_mock:
            result = producao_workflow.create_processo_folder(
                session=object(),
                current_id=10,
                current_base_dir=r"C:\Atual",
                tipo_pasta="Encomenda de Cliente",
            )

        self.assertEqual(result.base_dir, r"D:\Base")
        self.assertEqual(result.path, Path(r"D:\Base\2026\Proc"))
        create_mock.assert_called_once()

    def test_open_processo_folder_returns_path(self):
        processo = SimpleNamespace(codigo_processo="26.0417_01_01")
        with patch.object(producao_workflow.svc_producao, "obter_processo", return_value=processo), \
             patch.object(producao_workflow, "get_setting", return_value=r"D:\Base"), \
             patch.object(producao_workflow.svc_producao, "abrir_pasta_para_processo", return_value=r"D:\Base\2026\Proc"):
            result = producao_workflow.open_processo_folder(
                session=object(),
                current_id=10,
                current_base_dir=r"C:\Atual",
                tipo_pasta="Encomenda de Cliente",
            )

        self.assertEqual(result.base_dir, r"D:\Base")
        self.assertEqual(result.path, Path(r"D:\Base\2026\Proc"))

    def test_resolve_pdf_manager_target_requires_server_folder(self):
        processo = SimpleNamespace(pasta_servidor="")
        with patch.object(producao_workflow.svc_producao, "obter_processo", return_value=processo):
            with self.assertRaisesRegex(ValueError, "Pasta Servidor em falta"):
                producao_workflow.resolve_pdf_manager_target(session=object(), current_id=10)

    def test_prepare_lista_material_imos_builds_context(self):
        processo = SimpleNamespace(id=10)
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "obra"
            folder.mkdir()
            images_base = Path(tmp) / "imgs"
            images_base.mkdir()
            template = images_base / "Lista_Material_IMOS_MARTELO.xltm"
            template.write_text("template", encoding="utf-8")

            with patch.object(producao_workflow.svc_producao, "obter_processo", return_value=processo), \
                 patch.object(producao_workflow, "pasta_imagens_base", return_value=str(images_base)):
                context = producao_workflow.prepare_lista_material_imos(
                    session=object(),
                    current_id=10,
                    pasta_servidor=str(folder),
                    nome_enc_imos="0417_01_26_CLIENTE",
                    values={"RESPONSAVEL": "Paulo"},
                )

        self.assertEqual(context.folder_path, folder)
        self.assertEqual(context.template_path, template)
        self.assertEqual(context.output_path.name, "Lista_Material_0417_01_26_CLIENTE.xlsm")
        self.assertTrue(context.values_b64)

    def test_execute_lista_material_imos_runs_powershell(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "out.xlsm"
            context = producao_workflow.ListaMaterialImosContext(
                processo=SimpleNamespace(id=10),
                folder_path=Path(tmp),
                template_path=Path(tmp) / "template.xltm",
                output_path=output_path,
                values_b64="abc",
            )

            with patch.object(
                producao_workflow.subprocess,
                "run",
                return_value=SimpleNamespace(returncode=0, stdout="", stderr=""),
            ) as run_mock:
                result = producao_workflow.execute_lista_material_imos(context)

        self.assertEqual(result, output_path)
        run_mock.assert_called_once()

    def test_prepare_external_process_creation_builds_prompt_context(self):
        result_data = {
            "source": "phc",
            "ano": "2026",
            "num_enc_phc": "0417",
            "nome_cliente": "Cliente A",
        }
        with patch.object(producao_workflow.svc_producao, "listar_versoes_processo", return_value={("01", "01")}), \
             patch.object(producao_workflow.svc_producao, "listar_versoes_obra_em_pastas", return_value={"01"}), \
             patch.object(producao_workflow.svc_producao, "listar_versoes_plano_em_pastas", return_value={"02"}), \
             patch.object(producao_workflow.svc_producao, "listar_pastas_enc_arvore", return_value=("D:\\Base", {"A": {}})), \
             patch.object(producao_workflow.svc_producao, "sugerir_proxima_versao_obra", return_value="02"), \
             patch.object(producao_workflow.svc_producao, "sugerir_proxima_versao_plano", side_effect=["03", "04"]):
            prep = producao_workflow.prepare_external_process_creation(
                session=object(),
                result_data=result_data,
                responsavel_default="Paulo",
            )

        self.assertEqual(prep.ano, "2026")
        self.assertEqual(prep.num_enc, "0417")
        self.assertTrue(prep.should_prompt_versions)
        self.assertEqual(prep.reuse_versao_obra, "01")
        self.assertEqual(prep.reuse_versao_plano, "02")
        self.assertEqual(prep.creation_payload["responsavel"], "Paulo")

    def test_prepare_orcamento_conversion_validates_enc_phc(self):
        orcamento = SimpleNamespace(id=10, enc_phc="0417", ano="2026", versao="01")
        session = SimpleNamespace(get=lambda model, oid: orcamento if oid == 10 else None)
        with patch.object(producao_workflow.svc_producao, "sugerir_proxima_versao_plano", return_value="03"):
            prep = producao_workflow.prepare_orcamento_conversion(
                session=session,
                orcamento_id=10,
                responsavel_default="Paulo",
            )

        self.assertEqual(prep.enc_digits, "0417")
        self.assertEqual(prep.suggested_plano_default, "03")
        self.assertEqual(prep.responsavel_default, "Paulo")

    def test_create_process_from_orcamento_conversion_creates_processo(self):
        orcamento = SimpleNamespace(
            id=10,
            client_id=7,
            num_orcamento="260262",
            versao="01",
            obra="Obra",
            localizacao="Loc",
            descricao_orcamento="Desc",
            preco_total=12.3,
        )
        prep = producao_workflow.OrcamentoConversionPreparation(
            orcamento=orcamento,
            enc_digits="0417",
            ano_orc="2026",
            versao_obra="01",
            suggested_plano_default="03",
            responsavel_default="Paulo",
        )
        rows_phc = [
            {
                "Cliente": "Cliente A",
                "Cliente_Abreviado": "CLIENTE_A",
                "Num_PHC": "123",
                "Ref_Cliente": "REF",
                "Descricao_Artigo": "Artigo 1",
                "Data_Encomenda": "01.03.2026",
                "Data_Entrega": "10.03.2026",
                "Ano": "2026",
            }
        ]
        created = SimpleNamespace(codigo_processo="26.0417_01_03")
        with patch.object(producao_workflow.svc_phc, "query_phc_encomenda_itens", return_value=rows_phc), \
             patch.object(producao_workflow.svc_producao, "sugerir_proxima_versao_plano", return_value="03"), \
             patch.object(producao_workflow.svc_producao, "criar_processo", return_value=created) as create_mock:
            result = producao_workflow.create_process_from_orcamento_conversion(
                session=object(),
                preparation=prep,
                versao_plano="03",
                current_user_id=7,
            )

        self.assertIs(result, created)
        create_mock.assert_called_once()

    def test_create_process_from_orcamento_conversion_requires_synced_phc_simplex(self):
        orcamento = SimpleNamespace(id=10, client_id=7, num_orcamento="260262", versao="01")
        prep = producao_workflow.OrcamentoConversionPreparation(
            orcamento=orcamento,
            enc_digits="0417",
            ano_orc="2026",
            versao_obra="01",
            suggested_plano_default="03",
            responsavel_default="Paulo",
        )
        rows_phc = [
            {
                "Cliente": "Cliente Sem Abreviatura",
                "Cliente_Abreviado": "",
                "Num_PHC": "123",
                "Ref_Cliente": "REF",
                "Descricao_Artigo": "Artigo 1",
                "Data_Encomenda": "01.03.2026",
                "Data_Entrega": "10.03.2026",
                "Ano": "2026",
            }
        ]

        with patch.object(producao_workflow.svc_phc, "query_phc_encomenda_itens", return_value=rows_phc):
            with self.assertRaisesRegex(ValueError, "Atualizar PHC"):
                producao_workflow.create_process_from_orcamento_conversion(
                    session=object(),
                    preparation=prep,
                    versao_plano="03",
                    current_user_id=7,
                )

    def test_create_process_from_orcamento_conversion_requires_joined_phc_simplex(self):
        orcamento = SimpleNamespace(id=10, client_id=7, num_orcamento="260262", versao="01")
        prep = producao_workflow.OrcamentoConversionPreparation(
            orcamento=orcamento,
            enc_digits="0417",
            ano_orc="2026",
            versao_obra="01",
            suggested_plano_default="03",
            responsavel_default="Paulo",
        )
        rows_phc = [
            {
                "Cliente": "Cliente Com Espacos",
                "Cliente_Abreviado": "CLIENTE CASAIS",
                "Num_PHC": "123",
                "Ref_Cliente": "REF",
                "Descricao_Artigo": "Artigo 1",
                "Data_Encomenda": "01.03.2026",
                "Data_Entrega": "10.03.2026",
                "Ano": "2026",
            }
        ]

        with patch.object(producao_workflow.svc_phc, "query_phc_encomenda_itens", return_value=rows_phc):
            with self.assertRaisesRegex(ValueError, "usando '_' para unir as palavras"):
                producao_workflow.create_process_from_orcamento_conversion(
                    session=object(),
                    preparation=prep,
                    versao_plano="03",
                    current_user_id=7,
                )

    def test_sync_producao_statuses_from_phc_skips_when_already_checked_today(self):
        session = MagicMock()
        today = date(2026, 3, 20)

        with patch.object(producao_workflow, "get_setting", return_value=today.isoformat()):
            result = producao_workflow.sync_producao_statuses_from_phc(
                session,
                current_user_id=7,
                today=today,
            )

        self.assertTrue(result.skipped_daily)
        session.execute.assert_not_called()

    def test_sync_producao_statuses_from_phc_updates_matching_process(self):
        session = MagicMock()
        process = SimpleNamespace(
            id=10,
            codigo_processo="26.0402_01_01_VITOR_PEREIRA",
            ano="2026",
            num_enc_phc="0402",
            num_cliente_phc="163",
            nome_cliente="VITOR JOSE PEREIRA",
            responsavel="Paulo",
            estado="Planeamento",
            tipo_pasta="Encomenda de Cliente",
            updated_by=None,
        )
        session.execute.return_value.scalars.return_value.all.return_value = [process]
        phc_rows = [
            {
                "Ano": 2026,
                "Enc_No": 402,
                "Num_PHC": "163",
                "CL_Nome": "VITOR JOSE PEREIRA",
                "Estado_PHC": "7 - ARQUIVADO",
                "BO_Tabela1": "7 - ARQUIVADO",
                "BI_Tabela1": "7 - ARQUIVADO",
            }
        ]

        with patch.object(producao_workflow, "get_setting", return_value=""), \
             patch.object(producao_workflow, "set_setting") as set_setting_mock, \
             patch.object(producao_workflow.svc_phc, "query_phc_estado_debug_rows", return_value=phc_rows):
            result = producao_workflow.sync_producao_statuses_from_phc(
                session,
                current_user_id=7,
                force=True,
                today=date(2026, 3, 20),
            )

        self.assertFalse(result.skipped_daily)
        self.assertEqual(len(result.changed), 1)
        self.assertEqual(result.changed[0].estado_novo, "Arquivado")
        self.assertEqual(process.estado, "Arquivado")
        self.assertEqual(process.updated_by, 7)
        session.add.assert_called_with(process)
        saved_keys = [call.args[1] for call in set_setting_mock.call_args_list]
        self.assertIn(producao_workflow.KEY_PRODUCAO_PHC_STATUS_LAST_SYNC_DATE, saved_keys)
        self.assertIn(producao_workflow.KEY_PRODUCAO_PHC_STATUS_ISSUES_CACHE_DATE, saved_keys)
        self.assertIn(producao_workflow.KEY_PRODUCAO_PHC_STATUS_ISSUES_CACHE_JSON, saved_keys)

    def test_sync_producao_statuses_from_phc_reports_mismatch_details(self):
        session = MagicMock()
        process = SimpleNamespace(
            id=11,
            codigo_processo="26.0402_01_01_VITOR_PEREIRA",
            ano="2026",
            num_enc_phc="0402",
            num_cliente_phc="999",
            nome_cliente="VITOR JOSE PEREIRA",
            responsavel="Paulo",
            estado="Planeamento",
            tipo_pasta="Encomenda de Cliente",
            updated_by=None,
        )
        session.execute.return_value.scalars.return_value.all.return_value = [process]
        phc_rows = [
            {
                "Ano": 2026,
                "Enc_No": 402,
                "Num_PHC": "163",
                "CL_Nome": "VITOR JOSE PEREIRA",
                "Estado_PHC": "2 - DESENHO",
                "BO_Tabela1": "2 - DESENHO",
                "BI_Tabela1": "2 - DESENHO",
            }
        ]

        with patch.object(producao_workflow, "get_setting", return_value=""), \
             patch.object(producao_workflow, "set_setting"), \
             patch.object(producao_workflow.svc_phc, "query_phc_estado_debug_rows", return_value=phc_rows):
            result = producao_workflow.sync_producao_statuses_from_phc(
                session,
                current_user_id=7,
                force=True,
                today=date(2026, 3, 20),
            )

        self.assertEqual(len(result.changed), 0)
        self.assertEqual(len(result.issues), 1)
        self.assertIn("Nao foi encontrada correspondencia direta", result.issues[0].reason)
        self.assertIn("163", result.issues[0].phc_num_clientes)
        self.assertEqual(result.issues[0].responsavel, "Paulo")

    def test_build_user_phc_status_issue_summary_filters_by_user_and_hidden_state(self):
        store = {}
        issue_paulo = producao_workflow.PHCStatusSyncIssue(
            processo_id=11,
            codigo_processo="26.0402_01_01_VITOR_PEREIRA",
            responsavel="Paulo",
            reason="Divergencia",
            martelo_ano="2026",
            martelo_num_enc_phc="0402",
            martelo_num_cliente_phc="999",
            martelo_nome_cliente="VITOR JOSE PEREIRA",
            phc_anos=("2026",),
            phc_num_encs=("402",),
            phc_num_clientes=("163",),
            phc_nomes=("VITOR JOSE PEREIRA",),
            phc_estados=("2 - DESENHO",),
        )
        issue_ana = producao_workflow.PHCStatusSyncIssue(
            processo_id=12,
            codigo_processo="26.0410_01_01_OUTRO",
            responsavel="Ana",
            reason="Divergencia",
            martelo_ano="2026",
            martelo_num_enc_phc="0410",
            martelo_num_cliente_phc="200",
            martelo_nome_cliente="OUTRO CLIENTE",
            phc_anos=("2026",),
            phc_num_encs=("410",),
            phc_num_clientes=("201",),
            phc_nomes=("OUTRO CLIENTE PHC",),
            phc_estados=("7 - ARQUIVADO",),
        )

        def fake_get_setting(_db, key, default=None):
            return store.get(key, default)

        def fake_set_setting(_db, key, value):
            store[key] = value

        with patch.object(producao_workflow, "get_setting", side_effect=fake_get_setting), \
             patch.object(producao_workflow, "set_setting", side_effect=fake_set_setting):
            producao_workflow._cache_phc_status_issues(
                object(),
                issues=[issue_paulo, issue_ana],
                today_text="2026-03-21",
            )
            producao_workflow.set_producao_phc_issue_hidden(object(), user_id=7, processo_id=11, hidden=True)

            summary_hidden = producao_workflow.build_user_phc_status_issue_summary(
                object(),
                user_id=7,
                username="Paulo",
                today=date(2026, 3, 21),
            )
            self.assertEqual(summary_hidden.total_count, 1)
            self.assertEqual(summary_hidden.hidden_count, 1)
            self.assertEqual(summary_hidden.items, [])

            summary_all = producao_workflow.build_user_phc_status_issue_summary(
                object(),
                user_id=7,
                username="Paulo",
                today=date(2026, 3, 21),
                include_hidden=True,
            )
            self.assertEqual(len(summary_all.items), 1)
            self.assertTrue(summary_all.items[0].hidden)
            self.assertEqual(summary_all.items[0].issue.codigo_processo, "26.0402_01_01_VITOR_PEREIRA")

    def test_should_auto_show_producao_phc_issues_tracks_seen_per_user(self):
        store = {}

        def fake_get_setting(_db, key, default=None):
            return store.get(key, default)

        def fake_set_setting(_db, key, value):
            store[key] = value

        with patch.object(producao_workflow, "get_setting", side_effect=fake_get_setting), \
             patch.object(producao_workflow, "set_setting", side_effect=fake_set_setting):
            self.assertTrue(
                producao_workflow.should_auto_show_producao_phc_issues(
                    object(),
                    user_id=7,
                    today=date(2026, 3, 21),
                )
            )
            producao_workflow.mark_producao_phc_issues_seen(object(), user_id=7, today=date(2026, 3, 21))
            self.assertFalse(
                producao_workflow.should_auto_show_producao_phc_issues(
                    object(),
                    user_id=7,
                    today=date(2026, 3, 21),
                )
            )

    def test_build_processo_folders_context_uses_process_data(self):
        processo = SimpleNamespace(id=10, ano="2026", num_enc_phc="0417", tipo_pasta="Encomenda", codigo_processo="26.0417_01_01")
        with patch.object(producao_workflow.svc_producao, "obter_processo", return_value=processo), \
             patch.object(producao_workflow.svc_producao, "listar_pastas_enc_arvore", return_value=("D:\\Base", {"A": {}})):
            context = producao_workflow.build_processo_folders_context(session=object(), current_id=10)

        self.assertEqual(context.folder_root, "D:\\Base")
        self.assertEqual(context.title_suffix, "26.0417_01_01")

    def test_prepare_nova_versao_builds_creation_payload(self):
        processo = SimpleNamespace(id=10, tipo_pasta="Encomenda", orcamento_id=99, client_id=7)
        data = {
            "ano": "2026",
            "num_enc_phc": "0417",
            "versao_obra": "01",
            "versao_plano": "02",
            "estado": "Planeamento",
        }
        with patch.object(producao_workflow.svc_producao, "obter_processo", return_value=processo), \
             patch.object(producao_workflow.svc_producao, "listar_versoes_processo", return_value={("01", "01")}), \
             patch.object(producao_workflow.svc_producao, "listar_versoes_obra_em_pastas", return_value={"01"}), \
             patch.object(producao_workflow.svc_producao, "listar_versoes_plano_em_pastas", return_value={"02"}), \
             patch.object(producao_workflow.svc_producao, "listar_pastas_enc_arvore", return_value=("D:\\Base", {"A": {}})), \
             patch.object(producao_workflow.svc_producao, "sugerir_proxima_versao_plano", side_effect=["03", "04"]), \
             patch.object(producao_workflow.svc_producao, "sugerir_proxima_versao_obra", return_value="02"):
            prep = producao_workflow.prepare_nova_versao(
                session=object(),
                current_id=10,
                data=data,
            )

        self.assertEqual(prep.sug_obra_cutrite, "01")
        self.assertEqual(prep.sug_plano_cutrite, "03")
        self.assertEqual(prep.creation_data["orcamento_id"], 99)
        self.assertEqual(prep.creation_data["client_id"], 7)
        self.assertEqual(prep.creation_data["pasta_servidor"], "")

    def test_create_nova_versao_uses_create_service(self):
        created = SimpleNamespace(codigo_processo="26.0417_02_01")
        prep = producao_workflow.NovaVersaoPreparation(
            processo_atual=SimpleNamespace(id=10),
            existing_keys=set(),
            folder_root="",
            folder_tree={},
            sug_obra_cutrite="01",
            sug_plano_cutrite="02",
            sug_obra_obra="02",
            sug_plano_obra="01",
            creation_data={
                "ano": "2026",
                "num_enc_phc": "0417",
                "versao_obra": "01",
                "versao_plano": "02",
                "estado": "Planeamento",
                "pasta_servidor": "",
            },
        )
        with patch.object(producao_workflow.svc_producao, "criar_processo", return_value=created) as create_mock:
            result = producao_workflow.create_nova_versao(
                session=object(),
                preparation=prep,
                versao_obra="02",
                versao_plano="01",
                current_user_id=7,
            )

        self.assertIs(result, created)
        create_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
