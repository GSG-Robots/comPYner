from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .queue import Queue

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
    queue_manager = None

    def __init__(self):
        self.building_queue = None
        self.running_queue = None
        self.queue_manager = None

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

STATE = State()
