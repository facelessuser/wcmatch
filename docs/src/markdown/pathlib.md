# `wcmatch.pathlib`

```py3
from wcmatch import pathlib
```

!!! new "New 5.0"
    `wcmatch.pathlib` was added in `wcmatch` 5.0.

## Overview

`pathlib` is a library that contains subclasses of Python's `Path` and `PurePath` classes, and their Posix and Windows
subclasses, with purpose of overriding the default `glob` behavior with Wildcard Match's very own [`glob`](glob). This
allows a user of `pathlib` to use all of the glob enhancements such as extended glob patterns, and other great features.

The API is the same as Python's default `pathlib` except for the few differences listed below:

- Each `pathlib` object's `glob`, `rglob`, and `match` methods are now driven by the `wcmatch.glob` library.

- `glob` and `rglob` can take a single string pattern or a list of patterns. They also accept flags via the `flags`
  keyword.

- `globmatch` method is also added which is like `match` except without the recursive behavior.

## Classes

#### `pathlib.PurePath`

`PurePath` is Wildcard Match's version of Python's `PurePath`. Depending on the system, it will create either a
`PureWindowsPath` or a `PurePosixPath` object. Both objects will utilize `wcmatch.glob` for all glob related actions.

`PurePath` objects do not touch the filesystem. They include the methods `match` and `globmatch` (amongst others). You
can force the path to access the filesystem if you give either function the `pathlib.REALPATH` flag. We do not restrict
this, but we do not enable it by default. `pathlib.REALPATH` simply forces the match to check the filesystem to see if
the file exists and is a directory or not.

#### `pathlib.PureWindowsPath`

`PureWindowsPath` is Wildcard Match's version of Python's `PureWindowsPath`. This class will utilize `wcmatch.glob` for
all glob related actions. The class is subclassed from `pathlib.PurePath`.

#### `pathlib.PurePosixPath`

`PurePosixPath` is Wildcard Match's version of Python's `PurePosixPath`. This class will utilize `wcmatch.glob` for
all glob related actions. The class is subclassed from `pathlib.PurePath`.

#### `pathlib.Path`

`Path` is Wildcard Match's version of Python's `Path`. Depending on the system, it will create either a
`WindowsPath` or a `PosixPath` object. Both objects will utilize `wcmatch.glob` for all glob related actions.

`Path` classes are subclassed from the `PurePath` objects, and in addition to including `match` and `globmatch`, they
include `glob` and `rglob`. These objects **do** touch the filesystem, though, like `PurePath` objects, `match` and
`globmatch` do not touch the filesystem by default. `glob` and `rglob` are used exclusively to access the filesystem
and return files relative to the current `Path` object's filepath.

#### `pathlib.WindowsPath`

`WindowsPath` is Wildcard Match's version of Python's `WindowsPath`. This class will utilize `wcmatch.glob` for
all glob related actions. The class is subclassed from `pathlib.Path`.

#### `pathlib.PosixPath`

`PosixPath` is Wildcard Match's version of Python's `PosixPath`. This class will utilize `wcmatch.glob` for
all glob related actions. The class is subclassed from `pathlib.Path`.

## Methods

#### `PurePath.match`, `Path.match`

`match` mimics Python's `pathlib` version of `match` in that it uses a recursive logic. What this means is when you are
matching a path in the form `some/path/name`, the patterns `name`, `path/name` and `some/path/name` will all match.

Essentially, `match` appends `**/` the beginning of any pattern that is not an absolute pattern.

`match` does not access the filesystem, but you can force the path to access the filesystem if you give it the
`pathlib.REALPATH` flag. We do not restrict this, but we do not enable it by default. `pathlib.REALPATH` simply forces
the match to check the filesystem to see if the file exists and is a directory or not.

#### `PurePath.globmatch`, `Path.globmatch`

`globmatch` is similar to `match` except it does not use the same recursive logic that `match` does. In all other
respects, it behaves the same.

`globmatch` does not access the filesystem, but you can force the path to access the filesystem if you give it the
`pathlib.REALPATH` flag. We do not restrict this, but we do not enable it by default. `pathlib.REALPATH` simply forces
the match to check the filesystem to see if the file exists and is a directory or not.

#### `Path.rglob`

`rglob` mimics Python's `pathlib` version of `rglob` in that it uses a recursive logic. What this means is when you are
matching a path in the form `some/path/name`, the patterns `name`, `path/name` and `some/path/name` will all match.

Essentially, `rglob` appends `**/` the beginning of any pattern.

All paths returned are relative to the `pathlib` object. For this reason, absolute patterns are not supported.

#### `Path.glob`

`glob` is similar to `rglob` except it does not use the same recursive logic that `rglob` does. In all other respects,
it behaves the same.

All paths returned are relative to the `pathlib` object. For this reason, absolute patterns are not supported.

## Functions

#### `pathlib.escape`

```py3
def escape(pattern, unix=False):
```

This escapes special glob meta characters so they will be treated as literal characters.  It escapes using backslashes.
It will escape `-`, `!`, `*`, `?`, `(`, `[`, `|`, `^`, `{`, and `\`. On Windows, it will specifically only escape `\`
when not already escaped (`\\`). `/` and `\\` (on Windows) are not escaped as they are path separators.

```pycon3
>>> from wcmatch import pathlib
>>> p = pathlib.Path('some/path?/**file**{}.txt')
>>> p.globmatch(pathlib.escape('some/path?/**file**{}.txt'))
True
```

On a Windows system, drives are not escaped since meta characters are not parsed in drives. Drives on Windows are
generally treated special. This is because a drive could contain special characters like in `\\?\c:\`.

`escape` will detect the system it is running on and pick Windows escape logic or Linux/Unix logic. Since
`PurePath` classes allows you to match Unix style paths on a Windows system and vice versa, you can force Unix style
escaping or Windows style escaping via the `platform` parameter. Simply use the constants `AUTO`, `WINDOWS`, or `UNIX`.

```pycon3
>>> glob.escape('some/path?/**file**{}.txt', platform=glob.UNIX)
```

#### `pathlib.raw_escape`

```py3
def raw_escape(pattern, *, platform=AUTO):
```

This is like [`escape`](#pathlibescape) except it will apply raw character string escapes before doing meta character
escapes.  This is meant for use with the [`RAWCHARS`](#pathlibrawchars) flag.

```pycon3
>>> from wcmatch import glob
>>> p = pathlib.Path('some/path?/**file**{}.txt')
>>> p.globmatch('some/path?/**file**{}.txt', glob.escape(r'some/path?/\x2a\x2afile\x2a\x2a{}.txt'), flags=glob.RAWCHARS)
True
```

`raw_escape` will detect the system it is running on and pick Windows escape logic or Linux/Unix logic. Since
`PurePath` classes allows you to match Unix style paths on a Windows system and vice versa, you can force Unix style
escaping or Windows style escaping via the `platform` parameter. Simply use the constants `AUTO`, `WINDOWS`, or `UNIX`.

```pycon3
>>> glob.raw_escape(r'some/path?/\x2a\x2afile\x2a\x2a{}.txt', platform=glob.UNIX)
```

## Flags
