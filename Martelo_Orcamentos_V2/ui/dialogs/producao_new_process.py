from __future__ import annotations

import logging
import re
import unicodedata
from datetime import datetime
from typing import Optional

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt

from Martelo_Orcamentos_V2.app.services.clients import phc_simplex_validation_issue
from Martelo_Orcamentos_V2.app.services import phc_sql as svc_phc
from Martelo_Orcamentos_V2.app.services import streamlit_sql as svc_streamlit
from Martelo_Orcamentos_V2.app.utils.date_utils import format_date_display, parse_date_value
from Martelo_Orcamentos_V2.ui.models.qt_table import SimpleTableModel

logger = logging.getLogger(__name__)

def _phc_date_to_martelo(text: str) -> str:
    """
    Converte datas do PHC no formato dd.mm.yyyy para dd-MM-yyyy.
    """
    raw = str(text or "").strip()
    if not raw:
        return ""
    parsed = parse_date_value(raw.replace(".", "-"))
    if parsed is not None:
        return format_date_display(parsed)
    # fallback simples
    return raw.replace(".", "-")


def _simplex_from_text(text: str) -> str:
    """
    Gera um simplex seguro (sem acentos/pontuacao) para uso interno.
    """
    base = unicodedata.normalize("NFKD", text or "")
    base = "".join(ch for ch in base if not unicodedata.combining(ch))
    base = re.sub(r"[^A-Za-z0-9]+", "_", base)
    base = re.sub(r"_+", "_", base).strip("_").upper()
    return base or "CLIENTE"


