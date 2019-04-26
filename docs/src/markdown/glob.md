# `wcmatch.glob`

```py3
from wcmatch import glob
```

## Syntax

The `glob` library provides methods for traversing the file system and returning files that matched a defined set of glob patterns.  The library also provides functions for matching file paths which is similar to [`fnmatch`](fnmatch#fnmatchfnmatch), but for paths. In short, [`globmatch`](#globglobmatch) matches what [`glob`](#globglob) globs :slight_smile:. `globmatch`'s features are similar to `fnmatch`'s.

!!! tip
    When using backslashes, it is helpful to use raw strings. In a raw string, a single backslash is used to escape a character `#!py3 r'\?'`.  If you want to represent a literal backslash, you must use two: `#!py3 r'some\\path'`.

Pattern           | Meaning
----------------- | -------
`*`               | Matches everything except slashes.  On Windows it will avoid matching backslashes as well as slashes.
`**`              | Matches zero or more directories, but will never match the directories `.` and `..`.
`?`               | Matches any single character.
`[seq]`           | Matches any character in seq.
`[!seq]`          | Matches any character not in seq.
`[[:alnum:]]`     | POSIX style character classes inside sequences.  The `C` locale is used for byte strings and Unicode properties for Unicode strings. See [POSIX Character Classes](#posix-character-classes) for more info.
`\`               | Escapes characters. If applied to a meta character, it will be treated as a normal character.
`!`               | Inverse pattern (with configuration, can use `-` instead of `!`).
`?(pattern_list)` | The pattern matches if zero or one occurrences of any of the patterns in the `pattern_list` match the input string.
`*(pattern_list)` | The pattern matches if zero or more occurrences of any of the patterns in the `pattern_list` match the input string.
`+(pattern_list)` | The pattern matches if one or more occurrences of any of the patterns in the `pattern_list` match the input string.
`@(pattern_list)` | The pattern matches if exactly one occurrence of any of the patterns in the `pattern_list` match the input string.
`!(pattern_list)` | The pattern matches if the input string cannot be matched with any of the patterns in the `pattern_list`.
`{}`              | Bash style brace expansions.  This is applied to patterns before anything else.

- Slashes are generally treated special in glob related methods. Slashes are not matched in `[]`, `*`, `?`, or extended patterns like `*(...)`. Slashes can be matched by `**` unless [`NOGLOBSTAR`](#globnoglobstar) is set.
- On Windows, slashes will be normalized in paths and patterns: `/` will become `\\`. There is no need to explicitly use `\\` in patterns on Windows, but if you do, it will be handled.
- On Windows, drives are treated special and must come at the beginning of the pattern and cannot be matched with `*`, `[]`, `?`, or even extended match patterns like `+(...)`.
- Windows drives are recognized as either `C:\\` or `\\\\Server\\mount\\` (or `C:/` and `//Server/mount/`).
- Meta characters have no effect when inside a UNC path: `\\\\Server?\\mount*\\`.
- If [`FORCECASE`](#globforcecase) is applied on a Windows system, slashes will not be normalized and pattern and paths will be treated as if on Linux/Unix. Also Windows drives will no longer be handled special. Two exception is when using the functions [`glob`](#globglob) or [`iglob`](#globiglob) are used or when [`REALPATH`](#globrealpath) is enabled, as either of these cases will cause `FORCECASE` to be ignored.  Since `glob` and `iglob` work on the actual file system of the host, and `REALPATH` forces functions like [`globmatch`](#globglobmatch) and [`globfilter`](#globglobfilter) to work off the file system, slashes and drives *must* be normalized and handled properly on the system for good behavior. `FORECASE` has no meaningful results on a Windows when working off the actual file system, and should not be enabled in these cases.
- By default, file and directory names starting with `.` are only matched with literal `.`.  The patterns `*`, `**`, `?`, and `[]` will not match a leading `.`.  To alter this behavior, you can use the [`DOTGLOB`](#globdotglob) flag, but even with `DOTGLOB` these special tokens will not match a special directory (`.` or `..`).  But when a literal `.` is used, for instance in the pattern `.*`, the pattern will match `.` and `..`.
- Relative paths and patterns are supported.

    ```pycon3
    >>> from wcmatch import glob
    >>> glob.glob('./docs/src/../*')
    ['./docs/src/../src', './docs/src/../theme']
    ```

- In general, Wildcard Match's behavior is modeled off of Bash's, so unlike the Python's default `glob`, Wildcard Match's `glob` will match and return `.` and `..` in certain cases just like Bash does.

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

## API

#### `glob.glob`

```py3
def glob(patterns, *, flags=0):
```

`glob` takes a pattern (or list of patterns) and will crawl the file system returning matching files. If a file/folder matches any positive patterns, it is considered a match.  If it matches *any* inverse pattern (when enabling the [`NEGATE`](#globnegate) flag), then it will be not be returned.

```pycon3
>>> from wcmatch import glob
>>> glob.glob(r'**/*.md')
['docs/src/markdown/_snippets/abbr.md', 'docs/src/markdown/_snippets/links.md', 'docs/src/markdown/_snippets/refs.md', 'docs/src/markdown/changelog.md', 'docs/src/markdown/fnmatch.md', 'docs/src/markdown/glob.md', 'docs/src/markdown/index.md', 'docs/src/markdown/installation.md', 'docs/src/markdown/license.md', 'README.md']
```

We can also exclude directories and/or files:

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

#### `glob.iglob`

```py3
def iglob(patterns, *, flags=0):
```

`iglob` is just like [`glob`](#globglob) except it returns an iterator.

```pycon3
>>> from wcmatch import glob
>>> list(glob.iglob(r'**/*.md'))
['docs/src/markdown/_snippets/abbr.md', 'docs/src/markdown/_snippets/links.md', 'docs/src/markdown/_snippets/refs.md', 'docs/src/markdown/changelog.md', 'docs/src/markdown/fnmatch.md', 'docs/src/markdown/glob.md', 'docs/src/markdown/index.md', 'docs/src/markdown/installation.md', 'docs/src/markdown/license.md', 'README.md']
```

#### `glob.globmatch`

```py3
def globmatch(filename, patterns, \*, flags=0):
```

`globmatch` takes a file name, a pattern (or list of patterns), and flags.  It will return a boolean indicating whether the file path was matched by the pattern(s).

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

Inverse patterns are allowed as well.

```pycon3
>>> from wcmatch import glob
>>> glob.globmatch('some/path/test.txt', r'!**/*/*.txt', flags=glob.NEGATE)
False
>>> glob.globmatch('some/path/test.py', r'!**/*/*.txt', flags=glob.NEGATE)
True
```

When inverse patterns are used in conjunction with other patterns, a path will be considered matched if one of the positive patterns match **and** none of the inverse patterns match. If only inverse patterns are applied, the path must not match any of the patterns.

```pycon3
>>> from wcmatch import glob
>>> glob.globmatch('some/path/test.txt', [r'**/*/*.txt', r'!**/*/avoid.txt'], flags=glob.NEGATE)
True
>>> glob.globmatch('some/path/avoid.txt', [r'**/*/*.txt', r'!**/*/avoid.txt'], flags=glob.NEGATE)
False
```

By default, `globmatch` and `globfilter` do not operate on the file system. This is to allow you to process paths from any source, even paths that are not on your current system. So if you are trying to explicitly match a directory with a pattern such as `*/`, your path must end with a slash (`my_directory/`) to be recognized as a directory. It also won't be able to evaluate whether a directory is a symlink or not as it will have no way of checking.

If you would like for `globmatch` (or `globfilter`) to operate on your current filesystem paths directly, simply pass in the [`REALPATH`](#globrealpath) flag, and the path to be matched analyzed, applying directory and symlink context and match the path the same way that `glob` or `iglob` would match the path.

#### `glob.globfilter`

```py3
def globfilter(filenames, patterns, *, flags=0):
```

`globfilter` takes a list of file paths, a pattern (or list of patterns), and flags. It returns a list of all files paths that matched the pattern(s). The same logic used for [`globmatch`](#globglobmatch) is used for `globfilter`, albeit more efficient for processing multiple files.

```pycon3
>>> from wcmatch import glob
>>> glob.globfilter(['some/path/a.txt', 'b.txt', 'another/path/c.py'], r'**/*.txt')
['some/path/a.txt', 'b.txt']
```

Like [`globmatch`](#globglobmatch), `globfilter` does not operate directly on the file system, with all the caveats associated, but you can enable the [`REALPATH`](#globrealpath) flag analyze paths that are actually on your system and apply proper context to match the same way `glob` or `iglob` would.

#### `glob.globsplit`

```py3
def globsplit(pattern, *, flags=0):
```

`globsplit` is used to take a string of multiple patterns that are divided by `|` and split them into separate patterns. This is provided to help with some interfaces they might need a way to define multiple patterns in one input. It takes into account things like sequences (`[]`) and extended patterns (`*(...)`) and will not parse `|` within them.  You can escape the dividers if needed (`\|`).

```pycon3
>>> from wcmatch import glob
>>> glob.globsplit(r'**/*.txt|source/*(some|file).py')
('**/*.txt', 'source/*(some|file).py')
```

!!! warning "Flags affect splitting!"
    Remember to pass the same flags you plan to pass into `glob`, `iglob`, `globmatch`, or `globfilter` as the flags may affect how the content is split. Specifically flags like `EXTGLOB`, `REALPATH`, `RAWCHARS`, and `FORCECASE` can potential affect pattern splitting.

#### `glob.translate`

```py3
def translate(patterns, *, flags=0):
```

`translate` takes a glob pattern (or list of patterns) and returns two lists: one for positive patterns and one for inverse patterns. The lists contain the regular expressions used for matching the given patterns.

```pycon3
>>> from wcmatch import glob
>>> glob.translate(r'**/*.{py,txt}')
(['^(?s:(?:(?!(?:\\/|^)\\.).)*?(?:^|$|\\/)+(?=.)(?!(?:\\.{1,2})(?:$|\\/))(?:(?!\\.)[^\\/]*?)?\\.py[\\/]*?)$', '^(?s:(?:(?!(?:\\/|^)\\.).)*?(?:^|$|\\/)+(?=.)(?!(?:\\.{1,2})(?:$|\\/))(?:(?!\\.)[^\\/]*?)?\\.txt[\\/]*?)$'], [])
>>> glob.translate(r'!**/*.{py,txt}', flags=glob.NEGATE)
([], ['^(?!(?s:(?:(?!(?:\\/|^)\\.).)*?(?:^|$|\\/)+(?=.)(?!(?:\\.{1,2})(?:$|\\/))(?:(?!\\.)[^\\/]*?)?\\.py[\\/]*?)).*?$', '^(?!(?s:(?:(?!(?:\\/|^)\\.).)*?(?:^|$|\\/)+(?=.)(?!(?:\\.{1,2})(?:$|\\/))(?:(?!\\.)[^\\/]*?)?\\.txt[\\/]*?)).*?$'])
```

#### `glob.escape`

```py3
def escape(pattern, unix=False):
```

This escapes special glob meta characters so they will be treated as literal characters.  It escapes using backslashes. It will escape `-`, `!`, `*`, `?`, `(`, `[`, `|`, `^`, `{`, and `\`. On Windows, it will specifically only escape `\` when not already escaped (`\\`). `/` and `\\` (on Windows) are not escaped as they are path separators.

```pycon3
>>> from wcmatch import glob
>>> glob.escape('some/path?/**file**{}.txt')
'some/path\\?/\\*\\*file\\*\\*\\{}.txt'
>>> glob.globmatch('some/path?/**file**{}.txt', glob.escape('some/path?/**file**{}.txt'))
True
```

On a Windows system, drives are not escaped since meta characters are not parsed in drives. Drives on Windows are generally treated special. This is because a drive could contain special characters like in `\\?\c:\`.

`escape` will detect the system it is running on and pick Windows escape logic or Linux/Unix logic. Since [`globmatch`](#globglobmatch) allows you to match Unix style paths on a Windows system, you can force Unix style escaping via the `unix` parameter.

#### `glob.raw_escape`

```py3
def raw_escape(pattern, unix=False):
```

This is like [`escape`](#globescape) except it will apply raw character string escapes before doing meta character escapes.  This is meant for use with the [`RAWCHARS`](#globrawchars) flag.

```pycon3
>>> from wcmatch import glob
>>> glob.raw_escape('some/path?/\x2a\x2afile\x2a\x2a{}.txt')
'some/path\\?/\\*\\*file\\*\\*\\{}.txt'
>>> glob.globmatch('some/path?/**file**{}.txt', glob.escape('some/path?/\x2a\x2afile\x2a\x2a{}.txt'), flags=glob.RAWCHARS)
True
```

`raw_escape` will detect the system it is running on and pick Windows escape logic or Linux/Unix logic. Since [`globmatch`](#globglobmatch) allows you to match Unix style paths on a Windows system, you can force Unix style escaping via the `unix` parameter.

## Flags

#### `glob.FORCECASE, glob.F` {: #globforcecase}

`FORCECASE` forces case sensitivity.

On Windows, `FORCECASE` will also force paths to be treated like Linux/Unix paths in [`globmatch`](#globglobmatch) and [`globfilter`](#globfilter) when [`REALPATH`](#globrealpath) is not enabled. `iglob`, `glob`, and cases when `REALPATH` is enabled must normalize paths and use Windows logic as these operations are performed on the current file system of the host machine. File system operations should not enable `FORCECASE` on Windows as it provides no meaningful results. But, if you wish to evaluate Unix/Linux paths on a Windows machine, without touching the file system, then `FORCECASE` might be useful.

#### `glob.IGNORECASE, glob.I` {: #globignorecase}

`IGNORECASE` forces case insensitivity. [`FORCECASE`](#globforcecase) has higher priority than `IGNORECASE`.

#### `glob.RAWCHARS, glob.R` {: #globrawchars}

`RAWCHARS` causes string character syntax to be parsed in raw strings: `#!py3 r'\u0040'` --> `#!py3 r'@'`. This will handle standard string escapes and Unicode including `#!py3 r'\N{CHAR NAME}'`.

#### `glob.NEGATE, glob.N` {: #globnegate}

`NEGATE` causes patterns that start with `!` to be treated as inverse matches. A pattern of `!*.py` would match any file but Python files. If used with the extended glob feature, patterns like `!(inverse|pattern)` will be mistakenly parsed as an inverse pattern instead of as an inverse extended glob group.  See [`MINUSNEGATE`](#globminusgate) for an alternative syntax that plays nice with extended glob.

#### `glob.MINUSNEGATE, glob.M` {: #globminusnegate}

When `MINUSNEGATE` is used with [`NEGATE`](#globnegate), negate patterns are recognized by a pattern starting with `-` instead of `!`. This plays nice with the extended glob feature which already uses `!` in patterns such as `!(...)`.

#### `glob.GLOBSTAR, glob.G` {: #globglobstar}

`GLOBSTAR` enables the feature where `**` matches zero or more directories.

!!! new "New 3.0"
    `GLOBSTAR` will no longer match or traverse symlink directories. This models the recent behavior in Bash 5.0. To crawl symlink directories, the new [`FOLLOW`](#globfollow) flag must be enabled.

#### `glob.FOLLOW, glob.FL` {: #globfollow}

`FOLLOW` will cause `GLOBSTAR` patterns (`**`) to match and traverse symlink directories.

!!! new "New 3.0"
    `FOLLOW` was added in 3.0.

#### `glob.REALPATH, glob.P` {: #globrealpath}

In the past, only `glob` and `iglob` operated on the filesystem, but with `REALPATH`other functions will now operate on the filesystem as well: `globsplit`, `globmatch`, `globfilter`, etc.

Traditionally, functions such as `globmatch` would simply match a path with regular expression and return the result. It was not concerned with whether the path existing or not. It didn't care if it was even valid for the operating system as `FORCECASE` would force Unix/Linux path logic on Windows. `REALPATH` forces `globmatch` (and others) to treat the string path as a real file path for the given system it is running on. When `REALPATH` a number of additional logic performed when evaluating a path:

- Path must exist
- Directories that are symlinks will not be matched by `GLOBSTAR` patterns (`**`) unless the `FOLLOW` flag is enabled.
- `globmatch` and `globfilter` will properly retrieve context on path and will determine if it is a directory or a file, and it will apply suitable logic accordingly. Without `REALPATH`, `globmatch` required a path to end with a slash when a pattern was explicitly trying to match a directory.

!!! new "NEW 3.0"
    `REALPATH` was added in 3.0.

#### `glob.DOTGLOB, glob.D` {: #globdotglob}

By default, [`glob`](#globglob) and [`globmatch`](#globglobmatch) will not match file or directory names that start with dot `.` unless matched with a literal dot. `DOTGLOB` allows the meta characters (such as `*`) to glob dots like any other character. Dots will not be matched in `[]`, `*`, or `?`.

Alternatively `DOTMATCH` will also be accepted for consistency with the other provided libraries. Both flags are exactly the same and are provided as a convenience in case the user finds one more intuitive than the other since `DOTGLOB` is often the name used in Bash.

#### `glob.EXTGLOB, glob.E` {: #globextglob}

`EXTGLOB` enables extended pattern matching which includes special pattern lists such as `+(...)`, `*(...)`, `?(...)`, etc. See the [syntax overview](#syntax) for more information.

Alternatively `EXTMATCH` will also be accepted for consistency with the other provided libraries. Both flags are exactly the same and are provided as a convenience in case the user finds one more intuitive than the other since `EXTGLOB` is often the name used in Bash.

#### `glob.BRACE, glob.B` {: #globbrace}

`BRACE` enables Bash style brace expansion: `a{b,{c,d}}` --> `ab ac ad`. Brace expansion is applied before anything else. When applied, a pattern will be expanded into multiple patterns. Each pattern will then be parsed separately.

For simple patterns, it may make more sense to use [`EXTGLOB`](#globextglob) which will only generate a single pattern: `@(ab|ac|ad)`.

Be careful with patterns such as `{1..100}` which would generate one hundred patterns that will all get individually parsed. Sometimes you really need such a pattern, but be mindful that it will be slower as you generate larger sets of patterns.

--8<--
refs.txt
--8<--
