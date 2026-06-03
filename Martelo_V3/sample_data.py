from __future__ import annotations

from typing import Dict, List

from .domain import (
    Dimensions,
    MaterialRule,
    ModuleDefinition,
    ModuleLineTemplate,
    RuleSet,
    money,
)


def default_dimensions() -> Dimensions:
    return Dimensions(h=2400, l=900, p=550)


def default_rules() -> RuleSet:
    general: Dict[str, MaterialRule] = {
        "Laterais": MaterialRule("Laterais", "PL-MEL-19", "Melamina branca 19 mm", "PLACAS", "M2", money("12.80")),
        "Tampos e Bases": MaterialRule("Tampos e Bases", "PL-MEL-19", "Melamina branca 19 mm", "PLACAS", "M2", money("12.80")),
        "Costas": MaterialRule("Costas", "MDF-08", "MDF branco 8 mm", "PLACAS", "M2", money("7.20")),
        "Prateleiras": MaterialRule("Prateleiras", "PL-MEL-19", "Melamina branca 19 mm", "PLACAS", "M2", money("12.80")),
        "Portas Abrir 1": MaterialRule("Portas Abrir 1", "PT-LAC-19", "Porta lacada mate 19 mm", "PLACAS", "M2", money("24.50")),
        "Portas Abrir 2": MaterialRule("Portas Abrir 2", "PT-MEL-19", "Porta melamina 19 mm", "PLACAS", "M2", money("16.20")),
        "Painel Porta Correr 1": MaterialRule("Painel Porta Correr 1", "PC-LAC-19", "Painel correr lacado 19 mm", "SISTEMAS CORRER", "M2", money("27.00")),
        "Calha Superior 2 SPP": MaterialRule("Calha Superior 2 SPP", "SPP-SUP-2", "Calha superior 2 folhas", "SISTEMAS CORRER", "ML", money("11.50")),
        "Calha Inferior 2 SPP": MaterialRule("Calha Inferior 2 SPP", "SPP-INF-2", "Calha inferior 2 folhas", "SISTEMAS CORRER", "ML", money("10.40")),
        "Rodizio Correr": MaterialRule("Rodizio Correr", "SPP-ROD", "Rodízio porta correr", "SISTEMAS CORRER", "UN", money("8.90")),
        "Dobradicas Base": MaterialRule("Dobradicas Base", "DOB-110", "Dobradiça 110 graus", "FERRAGENS", "UN", money("1.35")),
        "Puxadores Base": MaterialRule("Puxadores Base", "PUX-STD", "Puxador standard", "FERRAGENS", "UN", money("3.80")),
        "Suportes Prateleira": MaterialRule("Suportes Prateleira", "SUP-PRAT", "Suporte prateleira", "FERRAGENS", "UN", money("0.16")),
        "Corrediças Gaveta": MaterialRule("Corrediças Gaveta", "COR-GAV", "Par corrediças gaveta", "FERRAGENS", "PAR", money("8.20")),
        "Cozinha Exterior": MaterialRule("Cozinha Exterior", "COZ-MEL-19", "Melamina cozinha exterior 19 mm", "PLACAS", "M2", money("18.40")),
        "Cozinha Interior": MaterialRule("Cozinha Interior", "COZ-INT-19", "Melamina cozinha interior 19 mm", "PLACAS", "M2", money("14.20")),
        "WC Hidrofugo": MaterialRule("WC Hidrofugo", "HID-19", "MDF hidrófugo 19 mm", "PLACAS", "M2", money("22.90")),
        "Ferragem WC": MaterialRule("Ferragem WC", "WC-FER", "Kit ferragem WC", "FERRAGENS", "UN", money("9.50")),
    }
    return RuleSet(general=general)


def demo_item_rules() -> Dict[str, MaterialRule]:
    return {
        "Portas Abrir 1": MaterialRule(
            "Portas Abrir 1",
            "PT-LAC-PREM",
            "Porta lacada premium definida no item",
            "PLACAS",
            "M2",
            money("31.75"),
            source="Dados Items",
        )
    }


