import argparse as _argp
import sys
from typing import Any, Callable, ContextManager


class __EnterExit:
    def __enter__(self): ...
    def __exit__(self, exc_type, exc_val, exc_tb): ...


__EnterExit_ = __EnterExit()


def wrp(decorator: Callable) -> ContextManager[Callable]:
    """Wrap the following code in a function decorated with the provided decorator and executed immideately

    Usage:

    with wrp(dec):
        print('hi')

    Equivalent to:

    @dec
    def _():
        print('hi')

    _()
    """


combine = None


def ingore_exception(exception: Exception) -> ContextManager[None]:
    """Context manager to ignore exceptions that happen within.

    Usage:

    with ignore_exception(RuntimeError):
        raise RuntimeError("test")


    This will print: 'Caught RuntimeError: test' to sys.stderr
    """


def __main__(func) -> Callable:
    """If __name__=='__main__' the function is executed automatically."""


if __name__ == "compyner_ext_features":
    import compyne_extend
    import ast
    import pathlib

    parser = _argp.ArgumentParser()
    parser.add_argument(
        "--output",
        "-o",
        required=False,
        action="store",
        type=_argp.FileType("w", encoding="utf-8"),
    )

    parser.add_argument(
        "--exclude", required=False, action="store", type=str, default=None, nargs="+"
    )
    args = parser.parse_args()

    code = pathlib.Path(sys.modules["__main__"].__file__).read_text()
    module_ast = ast.parse(code)
    new_code = compyne_extend.custom_expanded_compyne(module_ast)

    if args.output:
        args.output.write(new_code)
    else:
        pathlib.Path(sys.modules["__main__"].__file__).with_suffix(
            ".compyned.py"
        ).write_text(new_code)
