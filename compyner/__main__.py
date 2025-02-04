import ast
import sys
from argparse import ArgumentParser
from .logging import logger
from pathlib import Path
from compyner.engine import ComPYner


def file_path_exists(path: str) -> Path:
    pth = Path(path)
    if not pth.exists():
        raise FileNotFoundError(f"File not found: {pth}")
    return pth


def file_path_valid(path: str) -> Path:
    pth = Path(path)
    if not pth.resolve():
        raise FileNotFoundError(f"File not found: {pth}")
    return pth


ASCII_LOGO = r"""
                     ____ __   __               
   ___ ___  _ __ ___ |  _ \ \ / / __   ___ _ __ 
  / __/ _ \| '_ ` _ \| |_) \ V / '_ \ / _ \ '__|
 | (_| (_) | | | | | |  __/ | || | | |  __/ |   
  \___\___/|_| |_| |_|_|    |_||_| |_|\___|_|   
"""


def main() -> None:
    print(ASCII_LOGO)
    print()

    parser = ArgumentParser()
    parser.add_argument(
        "input",
        action="store",
        type=file_path_exists,
        help="Path to input file"
    )
    parser.add_argument(
        "--output",
        "-o",
        required=False,
        action="store",
        type=file_path_valid,
        default=None,
        help="Output file path. Defaults to input with .cpyd.py suffix"
    )

    parser.add_argument(
        "--exclude", required=False, action="store", type=str, default=None, nargs="+", help="Space-seperated list of modules not to include in the bundle"
    )
    parser.add_argument(
        "--random-name-length",
        "-r",
        required=False,
        action="store",
        type=int,
        default=0,
        help="How long the generated random names should be. Use 0 for keeping the original names; use any negative number for incrementing. Default 0."
    )
    parser.add_argument(
        "--reduce-dunder-name",
        required=False,
        action="store_true",
        help="Whether not to set __name__ if it is not used in the file."
    )
    args = parser.parse_args()

    if not args.output:
        args.output = args.input.with_suffix(".cpyd.py")

    module_ast = ast.parse(args.input.read_text(encoding="utf-8"))

    compyner = ComPYner(
        exclude_modules=args.exclude,
        require_dunder_name=not args.reduce_dunder_name,
        random_name_length=args.random_name_length,
        keep_names=not args.random_name_length,
    )

    logger.info("ComPYning...")

    sys.path.append(str(args.input.parent))
    content = (
        compyner.compyne_from_ast("__main__", module_ast, origin=args.input.name) + "\n"
    )

    logger.info("Writing to %s...", args.output)
    args.output.write_text(
        content,
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
