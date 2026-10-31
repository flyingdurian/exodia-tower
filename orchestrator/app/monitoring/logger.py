"""In-memory event bus backed by the DB; prevents secret-bearing logs."""
import asyncio
from collections import deque
from datetime import datetime, timezone
from threading import Lock
from app.security.vault import redact

class EventLog:
    def __init__(self):
        self._events = deque(maxlen=160)
        self._lock = Lock()
        self._listeners: set[asyncio.Queue] = set()

    def publish(self, kind: str, message: str, detail: str = '') -> dict:
        event = {
            'at': datetime.now(timezone.utc).isoformat(),
            'kind': kind[:24], 'message': redact(message[:240]), 'detail': redact(detail[:400])
        }
        with self._lock:
            self._events.appendleft(event)
            for q in list(self._listeners):
                try:
                    q.put_nowait(event)
                except asyncio.QueueFull:
                    pass
        return event

    def latest(self, limit: int = 30) -> list[dict]:
        with self._lock:
            return list(self._events)[:limit]

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=128)
        with self._lock:
            self._listeners.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        with self._lock:
            self._listeners.discard(q)
