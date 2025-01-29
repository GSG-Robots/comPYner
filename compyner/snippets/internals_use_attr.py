def __getattr__(self, key):
    return self[key]


def __setattr__(self, key, value):
    self[key] = value


def __repr__(self) -> str:
    return "<Module %s (comPyned)>" % self.get("__name__", "unknwon")
