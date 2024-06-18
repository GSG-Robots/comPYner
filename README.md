# compyner

ComPYner is a small tool to bundle a python file and all its imports into a single file.
This was created due to the limitations of the micropython implementation on the spike prime, where there is no filesystem to store multiple files.
We are aware that there are better ways to implement what we have done, but this is the least ugly code that will run on spike primes micropython.

## Installation

Install `compyner` with pip, or another tool using PyPI:
```bash
pip install compyner
```

## Usage

> [!WARNING]
> This tool is not extensively tested and may not work as expected. Use at your own risk.
> Feel free to open an issue if you encounter any problems.

```bash
compyner <input> -o <output>
```

This command will read the file at `<input>`, "compyne" it and writes the result to `<output>`

If the `-o/--output` argument is not used, the result will be printed to `stdout`.
If you want to read from `stdin`, you can do this by omitting the `input` argument and using the `--stdin` flag.

If any modules are imported that are in the standard library, these need to be excluded.
Normally, the script detects these imports and excludes them automatically, but this does not work for some, like the `collections` module.
Also, modules that are only availible in the standard library of the target environment should be excluded.

Modules that should be excluded should be passed as a space-seperated list to the `--exclude` argument.

### Example

```bash
compyner main.py --exclude math -o output.py
```

This will combine the file `main.py` with all the files it imports, except for `math`, and output the result to `output.py`.

## The `spike_prime_compyne` script

This script is a wrapper around the `compyner.py` script that is designed to be used with the spike prime.
It will automatically exclude all known standard library modules and add a comment for the Spike Prime VSCode extension to upload the file to the spike prime.

```bash
python3 spike_prime_compyne.py <input_file> [<slot>] > <output_file>
```

The `input_file` and `output_file` behave the same as mentioned for the `compyner.py` script.

The `slot` is the slot number on the spike prime the program is supposed to be uploaded to. This is an optional argument and defaults to 0.

## Known issues

None at the moment.

## Authors

- [J0J0HA](https://github.com/J0J0HA)
