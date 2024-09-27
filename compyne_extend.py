import ast
from typing import Callable, Optional
import warnings
import sys
from compyner.engine import ComPYner
from pathlib import Path
from argparse import ArgumentParser, FileType


class FindEnabledFeatures(ast.NodeTransformer):
    def __init__(self):
        self.trigger_words = {}

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module == "compyner_ext_features":
            for alias in node.names:
                self.trigger_words[alias.name] = alias.asname or alias.name
            return None
        return node


class AutoMainName(ast.NodeTransformer):
    def __init__(self, trigger_word="__main__"):
        self.trigger_word = trigger_word

    def visit_FunctionDef(self, node):
        found = False
        for dec in node.decorator_list.copy():
            if isinstance(dec, ast.Name) and dec.id == self.trigger_word:
                node.decorator_list.remove(dec)
                found = True
        if not found:
            return node
        node.args = self.visit(node.args) if node.args else None
        node.body = [self.visit(stmt) for stmt in node.body]
        node.decorator_list = [self.visit(dec) for dec in node.decorator_list]
        return [
            node,
            ast.If(
                ast.Compare(
                    left=ast.Name(id="__name__", ctx=ast.Load()),
                    ops=[ast.Eq()],
                    comparators=[ast.Constant(value=self.trigger_word)],
                ),
                ast.Expr(
                    ast.Call(
                        func=ast.Name(id=node.name, ctx=ast.Load()),
                        args=[],
                        keywords=[],
                    ),
                ),
                [],
            ),
        ]


class CombineConstantOperations(ast.NodeTransformer):
    def visit_BinOp(self, node: ast.BinOp) -> ast.AST:
        if isinstance(node.right, ast.Name) and node.right.id == "compile":
            print(ast.dump(node.left))
            return ast.Constant(
                value=eval(ast.unparse(node.left), {"__name__": "@compile"}, {})
            )
        node.right = self.visit(node.right)
        node.left = self.visit(node.left)
        print(ast.dump(node))

        if isinstance(node.right, ast.Constant) and isinstance(node.left, ast.Constant):
            return ast.Constant(
                value=eval(ast.unparse(node), {"__name__": "@compile"}, {})
            )
        return node


class ConvertWithBase(ast.NodeTransformer):
    FEATURE_NAME: Optional[str] = None

    def __init__(self, trigger_word=None):
        self.trigger_word = trigger_word or self.FEATURE_NAME

    def convert(
        self, inner: ast.Call, asname: str, body: list[ast.stmt]
    ) -> list[ast.AST] | ast.AST:
        raise NotImplementedError

    def visit_With(self, node: ast.With) -> list[ast.AST] | ast.AST:
        if len(node.items) != 1:
            return node
        withitem = node.items[0]
        if (
            isinstance(withitem.context_expr, ast.Call)
            and isinstance(withitem.context_expr.func, ast.Name)
            and withitem.context_expr.func.id == self.trigger_word
        ):
            asname = (
                withitem.optional_vars.id
                if isinstance(withitem.optional_vars, ast.Name)
                else "__comPYned_tmp"
            )
            conv = self.convert(withitem.context_expr, asname, node.body)
            return (
                [ast.copy_location(x, node) for x in conv]
                if isinstance(conv, list)
                else conv
            )

        return node


class WithDecorator(ConvertWithBase):
    FEATURE_NAME = "wrp"

    def convert(
        self, inner: ast.Call, asname: str, body: list[ast.stmt]
    ) -> list[ast.AST] | ast.AST:
        return [
            ast.FunctionDef(
                name=asname,
                args=ast.arguments(
                    args=[],
                    posonlyargs=[],
                    kwonlyargs=[],
                    kw_defaults=[],
                    kwarg=None,
                    defaults=[],
                ),
                body=body,
                decorator_list=[inner.args[0]],
                returns=None,
            ),
            ast.Expr(
                ast.Call(
                    func=ast.Name(id=asname, ctx=ast.Load()),
                    args=[],
                    keywords=[],
                )
            ),
        ]


