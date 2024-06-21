# LEGO type:standard slot:3 autostart
import time

try:
    from inspect import isgeneratorfunction, isgenerator
except ImportError:
    type_GeneratorFunction = type((lambda: (yield)))  # Generator function
    type_GeneratorObject = type((lambda: (yield))())  # Generator type
    def isgeneratorfunction(func):
        return isinstance(func, type_GeneratorFunction)
    def isgenerator(func):
        return isinstance(func, type_GeneratorObject)

class ChangeStateContext:
    """
    Context manager for changing the state of the program.
    This is used to change the state of the program to building or running, and then back to idle when the context is exited.
    """
    
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
    """
    The program state.
    This is used to keep track of whether the program is building a queue, running a queue, or idle.
    """
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
    """
    A collection of conditions that can be used with wait_until.
    """
    @classmethod
    def time_is(cls, until):
        """
        Returns a condition that is met when the current time is equal to or greater than `until`.
        """
        return lambda: time.time() >= until

    @classmethod
    def time_passed(cls, n):
        """
        Returns a condition that is met when `n` seconds have passed.
        """
        return cls.time_is(time.time() + n)
op = print

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

@queueable
def wait_until(check):
    """
    Yield/wait until a condition is met.
    """
    while not check():
        yield


class Queue:
    def __init__(self, name=None):
        self.name = name
        self.queue = []

    def add(self, func, args, kwargs):
        self.queue.append((func, args, kwargs))

    @queueable
    def start(self):
        global QUEUE_MANAGER
        QUEUE_MANAGER.add(self)
        
    @queueable
    def stop(self):
        global QUEUE_MANAGER
        QUEUE_MANAGER.remove(self)

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
            self._queue = queue(self.func)
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


STATE = State()
QUEUE_MANAGER = None
QueueManager()


@queueable
def sleep(n):
    """
    Shortcut for waiting for a certain amount of time. (in seconds)
    """
    yield from wait_until(Conditions.time_passed(n))


print = queueable(print)


@queuew
def main2():
    print("b1")
    sleep(1)
    print("b2")

@queuew
def main():
    print("a1")
    sleep(1)
    main2.start()
    print("a2")

# op(main.queue)
main.start()

QUEUE_MANAGER.run_until_complete()
