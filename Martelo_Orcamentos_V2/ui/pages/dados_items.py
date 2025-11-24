from __future__ import annotations

from functools import partial
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple
import json
import logging

from PySide6 import QtCore, QtWidgets, QtGui

from Martelo_Orcamentos_V2.app.models import OrcamentoItem
from sqlalchemy.orm import Session
from Martelo_Orcamentos_V2.app.services import dados_items as svc_di
from Martelo_Orcamentos_V2.app.services import dados_gerais as svc_dg
from Martelo_Orcamentos_V2.app.services import materias_primas as svc_mp
from Martelo_Orcamentos_V2.ui.delegates import DadosGeraisDelegate

from .dados_gerais import DadosGeraisPage, PREVIEW_COLUMNS, _format_preview_value
from ..utils.header import apply_highlight_text, init_highlight_label

logger = logging.getLogger(__name__)


def _extract_rows_from_payload(
    origin: str,
    payload: Optional[Mapping[str, Any]],
    menu: str,
) -> List[Dict[str, Any]]:
    rows: Sequence[Mapping[str, Any]] = []

    if not payload:
        return []

    if origin == "global":
        candidate = payload.get("linhas")
        if isinstance(candidate, Sequence) and not isinstance(candidate, (str, bytes)):
            rows = [row for row in candidate if isinstance(row, Mapping)]
        else:
            candidate = payload.get(menu)
            if isinstance(candidate, Sequence) and not isinstance(candidate, (str, bytes)):
                rows = [row for row in candidate if isinstance(row, Mapping)]
    else:
        candidate = payload.get(menu, [])
        if isinstance(candidate, Sequence) and not isinstance(candidate, (str, bytes)):
            rows = [row for row in candidate if isinstance(row, Mapping)]

    return [dict(row) for row in rows]


