class __comPYned_DotDict(dict):
    def __getattr__(self, key):
        return self[key]

    def __setattr__(self, key, value):
        self[key] = value

    def __delattr__(self, key):
        del self[key]


__comPYned_modules = {}
__comPYned_SELF = None


def __comPYned_begin_module(name):
    global __name__, __comPYned_SELF
    __name__ = name
    __comPYned_SELF = __comPYned_DotDict()


def __comPYned_end_module():
    global __comPYned_modules, __name__, __comPYned_SELF
    __comPYned_modules[__name__] = __comPYned_SELF

def __comPYned_import(module):
    return __comPYned_modules[module]()
