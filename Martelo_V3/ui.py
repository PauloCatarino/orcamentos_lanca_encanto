from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

from PySide6 import QtCore, QtGui, QtWidgets

from .domain import (
    CusteioItemV3,
    Dimensions,
    LocalOverride,
    RuleSet,
    build_custeio_lines,
    build_proposal_summary,
    module_by_id,
    money,
    validate_configuration,
)
from .sample_data import default_dimensions, default_rules, demo_item_rules, demo_modules


def _fmt_money(value) -> str:
    return f"{money(value):,.2f} €".replace(",", " ")


def _fmt_num(value: Optional[float]) -> str:
    if value is None:
        return "-"
    return f"{value:.0f}" if abs(value - round(value)) < 0.001 else f"{value:.2f}"


@dataclass
class DemoState:
    module_id: str = "wardrobe_open_1"
    dimensions: Dimensions = field(default_factory=default_dimensions)
    rules: RuleSet = field(default_factory=default_rules)
    local_overrides: Dict[str, LocalOverride] = field(default_factory=dict)

    def module(self):
        return module_by_id(demo_modules(), self.module_id)

    def rows(self) -> List[CusteioItemV3]:
        return build_custeio_lines(self.module(), self.dimensions, self.rules, self.local_overrides)

    def proposal(self):
        return build_proposal_summary(self.rows())


