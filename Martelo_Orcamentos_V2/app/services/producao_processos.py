from __future__ import annotations

import difflib
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence, Tuple

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy import String, cast, desc, or_, select

from Martelo_Orcamentos_V2.app.config import settings
from Martelo_Orcamentos_V2.app.models.client import Client
from Martelo_Orcamentos_V2.app.models.orcamento import Orcamento
from Martelo_Orcamentos_V2.app.models.producao import Producao
from Martelo_Orcamentos_V2.app.services.settings import get_setting

# Caminho base fornecido pelo utilizador
DEFAULT_BASE_PATH = r"\\SERVER_LE_Lanca_Encanto\LancaEncanto\Dep_Producao"
DEFAULT_PASTA_ENCOMENDA = "Encomenda de Cliente"
DEFAULT_PASTA_ENCOMENDA_FINAL = "Encomenda de Cliente Final"
KEY_PRODUCAO_BASE_PATH = "base_path_producao"

# IMOS IX / Imorder (base onde estão as pastas das obras IMOS)
DEFAULT_IMORDER_BASE_PATH = r"I:\Factory\Imorder"
KEY_IMORDER_BASE_PATH = "base_path_imorder_imos_ix"


# para testar Producao ->                   python -m Martelo_Orcamentos_V2.producao_processos 

@dataclass(frozen=True)
class PastaInfo:
    base: str
    ano_dir: str
    tipo_dir: str
    segments: Tuple[str, ...]

    @property
    def full_path(self) -> Path:
        path = Path(self.base) / self.ano_dir / self.tipo_dir
        for seg in self.segments:
            path = path / seg
        return path


def _two_digit(value: str | int | None) -> str:
    """Normaliza para 2 digitos (zero-fill)."""
    if value is None:
        return "01"
    text = str(value).strip()
    if text.isdigit():
        return f"{int(text):02d}"
    return text[:2] if len(text) >= 2 else text.zfill(2)


def _num_enc_norm(num_enc: str | int | None) -> str:
    """Normaliza numero de encomenda em 4 caracteres (PHC: 4 digitos | Cliente Final: _NNN)."""
    if num_enc is None:
        raise ValueError("Numero de encomenda PHC em falta.")
    text = str(num_enc).strip()
    if text.startswith("_"):
        m = re.fullmatch(r"_(\d{1,3})", text)
        if not m:
            raise ValueError("Numero de encomenda invalido.")
        return "_" + m.group(1).zfill(3)

    digits = re.sub(r"\D", "", text)
    if not digits:
        raise ValueError("Numero de encomenda PHC invalido.")
    if len(digits) < 4:
        digits = digits.zfill(4)
    return digits


def _ano_two_digits(ano: str | int | None) -> Tuple[str, str]:
    """
    Retorna (ano_completo, ano_2d). Aceita '2025' ou '25'.
    Se None, usa ano atual.
    """
    import datetime as _dt

    if ano is None:
        ano_completo = str(_dt.datetime.now().year)
    else:
        ano_completo = str(ano).strip()
    if len(ano_completo) == 2:
        ano_2d = ano_completo
    else:
        try:
            ano_int = int(ano_completo)
            ano_2d = f"{ano_int % 100:02d}"
        except Exception:
            ano_2d = ano_completo[-2:]
    return ano_completo, ano_2d


def gerar_codigo_processo(ano: str | int, num_enc_phc: str | int, versao_obra: str | int, versao_plano: str | int) -> str:
    """
    Gera codigo AA.NNNN_VV_PP (ex.: 25.0001_01_01).
    - AA: ultimos 2 digitos do ano
    - NNNN: encomenda PHC (4 digitos)
    - VV: versao da obra (2 digitos)
    - PP: versao do plano de corte (2 digitos)
    """
    _, ano_2d = _ano_two_digits(ano)
    enc = _num_enc_norm(num_enc_phc)
    ver_obra = _two_digit(versao_obra)
    ver_plano = _two_digit(versao_plano)
    return f"{ano_2d}.{enc}_{ver_obra}_{ver_plano}"


def _sanitize_nome_externo(text: str) -> str:
    safe = _sanitize_folder_name(text or "")
    safe = safe.replace(" ", "_")
    safe = re.sub(r"_+", "_", safe).strip("_")
    return safe or "cliente"


def gerar_nome_plano_cut_rite(
    ano: str | int,
    num_enc_phc: str | int,
    versao_obra: str | int,
    versao_plano: str | int,
    *,
    nome_cliente_simplex: Optional[str] = None,
    nome_cliente: Optional[str] = None,
    ref_cliente: Optional[str] = None,
) -> str:
    """
    Nome para ficheiro/plano CUT-RITE.
    Formato: NNNN_VV_PP_AA_CLIENTE (ex.: 1956_01_01_25_CICOMOL)
    """
    _, ano_2d = _ano_two_digits(ano)
    enc = _num_enc_norm(num_enc_phc)
    ver_obra = _two_digit(versao_obra)
    ver_plano = _two_digit(versao_plano)
    cli = _sanitize_nome_externo(nome_cliente_simplex or nome_cliente or ref_cliente or "cliente")
    return f"{enc}_{ver_obra}_{ver_plano}_{ano_2d}_{cli}"


def gerar_nome_enc_imos_ix(
    ano: str | int,
    num_enc_phc: str | int,
    versao: str | int,
    *,
    nome_cliente_simplex: Optional[str] = None,
    nome_cliente: Optional[str] = None,
    ref_cliente: Optional[str] = None,
) -> str:
    """
    Nome para encomenda IMOS IX.
    Formato: NNNN_VV_AA_CLIENTE (ex.: 1956_01_25_CICOMOL)
    """
    _, ano_2d = _ano_two_digits(ano)
    enc = _num_enc_norm(num_enc_phc)
    ver = _two_digit(versao)
    cli = _sanitize_nome_externo(nome_cliente_simplex or nome_cliente or ref_cliente or "cliente")
    return f"{enc}_{ver}_{ano_2d}_{cli}"


