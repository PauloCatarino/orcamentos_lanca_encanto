from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ProducaoFormState:
    codigo_display: str
    ano: str
    num_enc_phc: str
    versao_obra: str
    versao_plano: str
    responsavel: str
    estado: str
    nome_cliente: str
    nome_cliente_simplex: str
    num_cliente_phc: str
    ref_cliente: str
    num_orcamento: str
    versao_orc: str
    obra: str
    localizacao: str
    descricao_orcamento: str
    data_inicio: str | None
    data_entrega: str | None
    preco_total_text: str
    qt_artigos_text: str
    descricao_artigos: str
    descricao_producao: str
    materias_usados: str
    notas1: str
    notas2: str
    notas3: str
    pasta_servidor: str
    tipo_pasta: str
    imagem_path: str | None


def build_processo_codigo_display(proc) -> str:
    codigo = getattr(proc, "codigo_processo", None) or "-"
    suffix = getattr(proc, "nome_cliente_simplex", None) or getattr(proc, "nome_cliente", None) or getattr(proc, "ref_cliente", None)
    if codigo and codigo != "-" and suffix:
        safe_suffix = str(suffix).strip().replace(" ", "_")
        if str(codigo).endswith(f"_{safe_suffix}"):
            return codigo
        return f"{codigo}_{safe_suffix}"
    return codigo


def build_empty_form_state(*, current_year: str, default_tipo_pasta: str, default_estado: str = "") -> ProducaoFormState:
    return ProducaoFormState(
        codigo_display="-",
        ano=current_year,
        num_enc_phc="",
        versao_obra="01",
        versao_plano="01",
        responsavel="",
        estado=default_estado,
        nome_cliente="",
        nome_cliente_simplex="",
        num_cliente_phc="",
        ref_cliente="",
        num_orcamento="",
        versao_orc="",
        obra="",
        localizacao="",
        descricao_orcamento="",
        data_inicio=None,
        data_entrega=None,
        preco_total_text="",
        qt_artigos_text="",
        descricao_artigos="",
        descricao_producao="",
        materias_usados="",
        notas1="",
        notas2="",
        notas3="",
        pasta_servidor="",
        tipo_pasta=default_tipo_pasta,
        imagem_path=None,
    )


def build_form_state_from_processo(proc, *, default_tipo_pasta: str) -> ProducaoFormState:
    return ProducaoFormState(
        codigo_display=build_processo_codigo_display(proc),
        ano=str(getattr(proc, "ano", None) or ""),
        num_enc_phc=str(getattr(proc, "num_enc_phc", None) or ""),
        versao_obra=str(getattr(proc, "versao_obra", None) or "01"),
        versao_plano=str(getattr(proc, "versao_plano", None) or "01"),
        responsavel=str(getattr(proc, "responsavel", None) or "").strip(),
        estado=str(getattr(proc, "estado", None) or ""),
        nome_cliente=str(getattr(proc, "nome_cliente", None) or ""),
        nome_cliente_simplex=str(getattr(proc, "nome_cliente_simplex", None) or ""),
        num_cliente_phc=str(getattr(proc, "num_cliente_phc", None) or ""),
        ref_cliente=str(getattr(proc, "ref_cliente", None) or ""),
        num_orcamento=str(getattr(proc, "num_orcamento", None) or ""),
        versao_orc=str(getattr(proc, "versao_orc", None) or ""),
        obra=str(getattr(proc, "obra", None) or ""),
        localizacao=str(getattr(proc, "localizacao", None) or ""),
        descricao_orcamento=str(getattr(proc, "descricao_orcamento", None) or ""),
        data_inicio=getattr(proc, "data_inicio", None),
        data_entrega=getattr(proc, "data_entrega", None),
        preco_total_text="" if getattr(proc, "preco_total", None) in (None, "") else str(getattr(proc, "preco_total")),
        qt_artigos_text="" if getattr(proc, "qt_artigos", None) in (None, "") else str(getattr(proc, "qt_artigos")),
        descricao_artigos=str(getattr(proc, "descricao_artigos", None) or ""),
        descricao_producao=str(getattr(proc, "descricao_producao", None) or ""),
        materias_usados=str(getattr(proc, "materias_usados", None) or ""),
        notas1=str(getattr(proc, "notas1", None) or ""),
        notas2=str(getattr(proc, "notas2", None) or ""),
        notas3=str(getattr(proc, "notas3", None) or ""),
        pasta_servidor=str(getattr(proc, "pasta_servidor", None) or ""),
        tipo_pasta=str(getattr(proc, "tipo_pasta", None) or default_tipo_pasta),
        imagem_path=getattr(proc, "imagem_path", None),
    )


def build_processo_form_payload(
    *,
    ano: str,
    num_enc_phc: str,
    versao_obra: str,
    versao_plano: str,
    responsavel: str,
    estado: str,
    nome_cliente: str,
    nome_cliente_simplex: str,
    num_cliente_phc: str,
    ref_cliente: str,
    num_orcamento: str,
    versao_orc: str,
    obra: str,
    localizacao: str,
    data_inicio: str,
    data_entrega: str,
    preco_total,
    qt_artigos_text: str,
    descricao_artigos: str,
    materias_usados: str,
    descricao_producao: str,
    notas1: str,
    notas2: str,
    notas3: str,
    pasta_servidor: str,
    tipo_pasta: str,
    imagem_path: str | None,
) -> dict:
    qt_artigos_raw = str(qt_artigos_text or "").strip()
    return {
        "ano": str(ano or "").strip(),
        "num_enc_phc": str(num_enc_phc or "").strip(),
        "versao_obra": str(versao_obra or "").strip() or "01",
        "versao_plano": str(versao_plano or "").strip() or "01",
        "responsavel": str(responsavel or "").strip(),
        "estado": str(estado or "").strip(),
        "nome_cliente": str(nome_cliente or "").strip(),
        "nome_cliente_simplex": str(nome_cliente_simplex or "").strip(),
        "num_cliente_phc": str(num_cliente_phc or "").strip(),
        "ref_cliente": str(ref_cliente or "").strip(),
        "num_orcamento": str(num_orcamento or "").strip(),
        "versao_orc": str(versao_orc or "").strip(),
        "obra": str(obra or "").strip(),
        "localizacao": str(localizacao or "").strip(),
        "data_inicio": data_inicio,
        "data_entrega": data_entrega,
        "preco_total": preco_total,
        "qt_artigos": int(qt_artigos_raw) if qt_artigos_raw.isdigit() else None,
        "descricao_artigos": str(descricao_artigos or "").strip(),
        "materias_usados": str(materias_usados or "").strip(),
        "descricao_producao": str(descricao_producao or "").strip(),
        "notas1": str(notas1 or "").strip(),
        "notas2": str(notas2 or "").strip(),
        "notas3": str(notas3 or "").strip(),
        "pasta_servidor": str(pasta_servidor or "").strip(),
        "tipo_pasta": str(tipo_pasta or "").strip(),
        "imagem_path": imagem_path,
    }
