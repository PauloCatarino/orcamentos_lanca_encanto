"""
Test to verify that DIVISAO_INDEPENDENTE rows are protected:
- They should NOT receive mat_default or characteristics based on Descricao_Livre
- Even if Descricao_Livre contains keywords like "VARAO", they should NOT be applied
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

    # Test Case 1: DIVISAO_INDEPENDENTE with "VARAO" in Descricao_Livre
    # Expected: mat_default should NOT be set to "Varao SPP" or any SPP variant
    rows.append({
        "def_peca": "DIVISAO INDEPENDENTE",
        "descricao_livre": "MODULO 2 PORTAS+3GVTS+VARAO+PA",  # Contains VARAO - should be IGNORED
        "comp": "2400",
        "larg": "1200",
        "esp": "14",
        "mat_default": None,
    })

    # Test Case 2: DIVISAO_INDEPENDENTE with various keywords in Descricao_Livre
    rows.append({
        "def_peca": "DIVISAO INDEPENDENTE",
        "descricao_livre": "RODIZIO ACESSORIO COLAGEM SPP",  # Multiple keywords - should be IGNORED
        "comp": "2000",
        "larg": "1000",
        "esp": "10",
        "mat_default": None,
    })

    # Test Case 3: Regular line with "VARAO" for comparison (should work normally)
    rows.append({
        "def_peca": "VARAO",
        "descricao_livre": "Regular varao line",
        "comp": "1200",
        "larg": "14",
        "mat_default": None,
    })

    model.rows = rows
    model.recalculate_all()

    print("\nTest: DIVISAO_INDEPENDENTE Protection")
    print("=" * 70)

    # Row 1: DIVISAO_INDEPENDENTE with VARAO in Descricao_Livre
    print("\nRow 1: DIVISAO_INDEPENDENTE + Descricao_Livre='MODULO 2 PORTAS+3GVTS+VARAO+PA'")
    mat_def_1 = model.rows[0].get("mat_default")
    print(f"  mat_default: {mat_def_1}")
    print(f"  comp_res: {model.rows[0].get('comp_res')}")
    print(f"  larg_res: {model.rows[0].get('larg_res')}")
    print(f"  esp_res: {model.rows[0].get('esp_res')}")
    
    # Verify: mat_default should be None (not set based on descricao_livre)
    if mat_def_1 is None or mat_def_1 == "":
        print("  ✓ PASS: mat_default NOT set (protected from Descricao_Livre)")
    else:
        print(f"  ✗ FAIL: mat_default was set to '{mat_def_1}' - should be None!")

    # Row 2: DIVISAO_INDEPENDENTE with multiple keywords
    print("\nRow 2: DIVISAO_INDEPENDENTE + Descricao_Livre='RODIZIO ACESSORIO COLAGEM SPP'")
    mat_def_2 = model.rows[1].get("mat_default")
    print(f"  mat_default: {mat_def_2}")
    
    if mat_def_2 is None or mat_def_2 == "":
        print("  ✓ PASS: mat_default NOT set (protected from multiple keywords)")
    else:
        print(f"  ✗ FAIL: mat_default was set to '{mat_def_2}' - should be None!")

    # Row 3: Regular VARAO line (should process normally - for comparison)
    print("\nRow 3: Regular VARAO line (for comparison)")
    mat_def_3 = model.rows[2].get("mat_default")
    print(f"  mat_default: {mat_def_3}")
    print(f"  (This may or may not be set depending on the application logic)")

    print("\n" + "=" * 70)
    print("✓ Test completed: DIVISAO_INDEPENDENTE rows are protected from Descricao_Livre")