def listar_versoes_processo(session: Session, *, ano: str | int, num_enc_phc: str | int) -> set[tuple[str, str]]:
    """Lista pares (versao_obra, versao_plano) existentes para o mesmo ano+encomenda."""
    ano_full, _ = _ano_two_digits(ano)
    enc_norm = _num_enc_norm(num_enc_phc)
    rows = session.execute(
        select(Producao.versao_obra, Producao.versao_plano).where(
            Producao.ano == ano_full,
            Producao.num_enc_phc == enc_norm,
        )
    ).all()
    return {(str(v_obra or "").strip(), str(v_plano or "").strip()) for v_obra, v_plano in rows}


def _producao_root_dir(
    session: Session,
    *,
    ano: str | int,
    tipo_pasta: Optional[str],
    base_dir: str | Path | None = None,
) -> Path:
    ano_full, _ = _ano_two_digits(ano)
    resolved_base = _resolve_base_dir(session, base_dir)
    tipo_dir = _pasta_tipo_dir(tipo_pasta)
    return Path(resolved_base) / str(ano_full) / tipo_dir


_SEP_PATTERN = r"(?:_|-| )"


def listar_versoes_obra_em_pastas(
    session: Session,
    *,
    ano: str | int,
    num_enc_phc: str | int,
    tipo_pasta: Optional[str] = None,
    base_dir: str | Path | None = None,
) -> set[str]:
    """
    Lista versoes de obra (VV) existentes nas pastas do servidor para o mesmo ano+encomenda.
    Isto cobre casos onde as pastas existem (ex.: criadas por outros sistemas) mas ainda nao ha registo na BD.
    """
    enc = _num_enc_norm(num_enc_phc)
    root = _producao_root_dir(session, ano=ano, tipo_pasta=tipo_pasta, base_dir=base_dir)
    try:
        if not root.is_dir():
            return set()
    except Exception:
        return set()

    pat_vv = re.compile(rf"^{re.escape(enc)}{_SEP_PATTERN}(?P<vv>\d{{2}}){_SEP_PATTERN}", re.IGNORECASE)
    found: set[str] = set()

    try:
        for seg1 in root.iterdir():
            if not seg1.is_dir():
                continue
            if not _folder_name_matches_prefix(seg1.name, enc):
                continue
            try:
                for seg2 in seg1.iterdir():
                    if not seg2.is_dir():
                        continue
                    m = pat_vv.match(seg2.name)
                    if not m:
                        continue
                    found.add(_two_digit(m.group("vv")))
            except Exception:
                continue
    except Exception:
        return set()

    return found


def listar_versoes_plano_em_pastas(
    session: Session,
    *,
    ano: str | int,
    num_enc_phc: str | int,
    versao_obra: str | int,
    tipo_pasta: Optional[str] = None,
    base_dir: str | Path | None = None,
) -> set[str]:
    """
    Lista versoes de plano CUT-RITE (PP) existentes nas pastas do servidor dentro da versao de obra.
    """
    enc = _num_enc_norm(num_enc_phc)
    vv = _two_digit(versao_obra)
    root = _producao_root_dir(session, ano=ano, tipo_pasta=tipo_pasta, base_dir=base_dir)
    try:
        if not root.is_dir():
            return set()
    except Exception:
        return set()

    pat_vvpp = re.compile(
        rf"^{re.escape(enc)}{_SEP_PATTERN}{re.escape(vv)}{_SEP_PATTERN}(?P<pp>\d{{2}}){_SEP_PATTERN}",
        re.IGNORECASE,
    )
    found: set[str] = set()

    try:
        for seg1 in root.iterdir():
            if not seg1.is_dir():
                continue
            if not _folder_name_matches_prefix(seg1.name, enc):
                continue
            try:
                for seg2 in seg1.iterdir():
                    if not seg2.is_dir():
                        continue
                    if not _folder_name_matches_prefix(seg2.name, f"{enc}_{vv}"):
                        continue
                    try:
                        for seg3 in seg2.iterdir():
                            if not seg3.is_dir():
                                continue
                            m = pat_vvpp.match(seg3.name)
                            if not m:
                                continue
                            found.add(_two_digit(m.group("pp")))
                    except Exception:
                        continue
            except Exception:
                continue
    except Exception:
        return set()

    return found


def listar_pastas_enc_arvore(
    session: Session,
    *,
    ano: str | int,
    num_enc_phc: str | int,
    tipo_pasta: Optional[str] = None,
    base_dir: str | Path | None = None,
    max_nodes: int = 2000,
) -> tuple[str, dict[str, dict[str, list[str]]]]:
    """
    Devolve (root_path, arvore) das pastas existentes para uma encomenda.

    arvore: {seg1: {seg2: [seg3, ...]}}
    """
    enc = _num_enc_norm(num_enc_phc)
    root = _producao_root_dir(session, ano=ano, tipo_pasta=tipo_pasta, base_dir=base_dir)
    tree: dict[str, dict[str, list[str]]] = {}
    nodes = 0

    try:
        if not root.is_dir():
            return str(root), tree
    except Exception:
        return str(root), tree

    try:
        for seg1 in sorted((p for p in root.iterdir() if p.is_dir()), key=lambda p: p.name.casefold()):
            if nodes >= max_nodes:
                break
            if not _folder_name_matches_prefix(seg1.name, enc):
                continue
            nodes += 1
            tree.setdefault(seg1.name, {})
            try:
                seg2_dirs = sorted((p for p in seg1.iterdir() if p.is_dir()), key=lambda p: p.name.casefold())
            except Exception:
                continue
            for seg2 in seg2_dirs:
                if nodes >= max_nodes:
                    break
                nodes += 1
                tree[seg1.name].setdefault(seg2.name, [])
                try:
                    seg3_dirs = sorted((p for p in seg2.iterdir() if p.is_dir()), key=lambda p: p.name.casefold())
                except Exception:
                    continue
                for seg3 in seg3_dirs:
                    if nodes >= max_nodes:
                        break
                    nodes += 1
                    tree[seg1.name][seg2.name].append(seg3.name)
    except Exception:
        pass

    return str(root), tree


