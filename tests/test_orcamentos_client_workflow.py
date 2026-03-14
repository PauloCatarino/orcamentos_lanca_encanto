import unittest
from types import SimpleNamespace
from unittest.mock import patch

from Martelo_Orcamentos_V2.app.services import orcamentos_client_workflow


class OrcamentosClientWorkflowTests(unittest.TestCase):
    def test_load_cliente_combo_state_builds_names_and_consumidor_id(self):
        clients = [SimpleNamespace(id=1, nome="Cliente A"), SimpleNamespace(id=2, nome="CONSUMIDOR FINAL")]
        temp_clients = [SimpleNamespace(id=10, nome="Temp A", nome_simplex="TEMP_A")]

        with patch.object(orcamentos_client_workflow, "list_clients", return_value=clients), \
             patch.object(orcamentos_client_workflow, "list_clientes_temporarios", return_value=temp_clients):
            state = orcamentos_client_workflow.load_cliente_combo_state(
                db=object(),
                consumidor_final_label="CONSUMIDOR FINAL",
                consumidor_final_id=None,
            )

        self.assertEqual(state.consumidor_final_id, 2)
        self.assertEqual(state.names, ["Cliente A", "CONSUMIDOR FINAL", "TEMP_A"])

    def test_resolve_selected_cliente_prefers_temp_record_when_found(self):
        temp = SimpleNamespace(id=10, nome="Temp Real", nome_simplex="TEMP_REAL")
        with patch.object(orcamentos_client_workflow, "get_cliente_temporario_por_nome", return_value=temp):
            item = orcamentos_client_workflow.resolve_selected_cliente(
                db=object(),
                items=[SimpleNamespace(id=1, nome="Cliente Oficial", is_temp=False, temp_id=None)],
                current_text="TEMP_REAL",
                current_index=-1,
                consumidor_final_id=2,
            )

        self.assertIsNotNone(item)
        self.assertTrue(item.is_temp)
        self.assertEqual(item.temp_id, 10)

    def test_resolve_temp_client_dialog_selection_rejects_duplicate_phc_name(self):
        with self.assertRaisesRegex(ValueError, "Ja existe um cliente oficial no PHC"):
            orcamentos_client_workflow.resolve_temp_client_dialog_selection(
                db=object(),
                dialog_data={"nome": "Cliente Oficial", "temp_id": None},
                phc_name_set={"cliente oficial"},
            )

    def test_load_cliente_info_state_uses_temp_cliente_when_present(self):
        temp = SimpleNamespace(nome="Temp", nome_simplex="TEMP")
        with patch.object(orcamentos_client_workflow, "get_cliente_temporario", return_value=temp):
            state = orcamentos_client_workflow.load_cliente_info_state(
                db=object(),
                row_id=10,
                temp_id=5,
                temp_nome="Temp",
            )

        self.assertEqual(state.origem, "Temporario (CONSUMIDOR FINAL)")
        self.assertEqual(state.data["nome"], "Temp")

    def test_load_cliente_info_state_uses_linked_phc_client(self):
        client = SimpleNamespace(nome="Cliente A", nome_simplex="CLIENTE_A")
        with patch.object(
            orcamentos_client_workflow.orcamentos_workflow,
            "load_orcamento_with_client",
            return_value=(SimpleNamespace(id=10), client),
        ):
            state = orcamentos_client_workflow.load_cliente_info_state(
                db=object(),
                row_id=10,
                temp_id=None,
                temp_nome="",
            )

        self.assertEqual(state.origem, "PHC")
        self.assertEqual(state.data["nome"], "Cliente A")


if __name__ == "__main__":
    unittest.main()
