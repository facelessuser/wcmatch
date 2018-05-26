# wcmatch.glob

## Syntax

The `glob` library provides a method for traversing the file system and returning matching files defined via glob patterns.  It also provides methods for matching a file pattern (similar to fnmatch, but for paths) with the same glob patterns used for glob. In short, globmatch matches what glob globs :slight_smile:. The features are similar to `fnmatch`'s, but the flags and what features that are enabled by default vary.

Pattern           | Meaning
----------------- | -------
`*`               | Matches everything except slashes.  On Windows it will avoid matching backslashes as well as slashes.
`**`              | Matches zero or more directories, but will never match the directories `.` and `..`.
`?`               | Matches any single character.
`[seq]`           | Matches any character in seq.
`[!seq]`          | Matches any character not in seq.
`\`               | Escapes characters. If applied to a meta characters, it will be treated as normal characters.
`!`               | Inverse pattern (with configuration, can use `-` instead of `!`).
`?(pattern_list)` | The pattern matches if zero or one occurrences of any of the patterns in the `pattern_list` match the input string.
`*(pattern_list)` | The pattern matches if zero or more occurrences of any of the patterns in the `pattern_list` match the input string.
`+(pattern_list)` | The pattern matches if one or more occurrences of any of the patterns in the `pattern_list` match the input string.
`@(pattern_list)` | The pattern matches if exactly one occurrence of any of the patterns in the `pattern_list` match the input string.
`!(pattern_list)` | The pattern matches if the input string cannot be matched with any of the patterns in the `pattern_list`.
`{}`              | Bash style brace expansions.  This is applied to patterns before anything else.

- Slashes are generally treated special in glob related methods. Slashes are not matched in `[]`, `*`, `?`, or extended patterns like `*(...)`. Slashes can be matched by `**`.
- On windows, slashes will be normalized: `/` will become `\\`.
- If case sensitivity is applied on a Windows system, slashes will not be normalized and pattern will be treated as a Linux/Unix. One exception is when using `glob.glob` or `glob.iglob`.  Since `glob.glob` and `glob.iglob` work on the actual file system of the system, it will normalize slashes when on a Windows system.
- On Windows (no case sensitivity), drives are treated special and must come at the beginning of the pattern and cannot be matched with `*`, `[]`, `?`, or even extended match patterns `+(...)`, etc.
- Windows drives are recognized as either `C:\\` or `\\\\Server\\mount\\` (or `C:/` and `//Server/mount/`).
- Meta characters have no effect when inside a UNC path: `\\\\Server?\\mount*\\`.

### API

#### glob.glob

```py3
def glob(patterns, *, flags=0):
```

`glob` takes a pattern (or list of patterns) and will crawl the file system returning matching files. If a file/folder matches any postive patterns, it is considered a match.  If it matches *any* inverse pattern (when enabling the NEGATE flag), then it will be not be returned.

```pycon3
from wcmatch import glob
>>> glob.glob(r'**/*.md')
['docs/src/markdown/changelog.md', 'docs/src/markdown/index.md', 'docs/src/markdown/installation.md', 'docs/src/markdown/license.md', 'docs/src/markdown/_snippets/abbr.md', 'docs/src/markdown/_snippets/links.md', 'docs/src/markdown/_snippets/refs.md', 'README.md']
```

We can also exclude directories and/or files:

```pycon3
from wcmatch import glob
>>> glob.glob([r'**/*.md', r'!README.md', r'!**/_snippets'], flags=glob.NEGATE)
['docs/src/markdown/changelog.md', 'docs/src/markdown/index.md', 'docs/src/markdown/installation.md', 'docs/src/markdown/license.md']
```

When a glob pattern ends with a slash, it will only return directories:

```pycon3
from wcmatch import glob
>>> glob.glob(r'**/')
['__pycache__', 'docs', 'docs/docs', 'docs/src', 'docs/src/markdown', 'docs/src/markdown/_snippets', 'docs/theme', 'requirements', 'tests', 'tests/__pycache__', 'tests/dir_walker', 'wcmatch', 'wcmatch/__pycache__']
```

#### glob.iglob

```py3
def iglob(patterns, *, flags=0):
```

