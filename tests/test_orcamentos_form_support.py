import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from Martelo_Orcamentos_V2.ui.pages.orcamentos_form_support import (
    build_existing_orcamento_folder_path,
    build_orcamento_form_values,
    build_orcamento_version_dir,
    build_loaded_orcamento_selection_state,
    build_new_orcamento_form_state,
    extract_temp_name_from_extras,
    extract_temp_simplex_from_extras,
    list_candidate_orcamento_dirs,
    normalize_simplex,
    prepare_loaded_orcamento_selection,
    resolve_orcamento_simplex,
)


class OrcamentosFormSupportTests(unittest.TestCase):
    def test_extract_temp_name_from_extras_handles_json_string(self):
        extras = '{"temp_client_name": "Temp Nome"}'
        self.assertEqual(
            extract_temp_name_from_extras(extras, temp_client_name_key="temp_client_name"),
            "Temp Nome",
        )

    def test_extract_temp_simplex_prefers_loaded_temp(self):
        temp = SimpleNamespace(nome="Temp Nome", nome_simplex="TEMP_SIMPLEX")
        result = extract_temp_simplex_from_extras(
            {"temp_client_id": 5, "temp_client_name": "Ignorar"},
            temp_client_id_key="temp_client_id",
            temp_client_name_key="temp_client_name",
            consumidor_final_label="CONSUMIDOR FINAL",
            temp_loader=lambda temp_id: temp if temp_id == 5 else None,
        )
        self.assertEqual(result, "TEMP_SIMPLEX")

    def test_resolve_orcamento_simplex_uses_temp_first(self):
        client = SimpleNamespace(nome="Cliente Real", nome_simplex="CLI")
        self.assertEqual(resolve_orcamento_simplex(client=client, temp_simplex="Temp Nome"), "TEMP_NOME")
        self.assertEqual(resolve_orcamento_simplex(client=client, temp_simplex=None), "CLI")
        self.assertEqual(normalize_simplex("abc def"), "ABC_DEF")

    def test_build_orcamento_form_values_formats_basic_fields(self):
        orc = SimpleNamespace(
            ano="2026",
            num_orcamento="260262",
            versao="1",
            data="2026-03-05",
            status="Adjudicado",
            enc_phc="0417",
            ref_cliente="2603018",
            obra="Obra",
            preco_total=1120.04,
            descricao_orcamento="Desc",
            localizacao="Loc",
            info_1="I1",
            info_2="I2",
        )
        values = build_orcamento_form_values(
            orc,
            temp_nome="",
            format_version=lambda v: str(v).zfill(2),
            format_currency=lambda v: f"{v:.2f}",
        )
        self.assertEqual(values.seq_text, "0262")
        self.assertEqual(values.versao_text, "01")
        self.assertEqual(values.preco_text, "1120.04")
        self.assertEqual(values.status_text, "Adjudicado")

    def test_folder_helpers_find_expected_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            version_dir = build_orcamento_version_dir(
                base_path=tmp,
                ano="2026",
                num_orc="260262",
                simplex="CLIENTE",
                versao="01",
                format_version=lambda v: str(v).zfill(2),
            )
            Path(version_dir).mkdir(parents=True)

            found = build_existing_orcamento_folder_path(
                base_path=tmp,
                ano="2026",
                num_orc="260262",
                simplex="CLIENTE",
                versao="01",
                format_version=lambda v: str(v).zfill(2),
            )

            self.assertEqual(found, version_dir)

    def test_list_candidate_orcamento_dirs_falls_back_to_prefix(self):
        with tempfile.TemporaryDirectory() as tmp:
            yy_path = Path(tmp) / "2026"
            yy_path.mkdir()
            fallback = yy_path / "260262_CLIENTE_ALT"
            fallback.mkdir()

            dirs = list_candidate_orcamento_dirs(
                yy_path=str(yy_path),
                num_orc="260262",
                expected_dir=str(yy_path / "260262_CLIENTE"),
            )

            self.assertEqual(dirs, [str(fallback)])

    def test_build_loaded_orcamento_selection_state_prefers_temp_name(self):
        orc = SimpleNamespace(
            id=10,
            ano="2026",
            num_orcamento="260262",
            versao="01",
            data="2026-03-05",
            status="Adjudicado",
            created_by=12,
            extras={"temp_client_name": "TEMP SIMPLEX", "manual": True},
            preco_total=10.0,
            descricao_orcamento="Desc",
            localizacao="Loc",
            info_1="I1",
            info_2="I2",
        )
        client = SimpleNamespace(nome="Cliente Real")

        state = build_loaded_orcamento_selection_state(
            orc,
            client=client,
            available_client_names={"Cliente Real"},
            temp_client_name_key="temp_client_name",
            format_version=lambda v: str(v).zfill(2),
            format_currency=lambda v: f"{v:.2f}",
            manual_flag_extractor=lambda extras: bool(extras.get("manual")),
            folder_path_builder=lambda loaded_orc, loaded_client: f"{loaded_orc.id}:{getattr(loaded_client, 'nome', '')}",
        )

        self.assertEqual(state.current_id, 10)
        self.assertTrue(state.manual_flag)
        self.assertEqual(state.selected_client_name, "TEMP SIMPLEX")
        self.assertEqual(state.selected_user_id, 12)
        self.assertEqual(state.folder_path, "10:Cliente Real")
        self.assertEqual(state.form_values.preco_text, "10.00")

    def test_build_loaded_orcamento_selection_state_prefers_column_flag_over_legacy_extras(self):
        orc = SimpleNamespace(
            id=10,
            ano="2026",
            num_orcamento="260262",
            versao="01",
            data="2026-03-05",
            status="Adjudicado",
            created_by=12,
            extras={"manual": True},
            preco_total=10.0,
            preco_total_manual=0,
            descricao_orcamento="Desc",
            localizacao="Loc",
            info_1="I1",
            info_2="I2",
        )
        client = SimpleNamespace(nome="Cliente Real")

        state = build_loaded_orcamento_selection_state(
            orc,
            client=client,
            available_client_names={"Cliente Real"},
            temp_client_name_key="temp_client_name",
            format_version=lambda v: str(v).zfill(2),
            format_currency=lambda v: f"{v:.2f}",
            manual_flag_extractor=lambda extras: bool(extras.get("manual")),
            folder_path_builder=lambda loaded_orc, loaded_client: None,
        )

        self.assertFalse(state.manual_flag)

    def test_prepare_loaded_orcamento_selection_uses_loader_and_handles_missing_row(self):
        orc = SimpleNamespace(
            id=10,
            ano="2026",
            num_orcamento="260262",
            versao="01",
            data="2026-03-05",
            status="Adjudicado",
            extras={},
            preco_total=10.0,
            descricao_orcamento="Desc",
            localizacao="Loc",
            info_1="I1",
            info_2="I2",
        )
        client = SimpleNamespace(nome="Cliente Real")

        state = prepare_loaded_orcamento_selection(
            SimpleNamespace(id=10),
            orcamento_loader=lambda oid: (orc, client) if oid == 10 else (None, None),
            available_client_names={"Cliente Real"},
            temp_client_name_key="temp_client_name",
            format_version=lambda v: str(v).zfill(2),
            format_currency=lambda v: f"{v:.2f}",
            manual_flag_extractor=lambda extras: False,
            folder_path_builder=lambda loaded_orc, loaded_client: f"{loaded_orc.id}:{getattr(loaded_client, 'nome', '')}",
        )

        self.assertIsNotNone(state)
        self.assertEqual(state.current_id, 10)
        self.assertEqual(state.selected_client_name, "Cliente Real")
        self.assertIsNone(
            prepare_loaded_orcamento_selection(
                None,
                orcamento_loader=lambda oid: (None, None),
                available_client_names=set(),
                temp_client_name_key="temp_client_name",
                format_version=lambda v: str(v).zfill(2),
                format_currency=lambda v: f"{v:.2f}",
                manual_flag_extractor=lambda extras: False,
                folder_path_builder=lambda loaded_orc, loaded_client: None,
            )
        )

    def test_build_new_orcamento_form_state_sets_defaults(self):
        state = build_new_orcamento_form_state(ano_text="2026", seq_text="0007")
        self.assertEqual(state.ano_text, "2026")
        self.assertEqual(state.seq_text, "0007")
        self.assertEqual(state.versao_text, "01")
        self.assertEqual(state.status_text, "Falta Orcamentar")


if __name__ == "__main__":
    unittest.main()
