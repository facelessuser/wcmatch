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
`[[:alnum:]]`     | POSIX style character classes inside sequences. The `C` locale is used for byte strings and Unicode properties for Unicode strings. See [POSIX Character Classes](#posix-character-classes) for more info.
`\`               | Escapes characters. If applied to a meta character, it will be treated as a normal character.
`!`               | Inverse pattern (with configuration, can use `-` instead of `!`).
`?(pattern_list)` | The pattern matches if zero or one occurrences of any of the patterns in the `pattern_list` match the input string.
`*(pattern_list)` | The pattern matches if zero or more occurrences of any of the patterns in the `pattern_list` match the input string.
`+(pattern_list)` | The pattern matches if one or more occurrences of any of the patterns in the `pattern_list` match the input string.
`@(pattern_list)` | The pattern matches if exactly one occurrence of any of the patterns in the `pattern_list` match the input string.
`!(pattern_list)` | The pattern matches if the input string cannot be matched with any of the patterns in the `pattern_list`.
`{}`              | Bash style brace expansions.  This is applied to patterns before anything else.

- Slashes are generally treated as normal characters, but on windows they will be normalized: `/` will become `\\`. There is no need to explicitly use `\\` in patterns on Windows, but if you do, it will be handled.  This applies to matching patterns and the file names the patterns are applied to.
- If case sensitivity is applied on a Windows system, slashes will not be normalized and pattern and file names will be treated as a Linux/Unix path.
- By default, `.` is *not* matched by `*`, `?`, `[]`, and extended patterns such as `*(...)`. See the [`DOTMATCH`](#fnmatchdotmatch) flag to match `.` at the start of a filename without a literal `.`.

--8<-- "posix.txt"

## API

#### fnmatch.fnmatch

```py3
def fnmatch(filename, patterns, *, flags=0)
```

`fnmatch` takes a file name, a pattern (or list of patterns), and flags.  It will return a boolean indicating whether the file name was matched by the pattern(s).

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

When inverse patterns are used in conjunction with other patterns, a file will be considered matched if one of the positive patterns match **and** none of the inverse patterns match. If only inverse patterns are applied, the file must not match any of the patterns.

```pycon3
>>> from wcmatch import fnmatch
>>> fnmatch.fnmatch('test.txt', [r'*.txt', r'!avoid.txt'], flags=fnmatch.NEGATE)
True
>>> fnmatch.fnmatch('avoid.txt', [r'*.txt', r'!avoid.txt'], flags=fnmatch.NEGATE)
False
```

#### fnmatch.filter

```py3
def filter(filenames, patterns, *, flags=0):
```

`filter` takes a list of file names, a pattern (or list of patterns), and flags. It returns a list of all files that matched the pattern(s). The same logic used for [`fnmatch`](#fnmatchfnmatch) is used for `filter`, albeit more efficient for processing multiple files.

```pycon3
>>> from wcmatch import fnmatch
>>> fnmatch.filter(['a.txt', 'b.txt', 'c.py'], r'*.txt')
['a.txt', 'b.txt']
```

#### fnmatch.split

```py3
def fnsplit(pattern, *, flags=0):
```

`fnsplit` is used to take a string of multiple patterns that are divided by `|` and split them into separate patterns. This is provided to help with some interfaces they might need a way to define multiple patterns in one input. It takes into account things like sequences (`[]`) and extended patterns (`*(...)`) and will not parse `|` within them.  You can escape the dividers if needed (`\|`).

```pycon3
>>> from wcmatch import fnmatch
>>> fnmatch.fnsplit(r'*.txt|*(some|file).py', flags=fnmatch.EXTMATCH)
('*.txt', '*(some|file).py')
```

#### fnmatch.translate

```py3
def translate(patterns, *, flags=0):
```

`translate` takes a file pattern (or list of patterns) and returns two lists: one for positive patterns and one for inverse patterns. The lists contain the regular expressions used for matching the given patterns.

```pycon3
>>> from wcmatch import translate
>>> fnmatch.translate(r'*.{a,{b,c}}', flags=fnmatch.BRACE)
(['^(?s:(?=.).*?\\.a)$', '^(?s:(?=.).*?\\.b)$', '^(?s:(?=.).*?\\.c)$'], [])
>>> fnmatch.translate(r'!*.{a,{b,c}}', flags=fnmatch.BRACE | fnmatch.NEGATE)
([], ['^(?!(?s:(?=.).*?\\.a)).*?$', '^(?!(?s:(?=.).*?\\.b)).*?$', '^(?!(?s:(?=.).*?\\.c)).*?$'])
```

## Flags

#### fnmatch.FORCECASE, fnmatch.F {: #fnmatchforcecase}

`FORCECASE` forces case sensitivity. On Windows, this will force paths to be treated like Linux/Unix paths, and slashes will not be normalized. `FORCECASE` has higher priority than [`IGNORECASE`](#fnmatchignorecase).

#### fnmatch.IGNORECASE, fnmatch.I {: #fnmatchignorecase}

`IGNORECASE` forces case insensitivity. [`FORCECASE`](#fnmatchforecase) has higher priority than `IGNORECASE`.

#### fnmatch.RAWCHARS, fnmatch.R {: #fnmatchrawchars}

`RAWCHARS` causes string character syntax to be parsed in raw strings: `#!py3 r'\u0040'` --> `#!py3 r'@'`. This will handled standard string escapes and Unicode including `#!py3 r'\N{CHAR NAME}'`.

#### fnmatch.NEGATE, fnmatch.N {: #fnmatchnegate}

`NEGATE` causes patterns that start with `!` to be treated as inverse matches. A pattern of `!*.py` would match any file but Python files. If used with [`EXTMATCH`](#fnmatchextmatch), patterns like `!(inverse|pattern)` will be mistakenly parsed as an inverse pattern instead of an inverse extmatch group.  See [`MINUSNEGATE`](#fnmatchminusnegate) for an alternative syntax that plays nice with `EXTMATCH`.

#### fnmatch.MINUSNEGATE, fnmatch.M {: #fnmatchminusnegate}

When `MINUSNEGATE` is used with [`NEGATE`](#fnmatchnegate), negate patterns are recognized by a pattern starting with `-` instead of `!`. This plays nice with the [`EXTMATCH`](#fnmatchextmatch) option.

#### fnmatch.DOTMATCH, fnmatch.D {: #fnmatchdotmatch}

By default, [`glob`](#fnmatchfnmatch) and related functions will not match file or directory names that start with dot `.` unless matched with a literal dot. `DOTMATCH` allows the meta characters (such as `*`) to match dots like any other character. Dots will not be matched in `[]`, `*`, `?`, or extended patterns like `+(...)`.

#### fnmatch.EXTMATCH, fnmatch.E {: #fnmatchextmatch}

`EXTMATCH` enables extended pattern matching. This includes special pattern lists such as `+(...)`, `*(...)`, `?(...)`, etc. See the [syntax overview](#syntax) for more information.

#### fnmatch.BRACE, fnmatch.B {: #fnmatchbrace}

`BRACE` enables Bash style brace expansion: `a{b,{c,d}}` --> `ab ac ad`. Brace expansion is applied before anything else. When applied, a pattern will be expanded into multiple patterns. Each pattern will then be parsed separately.

For simple patterns, it may make more sense to use [`EXTMATCH`](#fnmatchextmatch) which will only generate a single pattern: `@(ab|ac|ad)`.

Be careful with patterns such as `{1..100}` which would generate one hundred patterns that will all get individually parsed. Sometimes you really need such a pattern, but be mindful that it will be slower as you generate larger sets of patterns.

--8<--
refs.txt
--8<--
