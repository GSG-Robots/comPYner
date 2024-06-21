from typing import TYPE_CHECKING
from .state import STATE
from .queue import Queue


class QueueManager:
    def __init__(self) -> None:
        self.queues: list[Queue] = []

    def add(self, queue_):
        if callable(queue_):
            queue_ = queue(queue_)
        if not isinstance(queue_, Queue):
            raise TypeError("'queue' must be a callable or Queue")
        self.queues.append(queue_)

    def remove(self, queue_):
        if not isinstance(queue_, Queue):
            raise TypeError("'queue' must be a Queue")
        self.queues.remove(queue_)

    def tick_all(self):
        for queue_ in self.queues:
            if not queue_.queue:
                self.queues.remove(queue_)
                continue
            queue_.next()

    def run_until_complete(self):
        while self.queues:
            self.tick_all()


STATE.queue_manager = QueueManager()
