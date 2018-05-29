# wcmatch.fnmatch

```py3
from wcmatch import fnmatch
```

## Syntax

The `fnmatch` library is similar to the builtin `fnmatch`, but with some enhancements and some differences. It is mainly used for matching file names with glob patterns. For pathnames, Wildcard Match's [`globmatch`](glob#globglobmatch) is a more appropriate choice. Not all of the features listed below are enabled by default. See [flags](#flags) for more information.

!!! tip
    When using backslashes, it is helpful to use raw strings. In a raw string, a single backslash is used to escape a character `#!py3 r'\?'`.  If you want to represent a literal backslash, you must use two: `#!py3 r'some\\path'`.

Pattern           | Meaning
----------------- | -------
`*`               | Matches everything.
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

- Slashes are generally treated as normal characters, but on windows they will be normalized: `/` will become `\\`. There is no need to explicitly use `\\` in patterns on Windows, but if you do, it will be handled.  This applies to matching patterns and the file names the patterns are applied to.
- If case sensitivity is applied on a Windows system, slashes will not be normalized and pattern and file names will be treated as a Linux/Unix path.
- For `glob` there are additional Windows drive consideration. Check out [`glob`](glob#wcmatchglob) for more information.
- By default `.` is matched (even at the start of a file) by `*`, `?`, `[]`, and extended patterns such as `*(...)`. See the [`PERIOD`](#fnmatchperiod) flag to limit this matching at the start of a filename.

### API

#### fnmatch.fnmatch

```py3
def fnmatch(filename, patterns, \*, flags=0)
```

`fnmatch` takes a file name, a pattern (or list of patterns) and flags.  It will return a boolean indicating whether the file name was matched by the pattern(s).

```pycon3
>>> from wcmatch import fnmatch
>>> fnmatch.fnmatch('test.txt', r'@(*.txt|*.py)', flags=fnmatch.EXTMATCH)
True
```

When applying multiple patterns, a file matches if it matches any of the patterns:

```pycon3
>>> from wcmatch import fnmatch
>>> fnmatch.fnmatch('test.txt', [r'*.txt', r'*.py'], flags=fnmatch.EXTMATCH)
True
```

Inverse patterns are allowed as well.

```pycon3
>>> from wcmatch import fnmatch
>>> fnmatch.fnmatch('test.py', r'!*.py', flags=fnmatch.NEGATE)
False
>>> fnmatch.fnmatch('test.txt', r'!*.py', flags=fnmatch.NEGATE)
True
```

When used in conjunction with other patterns, a file will match if matches one of the positive patterns **and** does not match any inverse pattern. If only inverse patterns are applied, the file must not match any of the patterns.

```pycon3
>>> from wcmatch import fnmatch
>>> fnmatch.fnmatch('test.txt', [r'*.txt', r'!avoid.txt'], flags=fnmatch.NEGATE)
True
>>> fnmatch.fnmatch('avoid.txt', [r'*.txt', r'!avoid.txt'], flags=fnmatch.NEGATE)
False
```

#### fnmatch.filter

```py3
def filter(filenames, patterns, \*, flags=0):
```

`filter` takes a list of file names, a pattern (or list of patterns) and flags. It returns a list of all files that matched the pattern(s). The same logic used for [`fnmatch`](#fnmatchfnmatch) is used for `filter`, albeit more efficient for processing multiple files.

```pycon3
>>> from wcmatch import fnmatch
>>> fnmatch.filter(['a.txt', 'b.txt', 'c.py'], r'*.txt')
['a.txt', 'b.txt']
```

#### fnmatch.split

```py3
def fnsplit(pattern, *, flags=0):
```

`fnsplit` is used to take a string of multiple patterns that divided by `|` and split them into separate patterns. It takes into account things like sequences (`[]`) and extended patterns (`*(...)`) and will not parse `|` within them.  You can escape the dividers if needed (`\|`). This is useful for certain interfaces.

```pycon3
>>> from wcmatch import fnmatch
>>> fnmatch.fnsplit(r'*.txt|*(some|file).py', flags=fnmatch.EXTMATCH)
('*.txt', '*(some|file).py')
```

#### fnmatch.translate

```py3
def translate(patterns, \*, flags=0):
```

`translate` takes a file glob pattern (or list of patterns) and returns two lists (one for positive patterns and one for inverse patterns) of equivalent regular expressions for each pattern. This returns a list even when only one pattern is given as features like brace expansion literally expand a pattern into multiple patterns.

```pycon3
>>> from wcmatch import translate
>>> fnmatch.translate(r'*.{a,{b,c}}', flags=fnmatch.BRACE)
(['^(?s:(?=.).*?\\.a)$', '^(?s:(?=.).*?\\.b)$', '^(?s:(?=.).*?\\.c)$'], [])
>>> fnmatch.translate(r'!*.{a,{b,c}}', flags=fnmatch.BRACE | fnmatch.NEGATE)
([], ['^(?!(?s:(?=.).*?\\.a)).*?$', '^(?!(?s:(?=.).*?\\.b)).*?$', '^(?!(?s:(?=.).*?\\.c)).*?$'])
```

### Flags

#### fnmatch.FORCECASE

`FORCECASE` forces case sensitivity. On Windows, this will force paths to be treated like Linux/Unix paths, and slashes will not be normalized. `FORCECASE` has higher priority than [`IGNORECASE`](#fnmatchignorecase).

#### fnmatch.IGNORECASE

`IGNORECASE` force case insensitivity. [`FORCECASE`](#fnmatchforecase) has higher priority than `IGNORECASE`.

#### fnmatch.RAWCHARS

`RAWCHARS` causes string character syntax to be parsed in raw strings: `#!py3 r'\u0040'` --> `#!py3 r'@'`. This will handled standard string escapes and Unicode (including `#!py3 r'\N{CHAR NAME}'`).

#### fnmatch.NEGATE

`NEGATE` causes patterns that start with `!` to be treated as inverse matches. A pattern of `!*.py` would match any file but Python files. If used with [`EXTMATCH`](#fnmatchextmatch), patterns like `!(inverse|pattern)` will be mistakenly parsed as an inverse path instead of an inverse extmatch group.  See [`MINUSNEGATE`](#fnmatchminusnegate) for an alternative syntax that plays nice with `EXTMATCH`.

#### fnmatch.MINUSNEGATE

When `MINUSNEGATE` is used with [`NEGATE`](#fnmatchnegate), negate patterns are recognized by a pattern starting with `-` instead of `!`. This plays nice with the [`EXTMATCH`](#fnmatchextmatch) option.

#### fnmatch.PERIOD

`PERIOD` causes file names that start with dot (`.`) to only be matched with a literal `.`. Dots will not be matched in `[]`, `*`, `?`, or extended patterns like `+(...)`.

#### fnmatch.EXTMATCH

`EXTMATCH` enables extended pattern matching which includes special pattern lists such as `+(...)`, `*(...)`, `?(...)`, etc. See the [syntax overview](#syntax) for more information.

#### fnmatch.BRACE

`BRACE` enables Bash style brace expansion: `a{b,{c,d}}` --> `ab ac ad`. Brace expansion is applied before anything else. When applied, a pattern will be expanded into multiple patterns. Each pattern will then be parsed separately.

For simple patterns, it may make more sense to use [`EXTMATCH`](#fnmatchextmatch) as it will be more efficient as it won't spawn multiple patterns that need to be separately parsed. A pattern such as `{1..100}` would generate one hundred patterns that will all get individually parsed. But when needed, this feature can be quite useful.
