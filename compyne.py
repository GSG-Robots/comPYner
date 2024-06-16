import ast
import importlib.util
from pathlib import Path
import sys
import warnings


def name_replacement(
    name: str, original_node: ast.AST, ctx: ast.expr_context
) -> ast.Attribute:
    if name.startswith("__comPYned_"):
        return ast.copy_location(ast.Name(id=name, ctx=ctx), original_node)
    attr = ast.Attribute(
        value=ast.Name(id="__comPYned_SELF", ctx=ast.Load()), attr=name, ctx=ctx
    )
    attr = ast.copy_location(attr, original_node)
    return attr


def ast_from_file(file_path: Path) -> ast.Module:
    with file_path.open() as f:
        code = f.read()
    return ast.parse(code)


START = ast_from_file(Path("comPYned_snippets/start.py"))
END = ast_from_file(Path("comPYned_snippets/end.py"))


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
            self.add(alias.asname or alias.name)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if self.explicit_only:
            return
        for alias in node.names:
            self.add(alias.asname or alias.name)


class GlobalReplacer(ast.NodeTransformer):
    def __init__(self, compyner: "ComPYner", globals, parent=None, context=None):
        super().__init__()
        self.globals = globals
        self.compyner = compyner
        self.parent = parent
        self.context = context or []

    def check(self, name, readonly):
        ctx = self.context.copy()
        while ctx and readonly:
            if (name, ctx) in self.globals:
                return True
            ctx = ctx[:-1]
        return (name, ctx) in self.globals

    def visit_Name(self, node):
        print(
            self.context,
            node.id,
            self.check(node.id, readonly=isinstance(node.ctx, ast.Load)),
            file=sys.stderr,
        )
        if self.check(node.id, readonly=isinstance(node.ctx, ast.Load)):
            return name_replacement(node.id, node, node.ctx)
        return node

    def visit_Global(self, node: ast.Global):
        return ast.Pass()

    def visit_FunctionDef(self, node):
        sub_replacer = GlobalReplacer(
            self.compyner, self.globals, self.parent, self.context + [node.name]
        )
        node.body = [sub_replacer.visit(n) for n in node.body]
        node.decorator_list = [self.visit(n) for n in node.decorator_list]

        if self.check(node.name, False):
            return [
                node,
                ast.copy_location(
                    ast.Assign(
                        targets=[name_replacement(node.name, node, ast.Store())],
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
        if self.check(node.name, False):
            return [
                node,
                ast.copy_location(
                    ast.Assign(
                        targets=[name_replacement(node.name, node, ast.Store())],
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
            print(ast.dump(node), file=sys.stderr)
            replace_import = self.compyner.load_module(alias.name, self.parent)
            glob = self.check(alias.asname or alias.name, False)
            if replace_import:
                new_imports.append(
                    ast.copy_location(
                        ast.Assign(
                            targets=[
                                (
                                    name_replacement(
                                        alias.asname or alias.name, alias, ast.Store()
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
                                ast.Name(id="__comPYned_import", ctx=ast.Load()),
                                [ast.Constant(replace_import)],
                                [],
                            ),
                        ),
                        node,
                    )
                )
            else:
                new_imports.append(
                    ast.copy_location(ast.Import([ast.alias(alias.name, "_")]), node)
                )
                new_imports.append(
                    ast.copy_location(
                        ast.Assign(
                            [
                                (
                                    name_replacement(
                                        alias.asname or alias.name, alias, ast.Store()
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
                            ast.Name("_", ast.Load()),
                        ),
                        node,
                    )
                )
        return new_imports

    def visit_ImportFrom(self, node: ast.ImportFrom):
        new_imports = []
        new_imports.append(
            self.visit_Import(
                ast.copy_location(
                    ast.Import(
                        [
                            ast.alias("." * node.level + node.module, "__comPYned_tmp"),
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
                        target=ast.Name("__comPYned_sub", ast.Store()),
                        iter=ast.Name("__comPYned_tmp", ast.Store()),
                        body=[
                            ast.copy_location(
                                ast.Assign(
                                    targets=[
                                        ast.Subscript(
                                            value=ast.Call(
                                                ast.Name("globals", ast.Load()), [], []
                                            ),
                                            slice=ast.Name(
                                                "__comPYned_sub", ast.Load()
                                            ),
                                            ctx=ast.Store(),
                                        )
                                    ],
                                    value=ast.Subscript(
                                        ast.Name("__comPYned_tmp", ast.Load()),
                                        ast.Name("__comPYned_sub", ast.Load()),
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
                                    alias.asname or alias.name, alias, ast.Store()
                                )
                                if glob
                                else ast.copy_location(
                                    ast.Name(alias.asname or alias.name, ast.Store()),
                                    alias,
                                )
                            )
                        ],
                        value=ast.Attribute(
                            name_replacement("__comPYned_tmp", node, ast.Load()),
                            alias.name,
                            ast.Load(),
                        ),
                    ),
                    alias,
                )
            )
        return new_imports


class ComPYner:
    def __init__(self, exclude=None):
        self.exclude = exclude or []
        self.loaded_modules = []
        self.result_module = ast.Module([*START.body], [])

    def load_module(self, name, parent=None):
        if name.split(".", 1)[0] in self.exclude:
            return False

        print(name, parent, file=sys.stderr)
        spec = importlib.util.find_spec(name, parent)
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

        print(spec.name, file=sys.stderr)
        if spec.name not in self.loaded_modules:
            self.add_module(spec.name, ast_from_file(Path(spec.origin)), spec.parent)
        self.loaded_modules.append(spec.name)

        return spec.name

    def add_module(self, name: str, module: ast.Module, parent=None):
        gf = GlobalFinder()
        gf.visit(module)
        tree = GlobalReplacer(self, gf.globals, parent=parent).visit(module)
        self.result_module.body.append(
            ast.FunctionDef(
                name="module",
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
                        targets=[ast.Name(id="__comPYned_SELF", ctx=ast.Store())],
                        value=ast.Call(
                            func=ast.Name(id="__comPYned_DotDict", ctx=ast.Load()),
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
                            name_replacement("__name__", tree, ast.Store()),
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
                            id="__comPYned_SELF",
                            ctx=ast.Load(),
                            lineno=0,
                            col_offset=0,
                            end_lineno=0,
                            end_col_offset=0,
                        ),
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
                        value=ast.Name(id="__comPYned_modules", ctx=ast.Load()),
                        slice=ast.Constant(value=name),
                        ctx=ast.Store(),
                    )
                ],
                value=ast.Name(id="module", ctx=ast.Load()),
                lineno=0,
                col_offset=0,
                end_lineno=0,
                end_col_offset=0,
            )
        )

    def compyne(self):
        self.result_module.body.extend(END.body)
        return ast.unparse(self.result_module)


def compyne(path, exclude=None):
    compyner = ComPYner(exclude)
    compyner.add_module("__main__", ast_from_file(Path(path)))
    return compyner.compyne()


if __name__ == "__main__":
    print(
        compyne(
            sys.argv[1],
            exclude=sys.argv[2:],
        )
    )
