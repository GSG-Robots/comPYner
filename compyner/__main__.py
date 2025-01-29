import ast
from pathlib import Path
from argparse import ArgumentParser, FileType
import sys

from compyner.engine import ComPYner, ast_from_file


def main():
    parser = ArgumentParser()
    in_group = parser.add_mutually_exclusive_group(required=True)
    in_group.add_argument("input", nargs='?', action="store", type=FileType('r', encoding='utf-8'), default=sys.stdin)
    in_group.add_argument("--stdin", required=False, dest="stdin", action="store_true")
    parser.add_argument("--output", "-o", required=False, action="store", type=FileType('w', encoding='utf-8'), default=sys.stdout)
    
    parser.add_argument("--exclude", required=False, action="store", type=str, default=None, nargs='+')
    parser.add_argument("--split-modules", required=False, action="store_true", default=False)
    parser.add_argument("--no-attrs", required=False, action="store_true", default=False)
    args = parser.parse_args()
    
    module_ast = ast.parse(args.input.read())

    compyner = ComPYner(
        exclude=args.exclude,
        debug_stack=False,
        debug_line=False,
        split_modules=args.split_modules,
        use_attr=not args.no_attrs,
        require_dunder_name=True,)
    compyner.add_module("__main__", module_ast)
    
    args.output.write(compyner.compyne())


if __name__ == "__main__":
    main()
