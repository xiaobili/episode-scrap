import json

from sqlmodel import Session, select

from app.config import settings
from app.models import Setting

_ALLOWED_KEYS = {
    "rename_template",
    "allowed_paths",
    "tmdb_api_key",
    "openlist_concurrency",
    "openlist_timeout",
    "openlist_retry",
    "strm_url_template",
    "strm_output_mode",
    "strm_target_dir",
    "strm_rules",
    "jellyfin_url",
    "jellyfin_api_key",
}


def get_value(session: Session, key: str) -> str | None:
    row = session.get(Setting, key)
    return row.value if row else None


def set_value(session: Session, key: str, value: str) -> None:
    if key not in _ALLOWED_KEYS:
        raise ValueError(f"未知配置项：{key}")
    row = session.get(Setting, key)
    if row:
        row.value = value
    else:
        row = Setting(key=key, value=value)
    session.add(row)


def get_rename_template(session: Session) -> str:
    return get_value(session, "rename_template") or settings.rename_template


def get_allowed_paths(session: Session) -> list[str]:
    raw = get_value(session, "allowed_paths")
    if raw is None:
        return settings.allowed_path_list
    return [p.strip() for p in raw.split(";") if p.strip()]


def get_openlist_options(session: Session) -> dict[str, int]:
    def _int(key: str, fallback: int) -> int:
        raw = get_value(session, key)
        try:
            return int(raw) if raw is not None else fallback
        except ValueError:
            return fallback

    return {
        "concurrency": _int("openlist_concurrency", settings.openlist_concurrency),
        "timeout": _int("openlist_timeout", settings.openlist_timeout),
        "retry": _int("openlist_retry", settings.openlist_retry),
    }


STRM_MODES = ("alongside", "library", "mirror")


def get_strm_rules(session: Session) -> list[dict]:
    raw = get_value(session, "strm_rules")
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        return []
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


def get_strm_options(session: Session) -> dict:
    mode = get_value(session, "strm_output_mode") or settings.strm_output_mode
    if mode not in STRM_MODES:
        mode = "alongside"
    return {
        "template": get_value(session, "strm_url_template")
        or settings.strm_url_template,
        "mode": mode,
        "target_dir": get_value(session, "strm_target_dir")
        or settings.strm_target_dir,
        "rules": get_strm_rules(session),
    }


def get_tmdb_key(session: Session) -> str:
    from app.services.crypto import decrypt

    encrypted = get_value(session, "tmdb_api_key")
    if encrypted:
        return decrypt(encrypted)
    return settings.tmdb_api_key


def has_tmdb_key(session: Session) -> bool:
    return bool(get_tmdb_key(session))


def get_jellyfin_url(session: Session) -> str:
    return get_value(session, "jellyfin_url") or settings.jellyfin_url


def get_jellyfin_key(session: Session) -> str:
    from app.services.crypto import decrypt

    encrypted = get_value(session, "jellyfin_api_key")
    if encrypted:
        return decrypt(encrypted)
    return settings.jellyfin_api_key


def has_jellyfin_key(session: Session) -> bool:
    return bool(get_jellyfin_key(session))
