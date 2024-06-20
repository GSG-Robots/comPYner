# LEGO type:standard slot:3 autostart
import time

try:
    from inspect import isgeneratorfunction, isgenerator
except ModuleNotFoundError:
    type_GeneratorFunction = type((lambda: (yield)))  # Generator function
    type_GeneratorObject = type((lambda: (yield))())  # Generator type
    def isgeneratorfunction(func):
        return isinstance(func, type_GeneratorFunction)
    def isgenerator(func):
        return isinstance(func, type_GeneratorObject)

class ChangeStateContext:
    def __init__(self, state: "State", building_queue: "Queue", running_queue: "Queue"):
        self.state = state
        self.new_building_queue = building_queue
        self.new_running_queue = running_queue
        self.old_building_queue = None
        self.old_running_queue = None

    def __enter__(self):
        self.old_building_queue = self.state.building_queue
        self.state.building_queue = self.new_building_queue
        self.old_building_queue = self.state.running_queue
        self.state.running_queue = self.new_running_queue

    def __exit__(self, *args):
        self.state.building_queue = self.old_building_queue
        self.state.running_queue = self.old_running_queue


class State:
    building_queue: "Queue" = None
    running_queue: "Queue" = None

    def __init__(self):
        self.building_queue = None
        self.running_queue = None

    @property
    def is_running(self):
        return self.running_queue is not None

    @property
    def is_building(self):
        return self.building_queue is not None

    @property
    def is_idle(self):
        return not self.is_running and not self.is_building

    @property
    def queue(self):
        return self.building_queue or self.running_queue

    def building(self, queue_):
        return ChangeStateContext(self, queue_, None)

    def running(self, queue_):
        return ChangeStateContext(self, None, queue_)

    def idle(self):
        return ChangeStateContext(self, None, None)


class Conditions:
    @classmethod
    def time_is(cls, until):
        return lambda: time.time() >= until

    @classmethod
    def time_passed(cls, n):
        return cls.time_is(time.time() + n)


def queueable(func):
    def wrapper(*args, **kwargs):
        nonlocal func
        if isgeneratorfunction(func):
            func = func(*args, **kwargs)
        if STATE.is_building:
            return STATE.queue.add(func, *args, **kwargs)
        return func(*args, **kwargs)

    return wrapper


def queue(func):
    queue_ = Queue()
    with STATE.building(queue_):
        func()
    return queue_


def wait_until(check):
    while not check():
        yield


class Queue:
    def __init__(self):
        self.queue = []
        # self.start = queueable(self.start)

    def add(self, func, *args, **kwargs):
        self.queue.append((func, args, kwargs))

    def start(self):
        global QUEUE_MANAGER
        QUEUE_MANAGER.add(self)

    def next(self):
        func, args, kwargs = self.queue[0]
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


class QueueManager:
    def __init__(self) -> None:
        global QUEUE_MANAGER
        if QUEUE_MANAGER is not None:
            raise RuntimeError("Only one QueueManager may exist!")
        QUEUE_MANAGER = self
        self.queues: list[Queue] = []

    def add(self, queue_):
        if callable(queue_):
            queue_ = queue(queue_)
        if not isinstance(queue_, Queue):
            raise TypeError("'queue' must be a callable or Queue")
        self.queues.append(queue_)

    # TODO: remove

    def tick_all(self):
        for queue_ in self.queues:
            if not queue_.queue:
                self.queues.remove(queue_)
                continue
            queue_.next()

    def run_until_complete(self):
        while self.queues:
            self.tick_all()


STATE = State()
QUEUE_MANAGER = None
QueueManager()


@queueable
def sleep(n):
    yield from wait_until(Conditions.time_passed(n))


print = queueable(print)


@queueable
def start_queue(queue_):
    queue_.start()


@queue
def main2():
    print("b1")
    sleep(1)
    print("b2")


@queue
def main():
    print("a1")
    sleep(1)
    start_queue(main2)
    print("a2")


main.start()

QUEUE_MANAGER.run_until_complete()
