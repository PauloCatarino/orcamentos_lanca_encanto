import unittest
from types import SimpleNamespace

from Martelo_Orcamentos_V2.ui.pages.orcamentos_support import (
    ClienteComboItem,
    build_auto_refresh_state,
    build_cliente_change_plan,
    build_focus_request,
    build_orcamento_table_state,
    build_post_save_plan,
    build_cliente_combo_items,
    build_cliente_info_data,
    build_temp_cliente_item,
    collect_orcamento_filter_values,
    filter_orcamento_rows,
    plan_table_selection,
    resolve_selected_cliente_item,
)


class OrcamentosSupportTests(unittest.TestCase):
    def test_build_cliente_combo_items_adds_temp_without_duplicates(self):
        clients = [
            SimpleNamespace(id=1, nome="Cliente Oficial"),
            SimpleNamespace(id=2, nome="CONSUMIDOR FINAL"),
        ]
        temp_clients = [
            SimpleNamespace(id=10, nome="Temp Real", nome_simplex="TEMP_SIMPLEX"),
            SimpleNamespace(id=11, nome="Cliente Oficial", nome_simplex="IGNORAR"),
        ]

        items, phc_names, consumidor_final_id = build_cliente_combo_items(
            clients=clients,
            temp_clients=temp_clients,
            consumidor_final_label="CONSUMIDOR FINAL",
            consumidor_final_id=None,
        )

        self.assertEqual(consumidor_final_id, 2)
        self.assertIn("cliente oficial", phc_names)
        self.assertEqual([item.nome for item in items], ["Cliente Oficial", "CONSUMIDOR FINAL", "TEMP_SIMPLEX"])
        self.assertTrue(items[-1].is_temp)
        self.assertEqual(items[-1].temp_id, 10)

    def test_filter_orcamento_rows_applies_all_filters(self):
        rows = [
            SimpleNamespace(estado="Enviado", cliente="ACME", utilizador="Paulo"),
            SimpleNamespace(estado="Adjudicado", cliente="Beta", utilizador="Andreia"),
            SimpleNamespace(estado="Enviado", cliente="ACME", utilizador="Andreia"),
        ]

        filtered = filter_orcamento_rows(
            rows,
            estado_filter="Enviado",
            cliente_filter="ACME",
            user_filter="Andreia",
        )

        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].utilizador, "Andreia")

    def test_collect_orcamento_filter_values_sorts_distinct_values(self):
        rows = [
            SimpleNamespace(estado="Enviado", cliente="Beta", utilizador="Paulo"),
            SimpleNamespace(estado="Adjudicado", cliente="ACME", utilizador="Andreia"),
            SimpleNamespace(estado="Enviado", cliente="ACME", utilizador="Paulo"),
        ]

        estados, clientes, users = collect_orcamento_filter_values(rows)

        self.assertEqual(estados, ["Adjudicado", "Enviado"])
        self.assertEqual(clientes, ["ACME", "Beta"])
        self.assertEqual(users, ["Andreia", "Paulo"])

    def test_build_orcamento_table_state_applies_filters_and_collects_values(self):
        rows = [
            SimpleNamespace(estado="Enviado", cliente="ACME", utilizador="Paulo"),
            SimpleNamespace(estado="Adjudicado", cliente="Beta", utilizador="Andreia"),
            SimpleNamespace(estado="Enviado", cliente="ACME", utilizador="Andreia"),
        ]

        state = build_orcamento_table_state(
            rows,
            estado_filter="Enviado",
            cliente_filter="ACME",
            user_filter="Todos",
        )

        self.assertEqual(len(state.rows), 2)
        self.assertEqual(state.estados, ["Enviado"])
        self.assertEqual(state.clientes, ["ACME"])
        self.assertEqual(state.users, ["Andreia", "Paulo"])

    def test_plan_table_selection_preserves_preferred_id_and_rows_flag(self):
        plan = plan_table_selection([SimpleNamespace(id=1)], preferred_id=7, select_first=False)
        self.assertEqual(plan.preferred_id, 7)
        self.assertFalse(plan.select_first)
        self.assertTrue(plan.has_rows)

    def test_build_auto_refresh_state_tracks_new_rows(self):
        rows = [
            SimpleNamespace(estado="Enviado", cliente="ACME", utilizador="Paulo"),
            SimpleNamespace(estado="Adjudicado", cliente="Beta", utilizador="Andreia"),
        ]
        state = build_auto_refresh_state(
            rows,
            last_row_count=1,
            estado_filter="Todos",
            cliente_filter="Todos",
            user_filter="Todos",
        )
        self.assertEqual(state.current_row_count, 2)
        self.assertEqual(state.new_count, 1)
        self.assertEqual(len(state.table_state.rows), 2)

    def test_build_focus_request_normalizes_id_and_flag(self):
        request = build_focus_request("15", open_items=True)
        self.assertIsNotNone(request)
        self.assertEqual(request.target_id, 15)
        self.assertTrue(request.open_items)

    def test_build_post_save_plan_for_new_record_prepares_next_form(self):
        plan = build_post_save_plan(was_new=True, saved_id=22, ano_text="2026")
        self.assertFalse(plan.refresh_select_first)
        self.assertEqual(plan.select_id, 22)
        self.assertEqual(plan.prepare_new_form_year, "2026")
        self.assertTrue(plan.leave_new_mode)

    def test_build_post_save_plan_for_edit_keeps_current_flow(self):
        plan = build_post_save_plan(was_new=False, saved_id=22, ano_text="2026")
        self.assertTrue(plan.refresh_select_first)
        self.assertEqual(plan.select_id, 22)
        self.assertIsNone(plan.prepare_new_form_year)
        self.assertFalse(plan.leave_new_mode)

    def test_build_cliente_change_plan_detects_consumidor_final(self):
        plan = build_cliente_change_plan(" CONSUMIDOR FINAL ", consumidor_final_label="CONSUMIDOR FINAL")
        self.assertEqual(plan.normalized_text, "CONSUMIDOR FINAL")
        self.assertTrue(plan.should_open_temp_dialog)
        self.assertIsNone(plan.remember_text)

        normal_plan = build_cliente_change_plan("Cliente A", consumidor_final_label="CONSUMIDOR FINAL")
        self.assertEqual(normal_plan.remember_text, "Cliente A")
        self.assertFalse(normal_plan.should_open_temp_dialog)

    def test_resolve_selected_cliente_item_falls_back_to_temp_item(self):
        items = [ClienteComboItem(id=1, nome="Cliente Oficial")]
        temp = build_temp_cliente_item(
            temp=SimpleNamespace(id=99, nome="Temp", nome_simplex="Temp Simplex"),
            consumidor_final_id=2,
            fallback_name="Temp",
        )

        result = resolve_selected_cliente_item(
            items=items,
            current_text="Temp Simplex",
            current_index=-1,
            temp_item=temp,
        )

        self.assertIsNotNone(result)
        self.assertTrue(result.is_temp)
        self.assertEqual(result.temp_id, 99)

    def test_build_cliente_info_data_maps_known_fields(self):
        record = SimpleNamespace(
            nome="Cliente",
            nome_simplex="CLIENTE",
            num_cliente_phc="123",
            telefone="111",
            telemovel="222",
            email="a@b.c",
            web_page="site",
            morada="Rua",
            info_1="i1",
            info_2="i2",
            notas="nota",
        )

        data = build_cliente_info_data(record)

        self.assertEqual(data["nome"], "Cliente")
        self.assertEqual(data["num_cliente_phc"], "123")
        self.assertEqual(data["notas"], "nota")


if __name__ == "__main__":
    unittest.main()