class WithCatch(ConvertWithBase):
    FEATURE_NAME = "ingore_exception"

    def convert(
        self, inner: ast.Call, asname: str, body: list[ast.stmt]
    ) -> list[ast.AST] | ast.AST:
        return ast.Try(
            body=body,
            handlers=[
                ast.ExceptHandler(
                    type=inner.args[0],
                    name=asname,
                    body=[
                        ast.Expr(
                            ast.Call(
                                func=ast.Name(id="print", ctx=ast.Load()),
                                args=[
                                    ast.BinOp(
                                        left=ast.Constant(value="Caught %s: %s"),
                                        op=ast.Mod(),
                                        right=ast.Tuple(
                                            elts=[
                                                ast.Attribute(
                                                    value=ast.Call(
                                                        func=ast.Name(
                                                            id="type", ctx=ast.Load()
                                                        ),
                                                        args=[
                                                            ast.Name(
                                                                id=asname,
                                                                ctx=ast.Load(),
                                                            )
                                                        ],
                                                        keywords=[],
                                                    ),
                                                    attr="__name__",
                                                ),
                                                ast.Name(id=asname, ctx=ast.Load()),
                                            ],
                                            ctx=ast.Load(),
                                        ),
                                    )
                                ],
                                keywords=[
                                    ast.keyword(
                                        arg="file",
                                        value=ast.Attribute(
                                            value=ast.Name(id="sys", ctx=ast.Load()),
                                            attr="stderr",
                                            ctx=ast.Load(),
                                        ),
                                    )
                                ],
                            )
                        )
                    ],
                )
            ],
            orelse=[],
            finalbody=[],
        )
        

class NameSeeker(ast.NodeVisitor):
    def __init__(self, triggers: list[str], callback: Callable[[str, int, int], None]):
        self.triggers = triggers
        self.callback = callback

    def visit_Name(self, node: ast.Name):
        if node.id in self.triggers:
            self.callback(node.id, node.lineno, node.col_offset)
        


def preprocess_ast(input_ast: ast.Module, filepath: str) -> ast.Module:
    first = input_ast.body[0]
    if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
        if first.value.value == "no-preprocess":
            input_ast.body.pop(0)
            return input_ast
    feature_finder = FindEnabledFeatures()
    tree = feature_finder.visit(input_ast)
    features = feature_finder.trigger_words
    reverse_features = {v: k for k, v in features.items()}
    if len(features) != len(reverse_features):
        raise ValueError("Imported features must have unique names!")
    if "__main__" in features:
        tree = AutoMainName(features["__main__"]).visit(tree)
    if "combine" in features:
        tree = CombineConstantOperations().visit(tree)
    with_converters = [WithDecorator, WithCatch]
    for with_converter in with_converters:
        if with_converter.FEATURE_NAME in features:
            tree = with_converter(features[with_converter.FEATURE_NAME]).visit(tree)
            
    
    def callback(name, lineno, col_offset):
        w = f"Feature '{reverse_features[name]}' imported as '{name}' cannot be used in this context! (at {filepath}:{lineno}:{col_offset})"
        warnings.warn(w, SyntaxWarning)
        
    NameSeeker(features.values(), callback).visit(tree)
        

    return tree, filepath


def custom_expanded_compyne(input_ast):
    compyner = ComPYner(module_preprocessor=preprocess_ast)
    compyner.add_module("__main__", input_ast)
    return compyner.compyne()
    # return ast.unparse(preprocess_ast(input_ast, "test.py")[0])


def main():
    parser = ArgumentParser()
    in_group = parser.add_mutually_exclusive_group(required=True)
    in_group.add_argument(
        "input",
        nargs="?",
        action="store",
        type=FileType("r", encoding="utf-8"),
        default=sys.stdin,
    )
    in_group.add_argument("--stdin", required=False, dest="stdin", action="store_true")
    parser.add_argument(
        "--output",
        "-o",
        required=False,
        action="store",
        type=FileType("w", encoding="utf-8"),
        default=sys.stdout,
    )

    parser.add_argument(
        "--exclude", required=False, action="store", type=str, default=None, nargs="+"
    )
    args = parser.parse_args()

    module_ast = ast.parse(args.input.read())

    args.output.write(custom_expanded_compyne(module_ast))


if __name__ == "__main__":
    main()
