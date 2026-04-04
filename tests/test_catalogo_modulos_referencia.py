from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy import Integer, create_engine
from sqlalchemy.orm import sessionmaker

from Martelo_Orcamentos_V2.app.services import custeio_items, modulos
from Martelo_Orcamentos_V2.app.services import dados_items as svc_dados_items
from Martelo_Orcamentos_V2.app.db import Base
from Martelo_Orcamentos_V2.app.models.client import Client
from Martelo_Orcamentos_V2.app.models.custeio import CusteioItem, CusteioItemDimensoes
from Martelo_Orcamentos_V2.app.models.dados_gerais import (
    DadosItemsAcabamento,
    DadosItemsFerragem,
    DadosItemsMaterial,
    DadosItemsSistemaCorrer,
)
from Martelo_Orcamentos_V2.app.models.materia_prima import MateriaPrima
from Martelo_Orcamentos_V2.app.models.orcamento import Orcamento, OrcamentoItem
from Martelo_Orcamentos_V2.app.models.user import User


def _material_stub(
    descricao: str,
    *,
    familia: str = "PLACAS",
    tipo: str | None = None,
    und: str = "UN",
) -> SimpleNamespace:
    return SimpleNamespace(
        descricao=descricao,
        ref_le=f"REF-{descricao[:12]}",
        descricao_material=descricao,
        preco_liq=10.0,
        und=und,
        desp=0.0,
        orl_0_4=None,
        orl_1_0=None,
        tipo=tipo,
        familia=familia,
        acabamento_sup=None,
        acabamento_inf=None,
        comp=None,
        larg=None,
        esp=19 if familia == "PLACAS" else None,
        comp_mp=None,
        larg_mp=None,
        esp_mp=None,
        spp_ml_und=None,
        custo_mp_und=1.0,
        custo_mp_total=1.0,
    )


def _snapshot_um_porta() -> list[dict]:
    return [
        {
            "id": 101,
            "_uid": "row-101",
            "def_peca": "LATERAL",
            "descricao": "Lateral",
            "qt_mod": 1,
            "qt_und": 2,
            "comp": "HM",
            "larg": "PM",
            "esp": 19,
            "familia": "PLACAS",
            "gravar_modulo": True,
            "_row_type": "parent",
            "_group_uid": "corpo-1",
        },
        {
            "id": 102,
            "_uid": "row-102",
            "def_peca": "PRAT. AMOV. [2111] + SUPORTE PRATELEIRA",
            "descricao": "Prateleira Amovivel",
            "qt_mod": 1,
            "qt_und": 5,
            "comp": "LM",
            "larg": "PM",
            "esp": 19,
            "familia": "PLACAS",
            "gravar_modulo": True,
            "_row_type": "parent",
            "_group_uid": "prat-1",
        },
        {
            "id": 103,
            "_uid": "row-103",
            "def_peca": "PORTA ABRIR [2222]",
            "descricao": "Porta Abrir",
            "qt_mod": 1,
            "qt_und": 1,
            "comp": "HM",
            "larg": "LM",
            "esp": 19,
            "familia": "PLACAS",
            "gravar_modulo": True,
            "_row_type": "parent",
            "_group_uid": "porta-1",
        },
        {
            "id": 104,
            "_uid": "row-104",
            "def_peca": "DOBRADICA",
            "descricao": "Dobradiça",
            "qt_mod": 1,
            "qt_und": 4,
            "tipo": "DOBRADICAS",
            "familia": "FERRAGENS",
            "gravar_modulo": True,
            "_row_type": "child",
            "_group_uid": "porta-1",
            "_parent_uid": "row-103",
            "_child_source": "DOBRADICA",
        },
        {
            "id": 105,
            "_uid": "row-105",
            "def_peca": "PUXADOR",
            "descricao": "Puxador",
            "qt_mod": 1,
            "qt_und": 1,
            "tipo": "PUXADOR",
            "familia": "FERRAGENS",
            "gravar_modulo": True,
            "_row_type": "child",
            "_group_uid": "porta-1",
            "_parent_uid": "row-103",
            "_child_source": "PUXADOR",
        },
    ]