class NovoProcessoDialog(QtWidgets.QDialog):
    """
    Criacao de novo processo a partir de uma Encomenda do PHC (read-only).

    A opcao Streamlit permite criar processo a partir de Encomenda Cliente Final (read-only).
    """

    def __init__(self, *, db, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setWindowTitle("Novo Processo")
        self.resize(980, 560)

        self._db = db
        self._rows_phc: list[dict] = []
        self._rows_streamlit: list[dict] = []
        self._result: Optional[dict] = None

        layout = QtWidgets.QVBoxLayout(self)

        self.tabs = QtWidgets.QTabWidget(self)
        layout.addWidget(self.tabs, 1)

        # --- PHC tab ---
        self.tab_phc = QtWidgets.QWidget(self)
        phc_layout = QtWidgets.QVBoxLayout(self.tab_phc)

        row = QtWidgets.QHBoxLayout()
        row.addWidget(QtWidgets.QLabel("Ano:"), 0)
        self.sp_ano = QtWidgets.QSpinBox()
        self.sp_ano.setRange(2000, 2100)
        self.sp_ano.setValue(datetime.now().year)
        self.sp_ano.setToolTip("Ano da encomenda (filtra por BI.DATAOBRA).")
        self.sp_ano.setFixedWidth(90)
        row.addWidget(self.sp_ano, 0)
        row.addWidget(QtWidgets.QLabel("Num_Enc_PHC:"), 0)
        self.ed_num_enc_phc = QtWidgets.QLineEdit()
        self.ed_num_enc_phc.setPlaceholderText("Ex.: 1956")
        self.ed_num_enc_phc.setValidator(QtGui.QIntValidator(0, 999999999, self))
        self.ed_num_enc_phc.setToolTip("Numero de encomenda no PHC (BI.OBRANO).")
        row.addWidget(self.ed_num_enc_phc, 0)
        self.btn_search = QtWidgets.QPushButton("Pesquisar")
        self.btn_search.setToolTip("Pesquisar a encomenda no PHC e mostrar os itens (apenas leitura).")
        self.btn_search.clicked.connect(self._on_search_phc)
        row.addWidget(self.btn_search, 0)
        row.addStretch(1)
        phc_layout.addLayout(row)

        self.lbl_status = QtWidgets.QLabel("")
        self.lbl_status.setStyleSheet("color:#555;")
        phc_layout.addWidget(self.lbl_status)

        self.tbl_phc = QtWidgets.QTableView(self.tab_phc)
        self.tbl_phc.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tbl_phc.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.tbl_phc.setAlternatingRowColors(True)
        self.tbl_phc.setSortingEnabled(True)

        self.model_phc = SimpleTableModel(
            rows=[],
            columns=[
                ("Ano", "Ano"),
                ("Nome Cliente", "Cliente"),
                ("Nome Cliente Simplex", "Cliente_Abreviado"),
                ("Num_Enc_PHC", "Enc_No"),
                ("Num_PHC", "Num_PHC"),
                ("Ref_Cliente", "Ref_Cliente"),
                ("Descricao Artigo", "Descricao_Artigo"),
                ("Data Encomenda", "Data_Encomenda"),
                ("Data Entrega", "Data_Entrega"),
            ],
            parent=self,
        )
        self.tbl_phc.setModel(self.model_phc)
        hdr = self.tbl_phc.horizontalHeader()
        try:
            hdr.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
            hdr.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
            hdr.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
            hdr.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)
            hdr.setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeToContents)
            hdr.setSectionResizeMode(5, QtWidgets.QHeaderView.ResizeToContents)
            hdr.setSectionResizeMode(6, QtWidgets.QHeaderView.Stretch)
            hdr.setSectionResizeMode(7, QtWidgets.QHeaderView.ResizeToContents)
            hdr.setSectionResizeMode(8, QtWidgets.QHeaderView.ResizeToContents)
        except Exception:
            hdr.setStretchLastSection(True)

        phc_layout.addWidget(self.tbl_phc, 1)
        self.tabs.addTab(self.tab_phc, "Encomenda de Cliente (PHC)")

        # --- Streamlit tab ---
        self.tab_streamlit = QtWidgets.QWidget(self)
        st_layout = QtWidgets.QVBoxLayout(self.tab_streamlit)

        st_row = QtWidgets.QHBoxLayout()
        st_row.addWidget(QtWidgets.QLabel("Ano:"), 0)
        self.sp_ano_streamlit = QtWidgets.QSpinBox()
        self.sp_ano_streamlit.setRange(2000, 2100)
        self.sp_ano_streamlit.setValue(datetime.now().year)
        self.sp_ano_streamlit.setToolTip("Ano da encomenda (filtra por Encomendas.Ano).")
        self.sp_ano_streamlit.setFixedWidth(90)
        st_row.addWidget(self.sp_ano_streamlit, 0)

        st_row.addWidget(QtWidgets.QLabel("Num_Enc_(F):"), 0)
        self.ed_num_enc_final = QtWidgets.QLineEdit()
        self.ed_num_enc_final.setPlaceholderText("Ex.: _001 ou 001")
        self.ed_num_enc_final.setToolTip("Numero de encomenda Cliente Final (Encomendas.Numero).")
        st_row.addWidget(self.ed_num_enc_final, 0)

        self.btn_search_streamlit = QtWidgets.QPushButton("Pesquisar")
        self.btn_search_streamlit.setToolTip("Pesquisar a encomenda Cliente Final e mostrar os itens (apenas leitura).")
        self.btn_search_streamlit.clicked.connect(self._on_search_streamlit)
        st_row.addWidget(self.btn_search_streamlit, 0)
        st_row.addStretch(1)
        st_layout.addLayout(st_row)

        self.lbl_status_streamlit = QtWidgets.QLabel("")
        self.lbl_status_streamlit.setStyleSheet("color:#555;")
        st_layout.addWidget(self.lbl_status_streamlit)

        self.tbl_streamlit = QtWidgets.QTableView(self.tab_streamlit)
        self.tbl_streamlit.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tbl_streamlit.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.tbl_streamlit.setAlternatingRowColors(True)
        self.tbl_streamlit.setSortingEnabled(True)

        self.model_streamlit = SimpleTableModel(
            rows=[],
            columns=[
                ("Ano", "Ano"),
                ("Cliente", "Cliente"),
                ("Cliente Abreviado", "Cliente_Abreviado"),
                ("Numero", "Numero"),
                ("RefCliente", "RefCliente"),
                ("Designacao", "Designacao"),
                ("Data Entrega", "DataEntrega"),
            ],
            parent=self,
        )
        self.tbl_streamlit.setModel(self.model_streamlit)
        hdr_st = self.tbl_streamlit.horizontalHeader()
        try:
            hdr_st.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
            hdr_st.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
            hdr_st.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
            hdr_st.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)
            hdr_st.setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeToContents)
            hdr_st.setSectionResizeMode(5, QtWidgets.QHeaderView.Stretch)
            hdr_st.setSectionResizeMode(6, QtWidgets.QHeaderView.ResizeToContents)
        except Exception:
            hdr_st.setStretchLastSection(True)

        st_layout.addWidget(self.tbl_streamlit, 1)
        self.tabs.addTab(self.tab_streamlit, "Encomenda Cliente Final (Streamlit)")

        # Buttons
        self.buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        self._btn_ok = self.buttons.button(QtWidgets.QDialogButtonBox.Ok)
        self._btn_ok.setText("Criar Processo")
        self._btn_ok.setEnabled(False)
        try:
            self._btn_ok.setAutoDefault(False)
            self._btn_ok.setDefault(False)
        except Exception:
            pass
        self.buttons.accepted.connect(self._on_accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons, 0)

        self.tabs.currentChanged.connect(self._refresh_ok_state)
        self._refresh_ok_state()

        # garantir que Enter faz pesquisa (e nao "Criar Processo") quando o foco esta nos campos de pesquisa
        self.ed_num_enc_phc.installEventFilter(self)
        try:
            self._ano_line_edit = self.sp_ano.lineEdit()
            if self._ano_line_edit:
                self._ano_line_edit.installEventFilter(self)
        except Exception:
            self._ano_line_edit = None

        self.ed_num_enc_final.installEventFilter(self)
        try:
            self._ano_line_edit_streamlit = self.sp_ano_streamlit.lineEdit()
            if self._ano_line_edit_streamlit:
                self._ano_line_edit_streamlit.installEventFilter(self)
        except Exception:
            self._ano_line_edit_streamlit = None

    def result_data(self) -> Optional[dict]:
        return self._result

    def eventFilter(self, obj, event):  # noqa: N802
        try:
            if event.type() == QtCore.QEvent.KeyPress and event.key() in (Qt.Key_Return, Qt.Key_Enter):
                if obj in (self.ed_num_enc_phc, getattr(self, "_ano_line_edit", None)):
                    self._on_search_phc()
                    return True
                if obj in (self.ed_num_enc_final, getattr(self, "_ano_line_edit_streamlit", None)):
                    self._on_search_streamlit()
                    return True
        except Exception:
            pass
        return super().eventFilter(obj, event)

    def _refresh_ok_state(self) -> None:
        cur = self.tabs.currentWidget()
        if cur == self.tab_phc:
            has_rows = bool(self._rows_phc)
        elif cur == self.tab_streamlit:
            has_rows = bool(self._rows_streamlit)
        else:
            has_rows = False
        self._btn_ok.setEnabled(bool(has_rows))

    def _on_search_phc(self) -> None:
        enc = (self.ed_num_enc_phc.text() or "").strip()
        enc_digits = re.sub(r"\\D", "", enc)
        if not enc_digits:
            QtWidgets.QMessageBox.warning(self, "Num_Enc_PHC", "Indique o numero da encomenda PHC (apenas digitos).")
            return

        try:
            ano = int(getattr(self, "sp_ano", None).value()) if hasattr(self, "sp_ano") else None
            rows = svc_phc.query_phc_encomenda_itens(self._db, num_enc_phc=enc_digits, ano=ano)
        except Exception as exc:
            logger.exception("NovoProcessoDialog: falha query PHC encomenda: %s", exc)
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao consultar PHC:\n{exc}")
            rows = []

        normalized: list[dict] = []
        for r in rows or []:
            cliente = str(r.get("Cliente") or "").strip()
            simplex = str(r.get("Cliente_Abreviado") or "").strip()
            if not simplex and cliente:
                base = _simplex_from_text(cliente)
                simplex = (base[:10] + "...") if len(base) > 10 else base

            normalized.append(
                {
                    "Ano": "" if r.get("Ano") is None else str(r.get("Ano")).strip(),
                    "Cliente": cliente,
                    "Cliente_Abreviado": simplex,
                    "Enc_No": "" if r.get("Enc_No") is None else str(r.get("Enc_No")).strip(),
                    "Num_PHC": "" if r.get("Num_PHC") is None else str(r.get("Num_PHC")).strip(),
                    "Ref_Cliente": "" if r.get("Ref_Cliente") is None else str(r.get("Ref_Cliente")).strip(),
                    "Descricao_Artigo": str(r.get("Descricao_Artigo") or "").strip(),
                    "Data_Encomenda": str(r.get("Data_Encomenda") or "").strip(),
                    "Data_Entrega": str(r.get("Data_Entrega") or "").strip(),
                }
            )

        self._rows_phc = normalized
        self.model_phc.set_rows(self._rows_phc)
        if not self._rows_phc:
            self.lbl_status.setText("Encomenda nao encontrada.")
        else:
            self.lbl_status.setText(f"{len(self._rows_phc)} linha(s) carregada(s).")
            try:
                self.tbl_phc.selectRow(0)
            except Exception:
                pass
        self._refresh_ok_state()

    def _on_search_streamlit(self) -> None:
        enc = (self.ed_num_enc_final.text() or "").strip()
        if not enc:
            QtWidgets.QMessageBox.warning(self, "Num_Enc_(F)", "Indique o numero da encomenda Cliente Final (ex.: _001 ou 001).")
            return

        try:
            ano = int(getattr(self, "sp_ano_streamlit", None).value()) if hasattr(self, "sp_ano_streamlit") else None
            rows = svc_streamlit.query_streamlit_encomenda_itens(self._db, num_enc_final=enc, ano=ano)
        except Exception as exc:
            logger.exception("NovoProcessoDialog: falha query Streamlit encomenda: %s", exc)
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao consultar Streamlit:\n{exc}")
            rows = []

        normalized: list[dict] = []
        for r in rows or []:
            cliente = str(r.get("Cliente") or "").strip()
            simplex = str(r.get("Cliente_Abreviado") or "").strip()
            if not simplex:
                # regra: se nao existir abreviado, usar o nome do cliente (sem truncar)
                simplex = cliente

            normalized.append(
                {
                    "Ano": "" if r.get("Ano") is None else str(r.get("Ano")).strip(),
                    "Cliente": cliente,
                    "Cliente_Abreviado": simplex,
                    "Numero": str(r.get("Numero") or "").strip(),
                    "RefCliente": str(r.get("RefCliente") or "").strip(),
                    "Designacao": str(r.get("Designacao") or "").strip(),
                    "DataEntrega": str(r.get("DataEntrega") or "").strip(),
                    "DataRecepcao": str(r.get("DataRecepcao") or "").strip(),
                }
            )

        self._rows_streamlit = normalized
        self.model_streamlit.set_rows(self._rows_streamlit)
        if not self._rows_streamlit:
            self.lbl_status_streamlit.setText("Encomenda nao encontrada.")
        else:
            self.lbl_status_streamlit.setText(f"{len(self._rows_streamlit)} linha(s) carregada(s).")
            try:
                self.tbl_streamlit.selectRow(0)
            except Exception:
                pass
        self._refresh_ok_state()

    @staticmethod
    def _year_from_phc_date(date_text: str) -> Optional[int]:
        raw = str(date_text or "").strip()
        if not raw:
            return None
        for fmt in ("%d.%m.%Y", "%d-%m-%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(raw, fmt).year
            except Exception:
                continue
        # fallback simples
        m = re.search(r"(19|20)\\d{2}", raw)
        if m:
            try:
                return int(m.group(0))
            except Exception:
                return None
        return None

    def _on_accept(self) -> None:
        cur = self.tabs.currentWidget()

        if cur == self.tab_phc:
            if not self._rows_phc:
                QtWidgets.QMessageBox.warning(self, "PHC", "Pesquise uma encomenda PHC antes de continuar.")
                return

            row_idx = 0
            try:
                idxs = self.tbl_phc.selectionModel().selectedRows()
                if idxs:
                    row_idx = idxs[0].row()
            except Exception:
                row_idx = 0
            if row_idx < 0 or row_idx >= len(self._rows_phc):
                row_idx = 0
            base = self._rows_phc[row_idx]
            nome_cliente = (base.get("Cliente") or "").strip()
            nome_simplex = (base.get("Cliente_Abreviado") or "").strip()
            num_enc = re.sub(r"\\D", "", str(base.get("Enc_No") or ""))
            num_phc = (base.get("Num_PHC") or "").strip()
            ref_cliente = (base.get("Ref_Cliente") or "").strip()
            validation_issue = phc_simplex_validation_issue(
                cliente_nome=nome_cliente,
                num_phc=num_phc,
                simplex=nome_simplex,
                action_label="criar o novo processo",
            )
            if validation_issue:
                QtWidgets.QMessageBox.warning(self, validation_issue[0], validation_issue[1])
                return

            # descricoes (itens) -> texto multi-linha, mantendo ordem e evitando duplicados
            seen = set()
            descr_list: list[str] = []
            for r in self._rows_phc:
                d = (r.get("Descricao_Artigo") or "").strip()
                if not d:
                    continue
                if d in seen:
                    continue
                seen.add(d)
                descr_list.append(d)
            descricao_artigos = "\n".join(descr_list).strip()

            data_enc = (base.get("Data_Encomenda") or "").strip()
            data_ent = (base.get("Data_Entrega") or "").strip()

            ano = (
                int(str(base.get("Ano")).strip())
                if str(base.get("Ano") or "").strip().isdigit()
                else int(getattr(self, "sp_ano", None).value()) if hasattr(self, "sp_ano") else None
            ) or self._year_from_phc_date(data_enc) or datetime.now().year

            self._result = {
                "source": "phc",
                "ano": str(ano),
                "num_enc_phc": num_enc or self.ed_num_enc_phc.text().strip(),
                "nome_cliente": nome_cliente,
                "nome_cliente_simplex": nome_simplex,
                "num_cliente_phc": num_phc,
                "ref_cliente": ref_cliente,
                "descricao_artigos": descricao_artigos,
                "data_inicio": _phc_date_to_martelo(data_enc),
                "data_entrega": _phc_date_to_martelo(data_ent),
            }
            self.accept()
            return

        if cur == self.tab_streamlit:
            if not self._rows_streamlit:
                QtWidgets.QMessageBox.warning(self, "Streamlit", "Pesquise uma encomenda Cliente Final antes de continuar.")
                return

            row_idx = 0
            try:
                idxs = self.tbl_streamlit.selectionModel().selectedRows()
                if idxs:
                    row_idx = idxs[0].row()
            except Exception:
                row_idx = 0
            if row_idx < 0 or row_idx >= len(self._rows_streamlit):
                row_idx = 0
            base = self._rows_streamlit[row_idx]

            nome_cliente = (base.get("Cliente") or "").strip()
            nome_simplex = (base.get("Cliente_Abreviado") or "").strip() or nome_cliente
            num_enc_raw = str(base.get("Numero") or "").strip()
            if not num_enc_raw:
                QtWidgets.QMessageBox.warning(self, "Num_Enc_(F)", "Numero invalido (vazio).")
                return
            if num_enc_raw.startswith("_"):
                m = re.fullmatch(r"_(\d{1,3})", num_enc_raw)
                if not m:
                    QtWidgets.QMessageBox.warning(self, "Num_Enc_(F)", "Numero invalido. Formato esperado: _001.")
                    return
                num_enc = "_" + m.group(1).zfill(3)
            else:
                digits = re.sub(r"\D", "", num_enc_raw)
                if not digits:
                    QtWidgets.QMessageBox.warning(self, "Num_Enc_(F)", "Numero invalido. Formato esperado: _001.")
                    return
                num_enc = "_" + digits.zfill(3)

            ref_cliente = (base.get("RefCliente") or "").strip()

            seen = set()
            descr_list: list[str] = []
            for r in self._rows_streamlit:
                d = (r.get("Designacao") or "").strip()
                if not d:
                    continue
                if d in seen:
                    continue
                seen.add(d)
                descr_list.append(d)
            descricao_artigos = "\n".join(descr_list).strip()

            data_rec = (base.get("DataRecepcao") or "").strip()
            data_ent = (base.get("DataEntrega") or "").strip()

            ano = (
                int(str(base.get("Ano")).strip())
                if str(base.get("Ano") or "").strip().isdigit()
                else int(getattr(self, "sp_ano_streamlit", None).value()) if hasattr(self, "sp_ano_streamlit") else None
            ) or self._year_from_phc_date(data_rec) or datetime.now().year

            self._result = {
                "source": "streamlit",
                "ano": str(ano),
                "num_enc_phc": num_enc,
                "nome_cliente": nome_cliente,
                "nome_cliente_simplex": nome_simplex,
                "num_cliente_phc": "",
                "ref_cliente": ref_cliente,
                "descricao_artigos": descricao_artigos,
                "data_inicio": _phc_date_to_martelo(data_rec),
                "data_entrega": _phc_date_to_martelo(data_ent),
            }
            self.accept()
            return

        QtWidgets.QMessageBox.warning(self, "Origem", "Selecione uma origem valida (PHC ou Streamlit).")
