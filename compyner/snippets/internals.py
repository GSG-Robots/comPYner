class Module(dict):
    def __getattr__(self, key):
        return self[key]

    def __setattr__(self, key, value):
        self[key] = value

    # def __delattr__(self, key):
    #     del self[key]

    def __repr__(self) -> str:
        return "<Module %s (comPyned)>" % self.get("__name__", "unknown")

    # def __str__(self) -> str:
    #     return repr(self)

modules = {}
# executed_modules = {}

def get(self, module):
    if module not in self.modules:
        raise ImportError("Module %s not found" % module)
    # if module not in self.executed_modules:
    #     self.executed_modules[module] = self.modules[module]()
    # return self.executed_modules[module]
    return self.modules[module]
