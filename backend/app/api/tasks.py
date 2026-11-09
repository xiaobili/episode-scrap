from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlmodel import Session, select

from app.db import engine, get_session
from app.models import TaskItem, TaskRecord
from app.schemas import TaskDetailOut, TaskOut, TaskItemOut, task_item_out, task_out
from app.services.task_manager import task_manager
from app.ws import manager

router = APIRouter(tags=["tasks"])


@router.get("/api/tasks", response_model=list[TaskOut])
def list_tasks(
    type: str | None = None,
    status: str | None = None,
    limit: int = Query(default=100, le=500),
    session: Session = Depends(get_session),
) -> list[TaskOut]:
    stmt = select(TaskRecord)
    if type:
        stmt = stmt.where(TaskRecord.type == type)
    if status:
        stmt = stmt.where(TaskRecord.status == status)
    stmt = stmt.order_by(TaskRecord.created_at.desc()).limit(limit)
    return [task_out(task) for task in session.exec(stmt).all()]


@router.get("/api/tasks/{task_id}", response_model=TaskDetailOut)
def task_detail(task_id: str, session: Session = Depends(get_session)) -> TaskDetailOut:
    task = session.get(TaskRecord, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    items = session.exec(
        select(TaskItem).where(TaskItem.task_id == task_id).order_by(TaskItem.id)
    ).all()
    return TaskDetailOut(
        **task_out(task).model_dump(),
        items=[task_item_out(item) for item in items],
    )


@router.post("/api/tasks/{task_id}/retry", response_model=TaskOut)
async def retry_task(task_id: str, session: Session = Depends(get_session)) -> TaskOut:
    task = session.get(TaskRecord, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    failed_items = session.exec(
        select(TaskItem).where(
            TaskItem.task_id == task_id, TaskItem.status == "failed"
        )
    ).all()
    if not failed_items:
        raise HTTPException(status_code=400, detail="该任务没有失败项")

    new_id = uuid4().hex
    new_task = TaskRecord(
        id=new_id,
        type=task.type,
        source_type=task.source_type,
        status="pending",
        total=len(failed_items),
        template=task.template,
        write_nfo=task.write_nfo,
        download_posters=task.download_posters,
        write_strm=task.write_strm,
    )
    session.add(new_task)
    for item in failed_items:
        session.add(
            TaskItem(
                task_id=new_id,
                file_id=item.file_id,
                name=item.name,
                new_name=item.new_name,
                status="pending",
            )
        )
    session.commit()
    session.refresh(new_task)
    task_manager.start(new_id)
    return task_out(new_task)


@router.websocket("/ws/tasks/{task_id}")
async def task_progress(websocket: WebSocket, task_id: str) -> None:
    await manager.connect(task_id, websocket)
    try:
        with Session(engine) as session:
            task = session.get(TaskRecord, task_id)
            if task:
                await websocket.send_json(task_manager._payload(task))
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(task_id, websocket)
    except Exception:
        manager.disconnect(task_id, websocket)