def sugerir_proxima_versao_obra(
    session: Session,
    *,
    ano: str | int,
    num_enc_phc: str | int,
    requested: str | int | None = None,
    tipo_pasta: Optional[str] = None,
    base_dir: str | Path | None = None,
) -> str:
    """Sugere a próxima versão de obra (VV) não usada para o mesmo ano+encomenda."""
    ano_full, _ = _ano_two_digits(ano)
    enc_norm = _num_enc_norm(num_enc_phc)
    existing = session.execute(
        select(Producao.versao_obra).where(
            Producao.ano == ano_full,
            Producao.num_enc_phc == enc_norm,
        )
    ).scalars().all()
    existing_set = {str(v or "").strip() for v in existing if str(v or "").strip()}
    try:
        existing_set |= set(
            listar_versoes_obra_em_pastas(
                session,
                ano=ano_full,
                num_enc_phc=enc_norm,
                tipo_pasta=tipo_pasta,
                base_dir=base_dir,
            )
        )
    except Exception:
        pass

    if requested is not None:
        req = _two_digit(requested)
        if req not in existing_set:
            return req

    parsed: list[int] = []
    for v in existing_set:
        try:
            parsed.append(int(v))
        except Exception:
            continue
    candidate = (max(parsed) + 1) if parsed else 1
    cand = _two_digit(candidate)
    while cand in existing_set:
        candidate += 1
        cand = _two_digit(candidate)
    return cand


def sugerir_proxima_versao_plano(
    session: Session,
    *,
    ano: str | int,
    num_enc_phc: str | int,
    versao_obra: str | int,
    requested: str | int | None = None,
    tipo_pasta: Optional[str] = None,
    base_dir: str | Path | None = None,
) -> str:
    """Sugere a próxima versão de plano CUT-RITE (PP) dentro da versão de obra."""
    ano_full, _ = _ano_two_digits(ano)
    enc_norm = _num_enc_norm(num_enc_phc)
    ver_obra = _two_digit(versao_obra)
    existing = session.execute(
        select(Producao.versao_plano).where(
            Producao.ano == ano_full,
            Producao.num_enc_phc == enc_norm,
            Producao.versao_obra == ver_obra,
        )
    ).scalars().all()
    existing_set = {str(v or "").strip() for v in existing if str(v or "").strip()}
    try:
        existing_set |= set(
            listar_versoes_plano_em_pastas(
                session,
                ano=ano_full,
                num_enc_phc=enc_norm,
                versao_obra=ver_obra,
                tipo_pasta=tipo_pasta,
                base_dir=base_dir,
            )
        )
    except Exception:
        pass

    if requested is not None:
        req = _two_digit(requested)
        if req not in existing_set:
            return req

    parsed: list[int] = []
    for v in existing_set:
        try:
            parsed.append(int(v))
        except Exception:
            continue
    candidate = (max(parsed) + 1) if parsed else 1
    cand = _two_digit(candidate)
    while cand in existing_set:
        candidate += 1
        cand = _two_digit(candidate)
    return cand


def _sanitize_folder_name(text: str) -> str:
    safe = re.sub(r"[\\\\/:*?\"<>|]", "_", text or "")
    return safe.strip() or "obra"


def _cliente_para_pasta(nome_simplex: Optional[str], nome_cliente: Optional[str], ref_cliente: Optional[str]) -> str:
    return _sanitize_folder_name(nome_simplex or nome_cliente or ref_cliente or "cliente")


def _pasta_tipo_dir(tipo: str | None) -> str:
    if not tipo:
        return DEFAULT_PASTA_ENCOMENDA
    tipo_norm = str(tipo).strip().lower()
    if "final" in tipo_norm:
        return DEFAULT_PASTA_ENCOMENDA_FINAL
    return DEFAULT_PASTA_ENCOMENDA


def _clean_base_path(text: str) -> str:
    cleaned = str(text or "").strip().strip('"').strip("'")
    cleaned = cleaned.replace("/", "\\").replace("\r", "").replace("\n", "")
    if not cleaned:
        return ""
    is_unc = cleaned.startswith("\\\\")
    rest = cleaned[2:] if is_unc else cleaned
    while "\\\\" in rest:
        rest = rest.replace("\\\\", "\\")
    cleaned = ("\\\\" + rest) if is_unc else rest
    cleaned = cleaned.rstrip(" .").strip()
    if not cleaned:
        return ""
    # Caracteres proibidos em paths Windows (":" é permitido apenas em "C:\..." / "C:")
    invalid = re.search(r'[<>\"|?*]', cleaned)
    if invalid:
        raise ValueError(f"Caminho base de producao invalido (caractere {invalid.group(0)}).")
    if ":" in cleaned:
        # Aceita drive-letter: "C:\" ou "C:"
        if not re.match(r"^[A-Za-z]:($|\\)", cleaned):
            raise ValueError("Caminho base de producao invalido (caractere :).")
    return cleaned