def _snapshot_duas_portas() -> list[dict]:
    return [
        {
            "id": 201,
            "_uid": "row-201",
            "def_peca": "PRAT. AMOV. [2111] + SUPORTE PRATELEIRA",
            "descricao": "Prateleira Amovivel",
            "qt_mod": 1,
            "qt_und": 5,
            "comp": "LM",
            "larg": "PM",
            "esp": 19,
            "familia": "PLACAS",
            "gravar_modulo": True,
            "_row_type": "parent",
            "_group_uid": "prat-2",
        },
        {
            "id": 202,
            "_uid": "row-202",
            "def_peca": "PORTA ABRIR [2222]",
            "descricao": "Porta Esquerda",
            "qt_mod": 1,
            "qt_und": 1,
            "comp": "HM",
            "larg": "LM/2",
            "esp": 19,
            "familia": "PLACAS",
            "gravar_modulo": True,
            "_row_type": "parent",
            "_group_uid": "porta-esq",
        },
        {
            "id": 203,
            "_uid": "row-203",
            "def_peca": "PORTA ABRIR [2222]",
            "descricao": "Porta Direita",
            "qt_mod": 1,
            "qt_und": 1,
            "comp": "HM",
            "larg": "LM/2",
            "esp": 19,
            "familia": "PLACAS",
            "gravar_modulo": True,
            "_row_type": "parent",
            "_group_uid": "porta-dir",
        },
        {
            "id": 204,
            "_uid": "row-204",
            "def_peca": "DOBRADICA",
            "descricao": "Dobradiça Esq.",
            "qt_mod": 1,
            "qt_und": 4,
            "tipo": "DOBRADICAS",
            "familia": "FERRAGENS",
            "gravar_modulo": True,
            "_row_type": "child",
            "_group_uid": "porta-esq",
            "_parent_uid": "row-202",
            "_child_source": "DOBRADICA",
        },
        {
            "id": 205,
            "_uid": "row-205",
            "def_peca": "DOBRADICA",
            "descricao": "Dobradiça Dir.",
            "qt_mod": 1,
            "qt_und": 4,
            "tipo": "DOBRADICAS",
            "familia": "FERRAGENS",
            "gravar_modulo": True,
            "_row_type": "child",
            "_group_uid": "porta-dir",
            "_parent_uid": "row-203",
            "_child_source": "DOBRADICA",
        },
    ]


def _snapshot_correr() -> list[dict]:
    return [
        {
            "id": 301,
            "_uid": "row-301",
            "def_peca": "PAINEL CORRER [2222]",
            "descricao": "Painel Correr 1",
            "qt_mod": 1,
            "qt_und": 1,
            "familia": "SISTEMAS CORRER",
            "tipo": "Painel Porta Correr 1",
            "gravar_modulo": True,
            "_row_type": "parent",
            "_group_uid": "correr-1",
        },
        {
            "id": 302,
            "_uid": "row-302",
            "def_peca": "PAINEL CORRER [2222]",
            "descricao": "Painel Correr 2",
            "qt_mod": 1,
            "qt_und": 1,
            "familia": "SISTEMAS CORRER",
            "tipo": "Painel Porta Correr 1",
            "gravar_modulo": True,
            "_row_type": "parent",
            "_group_uid": "correr-2",
        },
        {
            "id": 303,
            "_uid": "row-303",
            "def_peca": "CALHA SUPERIOR {SPP} 2 CORRER",
            "descricao": "Calha Superior",
            "qt_mod": 1,
            "qt_und": 1,
            "familia": "SISTEMAS CORRER",
            "tipo": "Calha Superior 2 SPP",
            "gravar_modulo": True,
            "_row_type": "parent",
            "_group_uid": "correr-kit",
        },
        {
            "id": 304,
            "_uid": "row-304",
            "def_peca": "CALHA INFERIOR {SPP} 2 CORRER",
            "descricao": "Calha Inferior",
            "qt_mod": 1,
            "qt_und": 1,
            "familia": "SISTEMAS CORRER",
            "tipo": "Calha Inferior 2 SPP",
            "gravar_modulo": True,
            "_row_type": "parent",
            "_group_uid": "correr-kit",
        },
    ]


