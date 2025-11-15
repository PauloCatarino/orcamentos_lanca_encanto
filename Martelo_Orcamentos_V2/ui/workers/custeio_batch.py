from __future__ import annotations

import logging
from typing import Dict, List, Optional

from PySide6 import QtCore, QtGui
from sqlalchemy import select

from Martelo_Orcamentos_V2.app.db import SessionLocal
from Martelo_Orcamentos_V2.app.models.orcamento import OrcamentoItem
from Martelo_Orcamentos_V2.app.services import custeio_items as svc_custeio
from Martelo_Orcamentos_V2.app.services import dados_items as svc_dados_items
from Martelo_Orcamentos_V2.app.services import producao as svc_producao
from Martelo_Orcamentos_V2.ui.pages.custeio_items import CusteioTableModel

logger = logging.getLogger(__name__)


class HeadlessCusteioPage(QtCore.QObject):
    """
    Headless helper usado pelo modelo de custeio para recalcular linhas fora da UI.
    Fornece apenas os metodos/propriedades necessarios pelo CusteioTableModel.
    """

    def __init__(
        self,
        session,
        ctx,
        *,
        production_mode: str,
        dimension_values: Optional[Dict[str, Optional[float]]] = None,
        production_rates: Optional[Dict[str, Dict[str, float]]] = None,
    ) -> None:
        super().__init__()
        self.session = session
        self.context = ctx
        self._production_mode = (production_mode or "STD").upper()
        self._dimension_values = dict(dimension_values or {})
        self._production_rates = {
            (key or "").upper(): value for key, value in (production_rates or {}).items()
        }
        self._hidden_column_keys = set()
        self._column_visibility_dirty = False
        self._collapsed_groups = set()

    # ---- API usada pelo modelo ----
    def _coerce_dimension_value(self, text) -> Optional[float]:
        if text in (None, ""):
            return None
        stripped = str(text).strip()
        if not stripped:
            return None
        stripped = stripped.replace(",", ".")
        try:
            return float(stripped)
        except ValueError:
            return None

    def dimension_values(self) -> Dict[str, Optional[float]]:
        return dict(self._dimension_values)

    def production_mode(self) -> str:
        return self._production_mode

    def get_production_rate_info(self, key: str) -> Optional[Dict[str, float]]:
        if not key:
            return None
        return self._production_rates.get(key.upper())

    def _set_rows_dirty(self, _dirty: bool) -> None:  # pragma: no cover - no-op
        return

    def _icon(self, _name: str) -> QtGui.QIcon:
        return QtGui.QIcon()

    def _apply_collapse_state(self) -> None:  # pragma: no cover - no-op
        return


class CusteioBatchWorker(QtCore.QObject):
    progress = QtCore.Signal(int, int)
    finished = QtCore.Signal(bool, str)

    def __init__(
        self,
        *,
        orcamento_id: int,
        versao: str,
        production_mode: str,
        user_id: Optional[int],
    ) -> None:
        super().__init__()
        self._orcamento_id = orcamento_id
        self._versao = (versao or "01").strip() or "01"
        self._production_mode = (production_mode or "STD").upper()
        self._user_id = user_id
        self._cancel_requested = False

    def request_cancel(self) -> None:
        self._cancel_requested = True

    @QtCore.Slot()
    def run(self) -> None:
        session = SessionLocal()
        try:
            if not self._user_id:
                raise RuntimeError("Utilizador atual desconhecido para atualizar o custeio.")
            ctx_prod = svc_producao.build_context(
                session, self._orcamento_id, self._user_id, versao=self._versao
            )
            rate_entries = svc_producao.load_values(session, ctx_prod)
            rate_lookup = {
                (entry.get("descricao_equipamento") or "").upper(): entry for entry in rate_entries
            }

            item_ids: List[int] = (
                session.execute(
                    select(OrcamentoItem.id_item)
                        .where(OrcamentoItem.id_orcamento == self._orcamento_id)
                        .order_by(OrcamentoItem.item_ord, OrcamentoItem.id_item)
                )
                .scalars()
                .all()
            )
            total = len(item_ids)

            for idx, item_id in enumerate(item_ids, start=1):
                if self._cancel_requested:
                    self.finished.emit(False, "cancelled")
                    return
                try:
                    ctx = svc_dados_items.carregar_contexto(
                        session, self._orcamento_id, item_id=item_id
                    )
                except Exception as exc:
                    logger.exception("Falha ao carregar contexto de dados do item %s: %s", item_id, exc)
                    continue
                if ctx is None:
                    continue
                try:
                    dimension_values, _ = svc_custeio.carregar_dimensoes(session, ctx)
                except Exception:
                    dimension_values = {}

                page_stub = HeadlessCusteioPage(
                    session,
                    ctx,
                    production_mode=self._production_mode,
                    dimension_values=dimension_values,
                    production_rates=rate_lookup,
                )

                linhas = svc_custeio.listar_custeio_items(session, self._orcamento_id, item_id)
                if not linhas:
                    continue

                model = CusteioTableModel(parent=page_stub)
                model.load_rows(linhas)
                model.recalculate_all()
                payload = model.export_rows()

                svc_custeio.salvar_custeio_items(
                    session,
                    ctx,
                    payload,
                    page_stub.dimension_values(),
                )

                self.progress.emit(idx, total)

            self.finished.emit(True, "")
        except Exception as exc:  # pragma: no cover - runtime safeguard
            self.finished.emit(False, str(exc))
        finally:
            session.close()