def _resolve_base_dir(session: Session, base_dir: str | Path | None) -> str:
    """
    Decide o caminho base para producao, respeitando override do utilizador.
    Limpa aspas e barras sobrantes para evitar paths invalidos.
    """
    candidates = []
    if base_dir:
        candidates.append(str(base_dir))
    try:
        cfg_value = get_setting(session, KEY_PRODUCAO_BASE_PATH, None)
        if cfg_value:
            candidates.append(cfg_value)
    except Exception:
        pass
    candidates.append(getattr(settings, "PRODUCAO_BASE_PATH", "") or DEFAULT_BASE_PATH)
    for path_text in candidates:
        cleaned = _clean_base_path(path_text)
        if cleaned:
            return cleaned
    return DEFAULT_BASE_PATH


def build_pasta_info(
    *,
    base_dir: str | Path | None,
    ano: str | int,
    tipo_pasta: str | None,
    segments: Tuple[str, ...],
) -> PastaInfo:
    base = str(base_dir or getattr(settings, "PRODUCAO_BASE_PATH", "") or DEFAULT_BASE_PATH)
    ano_dir = str(ano)
    return PastaInfo(
        base=base,
        ano_dir=ano_dir,
        tipo_dir=_pasta_tipo_dir(tipo_pasta),
        segments=tuple(_sanitize_folder_name(seg) for seg in segments),
    )


def criar_pasta_servidor(info: PastaInfo, *, exist_ok: bool = True) -> Path:
    path = info.full_path
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.mkdir(parents=True, exist_ok=exist_ok)
    except OSError as exc:
        raise OSError(f"Falha ao criar pasta: {path} ({exc})") from exc
    return path


def _montar_pasta_nome(
    codigo_processo: str, nome_cliente: Optional[str], ref_cliente: Optional[str], nome_simplex: Optional[str] = None
) -> str:
    # prioridade: simplex > nome > ref cliente
    if nome_simplex:
        return f"{codigo_processo}_{_sanitize_folder_name(nome_simplex)}"
    if nome_cliente:
        return f"{codigo_processo}_{_sanitize_folder_name(nome_cliente)}"
    if ref_cliente:
        return f"{codigo_processo}_{_sanitize_folder_name(ref_cliente)}"
    return codigo_processo


def _montar_codigo_processo_com_cliente(
    codigo_processo: str, nome_cliente: Optional[str], ref_cliente: Optional[str], nome_simplex: Optional[str] = None
) -> str:
    return _montar_pasta_nome(codigo_processo, nome_cliente, ref_cliente, nome_simplex)


def _montar_segmentos_pasta(
    num_enc_phc: str | int,
    versao_obra: str | int,
    versao_plano: str | int,
    nome_simplex: Optional[str],
    nome_cliente: Optional[str],
    ref_cliente: Optional[str],
) -> Tuple[str, str, str]:
    enc = _num_enc_norm(num_enc_phc)
    ver_obra = _two_digit(versao_obra)
    ver_plano = _two_digit(versao_plano)
    cli = _cliente_para_pasta(nome_simplex, nome_cliente, ref_cliente)
    seg1 = f"{enc}_{cli}"
    seg2 = f"{enc}_{ver_obra}_{cli}"
    seg3 = f"{enc}_{ver_obra}_{ver_plano}_{cli}"
    return seg1, seg2, seg3


def _mapear_campos_orcamento(orc: Orcamento, cliente: Optional[Client]) -> dict:
    return {
        "ano": orc.ano,
        "num_orcamento": orc.num_orcamento,
        "versao_orc": orc.versao,
        "client_id": getattr(orc, "client_id", None),
        "nome_cliente": getattr(cliente, "nome", None),
        "nome_cliente_simplex": getattr(cliente, "nome_simplex", None),
        "num_cliente_phc": getattr(cliente, "num_cliente_phc", None),
        "ref_cliente": orc.ref_cliente,
        "obra": orc.obra,
        "localizacao": orc.localizacao,
        "descricao_orcamento": orc.descricao_orcamento,
        "data_entrega": orc.data,
        "data_inicio": None,
        "preco_total": orc.preco_total,
        "qt_artigos": None,
        "descricao_artigos": None,
        "materias_usados": None,
        "descricao_producao": None,
        "notas1": orc.info_1 or orc.notas,
        "notas2": orc.info_2,
    }


def criar_processo(
    session: Session,
    *,
    ano: str | int,
    num_enc_phc: str | int,
    versao_obra: str | int = "01",
    versao_plano: str | int = "01",
    responsavel: Optional[str] = None,
    estado: Optional[str] = "Planeamento",
    tipo_pasta: Optional[str] = None,
    criar_pasta: bool = False,
    base_dir: str | Path | None = None,
    pasta_nome_custom: Optional[str] = None,
    current_user_id: Optional[int] = None,
    **campos_extra,
) -> Producao:
    """
    Cria um processo (livre ou ja mapeado) e opcionalmente cria a pasta.
    """
    codigo_base = gerar_codigo_processo(ano, num_enc_phc, versao_obra, versao_plano)
    codigo = _montar_codigo_processo_com_cliente(codigo_base, campos_extra.get("nome_cliente"), campos_extra.get("ref_cliente"), campos_extra.get("nome_cliente_simplex"))
    ano_full, _ = _ano_two_digits(ano)

    processo = Producao(
        codigo_processo=codigo,
        ano=ano_full,
        num_enc_phc=_num_enc_norm(num_enc_phc),
        versao_obra=_two_digit(versao_obra),
        versao_plano=_two_digit(versao_plano),
        responsavel=responsavel,
        estado=estado,
        created_by=current_user_id,
        updated_by=current_user_id,
        **campos_extra,
    )
    processo.tipo_pasta = _pasta_tipo_dir(tipo_pasta)

    session.add(processo)
    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise ValueError(f"Codigo de processo duplicado ou chave ja existente: {exc}") from exc

    if criar_pasta:
        criar_pasta_para_processo(
            session,
            int(processo.id),
            base_dir=base_dir,
            tipo_pasta=tipo_pasta,
            pasta_nome_custom=pasta_nome_custom,
        )

    return processo