`iglob` is just like [`glob`](#glob.glob) except it returns an iterator.

```pycon3
from wcmatch import glob
>>> list(glob.iglob(r'**/*.md'))
['docs/src/markdown/changelog.md', 'docs/src/markdown/index.md', 'docs/src/markdown/installation.md', 'docs/src/markdown/license.md', 'docs/src/markdown/_snippets/abbr.md', 'docs/src/markdown/_snippets/links.md', 'docs/src/markdown/_snippets/refs.md', 'README.md']
```

#### glob.globmatch

```py3
def globmatch(filename, patterns, \*, flags=0)
```

`globmatch` takes a file name, a pattern (or list of patterns) and flags.  It will return a boolean indicating whether the file path was matched by the pattern(s).

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

When used in conjunction with other patterns, a file path will match if matches one of the positive patterns **and** does not match any inverse patterns. If only inverse patterns are applied, the file must not match any of the patterns.

```pycon3
>>> from wcmatch import glob
>>> glob.globmatch('some/path/test.txt', [r'**/*/*.txt', r'!**/*/avoid.txt'], flags=glob.NEGATE)
True
>>> glob.globmatch('some/path/avoid.txt', [r'**/*/*.txt', r'!**/*/avoid.txt'], flags=glob.NEGATE)
False
```

#### glob.globfilter

```py3
def globfilter(filenames, patterns, *, flags=0):
```

`globfilter` takes a list of file paths, a pattern (or list of patterns) and flags. It returns a list of all files paths that matched the pattern(s). The same logic used for `globmatch` is used for `globfilter`, albeit more efficient for processing multiple files.

```pycon3
>>> from wcmatch import glob
>>> glob.globfilter(['some/path/a.txt', 'b.txt', 'another/path/c.py'], r'**/*.txt')
['some/path/a.txt', 'b.txt']
```

#### glob.globsplit

```py3
def globsplit(pattern, *, flags=0):
```

`globsplit` is used to take a string of multiple patterns that divided by `|` and split them into separate patterns. It takes into account things like sequences (`[]`) and extended patterns (`*(...)`) and will not parse `|` within them.  You can escape the dividers if needed (`\|`). This is useful for certain interfaces.

```pycon3
>>> from wcmatch import glob
>>> glob.globsplit(r'**/*.txt|source/*(some|file).py')
('**/*.txt', 'source/*(some|file).py')
```

#### glob.translate

```py3
def translate(patterns, \*, flags=0):
```

`translate` takes a glob pattern (or list of patterns) and returns two lists (one for positive patterns and one for inverse patterns) of equivalent regular expressions for each pattern. This returns a list even when only one pattern is given as features like brace expansion literally expand a pattern into multiple patterns.

```pycon3
from wcmatch import glob
>>> glob.translate(r'**/*.{py,txt}')
(['^(?s:(?:(?!(?:\\/|^)\\.).)*?(?:^|$|\\/)+(?=.)(?!(?:\\.{1,2})(?:$|\\/))(?:(?!\\.)[^\\/]*?)?\\.py[\\/]*?)$', '^(?s:(?:(?!(?:\\/|^)\\.).)*?(?:^|$|\\/)+(?=.)(?!(?:\\.{1,2})(?:$|\\/))(?:(?!\\.)[^\\/]*?)?\\.txt[\\/]*?)$'], [])
>>> glob.translate(r'!**/*.{py,txt}', flags=glob.NEGATE)
([], ['^(?!(?s:(?:(?!(?:\\/|^)\\.).)*?(?:^|$|\\/)+(?=.)(?!(?:\\.{1,2})(?:$|\\/))(?:(?!\\.)[^\\/]*?)?\\.py[\\/]*?)).*?$', '^(?!(?s:(?:(?!(?:\\/|^)\\.).)*?(?:^|$|\\/)+(?=.)(?!(?:\\.{1,2})(?:$|\\/))(?:(?!\\.)[^\\/]*?)?\\.txt[\\/]*?)).*?$'])
```

### Flags

#### glob.FORCECASE

`FORCECASE` forces case sensitivity. On Windows, this will force paths to be treated like Linux/Unix paths, and slashes will not be normalized. Path normalization only relates to globmatch and not for glob and iglob. Paths must be normalized for glob and iglob in order to scan the file system. `FORCECASE` has higher priority than `IGNORECASE`. 

#### glob.IGNORECASE

`IGNORECASE` force case insensitivity. `FORCECASE` has higher priority than `IGNORECASE`.

#### glob.RAWCHARS

`RAWCHARS` causes string character syntax to be parsed in raw strings: `r'\u0040'` --> `r'@'`. This will handled standard string escapes and Unicode (including `\N{CHAR NAME}`).

#### glob.NEGATE

`NEGATE` causes patterns that start with `!` to be treated as inverse matches. A pattern of `!*.py` would match any file but Python files. If used with `EXTMATCH`, patterns like `!(inverse|pattern)` will be mistakenly parsed as an inverse path instead of an inverse extmatch group.  See `MINUSNEGATE` for an alternative syntax that plays nice with `EXTMATCH`.

#### glob.MINUSNEGATE

When `MINUSNEGATE` is used with `NEGATE`, negate patterns are recognized by a pattern starting with `-` instead of `!`. This plays nice with the `EXTMATCH` option.

#### glob.NOGLOBSTAR

By default, `**` matches zero or more directories. You can disable `**` with `NOGLOBSTAR` and `**` will be treated as two `*`.

#### glob.DOTGLOB

By default, `glob` and `globmatch` will not match file or directory names that start with dot (`.`) unless matched with a literal dot. `DOTGLOB` allows the meta characters (such as `*`) to glob dots like any other character. Dots will not be matched in `[]`, `*`, `?`, or extended patterns like `+(...)`.

#### glob.NOEXTGLOB

`NOEXTGLOB` disables extended pattern matching which includes special pattern lists such as `+(...)`, `*(...)`, `?(...)`, etc. See the [syntax overview](#glob) for more information.

#### glob.NOBRACE

`NOBRACE` disables Bash style brace expansion: `a{b,{c,d}}` --> `ab ac ad`. Brace expansion is applied before anything else. When applied a pattern will be expanded into multiple patterns. Each pattern will then be parsed separately.

For simple patterns, it may make more sense to use extended patterns as they will be more efficient since they won't spawn multiple patterns that need to be separately parsed. A pattern such as `{1..100}` would generate one hundred patterns that will all get individually parsed. But when needed, this feature can be quite useful.