def _selecoes_um_porta() -> list[str]:
    return [
        "LATERAL",
        "LATERAL",
        "TETO",
        "FUNDO",
        "COSTA",
        *["PRAT. AMOV. [2111] + SUPORTE PRATELEIRA"] * 5,
        "PORTA ABRIR [2222] + DOBRADICA + PUXADOR",
    ]


def _selecoes_duas_portas() -> list[str]:
    return [
        "LATERAL",
        "LATERAL",
        "TETO",
        "FUNDO",
        "COSTA",
        *["PRAT. AMOV. [2111] + SUPORTE PRATELEIRA"] * 5,
        "PORTA ABRIR [2222] + DOBRADICA + PUXADOR",
        "PORTA ABRIR [2222] + DOBRADICA + PUXADOR",
    ]


def _selecoes_correr() -> list[str]:
    return [
        "LATERAL",
        "LATERAL",
        "TETO",
        "FUNDO",
        "PAINEL CORRER [2222]",
        "PAINEL CORRER [2222]",
        "CALHA SUPERIOR {SPP} 2 CORRER",
        "CALHA INFERIOR {SPP} 2 CORRER",
        "ACESSORIO {SPP} 7 CORRER",
        "ACESSORIO {SPP} 8 CORRER",
    ]


class CatalogoModulosSnapshotTests(unittest.TestCase):
    def test_snapshot_um_porta_limpa_transientes_sem_perder_estrutura(self) -> None:
        cleaned = modulos.limpar_linhas_para_modulo(_snapshot_um_porta())

        self.assertTrue(all(row.get("gravar_modulo") is False for row in cleaned))
        self.assertTrue(all("id" not in row for row in cleaned))
        self.assertTrue(all("_uid" not in row for row in cleaned))
        self.assertEqual(sum(1 for row in cleaned if row.get("def_peca") == "PORTA ABRIR [2222]"), 1)
        self.assertEqual(sum(1 for row in cleaned if row.get("_child_source") == "DOBRADICA"), 1)
        self.assertEqual(sum(1 for row in cleaned if row.get("_child_source") == "PUXADOR"), 1)

    def test_snapshot_duas_portas_preserva_dupla_frente_na_limpeza(self) -> None:
        cleaned = modulos.limpar_linhas_para_modulo(_snapshot_duas_portas())

        self.assertEqual(sum(1 for row in cleaned if row.get("def_peca") == "PORTA ABRIR [2222]"), 2)
        self.assertEqual(sum(1 for row in cleaned if row.get("_child_source") == "DOBRADICA"), 2)
        self.assertTrue(all(row.get("gravar_modulo") is False for row in cleaned))

    def test_snapshot_correr_prepara_importacao_sem_ids_e_preserva_familia(self) -> None:
        prepared = modulos.preparar_linhas_para_importacao(_snapshot_correr())

        self.assertTrue(all("id" not in row for row in prepared))
        self.assertTrue(all("_uid" not in row for row in prepared))
        self.assertTrue(all(row.get("gravar_modulo") is False for row in prepared))
        self.assertEqual(sum(1 for row in prepared if row.get("familia") == "SISTEMAS CORRER"), 4)