class MarteloV3Window(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.state = DemoState()
        self.modules = demo_modules()
        self.setWindowTitle("Martelo V3 - Protótipo de Orçamentação Guiada")
        self.resize(1380, 840)
        self._build_ui()
        self.refresh_all()

    def _build_ui(self) -> None:
        root = QtWidgets.QWidget()
        outer = QtWidgets.QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.nav = QtWidgets.QListWidget()
        self.nav.setFixedWidth(210)
        self.nav.setObjectName("sideNav")
        for label in (
            "Orçamentos",
            "Items",
            "Configurador",
            "Custeio",
            "Proposta",
            "Produção",
            "Bibliotecas",
            "Configurações",
        ):
            item = QtWidgets.QListWidgetItem(label)
            item.setSizeHint(QtCore.QSize(180, 42))
            self.nav.addItem(item)
        self.nav.currentRowChanged.connect(self._on_nav_changed)

        content = QtWidgets.QWidget()
        content_layout = QtWidgets.QVBoxLayout(content)
        content_layout.setContentsMargins(18, 14, 18, 14)
        content_layout.setSpacing(12)

        self.header = QtWidgets.QLabel()
        self.header.setObjectName("title")
        content_layout.addWidget(self.header)

        self.stack = QtWidgets.QStackedWidget()
        content_layout.addWidget(self.stack, 1)

        self._build_orcamentos_page()
        self._build_items_page()
        self._build_configurador_page()
        self._build_custeio_page()
        self._build_proposta_page()
        self._build_producao_page()
        self._build_bibliotecas_page()
        self._build_config_page()

        outer.addWidget(self.nav)
        outer.addWidget(content, 1)
        self.setCentralWidget(root)
        self._apply_style()
        self.nav.setCurrentRow(2)

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow { background: #f4f6f8; }
            QListWidget#sideNav { background: #20252b; color: #dbe1e8; border: 0; padding: 10px 8px; }
            QListWidget#sideNav::item { padding: 10px 12px; border-radius: 6px; }
            QListWidget#sideNav::item:selected { background: #2f7d7e; color: white; }
            QLabel#title { font-size: 20px; font-weight: 700; color: #1f2933; }
            QLabel.sectionTitle { font-size: 14px; font-weight: 700; color: #1f2933; }
            QLabel.metric { background: white; border: 1px solid #d9e0e7; border-radius: 6px; padding: 10px; }
            QTableWidget { background: white; border: 1px solid #d9e0e7; gridline-color: #edf1f4; }
            QHeaderView::section { background: #e9eef2; color: #23313d; padding: 6px; border: 0; font-weight: 700; }
            QPushButton { padding: 7px 12px; border-radius: 5px; background: #e4e9ee; color: #1f2933; }
            QPushButton#primary { background: #2f7d7e; color: white; font-weight: 700; }
            QPushButton#danger { background: #9b3d3d; color: white; font-weight: 700; }
            QTabWidget::pane { border: 1px solid #d9e0e7; background: white; }
            QTabBar::tab { padding: 8px 12px; background: #e9eef2; border: 1px solid #d9e0e7; }
            QTabBar::tab:selected { background: white; border-bottom-color: white; font-weight: 700; }
            """
        )

    def _on_nav_changed(self, row: int) -> None:
        self.stack.setCurrentIndex(max(0, row))
        text = self.nav.item(row).text() if row >= 0 and self.nav.item(row) else "Martelo V3"
        self.header.setText(text)
        self.refresh_all()

    def _label(self, text: str, class_name: str = "") -> QtWidgets.QLabel:
        label = QtWidgets.QLabel(text)
        label.setWordWrap(True)
        if class_name:
            label.setProperty("class", class_name)
        return label

    def _primary_button(self, text: str) -> QtWidgets.QPushButton:
        btn = QtWidgets.QPushButton(text)
        btn.setObjectName("primary")
        return btn

    def _table(self, columns: Sequence[str]) -> QtWidgets.QTableWidget:
        table = QtWidgets.QTableWidget(0, len(columns))
        table.setHorizontalHeaderLabels(list(columns))
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        table.horizontalHeader().setStretchLastSection(True)
        return table

    def _build_orcamentos_page(self) -> None:
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        layout.addWidget(self._label("Orçamento demo isolado do V2. A fase atual não grava nem importa dados reais.", "sectionTitle"))
        self.tbl_orcamentos = self._table(["Ano", "Nº", "Versão", "Cliente", "Estado", "Preço previsto"])
        layout.addWidget(self.tbl_orcamentos, 1)
        btn = self._primary_button("Abrir orçamento demo")
        btn.clicked.connect(lambda: self.nav.setCurrentRow(2))
        layout.addWidget(btn, 0, QtCore.Qt.AlignLeft)
        self.stack.addWidget(page)

    def _build_items_page(self) -> None:
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        layout.addWidget(self._label("Items do orçamento com módulo sugerido, estado de validação e preço previsto.", "sectionTitle"))
        self.tbl_items = self._table(["Item", "Descrição", "Módulo", "Medidas", "Estado", "Preço"])
        layout.addWidget(self.tbl_items, 1)
        btn = self._primary_button("Configurar item selecionado")
        btn.clicked.connect(lambda: self.nav.setCurrentRow(2))
        layout.addWidget(btn, 0, QtCore.Qt.AlignLeft)
        self.stack.addWidget(page)

    def _build_configurador_page(self) -> None:
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        self.tabs = QtWidgets.QTabWidget()
        layout.addWidget(self.tabs, 1)
        self._build_tab_resumo()
        self._build_tab_modulo()
        self._build_tab_rules()
        self._build_tab_generated()
        self._build_tab_costs()
        self._build_tab_calculations()
        self._build_tab_validation()
        self.stack.addWidget(page)

    def _build_tab_resumo(self) -> None:
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        self.lbl_resumo = self._label("")
        layout.addWidget(self.lbl_resumo)
        self.tbl_resumo_metrics = self._table(["Indicador", "Valor"])
        layout.addWidget(self.tbl_resumo_metrics, 1)
        self.tabs.addTab(tab, "Resumo do item")

    def _build_tab_modulo(self) -> None:
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QGridLayout(tab)
        self.module_combo = QtWidgets.QComboBox()
        for module in self.modules:
            self.module_combo.addItem(module.name, module.module_id)
        self.module_combo.currentIndexChanged.connect(self._on_module_changed)
        layout.addWidget(self._label("Módulo configurável", "sectionTitle"), 0, 0, 1, 3)
        layout.addWidget(self.module_combo, 1, 0, 1, 3)

        self.spin_h = self._spin(300, 3200)
        self.spin_l = self._spin(200, 4000)
        self.spin_p = self._spin(150, 900)
        for idx, (label, spin) in enumerate((("H", self.spin_h), ("L", self.spin_l), ("P", self.spin_p))):
            layout.addWidget(QtWidgets.QLabel(label), 2, idx)
            layout.addWidget(spin, 3, idx)
            spin.valueChanged.connect(self._on_dimensions_changed)
        self.lbl_module_card = self._label("")
        layout.addWidget(self.lbl_module_card, 4, 0, 1, 3)
        btn = self._primary_button("Recalcular peças e custos")
        btn.clicked.connect(self.refresh_all)
        layout.addWidget(btn, 5, 0, 1, 3, QtCore.Qt.AlignLeft)
        layout.setRowStretch(6, 1)
        self.tabs.addTab(tab, "Módulo e medidas")

    def _spin(self, min_value: int, max_value: int) -> QtWidgets.QSpinBox:
        spin = QtWidgets.QSpinBox()
        spin.setRange(min_value, max_value)
        spin.setSingleStep(10)
        spin.setSuffix(" mm")
        return spin

    def _build_tab_rules(self) -> None:
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        info = self._label("Mantém os 3 níveis: Dados Gerais, Dados Items e Edição Local no Custeio.", "sectionTitle")
        layout.addWidget(info)
        toolbar = QtWidgets.QHBoxLayout()
        btn_item = self._primary_button("Aplicar override Dados Items nas portas")
        btn_item.clicked.connect(self._apply_item_override)
        btn_reset = QtWidgets.QPushButton("Limpar Dados Items demo")
        btn_reset.clicked.connect(self._reset_item_overrides)
        toolbar.addWidget(btn_item)
        toolbar.addWidget(btn_reset)
        toolbar.addStretch(1)
        layout.addLayout(toolbar)
        self.tbl_rules = self._table(["Grupo", "Fonte", "Referência", "Descrição", "Custo unit."])
        layout.addWidget(self.tbl_rules, 1)
        self.tabs.addTab(tab, "Materiais/Ferragens")

    def _build_tab_generated(self) -> None:
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        self.tbl_generated = self._table(["Tipo", "Descrição", "Qtd", "Comp", "Larg", "Esp", "Grupo"])
        layout.addWidget(self.tbl_generated, 1)
        self.tabs.addTab(tab, "Peças geradas")

    def _build_tab_costs(self) -> None:
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        self.tbl_costs = self._table(["Descrição", "Material", "Orla", "Acab.", "Produção", "Total"])
        layout.addWidget(self.tbl_costs, 1)
        self.tabs.addTab(tab, "Custos")

    def _build_tab_calculations(self) -> None:
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        layout.addWidget(
            self._label(
                "Decomposição auditável: cada parcela mostra a fórmula usada para chegar ao custo da linha.",
                "sectionTitle",
            )
        )
        self.tbl_calculations = self._table([
            "Linha",
            "Uso",
            "Material/Ferragem",
            "Orla",
            "Acabamento",
            "Produção",
            "Total",
        ])
        layout.addWidget(self.tbl_calculations, 1)
        self.tabs.addTab(tab, "Cálculo linha")

    def _build_tab_validation(self) -> None:
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        self.tbl_validation = self._table(["Estado", "Validação"])
        layout.addWidget(self.tbl_validation, 1)
        self.tabs.addTab(tab, "Validação")

    def _build_custeio_page(self) -> None:
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        toolbar = QtWidgets.QHBoxLayout()
        btn_override = self._primary_button("Aplicar override local na porta")
        btn_override.clicked.connect(self._apply_local_override)
        btn_reset = QtWidgets.QPushButton("Limpar overrides locais")
        btn_reset.clicked.connect(self._reset_local_overrides)
        toolbar.addWidget(btn_override)
        toolbar.addWidget(btn_reset)
        toolbar.addStretch(1)
        layout.addLayout(toolbar)
        self.tbl_custeio = self._table([
            "Linha",
            "Tipo",
            "Fórmulas",
            "Resolvido",
            "Uso",
            "Fonte regra",
            "Material/Ferragem",
            "Total",
            "Override",
        ])
        layout.addWidget(self.tbl_custeio, 1)
        self.stack.addWidget(page)

    def _build_proposta_page(self) -> None:
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        layout.addWidget(self._label("Pré-visualização comercial gerada a partir do custeio interno.", "sectionTitle"))
        self.tbl_proposal = self._table(["Campo", "Valor"])
        layout.addWidget(self.tbl_proposal, 1)
        self.lbl_proposal_notes = self._label("")
        layout.addWidget(self.lbl_proposal_notes)
        self.stack.addWidget(page)

    def _build_producao_page(self) -> None:
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        layout.addWidget(self._label("Preparação futura: lista de material, lista de ferragens, desenhos e integração controlada com CUT-RITE/IMOS/PHC.", "sectionTitle"))
        self.tbl_producao = self._table(["Saída", "Estado demo", "Origem"])
        layout.addWidget(self.tbl_producao, 1)
        self.stack.addWidget(page)

    def _build_bibliotecas_page(self) -> None:
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        layout.addWidget(self._label("Catálogo V3 de módulos com ficha técnica, variáveis e validações.", "sectionTitle"))
        self.tbl_library = self._table(["Família", "Módulo", "Variáveis", "Regras herdadas", "Validações"])
        layout.addWidget(self.tbl_library, 1)
        layout.addWidget(self._label("Referências analisadas para evolução do V3.", "sectionTitle"))
        self.tbl_references = self._table(["Referência", "Padrão observado", "Aplicação no Martelo V3"])
        layout.addWidget(self.tbl_references, 1)
        self.stack.addWidget(page)

    def _build_config_page(self) -> None:
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        self.tbl_config = self._table(["Área", "Decisão V3"])
        layout.addWidget(self.tbl_config, 1)
        layout.addWidget(self._label("Instalação local com base de dados partilhada no servidor da empresa.", "sectionTitle"))
        self.tbl_server = self._table(["Camada", "Comportamento recomendado"])
        layout.addWidget(self.tbl_server, 1)
        self.stack.addWidget(page)

    def _on_module_changed(self) -> None:
        self.state.module_id = self.module_combo.currentData()
        self.state.local_overrides.clear()
        self.refresh_all()

    def _on_dimensions_changed(self) -> None:
        self.state.dimensions = Dimensions(
            h=float(self.spin_h.value()),
            l=float(self.spin_l.value()),
            p=float(self.spin_p.value()),
        )
        self.refresh_all(skip_spin=True)

    def _apply_item_override(self) -> None:
        self.state.rules.item.update(demo_item_rules())
        self.refresh_all()

    def _reset_item_overrides(self) -> None:
        self.state.rules.item.clear()
        self.refresh_all()

    def _apply_local_override(self) -> None:
        door_key = next((row.structure_key for row in self.state.rows() if "porta" in row.structure_key), None)
        if door_key:
            self.state.local_overrides[door_key] = LocalOverride(
                material_description="Porta com ajuste local validado pelo orçamentista",
                unit_cost=money("38.00"),
                reason="Exceção local: acabamento especial pedido pelo cliente.",
            )
        self.refresh_all()

    def _reset_local_overrides(self) -> None:
        self.state.local_overrides.clear()
        self.refresh_all()

    def refresh_all(self, *, skip_spin: bool = False) -> None:
        if not hasattr(self, "module_combo"):
            return
        if not skip_spin:
            dims = self.state.dimensions
            for spin, value in ((self.spin_h, dims.h), (self.spin_l, dims.l), (self.spin_p, dims.p)):
                spin.blockSignals(True)
                spin.setValue(int(value))
                spin.blockSignals(False)
        module_index = self.module_combo.findData(self.state.module_id)
        if module_index >= 0 and self.module_combo.currentIndex() != module_index:
            self.module_combo.blockSignals(True)
            self.module_combo.setCurrentIndex(module_index)
            self.module_combo.blockSignals(False)
        rows = self.state.rows()
        proposal = build_proposal_summary(rows)
        self._refresh_orcamentos(proposal)
        self._refresh_items(proposal)
        self._refresh_configurator(rows, proposal)
        self._refresh_custeio(rows)
        self._refresh_proposal(proposal, rows)
        self._refresh_producao()
        self._refresh_library()
        self._refresh_config()

    def _set_rows(self, table: QtWidgets.QTableWidget, rows: Sequence[Sequence[object]]) -> None:
        table.setRowCount(len(rows))
        for row_idx, row in enumerate(rows):
            for col_idx, value in enumerate(row):
                item = QtWidgets.QTableWidgetItem(str(value))
                if col_idx > 0 and isinstance(value, (int, float)):
                    item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                table.setItem(row_idx, col_idx, item)
        table.resizeColumnsToContents()

    def _refresh_orcamentos(self, proposal) -> None:
        self._set_rows(self.tbl_orcamentos, [["2026", "V3-0001", "01", "Cliente Demo", "Em configuração", _fmt_money(proposal.sell_price)]])

    def _refresh_items(self, proposal) -> None:
        dims = self.state.dimensions
        self._set_rows(
            self.tbl_items,
            [[
                "1",
                "Item demo configurável",
                self.state.module().name,
                f"{dims.h:.0f} x {dims.l:.0f} x {dims.p:.0f}",
                "Validar proposta",
                _fmt_money(proposal.sell_price),
            ]],
        )

    def _refresh_configurator(self, rows: Sequence[CusteioItemV3], proposal) -> None:
        module = self.state.module()
        self.lbl_resumo.setText(f"{module.name}\n{module.description}")
        self.lbl_module_card.setText(
            "Ficha do módulo\n"
            f"Família: {module.family}\n"
            f"Variáveis: {', '.join(module.variables)}\n"
            f"Regras herdadas: {', '.join(module.inherited_rules)}\n"
            f"Overrides por item: {', '.join(module.item_overrides)}"
        )
        self._set_rows(
            self.tbl_resumo_metrics,
            [
                ["Linhas geradas", len(rows)],
                ["Custo interno", _fmt_money(proposal.cost_total)],
                ["Preço proposto", _fmt_money(proposal.sell_price)],
                ["Overrides Dados Items", len(self.state.rules.item)],
                ["Overrides locais", len(self.state.local_overrides)],
            ],
        )
        groups = []
        seen = set()
        for row in rows:
            if row.rule_group in seen:
                continue
            seen.add(row.rule_group)
            groups.append([row.rule_group, row.rule_source, row.material_ref, row.material_description, _fmt_money(row.material_unit_cost)])
        self._set_rows(self.tbl_rules, groups)
        self._set_rows(
            self.tbl_generated,
            [[row.component_type, row.description, _fmt_num(row.quantity), _fmt_num(row.resolved_comp), _fmt_num(row.resolved_larg), _fmt_num(row.resolved_esp), row.rule_group] for row in rows],
        )
        self._set_rows(
            self.tbl_costs,
            [[row.description, _fmt_money(row.cost_material), _fmt_money(row.cost_edge), _fmt_money(row.cost_finish), _fmt_money(row.cost_labor), _fmt_money(row.cost_total)] for row in rows],
        )
        self._set_rows(
            self.tbl_calculations,
            [
                [
                    row.structure_key,
                    row.usage_label,
                    row.material_formula,
                    row.edge_formula,
                    row.finish_formula,
                    row.labor_formula,
                    row.total_formula,
                ]
                for row in rows
            ],
        )
        validations = validate_configuration(module, self.state.dimensions, self.state.rules, rows)
        self._set_rows(self.tbl_validation, validations)

    def _refresh_custeio(self, rows: Sequence[CusteioItemV3]) -> None:
        self._set_rows(
            self.tbl_custeio,
            [
                [
                    row.structure_key,
                    row.component_type,
                    f"{row.formula_comp or '-'} x {row.formula_larg or '-'} x {row.formula_esp or '-'}",
                    f"{_fmt_num(row.resolved_comp)} x {_fmt_num(row.resolved_larg)} x {_fmt_num(row.resolved_esp)}",
                    row.usage_label,
                    row.rule_source,
                    row.material_description,
                    _fmt_money(row.cost_total),
                    row.override_reason or "-",
                ]
                for row in rows
            ],
        )

    def _refresh_proposal(self, proposal, rows: Sequence[CusteioItemV3]) -> None:
        self._set_rows(
            self.tbl_proposal,
            [
                ["Custo matéria-prima/ferragens", _fmt_money(proposal.cost_material)],
                ["Custo orlas", _fmt_money(proposal.cost_edge)],
                ["Custo acabamentos", _fmt_money(proposal.cost_finish)],
                ["Custo produção/mão de obra", _fmt_money(proposal.cost_labor)],
                ["Custo interno", _fmt_money(proposal.cost_total)],
                ["Custos administrativos 5%", _fmt_money(proposal.admin_value)],
                ["Margem 35%", _fmt_money(proposal.margin_value)],
                ["Preço proposto", _fmt_money(proposal.sell_price)],
            ],
        )
        overrides = [row for row in rows if row.override_reason]
        self.lbl_proposal_notes.setText(
            "Observações: proposta demo gerada a partir de dados simulados. "
            + (f"Existem {len(overrides)} override(s) local(is) a rever." if overrides else "Sem overrides locais ativos.")
        )

    def _refresh_producao(self) -> None:
        self._set_rows(
            self.tbl_producao,
            [
                ["Lista de peças", "Gerada a partir do módulo", "Configurador"],
                ["Lista de ferragens", "Gerada a partir de Dados Gerais/Dados Items", "Custeio"],
                ["CUT-RITE", "Previsto para integração futura", "Produção"],
                ["IMOS/CNC", "Previsto para integração futura", "Produção"],
                ["PHC", "Consulta/importação read-only na fase inicial", "Configurações"],
            ],
        )

    def _refresh_library(self) -> None:
        self._set_rows(
            self.tbl_library,
            [[module.family, module.name, ", ".join(module.variables), ", ".join(module.inherited_rules), ", ".join(module.validations)] for module in self.modules],
        )
        self._set_rows(
            self.tbl_references,
            [
                [
                    "Microvellum",
                    "Estimativa com materiais, mão de obra, custos de produção, relatórios e proposta.",
                    "Separar custo interno, proposta, margens e relatórios por item.",
                ],
                [
                    "Mozaik / Cabinet Vision",
                    "Ligação entre desenho, cut lists, ferragens, relatórios e CNC.",
                    "Manter o orçamento orientado a módulos, mas preparar saída para produção.",
                ],
                [
                    "PolyBoard",
                    "Relatório de custos por materiais, orlas, ferragens, operações e linhas adicionais.",
                    "Separador Cálculo linha com uso real, fórmula e total por parcela.",
                ],
                [
                    "Kerf",
                    "Quoting rápido com material real, orlas, mão de obra e markup.",
                    "Fluxo mais simples para rever preço sem abrir uma grelha técnica gigante.",
                ],
            ],
        )

    def _refresh_config(self) -> None:
        self._set_rows(
            self.tbl_config,
            [
                ["Base de dados", "V3 separada; protótipo atual usa dados simulados em memória."],
                ["Importação V2", "Apenas read-only na fase inicial; sem escrita em dados V2."],
                ["CusteioItem V3", "Estrutura, regras, fórmulas, custos e overrides separados."],
                ["Dados Gerais", "Defaults globais do orçamento."],
                ["Dados Items", "Especialização do item sem afetar o orçamento inteiro."],
                ["Edição Local", "Override linha a linha com motivo visível."],
                ["Cálculo", "Cada linha guarda fórmula de material, orla, acabamento, produção e total."],
            ],
        )
        self._set_rows(
            self.tbl_server,
            [
                ["Aplicação", "Instalada localmente em cada PC da fábrica; UI e cache visual ficam no posto."],
                ["Base de dados", "Servidor central partilhado; todos os utilizadores leem/escrevem na mesma BD V3."],
                ["Ligação", "Configuração por DB_URI/ficheiro .env por posto, com credenciais por utilizador."],
                ["Concorrência", "Transações curtas, updated_at/versionamento e bloqueio lógico por orçamento/item em edição."],
                ["Permissões", "Roles por área: orçamentação, bibliotecas, produção, administração."],
                ["Auditoria", "Histórico de alterações em preço, regras, overrides e estados críticos."],
                ["Backups", "Backup/snapshot no servidor; o posto local não deve ser a fonte de verdade."],
                ["V2", "Importação inicial read-only para materiais, módulos e histórico; sem substituir dados V2."],
            ],
        )


def run() -> int:
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    window = MarteloV3Window()
    window.show()
    return app.exec()
