import sys
from compyne import compyne


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
    return f"# LEGO type:standard slot:{slot} autostart\n" + compyne(
        input_module, SPIKE_PRIME_MODULES
    )


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python spike_prime_compyne.py <name> [<slot>]")
        sys.exit(1)
    input_module = sys.argv[1]
    slot = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    print(spike_prime_compyne(input_module, slot))