class CatalogoModulosGeracaoTests(unittest.TestCase):
    def _ctx(self) -> SimpleNamespace:
        return SimpleNamespace(orcamento_id=1, item_id=1)

    @staticmethod
    def _fake_material_por_grupo(_session, _ctx, grupo):
        text = str(grupo or "").upper()
        if not text:
            return None
        if any(token in text for token in ("DOBRADICA", "PUXADOR", "SUPORTE PRATELEIRA")):
            return None
        if any(token in text for token in ("CORRER", "CALHA", "ACESSORIO")):
            return _material_stub(text, familia="SISTEMAS CORRER", tipo=text, und="ML" if "CALHA" in text else "UN")
        return _material_stub(text, familia="PLACAS")

    @staticmethod
    def _fake_ferragem_por_tipo(_session, _ctx, tipo, familia=None):
        tipo_text = str(tipo or "").strip() or "FERRAGEM"
        familia_text = str(familia or "FERRAGENS").strip() or "FERRAGENS"
        und = "ML" if "CALHA" in tipo_text.upper() else "UN"
        return _material_stub(tipo_text, familia=familia_text, tipo=tipo_text, und=und)

    @staticmethod
    def _fake_aplicar_cp(_session, linha, cache=None, **_kwargs):
        linha["_cp_def_found"] = True
        for campo in custeio_items.CP_VALUE_KEYS:
            linha.setdefault(campo, 0)
        return cache or {}

    def _gerar(self, selecoes: list[str]) -> list[dict]:
        with patch.object(custeio_items, "_build_orla_lookup", return_value={}), patch.object(
            custeio_items.svc_def_pecas,
            "mapa_por_nome",
            return_value={},
        ), patch.object(
            custeio_items,
            "aplicar_definicao_cp_linha",
            side_effect=self._fake_aplicar_cp,
        ), patch.object(
            custeio_items,
            "obter_material_por_grupo",
            side_effect=self._fake_material_por_grupo,
        ), patch.object(
            custeio_items,
            "obter_ferragem_por_tipo",
            side_effect=self._fake_ferragem_por_tipo,
        ):
            rows = custeio_items.gerar_linhas_para_selecoes(object(), self._ctx(), selecoes)
        custeio_items.aplicar_dimensoes_automaticas(rows)
        return rows

    def test_catalogo_um_porta_gera_estrutura_base_e_dimensoes_automaticas(self) -> None:
        rows = self._gerar(_selecoes_um_porta())

        porta_rows = [row for row in rows if str(row.get("def_peca") or "").startswith("PORTA ABRIR")]
        prat_rows = [row for row in rows if str(row.get("def_peca") or "").startswith("PRAT. AMOV.")]
        suporte_rows = [row for row in rows if row.get("_child_source") == "SUPORTE PRATELEIRA"]

        self.assertEqual(len(porta_rows), 1)
        self.assertEqual(len(prat_rows), 5)
        self.assertEqual(len(suporte_rows), 5)
        self.assertEqual(porta_rows[0].get("comp"), "HM")
        self.assertEqual(porta_rows[0].get("larg"), "LM")
        self.assertEqual(prat_rows[0].get("comp"), "LM")
        self.assertEqual(prat_rows[0].get("larg"), "PM")

    def test_catalogo_duas_portas_duplica_frente_sem_perder_regras_base(self) -> None:
        rows = self._gerar(_selecoes_duas_portas())

        porta_rows = [row for row in rows if str(row.get("def_peca") or "").startswith("PORTA ABRIR")]
        dobradica_rows = [row for row in rows if row.get("_child_source") == "DOBRADICA"]
        puxador_rows = [row for row in rows if row.get("_child_source") == "PUXADOR"]

        self.assertEqual(len(porta_rows), 2)
        self.assertEqual(len(dobradica_rows), 2)
        self.assertEqual(len(puxador_rows), 2)
        self.assertTrue(all(row.get("comp") == "HM" for row in porta_rows))
        self.assertTrue(all(row.get("larg") == "LM" for row in porta_rows))

    def test_catalogo_correr_gera_componentes_de_sistema_sem_confundir_com_portas_abrir(self) -> None:
        rows = self._gerar(_selecoes_correr())

        painel_rows = [row for row in rows if str(row.get("def_peca") or "").startswith("PAINEL CORRER")]
        sistema_rows = [row for row in rows if row.get("familia") == "SISTEMAS CORRER"]
        porta_abrir_rows = [row for row in rows if str(row.get("def_peca") or "").startswith("PORTA ABRIR")]

        self.assertEqual(len(painel_rows), 2)
        self.assertGreaterEqual(len(sistema_rows), 4)
        self.assertEqual(len(porta_abrir_rows), 0)


