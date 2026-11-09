from sqlmodel import Session, select

from app.core.renamer import (
    TemplateError,
    build_context,
    extension_of,
    parent_of,
    render_filename,
)
from app.datasources.factory import DataSourceError, get_datasource
from app.models import MediaFile, ScrapeMatch
from app.schemas import RenamePreviewItem


def load_matches(session: Session, file_ids: list[int]) -> dict[int, ScrapeMatch]:
    if not file_ids:
        return {}
    rows = session.exec(select(ScrapeMatch).where(ScrapeMatch.file_id.in_(file_ids))).all()
    return {row.file_id: row for row in rows}


async def build_preview(
    session: Session, files: list[MediaFile], template: str
) -> list[RenamePreviewItem]:
    matches = load_matches(session, [f.id for f in files if f.id is not None])
    datasource_cache = {}
    used: dict[str, set[str]] = {}
    items: list[RenamePreviewItem] = []

    for media in files:
        file_id = media.id or 0
        item = RenamePreviewItem(
            file_id=file_id,
            original_name=media.original_name,
            status="skipped",
        )

        if not media.is_video:
            item.reason = "非视频文件"
            items.append(item)
            continue

        match = matches.get(file_id)
        context = build_context(media, match)
        if context["season"] is None or context["episode"] is None:
            item.reason = "缺少季集信息，请先完成解析"
            items.append(item)
            continue
        if not context["title"]:
            item.reason = "缺少剧名"
            items.append(item)
            continue

        try:
            new_name = render_filename(
                template, context, extension_of(media.original_name)
            )
        except TemplateError as exc:
            item.status = "error"
            item.reason = str(exc)
            items.append(item)
            continue

        item.new_name = new_name
        if new_name == media.original_name:
            item.reason = "名称未变化"
            items.append(item)
            continue

        key = (media.source_type, media.openlist_id)
        try:
            if key not in datasource_cache:
                datasource_cache[key] = get_datasource(
                    session, media.source_type, media.openlist_id
                )
            datasource = datasource_cache[key]
            parent = parent_of(media.source_ref)
            batch_names = used.setdefault(parent, set())
            if new_name in batch_names:
                item.status = "conflict"
                item.reason = "同一批次内目标文件名重复"
            elif await datasource.exists(parent, new_name):
                item.status = "conflict"
                item.reason = "目标文件已存在"
            else:
                item.status = "ready"
            batch_names.add(new_name)
        except DataSourceError as exc:
            item.status = "error"
            item.reason = str(exc)
        except Exception as exc:  # 数据源网络/权限错误
            item.status = "error"
            item.reason = f"检查目标文件失败：{exc}"
        items.append(item)

    return items
