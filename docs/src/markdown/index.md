# Wildcard Match

## Overview

Wildcard Match provides an enhanced [`fnmatch`](./fnmatch.md), [`glob`](./glob.md), and [`pathlib`](./pathlib.md)
library in order to provide file matching and globbing that more closely follows the features found in Bash. In some
ways these libraries are similar to Python's builtin libraries as they provide a similar interface to match, filter, and
glob the file system. But they also include a number of features found in Bash's globbing such as backslash escaping,
brace expansion, extended glob pattern groups, etc. They also add a number of new useful functions as well, such as
[`globmatch`](./glob.md#globmatch) which functions like [`fnmatch`](./fnmatch.md#fnmatch), but for paths.

Wildcard Match also adds a file search utility called [`wcmatch`](./wcmatch.md) that is built on top of
[`fnmatch`](./fnmatch.md#fnmatch) and [`globmatch`](./glob.md#globmatch). It was originally written for
[Rummage](https://github.com/facelessuser/Rummage), but split out into this project to be used by other projects that
may find its approach useful.

Bash is used as a guide when making decisions on behavior for [`fnmatch`](./fnmatch.md) and [`glob`](./glob.md).
Behavior may differ from Bash version to Bash version, but an attempt is made to keep Wildcard Match up with the latest
relevant changes. With all of this said, there may be a few corner cases in which we've intentionally chosen to not
*exactly* mirror Bash. If an issue is found where Wildcard Match seems to deviate in an illogical way, we'd love to hear
about it in the [issue tracker][issues].

## Features

A quick overview of Wildcard Match's Features:

- Provides an interface comparable to Python's builtin in [`fnamtch`][fnmatch], [`glob`][glob], and
  [`pathlib`][pathlib].
- Allows for a much more configurable experience when matching or globbing with many more features.
- Adds support for `**` in glob.
- Adds support for escaping characters with `\`.
- Add support for POSIX style character classes inside sequences: `[[:alnum:]]`, etc. The `C` locale is used for byte
  strings and Unicode properties for Unicode strings.
- Adds support for brace expansion: `a{b,{c,d}}` --> `ab ac ad`.
- Adds support for expanding `~` or `~username` to the appropriate user path.
- Adds support for extended match patterns: `@(...)`, `+(...)`, `*(...)`, `?(...)`, and `!(...)`.
- Adds ability to match path names via the path centric `globmatch`.
- Provides a [`pathlib`][pathlib] variant that uses Wildcard Match's `glob` library instead of Python's default.
- Provides an alternative file crawler called `wcmatch`.
- And more...

## Installation

Installation is easy with pip:

```bash
pip install wcmatch
```

## Libraries

- [`fnmatch`](./fnmatch.md): A file name matching library.
- [`glob`](./glob.md): A file system searching and file path matching library.
- [`pathlib`](./pathlib.md): A implementation of Python's `pathlib` that uses our own `glob` implementation.
- [`wcmatch`](./wcmatch.md): An alternative file search library built on `fnmatch` and `globmatch`.

--8<--
refs.txt
--8<--