class CatalogoModulosDadosItemsDbTests(unittest.TestCase):
    @staticmethod
    def _fake_aplicar_cp(_session, linha, cache=None, **_kwargs):
        linha["_cp_def_found"] = True
        for campo in custeio_items.CP_VALUE_KEYS:
            linha.setdefault(campo, 0)
        return cache or {}

    def setUp(self) -> None:
        self._orig_custeio_id_type = CusteioItem.__table__.c.id.type
        self._orig_dim_id_type = CusteioItemDimensoes.__table__.c.id.type
        CusteioItem.__table__.c.id.type = Integer()
        CusteioItemDimensoes.__table__.c.id.type = Integer()
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(
            self.engine,
            tables=[
                User.__table__,
                Client.__table__,
                Orcamento.__table__,
                OrcamentoItem.__table__,
                MateriaPrima.__table__,
                DadosItemsMaterial.__table__,
                DadosItemsFerragem.__table__,
                DadosItemsSistemaCorrer.__table__,
                DadosItemsAcabamento.__table__,
                CusteioItem.__table__,
                CusteioItemDimensoes.__table__,
            ],
        )
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()
        self._seed_base_context()

    def tearDown(self) -> None:
        self.session.close()
        self.engine.dispose()
        CusteioItem.__table__.c.id.type = self._orig_custeio_id_type
        CusteioItemDimensoes.__table__.c.id.type = self._orig_dim_id_type

    def _seed_base_context(self) -> None:
        self.session.add(User(id=7, username="tester", pass_hash="x"))
        self.session.add(Client(id=1, nome="Cliente Teste", nome_simplex="CLIENTE_TESTE"))
        self.session.add(
            Orcamento(
                id=10,
                ano="2026",
                num_orcamento="260001",
                versao="01",
                client_id=1,
                created_by=7,
                updated_by=7,
            )
        )
        self.session.add(
            OrcamentoItem(
                id_item=11,
                id_orcamento=10,
                versao="01",
                item_ord=1,
                item="Modulo Teste",
                altura=2400,
                largura=900,
                profundidade=600,
                created_by=7,
                updated_by=7,
            )
        )
        self.session.flush()

    def _ctx(self):
        return svc_dados_items.carregar_contexto(self.session, 10, 11)

    def _add_dados_item_material(self, *, group: str, descricao: str) -> None:
        self.session.add(
            DadosItemsMaterial(
                id=100 + self.session.query(DadosItemsMaterial).count(),
                cliente_id=1,
                user_id=7,
                ano="2026",
                num_orcamento="260001",
                versao="01",
                ordem=1,
                orcamento_id=10,
                item_id=11,
                grupo_material=group,
                descricao=descricao,
                ref_le=f"REF-{group}",
                descricao_material=descricao,
                preco_liq=25,
                und="UN",
                desp=0,
                familia="PLACAS",
                linha=1,
                custo_mp_und=5,
                custo_mp_total=5,
            )
        )

    def _add_dados_item_ferragem(self, *, group: str, tipo: str, descricao: str) -> None:
        self.session.add(
            DadosItemsFerragem(
                id=200 + self.session.query(DadosItemsFerragem).count(),
                cliente_id=1,
                user_id=7,
                ano="2026",
                num_orcamento="260001",
                versao="01",
                ordem=1,
                orcamento_id=10,
                item_id=11,
                grupo_ferragem=group,
                descricao=descricao,
                ref_le=f"REF-{tipo}",
                descricao_material=descricao,
                preco_liq=3,
                und="UN",
                desp=0,
                tipo=tipo,
                familia="FERRAGENS",
                linha=1,
                custo_mp_und=1,
                custo_mp_total=1,
            )
        )

    def _add_dados_item_sistema(self, *, group: str, tipo: str, descricao: str, und: str = "UN") -> None:
        self.session.add(
            DadosItemsSistemaCorrer(
                id=300 + self.session.query(DadosItemsSistemaCorrer).count(),
                cliente_id=1,
                user_id=7,
                ano="2026",
                num_orcamento="260001",
                versao="01",
                ordem=1,
                orcamento_id=10,
                item_id=11,
                grupo_sistema=group,
                descricao=descricao,
                ref_le=f"REF-{tipo}",
                descricao_material=descricao,
                preco_liq=12,
                und=und,
                desp=0,
                tipo=tipo,
                familia="SISTEMAS CORRER",
                linha=1,
                custo_mp_und=2,
                custo_mp_total=2,
            )
        )

    def _gerar_real(self, selecoes: list[str]) -> list[dict]:
        ctx = self._ctx()
        with patch.object(
            custeio_items.svc_def_pecas,
            "mapa_por_nome",
            return_value={},
        ), patch.object(
            custeio_items,
            "aplicar_definicao_cp_linha",
            side_effect=self._fake_aplicar_cp,
        ):
            rows = custeio_items.gerar_linhas_para_selecoes(self.session, ctx, selecoes)
        custeio_items.aplicar_dimensoes_automaticas(rows)
        return rows

    @staticmethod
    def _materializar_resultados(
        rows: list[dict],
        *,
        h: float = 2400.0,
        l: float = 900.0,
        p: float = 600.0,
        hm: float | None = None,
        lm: float | None = None,
        pm: float | None = None,
    ) -> None:
        values = {
            "H": h,
            "L": l,
            "P": p,
            "HM": hm if hm is not None else h,
            "LM": lm if lm is not None else l,
            "PM": pm if pm is not None else p,
        }
        for row in rows:
            for key in ("comp", "larg", "esp"):
                expr = row.get(key)
                if key == "esp":
                    if expr not in (None, ""):
                        try:
                            row[f"{key}_res"] = float(expr)
                        except Exception:
                            row[f"{key}_res"] = 19.0
                    continue
                if expr in values:
                    row[f"{key}_res"] = values[str(expr)]
                elif expr not in (None, ""):
                    try:
                        row[f"{key}_res"] = float(expr)
                    except Exception:
                        row[f"{key}_res"] = None

    def _roundtrip_custeio(self, rows: list[dict], *, dimensoes: dict[str, float]) -> list[dict]:
        ctx = self._ctx()
        with patch.object(
            custeio_items.svc_def_pecas,
            "mapa_por_nome",
            return_value={},
        ), patch.object(
            custeio_items,
            "aplicar_definicao_cp_linha",
            side_effect=self._fake_aplicar_cp,
        ), patch.object(
            custeio_items,
            "atualizar_orlas_custeio",
            return_value=None,
        ), patch.object(
            custeio_items,
            "preencher_info_orlas_linha",
            return_value=None,
        ), patch.object(
            custeio_items,
            "_calcular_custo_acabamento_para_registro",
            return_value=0,
        ), patch.object(
            custeio_items,
            "_recalcular_custos_acabamento",
            return_value=None,
        ):
            custeio_items.salvar_custeio_items(self.session, ctx, rows, dimensoes)
            listed = custeio_items.listar_custeio_items(self.session, ctx.orcamento_id, ctx.item_id)
        return listed

    def test_catalogo_um_porta_resolve_dados_items_reais_para_porta_e_ferragens(self) -> None:
        self._add_dados_item_material(group="Portas Abrir 1", descricao="Porta Abrir DB")
        self._add_dados_item_ferragem(group="Dobradicas Base", tipo="DOBRADICAS", descricao="Dobradiça DB")
        self._add_dados_item_ferragem(group="Puxadores Base", tipo="PUXADOR", descricao="Puxador DB")
        self._add_dados_item_ferragem(
            group="Suportes Prateleira Base",
            tipo="SUPORTE PRATELEIRA",
            descricao="Suporte Prateleira DB",
        )
        self.session.flush()

        rows = self._gerar_real(_selecoes_um_porta())

        porta = next(row for row in rows if str(row.get("def_peca") or "").startswith("PORTA ABRIR"))
        dobradica = next(row for row in rows if row.get("_child_source") == "DOBRADICA")
        puxador = next(row for row in rows if row.get("_child_source") == "PUXADOR")
        suporte = next(row for row in rows if row.get("_child_source") == "SUPORTE PRATELEIRA")

        self.assertEqual(porta.get("descricao"), "Porta Abrir DB")
        self.assertEqual(porta.get("mat_default"), "Portas Abrir 1")
        self.assertEqual(dobradica.get("descricao"), "Dobradiça DB")
        self.assertEqual(puxador.get("descricao"), "Puxador DB")
        self.assertEqual(suporte.get("descricao"), "Suporte Prateleira DB")

    def test_catalogo_duas_portas_reutiliza_dados_items_reais_em_ambas_as_frentes(self) -> None:
        self._add_dados_item_material(group="Portas Abrir 1", descricao="Porta Abrir DB")
        self._add_dados_item_ferragem(group="Dobradiças", tipo="DOBRADICAS", descricao="Dobradiça DB")
        self._add_dados_item_ferragem(group="Puxadores", tipo="PUXADOR", descricao="Puxador DB")
        self._add_dados_item_ferragem(
            group="Suportes Prateleira",
            tipo="SUPORTE PRATELEIRA",
            descricao="Suporte Prateleira DB",
        )
        self.session.flush()

        rows = self._gerar_real(_selecoes_duas_portas())

        portas = [row for row in rows if str(row.get("def_peca") or "").startswith("PORTA ABRIR")]
        dobradicas = [row for row in rows if row.get("_child_source") == "DOBRADICA"]
        puxadores = [row for row in rows if row.get("_child_source") == "PUXADOR"]

        self.assertEqual(len(portas), 2)
        self.assertTrue(all(row.get("descricao") == "Porta Abrir DB" for row in portas))
        self.assertTrue(all(row.get("mat_default") == "Portas Abrir 1" for row in portas))
        self.assertEqual(len(dobradicas), 2)
        self.assertTrue(all(row.get("descricao") == "Dobradiça DB" for row in dobradicas))
        self.assertEqual(len(puxadores), 2)
        self.assertTrue(all(row.get("descricao") == "Puxador DB" for row in puxadores))

    def test_catalogo_correr_resolve_sistema_real_a_partir_de_dados_items(self) -> None:
        self._add_dados_item_sistema(
            group="Painel Porta Correr 1",
            tipo="Painel Porta Correr 1",
            descricao="Painel Correr DB",
        )
        self._add_dados_item_sistema(
            group="Calha Superior 2 SPP",
            tipo="Calha Superior 2 SPP",
            descricao="Calha Superior DB",
            und="ML",
        )
        self._add_dados_item_sistema(
            group="Calha Inferior 2 SPP",
            tipo="Calha Inferior 2 SPP",
            descricao="Calha Inferior DB",
            und="ML",
        )
        self._add_dados_item_sistema(
            group="Acessorio 7 SPP",
            tipo="Acessorio 7 SPP",
            descricao="Acessorio 7 DB",
        )
        self._add_dados_item_sistema(
            group="Acessorio 8 SPP",
            tipo="Acessorio 8 SPP",
            descricao="Acessorio 8 DB",
        )
        self.session.flush()

        rows = self._gerar_real(_selecoes_correr())

        paineis = [row for row in rows if str(row.get("def_peca") or "").startswith("PAINEL CORRER")]
        calha_sup = next(row for row in rows if str(row.get("def_peca") or "").startswith("CALHA SUPERIOR"))
        calha_inf = next(row for row in rows if str(row.get("def_peca") or "").startswith("CALHA INFERIOR"))
        acessorio7 = next(row for row in rows if "ACESSORIO {SPP} 7" in str(row.get("def_peca") or ""))

        self.assertEqual(len(paineis), 2)
        self.assertTrue(all(row.get("descricao") == "Painel Correr DB" for row in paineis))
        self.assertEqual(calha_sup.get("descricao"), "Calha Superior DB")
        self.assertEqual(calha_inf.get("descricao"), "Calha Inferior DB")
        self.assertEqual(calha_sup.get("familia"), "SISTEMAS CORRER")
        self.assertEqual(acessorio7.get("descricao"), "Acessorio 7 DB")

    def test_catalogo_um_porta_roundtrip_gerar_salvar_listar_preserva_estrutura(self) -> None:
        self._add_dados_item_material(group="Portas Abrir 1", descricao="Porta Abrir DB")
        self._add_dados_item_ferragem(group="Dobradiças", tipo="DOBRADICAS", descricao="Dobradiça DB")
        self._add_dados_item_ferragem(group="Puxadores", tipo="PUXADOR", descricao="Puxador DB")
        self._add_dados_item_ferragem(
            group="Suportes Prateleira",
            tipo="SUPORTE PRATELEIRA",
            descricao="Suporte Prateleira DB",
        )
        self.session.flush()

        rows = self._gerar_real(_selecoes_um_porta())
        self._materializar_resultados(rows, h=2400, l=600, p=550, lm=600, pm=550)
        listed = self._roundtrip_custeio(rows, dimensoes={"H": 2400, "L": 600, "P": 550})

        portas = [row for row in listed if str(row.get("def_peca") or "").startswith("PORTA ABRIR")]
        prateleiras = [row for row in listed if str(row.get("def_peca") or "").startswith("PRAT. AMOV.")]
        self.assertEqual(len(portas), 1)
        self.assertEqual(len(prateleiras), 5)
        self.assertEqual(portas[0].get("descricao"), "Porta Abrir DB")
        self.assertEqual(portas[0].get("comp"), "HM")
        self.assertEqual(portas[0].get("comp_res"), 2400.0)
        dims, has_record = custeio_items.carregar_dimensoes(self.session, self._ctx())
        self.assertTrue(has_record)
        self.assertEqual(dims["H"], 2400.0)
        self.assertEqual(dims["L"], 600.0)
        self.assertEqual(dims["P"], 550.0)

    def test_catalogo_duas_portas_roundtrip_preserva_dupla_frente_no_reload(self) -> None:
        self._add_dados_item_material(group="Portas Abrir 1", descricao="Porta Abrir DB")
        self._add_dados_item_ferragem(group="Dobradiças", tipo="DOBRADICAS", descricao="Dobradiça DB")
        self._add_dados_item_ferragem(group="Puxadores", tipo="PUXADOR", descricao="Puxador DB")
        self._add_dados_item_ferragem(
            group="Suportes Prateleira",
            tipo="SUPORTE PRATELEIRA",
            descricao="Suporte Prateleira DB",
        )
        self.session.flush()

        rows = self._gerar_real(_selecoes_duas_portas())
        self._materializar_resultados(rows, h=2400, l=900, p=550, lm=900, pm=550)
        listed = self._roundtrip_custeio(rows, dimensoes={"H": 2400, "L": 900, "P": 550})

        portas = [row for row in listed if str(row.get("def_peca") or "").startswith("PORTA ABRIR")]
        dobradicas = [row for row in listed if str(row.get("def_peca") or "").startswith("DOBRADICA")]
        self.assertEqual(len(portas), 2)
        self.assertEqual(len(dobradicas), 2)
        self.assertTrue(all(row.get("descricao") == "Porta Abrir DB" for row in portas))

    def test_catalogo_correr_roundtrip_preserva_componentes_de_sistema_no_reload(self) -> None:
        self._add_dados_item_sistema(
            group="Painel Porta Correr 1",
            tipo="Painel Porta Correr 1",
            descricao="Painel Correr DB",
        )
        self._add_dados_item_sistema(
            group="Calha Superior 2 SPP",
            tipo="Calha Superior 2 SPP",
            descricao="Calha Superior DB",
            und="ML",
        )
        self._add_dados_item_sistema(
            group="Calha Inferior 2 SPP",
            tipo="Calha Inferior 2 SPP",
            descricao="Calha Inferior DB",
            und="ML",
        )
        self._add_dados_item_sistema(
            group="Acessorio 7 SPP",
            tipo="Acessorio 7 SPP",
            descricao="Acessorio 7 DB",
        )
        self._add_dados_item_sistema(
            group="Acessorio 8 SPP",
            tipo="Acessorio 8 SPP",
            descricao="Acessorio 8 DB",
        )
        self.session.flush()

        rows = self._gerar_real(_selecoes_correr())
        self._materializar_resultados(rows, h=2400, l=1800, p=650, lm=1800, pm=650)
        listed = self._roundtrip_custeio(rows, dimensoes={"H": 2400, "L": 1800, "P": 650})

        paineis = [row for row in listed if str(row.get("def_peca") or "").startswith("PAINEL CORRER")]
        calhas = [row for row in listed if "CALHA" in str(row.get("def_peca") or "")]
        self.assertEqual(len(paineis), 2)
        self.assertEqual(len(calhas), 2)
        self.assertTrue(all(row.get("familia") == "SISTEMAS CORRER" for row in paineis + calhas))


if __name__ == "__main__":
    unittest.main()
