from .state import STATE
from .util import isgenerator, isgeneratorfunction


def queueable(func):
    """
    Make a function queueable. If the function is called while a queue is being built, it will be added to the queue. Otherwise, it will behave as normal.
    """

    def wrapper(*args, **kwargs):
        nonlocal func
        if STATE.is_building:
            return STATE.queue.add(func, args, kwargs)
        return func(*args, **kwargs)

    return wrapper


class Queue:
    def __init__(self, name=None):
        self.name = name
        self.queue = []

    def add(self, func, args, kwargs):
        self.queue.append((func, args, kwargs))

    @queueable
    def start(self):
        STATE.queue_manager.add(self)

    @queueable
    def stop(self):
        STATE.queue_manager.remove(self)

    @queueable
    def next(self):
        func, args, kwargs = self.queue[0]
        if isgeneratorfunction(func):
            with STATE.running(self):
                func = func(*args, **kwargs)
            args = ()
            kwargs = {}
            self.queue[0] = (func, args, kwargs)
        if isgenerator(func):
            try:
                with STATE.running(self):
                    next(func)
            except StopIteration:
                self.queue.pop(0)
        else:
            with STATE.running(self):
                func(*args, **kwargs)
            self.queue.pop(0)


class QueueWrapper:
    def __init__(self, func):
        self._queue = None
        self.func = func

    @property
    def _sub_queue(self):
        if self._queue is None:
            queue_ = Queue(self.func.__name__)
            with STATE.building(queue_):
                self.func()
            self._queue = queue_
        return self._queue

    @queueable
    def next(self):
        self._sub_queue.next()

    @queueable
    def start(self):
        self._sub_queue.start()

    @queueable
    def stop(self):
        self._sub_queue.stop()


def queue(func):
    """
    Create a queue from a function. All actions in the function should be queueable. If they are not, they will be executed immediately.
    """
    queue_ = Queue(func.__name__)
    with STATE.building(queue_):
        func()
    return queue_


def queuew(func):
    """
    Works similarly to queue, but wraps the queue in a QueueWrapper.
    This will act the same as a Queue, but the initialisation of the queue will be delayed until its first use.
    """
    return QueueWrapper(func)