def criar_de_orcamento(
    session: Session,
    *,
    orcamento_id: int,
    versao_plano: str | int = "01",
    tipo_pasta: Optional[str] = None,
    criar_pasta: bool = False,
    base_dir: str | Path | None = None,
    pasta_nome_custom: Optional[str] = None,
    responsavel: Optional[str] = None,
    estado: Optional[str] = "Planeamento",
    current_user_id: Optional[int] = None,
) -> Producao:
    """
    Converte um orcamento existente num processo de producao.
    """
    orc = session.get(Orcamento, orcamento_id)
    if orc is None:
        raise ValueError(f"Orcamento {orcamento_id} nao encontrado.")

    cliente = None
    if getattr(orc, "client_id", None):
        cliente = session.get(Client, orc.client_id)

    if not orc.enc_phc:
        raise ValueError("Orcamento nao tem numero de encomenda PHC (enc_phc) preenchido.")

    ano_full, _ = _ano_two_digits(orc.ano)
    enc_norm = _num_enc_norm(orc.enc_phc)
    ver_obra = _two_digit(orc.versao)
    ver_plano_req = _two_digit(versao_plano)

    # Evitar duplicados de codigo_processo: se ja existir, incrementa versao_plano automaticamente
    existing_plans = session.execute(
        select(Producao.versao_plano).where(
            Producao.ano == ano_full,
            Producao.num_enc_phc == enc_norm,
            Producao.versao_obra == ver_obra,
        )
    ).scalars().all()

    def _next_plano(existing: list[str], requested: str) -> str:
        parsed = []
        for v in existing:
            try:
                parsed.append(int(str(v).strip()))
            except Exception:
                continue
        try:
            req_int = int(requested)
        except Exception:
            req_int = None
        if req_int is not None and req_int not in parsed:
            return _two_digit(req_int)
        if parsed:
            return _two_digit(max(parsed) + 1)
        return _two_digit(req_int or 1)

    versao_plano_final = _next_plano(existing_plans, ver_plano_req)

    dados = _mapear_campos_orcamento(orc, cliente)
    dados.update(
        {
            "orcamento_id": orc.id,
            "versao_obra": orc.versao,
            "versao_plano": versao_plano_final,
            "responsavel": responsavel or getattr(cliente, "responsavel", None),
            "estado": estado,
        }
    )
    for key in ("ano", "versao_obra", "versao_plano", "num_enc_phc"):
        dados.pop(key, None)

    return criar_processo(
        session,
        ano=ano_full,
        num_enc_phc=enc_norm,
        versao_obra=ver_obra,
        versao_plano=versao_plano_final,
        tipo_pasta=tipo_pasta,
        criar_pasta=criar_pasta,
        base_dir=base_dir,
        pasta_nome_custom=pasta_nome_custom,
        current_user_id=current_user_id,
        **dados,
    )


# -----------------------
# CRUD / LISTAGEM BASICA
# -----------------------


_SEARCH_FIELDS_PRODUCAO = (
    # ids/chaves (cast para string)
    cast(Producao.id, String),
    cast(Producao.orcamento_id, String),
    cast(Producao.client_id, String),
    # campos curtos
    Producao.codigo_processo,
    Producao.ano,
    Producao.num_enc_phc,
    Producao.versao_obra,
    Producao.versao_plano,
    Producao.responsavel,
    Producao.estado,
    Producao.nome_cliente,
    Producao.nome_cliente_simplex,
    Producao.num_cliente_phc,
    Producao.ref_cliente,
    Producao.num_orcamento,
    Producao.versao_orc,
    Producao.obra,
    Producao.localizacao,
    Producao.data_entrega,
    Producao.data_inicio,
    # numéricos (cast para string)
    cast(Producao.preco_total, String),
    cast(Producao.qt_artigos, String),
    # campos longos (textos livres)
    Producao.descricao_orcamento,
    Producao.descricao_artigos,
    Producao.materias_usados,
    Producao.descricao_producao,
    Producao.notas1,
    Producao.notas2,
    Producao.notas3,
    # paths / meta
    Producao.imagem_path,
    Producao.pasta_servidor,
    Producao.tipo_pasta,
)


