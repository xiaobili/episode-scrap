import asyncio
import os

import httpx
from loguru import logger
from sqlmodel import Session, select

from app.core.nfo import generate_episode_nfo
from app.core.renamer import parent_of
from app.datasources.factory import get_datasource
from app.db import engine
from app.models import (
    MediaFile,
    RenameHistory,
    ScrapeMatch,
    TaskItem,
    TaskRecord,
    utcnow,
)
from app.schemas import RollbackOut
from app.ws import manager


class TaskManager:
    def __init__(self) -> None:
        self._running: dict[str, asyncio.Task] = {}

    def start(self, task_id: str) -> None:
        self._running[task_id] = asyncio.create_task(self._run(task_id))

    async def _run(self, task_id: str) -> None:
        with Session(engine) as session:
            task = session.get(TaskRecord, task_id)
            if not task:
                return
            task.status = "running"
            session.add(task)
            session.commit()
            await manager.broadcast(task_id, self._payload(task))

            items = session.exec(select(TaskItem).where(TaskItem.task_id == task_id)).all()
            datasource_cache = {}
            for item in items:
                media = session.get(MediaFile, item.file_id) if item.file_id else None
                if not media:
                    item.status = "failed"
                    item.error = "文件记录不存在"
                    task.failed += 1
                    session.add(item)
                    session.add(task)
                    session.commit()
                    await manager.broadcast(task_id, self._payload(task, item))
                    continue

                match = session.exec(
                    select(ScrapeMatch).where(ScrapeMatch.file_id == media.id)
                ).first()
                try:
                    key = (media.source_type, media.openlist_id)
                    if key not in datasource_cache:
                        datasource_cache[key] = get_datasource(
                            session, media.source_type, media.openlist_id
                        )
                    datasource = datasource_cache[key]
                    new_path = await datasource.rename(
                        media.source_ref, item.new_name or media.original_name
                    )

                    # 先落库重命名结果，保证元数据写入失败时仍可撤销
                    session.add(
                        RenameHistory(
                            task_id=task_id,
                            file_id=media.id,
                            source_type=media.source_type,
                            openlist_id=media.openlist_id,
                            original_path=media.source_ref,
                            new_path=new_path,
                        )
                    )
                    media.source_ref = new_path
                    media.original_name = item.new_name or media.original_name
                    media.new_name = media.original_name
                    media.status = "renamed"
                    session.add(media)

                    if task.write_nfo and match:
                        try:
                            nfo = generate_episode_nfo(media, match)
                            nfo_name = (
                                f"{os.path.splitext(item.new_name or media.original_name)[0]}.nfo"
                            )
                            await datasource.upload(
                                parent_of(new_path), nfo.encode("utf-8"), nfo_name
                            )
                        except Exception as exc:  # NFO 失败不影响重命名结果
                            logger.warning("写入 NFO 失败 {}: {}", item.name, exc)

                    if task.download_posters and match and match.still_url and media.source_type == "local":
                        await self._download_thumb(datasource, new_path, match.still_url, item.new_name)

                    item.status = "success"
                    item.error = None
                    task.done += 1
                except Exception as exc:  # 单文件失败不中断批次
                    logger.warning("重命名失败 {}: {}", item.name, exc)
                    item.status = "failed"
                    item.error = str(exc)
                    task.failed += 1

                session.add(item)
                session.add(task)
                session.commit()
                await manager.broadcast(task_id, self._payload(task, item))

            task.status = "completed"
            task.finished_at = utcnow()
            session.add(task)
            session.commit()
            await manager.broadcast(task_id, self._payload(task))
        self._running.pop(task_id, None)

    @staticmethod
    async def _download_thumb(datasource, new_path: str, url: str, new_name: str | None) -> None:
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()
            stem = os.path.splitext(new_name or os.path.basename(new_path))[0]
            await datasource.upload(parent_of(new_path), response.content, f"{stem}-thumb.jpg")
        except Exception as exc:
            logger.warning("下载剧照失败 {}: {}", url, exc)

    @staticmethod
    def _payload(task: TaskRecord, item: TaskItem | None = None) -> dict:
        payload = {
            "type": "progress",
            "task_id": task.id,
            "status": task.status,
            "total": task.total,
            "done": task.done,
            "failed": task.failed,
        }
        if item:
            payload["item"] = {
                "id": item.id,
                "name": item.name,
                "new_name": item.new_name,
                "status": item.status,
                "error": item.error,
            }
        return payload


task_manager = TaskManager()


async def rollback_task(session: Session, task_id: str | None) -> RollbackOut:
    if not task_id:
        latest = session.exec(
            select(RenameHistory)
            .where(RenameHistory.rolled_back.is_(False))
            .order_by(RenameHistory.executed_at.desc())
        ).first()
        if not latest:
            return RollbackOut(task_id=None, restored=0, failed=0, errors=["没有可撤销的重命名记录"])
        task_id = latest.task_id

    histories = session.exec(
        select(RenameHistory).where(
            RenameHistory.task_id == task_id,
            RenameHistory.rolled_back.is_(False),
        )
    ).all()
    restored = 0
    failed = 0
    errors: list[str] = []
    datasource_cache = {}

    for history in histories:
        try:
            key = (history.source_type, history.openlist_id)
            if key not in datasource_cache:
                datasource_cache[key] = get_datasource(
                    session, history.source_type, history.openlist_id
                )
            datasource = datasource_cache[key]
            original_name = os.path.basename(history.original_path)
            await datasource.rename(history.new_path, original_name)
            history.rolled_back = True
            session.add(history)

            if history.file_id:
                media = session.get(MediaFile, history.file_id)
                if media:
                    media.source_ref = history.original_path
                    media.original_name = original_name
                    media.new_name = None
                    media.status = "matched"
                    session.add(media)
            restored += 1
        except Exception as exc:
            failed += 1
            errors.append(f"{os.path.basename(history.new_path)}: {exc}")
        session.commit()

    return RollbackOut(
        task_id=task_id, restored=restored, failed=failed, errors=errors
    )