def demo_modules() -> List[ModuleDefinition]:
    common_vars = ("H", "L", "P", "HM", "LM", "PM")
    return [
        ModuleDefinition(
            module_id="wardrobe_open_1",
            name="Roupeiro | 1 porta abrir + 5 prateleiras",
            family="Roupeiros",
            description="Corpo simples com uma frente de abrir e interior de prateleiras.",
            variables=common_vars,
            inherited_rules=("Laterais", "Tampos e Bases", "Costas", "Prateleiras", "Portas Abrir 1"),
            item_overrides=("Portas Abrir 1", "Puxadores Base", "Dobradicas Base"),
            validations=("porta_unica", "prateleiras_5", "ferragens_porta"),
            lines=(
                ModuleLineTemplate("lat_1p", "peca", "Laterais", "Laterais", "PLACAS", quantity=2, comp_expr="HM", larg_expr="PM", esp_expr="19", edge_long_sides=1, labor_minutes=6),
                ModuleLineTemplate("top_1p", "peca", "Tampo superior", "Tampos e Bases", "PLACAS", comp_expr="LM", larg_expr="PM", esp_expr="19", edge_long_sides=1, labor_minutes=4),
                ModuleLineTemplate("base_1p", "peca", "Base", "Tampos e Bases", "PLACAS", comp_expr="LM", larg_expr="PM", esp_expr="19", edge_long_sides=1, labor_minutes=4),
                ModuleLineTemplate("costa_1p", "peca", "Costa", "Costas", "PLACAS", comp_expr="HM", larg_expr="LM", esp_expr="8", labor_minutes=5),
                ModuleLineTemplate("prat_1p", "peca", "Prateleira amovível", "Prateleiras", "PLACAS", quantity=5, comp_expr="LM - 36", larg_expr="PM - 20", esp_expr="19", edge_long_sides=1, labor_minutes=3),
                ModuleLineTemplate("porta_1p", "peca", "Porta abrir", "Portas Abrir 1", "PLACAS", comp_expr="HM - 4", larg_expr="LM - 4", esp_expr="19", edge_long_sides=2, edge_short_sides=2, finish_faces=2, labor_minutes=10),
                ModuleLineTemplate("dob_1p", "ferragem", "Dobradiças", "Dobradicas Base", "FERRAGENS", quantity=4, labor_minutes=2),
                ModuleLineTemplate("pux_1p", "ferragem", "Puxador", "Puxadores Base", "FERRAGENS", quantity=1, labor_minutes=2),
                ModuleLineTemplate("sup_1p", "ferragem", "Suportes prateleira", "Suportes Prateleira", "FERRAGENS", quantity=20),
            ),
        ),
        ModuleDefinition(
            module_id="wardrobe_open_2",
            name="Roupeiro | 2 portas abrir + 5 prateleiras",
            family="Roupeiros",
            description="Corpo simples com frente dupla e cinco prateleiras.",
            variables=common_vars,
            inherited_rules=("Laterais", "Tampos e Bases", "Costas", "Prateleiras", "Portas Abrir 1"),
            item_overrides=("Portas Abrir 1", "Puxadores Base", "Dobradicas Base"),
            validations=("duas_portas", "divisao_frente", "ferragens_duplicadas"),
            lines=(
                ModuleLineTemplate("lat_2p", "peca", "Laterais", "Laterais", "PLACAS", quantity=2, comp_expr="HM", larg_expr="PM", esp_expr="19", edge_long_sides=1, labor_minutes=6),
                ModuleLineTemplate("top_2p", "peca", "Tampo superior", "Tampos e Bases", "PLACAS", comp_expr="LM", larg_expr="PM", esp_expr="19", edge_long_sides=1, labor_minutes=4),
                ModuleLineTemplate("base_2p", "peca", "Base", "Tampos e Bases", "PLACAS", comp_expr="LM", larg_expr="PM", esp_expr="19", edge_long_sides=1, labor_minutes=4),
                ModuleLineTemplate("costa_2p", "peca", "Costa", "Costas", "PLACAS", comp_expr="HM", larg_expr="LM", esp_expr="8", labor_minutes=5),
                ModuleLineTemplate("prat_2p", "peca", "Prateleira amovível", "Prateleiras", "PLACAS", quantity=5, comp_expr="LM - 36", larg_expr="PM - 20", esp_expr="19", edge_long_sides=1, labor_minutes=3),
                ModuleLineTemplate("porta_2p", "peca", "Portas abrir", "Portas Abrir 1", "PLACAS", quantity=2, comp_expr="HM - 4", larg_expr="LM / 2 - 4", esp_expr="19", edge_long_sides=2, edge_short_sides=2, finish_faces=2, labor_minutes=10),
                ModuleLineTemplate("dob_2p", "ferragem", "Dobradiças", "Dobradicas Base", "FERRAGENS", quantity=8, labor_minutes=4),
                ModuleLineTemplate("pux_2p", "ferragem", "Puxadores", "Puxadores Base", "FERRAGENS", quantity=2, labor_minutes=3),
                ModuleLineTemplate("sup_2p", "ferragem", "Suportes prateleira", "Suportes Prateleira", "FERRAGENS", quantity=20),
            ),
        ),
        ModuleDefinition(
            module_id="wardrobe_sliding",
            name="Roupeiro | portas correr 2 folhas",
            family="Roupeiros",
            description="Frente de correr com duas folhas, calhas e rodízios.",
            variables=common_vars,
            inherited_rules=("Painel Porta Correr 1", "Calha Superior 2 SPP", "Calha Inferior 2 SPP", "Rodizio Correr"),
            item_overrides=("Painel Porta Correr 1", "Calha Superior 2 SPP", "Calha Inferior 2 SPP"),
            validations=("sistema_correr", "calhas", "rodizios"),
            lines=(
                ModuleLineTemplate("lat_cor", "peca", "Laterais", "Laterais", "PLACAS", quantity=2, comp_expr="HM", larg_expr="PM", esp_expr="19", edge_long_sides=1, labor_minutes=6),
                ModuleLineTemplate("painel_cor", "peca", "Painéis de correr", "Painel Porta Correr 1", "SISTEMAS CORRER", quantity=2, comp_expr="HM - 30", larg_expr="LM / 2 + 35", esp_expr="19", edge_long_sides=2, edge_short_sides=2, finish_faces=2, labor_minutes=12),
                ModuleLineTemplate("calha_sup", "ferragem", "Calha superior", "Calha Superior 2 SPP", "SISTEMAS CORRER", quantity_expr="LM / 1000", labor_minutes=5),
                ModuleLineTemplate("calha_inf", "ferragem", "Calha inferior", "Calha Inferior 2 SPP", "SISTEMAS CORRER", quantity_expr="LM / 1000", labor_minutes=5),
                ModuleLineTemplate("rod_cor", "ferragem", "Rodízios", "Rodizio Correr", "SISTEMAS CORRER", quantity=4, labor_minutes=6),
            ),
        ),
        ModuleDefinition(
            module_id="kitchen_base",
            name="Cozinha | módulo baixo 2 portas",
            family="Cozinhas",
            description="Módulo baixo de cozinha com duas portas e prateleira interior.",
            variables=common_vars,
            inherited_rules=("Cozinha Exterior", "Cozinha Interior", "Dobradicas Base", "Puxadores Base"),
            item_overrides=("Cozinha Exterior", "Puxadores Base"),
            validations=("cozinha_base", "rodape", "ferragem_portas"),
            lines=(
                ModuleLineTemplate("coz_lat", "peca", "Laterais cozinha", "Cozinha Interior", "PLACAS", quantity=2, comp_expr="HM", larg_expr="PM", esp_expr="19", edge_long_sides=1, labor_minutes=6),
                ModuleLineTemplate("coz_base", "peca", "Base cozinha", "Cozinha Interior", "PLACAS", comp_expr="LM", larg_expr="PM", esp_expr="19", edge_long_sides=1, labor_minutes=5),
                ModuleLineTemplate("coz_prat", "peca", "Prateleira cozinha", "Cozinha Interior", "PLACAS", comp_expr="LM - 36", larg_expr="PM - 20", esp_expr="19", edge_long_sides=1, labor_minutes=4),
                ModuleLineTemplate("coz_portas", "peca", "Portas cozinha", "Cozinha Exterior", "PLACAS", quantity=2, comp_expr="HM - 6", larg_expr="LM / 2 - 3", esp_expr="19", edge_long_sides=2, edge_short_sides=2, finish_faces=2, labor_minutes=9),
                ModuleLineTemplate("coz_dob", "ferragem", "Dobradiças cozinha", "Dobradicas Base", "FERRAGENS", quantity=4, labor_minutes=4),
                ModuleLineTemplate("coz_pux", "ferragem", "Puxadores cozinha", "Puxadores Base", "FERRAGENS", quantity=2, labor_minutes=2),
            ),
        ),
        ModuleDefinition(
            module_id="wc_base",
            name="WC | móvel lavatório 2 portas",
            family="WC",
            description="Móvel WC hidrófugo com duas portas e travessa técnica.",
            variables=common_vars,
            inherited_rules=("WC Hidrofugo", "Ferragem WC", "Puxadores Base"),
            item_overrides=("WC Hidrofugo", "Ferragem WC"),
            validations=("hidrofugo", "recorte_lavatorio", "ferragem_wc"),
            lines=(
                ModuleLineTemplate("wc_lat", "peca", "Laterais WC", "WC Hidrofugo", "PLACAS", quantity=2, comp_expr="HM", larg_expr="PM", esp_expr="19", edge_long_sides=1, labor_minutes=7),
                ModuleLineTemplate("wc_base", "peca", "Base WC", "WC Hidrofugo", "PLACAS", comp_expr="LM", larg_expr="PM", esp_expr="19", edge_long_sides=1, labor_minutes=5),
                ModuleLineTemplate("wc_trav", "peca", "Travessa técnica", "WC Hidrofugo", "PLACAS", quantity=2, comp_expr="LM", larg_expr="90", esp_expr="19", edge_long_sides=1, labor_minutes=4),
                ModuleLineTemplate("wc_porta", "peca", "Portas WC", "WC Hidrofugo", "PLACAS", quantity=2, comp_expr="HM - 6", larg_expr="LM / 2 - 3", esp_expr="19", edge_long_sides=2, edge_short_sides=2, finish_faces=2, labor_minutes=10),
                ModuleLineTemplate("wc_kit", "ferragem", "Kit ferragem WC", "Ferragem WC", "FERRAGENS", quantity=1, labor_minutes=8),
                ModuleLineTemplate("wc_pux", "ferragem", "Puxadores WC", "Puxadores Base", "FERRAGENS", quantity=2, labor_minutes=2),
            ),
        ),
    ]
