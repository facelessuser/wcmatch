[![Build][github-ci-image]][github-ci-link]
[![Unix Build Status][travis-image]][travis-link]
[![Windows Build Status][appveyor-image]][appveyor-link]
[![Coverage][codecov-image]][codecov-link]
[![PyPI Version][pypi-image]][pypi-link]
![License][license-image-mit]
# Wildcard Match

## Overview

Wildcard Match provides an enhanced `fnmatch`, `glob` and `pathlib` library in order to provide file matching and
globbing that more closely follows the features found in Bash. In some ways these libraries are similar to Python's
builtin libraries as they provide a similar interface to match, filter, and glob the file system. But they also include
a number of features found in Bash's globbing such as backslash escaping, brace expansion, extended glob pattern groups,
etc. They also add a number of new useful functions as well, such as `globmatch` which functions like `fnmatch`, but for
paths. Paths that would normally be returned when providing `glob` a pattern should also be properly match in
`globmatch`.

Wildcard Match uses Bash as a guide when making decisions on behavior in `fnmatch` and `glob`. Behavior may differ from
Bash version to Bash version, but an attempt is made to keep Wildcard Match up with the latest relevant changes. With
all of this said, there may be a few corner cases in which we've intentionally chosen to not *exactly* mirror Bash. If
an issue is found where Wildcard Match seems to deviate in an illogical way, we'd love to hear about it in the
[issue tracker](https://github.com/facelessuser/wcmatch/issues).

If all you are looking for is an alternative `fnmatch` and/or `glob` library that follows much more closely to Bash, or
even a `pathlib` library that taps into a more advanced `glob` library,  Wildcard Match has you covered, but Wildcard
Match also adds a file search utility called `wcmatch` that is built on top of `fnmatch` and `globmatch`. It was
originally written for [Rummage](https://github.com/facelessuser/Rummage), but split out into this project to be used by
other projects that may find its approach useful.

## Features

A quick overview of Wildcard Match's Features:

- Provides an interface comparable to Python's builtin in `fnamtch` and `glob`.
- Allows for a much more configurable experience when matching or globbing with many more features.
- Adds support for `**` in glob.
- Adds support for escaping characters with `\`.
- Add support for POSIX style character classes inside sequences: `[[:alnum:]]`, etc. The `C` locale is used for byte
  strings and Unicode properties for Unicode strings.
- Adds support for brace expansion: `a{b,{c,d}}` --> `ab ac ad`.
- Adds support for extended match patterns: `@(...)`, `+(...)`, `*(...)`, `?(...)`, and `!(...)`.
- Adds ability to match path names via the path centric `globmatch`.
- Provides a `pathlib` variant that uses Wildcard Match's `glob` library instead of Python's default.
- Provides an alternative file crawler called `wcmatch`.
- And more...

## Installation

Installation is easy with pip:

```
pip install wcmatch
```

## Documentation

http://facelessuser.github.io/wcmatch/

## License

The MIT License (MIT)

Copyright (c) 2018 - 2019 Isaac Muse

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

[github-ci-image]: https://github.com/facelessuser/wcmatch/workflows/build/badge.svg
[github-ci-link]: https://github.com/facelessuser/wcmatch/actions?workflow=build
[travis-image]: https://img.shields.io/travis/facelessuser/wcmatch/master.svg?label=Unix%20Build&logo=travis
[travis-link]: https://travis-ci.org/facelessuser/wcmatch
[appveyor-image]: https://img.shields.io/appveyor/ci/facelessuser/wcmatch/master.svg?label=Windows%20Build&logo=appveyor
[appveyor-link]: https://ci.appveyor.com/project/facelessuser/wcmatch
[codecov-image]: https://img.shields.io/codecov/c/github/facelessuser/wcmatch/master.svg
[codecov-link]: https://codecov.io/github/facelessuser/wcmatch
[pypi-image]: https://img.shields.io/pypi/v/wcmatch.svg?logo=python&logoColor=white
[pypi-link]: https://pypi.python.org/pypi/wcmatch
[license-image-mit]: https://img.shields.io/badge/license-MIT-blue.svg
