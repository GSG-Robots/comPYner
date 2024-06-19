# LEGO type:standard slot:3 autostart
import time

type_GeneratorObject = type((lambda: (yield))())  # Generator type
type_GeneratorFunction = type((lambda: (yield)))  # Generator function


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

    def building(self, queue):
        return ChangeStateContext(self, queue, None)

    def running(self, queue):
        return ChangeStateContext(self, None, queue)

    def idle(self):
        return ChangeStateContext(self, None, None)


STATE = State()


class Conditions:
    @classmethod
    def time_is(cls, until):
        return lambda: time.time() >= until

    @classmethod
    def time_passed(cls, n):
        return cls.time_is(time.time() + n)


class Queue:
    def __init__(self):
        self.queue = []

    def add(self, func, *args, **kwargs):
        self.queue.append((func, args, kwargs))

    def next(self):
        func, args, kwargs = self.queue[0]
        if isinstance(func, type_GeneratorFunction):
            func = func(*args, **kwargs)
            self.queue[0] = (func, args, kwargs)
        if isinstance(func, type_GeneratorObject):
            try:
                with STATE.running(self):
                    next(func)
            except StopIteration:
                self.queue.pop(0)
        else:
            func(*args, **kwargs)
            self.queue.pop(0)


def queueable(func):
    def wrapper(*args, **kwargs):
        if STATE.is_building:
            return STATE.queue.add(func, *args, **kwargs)
        return func(*args, **kwargs)

    return wrapper


def queue(func):
    queue = Queue()
    with STATE.building(queue):
        func()
    return queue

def wait_until(check):
    while not check():
        yield

@queueable
def sleep(n):
    yield from wait_until(Conditions.time_passed(n))


print = queueable(print)


@queue
def main():
    print(1)
    sleep(1)
    print(2)


print(main.queue)

while main.queue:
    main.next()
