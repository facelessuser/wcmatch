# `wcmatch.glob`

```py3
from wcmatch import glob
```

## Syntax

The `glob` library provides methods for traversing the file system and returning files that matched a defined set of
glob patterns.  The library also provides a function called [`globmatch`](#globglobmatch) for matching file paths which
is similar to [`fnmatch`](./fnmatch.md#fnmatchfnmatch), but for paths. In short, [`globmatch`](#globglobmatch) matches
what [`glob`](#globglob) globs :slight_smile:.

!!! tip
    When using backslashes, it is helpful to use raw strings. In a raw string, a single backslash is used to escape a
    character `#!py3 r'\?'`.  If you want to represent a literal backslash, you must use two: `#!py3 r'some\\path'`.

Pattern           | Meaning
----------------- | -------
`*`               | Matches everything except slashes.  On Windows it will avoid matching backslashes as well as slashes.
`**`              | Matches zero or more directories, but will never match the directories `.` and `..`. Requires the [`GLOBSTAR`](#globglobstar) flag.
`?`               | Matches any single character.
`[seq]`           | Matches any character in seq.
`[!seq]`          | Matches any character not in seq.
`[[:alnum:]]`     | POSIX style character classes inside sequences.  The `C` locale is used for byte strings and Unicode properties for Unicode strings. See [POSIX Character Classes](#posix-character-classes) for more info.
`\`               | Escapes characters. If applied to a meta character, it will be treated as a normal character.
`!`               | When used at the start of a pattern, the pattern will be an exclusion pattern. Requires the [`NEGATE`](#globnegate) flag. If also using the [`MINUSNEGATE`](#globminusnegate) flag, `-` will be used instead of `!`.
`?(pattern_list)` | The pattern matches if zero or one occurrences of any of the patterns in the `pattern_list` match the input string. Requires the [`EXTGLOB`](#globextglob) flag.
`*(pattern_list)` | The pattern matches if zero or more occurrences of any of the patterns in the `pattern_list` match the input string. Requires the [`EXTGLOB`](#globextglob) flag.
`+(pattern_list)` | The pattern matches if one or more occurrences of any of the patterns in the `pattern_list` match the input string. Requires the [`EXTGLOB`](#globextglob) flag.
`@(pattern_list)` | The pattern matches if exactly one occurrence of any of the patterns in the `pattern_list` match the input string. Requires the [`EXTGLOB`](#globextglob) flag.
`!(pattern_list)` | The pattern matches if the input string cannot be matched with any of the patterns in the `pattern_list`. Requires the [`EXTGLOB`](#globextglob) flag.
`{}`              | Bash style brace expansions.  This is applied to patterns before anything else. Requires the [`BRACE`](#globbrace) flag.
`~/pattern`       | User path expansion via `~/pattern` or `~user/pattern`. Requires the [`GLOBTILDE`](#globglobtilde) flag.

- Slashes are generally treated special in glob related methods. Slashes are not matched in `[]`, `*`, `?`, or extended
  patterns like `*(...)`. Slashes can be matched by `**` if [`GLOBSTAR`](#globglobstar) is set.

- On Windows, slashes will be normalized in paths and patterns: `/` will become `\\`. There is no need to explicitly use
  `\\` in patterns on Windows, but if you do, it will be handled properly.

- On Windows, drives are treated special and must come at the beginning of the pattern and cannot be matched with `*`,
  `[]`, `?`, or even extended match patterns like `+(...)`.

- Windows drives are recognized as either `C:/` and `//Server/mount/`. If a path uses an ambiguous root (`/some/path`),
  the system will assume the drive of the current working directory.

- Meta characters have no effect when inside a UNC path: `//Server?/mount*/`.

- If [`FORCEUNIX`](#globforceunix) is applied on a Windows system, match and filter commands that do not touch the file
  system will **not** have slashes normalized. In addition, drive letters will also not be handled. Essentially, paths
  will be treated as if on a Linux/Unix system. Commands that do touch the file system ([`glob`](#globglob) and
  [`iglob`](#globiglob)) will ignore [`FORCEUNIX`](#globforceunix) and [`FORCEWIN`](#globforcewin).
  [`globmatch`](#globglobmatch) and [`globfilter`](#globglobfilter), will also ignore [`FORCEUNIX`](#globforceunix) and
  [`FORCEWIN`](#globforcewin) if the [`REALPATH`](#globrealpath) flag is enabled.

    [`FORCEWIN`](#globforcewin) will do the opposite on a Linux/Unix system, and will force Windows logic on a
    Linux/Unix system. Like with [`FORCEUNIX`](#globforceunix), it only applies to commands that don't touch the file
    system.

- By default, file and directory names starting with `.` are only matched with literal `.`.  The patterns `*`, `**`,
  `?`, and `[]` will not match a leading `.`.  To alter this behavior, you can use the [`DOTGLOB`](#globdotglob) flag.

- Even with [`DOTGLOB`](#globdotglob) enabled, special tokens will not match a special directory (`.` or `..`).  But
  when a literal `.` is used at the start of the pattern (`.*`, `.`, `..`, etc.), `.` and `..` can potentially be
  matched.

- In general, Wildcard Match's behavior is modeled off of Bash's, so unlike Python's default [`glob`][glob], Wildcard
  Match's `glob` will match and return `.` and `..` in certain cases just like Bash does.

    Python's default:

    ```pycon3
    >>> import glob
    >>> glob.glob('docs/.*')
    []
    ```

    Wcmatch:

    ```pycon3
    >>> from wcmatch import glob
    >>> glob.glob('docs/.*')
    ['docs/.', 'docs/..']
    ```

    Bash:

    ```shell-session
    $ echo docs/.*
    docs/. docs/..
    ```

--8<-- "posix.txt"

## Multi-Pattern Limits

Many of the API functions allow passing in multiple patterns or using either [`BRACE`](#globbrace) or
[`SPLIT`](#globsplit) to expand a pattern in to more patterns. The number of allowed patterns is limited `1000`, but you
can raise or lower this limit via the keyword option `limit`. If you set `limit` to `0`, there will be
no limit.

!!! new "New 6.0"
    The imposed pattern limit and corresponding `limit` option was introduced in 6.0.

## API

#### `glob.glob`

```py3
def glob(patterns, *, flags=0, root_dir=None, limit=1000):
```

`glob` takes a pattern (or list of patterns), flags, and an option root directory (string or path-like object). It also
allows configuring the [max pattern limit](#multi-pattern-limits). When executed it will crawl the file system returning
matching files.

!!! warning "Path-like Input Support"
    Path-like object input support is only available in Python 3.6+ as the path-like protocol was added in Python 3.6.

```pycon3
>>> from wcmatch import glob
>>> glob.glob(r'**/*.md')
['docs/src/markdown/_snippets/abbr.md', 'docs/src/markdown/_snippets/links.md', 'docs/src/markdown/_snippets/refs.md', 'docs/src/markdown/changelog.md', 'docs/src/markdown/fnmatch.md', 'docs/src/markdown/glob.md', 'docs/src/markdown/index.md', 'docs/src/markdown/installation.md', 'docs/src/markdown/license.md', 'README.md']
```

Using a list, we can add exclusion patterns and also exclude directories and/or files:

```pycon3
>>> from wcmatch import glob
>>> glob.glob([r'**/*.md', r'!README.md', r'!**/_snippets'], flags=glob.NEGATE)
['docs/src/markdown/changelog.md', 'docs/src/markdown/fnmatch.md', 'docs/src/markdown/glob.md', 'docs/src/markdown/index.md', 'docs/src/markdown/installation.md', 'docs/src/markdown/license.md']
```

When a glob pattern ends with a slash, it will only return directories:

```pycon3
>>> from wcmatch import glob
>>> glob.glob(r'**/')
['__pycache__/', 'docs/', 'docs/src/', 'docs/src/markdown/', 'docs/src/markdown/_snippets/', 'docs/theme/', 'requirements/', 'stuff/', 'tests/', 'tests/__pycache__/', 'wcmatch/', 'wcmatch/__pycache__/']
```

When providing a list, all patterns are run in the same context, but will not be run in the same pass. Each pattern is
run in a separate pass, except for exclusion patterns (see the [`NEGATE`](#globnegate) flag) which are applied as
filters to the inclusion patterns. Since each pattern is run in its own pass, it is possible for many directories to be
researched multiple times. In Bash, duplicate files can be returned:

```console
$ echo *.md README.md
LICENSE.md README.md README.md
```

And we see that Wildcard Match's `glob` behaves the same, except it only returns unique results.

```pycon3
>>> from wcmatch import glob
>>> glob.glob(['*.md', 'README.md'])
['LICENSE.md', 'README.md']
```

If we wanted to completely match Bash's results, we would turn off unique results with the [`NOUNIQUE`](#globnounique)
flag.

```pycon3
>>> from wcmatch import glob
>>> glob.glob(['*.md', 'README.md'], flags=glob.NOUNIQUE)
['LICENSE.md', 'README.md', 'README.md']
```

And if we apply an exclusion pattern, since the patterns share the same context, the exclusion applies to both:

```pycon3
>>> from wcmatch import glob
>>> glob.glob(['*.md', , 'README.md', '!README.md'], flags=glob.NEGATE | glob.NOUNIQUE)
['LICENSE.md']
```

Features like [`BRACE`](#globbrace) and [`SPLIT`](#globsplit) actually take a single string and breaks them up into
multiple patterns. These features, when enabled and used, will also exhibit this behavior:

```pycon3
>>> from wcmatch import glob
>>> glob.glob('{*,README}.md', flags=glob.BRACE | glob.NOUNIQUE)
['LICENSE.md', 'README.md', 'README.md']
```

This also aligns with Bash's behavior:

```console
$ echo {*,README}.md
LICENSE.md README.md README.md
```

You can resolve user paths with `~` if the [`GLOBTILDE`](#globglobtilde) flag is enabled. You can also target specific
users with `~user`.

```pycon3
>>> from wcmatch import glob
>>> glob.glob('~', flags=glob.GLOBTILDE)
['/home/facelessuser']
>>> glob.glob('~root', flags=glob.GLOBTILDE)
['/root']
```

By default, `glob` uses the current working directory to evaluate relative patterns. Normally you'd have to use
`#!py3 os.chdir('/new/path')` to evaluate patterns relative to a different path. By setting `root_dir` parameter you can
change the root path without using `os.chdir`.

```pycon3
>>> from wcmatch import glob
>>> glob.glob('*')
['appveyor.yml', 'docs', 'LICENSE.md', 'MANIFEST.in', 'mkdocs.yml', 'README.md', 'requirements', 'setup.cfg', 'setup.py', 'tests', 'tox.ini', 'wcmatch']
>>> glob.glob('*', root_dir='docs/src')
['dictionary', 'markdown']
```

!!! new "New 5.1"
    `root_dir` was added in 5.1.0.

!!! new "New 6.0"
    `limit` was added in 6.0.

#### `glob.iglob`

```py3
def iglob(patterns, *, flags=0, root_dir=None, limit=1000):
```

`iglob` is just like [`glob`](#globglob) except it returns an iterator.

```pycon3
>>> from wcmatch import glob
>>> list(glob.iglob(r'**/*.md'))
['docs/src/markdown/_snippets/abbr.md', 'docs/src/markdown/_snippets/links.md', 'docs/src/markdown/_snippets/refs.md', 'docs/src/markdown/changelog.md', 'docs/src/markdown/fnmatch.md', 'docs/src/markdown/glob.md', 'docs/src/markdown/index.md', 'docs/src/markdown/installation.md', 'docs/src/markdown/license.md', 'README.md']
```

!!! new "New 5.1"
    `root_dir` was added in 5.1.0.

!!! new "New 6.0"
    `limit` was added in 6.0.

#### `glob.globmatch`

```py3
def globmatch(filename, patterns, *, flags=0, root_dir=None, limit=1000):
```

`globmatch` takes a file name (string or path-like object), a pattern (or list of patterns), flags, and an optional root
directory.  It also allows configuring the [max pattern limit](#multi-pattern-limits). It will return a boolean
indicating whether the file path was matched by the pattern(s).

!!! warning "Path-like Input Support"
    Path-like object input support is only available in Python 3.6+ as the path-like protocol was added in Python 3.6.

```pycon3
>>> from wcmatch import glob
>>> glob.globmatch('some/path/test.txt', r'**/*/@(*.txt|*.py)')
True
```

When applying multiple patterns, a file path matches if it matches any of the patterns:

```pycon3
>>> from wcmatch import glob
>>> glob.globmatch('some/path/test.txt', [r'**/*/*.txt', r'**/*/*.py'])
True
```

Exclusion patterns are allowed as well. When exclusion patterns are used in conjunction with other patterns, a path will
be considered matched if one of the positive patterns match **and** none of the exclusion patterns match. If an
exclusion pattern is given without any inclusion patterns, the pattern will match nothing. Exclusion patterns are meant
to filter other patterns, not match anything by themselves.

```pycon3
>>> from wcmatch import glob
>>> glob.globmatch('some/path/test.py', r'**|!**/*.txt', flags=glob.NEGATE | glob.GLOBSTAR | glob.SPLIT)
True
>>> glob.globmatch('some/path/test.txt', r'**|!**/*.txt', flags=glob.NEGATE | glob.GLOBSTAR | glob.SPLIT)
False
>>> glob.globmatch('some/path/test.txt', [r'*/*/*.txt', r'!*/*/avoid.txt'], flags=glob.NEGATE)
True
>>> glob.globmatch('some/path/avoid.txt', [r'*/*/*.txt', r'!*/*/avoid.txt'], flags=glob.NEGATE)
False
```

As mentioned, exclusion patterns need to be applied to a inclusion pattern to work, but if it is desired, you can force
exclusion patterns to assume all files should be filtered with the exclusion pattern(s) with the
[`NEGATEALL`](#globnegateall) flag. Essentially, it means if you use a pattern such as `!*.md`, it means if you use a
pattern such as `!*.md`, it will assume two pattern were given: `*` and `!*.md` (where `**` is specifically treated as
if [`GLOBSTAR`](#globglobstar) was enabled).

```pycon3
>>> from wcmatch import glob
>>> glob.globmatch('some/path/test.py', r'!**/*.txt', flags=glob.NEGATE | glob.GLOBSTAR | glob.NEGATEALL)
True
>>> glob.globmatch('some/path/test.txt', r'!**/*.txt', flags=glob.NEGATE | glob.GLOBSTAR | glob.NEGATEALL)
False
```

By default, `globmatch` and [`globfilter`](#globglobfilter) do not operate on the file system. This is to allow you to
process paths from any source, even paths that are not on your current system. So if you are trying to explicitly match
a directory with a pattern such as `*/`, your path must end with a slash (`my_directory/`) to be recognized as a
directory. It also won't be able to evaluate whether a directory is a symlink or not as it will have no way of checking.
Here we see that `globmatch` fails to match the filepath as the pattern is explicitly looking for a directory and our
filepath does not end with `/`.

```pycon3
>>> from wcmatch import glob
>>> glob.globmatch('docs', '*/')
False
```

If you would like for `globmatch` (or [`globfilter`](#globglobfilter)) to operate on your current filesystem directly,
simply pass in the [`REALPATH`](#globrealpath) flag. When enabled, the path under consideration will be analyzed and
will use that context to determine if the file exists, if it is a directory, does it's context make sense compared to
what the pattern is looking vs the current working directory, or if it has symlinks that should not be matched by
[`GLOBSTAR`](#globglobstar).

Here we use [`REALPATH`](#globrealpath) and can see that `globmatch` now knows that `doc` is a directory.

```pycon3
>>> from wcmatch import glob
>>> glob.globmatch('docs', '*/', flags=glob.REALPATH)
True
```

It also can tell if a file doesn't exist or is out of scope compared to what is being asked. For instance, the below
example fails because the pattern is looking for any folder that is relative to the current path, which `/usr` is not.
When we disable [`REALPATH`](#globrealpath), it will match just fine. Both cases can be useful depending on how you plan
to use `globmatch`.

```pycon3
>>> from wcmatch import glob
>>> glob.globmatch('/usr', '**/', flags=glob.G | glob.REALPATH)
False
>>> glob.globmatch('/usr', '**/', flags=glob.G)
True
```

If you are using [`REALPATH`](#globrealpath) and want to evaluate the paths relative to a different directory, you can
set the `root_dir` parameter.

```pycon3
>>> from wcmatch import glob
>>> glob.globmatch('markdown', 'markdown', flags=glob.REALPATH)
False
>>> glob.globmatch('markdown', 'markdown', flags=glob.REALPATH, root_dir='docs/src')
True
```

!!! new "New 5.1"
    - `root_dir` was added in 5.1.0.
    - path-like object support for file path inputs was added in 5.1.0

!!! new "New 6.0"
    `limit` was added in 6.0.

#### `glob.globfilter`

```py3
def globfilter(filenames, patterns, *, flags=0, root_dir=None, limit=1000):
```

`globfilter` takes a list of file paths (strings or path-like objects), a pattern (or list of patterns), and flags. It
also allows configuring the [max pattern limit](#multi-pattern-limits). It returns a list of all files paths that
matched the pattern(s). The same logic used for [`globmatch`](#globglobmatch) is used for `globfilter`, albeit more
efficient for processing multiple files.

!!! warning "Path-like Input Support"
    Path-like object input support is only available in Python 3.6+ as the path-like protocol was added in Python 3.6.

```pycon3
>>> from wcmatch import glob
>>> glob.globfilter(['some/path/a.txt', 'b.txt', 'another/path/c.py'], r'**/*.txt')
['some/path/a.txt', 'b.txt']
```

Like [`globmatch`](#globglobmatch), `globfilter` does not operate directly on the file system, with all the caveats
associated. But you can enable the [`REALPATH`](#globrealpath) flag and `globfilter` will use the filesystem to gain
context such as: whether the file exists, whether it is a directory or not, or whether it has symlinks that should not
be matched by `GLOBSTAR`. See [`globmatch`](#globglobmatch) for examples.

!!! new "New 5.1"
    - `root_dir` was added in 5.1.0.
    - path-like object support for file path inputs was added in 5.1.0

!!! new "New 6.0"
    `limit` was added in 6.0.

#### `glob.translate`

```py3
def translate(patterns, *, flags=0, limit=1000):
```

`translate` takes a file pattern (or list of patterns) and flags. It also allows configuring the [max pattern
limit](#multi-pattern-limits). It returns two lists: one for inclusion patterns and one for exclusion patterns. The
lists contain the regular expressions used for matching the given patterns. It should be noted that a file is considered
matched if it matches at least one inclusion pattern and matches **none** of the exclusion patterns.

```pycon3
>>> from wcmatch import glob
>>> glob.translate(r'**/*.{py,txt}')
(['^(?s:(?:(?!(?:\\/|^)\\.).)*?(?:^|$|\\/)+(?=.)(?!(?:\\.{1,2})(?:$|\\/))(?:(?!\\.)[^\\/]*?)?\\.py[\\/]*?)$', '^(?s:(?:(?!(?:\\/|^)\\.).)*?(?:^|$|\\/)+(?=.)(?!(?:\\.{1,2})(?:$|\\/))(?:(?!\\.)[^\\/]*?)?\\.txt[\\/]*?)$'], [])
>>> glob.translate(r'**|!**/*.{py,txt}', flags=glob.NEGATE | glob.SPLIT)
(['^(?s:(?=.)(?!(?:\\.{1,2})(?:$|\\/))(?:(?!\\.)[^\\/]*?)?[\\/]*?)$'], ['^(?s:(?=.)(?!(?:\\.{1,2})(?:$|\\/))[^\\/]*?\\/+(?=.)(?!(?:\\.{1,2})(?:$|\\/))[^\\/]*?\\.\\{py\\,txt\\}[\\/]*?)$'])
```

!!! warning "Changed 4.0"
    Translate now outputs exclusion patterns so that if they match, the file is excluded. This is opposite logic to how
    it used to be, but is more efficient.

!!! new "New 6.0"
    `limit` was added in 6.0.

#### `glob.escape`

```py3
def escape(pattern, unix=None):
```

This escapes special glob meta characters so they will be treated as literal characters.  It escapes using backslashes.
It will escape `-`, `!`, `*`, `?`, `(`, `[`, `|`, `^`, `{`, and `\`. On Windows, it will specifically only escape `\`
when not already escaped (`\\`). `/` and `\\` (on Windows) are not escaped as they are path separators.

```pycon3
>>> from wcmatch import glob
>>> glob.escape('some/path?/**file**{}.txt')
'some/path\\?/\\*\\*file\\*\\*\\{}.txt'
>>> glob.globmatch('some/path?/**file**{}.txt', glob.escape('some/path?/**file**{}.txt'))
True
```

On a Windows system, drives are not escaped since meta characters are not parsed in drives. Drives on Windows are
generally treated special. This is because a drive could contain special characters like in `\\?\c:\`.

`escape` will detect the system it is running on and pick Windows escape logic or Linux/Unix logic. Since
[`globmatch`](#globglobmatch) allows you to match Unix style paths on a Windows system, and vice versa. You can force
Unix style escaping or Windows style escaping via the `unix` parameter. When `unix` is `None`, the escape style will be
detected, when `unix` is `True` Linux/Unix style escaping will be used, and when `unix` is `False` Windows style
escaping will be used.

```pycon3
>>> glob.escape('some/path?/**file**{}.txt', platform=glob.UNIX)
```

!!! new "New 5.0"
    The `unix` parameter is now `None` by default. Set to `True` to force Linux/Unix style escaping or set to `False` to
    force Windows style escaping.

#### `glob.raw_escape`

```py3
def raw_escape(pattern, unix=None):
```

This is like [`escape`](#globescape) except it will apply raw character string escapes before doing meta character
escapes.  This is meant for use with the [`RAWCHARS`](#globrawchars) flag.

```pycon3
>>> from wcmatch import glob
>>> glob.raw_escape(r'some/path?/\x2a\x2afile\x2a\x2a{}.txt')
'some/path\\?/\\*\\*file\\*\\*\\{}.txt'
>>> glob.globmatch('some/path?/**file**{}.txt', glob.escape(r'some/path?/\x2a\x2afile\x2a\x2a{}.txt'), flags=glob.RAWCHARS)
True
```

`raw_escape` will detect the system it is running on and pick Windows escape logic or Linux/Unix logic. Since
[`globmatch`](#globglobmatch) allows you to match Unix style paths on a Windows system, and vice versa. You can force
Unix style escaping or Windows style escaping via the `unix` parameter. When `unix` is `None`, the escape style will be
detected, when `unix` is `True` Linux/Unix style escaping will be used, and when `unix` is `False` Windows style
escaping will be used.

```pycon3
>>> glob.raw_escape(r'some/path?/\x2a\x2afile\x2a\x2a{}.txt', platform=glob.UNIX)
```

!!! new "New 5.0"
    The `unix` parameter is now `None` by default. Set to `True` to force Linux/Unix style escaping or set to `False` to
    force Windows style escaping.

## Flags

#### `glob.CASE, glob.C` {: #globcase}

`CASE` forces case sensitivity. `CASE` has higher priority than [`IGNORECASE`](#globignorecase).

On Windows, drive letters (`C:`) and UNC host/share (`//host/share`) portions of a path will still be treated case
insensitively, but the rest of the path will have case sensitive logic applied.

!!! new "New 4.3"
    `CASE` is new in 4.3.0.

#### `glob.IGNORECASE, glob.I` {: #globignorecase}

`IGNORECASE` forces case insensitivity. [`CASE`](#globcase) has higher priority than `IGNORECASE`.

#### `glob.RAWCHARS, glob.R` {: #globrawchars}

`RAWCHARS` causes string character syntax to be parsed in raw strings: `#!py3 r'\u0040'` --> `#!py3 r'@'`. This will
handle standard string escapes and Unicode including `#!py3 r'\N{CHAR NAME}'`.

#### `glob.NEGATE, glob.N` {: #globnegate}

`NEGATE` causes patterns that start with `!` to be treated as exclusion patterns. A pattern of `!*.py` would match any
file but Python files. Exclusion patterns cannot be used by themselves though, and must be paired with a normal,
inclusion pattern, either by utilizing the [`SPLIT`](#globSPLIT) flag, or providing multiple patterns in a list.
Assuming the [`SPLIT`](#globsplit) flag, this means using it in a pattern such as `inclusion|!exclusion`.

If it is desired, you can force exclusion patterns, when no inclusion pattern is provided, to assume all files match
unless the file matches the excluded pattern. This is done with the [`NEGATEALL`](#globnegateall) flag.

If used with the extended glob feature, patterns like `!(inverse|pattern)` will be mistakenly parsed as an exclusion
pattern instead of as an inverse extended glob group.  See [`MINUSNEGATE`](#globminusgate) for an alternative syntax
that plays nice with extended glob.

!!! warning "Changes 4.0"
    In 4.0, `NEGATE` now requires a non-exclusion pattern to be paired with it or it will match nothing. If you really
    need something similar to the old behavior, that would assume a default inclusion pattern, you can use the
    [`NEGATEALL`](#globnegateall).

#### `glob.NEGATEALL, glob.A` {: #globnegateall}

`NEGATEALL` can force exclusion patterns, when no inclusion pattern is provided, to assume all files match unless the
file matches the excluded pattern. Essentially, it means if you use a pattern such as `!*.md`, it will assume two
patterns were given: `**` and `!*.md`, where `!*.md` is applied to the results of `**`, and `**` is specifically treated
as if [`GLOBSTAR`](#globglobstar) was enabled.

Dot files will not be returned unless [`DOTGLOB`](#globdotglob) is enabled. Symlinks will also be ignored in the return
unless [`FOLLOW`](#globfollow) is enabled.

#### `glob.MINUSNEGATE, glob.M` {: #globminusnegate}

When `MINUSNEGATE` is used with [`NEGATE`](#globnegate), exclusion patterns are recognized by a pattern starting with
`-` instead of `!`. This plays nice with the extended glob feature which already uses `!` in patterns such as `!(...)`.

#### `glob.GLOBSTAR, glob.G` {: #globglobstar}

`GLOBSTAR` enables the feature where `**` matches zero or more directories.

!!! new "New 3.0"
    `GLOBSTAR` will no longer match or traverse symlink directories. This models the recent behavior in Bash 5.0. To
    crawl symlink directories, the new [`FOLLOW`](#globfollow) flag must be enabled.

#### `glob.FOLLOW, glob.L` {: #globfollow}

`FOLLOW` will cause [`GLOBSTAR`](#globglobstar) patterns (`**`) to match and traverse symlink directories.

!!! new "New 3.0"
    `FOLLOW` was added in 3.0.

#### `glob.REALPATH, glob.P` {: #globrealpath}

In the past, only [`glob`](#globglob) and [`iglob`](#globiglob) operated on the filesystem, but with `REALPATH`, other
functions will now operate on the filesystem as well: [`globmatch`](#globglobmatch) and [`globfilter`](#globglobfilter).

Normally, functions such as [`globmatch`](#globglobmatch) would simply match a path with regular expression and return
the result. The functions were not concerned with whether the path existed or not. It didn't care if it was even valid
for the operating system.

`REALPATH` forces [`globmatch`](#globglobmatch) and [`globfilter`](#globglobfilter) to treat the string path as a real
file path for the given system it is running on. It will augment the patterns used to match files and enable additional
logic so that the path must meet the following in order to match:

- Path must exist.
- Directories that are symlinks will not be matched by [`GLOBSTAR`](#globglobstar) patterns (`**`) unless the
  [`FOLLOW`](#globfollow) flag is enabled.
- When presented with a pattern where the match must be a directory, but the file path being compared doesn't indicate
  the file is a directory with a trailing slash, the command will look at the filesystem to determine if it is a
  directory.
- Paths must match in relation to the current working directory unless the pattern is constructed in a way to indicates
  an absolute path.

Since `REALPATH` causes the file system to be referenced when matching a path, flags such as
[`FORCEUNIX`](#globforceunix) and [`FORCEWIN`](#globforcewin) are not allowed with this flag and will be ignored.

!!! new "New 3.0"
    `REALPATH` was added in 3.0.

#### `glob.DOTGLOB, glob.D` {: #globdotglob}

By default, [`glob`](#globglob) and [`globmatch`](#globglobmatch) will not match file or directory names that start with
dot `.` unless matched with a literal dot. `DOTGLOB` allows the meta characters (such as `*`) to glob dots like any
other character. Dots will not be matched in `[]`, `*`, or `?`.

Alternatively `DOTMATCH` will also be accepted for consistency with the other provided libraries. Both flags are exactly
the same and are provided as a convenience in case the user finds one more intuitive than the other since `DOTGLOB` is
often the name used in Bash.

#### `glob.EXTGLOB, glob.E` {: #globextglob}

`EXTGLOB` enables extended pattern matching which includes special pattern lists such as `+(...)`, `*(...)`, `?(...)`,
etc. See the [syntax overview](#syntax) for more information.

Alternatively `EXTMATCH` will also be accepted for consistency with the other provided libraries. Both flags are exactly
the same and are provided as a convenience in case the user finds one more intuitive than the other since `EXTGLOB` is
often the name used in Bash.

!!! tip "EXTMATCH and NEGATE"
    When using `EXTMATCH` and [`NEGATE`](#globnegate) together, it is recommended to also use
    [`MINUSNEGATE`](#globminusnegate) to avoid conflicts in regards to the `!` meta character.

#### `glob.BRACE, glob.B` {: #globbrace}

`BRACE` enables Bash style brace expansion: `a{b,{c,d}}` --> `ab ac ad`. Brace expansion is applied before anything
else. When applied, a pattern will be expanded into multiple patterns. Each pattern will then be parsed separately.

Redundant, identical patterns are discarded[^1] by default, and `glob` and `iglob` will limit the returned values to
unique results. If you need [`glob`](#globglob) or [`iglob`](#globiglob) to behave more like Bash and return all
results, you can set [`NOUNIQUE`](#globnounique). [`NOUNIQUE`](#globnounique) has no effect on matching functions such
as [`globmatch`](#globglobmatch).

For simple patterns, it may make more sense to use [`EXTGLOB`](#globextglob) which will only generate a single pattern
which will perform much better: `@(ab|ac|ad)`.

!!! warning "Massive Expansion Risk"
    1. It is important to note that each pattern is crawled separately, so patterns such as `{1..100}` would generate
    **one hundred** patterns. In a match function ([`globmatch`](#globglobmatch)), that would cause a hundred compares,
    and in a file crawling function ([`glob`](#globglob)), it would cause the file system to be crawled one hundred
    times. Sometimes patterns like this are needed, so construct patterns thoughtfully and carefully.

    2. `BRACE` and [`SPLIT`](#globsplit) both expand patterns into multiple patterns. Using these two syntaxes
    simultaneously can exponential increase in duplicate patterns:

        ```pycon3
        >>> expand('test@(this{|that,|other})|*.py', BRACE | SPLIT | EXTMATCH)
        ['test@(this|that)', 'test@(this|other)', '*.py', '*.py']
        ```

        This effect is reduced as redundant, identical patterns are optimized away[^1], but when using crawling
    functions ([`glob`](#globglob)) *and* [`NOUNIQUE`](#globnounique) of that optimization is removed, and all of those
    patterns will be crawled. For this reason, especially when using functions like [`glob`](#globglob), it is
    recommended to use one syntax or the other.

[^1]: Identical patterns are only reduced by comparing case sensitively as POSIX character classes are case sensitive:
`[[:alnum:]]` =/= `[[:ALNUM:]]`.

#### `glob.SPLIT, glob.S` {: #globsplit}

`SPLIT` is used to take a string of multiple patterns that are delimited by `|` and split them into separate patterns.
This is provided to help with some interfaces that might need a way to define multiple patterns in one input. It pairs
really well with [`EXTGLOB`](#globextglob) and takes into account sequences (`[]`) and extended patterns (`*(...)`) and
will not parse `|` within them.  You can also escape the delimiters if needed: `\|`.

While `SPLIT` is not as powerful as [`BRACE`](#globbrace), it's syntax is very easy to use, and when paired with
[`EXTGLOB`](#globextglob), it feels natural and comes a bit closer. It also much harder to create massive expansions
of patterns with it, except when paired *with* [`BRACE`](#globbrace). See [`BRACE`](#globbrace) and it's warnings
related to pairing it with `SPLIT`.

```pycon3
>>> from wcmatch import glob
>>> glob.globmatch('test.txt', r'*.txt|*.py', flags=fnmatch.SPLIT)
True
>>> glob.globmatch('test.py', r'*.txt|*.py', flags=fnmatch.SPLIT)
True
```

### `glob.NOUNIQUE, glob.Q` {: #globnounique}

`NOUNIQUE` is used to disable Wildcard Match's unique results return. This mimics Bash's output behavior if that is
desired.

```pycon3
>>> from wcmatch import glob
>>> glob.glob('{*,README}.md', flags=glob.BRACE | glob.NOUNIQUE)
['LICENSE.md', 'README.md', 'README.md']
>>> glob.glob('{*,README}.md', flags=glob.BRACE )
['LICENSE.md', 'README.md']
```

By default, only unique paths are returned in [`glob`](#globglob) and [`iglob`](#globiglob). Normally this is what a
programmer would want from such a library, so input patterns are reduced to unique patterns[^1] to reduce excessive
matching with redundant patterns and excessive crawls through the file system. Also, as two different patterns that have
been fed into [`glob`](#globglob) may match the same file, the results are also filtered as to not return duplicates.

`NOUNIQUE` disables all of the aforementioned "unique" optimizations, but only for [`glob`](#globglob) and
[`iglob`](#globiglob). Functions like [`globmatch`](#globglobmatch) and [`globfilter`](#globglobfilter) would get no
benefit from disabling "unique" optimizations, they would only run slower, so `NOUNIQUE` will be ignored.

!!! new "New in 6.0"
    "Unique" optimizations were added in 6.0, along with `NOUNIQUE`.

#### `glob.GLOBTILDE, glob.T` {: #globglobtilde}

`GLOBTILDE` allows for user path expansion via `~`. You can get the current user path by using `~` at the start of a path.
`~` can be used as the entire pattern, or it must be followed by a directory slash: `~/more-pattern`.

To specify a specific user, you can explicitly specify a user name via `~user`. If additional pattern is needed, the
user name must be followed by a directory slash: `~user/more-pattern`.

```pycon3
>>> from wcmatch import glob
>>> glob.glob('~', flags=glob.GLOBTILDE)
['/home/facelessuser']
>>> glob.glob('~root', flags=glob.GLOBTILDE)
['/root']
```

`GLOBTILDE` can also be used in things like [`globfilter`](#globglobfilter) or [`globmatch`](#globglobmatch), but you must
be using [`REALPATH`](#globrealpath) or the user path will not be expanded.

```pycon3
from wcmatch import glob
>>> glob.globmatch('/home/facelessuser/', '~', flags=glob.GLOBTILDE | glob.REALPATH)
True
```

!!! new "New 6.0"
    Tilde expansion with `GLOBTILDE` was added in version 6.0.

#### `glob.MARK, glob.K` {: #globmark}

`MARK` ensures that [`glob`](#globglob) and [`iglob`](#globiglob) to return all directories with a trailing slash. This
makes it very clear which paths are directories and allows you to save calling `os.path.isdir` as you can simply check
for a path separator at the end of the path. This flag only applies to calls to `glob` or `iglob`.

If you are passing the returned files from `glob` to [`globfilter`](#globglobfilter) or [`globmatch`](#globglobmatch),
it is important to ensure directory paths have trailing slashes as these functions have no way of telling the path is a
directory otherwise (except when [`REALPATH`](#globrealpath) is enabled). If you have [`REALPATH`](#globrealpath)
enabled, ensuring the files have trailing slashes can still save you a call to `os.path.isdir` as
[`REALPATH`](#globrealpath) resorts to calling it if there is no trailing slash.

```pycon3
>>> from wcmatch import glob
>>> glob.glob('*', flags=glob.MARK)
['appveyor.yml', 'base.patch', 'basematch.diff', 'docs/', 'LICENSE.md', 'MANIFEST.in', 'mkdocs.yml', 'README.md', 'requirements/', 'setup.cfg', 'setup.py', 'tests/', 'tools/', 'tox.ini', 'wcmatch/']
>>> glob.glob('*')
['appveyor.yml', 'base.patch', 'basematch.diff', 'docs', 'LICENSE.md', 'MANIFEST.in', 'mkdocs.yml', 'README.md', 'requirements', 'setup.cfg', 'setup.py', 'tests', 'tools', 'tox.ini', 'wcmatch']
```

!!! new "New 4.0"
    `MARK` added in 4.0.

#### `glob.MATCHBASE, glob.X` {: #globmatchbase}

`MATCHBASE`, when a pattern has no slashes in it, will cause [`glob`](#globglob) and [`iglob`](#globiglob) to seek for
any file anywhere in the tree with a matching basename. When enabled for [`globfilter`](#globglobfilter) and
[`globmatch`](#globglobmatch), any path whose basename matches.

```pycon3
>>> from wcmatch import glob
>>> glob.glob('*.txt', flags=glob.MATCHBASE)
['docs/src/dictionary/en-custom.txt', 'docs/src/markdown/_snippets/abbr.txt', 'docs/src/markdown/_snippets/links.txt', 'docs/src/markdown/_snippets/posix.txt', 'docs/src/markdown/_snippets/refs.txt', 'requirements/docs.txt', 'requirements/lint.txt', 'requirements/setup.txt', 'requirements/test.txt', 'requirements/tools.txt']
```

!!! new "New 4.0"
    `MATCHBASE` added in 4.0.

#### `glob.NODIR, glob.O` {: #globnodir}

`NODIR` will cause [`glob`](#globglob), [`iglob`](#globiglob), [`globmatch`](#globglobmatch), and [`globfilter`](#globglobfilter) to return only matched files.

```pycon3
>>> from wcmatch import glob
>>> glob.glob('*', flags=glob.NODIR)
['appveyor.yml', 'LICENSE.md', 'MANIFEST.in', 'mkdocs.yml', 'README.md', 'setup.cfg', 'setup.py', 'spell.log', 'tox.ini']
>>> glob.glob('*')
['appveyor.yml', 'docs', 'LICENSE.md', 'MANIFEST.in', 'mkdocs.yml', 'README.md', 'requirements', 'setup.cfg', 'setup.py', 'spell.log', 'tests', 'tools', 'tox.ini', 'wcmatch']
```

#### `glob.FORCEWIN, glob.W` {: #globforcewin}

`FORCEWIN` will force Windows path and case logic to be used on Linux/Unix systems. It will also cause slashes to be
normalized and Windows drive syntax to be handled special. This is great if you need to match Windows specific paths on
a Linux/Unix system. This will only work on commands that do not access the file system: [`translate`](#globtranslate),
[`globmatch`](#globglobmatch), [`globfilter`](#globglobfilter), etc. These flags will not work with [`glob`](#globglob)
or [`iglob`](#globiglob). It also will not work when using the [`REALPATH`](#globrealpath) flag with things like
[`globmatch`](#globglobmatch) and [`globfilter`](#globglobfilter).

If `FORCEWIN` is used along side [`FORCEUNIX`](#globforceunix), both will be ignored.

!!! new "New 4.2"
    `FORCEWIN` is new in 4.2.0.

#### `glob.FORCEUNIX, glob.U` {: #globforceunix}

`FORCEUNIX` will force Linux/Unix path and case logic to be used on Windows systems. This is great if you need to match
Linux/Unix specific paths on a Windows system. This will only work on commands that do not access the file system:
[`translate`](#globtranslate), [`globmatch`](#globglobmatch), [`globfilter`](#globglobfilter), etc. These flags will not
work with [`glob`](#globglob) or [`iglob`](#globiglob). It also will not work when using the [`REALPATH`](#globrealpath)
flag with things like [`globmatch`](#globglobmatch) and [`globfilter`](#globglobfilter).

When using `FORCEUNIX`, the paths are assumed to be case sensitive, but you can use [`IGNORECASE`](#globignorecase) to
use case insensitivity.

If `FORCEUNIX` is used along side [`FORCEWIN`](#globforcewin), both will be ignored.

!!! new "New 4.2"
    `FORCEUNIX` is new in 4.2.0.

--8<--
refs.txt
--8<--