def _normalize_txt(val: str) -> str:
    """
    Normaliza texto para pesquisa:
    - casefold
    - remove acentos
    - remove pontuação (substitui por espaço)
    """
    raw = str(val or "").strip()
    if not raw:
        return ""
    txt = unicodedata.normalize("NFKD", raw)
    txt = "".join(ch for ch in txt if not unicodedata.combining(ch))
    txt = txt.casefold()
    txt = re.sub(r"[^0-9a-z]+", " ", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt


def _uniq_terms(terms: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for t in terms:
        token = (t or "").strip()
        if not token:
            continue
        key = token.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(token)
    return out


def _split_terms_raw(query: str) -> list[str]:
    if not (query or "").strip():
        return []
    cleaned = str(query).replace("%", " ").strip()
    parts = [p.strip() for p in cleaned.split() if p.strip()]
    # apenas limpa pontuação nas extremidades (mantém códigos tipo "25.0001_01_01")
    terms: list[str] = []
    for p in parts:
        t = p.strip(".,;:!?'\"()[]{}<>")
        if t:
            terms.append(t)
    return _uniq_terms(terms)


def _split_terms_normalized(query: str) -> list[str]:
    norm = _normalize_txt(query or "")
    if not norm:
        return []
    return _uniq_terms(norm.split())


def _build_search_filters(terms: Sequence[str]):
    filters = []
    for t in terms:
        like = f"%{t}%"
        filters.append(or_(*[f.ilike(like) for f in _SEARCH_FIELDS_PRODUCAO]))
    return filters


def _producao_blob(proc: Producao) -> str:
    parts = []
    for attr in (
        "id",
        "codigo_processo",
        "ano",
        "num_enc_phc",
        "versao_obra",
        "versao_plano",
        "orcamento_id",
        "client_id",
        "responsavel",
        "estado",
        "nome_cliente",
        "nome_cliente_simplex",
        "num_cliente_phc",
        "ref_cliente",
        "num_orcamento",
        "versao_orc",
        "obra",
        "localizacao",
        "descricao_orcamento",
        "data_entrega",
        "data_inicio",
        "preco_total",
        "qt_artigos",
        "descricao_artigos",
        "materias_usados",
        "descricao_producao",
        "notas1",
        "notas2",
        "notas3",
        "imagem_path",
        "pasta_servidor",
        "tipo_pasta",
    ):
        try:
            val = getattr(proc, attr, None)
        except Exception:
            val = None
        if val in (None, ""):
            continue
        parts.append(str(val))
    return " | ".join(parts)


def _fuzzy_match_blob(blob_norm: str, *, terms_norm: Sequence[str]) -> Optional[float]:
    """
    Match por aproximação:
    - cada termo tem de existir no blob normalizado OU ter close-match em alguma palavra
    - retorna score (maior = melhor) ou None se não corresponder
    """
    if not terms_norm:
        return 0.0
    if not blob_norm:
        return None
    words = set(blob_norm.split())
    score = 0.0
    for t in terms_norm:
        if t in blob_norm:
            score += 1.0
            continue
        if len(t) < 4:
            return None
        close = difflib.get_close_matches(t, words, n=1, cutoff=0.82)
        if not close:
            return None
        score += difflib.SequenceMatcher(None, t, close[0]).ratio()
    return score


def listar_processos(
    session: Session,
    *,
    search: Optional[str] = None,
    estado: Optional[str] = None,
    cliente: Optional[str] = None,
    responsavel: Optional[str] = None,
    limit: int = 200,
    approx: bool = True,
):
    """
    Lista processos de producao ordenados por id desc, com filtro opcional.

    Pesquisa:
    - procura em todos os campos relevantes do modelo `Producao` (inclui descrições/notas)
    - suporta multi-termos separados por '%' ou espaço
    - ignora pontuação no fallback (normalização) e tenta aproximação se não houver resultados
    """
    base = select(Producao).order_by(desc(Producao.id))
    if estado:
        base = base.where(Producao.estado == estado)
    if cliente:
        term_cli = f"%{cliente}%"
        base = base.where(Producao.nome_cliente.ilike(term_cli))
    if responsavel:
        term_resp = f"%{responsavel}%"
        base = base.where(Producao.responsavel.ilike(term_resp))

    if not (search or "").strip():
        stmt = base.limit(limit) if limit else base
        return session.execute(stmt).scalars().all()

    raw_terms = _split_terms_raw(search or "")
    norm_terms = _split_terms_normalized(search or "")

    def _run_sql(terms: Sequence[str]) -> list[Producao]:
        if not terms:
            return []
        stmt = base.where(*_build_search_filters(terms))
        if limit:
            stmt = stmt.limit(limit)
        return session.execute(stmt).scalars().all()

    # 1) tentativa "precisa" (mantém pontuação interna para códigos)
    if raw_terms:
        rows = _run_sql(raw_terms)
        if rows:
            return rows

    # 2) tentativa normalizada (ignora pontuação e separa em tokens)
    if norm_terms and norm_terms != raw_terms:
        rows = _run_sql(norm_terms)
        if rows:
            return rows

    if not approx:
        return []

    # 3) fallback por aproximação sobre candidatos (normalização + difflib)
    try:
        candidate_limit = int(limit or 0)
    except Exception:
        candidate_limit = 0
    candidate_limit = max(candidate_limit, 2000)
    candidate_limit = min(candidate_limit, 5000)

    cand_stmt = base.limit(candidate_limit) if candidate_limit else base
    candidates = session.execute(cand_stmt).scalars().all()
    if not candidates:
        return []

    if not norm_terms:
        norm_terms = _split_terms_normalized(" ".join(raw_terms))

    scored: list[tuple[float, Producao]] = []
    for proc in candidates:
        blob_norm = _normalize_txt(_producao_blob(proc))
        score = _fuzzy_match_blob(blob_norm, terms_norm=norm_terms)
        if score is None:
            continue
        scored.append((float(score), proc))

    scored.sort(key=lambda x: (x[0], int(getattr(x[1], "id", 0) or 0)), reverse=True)
    if limit:
        scored = scored[: int(limit)]
    return [p for _, p in scored]


def obter_processo(session: Session, proc_id: int) -> Optional[Producao]:
    return session.get(Producao, proc_id)


def atualizar_processo(session: Session, proc_id: int, data: dict, *, current_user_id: Optional[int] = None) -> Producao:
    proc = session.get(Producao, proc_id)
    if proc is None:
        raise ValueError("Processo nao encontrado.")

    allowed = {
        "responsavel",
        "estado",
        "nome_cliente",
        "nome_cliente_simplex",
        "num_cliente_phc",
        "ref_cliente",
        "num_orcamento",
        "versao_orc",
        "obra",
        "localizacao",
        "descricao_orcamento",
        "data_entrega",
        "data_inicio",
        "preco_total",
        "qt_artigos",
        "descricao_artigos",
        "materias_usados",
        "descricao_producao",
        "notas1",
        "notas2",
        "notas3",
        "imagem_path",
        "pasta_servidor",
        "tipo_pasta",
        "ano",
        "num_enc_phc",
        "versao_obra",
        "versao_plano",
    }
    for key, value in data.items():
        if key in allowed:
            setattr(proc, key, value)
    if current_user_id is not None:
        proc.updated_by = current_user_id
    session.add(proc)
    session.flush()
    return proc


def eliminar_processo(session: Session, proc_id: int) -> None:
    proc = session.get(Producao, proc_id)
    if proc is None:
        return
    session.delete(proc)
    session.flush()


# -----------------------
# PASTAS
# -----------------------


_FOLDER_PREFIX_SEPARATORS = ("_", "-", " ")


def _folder_name_matches_prefix(name: str, prefix: str) -> bool:
    """
    Verifica se `name` corresponde ao `prefix`:
    - igual ao prefix, OU
    - começa por prefix e o próximo char é um separador (ex.: '_' ou ' ').
    """
    name_text = str(name or "")
    prefix_text = str(prefix or "")
    if not name_text or not prefix_text:
        return False
    if not name_text.startswith(prefix_text):
        return False
    if len(name_text) == len(prefix_text):
        return True
    return name_text[len(prefix_text)] in _FOLDER_PREFIX_SEPARATORS


def _prefix_chain_depth(root: Path, prefixes: Sequence[str]) -> int:
    """
    Mede quantos níveis consecutivos de `prefixes` existem a partir de `root`,
    considerando diretórios cujo nome "casa" por prefix (ignora sufixos como o cliente).
    """
    if not prefixes:
        return 0

    candidates = [root]
    depth = 0
    for pref in prefixes:
        next_candidates: list[Path] = []
        for parent in candidates:
            try:
                for child in parent.iterdir():
                    if child.is_dir() and _folder_name_matches_prefix(child.name, pref):
                        next_candidates.append(child)
            except Exception:
                continue
        if not next_candidates:
            break
        depth += 1
        candidates = next_candidates
    return depth


def _name_endswith_suffix(name: str, suffix: str) -> bool:
    if not (name or "").strip() or not (suffix or "").strip():
        return False
    n = str(name).casefold()
    s = str(suffix).casefold()
    if n == s:
        return True
    return any(n.endswith(f"{sep}{s}") for sep in _FOLDER_PREFIX_SEPARATORS)


def _find_best_dir_match(
    parent: Path,
    *,
    prefix: str,
    preferred_name: Optional[str] = None,
    preferred_suffix: Optional[str] = None,
    chain_prefixes: Sequence[str] = (),
) -> Optional[Path]:
    """
    Procura o melhor diretório filho dentro de `parent`:
    - dá prioridade a `preferred_name` se existir
    - senão, procura por `prefix` (ignorando sufixos como o cliente) e escolhe:
        - maior profundidade da cadeia `chain_prefixes` (ex.: VV -> PP)
        - sufixo preferido (cliente atual) para desempate
        - ordem alfabética para determinismo
    """
    try:
        if not parent.is_dir():
            return None
    except Exception:
        return None

    matches: list[Path] = []
    try:
        for child in parent.iterdir():
            if not child.is_dir():
                continue
            if _folder_name_matches_prefix(child.name, prefix):
                matches.append(child)
    except Exception:
        # fallback: se existir um nome preferido, tenta usar mesmo sem conseguir listar
        try:
            if preferred_name:
                candidate = parent / preferred_name
                if candidate.is_dir():
                    return candidate
        except Exception:
            pass
        return None

    if not matches:
        return None
    if len(matches) == 1:
        return matches[0]

    def _dir_has_entries(path: Path) -> bool:
        try:
            next(path.iterdir())
            return True
        except StopIteration:
            return False
        except Exception:
            return False

    preferred_name_cf = preferred_name.casefold() if preferred_name else None
    scored: list[tuple[int, str, Path]] = []
    for cand in matches:
        score = 0
        if preferred_name_cf and cand.name.casefold() == preferred_name_cf:
            score += 8
        if chain_prefixes:
            score += _prefix_chain_depth(cand, chain_prefixes) * 20
        if preferred_suffix and _name_endswith_suffix(cand.name, preferred_suffix):
            score += 5
        # em pastas finais (sem chain), um diretório já com conteúdo costuma ser o "certo"
        if not chain_prefixes and _dir_has_entries(cand):
            score += 15
        scored.append((score, cand.name.casefold(), cand))

    scored.sort(key=lambda t: (t[0], t[1]), reverse=True)
    return scored[0][2]


def resolver_pasta_para_processo(
    session: Session,
    proc_id: int,
    *,
    base_dir: str | Path | None = None,
    tipo_pasta: Optional[str] = None,
    pasta_nome_custom: Optional[str] = None,
    create: bool = False,
) -> Path:
    """
    Resolve (e opcionalmente cria) a Pasta Servidor para um processo.

    Importante: a lógica de procura ignora o sufixo do cliente no nome das pastas.
    Assim, se o Cliente Simplex mudar no PHC, o programa continua a encontrar a
    pasta existente sem criar duplicados.
    """
    proc = session.get(Producao, proc_id)
    if proc is None:
        raise ValueError("Processo nao encontrado.")
    if not proc.codigo_processo:
        raise ValueError("Processo sem codigo_processo gerado.")

    resolved_base = _resolve_base_dir(session, base_dir)
    tipo_dir = _pasta_tipo_dir(tipo_pasta or proc.tipo_pasta)

    ano_dir = str(proc.ano or "").strip()
    if not ano_dir:
        raise ValueError("Processo sem ano definido.")

    root = Path(resolved_base) / ano_dir / tipo_dir
    if create:
        try:
            root.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise OSError(f"Falha ao criar pasta: {root} ({exc})") from exc
    else:
        try:
            if not root.is_dir():
                raise ValueError("Pasta base de producao nao encontrada (ano/tipo).")
        except ValueError:
            raise
        except Exception:
            raise ValueError("Pasta base de producao nao encontrada (ano/tipo).")

    enc = _num_enc_norm(proc.num_enc_phc)
    ver_obra = _two_digit(proc.versao_obra)
    ver_plano = _two_digit(proc.versao_plano)
    cli = _cliente_para_pasta(proc.nome_cliente_simplex, proc.nome_cliente, proc.ref_cliente)

    pref1 = enc
    pref2 = f"{enc}_{ver_obra}"
    pref3 = f"{enc}_{ver_obra}_{ver_plano}"

    seg1_desired = _sanitize_folder_name(f"{enc}_{cli}")
    seg2_desired = _sanitize_folder_name(f"{enc}_{ver_obra}_{cli}")
    if pasta_nome_custom:
        seg3_desired = _sanitize_folder_name(pasta_nome_custom)
        seg3_prefix: Optional[str] = None
    else:
        seg3_desired = _sanitize_folder_name(f"{enc}_{ver_obra}_{ver_plano}_{cli}")
        seg3_prefix = pref3

    # Nível 1: ENC_Cliente (cliente é só "visual")
    seg1_dir = _find_best_dir_match(
        root,
        prefix=pref1,
        preferred_name=seg1_desired,
        preferred_suffix=cli,
        chain_prefixes=(pref2, pref3) if seg3_prefix else (pref2,),
    )
    if seg1_dir is None:
        if not create:
            raise ValueError("Pasta nao encontrada. Use 'Criar Pasta' para gerar a pasta da obra no servidor.")
        seg1_dir = root / seg1_desired
        seg1_dir.mkdir(parents=True, exist_ok=True)

    # Nível 2: ENC_VV_Cliente (cliente é só "visual")
    seg2_dir = _find_best_dir_match(
        seg1_dir,
        prefix=pref2,
        preferred_name=seg2_desired,
        preferred_suffix=cli,
        chain_prefixes=(pref3,) if seg3_prefix else (),
    )
    if seg2_dir is None:
        if not create:
            raise ValueError("Pasta nao encontrada. Use 'Criar Pasta' para gerar a pasta da obra no servidor.")
        seg2_dir = seg1_dir / seg2_desired
        seg2_dir.mkdir(parents=True, exist_ok=True)

    # Nível 3: ENC_VV_PP_Cliente (ou custom)
    if seg3_prefix:
        seg3_dir = _find_best_dir_match(
            seg2_dir,
            prefix=seg3_prefix,
            preferred_name=seg3_desired,
            preferred_suffix=cli,
            chain_prefixes=(),
        )
        if seg3_dir is None:
            if not create:
                raise ValueError("Pasta nao encontrada. Use 'Criar Pasta' para gerar a pasta da obra no servidor.")
            seg3_dir = seg2_dir / seg3_desired
            seg3_dir.mkdir(parents=True, exist_ok=True)
    else:
        seg3_dir = seg2_dir / seg3_desired
        if not seg3_dir.is_dir():
            if not create:
                raise ValueError("Pasta nao encontrada. Use 'Criar Pasta' para gerar a pasta da obra no servidor.")
            seg3_dir.mkdir(parents=True, exist_ok=True)

    proc.pasta_servidor = str(seg3_dir)
    proc.tipo_pasta = tipo_dir
    session.add(proc)
    session.flush()
    return seg3_dir


def criar_pasta_para_processo(
    session: Session,
    proc_id: int,
    *,
    base_dir: str | Path | None = None,
    tipo_pasta: Optional[str] = None,
    pasta_nome_custom: Optional[str] = None,
) -> Path:
    return resolver_pasta_para_processo(
        session,
        proc_id,
        base_dir=base_dir,
        tipo_pasta=tipo_pasta,
        pasta_nome_custom=pasta_nome_custom,
        create=True,
    )


def _abrir_pasta_path(path: Path) -> None:
    try:
        import subprocess
        import platform

        if platform.system() == "Windows":
            subprocess.Popen(["explorer", str(path)])
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except Exception as exc:
        raise RuntimeError(f"Falha ao abrir pasta: {exc}") from exc


def abrir_pasta_para_processo(
    session: Session,
    proc_id: int,
    *,
    base_dir: str | Path | None = None,
    tipo_pasta: Optional[str] = None,
    pasta_nome_custom: Optional[str] = None,
) -> Path:
    """
    Abre a Pasta Servidor do processo. Se o path guardado estiver desatualizado,
    tenta resolver novamente (ignorando sufixo do cliente) e atualiza o registo.
    """
    proc = session.get(Producao, proc_id)
    if proc is None:
        raise ValueError("Processo nao encontrado.")

    if proc.pasta_servidor:
        try:
            current = Path(proc.pasta_servidor)
            if current.is_dir():
                _abrir_pasta_path(current)
                return current
        except Exception:
            pass

    path = resolver_pasta_para_processo(
        session,
        proc_id,
        base_dir=base_dir,
        tipo_pasta=tipo_pasta,
        pasta_nome_custom=pasta_nome_custom,
        create=False,
    )
    _abrir_pasta_path(path)
    return path


def abrir_pasta(proc: Producao) -> None:
    """
    Compat: abre apenas o path já guardado no processo.
    Preferir `abrir_pasta_para_processo()` (resolve e atualiza automaticamente).
    """
    if not proc or not proc.pasta_servidor:
        raise ValueError("Processo sem pasta associada.")
    path = Path(proc.pasta_servidor)
    if not path.exists():
        raise ValueError("Pasta nao encontrada.")
    _abrir_pasta_path(path)
