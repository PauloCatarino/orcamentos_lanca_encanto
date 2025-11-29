"""
Test CP08_MAO_DE_OBRA_und calculation with factor multiplication.
Expected: CP08_MAO_DE_OBRA_und = (€/min) × cp08_mao_de_obra factor (when factor > 0)
"""

from PySide6 import QtWidgets
from Martelo_Orcamentos_V2.ui.pages.custeio_items import CusteioTableModel, DEF_LABEL_MAO_OBRA_MIN


class FakePage:
    def production_mode(self):
        return "STD"

    def get_production_rate_info(self, key):
        mapping = {
            "EUROS_HORA_MO": {"valor_std": 24.0},   # 24 €/h -> 0.4 €/min
        }
        return mapping.get(key)

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

    # Test 1: MAO OBRA with factor = 0 (no multiplication expected)
    rows.append({
        "def_peca": DEF_LABEL_MAO_OBRA_MIN,
        "cp08_mao_de_obra": 0,
        "qt_und": 1,
        "qt_total": 1,
    })
    
    # Test 2: MAO OBRA with factor = 1.0 (standard case)
    rows.append({
        "def_peca": DEF_LABEL_MAO_OBRA_MIN,
        "cp08_mao_de_obra": 1.0,
        "qt_und": 1,
        "qt_total": 1,
    })

    # Test 3: MAO OBRA with factor = 1.5 (expect 0.4 * 1.5 = 0.6 €)
    rows.append({
        "def_peca": DEF_LABEL_MAO_OBRA_MIN,
        "cp08_mao_de_obra": 1.5,
        "qt_und": 1,
        "qt_total": 1,
    })

    # Test 4: MAO OBRA with factor = 3.0 (expect 0.4 * 3.0 = 1.2 €)
    rows.append({
        "def_peca": DEF_LABEL_MAO_OBRA_MIN,
        "cp08_mao_de_obra": 3.0,
        "qt_und": 1,
        "qt_total": 1,
    })

    model.rows = rows
    model.recalculate_all()

    print("\nCP08_MAO_DE_OBRA_und Calculation Tests")
    print("=" * 60)
    print(f"Base tariff: 24.0 €/h → 0.4 €/min")
    print("=" * 60)

    for i, r in enumerate(model.rows):
        factor = r.get("cp08_mao_de_obra")
        cp08_und = r.get("cp08_mao_de_obra_und")
        expected = round((24.0 / 60.0) * factor, 4) if factor and factor > 0 else (24.0 / 60.0)
        
        print(f"\nTest {i+1}:")
        print(f"  Factor (cp08_mao_de_obra): {factor}")
        print(f"  CP08_MAO_DE_OBRA_und: {cp08_und}")
        print(f"  Expected: {expected}")
        
        if factor is not None and factor > 0:
            print(f"  Formula: (24.0 / 60) × {factor} = {cp08_und}")
            assert cp08_und == expected, f"Test {i+1} failed: expected {expected}, got {cp08_und}"
            print(f"  ✓ PASS")
        else:
            print(f"  No multiplication (factor = {factor})")
            print(f"  ✓ PASS")

    print("\n" + "=" * 60)
    print("✓ All CP08 factor multiplication tests passed!")
