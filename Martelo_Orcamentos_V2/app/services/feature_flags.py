from typing import Dict, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from Martelo_Orcamentos_V2.app.models.user_feature_flag import UserFeatureFlag


FEATURE_PDF_MANAGER = "feature_pdf_manager"
FEATURE_PRODUCAO_PREPARACAO = "feature_producao_preparacao"
FEATURE_LISTA_MATERIAL_AUDIT = "feature_lista_material_audit"

_DEFAULT_FEATURE_STATES = {
    FEATURE_PDF_MANAGER: False,
    FEATURE_PRODUCAO_PREPARACAO: True,
    FEATURE_LISTA_MATERIAL_AUDIT: False,
}


def feature_default_enabled(feature_key: str) -> bool:
    return bool(_DEFAULT_FEATURE_STATES.get(str(feature_key or "").strip(), False))


def has_feature(db: Session, user_id: Optional[int], feature_key: str = FEATURE_PDF_MANAGER) -> bool:
    if not user_id:
        return feature_default_enabled(feature_key)
    row = db.execute(
        select(UserFeatureFlag.enabled).where(
            UserFeatureFlag.user_id == int(user_id),
            UserFeatureFlag.feature_key == feature_key,
        )
    ).scalar_one_or_none()
    if row is None:
        return feature_default_enabled(feature_key)
    return bool(row)


def list_feature_flags(db: Session, feature_key: str = FEATURE_PDF_MANAGER) -> Dict[int, bool]:
    rows = db.execute(
        select(UserFeatureFlag.user_id, UserFeatureFlag.enabled).where(UserFeatureFlag.feature_key == feature_key)
    ).all()
    return {int(user_id): bool(enabled) for user_id, enabled in rows if user_id is not None}


def set_feature(db: Session, user_id: int, feature_key: str, enabled: bool) -> None:
    row = db.execute(
        select(UserFeatureFlag).where(
            UserFeatureFlag.user_id == int(user_id),
            UserFeatureFlag.feature_key == feature_key,
        )
    ).scalar_one_or_none()
    if row is None:
        row = UserFeatureFlag(user_id=int(user_id), feature_key=feature_key, enabled=bool(enabled))
        db.add(row)
    else:
        row.enabled = bool(enabled)
