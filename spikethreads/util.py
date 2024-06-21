try:
    from inspect import isgeneratorfunction, isgenerator
except ImportError:
    type_GeneratorFunction = type((lambda: (yield)))  # Generator function
    type_GeneratorObject = type((lambda: (yield))())  # Generator type

    def isgeneratorfunction(func):
        return isinstance(func, type_GeneratorFunction)

    def isgenerator(func):
        return isinstance(func, type_GeneratorObject)
