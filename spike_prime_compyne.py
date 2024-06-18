from pathlib import Path
import sys
from compyner.engine import ComPYner, ast_from_file


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


def spike_prime_compyne(input_module, slot=0):
    compyner = ComPYner(SPIKE_PRIME_MODULES)
    compyner.add_module("__main__", ast_from_file(Path(input_module)))
    return f"# LEGO type:standard slot:{slot} autostart\n" + compyner.compyne()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python spike_prime_compyne.py <name> [<slot>]")
        sys.exit(1)
    input_module = sys.argv[1]
    slot = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    print(spike_prime_compyne(input_module, slot))
