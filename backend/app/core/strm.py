import os
import string
from urllib.parse import quote

from app.core.renamer import sanitize

STRM_FIELDS = {"base_url", "path", "raw_path", "filename"}


class StrmTemplateError(ValueError):
    pass


def validate_strm_template(template: str) -> None:
    if not template.strip():
        raise StrmTemplateError("STRM 模板不能为空")
    try:
        parsed = list(string.Formatter().parse(template))
    except ValueError as exc:
        raise StrmTemplateError(f"模板格式错误：{exc}") from exc

    fields: set[str] = set()
    for _literal, field_name, format_spec, _conversion in parsed:
        if field_name is None:
            continue
        if field_name not in STRM_FIELDS:
            allowed = "、".join(sorted(STRM_FIELDS))
            raise StrmTemplateError(f"未知模板变量 {{{field_name}}}，可用变量：{allowed}")
        if format_spec:
            raise StrmTemplateError(f"变量 {{{field_name}}} 不支持格式说明符")
        fields.add(field_name)

    if not fields & {"path", "raw_path"}:
        raise StrmTemplateError("STRM 模板必须包含 {path} 或 {raw_path}")


def render_strm(template: str, *, base_url: str, path: str) -> str:
    validate_strm_template(template)
    return template.format(
        base_url=base_url.rstrip("/"),
        # 站内路径省略前导斜杠，避免与模板中的 / 叠成双斜杠
        path=quote(path.lstrip("/"), safe="/"),
        raw_path=path,
        filename=os.path.basename(path),
    )


def strm_filename(name: str) -> str:
    stem, _ = os.path.splitext(os.path.basename(name))
    return f"{stem}.strm"


def library_target(root: str, title: str, season: int | None, filename: str) -> str:
    return os.path.join(
        root,
        sanitize(title) or "未分类",
        f"Season {int(season or 1):02d}",
        filename,
    )


def mirror_target(
    root: str, base: str | None, source_path: str, filename: str
) -> str | None:
    if not base:
        return None
    parent = os.path.dirname(source_path)
    try:
        rel = os.path.relpath(parent, base)
    except ValueError:
        return None
    if rel == ".." or rel.startswith(f"..{os.sep}"):
        return None
    if rel == ".":
        return os.path.join(root, filename)
    return os.path.join(root, rel, filename)


def match_strm_rule(rules: list[dict], path: str) -> tuple[dict, str] | None:
    """按路径段边界做最长前缀匹配，返回命中的规则与相对目录。"""
    parent = os.path.dirname(path)
    best: tuple[dict, str, int] | None = None
    for rule in rules:
        source = os.path.normpath(str(rule.get("source") or "")).rstrip("/")
        if not source:
            continue
        if parent == source:
            rel = ""
        elif parent.startswith(f"{source}/"):
            rel = os.path.relpath(parent, source)
        else:
            continue
        if best is None or len(source) > best[2]:
            best = (rule, rel, len(source))
    if best is None:
        return None
    return best[0], best[1]


def rule_target_dir(rule: dict, rel_dir: str) -> str:
    base = str(rule.get("target_dir") or "/").rstrip("/")
    return f"{base}/{rel_dir}" if rel_dir else base or "/"