class DadosItemsPage(DadosGeraisPage):
    def __init__(self, parent=None, current_user=None):
        super().__init__(
            parent=parent,
            current_user=current_user,
            svc_module=svc_di,
            page_title="Dados Items",
            save_button_text="Guardar Dados Items",
            import_button_text="Importar Dados Items",
            import_multi_button_text="Importar Multi Dados Items",
        )
        self._setup_item_header()
        self.current_orcamento_id: Optional[int] = None
        self.current_item_id: Optional[int] = None

    def _setup_item_header(self) -> None:
        grid = getattr(self, "_header_grid", None)
        if not isinstance(grid, QtWidgets.QGridLayout):
            return

        column_span = max(1, grid.columnCount())

        if not hasattr(self, "lbl_highlight"):
            self.lbl_highlight = QtWidgets.QLabel("")
            init_highlight_label(self.lbl_highlight)
        grid.addWidget(self.lbl_highlight, 1, 0, 1, column_span)

        self.lbl_item_description = QtWidgets.QLabel("-")
        self.lbl_item_description.setWordWrap(True)
        self.lbl_item_description.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)

        grid.addWidget(self.lbl_item_description, 2, 0, 1, column_span)

        if self._dimensions_layout is not None:
            grid.removeItem(self._dimensions_layout)
            grid.addLayout(self._dimensions_layout, 3, 0, 1, column_span)

        if self._info_pairs_layout is not None:
            grid.removeItem(self._info_pairs_layout)
            grid.addLayout(self._info_pairs_layout, 4, 0, 1, column_span)
            self._info_pairs_layout.setSpacing(18)

        captions = (self._dimension_labels or {}).get("captions", [])
        if len(captions) >= 3:
            captions[0].setText("Comp:")
            captions[1].setText("Largura:")
            captions[2].setText("Profundidade:")

    # ------------------------------------------------------------------ Matérias-primas merge
    def _merge_with_materias_primas(self, rows: List[Dict[str, Any]], menu: str) -> List[Dict[str, Any]]:
        """
        Preenche campos faltantes a partir de materias_primas (match por ref_le).
        Se houver conflito (modelo vs MP), apresenta dialogo para o utilizador decidir.
        """
        fill_fields = {"desp", "orl_0_4", "orl_1_0", "comp_mp", "larg_mp", "esp_mp", "id_mp", "nao_stock"}
        compare_fields = ["ref_le", "descricao_material", "preco_tab", "preco_liq", "margem", "desconto", "und"]
        conflicts: Dict[int, Dict[str, Any]] = {}
        merged: List[Dict[str, Any]] = []
        mp_cache: Dict[int, Any] = {}
        label_field_map = {
            svc_di.MENU_MATERIAIS: "materiais",
            svc_di.MENU_FERRAGENS: "ferragens",
            svc_di.MENU_SIS_CORRER: "sistemas_correr",
            svc_di.MENU_ACABAMENTOS: "acabamentos",
        }
        label_header_map = {
            svc_di.MENU_MATERIAIS: "Materiais",
            svc_di.MENU_FERRAGENS: "Ferragens",
            svc_di.MENU_SIS_CORRER: "Sistemas Correr",
            svc_di.MENU_ACABAMENTOS: "Acabamentos",
        }
        label_field = label_field_map.get(menu, "label")
        line_header = label_header_map.get(menu, "Linha")

        def _fmt_one_dec(val: Any):
            try:
                from decimal import Decimal
                return float(Decimal(str(val)).quantize(Decimal("0.1")))
            except Exception:
                try:
                    return round(float(val), 1)
                except Exception:
                    return val

        def _norm(val: Any) -> Any:
            if val is None:
                return None
            if isinstance(val, (int, float)):
                return float(val)
            return str(val).strip()

        def _is_close(a: Any, b: Any, field: str) -> bool:
            # tolera arredondamentos para valores monet�rios/percentuais
            if a in (None, "") and b in (None, ""):
                return True
            try:
                fa = float(a)
                fb = float(b)
                if field in {"preco_tab", "preco_liq"}:
                    return abs(fa - fb) < 0.01  # tolera 1 c�ntimo
                if field in {"margem", "desconto"}:
                    return abs(fa - fb) < 0.0001  # tolera pequenas casas decimais
            except Exception:
                pass
            return _norm(a) == _norm(b)

        def _mp_value(mp_obj: Any, field: str) -> Any:
            # resolve aliases for comparacao (campos principais)
            alias_map = {
                "descricao_material": [
                    "descricao_material",
                    "descricao_no_orcamento",
                    "descricao_orcamento",
                    "DESCRICAO_no_ORCAMENTO",
                    "DESCRICAO_ORCAMENTO",
                ],
                "preco_tab": ["preco_tab", "preco_tabela", "PRECO_TABELA"],
                "preco_liq": ["preco_liq", "pliq", "PLIQ", "PRECO_LIQ"],
                "margem": ["margem", "MARGEM"],
                "desconto": ["desconto", "DESCONTO"],
                "ref_le": ["ref_le", "REF_LE", "Ref_LE"],
                "und": ["und", "UND"],
            }
            keys = alias_map.get(field, [field])
            for k in keys:
                try:
                    val = getattr(mp_obj, k)
                except Exception:
                    val = None
                if val not in (None, ""):
                    return val
            return None

        table_model_for_menu = self.models.get(menu)

        for idx, row in enumerate(rows):
            new_row = dict(row)
            ref_le = (new_row.get("ref_le") or "").strip()
            mp = svc_mp.get_materia_prima_by_ref_le(self.session, ref_le) if ref_le else None
            if mp:
                mp_cache[idx] = mp
                for field in fill_fields:
                    mp_val = getattr(mp, field, None)
                    if field in {"comp_mp", "larg_mp", "esp_mp"} and mp_val not in (None, ""):
                        mp_val = _fmt_one_dec(mp_val)
                    if mp_val is None:
                        continue
                    if new_row.get(field) in (None, ""):
                        new_row[field] = mp_val

                model_subset = {f: new_row.get(f) for f in compare_fields}
                mp_subset = {f: _mp_value(mp, f) for f in compare_fields}
                if any(not _is_close(model_subset.get(f), mp_subset.get(f), f) for f in compare_fields):
                    mp_full = {
                        "ref_le": getattr(mp, "ref_le", None),
                        "descricao_no_orcamento": getattr(mp, "descricao_no_orcamento", None)
                        or getattr(mp, "descricao_orcamento", None)
                        or getattr(mp, "DESCRICAO_no_ORCAMENTO", None)
                        or getattr(mp, "DESCRICAO_NO_ORCAMENTO", None)
                        or getattr(mp, "DESCRICAO_ORCAMENTO", None),
                        "descricao_material": getattr(mp, "descricao_material", None)
                        or getattr(mp, "DESCRICAO_MATERIAL", None),
                        "preco_tab": getattr(mp, "preco_tab", None) or getattr(mp, "PRECO_TAB", None),
                        "preco_tabela": getattr(mp, "preco_tabela", None) or getattr(mp, "PRECO_TABELA", None),
                        "preco_liq": getattr(mp, "preco_liq", None) or getattr(mp, "PRECO_LIQ", None),
                        "pliq": getattr(mp, "pliq", None) or getattr(mp, "PLIQ", None),
                        "margem": getattr(mp, "margem", None) or getattr(mp, "MARGEM", None),
                        "desconto": getattr(mp, "desconto", None) or getattr(mp, "DESCONTO", None),
                        "und": getattr(mp, "und", None) or getattr(mp, "UND", None),
                    }
                    def _first_label(candidates):
                        for cand in candidates:
                            if cand is None:
                                continue
                            if isinstance(cand, str):
                                val = cand.strip()
                                if val and not val.isdigit():
                                    return val
                            else:
                                try:
                                    # skip pure numbers as labels if possible
                                    float(cand)
                                    continue
                                except Exception:
                                    pass
                                return str(cand)
                        # fallback: allow numeric if nothing else
                        for cand in candidates:
                            if cand not in (None, ""):
                                return str(cand)
                        return ""

                    label_from_table = None
                    if table_model_for_menu is not None:
                        try:
                            item = table_model_for_menu.item(idx, 0)  # primeira coluna visível
                            if item:
                                label_from_table = item.text()
                        except Exception:
                            try:
                                idx_qt = table_model_for_menu.index(idx, 0)  # type: ignore[attr-defined]
                                label_from_table = idx_qt.data()
                            except Exception:
                                pass

                    label_value = _first_label(
                        [
                            label_from_table,
                            new_row.get(label_field),
                            new_row.get("materiais"),
                            new_row.get("ferragens"),
                            new_row.get("sistemas_correr"),
                            new_row.get("acabamentos"),
                            new_row.get("linha"),
                            new_row.get("descricao"),
                            new_row.get("descricao_material"),
                            new_row.get("ref_le"),
                        ]
                    )
                    conflicts[idx] = {
                        "model": model_subset,
                        "mp": mp_subset,
                        "mp_full": mp_full,
                        "label": label_value,
                        "line_header": line_header,
                    }
            merged.append(new_row)

        if conflicts:
            dialog = MateriaPrimaConflictDialog(conflicts, parent=self, line_header=line_header)
            if dialog.exec() == QtWidgets.QDialog.Accepted:
                choices = dialog.selected_sources()
                for row_idx, use_mp in choices.items():
                    if not (0 <= row_idx < len(merged)):
                        continue
                    mp = mp_cache.get(row_idx)
                    if not mp:
                        continue
                    mp_subset = conflicts[row_idx]["mp"]
                    if use_mp:
                        for field, val in mp_subset.items():
                            merged[row_idx][field] = val
                        for field in fill_fields:
                            mp_val = getattr(mp, field, merged[row_idx].get(field))
                            if field in {"comp_mp", "larg_mp", "esp_mp"} and mp_val not in (None, ""):
                                mp_val = _fmt_one_dec(mp_val)
                            merged[row_idx][field] = mp_val

        return merged

