import os
import re
import string
from pathlib import Path

from app.models import MediaFile, ScrapeMatch

TEMPLATE_FIELDS = {
    "title",
    "year",
    "season",
    "episode",
    "episode_end",
    "episode_title",
    "resolution",
    "codec",
    "release_group",
}

_ILLEGAL = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_SEPARATOR = re.compile(r"(?:\s*[-–]\s*){2,}")


class TemplateError(ValueError):
    pass


def validate_template(template: str) -> None:
    try:
        parsed = list(string.Formatter().parse(template))
    except ValueError as exc:
        raise TemplateError(f"模板格式错误：{exc}") from exc
    for _literal, field_name, format_spec, _conversion in parsed:
        if field_name is None:
            continue
        if field_name not in TEMPLATE_FIELDS:
            allowed = "、".join(sorted(TEMPLATE_FIELDS))
            raise TemplateError(f"未知模板变量 {{{field_name}}}，可用变量：{allowed}")
        if format_spec and field_name not in {"season", "episode", "episode_end", "year"}:
            raise TemplateError(f"变量 {{{field_name}}} 不支持格式说明符")


def build_context(media: MediaFile, match: ScrapeMatch | None) -> dict:
    return {
        "title": (match.show_title if match else None) or media.parsed_title or "",
        "year": (match.show_year if match else None) or media.parsed_year or "",
        "season": media.parsed_season,
        "episode": media.parsed_episode,
        "episode_end": media.parsed_episode_end or "",
        "episode_title": (match.episode_title if match else None)
        or media.parsed_episode_title
        or "",
        "resolution": media.parsed_resolution or "",
        "codec": media.parsed_codec or "",
        "release_group": media.parsed_release_group or "",
    }


def sanitize(name: str) -> str:
    cleaned = _ILLEGAL.sub("", name)
    cleaned = _SEPARATOR.sub(" - ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = cleaned.strip(" .-–_")
    return cleaned[:200].strip()


def render_filename(template: str, context: dict, extension: str) -> str:
    validate_template(template)
    values = dict(context)
    for field in ("season", "episode"):
        if values.get(field) is None:
            raise TemplateError(f"缺少 {field}，无法生成文件名")
    try:
        rendered = template.format(**values)
    except (KeyError, ValueError, TypeError) as exc:
        raise TemplateError(f"模板渲染失败：{exc}") from exc
    name = sanitize(rendered)
    if not name:
        raise TemplateError("模板渲染结果为空")
    ext = extension if extension.startswith(".") else f".{extension}"
    return f"{name}{ext}"


def parent_of(path: str) -> str:
    return os.path.dirname(path)


def extension_of(name: str) -> str:
    return Path(name).suffix
