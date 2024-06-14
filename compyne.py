import os
import re
import sys
import importlib.util
import warnings


def tabulate(code, spaces=4):
    spaces = " " * spaces
    return "\n".join([spaces + line for line in code.splitlines() if line.strip()])


sys.path.append(os.getcwd())


class Compyner:
    def __init__(self, exclude=None):
        self.exclude = exclude or ()
        self.modules = {}
        self.main = None
        self.last_temp_import = None

    def load_module(self, name, parent=None):
        if name.split(".", 1)[0] in self.exclude:
            return True
        if self.modules.get(name) is not None:
            return False

        spec = importlib.util.find_spec(name, parent)
        if not spec:
            raise ModuleNotFoundError(f"Module {name} not found")
        if spec.origin == "built-in":
            warnings.warn(
                f"Module {name} cannot be included: It is a built-in module. Excluded automatically, make sure it exists in the target environment."
            )
            return True
        if not spec.has_location:
            warnings.warn(
                f"Module {name} cannot be included: It does not have a location. Excluded automatically, make sure it exists in the target environment."
            )
            return True
        print(f"Loading module {name} from {spec.origin}", file=sys.stderr)
        with open(spec.origin, "r", encoding="utf-8") as f:
            module_code = f.read()

        if "__comPYned" in module_code:
            warnings.warn(f"Module {name} contains __comPYned, which may cause issues.")

        self.modules[name] = self.replace_imports(module_code, spec.parent)

        return False

    def import_module(self, module, as_name=None, parent=None):
        is_builtin = self.load_module(module, parent)
        if is_builtin:
            return f'{as_name or module} = __import__("{module}", globals(), locals(), [""])'
        return f'__comPYned_import_module("{module}", "{as_name or module}")'

    def import_object(self, module, object, as_name=None, parent=None):
        is_builtin = self.load_module(module, parent)
        if is_builtin:
            return f'{as_name or object} = __import__("{module}", globals(), locals(), ["{object}"]).{object}'
        return (
            f'__comPYned_import_object("{module}", "{object}", "{as_name or object}")'
        )

    def import_all(self, module, parent=None):
        is_builtin = self.load_module(module, parent)
        if is_builtin:
            return f'_a = __import__("{module}", globals(), locals(), [""]):print(_a)'
        return f'__comPYned_import_all("{module}")'

    def replace_imports(self, code, parent=None):
        def replace_object_import(match):
            module = match.group(2)
            return match.group(1) + "\n".join(
                [
                    self.import_object(
                        module,
                        object,
                        match.group(4),
                        parent,
                    )
                    for object in match.group(3)
                    .replace(" ", "")
                    .replace("\n", "")
                    .replace("\t", "")
                    .replace("\r", "")
                    .replace("(", "")
                    .replace("),", "")
                    .split(",")
                ]
            )

        def replace_module_imports(match):
            module = match.group(2)
            return match.group(1) + self.import_module(module, match.group(3), parent)

        def replace_all_imports(match):
            module = match.group(2)
            return match.group(1) + self.import_all(module, parent=parent)

        code = re.sub(
            r"(^|\n)from\s+([A-Za-z0-9_.]+)\s+import\s+\(?(?:\*)\)?",
            replace_all_imports,
            code,
            re.MULTILINE,
        )
        code = re.sub(
            r"(^|\n)from\s+([A-Za-z0-9_.]+)\s+import\s+(?:\(?\s*)((?:[A-Za-z0-9_]+(?:,\s*)?)+)\)?(?:\s+as\s+([A-Za-z0-9_]+))?",
            replace_object_import,
            code,
            re.MULTILINE,
        )
        code = re.sub(
            r"(^|\n)import\s+([A-Za-z0-9_.]+)(?:\s+as\s+([A-Za-z0-9_]+))?",
            replace_module_imports,
            code,
            re.MULTILINE,
        )
        return code

    def set_main(self, name):
        self.load_module(name)
        self.main = name

    def get_code(self):
        module_code = "\n".join(
            [
                f"""__comPYned_start_record()
__comPYned_import_as = "{name}"
__name__ = "{'__main__' if self.main == name else name}"
{code}
__comPYned_finish_record()"""
                for name, code in self.modules.items()
            ]
        )
        code = f"""class __comPYnedModule:
    def __init__(self, module_data):
        self.module_data = module_data

    def __getattr__(self, name):
        return self.module_data[name]

    def __repr__(self):
        return "<module '%s' (comPYned)>" % self.__name__

    def __str__(self):
        return repr(self)
    
    def __dir__(self):
        return self.module_data.keys()


__comPYned_modules = {{}}
__comPYned_globals_tracker = {{}}
__comPYned_import_as = None


def __comPYned_import_module(module, named):
    globals()[named] = __comPYned_modules[module]

def __comPYned_import_object(module, object, named):
    globals()[named] = getattr(__comPYned_modules[module], object)
    
def __comPYned_import_all(module):
    for key in dir(__comPYned_modules[module]):
        if key == "__name__":
            continue
        globals()[key] = getattr(module, key)


def __comPYned_start_record():
    global __comPYned_globals_tracker
    __comPYned_globals_tracker = globals().copy()


def __comPYned_finish_record():
    module = {{name: value for name, value in globals().items() if not name.startswith("__comPYned") and __comPYned_globals_tracker.get(name) != value}}
    __comPYned_modules[__comPYned_import_as] = __comPYnedModule(module)
    for key in globals().copy().keys():
        if key.startswith("__comPYned"):
            continue
        if key.startswith("__") and key.endswith("__"):
            continue
        del globals()[key]


{module_code}

raise SystemExit("Reached comPYned file end.")
"""
        return code


def compyne(name, exclude=None):
    compyner = Compyner(exclude)
    compyner.set_main(name)
    return compyner.get_code()


if __name__ == "__main__":
    print(
        compyne(
            sys.argv[1],
            exclude=sys.argv[2:],
        )
    )
