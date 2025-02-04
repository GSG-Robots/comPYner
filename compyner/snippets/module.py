def __init__(self, name=None):
    super().__init__()
    self["__name__"] = name


def __getattr__(self, key):
    return self[key]


def __setattr__(self, key, value):
    self[key] = value


def __delattr__(self, key):
    del self[key]


def __repr__(self) -> str:
    return "<Module %s (comPyned)>" % self.get("__name__", "unknown")
