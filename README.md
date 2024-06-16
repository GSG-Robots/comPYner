# compyner

This is a tool to combine the main file and any imported files into a single file.
This was created due to the limitations of the micropython implementation on the spike prime, where there is no filesystem to store multiple files.
We are aware that there are better ways to implement what we have done, but this is the least ugly code that will run on spike primes micropython.

## Usage

> [!WARNING]
> This tool is not extensively tested and may not work as expected. Use at your own risk.
> Feel free to open an issue if you encounter any problems.

```bash
python3 compyner.py <input_file> <excludes> > <output_file>
```

The `input_file` is the path to the main file that you want to combine with all the files it imports. This can be a relative or absolute path.

The excludes are the modules that are imported, but you do not want to include in the final file. This is a space separated list of module names.
This is useful for excluding modules that are in the standard library, or are not needed in the final file.

The program will skip imports from builtins and some from the standard library automatically, but by providing this it gets a lot safer.

The `output_file` is the filepath to the output file. This can be a relative or absolute path.

## Example

```bash
python3 compyner.py main math > output.py
```

This will combine the file `main.py` with all the files it imports, except for `math`, and output the result to `output.py`.

## The `spike_prime_compyne` script

This script is a wrapper around the `compyner.py` script that is designed to be used with the spike prime.
It will automatically exclude all known standard library modules and add a comment for the Spike Prime VSCode extension to upload the file to the spike prime.

```bash
python3 spike_prime_compyne.py <input_file> [<slot>] > <output_file>
```

The `input_file` and `output_file` behave the same as mentioned for the `compyner.py` script. The slot is the slot number on the spike prime the program is supposed to be uploaded to. This is an optional argument and defaults to 0.

## Known issues

- **FIXED**: `*`-Importing a module that is not excluded will not work. This is because we internally use variables to store the globals of each module, and something like `* = __comPYned_modules["test"]` ~~is not possible.~~ (`for name, value in __comPYned_modules["test"].items(): globals()[name] = value`)

## Authors

- [J0J0HA](https://github.com/J0J0HA)
