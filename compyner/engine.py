import ast
import importlib.util
from pathlib import Path
import re
import sys
import warnings


def name_replacement(
    compyner: "ComPYner", name: str, original_node: ast.AST, ctx: ast.expr_context
) -> ast.Attribute:
    if (
        name in (compyner.tmp, compyner.tmp_sub, compyner.static)
        or name == "ComPYnerBuildTools"
    ):
        return ast.copy_location(ast.Name(id=name, ctx=ctx), original_node)
    attr = ast.Attribute(
        value=ast.Name(compyner.tmp_self, ast.Load()),
        attr=name,
        ctx=ctx,
    )
    attr = ast.copy_location(attr, original_node)
    return attr


def ast_from_file(file_path: Path) -> ast.Module:
    with file_path.open(encoding="utf-8") as f:
        code = f.read()
    return ast.parse(code)


def path_from_module(module: str) -> Path:
    return Path(importlib.util.find_spec(module).origin)


START = ast_from_file(path_from_module("compyner.snippets.start"))
END = ast_from_file(path_from_module("compyner.snippets.end"))


class ComPYnerBuildTools:
    @staticmethod
    def get_modules_path_glob(
        replacer: "GlobalReplacer", node: ast.Call, /
    ) -> list[ast.AST]:
        args = [replacer.visit(arg) for arg in node.args]
        if len(args) != 1:
            raise ValueError("Import regex takes exaclty one argument")
        if not isinstance(args[0], ast.Constant):
            raise TypeError("The first argument of import_regex must be a constant")
        glob = args[0].value
        files = [file.absolute() for file in Path.cwd().glob(glob)]
        names = [file.with_suffix("").name for file in files]
        elts = []
        for name, file in zip(names, files):
            spec = importlib.util.spec_from_file_location(
                file.with_suffix("").name, file
            )
            do = replacer.compyner._load_module(spec, spec.name)
            if do is False:
                raise ValueError(
                    f"Could not import module {file.relative_to(Path.cwd())} using glob."
                )
            elts.append(
                ast.copy_location(
                    ast.Call(
                        ast.Attribute(
                            ast.Name(replacer.compyner.static, ast.Load()),
                            "get",
                            ast.Load(),
                        ),
                        [ast.Constant(name)],
                        [],
                    ),
                    node,
                )
            )

        return ast.copy_location(
            ast.List(
                elts=elts,
                ctx=ast.Load(),
            ),
            node,
        )


class GlobalFinder(ast.NodeVisitor):
    def __init__(self, explicit_only=False, context=None):
        super().__init__()
        self.globals = []
        self.explicit_only = explicit_only
        self.context = context or []

    def add(self, name):
        if name not in self.globals:
            self.globals.append((name, self.context))

    def visit_Name(self, node: ast.Name):
        if self.explicit_only:
            return
        if isinstance(node.ctx, ast.Store):
            self.add(node.id)

    def visit_Global(self, node):
        for name in node.names:
            self.add(name)

    def visit_FunctionDef(self, node):
        if not self.explicit_only:
            self.add(node.name)
        global_finder = GlobalFinder(
            explicit_only=True, context=self.context + [node.name]
        )
        for subnode in node.body:
            global_finder.visit(subnode)
        for decorator in node.decorator_list:
            self.visit(decorator)
        self.globals.extend(global_finder.globals)

    def visit_ClassDef(self, node):
        if not self.explicit_only:
            self.add(node.name)
        global_finder = GlobalFinder(
            explicit_only=True, context=self.context + [node.name]
        )
        for subnode in node.body:
            global_finder.visit(subnode)
        self.globals.extend(global_finder.globals)

    def visit_Import(self, node: ast.Import):
        if self.explicit_only:
            return
        for alias in node.names:
            self.add((alias.asname or alias.name).split(".")[0])

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if self.explicit_only:
            return
        for alias in node.names:
            self.add(alias.asname or alias.name)


