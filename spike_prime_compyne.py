import ast_comments as ast
import collections
from pathlib import Path
import sys
from compyner.engine import ComPYner, ast_from_file, Namer


SPIKE_PRIME_MODULES = [
    "array",
    "binascii",
    "builtins",
    "cmath",
    "collections",
    "errno",
    "gc",
    "hashlib",
    "heapq",
    "io",
    "json",
    "math",
    "os",
    "random",
    "re",
    "select",
    "struct",
    "sys",
    "time",
    "zlib",
    "bluetooth",
    "machine",
    "micropython",
    "uctypes",
    "__main__",
    "_onewire",
    "firmware",
    "hub",
    "uarray",
    "ubinascii",
    "ubluetooth",
    "ucollections",
    "uerrno",
    "uhashlib",
    "uheapq",
    "uio",
    "ujson",
    "umachine",
    "uos",
    "urandom",
    "ure",
    "uselect",
    "utime",
    "utimeq",
    "uzlib",
    "spike",
    "mindstorms",
    "hub",
    "runtime",
]


class PreOptimize(ast.NodeTransformer):
    def visit_FunctionDef(self, node):
        for arg in node.args.args:
            arg.annotation = None
        for arg in node.args.posonlyargs:
            arg.annotation = None
        for arg in node.args.kwonlyargs:
            arg.annotation = None
        node.returns = None
        node = self.generic_visit(node)
        node.body = [
            stmt
            for stmt in node.body
            if not (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant))
        ] or [ast.copy_location(ast.Pass(), node)]
        return node
    
    def visit_Comment(self, node):
        return None

    def visit_AnnAssign(self, node):
        if node.value:
            return self.generic_visit(
                ast.copy_location(
                    ast.Assign(targets=[node.target], value=node.value), node
                )
            )
        else:
            return None

    def visit_Module(self, node):
        node = self.generic_visit(node)
        node.body = [
            stmt
            for stmt in node.body
            if not (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant))
        ] or [ast.copy_location(ast.Pass(), node)]
        return node

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.ClassDef | ast.Assign:
        node = self.generic_visit(node)
        node.body = [
            stmt
            for stmt in node.body
            if not (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant))
        ] or [ast.copy_location(ast.Pass(), node)]

        if len(node.body) == 1 and len(node.bases) == 1:
            return ast.Assign(
                [ast.Name(node.name, ast.Store())],
                node.bases[0],
                lineno=0,
                col_offset=0,
            )
        return node


def pre_optimize(module, name):
    return PreOptimize().visit(module)


class PastOptimizeCounter(ast.NodeVisitor):
    def __init__(self):
        self.counter = collections.Counter()

    def visit_Constant(self, node: ast.Constant):
        if isinstance(node.value, bool):
            return
        if isinstance(node.value, (str, int, float)):
            self.counter[node.value] += 1


class PastOptimize(ast.NodeTransformer):
    def __init__(self, values_to_replace):
        self.values_to_replace = values_to_replace
        self.names = {}
        self.namer = Namer()
        
        
    # def visit_Comment(self, node: ast.Comment):
    #     if node.inline:
    #         return None

    def visit_Constant(self, node: ast.Constant):
        if isinstance(node.value, bool):
            return node
        if node.value not in self.values_to_replace:
            return node
        if node.value not in self.names:
            self.names[node.value] = self.namer.get_unique_name()
        return ast.copy_location(ast.Name(self.names[node.value]), node)

    def visit_Module(self, node: ast.Module):
        node = self.generic_visit(node)
        definitions = (
            []
        )  # [ast.ImportFrom("micropython", [ast.alias("const", "_const_")])]
        for value, name in self.names.items():
            definitions.append(
                ast.Assign(
                    [ast.Name(name)],
                    # ast.Call(
                    #     ast.Name("_const_"),
                    #     [
                    ast.Constant(value),
                    #         ],
                    #     [],
                    #     lineno=0,
                    #     col_offset=0,
                    # ),
                    lineno=0,
                    col_offset=0,
                )
            )
        node.body = definitions + node.body
        return node


def past_optimize(module):
    module = ast.parse(module)
    counter = PastOptimizeCounter()
    counter.visit(module)
    values_to_replace = [value for value, count in counter.counter.items() if count > 4]
    return ast.unparse(PastOptimize(values_to_replace).visit(module))


def spike_prime_compyne(input_module, slot=0, debug_build=False):
    sys.path.append(str(Path(input_module).parent))
    compyner = ComPYner(
        exclude=SPIKE_PRIME_MODULES,
        debug_stack=debug_build,# and False,
        debug_line=debug_build,# and False,
        split_modules=False,
        use_attr=True,
        module_preprocessor=pre_optimize,
        # pastprocessor=past_optimize,
        require_dunder_name=debug_build,
    )
    compyner.add_module("__main__", ast_from_file(Path(input_module)), origin=Path(input_module).absolute())
    code = f"# LEGO type:standard slot:{slot} autostart\n" + compyner.compyne()
    sys.path.pop()
    return code


def main():
    if len(sys.argv) < 2:
        print("Usage: python spike_prime_compyne.py <name> [<slot>]")
        sys.exit(1)
    input_module = sys.argv[1]
    slot = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    print(spike_prime_compyne(input_module, slot))


if __name__ == "__main__":
    main()
