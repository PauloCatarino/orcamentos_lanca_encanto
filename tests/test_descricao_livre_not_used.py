"""
Test to verify that descricao_livre is not used in calculation/matching logic.

A line with def_peca=DIVISAO_INDEPENDENTE and descricao_livre containing "VARAO"
should NOT be treated as a VARAO line.
"""
from PySide6 import QtWidgets
from Martelo_Orcamentos_V2.ui.pages.custeio_items import CusteioTableModel


class FakePage:
    def production_mode(self):
        return "STD"

    def get_production_rate_info(self, key):
        return None

    def dimension_values(self):
        return {}

    def _icon(self, name):
        return None

    def _apply_collapse_state(self):
        return None


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    page = FakePage()
    model = CusteioTableModel(parent=None)
    model._page = page

    rows = []

    # Case 1: DIVISAO_INDEPENDENTE with descricao_livre containing "VARAO"
    # This should NOT be treated as a VARAO line (which would normally get spp_ml_und calculated)
    rows.append({
        "def_peca": "DIVISAO INDEPENDENTE",
        "descricao_livre": "MODULO 2 PORTAS+3GVTS+VARAO+PA",  # Contains VARAO but should not affect calculation
        "qt_mod": 1,
        "comp": "2400",
        "larg": "1200",
        "esp": "14",
    })

    # Case 2: A normal item with def_peca not containing VARAO (should not get SPP)
    rows.append({
        "def_peca": "COSTA CHAPAR [0000]",
        "descricao_livre": "Some helper text",
        "comp": "2400",
        "larg": "1200",
        "esp": "10",
    })

    model.rows = rows
    model.recalculate_all()

    print("Test Results:")
    print()

    for i, r in enumerate(model.rows):
        print(f"--- Row {i+1}: def_peca={r.get('def_peca')} ---")
        print(f"descricao_livre: {r.get('descricao_livre')}")
        print(f"spp_ml_und: {r.get('spp_ml_und')}")
        print(f"comp_res: {r.get('comp_res')}")
        print(f"larg_res: {r.get('larg_res')}")
        print(f"esp_res: {r.get('esp_res')}")
        print(f"_row_type: {r.get('_row_type')}")
        print()

    # Verify: Row 1 (DIVISAO_INDEPENDENTE) should have spp_ml_und = None (not calculated as SPP)
    row1_spp = model.rows[0].get("spp_ml_und")
    assert row1_spp is None, f"ERROR: Row 1 (DIVISAO_INDEPENDENTE) should not have spp_ml_und calculated, got {row1_spp}"

    # Verify: Row 1 should have comp_res, larg_res, esp_res (basic dimension calculation for DIVISAO)
    row1_comp = model.rows[0].get("comp_res")
    assert row1_comp is not None, f"ERROR: Row 1 should have comp_res, got {row1_comp}"

    print("✓ Test passed: descricao_livre is not used in calculation logic")
    print("  - DIVISAO_INDEPENDENTE with 'VARAO' in descricao_livre is NOT treated as SPP/VARAO")