class GlobalReplacer(ast.NodeTransformer):
    def __init__(
        self,
        compyner: "ComPYner",
        globals_,
        parent: "GlobalReplacer" = None,
        context=None,
    ):
        super().__init__()
        self.globals = globals_
        self.compyner = compyner
        self.parent = parent
        self.context = context or []

    def check(self, name, readonly):
        name = name.split(".")[0]
        ctx = self.context.copy()
        while ctx and readonly:
            if (name, ctx) in self.globals:
                return True
            ctx = ctx[:-1]
        return (name, ctx) in self.globals

    def visit_Name(self, node):
        if self.check(node.id, readonly=isinstance(node.ctx, ast.Load)):
            return name_replacement(self.compyner, node.id, node, node.ctx)
        return node

    def visit_Global(self, node: ast.Global):
        return ast.Pass()

    def visit_FunctionDef(self, node):
        sub_replacer = GlobalReplacer(
            self.compyner, self.globals, self.parent, self.context + [node.name]
        )
        node.body = [sub_replacer.visit(n) for n in node.body]
        node.decorator_list = [self.visit(n) for n in node.decorator_list]
        node.args = self.visit(node.args) if node.args else None
        if node.returns is not None:
            node.returns = self.visit(node.returns)

        if self.check(node.name, False):
            return [
                node,
                ast.copy_location(
                    ast.Assign(
                        targets=[
                            name_replacement(
                                self.compyner, node.name, node, ast.Store()
                            )
                        ],
                        value=ast.Name(id=node.name, ctx=ast.Load()),
                    ),
                    node,
                ),
            ]
        else:
            return node

    def visit_ClassDef(self, node):
        sub_replacer = GlobalReplacer(
            self.compyner, self.globals, self.parent, self.context + [node.name]
        )
        node.body = [sub_replacer.visit(n) for n in node.body]
        node.bases = [self.visit(n) for n in node.bases]

        if self.check(node.name, False):
            return [
                node,
                ast.copy_location(
                    ast.Assign(
                        targets=[
                            name_replacement(
                                self.compyner, node.name, node, ast.Store()
                            )
                        ],
                        value=ast.Name(id=node.name, ctx=ast.Load()),
                    ),
                    node,
                ),
            ]
        else:
            return node

    def visit_Import(self, node: ast.Import):
        new_imports = []
        for alias in node.names:
            replace_import = self.compyner.load_module(alias.name, self.parent)
            glob = self.check(alias.asname or alias.name, False)
            parts = (alias.asname or alias.name).split(".")
            for part in range(len(parts) - 1):
                new_imports.append(
                    ast.copy_location(
                        ast.Assign(
                            targets=[
                                name_replacement(
                                    self.compyner,
                                    ".".join(parts[: part + 1]),
                                    alias,
                                    ast.Store(),
                                )
                            ],
                            value=ast.Call(
                                ast.Attribute(
                                    ast.Name(self.compyner.static, ast.Load()),
                                    "Module",
                                    ast.Load(),
                                ),
                                [],
                                [],
                            ),
                        ),
                        node,
                    )
                )
            if replace_import:
                new_imports.append(
                    ast.copy_location(
                        ast.Assign(
                            targets=[
                                (
                                    name_replacement(
                                        self.compyner,
                                        alias.asname or alias.name,
                                        alias,
                                        ast.Store(),
                                    )
                                    if glob
                                    else ast.copy_location(
                                        ast.Name(
                                            alias.asname or alias.name, ast.Store()
                                        ),
                                        alias,
                                    )
                                )
                            ],
                            value=ast.Call(
                                ast.Attribute(
                                    ast.Name(self.compyner.static, ast.Load()),
                                    "get",
                                    ast.Load(),
                                ),
                                [ast.Constant(replace_import)],
                                [],
                            ),
                        ),
                        node,
                    )
                )
            else:
                new_imports.append(
                    ast.copy_location(
                        ast.Import([ast.alias(alias.name, self.compyner.tmp)]), node
                    )
                )
                if alias.asname != self.compyner.tmp:
                    new_imports.append(
                        ast.copy_location(
                            ast.Assign(
                                [
                                    (
                                        name_replacement(
                                            self.compyner,
                                            alias.asname or alias.name,
                                            alias,
                                            ast.Store(),
                                        )
                                        if glob
                                        else ast.copy_location(
                                            ast.Name(
                                                alias.asname or alias.name, ast.Store()
                                            ),
                                            node,
                                        )
                                    )
                                ],
                                ast.Name(self.compyner.tmp, ast.Load()),
                            ),
                            node,
                        )
                    )
        return new_imports

    def visit_Call(self, node: ast.Call):
        node.args = [self.visit(arg) for arg in node.args]
        node.keywords = [self.visit(kwarg) for kwarg in node.keywords]
        if (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "ComPYnerBuildTools"
        ):
            return getattr(ComPYnerBuildTools, node.func.attr)(self, node)

        node.func = self.visit(node.func)

        return node

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module == "compyner.typehints":
            return ast.Pass()
        new_imports = []
        if node.module is None:
            return self.visit(
                ast.copy_location(
                    ast.Import(
                        [
                            ast.alias(
                                name="." * node.level + alias.name,
                                asname=alias.asname or alias.name,
                            )
                            for alias in node.names
                        ]
                    ),
                    node,
                )
            )
        new_imports.append(
            self.visit_Import(
                ast.copy_location(
                    ast.Import(
                        [
                            ast.alias(
                                "." * node.level + node.module, self.compyner.tmp
                            ),
                        ],
                    ),
                    node,
                )
            )
        )
        if node.names[0].name == "*":
            new_imports.append(
                ast.copy_location(
                    ast.For(
                        target=ast.Name(self.compyner.tmp_sub, ast.Store()),
                        iter=ast.Name(self.compyner.tmp, ast.Store()),
                        body=[
                            ast.copy_location(
                                ast.Assign(
                                    targets=[
                                        ast.Subscript(
                                            value=ast.Call(
                                                ast.Name("globals", ast.Load()), [], []
                                            ),
                                            slice=ast.Name(
                                                self.compyner.tmp_sub, ast.Load()
                                            ),
                                            ctx=ast.Store(),
                                        )
                                    ],
                                    value=ast.Subscript(
                                        ast.Name(self.compyner.tmp, ast.Load()),
                                        ast.Name(self.compyner.tmp_sub, ast.Load()),
                                        ast.Load(),
                                    ),
                                ),
                                node,
                            )
                        ],
                        orelse=[],
                    ),
                    node,
                ),
            )
            return new_imports
        for alias in node.names:
            glob = self.check(alias.asname or alias.name, False)
            new_imports.append(
                ast.copy_location(
                    ast.Assign(
                        targets=[
                            (
                                name_replacement(
                                    self.compyner,
                                    alias.asname or alias.name,
                                    alias,
                                    ast.Store(),
                                )
                                if glob
                                else ast.copy_location(
                                    ast.Name(alias.asname or alias.name, ast.Store()),
                                    alias,
                                )
                            )
                        ],
                        value=ast.Attribute(
                            name_replacement(
                                self.compyner, self.compyner.tmp, node, ast.Load()
                            ),
                            alias.name,
                            ast.Load(),
                        ),
                    ),
                    alias,
                )
            )
        return new_imports


