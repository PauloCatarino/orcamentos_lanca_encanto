from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from ..models.app_setting import AppSetting


def get_setting(db: Session, key: str, default: Optional[str] = None) -> Optional[str]:
    s = db.execute(select(AppSetting).where(AppSetting.key == key)).scalar_one_or_none()
    return s.value if s else default


def set_setting(db: Session, key: str, value: Optional[str]) -> None:
    s = db.execute(select(AppSetting).where(AppSetting.key == key)).scalar_one_or_none()
    if s:
        s.value = value
    else:
        s = AppSetting(key=key, value=value)
        db.add(s)
    db.flush()

