"""
Test to verify that DIVISAO_INDEPENDENTE rows are COMPLETELY protected:
- They should NEVER receive mat_default or any characteristics
- They should NEVER be processed by _apply_updates_from_items
- Even if Descricao_Livre contains keywords, they should be IGNORED
- Only comp_res, larg_res, esp_res should be filled (basic dimensions)
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

    # Test Case 1: DIVISAO_INDEPENDENTE with keywords in Descricao_Livre
    # Should have ONLY: comp_res, larg_res, esp_res filled; NO mat_default
    rows.append({
        "def_peca": "DIVISAO INDEPENDENTE",
        "descricao_livre": "MODULO 2 PORTAS+3GVTS+PUXADOR",  # Keywords that would match mat_default
        "comp": "2400",
        "larg": "1200",
        "esp": "14.0",
        "mat_default": None,
        "tipo": None,
        "familia": None,
    })

    # Test Case 2: Another DIVISAO_INDEPENDENTE with MORE keywords
    rows.append({
        "def_peca": "DIVISAO INDEPENDENTE",
        "descricao_livre": "RODIZIO ACESSORIO COLAGEM SPP VARAO",
        "comp": "2000",
        "larg": "1000",
        "esp": "10.0",
        "mat_default": None,
        "tipo": None,
        "familia": None,
    })

    # Test Case 3: Normal line for comparison (should work normally)
    rows.append({
        "def_peca": "VARAO",
        "descricao_livre": "Regular varao line",
        "comp": "1200",
        "larg": "14",
        "mat_default": None,
    })

    model.rows = rows
    model.recalculate_all()

    print("\nTest: DIVISAO_INDEPENDENTE Complete Protection")
    print("=" * 80)

    # Test Row 1
    print("\nRow 1: DIVISAO_INDEPENDENTE + Keywords in Descricao_Livre")
    print(f"  Descricao_Livre: {model.rows[0].get('descricao_livre')}")
    mat_def_1 = model.rows[0].get("mat_default")
    tipo_1 = model.rows[0].get("tipo")
    familia_1 = model.rows[0].get("familia")
    comp_res_1 = model.rows[0].get("comp_res")
    larg_res_1 = model.rows[0].get("larg_res")
    esp_res_1 = model.rows[0].get("esp_res")
    
    print(f"  mat_default: {mat_def_1}")
    print(f"  tipo: {tipo_1}")
    print(f"  familia: {familia_1}")
    print(f"  comp_res: {comp_res_1}")
    print(f"  larg_res: {larg_res_1}")
    print(f"  esp_res: {esp_res_1}")
    
    all_pass_1 = (
        mat_def_1 is None or mat_def_1 == "",
        tipo_1 is None or tipo_1 == "",
        familia_1 is None or familia_1 == "",
        comp_res_1 == 2400.0,
        larg_res_1 == 1200.0,
        esp_res_1 == 14.0,
    )
    if all(all_pass_1):
        print("  ✓ PASS: No mat_default/tipo/familia; dimensions filled correctly")
    else:
        print("  ✗ FAIL: Row received unwanted assignments!")

    # Test Row 2
    print("\nRow 2: DIVISAO_INDEPENDENTE + Multiple Keywords")
    print(f"  Descricao_Livre: {model.rows[1].get('descricao_livre')}")
    mat_def_2 = model.rows[1].get("mat_default")
    tipo_2 = model.rows[1].get("tipo")
    familia_2 = model.rows[1].get("familia")
    comp_res_2 = model.rows[1].get("comp_res")
    larg_res_2 = model.rows[1].get("larg_res")
    esp_res_2 = model.rows[1].get("esp_res")
    
    print(f"  mat_default: {mat_def_2}")
    print(f"  tipo: {tipo_2}")
    print(f"  familia: {familia_2}")
    print(f"  comp_res: {comp_res_2}")
    print(f"  larg_res: {larg_res_2}")
    print(f"  esp_res: {esp_res_2}")
    
    all_pass_2 = (
        mat_def_2 is None or mat_def_2 == "",
        tipo_2 is None or tipo_2 == "",
        familia_2 is None or familia_2 == "",
        comp_res_2 == 2000.0,
        larg_res_2 == 1000.0,
        esp_res_2 == 10.0,
    )
    if all(all_pass_2):
        print("  ✓ PASS: No mat_default/tipo/familia; dimensions filled correctly")
    else:
        print("  ✗ FAIL: Row received unwanted assignments!")

    # Test Row 3 (normal line - for reference)
    print("\nRow 3: Regular VARAO line (for comparison)")
    print(f"  Descricao_Livre: {model.rows[2].get('descricao_livre')}")
    print(f"  mat_default: {model.rows[2].get('mat_default')}")
    print("  (Normal processing applies)")

    print("\n" + "=" * 80)
    if all(all_pass_1) and all(all_pass_2):
        print("✓ ALL TESTS PASSED: DIVISAO_INDEPENDENTE rows are completely protected")
    else:
        print("✗ SOME TESTS FAILED: DIVISAO_INDEPENDENTE still receiving assignments!")

