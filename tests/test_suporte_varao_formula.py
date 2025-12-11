"""
Test to verify that SUPORTE VARAO (parent-child relationship) calculates correctly:
- qt_und of SUPORTE VARAO should be 2 × qt_und of sibling VARAO
- comp of SUPORTE VARAO should be EMPTY (not inherited from parent)
- This is a crucial formula for furniture support bar calculations
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


def compare_floats(a, b, tolerance=0.01):
    """Compare two floats with tolerance"""
    if a is None or b is None:
        return a == b
    return abs(float(a) - float(b)) <= tolerance


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    page = FakePage()
    model = CusteioTableModel(parent=None)
    model._page = page

    rows = []

    # Create parent-child structure:
    # 1. Parent row (PRATELEIRA)
    # 2. Child VARAO (regular bar, inherits comp from parent)
    # 3. Child SUPORTE VARAO (support bars, should have qt_und=2× VARAO, comp empty)

    # Parent row (explicit children tokens via '+')
    rows.append({
        "def_peca": "PRATELEIRA+VARAO+SUPORTE VARAO",
        "descricao_livre": "Example parent",
        "qt_mod": "1",
        "qt_und": "1",
        "comp": "1000",
        "larg": "600",
        "esp": "14",
        "_row_type": None,
        "_uid": "uid-parent-1",
    })

    # Child VARAO
    rows.append({
        "def_peca": "VARAO",
        "descricao_livre": "Regular varao",
        "qt_mod": "1",
        "qt_und": "1",
        "comp": "",
        "larg": "14",
        "_row_type": None,
        "_parent_uid": "uid-parent-1",
        "_child_source": "VARAO",
        "_uid": "uid-varao-1",
    })

    # Child SUPORTE VARAO
    rows.append({
        "def_peca": "SUPORTE VARAO",
        "descricao_livre": "Support bar",
        "qt_mod": "1",
        "qt_und": "1",  # Will be overridden to 2 by formula
        "comp": "",
        "larg": "14",
        "_row_type": None,
        "_parent_uid": "uid-parent-1",
        "_child_source": "SUPORTE VARAO",
        "_uid": "uid-support-1",
    })

    model.rows = rows
    model.recalculate_all()

    print("\nTest: SUPORTE VARAO Formula (qt_und = 2 × VARAO)")
    print("=" * 80)

    # Check parent
    parent_row = model.rows[0]
    print("\nParent Row: PRATELEIRA")
    print(f"  def_peca: {parent_row.get('def_peca')}")
    print(f"  qt_und: {parent_row.get('qt_und')}")
    print(f"  comp: {parent_row.get('comp')}")
    print(f"  comp_res: {parent_row.get('comp_res')}")

    # Check VARAO
    varao_row = model.rows[1]
    print("\nChild Row 1: VARAO")
    print(f"  def_peca: {varao_row.get('def_peca')}")
    print(f"  qt_und: {varao_row.get('qt_und')}")
    print(f"  comp: {varao_row.get('comp')}")
    print(f"  comp_res: {varao_row.get('comp_res')}")
    # Ensure numeric
    varao_qt_und = float(varao_row.get("qt_und") or 1)

    # Check SUPORTE VARAO
    support_row = model.rows[2]
    print("\nChild Row 2: SUPORTE VARAO")
    print(f"  def_peca: {support_row.get('def_peca')}")
    print(f"  _normalized_child: {support_row.get('_normalized_child')}")
    print(f"  _regra_nome: {support_row.get('_regra_nome')}")
    print(f"  qt_und: {support_row.get('qt_und')} (expected: 2 × {varao_qt_und} = {2 * (varao_qt_und or 1)})")
    print(f"  comp: '{support_row.get('comp')}' (expected: empty string)")
    print(f"  comp_res: {support_row.get('comp_res')} (expected: None or empty)")
    print(f"  _qt_formula_value: {support_row.get('_qt_formula_value')}")
    print(f"  _qt_rule_tooltip: {support_row.get('_qt_rule_tooltip')}")

    # Validation
    expected_support_qt_und = 2 * (varao_qt_und or 1)
    actual_support_qt_und = support_row.get("qt_und")
    support_comp = support_row.get("comp")
    support_comp_res = support_row.get("comp_res")

    print("\n" + "=" * 80)
    print("Validation Results:")
    print("-" * 80)

    test_pass = True

    # Test 1: qt_und = 2 × VARAO
    test1_pass = compare_floats(actual_support_qt_und, expected_support_qt_und, tolerance=0.01)
    status1 = "✓ PASS" if test1_pass else "✗ FAIL"
    print(f"{status1}: SUPORTE VARAO qt_und = {actual_support_qt_und} (expected {expected_support_qt_und})")
    test_pass = test_pass and test1_pass

    # Test 2: comp = empty
    test2_pass = (support_comp == "" or support_comp is None)
    status2 = "✓ PASS" if test2_pass else "✗ FAIL"
    print(f"{status2}: SUPORTE VARAO comp = '{support_comp}' (expected empty)")
    test_pass = test_pass and test2_pass

    # Test 3: comp_res = empty/None
    test3_pass = (support_comp_res == "" or support_comp_res is None)
    status3 = "✓ PASS" if test3_pass else "✗ FAIL"
    print(f"{status3}: SUPORTE VARAO comp_res = {support_comp_res} (expected None/empty)")
    test_pass = test_pass and test3_pass

    # Test 4: VARAO inherits comp from parent
    varao_comp_res = varao_row.get("comp_res")
    test4_pass = compare_floats(varao_comp_res, 1000.0, tolerance=0.01)
    status4 = "✓ PASS" if test4_pass else "✗ FAIL"
    print(f"{status4}: VARAO inherits comp_res = {varao_comp_res} (expected 1000)")
    test_pass = test_pass and test4_pass

    print("=" * 80)
    if test_pass:
        print("Overall: ✓ ALL TESTS PASSED")
    else:
        print("Overall: ✗ SOME TESTS FAILED")
        exit(1)
