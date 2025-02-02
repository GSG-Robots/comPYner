from collections import defaultdict
import ast_comments as ast
import importlib.util
from pathlib import Path
import re
import sys
import logging
import random
import string


class NoneFriendlyUnparser(ast._Unparser):
    def generic_visit(self, node):
        if node is None:
            return
        return super().generic_visit(node)


def name_replacement(
    gr: "TransformGlobals", name: str, original_node: ast.AST, ctx: ast.expr_context
) -> ast.Attribute:
    if name == gr.compyner.static or name == "ComPYnerBuildTools":
        return ast.copy_location(ast.Name(id=name, ctx=ctx), original_node)
    attr = ast.Attribute(
        value=ast.Name(gr.tmp_self, ast.Load()),
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


MODULE_CLASS_BODY = ast_from_file(path_from_module("compyner.snippets.module"))


class ComPYnerBuildTools:
    @staticmethod
    def get_modules_path_glob(
        replacer: "TransformGlobals", node: ast.Call, /
    ) -> list[ast.AST]:

        args = [replacer.visit(arg) for arg in node.args]
        if len(args) != 1:
            raise ValueError("Import regex takes exaclty one argument", args)
        if not isinstance(args[0], ast.Constant):
            raise TypeError(
                "The first argument of import_regex must be a constant.", args[0]
            )
        glob = args[0].value
        path = Path(sys.path[-1]).absolute()
        files = [file.absolute() for file in path.glob(glob)]
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
                    (ast.Name(replacer.compyner.names_for_modules[name])),
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


class DiscoverGlobals(ast.NodeVisitor):
    def __init__(self, explicit_only=False, context=None):
        super().__init__()
        self.globals = []
        self.explicit_only = explicit_only
        self.context = context or []
        self.has_dunder_name = False

    def add(self, name):
        if name not in self.globals:
            self.globals.append((name, self.context))

    def visit_Name(self, node: ast.Name):
        if node.id == "__name__":
            self.has_dunder_name = True
            self.add(node.id)
        if self.explicit_only:
            return
        if isinstance(node.ctx, ast.Store):
            self.add(node.id)

    def visit_If(self, node: ast.If):
        match node.test:
            case ast.Attribute(ast.Name("typing"), "TYPE_CHECKING"):
                return
            case _:
                return self.generic_visit(node)

    def visit_Global(self, node):
        for name in node.names:
            self.add(name)

    def visit_FunctionDef(self, node):
        if not self.explicit_only:
            self.add(node.name)
        global_finder = DiscoverGlobals(
            explicit_only=True, context=self.context + [node.name]
        )
        if global_finder.has_dunder_name:
            self.has_dunder_name = True
        for subnode in node.body:
            global_finder.visit(subnode)
        for decorator in node.decorator_list:
            self.visit(decorator)
        self.globals.extend(global_finder.globals)

    def visit_ClassDef(self, node):
        if not self.explicit_only:
            self.add(node.name)
        global_finder = DiscoverGlobals(
            explicit_only=True, context=self.context + [node.name]
        )
        if global_finder.has_dunder_name:
            self.has_dunder_name = True
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


class TransformGlobals(ast.NodeTransformer):
    def __init__(
        self,
        compyner: "ComPYner",
        globals_,
        parent: "TransformGlobals" = None,
        context=None,
        tmp_self=None,
    ):
        super().__init__()
        self.globals = globals_
        self.compyner = compyner
        self.parent = parent
        self.context = context or []
        self.tmp_self = tmp_self or "_comPYned_SELF"

    def set_line(self, line):
        return self.compyner.set_line(line)

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
            return name_replacement(self, node.id, node, node.ctx)

        return node

    def visit_Global(self, node: ast.Global):
        return ast.Pass()

    def visit_Return(self, node: ast.Return):
        node.value = self.visit(node.value)
        return [
            self.set_line(node.lineno),
            node,
        ]

    def visit_FunctionDef(self, node):
        sub_replacer = TransformGlobals(
            self.compyner,
            self.globals,
            self.parent,
            self.context + [node.name],
            self.tmp_self,
        )
        original_name = node.name
        node.name = self.compyner.namer.get_unique_name("func_" + original_name)
        node.body = [sub_replacer.visit(n) for n in node.body]
        node.decorator_list = [self.visit(n) for n in node.decorator_list]
        node.args = self.visit(node.args) if node.args else None

        if node.returns is not None:
            node.returns = self.visit(node.returns)

        if self.check(original_name, False):
            return [
                self.set_line(node.lineno),
                node,
                ast.copy_location(
                    ast.Assign(
                        targets=[name_replacement(self, original_name, node, ast.Store())],
                        value=ast.Name(id=node.name, ctx=ast.Load()),
                    ),
                    node,
                ),
                # TODO
                ast.copy_location(
                    ast.Delete(
                        [ast.Name(id=node.name, ctx=ast.Del())],
                    ),
                    node,
                ),
            ]
        else:
            return [
                self.set_line(node.lineno),
                node,
            ]

    def visit_ClassDef(self, node: ast.ClassDef):
        sub_replacer = TransformGlobals(
            self.compyner,
            self.globals,
            self.parent,
            self.context + [node.name],
            self.tmp_self,
        )
        node.body = [sub_replacer.visit(n) for n in node.body]
        node.bases = [self.visit(n) for n in node.bases]
        original_name = node.name
        node.name = self.compyner.namer.get_unique_name("class_" + original_name)

        if self.check(original_name, False):
            return [
                self.set_line(node.lineno),
                node,
                ast.copy_location(
                    ast.Assign(
                        targets=[name_replacement(self, original_name, node, ast.Store())],
                        value=ast.Name(id=node.name, ctx=ast.Load()),
                    ),
                    node,
                ),
                # TODO
                ast.copy_location(
                    ast.Delete(
                        [ast.Name(id=node.name, ctx=ast.Del())],
                    ),
                    node,
                ),
            ]
        else:
            return [
                self.set_line(node.lineno),
                node,
            ]

    def visit_Import(self, node: ast.Import):
        new_imports = []
        for alias in node.names:
            replace_import = self.compyner.load_module(alias.name, self.parent)
            tmp_name = (
                self.compyner.names_for_modules.get(alias.name)
                or self.compyner.namer.get_unique_name("import_" + (alias.asname or alias.name))
            )
            glob = self.check(alias.asname or alias.name, False)
            parts = (alias.asname or alias.name).split(".")
            for part in range(len(parts) - 1):
                new_imports.append(
                    ast.copy_location(
                        ast.Assign(
                            targets=[
                                name_replacement(
                                    self,
                                    ".".join(parts[: part + 1]),
                                    alias,
                                    ast.Store(),
                                )
                            ],
                            value=ast.Call(
                                (ast.Name(self.compyner.static, ast.Load())),
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
                                        self,
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
                            value=(
                                ast.Name(
                                    self.compyner.names_for_modules[replace_import]
                                )
                            ),
                        ),
                        node,
                    )
                )
            else:
                new_imports.append(
                    ast.copy_location(
                        ast.Import([ast.alias(alias.name, tmp_name)]), node
                    )
                )
                if alias.asname != tmp_name:
                    new_imports.append(
                        ast.copy_location(
                            ast.Assign(
                                [
                                    (
                                        name_replacement(
                                            self,
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
                                ast.Name(tmp_name, ast.Load()),
                            ),
                            node,
                        )
                    )
        return [
            self.set_line(node.lineno),
            new_imports,
        ]

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
        
        if node.names[0].name == "*":
            raise ValueError("Star imports are not supported, found at " + self.compyner.current_file + ":" + str(node.lineno))
        
        new_imports = []
        tmp_module = self.compyner.namer.get_unique_name("import_" + node.module)
        new_imports.append(
            self.visit_Import(
                ast.copy_location(
                    ast.Import(
                        [
                            ast.alias("." * node.level + node.module, tmp_module),
                        ],
                    ),
                    node,
                )
            )
        )
        
        for alias in node.names:
            glob = self.check(alias.asname or alias.name, False)
            new_imports.append(
                ast.copy_location(
                    ast.Assign(
                        targets=[
                            (
                                name_replacement(
                                    self,
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
                            ast.Name(tmp_module, ast.Load()),
                            alias.name,
                            ast.Load(),
                        ),
                    ),
                    alias,
                )
            )
        return new_imports

    def visit_If(self, node: ast.If):
        match node.test:
            case ast.Attribute(ast.Name("typing"), "TYPE_CHECKING"):
                return
            case _:
                return self.generic_visit(node)

    def generic_visit(self, node: ast.stmt) -> list[ast.stmt]:
        if node is None:
            return None
        if isinstance(node, ast.stmt):
            return [
                self.set_line(node.lineno),
                super().generic_visit(node),
            ]
        return super().generic_visit(node)


class Namer:
    def __init__(self, prefix=None, keep_name=True, random_length=0):#4):
        self.taken_names = defaultdict(int)
        self.prefix = prefix or ""
        self.keep_name = keep_name
        self.random_length = random_length

    def generate_random_string(self):
        return "".join(
            random.choices(
                string.ascii_letters + string.digits + "_", k=self.random_length
            )
        )

    def get_unique_name(self, name: str = ""):
        parts = [self.prefix]
        if self.keep_name and name:
            parts.append(re.sub(r"\W", "_", name))
        if self.random_length:
            parts.append(self.generate_random_string())
        new_name = "_".join(parts)
        self.taken_names[new_name] += 1
        if self.taken_names[new_name] > 1:
            new_name += "_" + str(self.taken_names[new_name])
        return new_name


class ComPYner:
    def __init__(
        self,
        exclude=None,
        module_preprocessor=None,
        debug_stack=False,
        debug_line=False,
        split_modules=True,
        pastprocessor=None,
        require_dunder_name=False,
    ):
        self.exclude = exclude or []
        self.loaded_modules = []
        self.current_modules = []
        self.result_module = ast.Module([], [])
        self.module_preprocessor = module_preprocessor or (lambda x, y: x)
        self.pastprocessor = pastprocessor or (lambda x: x)
        self.namer = Namer()  # "_CPYD")
        self.names = {}
        self.require_dunder_name = require_dunder_name
        self.static = self.namer.get_unique_name()
        internals = self.namer.get_unique_name()
        self.names_for_modules = {}
        self.result_module.body.append(
            ast.ClassDef(
                name=internals,
                bases=[ast.Name("dict", ast.Load())],
                keywords=[],
                body=[*(MODULE_CLASS_BODY).body],
                decorator_list=[],
                lineno=0,
                col_offset=0,
                end_lineno=0,
                end_col_offset=0,
            )
        )
        self.static = internals
        self.stack_var = self.namer.get_unique_name()
        self.current_file = "<comPYned>"
        if debug_stack:
            self.result_module.body.append(
                ast.Assign(
                    targets=[ast.Name(self.stack_var, ast.Store())],
                    value=ast.List(elts=[], ctx=ast.Load()),
                    lineno=0,
                    col_offset=0,
                    end_lineno=0,
                    end_col_offset=0,
                )
            )
        self.debug_stack = debug_stack
        self.debug_line = debug_line and debug_stack
        self.split_modules = split_modules

    def set_file(self, file):
        return ast.Comment(f"##{str(file)}##", inline=False)

    def set_line(self, line):
        return ast.Comment(f"##{self.current_file}:{line}##", inline=False)

    def load_module(self, name, parent=None):
        if name.split(".", 1)[0] in self.exclude:
            return False

        try:
            special_spec = importlib.util.find_spec("compyned_polyfills." + name)
            if special_spec:
                return self._load_module(special_spec, name)
        except ModuleNotFoundError:
            pass

        spec = importlib.util.find_spec(name, parent)
        return self._load_module(spec, name)

    def _load_module(self, spec, name=None):
        if not spec:
            raise ModuleNotFoundError(f"Module {name} not found")
        if spec.origin == "built-in":
            logging.warning(
                "Module %s cannot be included: It is a built-in module. Excluded automatically, make sure it exists in the target environment.",
                name,
            )
            return False
        if not spec.has_location:
            logging.warning(
                "Module %s cannot be included: It does not have a location. Excluded automatically, make sure it exists in the target environment.",
                name,
            )
            return False

        if spec.name in self.current_modules:
            raise RecursionError(
                f"Recursive import detected: {' > '.join(self.current_modules)} >> {spec.name}"
            )

        if spec.name not in self.loaded_modules:
            self.current_modules.append(spec.name)
            self.add_module(
                spec.name,
                ast_from_file(Path(spec.origin)),
                spec.parent,
                origin=spec.origin,
            )
            self.current_modules.pop()
        self.loaded_modules.append(spec.name)

        return spec.name

    def add_module(self, name: str, module: ast.Module, parent=None, origin=None):
        # Simplify name
        simple_name = (
            Path(origin).relative_to(Path.cwd()).as_posix() if origin else name
        )
        module = self.module_preprocessor(module, origin or name)
        gf = DiscoverGlobals()
        gf.visit(module)

        logging.info("Adding module %s from %s", name, simple_name)

        tmp_self = self.namer.get_unique_name("module_" + name)
        old_file = self.current_file
        file_set = self.set_file(simple_name)
        self.current_file = str(simple_name)
        tree = TransformGlobals(
            self, gf.globals, parent=parent, tmp_self=tmp_self
        ).visit(module)
        self.current_file = old_file
        fname = self.namer.get_unique_name(
            "load_" + name
        )
        if self.split_modules:
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
                        file_set,
                        (
                            ast.Assign(
                                targets=[ast.Name(tmp_self, ast.Load())],
                                value=ast.Call(
                                    func=(ast.Name(self.static, ast.Load())),
                                    args=[],
                                    keywords=[],
                                ),
                                lineno=0,
                                col_offset=0,
                                end_lineno=0,
                                end_col_offset=0,
                            )
                        ),
                        (
                            ast.Assign(
                                targets=[
                                    (
                                        ast.Attribute(
                                            value=ast.Name(tmp_self, ast.Load()),
                                            attr="__name__",
                                            ctx=ast.Store(),
                                        )
                                    )
                                ],
                                value=ast.Constant(value=name),
                                lineno=0,
                                col_offset=0,
                                end_lineno=0,
                                end_col_offset=0,
                            )
                            if gf.has_dunder_name or self.require_dunder_name
                            else None
                        ),
                        *tree.body,
                        ast.Return(
                            value=ast.Name(
                                tmp_self,
                                ast.Load(),
                                lineno=0,
                                col_offset=0,
                                end_lineno=0,
                                end_col_offset=0,
                            ),
                            lineno=0,
                            col_offset=0,
                            end_lineno=0,
                            end_col_offset=0,
                        ),
                    ],
                    decorator_list=[],
                    lineno=0,
                    col_offset=0,
                    end_lineno=0,
                    end_col_offset=0,
                ),
            )

            assign = ast.Assign(
                targets=[ast.Name(tmp_self, ast.Load())],
                value=ast.Call(
                    ast.Name(id=fname, ctx=ast.Load()),
                    [],
                    [],
                    lineno=0,
                    col_offset=0,
                    end_lineno=0,
                    end_col_offset=0,
                ),
                lineno=0,
                col_offset=0,
                end_lineno=0,
                end_col_offset=0,
            )
            self.names_for_modules[name] = tmp_self

        else:
            self.result_module.body.extend(
                [
                    file_set,
                    ast.Assign(
                        targets=[ast.Name(tmp_self, ast.Load())],
                        value=ast.Call(
                            func=(ast.Name(self.static, ast.Load())),
                            args=[],
                            keywords=[],
                        ),
                        lineno=0,
                        col_offset=0,
                        end_lineno=0,
                        end_col_offset=0,
                    ),
                    (
                        ast.Assign(
                            targets=[
                                (
                                    ast.Attribute(
                                        value=ast.Name(tmp_self, ast.Load()),
                                        attr="__name__",
                                        ctx=ast.Store(),
                                    )
                                ),
                            ],
                            value=ast.Constant(value=name),
                            lineno=0,
                            col_offset=0,
                            end_lineno=0,
                            end_col_offset=0,
                        )
                        if gf.has_dunder_name or self.require_dunder_name
                        else None
                    ),
                    *tree.body,
                ]
            )
            assign = None
            self.names_for_modules[name] = tmp_self

        if not assign:
            return
        if name == "__main__" and (self.debug_stack or self.debug_line):
            error_name = self.namer.get_unique_name()
            self.result_module.body.append(
                ast.Try(
                    body=[assign],
                    handlers=[
                        ast.ExceptHandler(
                            type=ast.Name("Exception", ast.Load()),
                            name=error_name,
                            body=[
                                ast.Expr(
                                    ast.Call(
                                        ast.Name("print", ast.Load()),
                                        [
                                            # ast.Constant("Error at: "),
                                            # ast.Subscript(
                                            #     ast.Name(self.stack_var, ast.Load()),
                                            #     ast.Index(ast.Constant("file")),
                                            #     ast.Load(),
                                            # ),
                                            # ast.Constant(":"),
                                            # ast.Subscript(
                                            #     ast.Name(self.metadata_var, ast.Load()),
                                            #     ast.Index(ast.Constant("line")),
                                            #     ast.Load(),
                                            # ),
                                            # ast.Subscript(
                                            #     ast.Name(self.metadata_var, ast.Load()),
                                            #     ast.Index(ast.Constant("stack")),
                                            #     ast.Load(),
                                            # ),
                                            ast.Name(self.stack_var, ast.Load()),
                                        ],
                                        [
                                            # ast.keyword(
                                            #     arg="sep", value=ast.Constant("")
                                            # ),
                                        ],
                                        lineno=0,
                                        col_offset=0,
                                        end_lineno=0,
                                        end_col_offset=0,
                                    ),
                                    lineno=0,
                                    col_offset=0,
                                    end_lineno=0,
                                    end_col_offset=0,
                                ),
                                ast.Raise(
                                    exc=ast.Name(error_name, ast.Load()),
                                    cause=None,
                                    lineno=0,
                                    col_offset=0,
                                    end_lineno=0,
                                    end_col_offset=0,
                                ),
                            ],
                        )
                    ],
                    orelse=[],
                    finalbody=[],
                    lineno=0,
                    col_offset=0,
                    end_lineno=0,
                    end_col_offset=0,
                )
            )
            return
        self.result_module.body.append(assign)

    def compyne(self):
        return self.pastprocessor(NoneFriendlyUnparser().visit(self.result_module))


class LocationSearcher(ast.NodeVisitor):
    def __init__(self):
        self.lineno_map = {}
        self.location = "<comPYned>"

    def visit_Comment(self, node):
        if (
            isinstance(node, ast.Comment)
            and node.value.startswith("##")
            and node.value.endswith("##")
        ):
            self.location = node.value[2:-2]

    def generic_visit(self, node: ast.AST) -> ast.AST:
        if isinstance(node, ast.stmt):
            self.lineno_map[node.lineno] = self.location
        return super().generic_visit(node)


def get_lineno_map(module: ast.Module):
    searcher = LocationSearcher()
    searcher.visit(module)
    return searcher.lineno_map


class CommentRemover(ast.NodeTransformer):
    def generic_visit(self, node: ast.AST) -> ast.AST:
        if isinstance(node, ast.Comment):
            return None
        return super().generic_visit(node)


def without_comments(): ...