# ------------------------------------------------------------------ Import override (usar ordenação fixa)
    def _apply_imported_rows(self, key: str, rows: Sequence[Mapping[str, Any]], *, replace: bool) -> None:  # type: ignore[override]
        model = self.models[key]
        prepared_rows = [dict(r) for r in rows if isinstance(r, Mapping)]
        if not prepared_rows:
            return

        if replace:
            existing_rows = model.export_rows()
            merged: List[Dict[str, Any]] = []
            for idx, base in enumerate(existing_rows):
                incoming = prepared_rows[idx] if idx < len(prepared_rows) else {}
                merged_row = dict(base or {})
                for k, v in incoming.items():
                    if v in (None, ""):
                        # preserva tipo/familia/não stock existentes se o modelo trouxer vazio
                        if k in {"tipo", "familia"}:
                            continue
                    merged_row[k] = v
                merged.append(merged_row)

            merged = self._merge_with_materias_primas(merged, key)
            model.load_rows(merged)
            if hasattr(model, "_reindex"):
                try:
                    model._reindex()  # type: ignore[attr-defined]
                except Exception:
                    pass
            if hasattr(model, "recalculate"):
                for idx in range(model.rowCount()):
                    try:
                        model.recalculate(idx)  # type: ignore[attr-defined]
                    except Exception:
                        continue
            else:
                self._recalculate_menu_rows(key)
            return

        # Caso mesclar, reconciliamos antes de delegar para lógica base
        prepared_rows = self._merge_with_materias_primas(prepared_rows, key)
        return super()._apply_imported_rows(key, prepared_rows, replace=replace)

    # ------------------------------------------------------------------ Integration
    def load_item(self, orcamento_id: int, item_id: Optional[int]) -> None:
        logger.debug("DadosItems.load_item orcamento_id=%s item_id=%s", orcamento_id, item_id)
        self.current_orcamento_id = orcamento_id
        normalized_item_id = item_id
        if item_id is not None:
            try:
                normalized_item_id = int(item_id)
            except (TypeError, ValueError):
                normalized_item_id = item_id
            try:
                self.session.flush()
            except Exception:
                pass
            try:
                self.session.expire_all()
            except Exception:
                pass
        logger.debug("DadosItems.load_item normalized_item_id=%s", normalized_item_id)
        self.current_item_id = normalized_item_id

        try:
            self.session.rollback()
        except Exception:
            pass

        if not normalized_item_id:
            self.context = None
            self._reset_tables()
            self.lbl_title.setText(self.page_title)
            self.lbl_item_description.setText("-")
            self._update_dimensions_labels(visible=False)
            self._update_highlight_banner()
            return

        try:
            logger.debug("DadosItems.load_item calling super.load_orcamento with item_id=%s", normalized_item_id)
            super().load_orcamento(orcamento_id, item_id=normalized_item_id)
        except Exception as exc:  # pragma: no cover - UI feedback
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao carregar Dados Items: {exc}")
            self._reset_tables()
            self._update_dimensions_labels(visible=False)
            return

        self._update_item_header(item_id)
        self._update_highlight_banner()

    def _reset_tables(self) -> None:
        for model in self.models.values():
            model.load_rows([])
            model._reindex()

        self._update_dimensions_labels(visible=False)

        self.lbl_item_description.setText("-")

        self._update_highlight_banner()

    def _update_highlight_banner(self) -> None:
        label = getattr(self, "lbl_highlight", None)
        if label is None:
            return

        def _clean(lbl: QtWidgets.QLabel) -> str:
            text = (lbl.text() or "").strip()
            return "" if text in {"", "-"} else text

        apply_highlight_text(
            label,
            cliente=_clean(self.lbl_cliente),
            numero=_clean(self.lbl_num),
            versao=_clean(self.lbl_ver),
            ano=_clean(self.lbl_ano),
            utilizador=_clean(self.lbl_utilizador),
        )



    def _update_item_header(self, item_id: int) -> None:
        item: Optional[OrcamentoItem] = self.session.get(OrcamentoItem, item_id)
        if not item:
            self.lbl_title.setText(self.page_title)
            self.lbl_item_description.setText("-")
            self._update_dimensions_labels(visible=False)
            return
        numero = getattr(item, "item_ord", None) or getattr(item, "item", None) or item_id
        descricao = (item.descricao or "").strip()
        self.lbl_title.setText(f"{self.page_title} - Item: {numero}")
        self.lbl_item_description.setText(descricao or "-")
        self._update_dimensions_labels(
            altura=getattr(item, "altura", None),
            largura=getattr(item, "largura", None),
            profundidade=getattr(item, "profundidade", None),
            visible=True,
        )

    def _post_table_setup(self, key: str) -> None:  # type: ignore[override]
        super()._post_table_setup(key)
        table = self.tables.get(key)
        model = self.models.get(key)
        if not table or not model:
            return
        # Permitir toggle imediato nos checkboxes e reaplicar delegate padrão
        table.setEditTriggers(QtWidgets.QAbstractItemView.AllEditTriggers)
        table.setItemDelegate(DadosGeraisDelegate(table))
        for col_idx, spec in enumerate(model.columns):
            field = getattr(spec, "field", "") or ""
            if field.lower().startswith("reserva"):
                table.setColumnHidden(col_idx, True)

    def on_guardar(self) -> None:  # type: ignore[override]
        if not self.context:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Nenhum item selecionado.")
            return
        # -------------- COMMIT de editores Abertos --------------
        # Se um editor estiver aberto, commit e fechar para garantir que
        # o modelo tem o valor mais recente antes de exportar
        for t in (self.tables or {}).values():
            try:
                editor = t.focusWidget()
                # se o editor pertence ao viewport da tabela, comitamos
                if editor and editor.parent() is t.viewport():
                    try:
                        t.commitData(editor)
                        t.closeEditor(editor, QtWidgets.QAbstractItemDelegate.SubmitModelCache)
                    except Exception:
                        # não fatal: continuamos
                        pass
            except Exception:
                pass

        # -------------- export payload (debug) --------------
        payload = {key: model.export_rows() for key, model in self.models.items()}

        # DEBUG: mostra payload que será enviado ao serviço (via logging)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                "DadosItems.on_guardar payload\n%s",
                json.dumps(payload, indent=2, default=str),
            )

        

        payload = {key: model.export_rows() for key, model in self.models.items()}

        try:
            self.svc.guardar_dados_gerais(self.session, self.context, payload)
            self.session.commit()
        except Exception as exc:
            self.session.rollback()
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao guardar dados do item: {exc}")
            return

        ctx = self.context
        item_label = getattr(ctx, "item_ordem", None)
        if item_label is None:
            item_label = getattr(ctx, "item_id", None)
        item_text = str(item_label) if item_label is not None else "-"

        versao = (getattr(ctx, "versao", "") or "").strip()
        versao_text = versao.zfill(2) if versao.isdigit() else (versao or "-")

        mensagem = (
            f"Dados do Item: {item_text} para o Orcamento: {getattr(ctx, 'num_orcamento', '-')}"
            f" com Versao: {versao_text} gravados com sucesso."
        )
        QtWidgets.QMessageBox.information(self, "Sucesso", mensagem)

    # ------------------------------------------------------------------ Local models

    # ------------------------------------------------------------------ Local models
    def on_guardar_modelo(self, key: str) -> None:  # type: ignore[override]
        if not self.context:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Nenhum item selecionado.")
            return

        linhas = self.models[key].export_rows()
        if not linhas:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Nao existem linhas para guardar.")
            return

        modelos_existentes = svc_di.listar_modelos(
            self.session,
            orcamento_id=self.context.orcamento_id,
            item_id=self.context.item_id,
            user_id=getattr(self.current_user, "id", None),
        )
        nomes = [m.nome_modelo for m in modelos_existentes]
        default_idx = 0 if nomes else -1
        nome, ok = QtWidgets.QInputDialog.getItem(
            self,
            "Guardar Dados Items",
            "Selecione ou escreva o nome do modelo:",
            nomes or ["<novo>"],
            default_idx,
            True,
        )
        if not ok:
            return
        nome = nome.strip()
        if not nome or nome == "<novo>":
            QtWidgets.QMessageBox.warning(self, "Aviso", "Nome invalido.")
            return

        replace_id: Optional[int] = None
        for m in modelos_existentes:
            if m.nome_modelo.strip().lower() == nome.lower():
                resp = QtWidgets.QMessageBox.question(
                    self,
                    "Confirmar",
                    "Ja existe um modelo com este nome. Pretende substitui-lo?",
                )
                if resp != QtWidgets.QMessageBox.StandardButton.Yes:
                    return
                replace_id = m.id
                break

        try:
            payload = {key: linhas}
            svc_di.guardar_modelo(
                self.session,
                self.context,
                nome,
                payload,
                replace_model_id=replace_id,
            )
            QtWidgets.QMessageBox.information(self, "Sucesso", "Dados Items guardados.")
        except Exception as exc:  # pragma: no cover - UI feedback
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao guardar: {exc}")

    def on_importar_modelo(self, key: str) -> None:  # type: ignore[override]
        if not self.context:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Nenhum item selecionado.")
            return

        dialog = ImportarDadosItemsDialog(
            session=self.session,
            context=self.context,
            tipo_menu=key,
            current_user=self.current_user,
            parent=self,
        )
        if dialog.exec() != QtWidgets.QDialog.Accepted:
            return

        rows = dialog.selected_rows()
        if not rows:
            return

        replace = dialog.replace_existing()

        self._apply_imported_rows(key, rows, replace=replace)

    def _extract_rows_for_import(
        self,
        origin: str,
        linhas_por_menu: Mapping[str, Sequence[Mapping[str, Any]]],
        menu: str,
    ) -> List[Dict[str, Any]]:
        return _extract_rows_from_payload(origin, linhas_por_menu, menu)

    def on_importar_multi_modelos(self) -> None:  # type: ignore[override]
        if not self.context:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Nenhum item selecionado.")
            return

        dialog = ImportarMultiDadosItemsDialog(
            session=self.session,
            context=self.context,
            current_user=self.current_user,
            parent=self,
        )
        if dialog.exec() != QtWidgets.QDialog.Accepted:
            return

        selections = dialog.selected_models()
        if not selections:
            return

        user_id = getattr(self.current_user, "id", None)
        for menu, info in selections.items():
            origin, model_id, replace = info

            try:
                if origin == "local":
                    linhas_por_menu = svc_di.carregar_modelo(self.session, model_id)
                else:
                    linhas_por_menu = svc_dg.carregar_modelo(self.session, model_id, user_id=user_id)
            except Exception as exc:  # pragma: no cover
                QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao importar {menu}: {exc}")
                continue

            linhas = self._extract_rows_for_import(origin, linhas_por_menu, menu)
            self._apply_imported_rows(menu, linhas, replace=replace)