class Namer:
    def __init__(self):
        self.names = {}

    def get_unique_name(self, name: str):
        name = re.sub(r"\W", "_", name)
        self.names[name] = self.names.get(name, 0) + 1
        return name + ("_" + str(self.names[name]) if self.names[name] > 1 else "")

class ComPYner:
    def __init__(self, exclude=None, module_preprocessor=None):
        self.exclude = exclude or []
        self.loaded_modules = []
        self.result_module = ast.Module([*START.body], [])
        self.module_preprocessor = module_preprocessor or (lambda x, y: x)
        self.namer = Namer()
        self.static = self.namer.get_unique_name("_comPYned")
        self.tmp = self.namer.get_unique_name("_comPYned")
        self.tmp_sub = self.namer.get_unique_name("_comPYned")
        self.tmp_self = self.namer.get_unique_name("_comPYned")

    def load_module(self, name, parent=None):
        if name.split(".", 1)[0] in self.exclude:
            return False

        spec = importlib.util.find_spec(name, parent)
        return self._load_module(spec, name)

    def _load_module(self, spec, name=None):
        if not spec:
            raise ModuleNotFoundError(f"Module {name} not found")
        if spec.origin == "built-in":
            warnings.warn(
                f"Module {name} cannot be included: It is a built-in module. Excluded automatically, make sure it exists in the target environment."
            )
            return False
        if not spec.has_location:
            warnings.warn(
                f"Module {name} cannot be included: It does not have a location. Excluded automatically, make sure it exists in the target environment."
            )
            return False
        print(
            f"Loading module {name} as {spec.name} from {spec.origin}", file=sys.stderr
        )

        if spec.name not in self.loaded_modules:
            self.add_module(
                spec.name,
                ast_from_file(Path(spec.origin)),
                spec.parent,
                origin=spec.origin,
            )
        self.loaded_modules.append(spec.name)

        return spec.name

    def add_module(self, name: str, module: ast.Module, parent=None, origin=None):
        module = self.module_preprocessor(module, origin or name)
        gf = GlobalFinder()
        gf.visit(module)
        print(f"Globals in {name}:", file=sys.stderr)
        for glob, target in gf.globals:
            print(f"  {'.'.join(target + [glob])}", file=sys.stderr)
        if not gf.globals:
            print("   (none)", file=sys.stderr)
        tree = GlobalReplacer(self, gf.globals, parent=parent).visit(module)
        fname = self.get_unique_name("main" if name == "__main__" else "module_" + name)
        self.result_module.body.append(
            ast.FunctionDef(
                name=fname,
                args=ast.arguments(
                    args=[],
                    vararg=None,
                    kwonlyargs=[],
                    posonlyargs=[],
                    kw_defaults=[],
                    kwarg=None,
                    defaults=[],
                ),
                body=[
                    ast.Assign(
                        targets=[ast.Name(self.tmp_self, ast.Load())],
                        value=ast.Call(
                            func=ast.Attribute(
                                ast.Name(self.static, ast.Load()), "Module", ast.Load()
                            ),
                            args=[],
                            keywords=[],
                        ),
                        lineno=0,
                        col_offset=0,
                        end_lineno=0,
                        end_col_offset=0,
                    ),
                    ast.Assign(
                        targets=[
                            name_replacement(self, "__name__", tree, ast.Store()),
                            ast.Name(
                                "__name__",
                                ast.Store(),
                            ),
                        ],
                        value=ast.Constant(value=name),
                        lineno=0,
                        col_offset=0,
                        end_lineno=0,
                        end_col_offset=0,
                    ),
                    *tree.body,
                    ast.Return(
                        value=ast.Name(
                            self.tmp_self,
                            ast.Load(),
                            lineno=0,
                            col_offset=0,
                            end_lineno=0,
                            end_col_offset=0,
                        )
                    ),
                ],
                decorator_list=[],
                lineno=0,
                col_offset=0,
                end_lineno=0,
                end_col_offset=0,
            ),
        )
        self.result_module.body.append(
            ast.Assign(
                targets=[
                    ast.Subscript(
                        value=ast.Attribute(
                            ast.Name(self.static, ast.Load()), "modules", ast.Load()
                        ),
                        slice=ast.Constant(value=name),
                        ctx=ast.Store(),
                    )
                ],
                value=ast.Name(id=fname, ctx=ast.Load()),
                lineno=0,
                col_offset=0,
                end_lineno=0,
                end_col_offset=0,
            )
        )

    def compyne(self):
        self.result_module.body.extend(END.body)
        return ast.unparse(self.result_module)
