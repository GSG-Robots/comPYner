class __comPYned_Module(dict):
    def __getattr__(self, key):
        return self[key]

    def __setattr__(self, key, value):
        self[key] = value

    def __delattr__(self, key):
        del self[key]

    def __repr__(self) -> str:
        return "<Module %s (comPyned)>" % self.__name__

    def __str__(self) -> str:
        return repr(self)


__comPYned_modules = {}


def __comPYned_import(module):
    return __comPYned_modules[module]()
