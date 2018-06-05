# Wildcard Match

## Overview

Wildcard Match provides an enhanced `fnmatch` and `glob` library. In some ways it is similar to Python's builtin `fnmatch` and `glob` as it provides functions to match, filter, and glob the file system. But it adds a number of features found in Bash's globbing such as backslash escaping, brace expansion, extended glob pattern groups, etc. It also adds a path centric matcher called `globmatch` which functions like `fnmatch`, but for paths. Paths that would normally be returned when providing `glob` a pattern should also be properly match in `globmatch`.

- Adds support for `**` in glob.
- Adds support for escaping characters with `\`.
- Add support for POSIX style character classes inside sequences: `[[:alnum:]]`, etc. The `C` locale is used for byte string and Unicode properties for Unicode strings.
- Adds support for brace expansion: `a{b,{c,d}}` --> `ab ac ad`.
- Adds support for extended match patterns: `@(...)`, `+(...)`, `*(...)`, `?(...)`, and `!(...)`.
- Adds ability to match path names via `globmatch` as well as traditional file system searching via `glob`.
- And more...

If all you are looking for is an alternative `fnmatch` and/or `glob`, Wildcard Match has you covered, but Wildcard Match also adds a file search utility called `wcmatch` that is built on top of `fnmatch` and `globmatch`. It was originally written for [Rummage](https://github.com/facelessuser/Rummage), but split out into this project to be used by other projects that may find it's approach useful.

## Installation

Installation is easy with pip:

```bash
pip install wcmatch
```

## Libraries

- [fnmatch](fnmatch): A file name matching library.
- [glob](glob): A file system searching and file path matching library.
- [wcmatch](wcmatch): An file search library built on `fnmatch` and `globmatch`.

--8<--
refs.md
--8<--
