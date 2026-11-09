from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = {}

    async def connect(self, task_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.setdefault(task_id, set()).add(websocket)

    def disconnect(self, task_id: str, websocket: WebSocket) -> None:
        connections = self._connections.get(task_id)
        if not connections:
            return
        connections.discard(websocket)
        if not connections:
            self._connections.pop(task_id, None)

    async def broadcast(self, task_id: str, message: dict) -> None:
        for websocket in list(self._connections.get(task_id, set())):
            try:
                await websocket.send_json(message)
            except Exception:
                self.disconnect(task_id, websocket)


manager = ConnectionManager()
