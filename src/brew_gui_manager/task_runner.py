from __future__ import annotations

from dataclasses import dataclass
from queue import Empty
from queue import Queue
import threading
from typing import Any, Callable


@dataclass(slots=True)
class TaskEvent:
    task_id: int
    description: str
    status: str
    payload: Any = None
    error: Exception | None = None


class BackgroundTaskRunner:
    def __init__(self) -> None:
        self._events: Queue[TaskEvent] = Queue()
        self._lock = threading.Lock()
        self._next_task_id = 1

    def submit(self, description: str, fn: Callable[[], Any]) -> int:
        with self._lock:
            task_id = self._next_task_id
            self._next_task_id += 1

        self._events.put(TaskEvent(task_id=task_id, description=description, status="started"))
        thread = threading.Thread(
            target=self._run_task,
            args=(task_id, description, fn),
            daemon=True,
        )
        thread.start()
        return task_id

    def drain_events(self) -> list[TaskEvent]:
        events: list[TaskEvent] = []
        while True:
            try:
                events.append(self._events.get_nowait())
            except Empty:
                return events

    def _run_task(self, task_id: int, description: str, fn: Callable[[], Any]) -> None:
        try:
            payload = fn()
        except Exception as exc:  # noqa: BLE001
            self._events.put(
                TaskEvent(
                    task_id=task_id,
                    description=description,
                    status="failed",
                    error=exc,
                )
            )
            return

        self._events.put(
            TaskEvent(
                task_id=task_id,
                description=description,
                status="completed",
                payload=payload,
            )
        )
