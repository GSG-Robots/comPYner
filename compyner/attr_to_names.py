import pathlib
from typing import Any
import ast_comments as ast


class AttrToNames(ast.NodeTransformer):
    def __init__(self, module_class: str = None):
        self.modules = []
        self.module_alias = {}
        self.names = []

        self.module_class = module_class

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.ClassDef:
        if self.module_class is None:
            self.module_class = node.name
            return None
        return self.generic_visit(node)

    def generic_visit(self, node: ast.AST) -> ast.AST:
        unparsed = ast.unparse(node)
        if unparsed in self.module_alias:
            return ast.Name(self.module_alias[unparsed], ast.Load())
        return super().generic_visit(node)

    def visit_Assign(self, node: ast.Assign):
        if ast.unparse(node.value) in self.module_alias:
            for target in node.targets:
                self.module_alias[ast.unparse(target)] = self.module_alias[
                    ast.unparse(node.value)
                ]
                return None
        if len(node.targets) == 1:
            match node.value:
                case ast.Call(ast.Name(self.module_class, ast.Load()), [], []):
                    if not isinstance(node.targets[0], ast.Name):
                        raise NotImplementedError
                    self.modules.append(node.targets[0].id)
                    self.module_alias[node.targets[0].id] = node.targets[0].id
                    return None
        return self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> ast.Attribute | ast.Name:
        if ast.unparse(node.value) in self.module_alias:
            self.names.append(
                f"{self.module_alias[ast.unparse(node.value)]}_{node.attr}"
            )
            return ast.Name(f"{self.module_alias[ast.unparse(node.value)]}_{node.attr}")
        return self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> ast.Name:
        if node.id in self.modules:
            return ast.Constant(0)
        return self.generic_visit(node)

    def visit_Module(self, node: ast.Module) -> ast.Module:
        node = self.generic_visit(node)
        new_body = []
        index = 0
        while index < len(node.body) - 1:
            item = node.body[index]
            next_item = node.body[index + 1]
            if (
                isinstance(item, (ast.FunctionDef, ast.ClassDef))
                and isinstance(next_item, ast.Assign)
                and len(next_item.targets) == 1
                and isinstance(next_item.targets[0], ast.Name)
                and isinstance(next_item.value, ast.Name)
                and next_item.value.id == item.name
            ):
                item.name = next_item.targets[0].id
                index += 1
            index += 1
            new_body.append(item)
        node.body = [
            ast.FunctionDef(
                "main",
                ast.arguments([], [], [], [], [], [], []),
                new_body,
                [],
                lineno=0,
                col_offset=0,
            ),
            ast.Expr(
                ast.Call(ast.Name("main", ast.Load()), [], []), lineno=0, col_offset=0
            ),
        ]
        return node


# inp = pathlib.Path(
#     r"C:\Users\Johannes\Documents\GitHub\competition-programs/src/main.cpyd.py"
# )
# out = pathlib.Path(
#     r"C:\Users\Johannes\Documents\GitHub\competition-programs/src/main.atn.py"
# )

# out.write_text(ast.unparse(AttrToNames().visit(ast.parse(inp.read_text()))))
