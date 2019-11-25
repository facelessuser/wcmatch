# `wcmatch.fnmatch`

```py3
from wcmatch import fnmatch
```

## Syntax

The `fnmatch` library is similar to the builtin [`fnmatch`][fnmatch], but with some enhancements and some differences.
It is mainly used for matching filenames with glob patterns. For path names, Wildcard Match's
[`globmatch`](./glob.md#globglobmatch) is a more appropriate choice. Not all of the features listed below are enabled by
default. See [flags](#flags) for more information.

!!! tip
    When using backslashes, it is helpful to use raw strings. In a raw string, a single backslash is used to escape a
    character `#!py3 r'\?'`.  If you want to represent a literal backslash, you must use two: `#!py3 r'some\\path'`.

Pattern           | Meaning
----------------- | -------
`*`               | Matches everything.
`?`               | Matches any single character.
`[seq]`           | Matches any character in seq.
`[!seq]`          | Matches any character not in seq.
`[[:alnum:]]`     | POSIX style character classes inside sequences. The `C` locale is used for byte strings and Unicode properties for Unicode strings. See [POSIX Character Classes](#posix-character-classes) for more info.
`\`               | Escapes characters. If applied to a meta character, it will be treated as a normal character.
`!`               | Pattern will be treated as an exclusion pattern when used at the start of the pattern (with configuration, can use `-` instead of `!`).
`?(pattern_list)` | The pattern matches if zero or one occurrences of any of the patterns in the `pattern_list` match the input string.
`*(pattern_list)` | The pattern matches if zero or more occurrences of any of the patterns in the `pattern_list` match the input string.
`+(pattern_list)` | The pattern matches if one or more occurrences of any of the patterns in the `pattern_list` match the input string.
`@(pattern_list)` | The pattern matches if exactly one occurrence of any of the patterns in the `pattern_list` match the input string.
`!(pattern_list)` | The pattern matches if the input string cannot be matched with any of the patterns in the `pattern_list`.
`{}`              | Bash style brace expansions.  This is applied to patterns before anything else.

- Slashes are generally treated as normal characters, but on windows they will be normalized: `/` will become `\\`.
  There is no need to explicitly use `\\` in patterns on Windows, but if you do, it will be handled.  This applies to
  matching patterns and the filenames the patterns are applied to.
- By default, `.` is *not* matched by `*`, `?`, and `[]`. See the [`DOTMATCH`](#fnmatchdotmatch) flag to match `.` at
  the start of a filename without a literal `.`.

--8<-- "posix.txt"

## API

#### `fnmatch.fnmatch`

```py3
def fnmatch(filename, patterns, *, flags=0)
```

`fnmatch` takes a file name, a pattern (or list of patterns), and flags.  It will return a boolean indicating whether
the file name was matched by the pattern(s).

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

Exclusion patterns are allowed as well. When exclusion patterns are used in conjunction with inclusion patterns, a file
will be considered matched if one of the inclusion patterns match **and** none of the exclusion patterns match. If an
exclusion pattern is given without any inclusion patterns, the pattern will match nothing. Exclusion patterns are meant
to filter other patterns, not match anything by themselves.

```pycon3
>>> from wcmatch import fnmatch
>>> fnmatch.fnmatch('test.py', r'*|!*.py', flags=fnmatch.NEGATE | fnamtch.SPLIT)
False
>>> fnmatch.fnmatch('test.txt', r'*|!*.py', flags=fnmatch.NEGATE | fnamtch.SPLIT)
True
>>> fnmatch.fnmatch('test.txt', [r'*.txt', r'!avoid.txt'], flags=fnmatch.NEGATE)
True
>>> fnmatch.fnmatch('avoid.txt', [r'*.txt', r'!avoid.txt'], flags=fnmatch.NEGATE)
False
```

As mentioned, exclusion patterns need to be applied to a inclusion pattern to work, but if it is desired, you can force
exclusion patterns to assume all files should be filtered with the exclusion pattern(s) with the
[`NEGATEALL`](#fnmatchnegateall) flag. Essentially, it means if you use a pattern such as `!*.md`, it will assume two
pattern were given: `*` and `!*.md`.

```pycon3
>>> from wcmatch import fnmatch
>>> fnmatch.fnmatch('test.py', r'!*.py', flags=fnmatch.NEGATE | fnamtch.NEGATEALL)
False
>>> fnmatch.fnmatch('test.txt', r'!*.py', flags=fnmatch.NEGATE | fnamtch.NEGATEALL)
True
```

#### `fnmatch.filter`

```py3
def filter(filenames, patterns, *, flags=0):
```

`filter` takes a list of filenames, a pattern (or list of patterns), and flags. It returns a list of all files that
matched the pattern(s). The same logic used for [`fnmatch`](#fnmatchfnmatch) is used for `filter`, albeit more efficient
for processing multiple files.

```pycon3
>>> from wcmatch import fnmatch
>>> fnmatch.filter(['a.txt', 'b.txt', 'c.py'], r'*.txt')
['a.txt', 'b.txt']
```

#### `fnmatch.translate`

```py3
def translate(patterns, *, flags=0):
```

`translate` takes a file pattern (or list of patterns) and returns two lists: one for inclusion patterns and one for
exclusion patterns. The lists contain the regular expressions used for matching the given patterns. It should be noted
that a file is considered matched if it matches at least one inclusion pattern and matches **none** of the exclusion
patterns.

```pycon3
>>> from wcmatch import translate
>>> fnmatch.translate(r'*.{a,{b,c}}', flags=fnmatch.BRACE)
(['^(?s:(?=.).*?\\.a)$', '^(?s:(?=.).*?\\.b)$', '^(?s:(?=.).*?\\.c)$'], [])
>>> fnmatch.translate(r'**|!*.{a,{b,c}}', flags=fnmatch.BRACE | fnmatch.NEGATE | fnmatch.SPLIT)
(['^(?s:(?=.)(?![.]).*?)$'], ['^(?s:(?=.).*?\\.a)$', '^(?s:(?=.).*?\\.b)$', '^(?s:(?=.).*?\\.c)$'])
```

!!! warning "Changed 4.0"
    Translate now outputs exclusion patterns so that if they match, the file is excluded. This is opposite logic to how
    it used to be, but is more efficient.

## Flags

#### `fnmatch.CASE, fnmatch.C` {: #fnmatchcase}

`CASE` forces case sensitivity. `CASE` has higher priority than [`IGNORECASE`](#fnmatchignorecase).

!!! new "New 4.3"
    `CASE` is new in 4.3.0.

#### `fnmatch.IGNORECASE, fnmatch.I` {: #fnmatchignorecase}

`IGNORECASE` forces case insensitivity. [`CASE`](#fnmatchcase) has higher priority than `IGNORECASE`.

#### `fnmatch.RAWCHARS, fnmatch.R` {: #fnmatchrawchars}

`RAWCHARS` causes string character syntax to be parsed in raw strings: `#!py3 r'\u0040'` --> `#!py3 r'@'`. This will
handle standard string escapes and Unicode including `#!py3 r'\N{CHAR NAME}'`.

#### `fnmatch.NEGATE, fnmatch.N` {: #fnmatchnegate}

`NEGATE` causes patterns that start with `!` to be treated as exclusion patterns. A pattern of `!*.py` would match any
file but Python files. Exclusion patterns cannot be used by themselves though, and must be paired with a normal,
inclusion pattern, either by utilizing the [`SPLIT`](#fnmatchsplit) flag, or providing multiple patterns in a list.
Assuming the `SPLIT` flag, this means using it in a pattern such as `inclusion|!exclusion`.

If it is desired, you can force exclusion patterns, when no inclusion pattern is provided, to assume all files match
unless the file matches the excluded pattern. This is done with the [`NEGATEALL`](#fnmatchnegateall) flag.

If used with the extended match feature, patterns like `!(inverse|pattern)` will be mistakenly parsed as an exclusion
pattern instead of as an inverse extended glob group.  See [`MINUSNEGATE`](#fnmatchminusgate) for an alternative syntax
that plays nice with extended glob.

!!! warning "Changes 4.0"
    In 4.0, `NEGATE` now requires a non-exclusion pattern to be paired with it or it will match nothing. If you really
    need something similar to the old behavior, that would assume a default inclusion pattern, you can use the
    [`NEGATEALL`](#fnmatchnegateall).

#### `fnmatch.NEGATEALL, fnmatch.A` {: #fnmatchnegateall}

`NEGATEALL` can force exclusion patterns, when no inclusion pattern is provided, to assume all files match unless the
file matches the excluded pattern. Essentially, it means if you use a pattern such as `!*.md`, it will assume two
patterns were given: `*` and `!*.md`, where `!*.md` is applied to the results of `*`.

Dot files will not be returned unless [`DOTMATCH`](#fnmatchdotmatch).

#### `fnmatch.MINUSNEGATE, fnmatch.M` {: #fnmatchminusnegate}

When `MINUSNEGATE` is used with [`NEGATE`](#fnmatchnegate), exclusion patterns are recognized by a pattern starting with
`-` instead of `!`. This plays nice with the [`EXTMATCH`](#fnmatchextmatch) option.

#### `fnmatch.DOTMATCH, fnmatch.D` {: #fnmatchdotmatch}

By default, [`fnmatch`](#fnmatchfnmatch) and related functions will not match file or directory names that start with
dot `.` unless matched with a literal dot. `DOTMATCH` allows the meta characters (such as `*`) to match dots like any
other character. Dots will not be matched in `[]`, `*`, or `?`.

#### `fnmatch.EXTMATCH, fnmatch.E` {: #fnmatchextmatch}

`EXTMATCH` enables extended pattern matching. This includes special pattern lists such as `+(...)`, `*(...)`, `?(...)`,
etc. See the [syntax overview](#syntax) for more information.

#### `fnmatch.BRACE, fnmatch.B` {: #fnmatchbrace}

`BRACE` enables Bash style brace expansion: `a{b,{c,d}}` --> `ab ac ad`. Brace expansion is applied before anything
else. When applied, a pattern will be expanded into multiple patterns. Each pattern will then be parsed separately.

For simple patterns, it may make more sense to use [`EXTMATCH`](#fnmatchextmatch) which will only generate a single
pattern: `@(ab|ac|ad)`.

Be careful with patterns such as `{1..100}` which would generate one hundred patterns that will all get individually
parsed. Sometimes you really need such a pattern, but be mindful that it will be slower as you generate larger sets of
patterns.

#### `fnmatch.SPLIT, fnmatch.S` {: #fnmatchsplit}

`SPLIT` is used to take a string of multiple patterns that are delimited by `|` and split them into separate patterns.
This is provided to help with some interfaces that might need a way to define multiple patterns in one input. It takes
into account things like sequences (`[]`) and extended patterns (`*(...)`) and will not parse `|` within them.  You can
escape the delimiters if needed: `\|`.

```pycon3
>>> from wcmatch import fnmatch
>>> fnmatch.fnmatch('test.txt', r'*.txt|*.py', flags=fnmatch.SPLIT)
True
>>> fnmatch.fnmatch('test.py', r'*.txt|*.py', flags=fnmatch.SPLIT)
True
```

#### `fnmatch.FORCEWIN, fnmatch.W` {: #fnmatchforcewin}

`FORCEWIN` will force Windows name and case logic to be used on Linux/Unix systems. It will also cause slashes to be
normalized. This is great if you need to match Windows specific names on a Linux/Unix system.

If `FORCEWIN` is used along side [`FORCEUNIX`](#fnmatchforceunix), both will be ignored.

!!! new "New 4.2"
    `FORCEWIN` is new in 4.2.0.

#### `fnmatch.FORCEUNIX, fnmatch.U` {: #fnmatchforceunix}

`FORCEUNIX` will force Linux/Unix name and case logic to be used on Windows systems. This is great if you need to match
Linux/Unix specific names on a Windows system.

When using `FORCEUNIX`, the names are assumed to be case sensitive, but you can use [`IGNORECASE`](#fnmatchignorecase)
to use case insensitivity.

If `FORCEUNIX` is used along side [`FORCEWIN`](#fnmatchforcewin), both will be ignored.

!!! new "New 4.2"
    `FORCEUNIX` is new in 4.2.0.

--8<--
refs.txt
--8<--
