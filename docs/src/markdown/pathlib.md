# `wcmatch.pathlib`

```py3
from wcmatch import pathlib
```

!!! new "New 5.0"
    `wcmatch.pathlib` was added in `wcmatch` 5.0.

## Overview

`pathlib` is a library that contains subclasses of Python's [`pathlib`][pathlib] `Path` and `PurePath` classes, and
their Posix and Windows subclasses, with the purpose of overriding the default `glob` behavior with Wildcard Match's
very own [`glob`](./glob.md). This allows a user of `pathlib` to use all of the glob enhancements that Wildcard Match
provides. This includes features such as extended glob patterns, brace expansions, and more.

This documentation does not mean to exhaustively describe the [`pathlib`][pathlib] library, just the differences
introduced by Wildcard Match's implementation. Please check out Python's [`pathlib`][pathlib] documentation to learn
more about [`pathlib`][pathlib] in general. Also, to learn more about the underlying glob library being used, check out
the documentation for Wildcard Match's [`glob`](./glob.md).

## Multi-Pattern Limits

Many of the API functions allow passing in multiple patterns or using either [`BRACE`](#pathlibbrace) or
[`SPLIT`](#pathlibsplit) to expand a pattern in to more patterns. The number of allowed patterns is limited `1000`, but
you can raise or lower this limit via the keyword option `limit`. If you set `limit` to `0`, there will
be no limit.

!!! new "New 6.0"
    The imposed pattern limit and corresponding `limit` option was introduced in 6.0.

### Differences

The API is the same as Python's default [`pathlib`][pathlib] except for the few differences related to file globbing and
matching:

- Each `pathlib` object's [`glob`](#pathglob), [`rglob`](#pathrglob), and [`match`](#purepathmatch) methods are now
  driven by the [`wcmatch.glob`](./glob.md) library.

- [`glob`](#pathglob) and [`rglob`](#pathrglob) can take a single string pattern or a list of patterns. They also accept
  [flags](#flags) via the `flags` keyword. This matches the interfaces found detailed in our [`glob`](./glob.md)
  documentation.

- A [`globmatch`](#purepathglobmatch) method has been added to `PurePath` classes (and `Path` classes which are derived
  from `PurePath`) which is like [`match`](#purepathmatch) except without the recursive behavior. See
  [`match`](#purepathmatch) and [`globmatch`](purepathglobmatch) for more information.

- [`glob`](#pathglob) and [`rglob`](#pathrglob) do not enable [`GLOBSTAR`](#pathlibglobstar) or
  [`DOTGLOB`](#pathlibdotglob) by default. These flags must be passed in to take advantage of this functionality.

- Python's [`pathlib`][pathlib], when using `match` has logic to ignore `.` when used as a directory. In our
  implementation, `.` explicitly matches a path with `.` as a directory part. Since [`pathlib`][pathlib] normalizes
  paths by removing `.` directories, there is really no reason to use them in your patterns. If you expect `.`, when
  used as a directory, to be ignored, then this is a difference you should be aware of.

    Our behavior mirrors Bash in that when you glob with `.` your paths are returned with `.`. And when you don't, the
    path's are returned without:

    ```console
    $ echo ./wcmatch/*.py
    ./wcmatch/__init__.py ./wcmatch/__meta__.py ./wcmatch/_wcparse.py ./wcmatch/fnmatch.py ./wcmatch/glob.py ./wcmatch/pathlib.py ./wcmatch/util.py ./wcmatch/wcmatch.py
    ```

    ```console
    $ echo wcmatch/*.py
    wcmatch/__init__.py wcmatch/__meta__.py wcmatch/_wcparse.py wcmatch/fnmatch.py wcmatch/glob.py wcmatch/pathlib.py wcmatch/util.py wcmatch/wcmatch.py
    ```

    [`globmatch`](./glob.md#globglobmatch)'s goal, which [`match`](#purepathmatch) uses, is to match what
    [`glob`](./glob.md#globglob) globs. So when you use [`match`](#purepathmatch) with a `.`, you are requesting a path
    where `.` is explicitly used.

### Similarities

As far as similarities, all non-glob related methods should behave exactly like Python's as our version is derived from
theirs. [`glob`](#pathglob), [`rglob`](#pathrglob), and [`match`](#purepathmatch) should mimic the basic behavior of
Python's original [`pathlib`][pathlib] library as well, just with the enhancements and configurability that Wildcard
Match's [`glob`](./glob.md) provides:

- [`glob`](#pathglob) and [`rglob`](#pathrglob) will yield an iterator of the results.

- [`rglob`](#pathrglob) and [`match`](#purepathmatch) will exhibit the same *recursive* type behavior as the original
  implementation.

## Classes

#### `pathlib.PurePath`

`PurePath` is Wildcard Match's version of Python's `PurePath` class. Depending on the system, it will create either a
[`PureWindowsPath`](#pathlibpurewindowspath) or a [`PurePosixPath`](#pathlibpureposixpath) object. Both objects will
utilize [`wcmatch.glob`](./glob.md) for all glob related actions.

`PurePath` objects do **not** touch the filesystem. They include the methods [`match`](#purepathmatch) and
[`globmatch`](#purepathglobmatch) (amongst others). You can force the path to access the filesystem if you give either
function the [`REALPATH`](#pathlibrealpath) flag. We do not restrict this, but we do not enable it by default.
[`REALPATH`](#pathlibrealpath) simply forces the match to check the filesystem to see if the file exists and is a
directory or not.

```pycon3
>>> from wcmatch import pathlib
>>> pathlib.PurePath('docs/src')
PurePosixPath('docs/src')
```

`PurePath` classes implement the [`match`](#purepathmatch) and [`globmatch`](#purepathglobmatch) methods:

```pycon3
>>> from wcmatch import pathlib
>>> p = pathlib.PurePath('docs/src')
>>> p.match('src')
True
>>> p.globmatch('**/src', flags=pathlib.GLOBSTAR)
True
```

#### `pathlib.PureWindowsPath`

`PureWindowsPath` is Wildcard Match's version of Python's `PureWindowsPath`. The `PureWindowsPath` class is useful if
you'd like to have the ease that `pathlib` offers when working with a path, but don't want it to access the filesystem.
This is also useful if you'd like to manipulate Windows path strings on a Posix system. This class will utilize Wildcard
Match's [`glob`](./glob.md) for all glob related actions. The class is subclassed from [`PurePath`](#pathlibpurepath).

```pycon3
>>> from wcmatch import pathlib
>>> os.name
'posix'
>>> pathlib.PureWindowsPath('c:/some/path')
PureWindowsPath('c:/some/path')
```

#### `pathlib.PurePosixPath`

`PurePosixPath` is Wildcard Match's version of Python's `PurePosixPath`. The `PurePosixPath` class is useful if
you'd like to have the ease that `pathlib` offers when working with a path, but don't want it to access the filesystem.
This is also useful if you'd like to manipulate Posix path strings on a Windows system. This class will utilize Wildcard
Match's [`glob`](./glob.md) for all glob related actions. The class is subclassed from [`PurePath`](#pathlibpurepath).

```pycon3
>>> from wcmatch import pathlib
>>> os.name
'nt'
>>> pathlib.PureWindowsPath('/usr/local/bin')
PurePosixPath('/usr/local/bin')
```

#### `pathlib.Path`

`Path` is Wildcard Match's version of Python's `Path` class. Depending on the system, it will create either a
[`WindowsPath`](#pathlibwindowspath) or a [`PosixPath`](#pathlibposixpath) object. Both objects will
utilize [`wcmatch.glob`](./glob.md) for all glob related actions.

`Path` classes are subclassed from the [`PurePath`](#pathlibpurepath) objects, so you get all the features of the `Path`
class in addition to the [`PurePath`](#pathlibpurepath) class features. `Path` objects have access to the filesystem.
They include the [`PurePath`](#pathlibpurepath) methods [`match`](#purepathmatch) and [`globmatch`](#purepathglobmatch)
(amongst others). Since these methods are [`PurePath`](#pathlibpurepath) methods, they do not touch the filesystem. But,
you can force them to access the filesystem if you give either function the [`REALPATH`](#pathlibrealpath) flag. We do
not restrict this, but we do not enable it by default. [`REALPATH`](#pathlibrealpath) simply forces the match to check
the filesystem to see if the file exists and is a directory or not.

```pycon3
>>> from wcmatch import pathlib
>>> pathlib.PurePath('docs/src')
PosixPath('docs/src')
```

`Path` classes implement the [`glob`](#pathglob) and [`globmatch`](#pathrglob) methods:

```pycon3
>>> from wcmatch import pathlib
>>> p = pathlib.Path('docs/src')
>>> p.match('src')
True
>>> p.globmatch('**/src', flags=pathlib.GLOBSTAR)
True
>>> list(p.glob('**/*.txt', flags=pathlib.GLOBSTAR))
[PosixPath('docs/src/dictionary/en-custom.txt'), PosixPath('docs/src/markdown/_snippets/links.txt'), PosixPath('docs/src/markdown/_snippets/refs.txt'), PosixPath('docs/src/markdown/_snippets/abbr.txt'), PosixPath('docs/src/markdown/_snippets/posix.txt')]
>>> list(p.rglob('*.txt'))
[PosixPath('docs/src/dictionary/en-custom.txt'), PosixPath('docs/src/markdown/_snippets/links.txt'), PosixPath('docs/src/markdown/_snippets/refs.txt'), PosixPath('docs/src/markdown/_snippets/abbr.txt'), PosixPath('docs/src/markdown/_snippets/posix.txt')]
```

#### `pathlib.WindowsPath`

`WindowsPath` is Wildcard Match's version of Python's `WindowsPath`. The `WindowsPath` class is useful if you'd like to
have the ease that `pathlib` offers when working with a path and be able to manipulate or gain access to to information
about that file. You cannot instantiate this class on a Posix system. This class will utilize Wildcard Match's
[`glob`](./glob.md) for all glob related actions. The class is subclassed from [`Path`](#pathlibpath).

```pycon3
>>> from wcmatch import pathlib
>>> os.name
'posix'
>>> pathlib.Path('c:/some/path')
WindowsPath('c:/some/path')
```

#### `pathlib.PosixPath`

`PosixPath` is Wildcard Match's version of Python's `PosixPath`. The `PosixPath` class is useful if you'd like to
have the ease that `pathlib` offers when working with a path and be able to manipulate or gain access to to information
about that file. You cannot instantiate this class on a Windows system. This class will utilize Wildcard Match's
[`glob`](./glob.md) for all glob related actions. The class is subclassed from [`Path`](#pathlibpath).

```pycon3
>>> from wcmatch import pathlib
>>> os.name
'posix'
>>> pathlib.Path('/usr/local/bin')
PosixPath('/usr/local/bin')
```

## Methods

#### `PurePath.match`

```py3
def match(self, patterns, *, flags=0, limit=1000):
```

`match` takes a pattern (or list of patterns), and flags.  It also allows configuring the [max pattern
limit](#multi-pattern-limits). It will return a boolean indicating whether the objects file path was matched by the
pattern(s).

`match` mimics Python's `pathlib` version of `match` in that it uses a recursive logic. What this means is when you are
matching a path in the form `some/path/name`, the patterns `name`, `path/name` and `some/path/name` will all match.
Essentially, the pattern, if not an absolute pattern, behaves as if a [`GLOBSTAR`](#pathlibglobstar) pattern of `**/`
was added at the beginning of the pattern.

`match` does not access the filesystem, but you can force the path to access the filesystem if you give it the
[`REALPATH`](#pathlibrealpath) flag. We do not restrict this, but we do not enable it by default.
[`REALPATH`](#pathlibrealpath) simply forces the match to check the filesystem to see if the file exists and is a
directory or not.

Since [`Path`](#pathlibpath) is derived from [`PurePath`](#pathlibpurepath), this method is also available in
[`Path`](#pathlibpath) objects.

```pycon3
>>> from wcmatch import pathlib
>>> p = pathlib.PurePath('docs/src')
>>> p.match('src')
True
```

!!! new "New 6.0"
    `limit` was added in 6.0.

#### `PurePath.globmatch`

```py3
def globmatch(self, patterns, *, flags=0, limit=1000):
```

`globmatch` takes a pattern (or list of patterns), and flags.  It also allows configuring the [max pattern
limit](#multi-pattern-limits).It will return a boolean indicating whether the objects file path was matched by the
pattern(s).

`globmatch` is similar to [`match`](#purepathmatch) except it does not use the same recursive logic that
[`match`](#purepathmatch) does. In all other respects, it behaves the same.

`globmatch` does not access the filesystem, but you can force the path to access the filesystem if you give it the
[`REALPATH`](#pathlibrealpath) flag. We do not restrict this, but we do not enable it by default.
[`REALPATH`](#pathlibrealpath) simply forces the match to check the filesystem to see if the file exists and is a
directory or not.

Since [`Path`](#pathlibpath) is derived from  [`PurePath`](#pathlibpurepath), this method is also available in
[`Path`](#pathlibpath) objects.

```pycon3
>>> from wcmatch import pathlib
>>> p = pathlib.PurePath('docs/src')
>>> p.globmatch('**/src', flags=pathlib.GLOBSTAR)
True
```

!!! new "New 6.0"
    `limit` was added in 6.0.

#### `Path.glob`

```py3
def glob(self, patterns, *, flags=0, limit=1000):
```

`glob` takes a pattern (or list of patterns) and flags. It also allows configuring the [max pattern
limit](#multi-pattern-limits). It will crawl the file system, relative to the current [`Path`](#pathlibpath) object,
returning a generator of [`Path`](#pathlibpath) objects. If a file/folder matches any regular, inclusion pattern, it is
considered a match.  If a file matches *any* exclusion pattern (when enabling the [`NEGATE`](#pathlibnegate) flag), then
it will not be returned.

This method calls our own [`iglob`](./glob.md#globiglob) implementation, and as such, should behave in the same manner
in respect to features, the one exception being that instead of returning path strings in the generator, it will return
[`Path`](#pathlibpath) objects.

The one difference between this `glob` and the [`iglob`](./glob.md#globiglob) API is that this function does not accept
the `root_dir` parameter. All searches are relative to the object's path, which is evaluated relative to the current
working directory.

```pycon3
>>> from wcmatch import pathlib
>>> p = pathlib.Path('docs/src')
>>> list(p.glob('**/*.txt', flags=pathlib.GLOBSTAR))
[PosixPath('docs/src/dictionary/en-custom.txt'), PosixPath('docs/src/markdown/_snippets/links.txt'), PosixPath('docs/src/markdown/_snippets/refs.txt'), PosixPath('docs/src/markdown/_snippets/abbr.txt'), PosixPath('docs/src/markdown/_snippets/posix.txt')]
```

!!! new "New 6.0"
    `limit` was added in 6.0.

#### `Path.rglob`

```py3
def rglob(self, patterns, *, flags=0, path_limit=1000):
```

`rglob` takes a pattern (or list of patterns) and flags. It also allows configuring the [max pattern
limit](#multi-pattern-limits). It will crawl the file system, relative to the current [`Path`](#pathlibpath) object,
returning a generator of [`Path`](#pathlibpath) objects. If a file/folder matches any regular patterns, it is considered
a match.  If a file matches *any* exclusion pattern (when enabling the [`NEGATE`](#pathlibnegate) flag), then it will be
not be returned.

`rglob` mimics Python's [`pathlib`][pathlib] version of `rglob` in that it uses a recursive logic. What this means is
that when you are matching a path in the form `some/path/name`, the patterns `name`, `path/name` and `some/path/name`
will all match. Essentially, the pattern behaves as if a [`GLOBSTAR`](#pathlibglobstar) pattern of `**/` was added at
the beginning of the pattern.

`rglob` is similar to [`glob`](#pathlibglob) except for the use of recursive logic. In all other respects, it behaves
the same.

```pycon3
>>> from wcmatch import pathlib
>>> p = pathlib.Path('docs/src')
>>> list(p.rglob('*.txt'))
[PosixPath('docs/src/dictionary/en-custom.txt'), PosixPath('docs/src/markdown/_snippets/links.txt'), PosixPath('docs/src/markdown/_snippets/refs.txt'), PosixPath('docs/src/markdown/_snippets/abbr.txt'), PosixPath('docs/src/markdown/_snippets/posix.txt')]
```

!!! new "New 6.0"
    `limit` was added in 6.0.

## Flags

#### `pathlib.CASE, pathlib.C` {: #pathlibcase}

`CASE` forces case sensitivity. `CASE` has higher priority than [`IGNORECASE`](#pathlibignorecase).

On Windows, drive letters (`C:`) and UNC host/share (`//host/share`) portions of a path will still be treated case
insensitively, but the rest of the path will have case sensitive logic applied.

#### `pathlib.IGNORECASE, pathlib.I` {: #pathlibignorecase}

`IGNORECASE` forces case insensitivity. [`CASE`](#pathlibcase) has higher priority than `IGNORECASE`.

#### `glob.RAWCHARS, glob.R` {: #pathlibrawchars}

`RAWCHARS` causes string character syntax to be parsed in raw strings: `#!py3 r'\u0040'` --> `#!py3 r'@'`. This will
handle standard string escapes and Unicode including `#!py3 r'\N{CHAR NAME}'`.

#### `pathlib.NEGATE, pathlib.N` {: #pathlibnegate}

`NEGATE` causes patterns that start with `!` to be treated as exclusion patterns. A pattern of `!*.py` would match any
file but Python files. Exclusion patterns cannot be used by themselves though, and must be paired with a normal,
inclusion pattern, either by utilizing the [`SPLIT`](#pathlibsplit) flag, or providing multiple patterns in a list.
Assuming the [`SPLIT`](#pathlibsplit) flag, this means using it in a pattern such as `inclusion|!exclusion`.

If it is desired, you can force exclusion patterns, when no inclusion pattern is provided, to assume all files match
unless the file matches the excluded pattern. This is done with the [`NEGATEALL`](#pathlibnegateall) flag.

If used with the extended glob feature, patterns like `!(inverse|pattern)` will be mistakenly parsed as an exclusion
pattern instead of as an inverse extended glob group.  See [`MINUSNEGATE`](#pathlibminusnegate) for an alternative
syntax that plays nice with extended glob.

#### `pathlib.NEGATEALL, pathlib.A` {: #pathlibnegateall}

`NEGATEALL` can force exclusion patterns, when no inclusion pattern is provided, to assume all files match unless the
file matches the excluded pattern. Essentially, it means if you use a pattern such as `!*.md`, it will assume two
patterns were given: `**` and `!*.md`, where `!*.md` is applied to the results of `**`, and `**` is specifically treated
as if [`GLOBSTAR`](#pathlibglobstar) was enabled.

Dot files will not be returned unless [`DOTGLOB`](#pathlibdotglob) is enabled. Symlinks will also be ignored in the
return unless [`FOLLOW`](#pathlibfollow) is enabled.

#### `pathlib.MINUSNEGATE, pathlib.M` {: #pathlibminusnegate}

When `MINUSNEGATE` is used with [`NEGATE`](#pathlibnegate), exclusion patterns are recognized by a pattern starting with
`-` instead of `!`. This plays nice with the extended glob feature which already uses `!` in patterns such as `!(...)`.

#### `pathlib.GLOBSTAR, pathlib.G` {: #pathlibglobstar}

`GLOBSTAR` enables the feature where `**` matches zero or more directories.

#### `pathlib.FOLLOW, pathlib.L` {: #pathlibfollow}

`FOLLOW` will cause `GLOBSTAR` patterns (`**`) to match and traverse symlink directories.

#### `pathlib.REALPATH, pathlib.P` {: #pathlibrealpath}

In the past, only `glob` and `iglob` operated on the filesystem, but with `REALPATH`, other functions will now operate
on the filesystem as well: [`globmatch`](#purepathglobmatch) and [`match`](#purepathmatch).

Normally, functions such as [`globmatch`](#purepathglobmatch) would simply match a path with regular expression and
return the result. The functions were not concerned with whether the path existed or not. It didn't care if it was even
valid for the operating system.

`REALPATH` forces [`globmatch`](#purepathglobmatch) and [`match`](#purepathmatch) to treat the path as a real file path
for the given system it is running on. It will augment the patterns used to match files and enable additional logic so
that the path must meet the following in order to match:

- Path must exist.
- Directories that are symlinks will not be matched by [`GLOBSTAR`](#pathlibglobstar) patterns (`**`) unless the
  [`FOLLOW`](#pathlibfollow) flag is enabled.
- When presented with a pattern where the match must be a directory, but the file path being compared doesn't indicate
  the file is a directory with a trailing slash, the command will look at the filesystem to determine if it is a
  directory.
- Paths must match in relation to the current working directory unless the pattern is constructed in a way to indicates
  an absolute path.

#### `pathlib.DOTGLOB, pathlib.D` {: #pathlibdotglob}

By default, globbing and matching functions will not match file or directory names that start with dot `.` unless
matched with a literal dot. `DOTGLOB` allows the meta characters (such as `*`) to glob dots like any other character.
Dots will not be matched in `[]`, `*`, or `?`.

Alternatively `DOTMATCH` will also be accepted for consistency with the other provided libraries. Both flags are exactly
the same and are provided as a convenience in case the user finds one more intuitive than the other since `DOTGLOB` is
often the name used in Bash.

#### `pathlib.EXTGLOB, pathlib.E` {: #pathlibextglob}

`EXTGLOB` enables extended pattern matching which includes special pattern lists such as `+(...)`, `*(...)`, `?(...)`,
etc. See the [syntax overview](#syntax) for more information.

Alternatively `EXTMATCH` will also be accepted for consistency with the other provided libraries. Both flags are exactly
the same and are provided as a convenience in case the user finds one more intuitive than the other since `EXTGLOB` is
often the name used in Bash.

!!! tip "EXTMATCH and NEGATE"
    When using `EXTMATCH` and [`NEGATE`](#pathlibnegate) together, it is recommended to also use
    [`MINUSNEGATE`](#pathlibminusnegate) to avoid conflicts in regards to the `!` meta character.

#### `pathlib.BRACE, pathlib.B` {: #pathlibbrace}

`BRACE` enables Bash style brace expansion: `a{b,{c,d}}` --> `ab ac ad`. Brace expansion is applied before anything
else. When applied, a pattern will be expanded into multiple patterns. Each pattern will then be parsed separately.

Redundant, identical patterns are discarded[^1] by default, and `glob` and `iglob` will limit the returned values to
unique results. If you need [`glob`](#pathglob) or [`iglob`](#pathrglob) to behave more like Bash and return all
results, you can set [`NOUNIQUE`](#pathlibnounique). [`NOUNIQUE`](#pathlibnounique) has no effect on matching functions
such as [`globmatch`](#purepathglobmatch).

For simple patterns, it may make more sense to use [`EXTGLOB`](#pathlibextglob) which will only generate a single pattern
which will perform much better: `@(ab|ac|ad)`.

!!! warning "Massive Expansion Risk"
    1. It is important to note that each pattern is crawled separately, so patterns such as `{1..100}` would generate
    **one hundred** patterns. In a match function ([`globmatch`](#purepathglobmatch)), that would cause a hundred
    compares, and in a file crawling function ([`glob`](#pathglob)), it would cause the file system to be crawled one
    hundred times. Sometimes patterns like this are needed, so construct patterns thoughtfully and carefully.

    2. `BRACE` and [`SPLIT`](#pathlibsplit) both expand patterns into multiple patterns. Using these two syntaxes
    simultaneously can exponential increase in duplicate patterns:

        ```pycon3
        >>> expand('test@(this{|that,|other})|*.py', BRACE | SPLIT | EXTMATCH)
        ['test@(this|that)', 'test@(this|other)', '*.py', '*.py']
        ```

        This effect is reduced as redundant, identical patterns are optimized away[^1], but when using crawling
    functions ([`glob`](#pathglob)) *and* [`NOUNIQUE`](#pathlibnounique) of that optimization is removed, and all of
    those patterns will be crawled. For this reason, especially when using functions like [`glob`](#pathglob), it is
    recommended to use one syntax or the other.

[^1]: Identical patterns are only reduced by comparing case sensitively as POSIX character classes are case sensitive:
`[[:alnum:]]` =/= `[[:ALNUM:]]`.

#### `pathlib.SPLIT, pathlib.S` {: #pathlibsplit}

`SPLIT` is used to take a string of multiple patterns that are delimited by `|` and split them into separate patterns.
This is provided to help with some interfaces that might need a way to define multiple patterns in one input. It pairs
really well with [`EXTGLOB`](#pathlibextglob) and takes into account sequences (`[]`) and extended patterns (`*(...)`) and
will not parse `|` within them.  You can also escape the delimiters if needed: `\|`.

While `SPLIT` is not as powerful as [`BRACE`](#pathlibbrace), it's syntax is very easy to use, and when paired with
[`EXTGLOB`](#pathlibextglob), it feels natural and comes a bit closer. It also much harder to create massive expansions
of patterns with it, except when paired *with* [`BRACE`](#pathlibbrace). See [`BRACE`](#pathlibbrace) and it's warnings
related to pairing it with `SPLIT`.

```pycon3
>>> from wcmatch import pathlib
>>> list(pathlib.Path('.').glob('README.md|LICENSE.md', flags=pathlib.SPLIT))
[WindowsPath('README.md'), WindowsPath('LICENSE.md')]
```

### `pathlib.NOUNIQUE, pathlib.Q` {: #pathlibnounique}

`NOUNIQUE` is used to disable Wildcard Match's unique results return. This mimics Bash's output behavior if that is
desired.

```pycon3
>>> from wcmatch import glob
>>> glob.glob('{*,README}.md', flags=glob.BRACE | glob.NOUNIQUE)
['LICENSE.md', 'README.md', 'README.md']
>>> glob.glob('{*,README}.md', flags=glob.BRACE )
['LICENSE.md', 'README.md']
```

By default, only unique paths are returned in [`glob`](#pathglob) and [`rglob`](#pathrglob). Normally this is what a
programmer would want from such a library, so input patterns are reduced to unique patterns[^1] to reduce excessive
matching with redundant patterns and excessive crawls through the file system. Also, as two different patterns that have
been fed into [`glob`](#pathglob) may match the same file, the results are also filtered as to not return duplicates.

`NOUNIQUE` disables all of the aforementioned "unique" optimizations, but only for [`glob`](#globglob) and
[`rglob`](#pathrglob). Functions like [`globmatch`](#purepathglobmatch) and [`match`](#purepathmatch) would get no
benefit from disabling "unique" optimizations, they would only run slower, so `NOUNIQUE` will be ignored.

!!! new "New in 6.0"
    "Unique" optimizations were added in 6.0, along with `NOUNIQUE`.

#### `pathlib.MATCHBASE, pathlib.X` {: #pathlibmatchbase}

`MATCHBASE`, when a pattern has no slashes in it, will cause all glob related functions to seek for any file anywhere in
the tree with a matching basename, or in the case of [`match`](#purepathmatch) and [`globmatch`](#purepathglobmatch),
path whose basename matches.

```pycon3
>>> from wcmatch import pathlib
>>> list(pathlib.Path('.').glob('*.txt', flags=pathlib.MATCHBASE))
[WindowsPath('docs/src/dictionary/en-custom.txt'), WindowsPath('docs/src/markdown/_snippets/abbr.txt'), WindowsPath('docs/src/markdown/_snippets/links.txt'), WindowsPath('docs/src/markdown/_snippets/posix.txt'), WindowsPath('docs/src/markdown/_snippets/refs.txt'), WindowsPath('requirements/docs.txt'), WindowsPath('requirements/lint.txt'), WindowsPath('requirements/setup.txt'), WindowsPath('requirements/test.txt'), WindowsPath('requirements/tools.txt'), WindowsPath('site/_snippets/abbr.txt'), WindowsPath('site/_snippets/links.txt'), WindowsPath('site/_snippets/posix.txt'), WindowsPath('site/_snippets/refs.txt')]  
```

#### `pathlib.NODIR, pathlib.O` {: #pathlibnodir}

`NODIR` will cause all glob related functions to return only matched files. In the case of
[`PurePath`](#pathlibpurepath) classes, this may not be possible as those classes do not access the file system, nor
will they retain trailing slashes.

```pycon3
>>> from wcmatch import pathlib
>>> list(pathlib.Path('.').glob('*', flags=pathlib.NODIR))
[WindowsPath('appveyor.yml'), WindowsPath('LICENSE.md'), WindowsPath('MANIFEST.in'), WindowsPath('mkdocs.yml'), WindowsPath('README.md'), WindowsPath('setup.cfg'), WindowsPath('setup.py'), WindowsPath('tox.ini')] 
>>> list(pathlib.Path('.').glob('*'))
[WindowsPath('appveyor.yml'), WindowsPath('docs'), WindowsPath('LICENSE.md'), WindowsPath('MANIFEST.in'), WindowsPath('mkdocs.yml'), WindowsPath('README.md'), WindowsPath('requirements'), WindowsPath('setup.cfg'), WindowsPath('setup.py'), WindowsPath('site'), WindowsPath('tests'), WindowsPath('tox.ini'), WindowsPath('wcmatch')]
```

--8<--
refs.txt
--8<--
