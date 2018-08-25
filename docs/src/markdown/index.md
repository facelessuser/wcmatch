# Wildcard Match

## Overview

Wildcard Match provides an enhanced `fnmatch` and `glob` library. In some ways it is similar to Python's builtin `fnmatch` and `glob` as it provides functions to match, filter, and glob the file system. But it adds a number of features found in Bash's globbing such as backslash escaping, brace expansion, extended glob pattern groups, etc. It also adds a path centric matcher called `globmatch` which functions like `fnmatch`, but for paths. Paths that would normally be returned when providing `glob` a pattern should also be properly match in `globmatch`.

- Provides features comparable to Python's builtin in `fnamtch` and `glob`.
- Adds support for `**` in glob.
- Adds support for escaping characters with `\`.
- Add support for POSIX style character classes inside sequences: `[[:alnum:]]`, etc. The `C` locale is used for byte strings and Unicode properties for Unicode strings.
- Adds support for brace expansion: `a{b,{c,d}}` --> `ab ac ad`.
- Adds support for extended match patterns: `@(...)`, `+(...)`, `*(...)`, `?(...)`, and `!(...)`.
- Adds ability to match path names via the path centric `globmatch`.
- Provides an alternative file crawler called `wcmatch`.
- And more...

## Installation

Installation is easy with pip:

```bash
pip install wcmatch
```

## Libraries

- [fnmatch](fnmatch): A file name matching library.
- [glob](glob): A file system searching and file path matching library.
- [wcmatch](wcmatch): An alternative file search library built on `fnmatch` and `globmatch`.

--8<--
refs.txt
--8<--
