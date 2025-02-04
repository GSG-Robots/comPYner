from collections import defaultdict
import ast_comments as ast
import importlib.util
from pathlib import Path
import re
import sys
from .logging import logger
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
    if name == gr.compyner.module_class_name or name == "ComPYnerBuildTools":
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


class CompileTimeReplacements:
    @staticmethod
    def glob_import(
        replacer: "TransformGlobals", node: ast.Call, /
    ) -> tuple[list[ast.AST], ast.AST]:
        args = [replacer.visit(arg) for arg in node.args]
        if len(args) != 1:
            raise ValueError("Import regex takes exactly one argument", args)
        if not isinstance(args[0], ast.Constant):
            raise TypeError(
                "The first argument of import_regex must be a constant.", args[0]
            )
        glob = args[0].value
        path = Path(sys.path[-1]).absolute()
        files = [file.absolute() for file in path.glob(glob)]
        names = [file.with_suffix("").name for file in files]
        prefix = []
        elts = []
        for name, file in zip(names, files):
            spec = importlib.util.spec_from_file_location(
                file.with_suffix("").name, file
            )
            do, code = replacer.compyner.import_module_from_spec(spec, spec.name)
            prefix.extend(code)
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

        return prefix, ast.List(
            elts=elts,
            ctx=ast.Load(),
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
        parent: str = None,
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

    def is_name_global(self, name, readonly):
        # check whether name is a global variable
        name = name.split(".")[0]
        ctx = self.context.copy()
        while ctx and readonly:
            if (name, ctx) in self.globals:
                return True
            ctx = ctx[:-1]
        return (name, ctx) in self.globals

    def visit_Name(self, node):
        # replace names if global
        if self.is_name_global(node.id, readonly=isinstance(node.ctx, ast.Load)):
            return name_replacement(self, node.id, node, node.ctx)

        return node

    def visit_Global(self, node: ast.Global):
        # remove global keyword
        return ast.Pass()

    def visit_FunctionDef(self, node):
        sub_replacer = TransformGlobals(
            self.compyner,
            self.globals,
            self.parent,
            self.context + [node.name],
            self.tmp_self,
        )
        node.body = [sub_replacer.visit(n) for n in node.body]
        node.decorator_list = [self.visit(n) for n in node.decorator_list]
        node.args = self.visit(node.args) if node.args else None

        if node.returns is not None:
            node.returns = self.visit(node.returns)

        if not self.is_name_global(node.name, False):
            return [
                self.set_line(node.lineno),
                node,
            ]

        # change name to temp name as args are impossible in func name
        original_name = node.name
        node.name = self.compyner.namer.get_unique_name("func_" + original_name)

        return [
            self.set_line(node.lineno),
            node,
            # reassign and delete temp var
            ast.copy_location(
                ast.Assign(
                    targets=[name_replacement(self, original_name, node, ast.Store())],
                    value=ast.Name(id=node.name, ctx=ast.Load()),
                ),
                node,
            ),
            ast.copy_location(
                ast.Delete(
                    [ast.Name(id=node.name, ctx=ast.Del())],
                ),
                node,
            ),
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

        if not self.is_name_global(node.name, False):
            return [
                self.set_line(node.lineno),
                node,
            ]

        # change name to temp name as args are impossible in class name
        original_name = node.name
        node.name = self.compyner.namer.get_unique_name("class_" + original_name)

        return [
            self.set_line(node.lineno),
            node,
            # reassign and delete temp var
            ast.copy_location(
                ast.Assign(
                    targets=[name_replacement(self, original_name, node, ast.Store())],
                    value=ast.Name(id=node.name, ctx=ast.Load()),
                ),
                node,
            ),
            ast.copy_location(
                ast.Delete(
                    [ast.Name(id=node.name, ctx=ast.Del())],
                ),
                node,
            ),
        ]

    def visit_Import(self, node: ast.Import):
        new_imports = []
        for alias in node.names:
            replace_import, body = self.compyner.import_module(alias.name, self.parent)
            new_imports.extend(body)
            glob = self.is_name_global(alias.asname or alias.name, False)
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
                                (ast.Name(self.compyner.module_class_name, ast.Load())),
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
                tmp_name = self.compyner.names_for_modules.get(
                    alias.name
                ) or self.compyner.namer.get_unique_name(
                    "import_" + (alias.asname or alias.name)
                )
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

    # def visit_Call(self, node: ast.Call):
    #     node.args = [self.visit(arg) for arg in node.args]
    #     node.keywords = [self.visit(kwarg) for kwarg in node.keywords]
    #     # if func is attr of anything called ComPYnerBuildTools, run it at compile time and replace call with reurn value
    #     if (
    #         isinstance(node.func, ast.Attribute)
    #         and isinstance(node.func.value, ast.Name)
    #         and node.func.value.id == "ComPYnerBuildTools"
    #     ):
    #         node = getattr(ComPYnerBuildTools, node.func.attr)(self, node)
    #         print(4, ast.unparse(node))
    #         return node

    #     node.func = self.visit(node.func)

    #     return node

    def visit_ImportFrom(self, node: ast.ImportFrom):
        # imports from compyner.typehints are dropped and ignored
        if node.module == "compyner.typehints":
            return ast.Pass()

        # from . import a or from .. import a
        if node.module is None:
            # import as if: import .a or import ..a
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

        # deny star-import
        if node.names[0].name == "*":
            raise ValueError(
                "Star imports are not supported, found at "
                + self.compyner.current_file
                + ":"
                + str(node.lineno)
            )

        new_imports = []
        # import parent module as tmp_name
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

        # assign each import to the specified asname
        for alias in node.names:
            glob = self.is_name_global(alias.asname or alias.name, False)
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
        # if typing.TYPE_CHECKING: is dropped and ignored
        match node.test:
            case ast.Attribute(ast.Name("typing"), "TYPE_CHECKING"):
                return
            case _:
                return self.generic_visit(node)

    def generic_visit(self, node: ast.stmt) -> list[ast.stmt]:
        # don't care for None
        if node is None:
            return None

        match node:
            case ast.Assign(
                value=ast.Call(
                    func=ast.Name(id="__glob_import__"),
                    args=[ast.Constant()],
                )
            ):
                prefix, val = CompileTimeReplacements.glob_import(self, node.value)
                return prefix + [
                    ast.copy_location(ast.Assign(targets=[self.visit(target) for target in node.targets], value=val), node)
                ]

        # Add lineno to statements
        if isinstance(node, ast.stmt):
            subnodes = super().generic_visit(node)
            if isinstance(subnodes, list):
                return [self.set_line(node.lineno), *subnodes]
            return [
                self.set_line(node.lineno),
                subnodes,
            ]
        return super().generic_visit(node)


class Namer:
    def __init__(self, prefix=None, keep_name=True, random_length=0):
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
        exclude_modules=None,
        module_preprocessor=None,
        pastprocessor=None,
        require_dunder_name=False,
        keep_names=True,
        random_name_length=0,
    ):
        self.exclude_modules = exclude_modules or []
        self.loaded_modules = []
        self.current_modules = []
        self.module_preprocessor = module_preprocessor or (lambda x, y: x)
        self.pastprocessor = pastprocessor or (lambda x: x)
        self.namer = Namer(
            keep_name=keep_names, random_length=random_name_length, prefix="c"
        )
        self.require_dunder_name = require_dunder_name
        self.module_class_name = self.namer.get_unique_name("Module")
        self.names_for_modules = {}
        self.current_file = "<comPYned>"

    def set_file(self, file: Path | str) -> ast.Comment:
        return ast.Comment(f"##{str(file)}##", inline=False)

    def set_line(self, line: int) -> ast.Comment:
        return ast.Comment(f"##{self.current_file}:{line}##", inline=False)

    def import_module(self, name: str, parent: str = None) -> bool:
        # If top parent is excluded, do not import module
        if name.split(".", 1)[0] in self.exclude_modules:
            return False, []

        # look for polyfill
        try:
            special_spec = importlib.util.find_spec("compyned_polyfills." + name)
            if special_spec:
                return self.import_module_from_spec(special_spec, name)
        except ModuleNotFoundError:
            pass

        # get spec and go from there
        spec = importlib.util.find_spec(name, parent)
        return self.import_module_from_spec(spec, name)

    def import_module_from_spec(self, spec, name=None) -> tuple[str, list[ast.stmt]]:
        # spec is None => Module not found
        if not spec:
            raise ModuleNotFoundError(f"Module {name} not found")

        # Warn about builtin modules
        if spec.origin == "built-in":
            logger.warning(
                "Module %s cannot be included: It is a built-in module. Excluded automatically, make sure it exists in the target environment.",
                name,
            )
            return False, []
        if not spec.has_location:
            logger.warning(
                "Module %s cannot be included: It does not have a location. Excluded automatically, make sure it exists in the target environment.",
                name,
            )
            return False, []

        # Error out over recursive import
        if spec.name in self.current_modules:
            raise RecursionError(
                f"Recursive import detected: {' > '.join(self.current_modules)} >> {spec.name}"
            )

        # if not imported before
        if spec.name not in self.loaded_modules:
            # build module and return for insertion
            self.current_modules.append(spec.name)
            body = self.transform_module(
                spec.name,
                ast_from_file(Path(spec.origin)),
                spec.parent,
                origin=spec.origin,
            )
            self.current_modules.pop()
            self.loaded_modules.append(spec.name)
            return spec.name, body

        return spec.name, []

    def transform_module(
        self, name: str, module: ast.Module, parent: str = None, origin: str = None
    ):
        # Simplify name
        simple_path = (
            Path(origin).absolute().relative_to(Path.cwd()).as_posix()
            if origin
            else name
        )
        logger.info("Adding %-15s from %s", name, simple_path)

        module = self.module_preprocessor(module, origin or name)

        # Discorver globals
        gf = DiscoverGlobals()
        gf.visit(module)

        module_varname = self.namer.get_unique_name("module_" + name)

        # Transform globals
        old_file = self.current_file
        self.current_file = simple_path
        tree = TransformGlobals(
            self, gf.globals, parent=parent, tmp_self=module_varname
        ).visit(module)
        self.current_file = old_file

        # Store module as already imported for later access
        self.names_for_modules[name] = module_varname

        # Produce transformed module
        return [
            # Set file path for debug
            self.set_file(simple_path),
            # Create Module object
            ast.Assign(
                targets=[ast.Name(module_varname, ast.Load())],
                value=ast.Call(
                    func=(ast.Name(self.module_class_name, ast.Load())),
                    args=(
                        [ast.Constant(value=name)]
                        if gf.has_dunder_name or self.require_dunder_name
                        else []
                    ),
                    keywords=[],
                ),
                lineno=0,
                col_offset=0,
                end_lineno=0,
                end_col_offset=0,
            ),
            # Module body
            *tree.body,
        ]

    def compyne_from_ast(
        self,
        name: str,
        module: ast.Module,
        parent: str = None,
        origin: str = None,
    ):
        return self.pastprocessor(
            NoneFriendlyUnparser().visit(
                ast.Module(
                    [
                        ast.ClassDef(
                            name=self.module_class_name,
                            bases=[ast.Name("dict", ast.Load())],
                            keywords=[],
                            body=[*(MODULE_CLASS_BODY).body],
                            decorator_list=[],
                            lineno=0,
                            col_offset=0,
                            end_lineno=0,
                            end_col_offset=0,
                        ),
                        *self.transform_module(name, module, parent, origin),
                    ],
                    [],
                )
            )
        )


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
