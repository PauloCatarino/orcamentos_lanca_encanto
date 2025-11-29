from PySide6 import QtWidgets

from Martelo_Orcamentos_V2.ui.pages.custeio_items import CusteioTableModel, DEF_LABEL_CNC_MIN, DEF_LABEL_CNC_5_MIN, DEF_LABEL_CNC_15_MIN, DEF_LABEL_EMBALAGEM, DEF_LABEL_COLAGEM


class FakePage:
    def production_mode(self):
        return "STD"

    def get_production_rate_info(self, key):
        mapping = {
            "EUROS_HORA_CNC": {"valor_std": 30.0},  # 30 €/h -> 0.5 €/min
            "EUROS_HORA_MO": {"valor_std": 24.0},   # 24 €/h -> 0.4 €/min
            "EUROS_EMBALAGEM_M3": {"valor_std": 100.0},
            "COLAGEM/REVESTIMENTO": {"valor_std": 10.0},
            # rates for piece-based CNC pricing (not used for manual CNC)
            "CNC_PRECO_PECA_BAIXO": {"valor_std": 2.0},
            "CNC_PRECO_PECA_MEDIO": {"valor_std": 3.0},
            "CNC_PRECO_PECA_ALTO": {"valor_std": 5.0},
        }
        return mapping.get(key)

    def dimension_values(self):
        return {}

    def _icon(self, name):
        return None
    def _apply_collapse_state(self):
        # no-op for tests
        return None


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    page = FakePage()
    # CusteioTableModel expects a QObject parent; provide None and attach the fake page
    model = CusteioTableModel(parent=None)
    model._page = page

    rows = []

    # 1) CNC (Min) - expect cp03_cnc_und = EUROS_HORA_CNC / 60 = 0.5 €/min
    rows.append({
        "def_peca": "CNC (Min)",
        "qt_und": 1,
        "qt_total": 10,
    })
    
    # 1b) MAO OBRA (Min) - expect cp08_mao_de_obra_und = (EUROS_HORA_MO / 60) × cp08_mao_de_obra factor
    # Note: cp08_mao_de_obra value will be set by recalculate_all based on row data
    rows.append({
        "def_peca": "MAO OBRA (Min)",
        "qt_und": 1,
        "qt_total": 5,
    })

    # 2) Embalagem (M3) - comp=1000mm, larg=500mm, esp=20mm -> volume per unit = 0.01 m3
    #    embal rate = 100 €/m3 -> cp07_embalagem_und = 0.01 * 100 = 1.0 €/und
    rows.append({
        "def_peca": "EMBALAGEM (M3)",
        "comp": "1000",
        "larg": "500",
        "esp": "20",
        "qt_und": 1,
        "qt_total": 2,
    })

    # 3) Colagem - comp=2000mm, larg=1000mm -> area per unit = 2.0 m2
    #    colagem rate = 10 €/m2 -> per unit = 20.0 €/und; total = 20 * qt_total
    rows.append({
        "def_peca": "COLAGEM/REVESTIMENTO (M2)",
        "comp": "2000",
        "larg": "1000",
        "qt_und": 1,
        "qt_total": 3,
    })

    model.rows = rows
    model.recalculate_all()

    for i, r in enumerate(model.rows):
        print(f"--- Row {i+1}: def_peca={r.get('def_peca')} ---")
        print("cp03_cnc_und:", r.get("cp03_cnc_und"))
        print("cp07_embalagem_und:", r.get("cp07_embalagem_und"))
        print("cp08_mao_de_obra_und:", r.get("cp08_mao_de_obra_und"))
        print("cp09_colagem_und:", r.get("cp09_colagem_und"))
        print("soma_custo_und:", r.get("soma_custo_und"))
        print("soma_custo_total:", r.get("soma_custo_total"))
        print("qt_total:", r.get("qt_total"))
        print()

    print("Done")