class ImportarDadosItemsDialog(QtWidgets.QDialog):
    ORIGINS: Tuple[str, str] = ("local", "global")

    def __init__(
        self,
        session: Session,
        context: svc_di.DadosItemsContext,
        tipo_menu: str,
        current_user=None,
        parent: Optional[QtWidgets.QWidget] = None,
    ):
        super().__init__(parent)
        self.session = session
        self.context = context
        self.tipo_menu = tipo_menu
        self.current_user = current_user

        self._selected_source: Optional[Tuple[str, int]] = None
        self._selected_rows: List[Dict[str, Any]] = []

        self.setWindowTitle("Importar Dados Items")
        self.resize(1100, 650)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self.tabs = QtWidgets.QTabWidget(self)
        layout.addWidget(self.tabs, 1)

        self.models: Dict[str, List[Any]] = {origin: [] for origin in self.ORIGINS}
        self.models_list: Dict[str, QtWidgets.QListWidget] = {}
        self.tables: Dict[str, QtWidgets.QTableWidget] = {}
        self.display_lines: Dict[str, List[Dict[str, Any]]] = {origin: [] for origin in self.ORIGINS}
        self.current_model_id: Dict[str, Optional[int]] = {origin: None for origin in self.ORIGINS}

        titles = {
            "local": "Dados Items",
            "global": "Dados Gerais",
        }

        for origin in self.ORIGINS:
            page = QtWidgets.QWidget()
            page_layout = QtWidgets.QVBoxLayout(page)
            page_layout.setContentsMargins(0, 0, 0, 0)
            page_layout.setSpacing(6)

            splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal, page)
            splitter.setChildrenCollapsible(False)

            list_widget = QtWidgets.QListWidget()
            list_widget.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
            actions_layout = QtWidgets.QHBoxLayout()
            btn_rename = QtWidgets.QPushButton("Renomear")
            btn_delete = QtWidgets.QPushButton("Eliminar")
            btn_rename.clicked.connect(partial(self._on_rename_model, origin))
            btn_delete.clicked.connect(partial(self._on_delete_model, origin))
            actions_layout.addWidget(btn_rename)
            actions_layout.addWidget(btn_delete)
            list_container = QtWidgets.QWidget()
            list_layout = QtWidgets.QVBoxLayout(list_container)
            list_layout.setContentsMargins(0, 0, 0, 0)
            list_layout.addWidget(list_widget)
            list_layout.addLayout(actions_layout)
            splitter.addWidget(list_container)

            table = QtWidgets.QTableWidget()
            table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
            table.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
            table.setAlternatingRowColors(True)
            splitter.addWidget(table)

            splitter.setStretchFactor(0, 1)
            splitter.setStretchFactor(1, 2)

            page_layout.addWidget(splitter, 1)
            self.tabs.addTab(page, titles[origin])

            list_widget.itemSelectionChanged.connect(partial(self._on_model_selected, origin))

            self.models_list[origin] = list_widget
            self.tables[origin] = table

        controls_layout = QtWidgets.QHBoxLayout()
        self.btn_select_all = QtWidgets.QPushButton("Selecionar Tudo")
        self.btn_clear_selection = QtWidgets.QPushButton("Limpar Selecao")
        self.btn_select_all.clicked.connect(self._select_all_current)
        self.btn_clear_selection.clicked.connect(self._clear_selection_current)
        controls_layout.addWidget(self.btn_select_all)
        controls_layout.addWidget(self.btn_clear_selection)
        controls_layout.addStretch()
        layout.addLayout(controls_layout)

        options_layout = QtWidgets.QHBoxLayout()
        self.radio_replace = QtWidgets.QRadioButton("Substituir linhas atuais")
        self.radio_replace.setChecked(True)
        self.radio_append = QtWidgets.QRadioButton("Adicionar / mesclar")
        options_layout.addWidget(self.radio_replace)
        options_layout.addWidget(self.radio_append)
        options_layout.addStretch()
        layout.addLayout(options_layout)

        self.button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        self.tabs.currentChanged.connect(lambda _: self._update_controls_state())

        self._populate_models("local")
        self._populate_models("global")

        if self.models_list["local"].count():
            self.models_list["local"].setCurrentRow(0)
        elif self.models_list["global"].count():
            self.tabs.setCurrentIndex(1)
            self.models_list["global"].setCurrentRow(0)

        self._update_controls_state()

    def _populate_models(self, origin: str) -> None:
        list_widget = self.models_list[origin]
        list_widget.blockSignals(True)
        list_widget.clear()
        try:
            if origin == "local":
                models = svc_di.listar_modelos(
                    self.session,
                    orcamento_id=self.context.orcamento_id,
                    item_id=self.context.item_id,
                )
            else:
                user_id = getattr(self.current_user, "id", None)
                models = (
                    svc_dg.listar_modelos(self.session, user_id=user_id, tipo_menu=self.tipo_menu)
                    if user_id
                    else []
                )
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao carregar modelos: {exc}")
            models = []
        finally:
            list_widget.blockSignals(False)

        self.models[origin] = models

        list_widget.blockSignals(True)
        for model in models:
            item = QtWidgets.QListWidgetItem(self._model_display(model))
            item.setData(QtCore.Qt.UserRole, getattr(model, "id", None))
            list_widget.addItem(item)
        list_widget.blockSignals(False)

        self.display_lines[origin] = []
        self.current_model_id[origin] = None

        table = self.tables[origin]
        table.setRowCount(0)
        table.setColumnCount(0)

    def _model_display(self, model: Any) -> str:
        display = getattr(model, "nome_modelo", str(model))
        if display.startswith("__GLOBAL__|"):
            display = f"[Global] {display[len('__GLOBAL__|'):]}"
        created = getattr(model, "created_at", None)
        if created:
            try:
                display += f" ({created})"
            except Exception:
                pass
        return display

    def _on_model_selected(self, origin: str) -> None:
        list_widget = self.models_list[origin]
        item = list_widget.currentItem()
        if not item:
            self.display_lines[origin] = []
            self.current_model_id[origin] = None
            table = self.tables[origin]
            table.setRowCount(0)
            table.setColumnCount(0)
            self._update_controls_state()
            return

        model_id = item.data(QtCore.Qt.UserRole)
        payload = self._load_model_payload(origin, model_id)

        rows = _extract_rows_from_payload(origin, payload, self.tipo_menu)
        self.display_lines[origin] = self._filtered_lines(rows)
        self.current_model_id[origin] = model_id
        self._populate_table(origin)
        self._update_controls_state()

    def _load_model_payload(self, origin: str, model_id: Optional[int]) -> Optional[Mapping[str, Any]]:
        if model_id is None:
            return None
        try:
            if origin == "local":
                return svc_di.carregar_modelo(self.session, model_id)
            user_id = getattr(self.current_user, "id", None)
            return svc_dg.carregar_modelo(self.session, model_id, user_id=user_id)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao carregar modelo: {exc}")
            return None

    def _filtered_lines(self, rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
        return [dict(row) for row in rows if isinstance(row, Mapping)]

    def _populate_table(self, origin: str) -> None:
        table = self.tables[origin]
        rows = self.display_lines.get(origin, [])
        columns = PREVIEW_COLUMNS.get(self.tipo_menu, PREVIEW_COLUMNS["ferragens"])

        table.clear()
        table.setColumnCount(len(columns) + 1)
        table.setRowCount(len(rows))
        table.setHorizontalHeaderLabels(["Importar"] + [col[0] for col in columns])

        for row_idx, row_data in enumerate(rows):
            check_item = QtWidgets.QTableWidgetItem()
            check_item.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
            check_item.setCheckState(QtCore.Qt.Checked)
            table.setItem(row_idx, 0, check_item)

            for col_idx, (_, key, kind) in enumerate(columns, start=1):
                value = _format_preview_value(kind, row_data.get(key))
                item = QtWidgets.QTableWidgetItem(value)
                item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                table.setItem(row_idx, col_idx, item)

        if rows:
            table.resizeColumnsToContents()

    def _current_origin(self) -> str:
        index = self.tabs.currentIndex()
        if 0 <= index < len(self.ORIGINS):
            return self.ORIGINS[index]
        return self.ORIGINS[0]

    def _set_all_checks(self, origin: str, state: QtCore.Qt.CheckState) -> None:
        table = self.tables.get(origin)
        if not table:
            return
        for row_idx in range(table.rowCount()):
            item = table.item(row_idx, 0)
            if item:
                item.setCheckState(state)

    def _select_all_current(self) -> None:
        self._set_all_checks(self._current_origin(), QtCore.Qt.Checked)

    def _clear_selection_current(self) -> None:
        self._set_all_checks(self._current_origin(), QtCore.Qt.Unchecked)

    def _collect_selected_rows(self, origin: str) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        table = self.tables.get(origin)
        display = self.display_lines.get(origin, [])
        if not table or not display:
            return rows
        for row_idx in range(table.rowCount()):
            item = table.item(row_idx, 0)
            if item and item.checkState() == QtCore.Qt.Checked:
                try:
                    rows.append(dict(display[row_idx]))
                except IndexError:
                    continue
        return rows

    def _update_controls_state(self) -> None:
        origin = self._current_origin()
        table = self.tables.get(origin)
        has_rows = bool(table and table.rowCount())
        self.btn_select_all.setEnabled(has_rows)
        self.btn_clear_selection.setEnabled(has_rows)

    def selected_source(self) -> Optional[Tuple[str, int]]:
        return self._selected_source

    def selected_rows(self) -> List[Dict[str, Any]]:
        return [dict(row) for row in self._selected_rows]

    def replace_existing(self) -> bool:
        return self.radio_replace.isChecked()

    def accept(self) -> None:
        origin = self._current_origin()
        model_id = self.current_model_id.get(origin)
        if not model_id:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Selecione um modelo para importar.")
            return

        rows = self._collect_selected_rows(origin)
        if not rows:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Selecione pelo menos uma linha para importar.")
            return

        self._selected_source = (origin, model_id)
        self._selected_rows = rows
        super().accept()

    def _on_delete_model(self, origin: str) -> None:
        list_widget = self.models_list.get(origin)
        if not list_widget:
            return
        item = list_widget.currentItem()
        if not item:
            return
        model_id = item.data(QtCore.Qt.UserRole)
        if not model_id:
            return
        if QtWidgets.QMessageBox.question(self, "Eliminar", "Eliminar este modelo?") != QtWidgets.QMessageBox.Yes:
            return
        try:
            if origin == "local":
                svc_di.eliminar_modelo(self.session, modelo_id=model_id, orcamento_id=self.context.orcamento_id)
            else:
                user_id = getattr(self.current_user, "id", None)
                svc_dg.eliminar_modelo(self.session, modelo_id=model_id, user_id=user_id)
            self.session.commit()
        except Exception as exc:
            self.session.rollback()
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao eliminar: {exc}")
            return
        self._populate_models(origin)

    def _on_rename_model(self, origin: str) -> None:
        list_widget = self.models_list.get(origin)
        if not list_widget:
            return
        item = list_widget.currentItem()
        if not item:
            return
        model_id = item.data(QtCore.Qt.UserRole)
        if not model_id:
            return
        base_name = item.text().split(" (")[0]
        new_name, ok = QtWidgets.QInputDialog.getText(self, "Renomear Modelo", "Novo nome:", text=base_name)
        if not ok or not new_name.strip():
            return
        try:
            if origin == "local":
                svc_di.renomear_modelo(
                    self.session,
                    modelo_id=model_id,
                    orcamento_id=self.context.orcamento_id,
                    novo_nome=new_name.strip(),
                )
            else:
                user_id = getattr(self.current_user, "id", None)
                svc_dg.renomear_modelo(self.session, modelo_id=model_id, user_id=user_id, novo_nome=new_name.strip())
            self.session.commit()
        except Exception as exc:
            self.session.rollback()
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao renomear: {exc}")
            return
        self._populate_models(origin)

    def _on_delete_model(self, origin: str) -> None:
        list_widget = self.models_list.get(origin)
        if not list_widget:
            return
        item = list_widget.currentItem()
        if not item:
            return
        model_id = item.data(QtCore.Qt.UserRole)
        if not model_id:
            return
        if QtWidgets.QMessageBox.question(self, "Eliminar", "Eliminar este modelo?") != QtWidgets.QMessageBox.Yes:
            return
        try:
            if origin == "local":
                svc_di.eliminar_modelo(self.session, modelo_id=model_id, orcamento_id=self.context.orcamento_id)
            else:
                user_id = getattr(self.current_user, "id", None)
                svc_dg.eliminar_modelo(self.session, modelo_id=model_id, user_id=user_id)
            self.session.commit()
        except Exception as exc:
            self.session.rollback()
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao eliminar: {exc}")
            return
        self._populate_models(origin)

    def _on_rename_model(self, origin: str) -> None:
        list_widget = self.models_list.get(origin)
        if not list_widget:
            return
        item = list_widget.currentItem()
        if not item:
            return
        model_id = item.data(QtCore.Qt.UserRole)
        if not model_id:
            return
        base_name = item.text().split(" (")[0]
        new_name, ok = QtWidgets.QInputDialog.getText(self, "Renomear Modelo", "Novo nome:", text=base_name)
        if not ok or not new_name.strip():
            return
        try:
            if origin == "local":
                svc_di.renomear_modelo(
                    self.session,
                    modelo_id=model_id,
                    orcamento_id=self.context.orcamento_id,
                    novo_nome=new_name.strip(),
                )
            else:
                user_id = getattr(self.current_user, "id", None)
                svc_dg.renomear_modelo(self.session, modelo_id=model_id, user_id=user_id, novo_nome=new_name.strip())
            self.session.commit()
        except Exception as exc:
            self.session.rollback()
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao renomear: {exc}")
            return
        self._populate_models(origin)


class ImportarMultiDadosItemsDialog(QtWidgets.QDialog):
    def __init__(
        self,
        session: Session,
        context: svc_di.DadosItemsContext,
        current_user=None,
        parent: Optional[QtWidgets.QWidget] = None,
    ):
        super().__init__(parent)
        self.session = session
        self.context = context
        self.current_user = current_user
        self.selections: Dict[str, Tuple[str, int, bool]] = {}

        self.setWindowTitle("Importar Multi Dados Items")
        self.resize(620, 480)

        layout = QtWidgets.QVBoxLayout(self)

        self.sections: Dict[str, Dict[str, Any]] = {}

        for menu, titulo in (
            (svc_di.MENU_MATERIAIS, "Materiais"),
            (svc_di.MENU_FERRAGENS, "Ferragens"),
            (svc_di.MENU_SIS_CORRER, "Sistemas Correr"),
            (svc_di.MENU_ACABAMENTOS, "Acabamentos"),
        ):
            box = QtWidgets.QGroupBox(titulo)
            box_layout = QtWidgets.QHBoxLayout(box)

            combo = QtWidgets.QComboBox()
            combo.addItem("(nenhum)", None)
            for model in svc_di.listar_modelos(
                self.session,
                orcamento_id=self.context.orcamento_id,
                item_id=self.context.item_id,
            ):
                combo.addItem(f"Local - {model.nome_modelo}", ("local", model.id))

            user_id = getattr(self.current_user, "id", None)
            for model in svc_dg.listar_modelos(self.session, user_id=user_id, tipo_menu=menu):
                combo.addItem(f"Global - {model.nome_modelo}", ("global", model.id))

            replace_check = QtWidgets.QCheckBox("Substituir", checked=True)

            box_layout.addWidget(combo, 1)
            box_layout.addWidget(replace_check)

            layout.addWidget(box)
            self.sections[menu] = {"combo": combo, "replace": replace_check}

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_accept(self) -> None:
        selections: Dict[str, Tuple[str, int, bool]] = {}
        for menu, widgets in self.sections.items():
            combo: QtWidgets.QComboBox = widgets["combo"]
            data = combo.currentData()
            if not data:
                continue
            origin, model_id = data
            replace = widgets["replace"].isChecked()
            selections[menu] = (origin, model_id, replace)
        if not selections:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Selecione pelo menos um modelo.")
            return
        self.selections = selections
        self.accept()

    def selected_models(self) -> Dict[str, Tuple[str, int, bool]]:
        return self.selections


class MateriaPrimaConflictDialog(QtWidgets.QDialog):
    COLS_DISPLAY = [
        ("ref_le", "Ref_LE"),
        ("descricao_material", "Descrição Material"),
        ("preco_tab", "Preço Tabela"),
        ("preco_liq", "Preço Líquido"),
        ("margem", "Margem"),
        ("desconto", "Desconto"),
        ("und", "Und"),
    ]

    def __init__(self, conflicts: Mapping[int, Mapping[str, Any]], parent=None, line_header: str = "Linha") -> None:
        super().__init__(parent)
        self.setWindowTitle("Diferenças entre Dados do Modelo vs Matérias-Primas")
        self.resize(1700, 820)
        self._choices: Dict[int, bool] = {}  # row_idx -> use_mp
        self._conflicts = conflicts
        self._line_header = line_header

        layout = QtWidgets.QVBoxLayout(self)
        info = QtWidgets.QLabel(
            "Foram encontradas diferenças entre o modelo importado e a tabela de Matérias-Primas.\n"
            "Para cada linha, escolha se pretende aplicar os valores do Modelo ou da Matéria-Prima."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal, self)

        self.table_model = QtWidgets.QTableWidget()
        self.COLS_MODEL = [("label", line_header)] + self.COLS_DISPLAY
        self.table_model.setColumnCount(len(self.COLS_MODEL) + 1)
        self.table_model.setHorizontalHeaderLabels(["Usar Modelo"] + [label for _, label in self.COLS_MODEL])
        self.table_model.setRowCount(len(conflicts))

        self.table_mp = QtWidgets.QTableWidget()
        self.table_mp.setColumnCount(len(self.COLS_DISPLAY) + 1)
        self.table_mp.setHorizontalHeaderLabels(["Usar MP"] + [label for _, label in self.COLS_DISPLAY])
        self.table_mp.setRowCount(len(conflicts))

        header_wrapper = QtWidgets.QWidget()
        header_layout = QtWidgets.QHBoxLayout(header_wrapper)
        lbl_model = QtWidgets.QLabel("<b>DADOS DO MODELO</b>")
        lbl_mp = QtWidgets.QLabel("<b>DADOS MAT�RIAS-PRIMAS</b>")
        header_layout.addWidget(lbl_model, 1)
        header_layout.addWidget(lbl_mp, 1)
        layout.addWidget(header_wrapper)

        def _format_value(field: str, val: Any) -> str:
            if val is None or val == "":
                return ""
            try:
                num = float(val)
            except Exception:
                return str(val)
            if field in {"preco_tab", "preco_liq"}:
                return f"{num:,.2f} €"
            if field in {"margem", "desconto"}:
                return f"{num*100:.2f} %"
            return str(val)

        sorted_conflicts = list(conflicts.items())
        self._row_keys = [row_idx for row_idx, _ in sorted_conflicts]
        for r_idx, (row_idx, data) in enumerate(sorted_conflicts):
            model_data = data.get("model", {})
            mp_data = data.get("mp_full") or data.get("mp", {})
            # mapeia aliases de materias-primas
            def _mp_val(*keys: str):
                for k in keys:
                    if k in mp_data and mp_data.get(k) not in (None, ""):
                        return mp_data.get(k)
                    upper = k.upper()
                    if upper in mp_data and mp_data.get(upper) not in (None, ""):
                        return mp_data.get(upper)
                return mp_data.get(keys[0], None)

            mp_display = {
                "ref_le": _mp_val("ref_le"),
                "descricao_material": _mp_val(
                    "descricao_material",
                    "descricao_no_orcamento",
                    "descricao_orcamento",
                    "DESCRICAO_no_ORCAMENTO",
                    "DESCRICAO_ORCAMENTO",
                ),
                "preco_tab": _mp_val("preco_tab", "preco_tabela", "PRECO_TABELA"),
                "preco_liq": _mp_val("preco_liq", "pliq", "PLIQ"),
                "margem": _mp_val("margem", "MARGEM"),
                "desconto": _mp_val("desconto", "DESCONTO"),
                "und": _mp_val("und", "UND"),
            }
            model_data["label"] = data.get("label") or model_data.get("descricao_material") or model_data.get("ref_le")

            chk_model = QtWidgets.QTableWidgetItem()
            chk_model.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
            chk_model.setCheckState(QtCore.Qt.Unchecked)
            self.table_model.setItem(r_idx, 0, chk_model)

            chk_mp = QtWidgets.QTableWidgetItem()
            chk_mp.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
            chk_mp.setCheckState(QtCore.Qt.Checked)
            self.table_mp.setItem(r_idx, 0, chk_mp)
            self._choices[row_idx] = True

            # modelo (inclui coluna de linha/aba)
            for c_idx, (field, _) in enumerate(self.COLS_MODEL, start=1):
                model_val = model_data.get(field)
                item_model = QtWidgets.QTableWidgetItem(_format_value(field, model_val))
                self.table_model.setItem(r_idx, c_idx, item_model)

            # materias-primas: mantém apenas as colunas originais, alinhadas
            for mp_c_idx, (field, _) in enumerate(self.COLS_DISPLAY, start=1):
                mp_val = mp_display.get(field)
                item_mp = QtWidgets.QTableWidgetItem(_format_value(field, mp_val))
                model_val = model_data.get(field)
                if str(model_val) != str(mp_val):
                    # realça apenas colunas não-idênticas
                    item_mp.setBackground(QtGui.QColor("#e0e0e0"))
                    # também realça célula correspondente no modelo
                    model_item = self.table_model.item(r_idx, mp_c_idx + 1)  # +1 porque modelo tem coluna label extra
                    if model_item:
                        model_item.setBackground(QtGui.QColor("#e0e0e0"))
                self.table_mp.setItem(r_idx, mp_c_idx, item_mp)

        self.table_model.resizeColumnsToContents()
        self.table_mp.resizeColumnsToContents()
        splitter.addWidget(self.table_model)
        splitter.addWidget(self.table_mp)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter, 1)

        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        # ligações únicas para mutual exclusivity
        self.table_model.itemChanged.connect(self._on_model_item_changed)
        self.table_mp.itemChanged.connect(self._on_mp_item_changed)

    def selected_sources(self) -> Dict[int, bool]:
        return dict(self._choices)

    def _toggle_choice(self, row_key: int, use_mp: bool) -> None:
        self._choices[row_key] = use_mp
        # sincroniza checkboxes sem recursão
        row_idx = self._row_keys.index(row_key)
        m_item = self.table_model.item(row_idx, 0)
        p_item = self.table_mp.item(row_idx, 0)
        if not m_item or not p_item:
            return
        with QtCore.QSignalBlocker(self.table_model), QtCore.QSignalBlocker(self.table_mp):
            if use_mp:
                p_item.setCheckState(QtCore.Qt.Checked)
                m_item.setCheckState(QtCore.Qt.Unchecked)
            else:
                m_item.setCheckState(QtCore.Qt.Checked)
                p_item.setCheckState(QtCore.Qt.Unchecked)

    def _on_model_item_changed(self, item: QtWidgets.QTableWidgetItem) -> None:
        if item.column() != 0:
            return
        row_idx = item.row()
        if not (0 <= row_idx < len(self._row_keys)):
            return
        use_model = item.checkState() == QtCore.Qt.Checked
        self._toggle_choice(self._row_keys[row_idx], use_mp=not use_model)

    def _on_mp_item_changed(self, item: QtWidgets.QTableWidgetItem) -> None:
        if item.column() != 0:
            return
        row_idx = item.row()
        if not (0 <= row_idx < len(self._row_keys)):
            return
        use_mp = item.checkState() == QtCore.Qt.Checked
        self._toggle_choice(self._row_keys[row_idx], use_mp=use_mp)
