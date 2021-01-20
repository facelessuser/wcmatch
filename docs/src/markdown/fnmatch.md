# `wcmatch.fnmatch`

```py3
from wcmatch import fnmatch
```

## Syntax

The `fnmatch` library is similar to the builtin [`fnmatch`][fnmatch], but with some enhancements and some differences.
It is mainly used for matching filenames with glob patterns. For path names, Wildcard Match's
[`globmatch`](./glob.md#globmatch) is a more appropriate choice. Not all of the features listed below are enabled by
default. See [flags](#flags) for more information.

!!! tip "Backslashes"
    When using backslashes, it is helpful to use raw strings. In a raw string, a single backslash is used to escape a
    character `#!py3 r'\?'`.  If you want to represent a literal backslash, you must use two: `#!py3 r'some\\path'`.

Pattern           | Meaning
----------------- | -------
`*`               | Matches everything.
`?`               | Matches any single character.
`[seq]`           | Matches any character in seq.
`[!seq]`          | Matches any character not in seq. Will also accept character exclusions in the form of `[^seq]`.
`[[:alnum:]]`     | POSIX style character classes inside sequences. See [POSIX Character Classes](#posix-character-classes) for more info.
`\`               | Escapes characters. If applied to a meta character, it will be treated as a normal character.
`!`               | When used at the start of a pattern, the pattern will be an exclusion pattern. Requires the [`NEGATE`](#negate) flag. If also using the [`MINUSNEGATE`](#minusnegate) flag, `-` will be used instead of `!`.
`?(pattern_list)` | The pattern matches if zero or one occurrences of any of the patterns in the `pattern_list` match the input string. Requires the [`EXTMATCH`](#extmatch) flag.
`*(pattern_list)` | The pattern matches if zero or more occurrences of any of the patterns in the `pattern_list` match the input string. Requires the [`EXTMATCH`](#extmatch) flag.
`+(pattern_list)` | The pattern matches if one or more occurrences of any of the patterns in the `pattern_list` match the input string. Requires the [`EXTMATCH`](#extmatch) flag.
`@(pattern_list)` | The pattern matches if exactly one occurrence of any of the patterns in the `pattern_list` match the input string. Requires the [`EXTMATCH`](#extmatch) flag.
`!(pattern_list)` | The pattern matches if the input string cannot be matched with any of the patterns in the `pattern_list`. Requires the [`EXTMATCH`](#extmatch) flag.
`{}`              | Bash style brace expansions.  This is applied to patterns before anything else. Requires the [`BRACE`](#brace) flag.

- Slashes are generally treated as normal characters, but on windows they will be normalized: `/` will become `\\`.
  There is no need to explicitly use `\\` in patterns on Windows, but if you do, it will be handled.  This applies to
  matching patterns and the filenames the patterns are applied to.
- By default, `.` is *not* matched by `*`, `?`, and `[]`. See the [`DOTMATCH`](#dotmatch) flag to match `.` at
  the start of a filename without a literal `.`.

--8<-- "posix.txt"

## Multi-Pattern Limits

Many of the API functions allow passing in multiple patterns or using either [`BRACE`](#brace) or
[`SPLIT`](#split) to expand a pattern in to more patterns. The number of allowed patterns is limited `1000`, but
you can raise or lower this limit via the keyword option `limit`. If you set `limit` to `0`, there will
be no limit.

!!! new "New 6.0"
    The imposed pattern limit and corresponding `limit` option was introduced in 6.0.

## API

#### `fnmatch.fnmatch` {: #fnmatch}

```py3
def fnmatch(filename, patterns, *, flags=0, limit=1000)
```

`fnmatch` takes a file name, a pattern (or list of patterns), and flags.  It also allows configuring the [max pattern
limit](#multi-pattern-limits). It will return a boolean indicating whether the file name was matched by the pattern(s).

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
[`NEGATEALL`](#negateall) flag. Essentially, it means if you use a pattern such as `!*.md`, it will assume two
pattern were given: `*` and `!*.md`.

```pycon3
>>> from wcmatch import fnmatch
>>> fnmatch.fnmatch('test.py', r'!*.py', flags=fnmatch.NEGATE | fnamtch.NEGATEALL)
False
>>> fnmatch.fnmatch('test.txt', r'!*.py', flags=fnmatch.NEGATE | fnamtch.NEGATEALL)
True
```

!!! new "New 6.0"
    `limit` was added in 6.0.

#### `fnmatch.filter` {: #filter}

```py3
def filter(filenames, patterns, *, flags=0, limit=1000):
```

`filter` takes a list of filenames, a pattern (or list of patterns), and flags. It also allows configuring the [max 
pattern limit](#multi-pattern-limits). It returns a list of all files that matched the pattern(s). The same logic used for
[`fnmatch`](#fnmatch) is used for `filter`, albeit more efficient for processing multiple files.

```pycon3
>>> from wcmatch import fnmatch
>>> fnmatch.filter(['a.txt', 'b.txt', 'c.py'], r'*.txt')
['a.txt', 'b.txt']
```

!!! new "New 6.0"
    `limit` was added in 6.0.

#### `fnmatch.translate` {: #translate}

```py3
def translate(patterns, *, flags=0, limit=1000):
```

`translate` takes a file pattern (or list of patterns) and flags. It also allows configuring the [max pattern
limit](#multi-pattern-limits). It returns two lists: one for inclusion patterns and one for exclusion patterns. The
lists contain the regular expressions used for matching the given patterns. It should be noted that a file is considered
matched if it matches at least one inclusion pattern and matches **none** of the exclusion patterns.

```pycon3
>>> from wcmatch import translate
>>> fnmatch.translate(r'*.{a,{b,c}}', flags=fnmatch.BRACE)
(['^(?s:(?=.).*?\\.a)$', '^(?s:(?=.).*?\\.b)$', '^(?s:(?=.).*?\\.c)$'], [])
>>> fnmatch.translate(r'**|!*.{a,{b,c}}', flags=fnmatch.BRACE | fnmatch.NEGATE | fnmatch.SPLIT)
(['^(?s:(?=.)(?![.]).*?)$'], ['^(?s:(?=.).*?\\.a)$', '^(?s:(?=.).*?\\.b)$', '^(?s:(?=.).*?\\.c)$'])
```

When using [`EXTMATCH`](#extmatch) patterns, patterns will be returned with capturing groups around the groups:

While in regex patterns like `#!py3 r'(a)+'` would capture only the last character, even though multiple where matched,
we wrap the entire group to be captured: `#!py3 '+(a)'` --> `#!py3 r'((a)+)'`.

```pycon3
>>> from wcmatch import fnmatch
>>> import re
>>> gpat = fnmatch.translate("@(file)+([[:digit:]])@(.*)", flags=fnmatch.EXTMATCH)
>>> pat = re.compile(gpat[0][0])
>>> pat.match('file33.test.txt').groups()
('file', '33', '.test.txt')
```

!!! new "New 6.0"
    `limit` was added in 6.0.

!!! new "New 7.1"
    Translate patterns now provide capturing groups for [`EXTMATCH`](#extmatch) groups.

## Flags

#### `fnmatch.CASE, fnmatch.C` {: #case}

`CASE` forces case sensitivity. `CASE` has higher priority than [`IGNORECASE`](#ignorecase).

#### `fnmatch.IGNORECASE, fnmatch.I` {: #ignorecase}

`IGNORECASE` forces case insensitivity. [`CASE`](#case) has higher priority than `IGNORECASE`.

#### `fnmatch.RAWCHARS, fnmatch.R` {: #rawchars}

`RAWCHARS` causes string character syntax to be parsed in raw strings: `#!py3 r'\u0040'` --> `#!py3 r'@'`. This will
handle standard string escapes and Unicode including `#!py3 r'\N{CHAR NAME}'`.

#### `fnmatch.NEGATE, fnmatch.N` {: #negate}

`NEGATE` causes patterns that start with `!` to be treated as exclusion patterns. A pattern of `!*.py` would match any
file but Python files. Exclusion patterns cannot be used by themselves though, and must be paired with a normal,
inclusion pattern, either by utilizing the [`SPLIT`](#split) flag, or providing multiple patterns in a list.
Assuming the `SPLIT` flag, this means using it in a pattern such as `inclusion|!exclusion`.

If it is desired, you can force exclusion patterns, when no inclusion pattern is provided, to assume all files match
unless the file matches the excluded pattern. This is done with the [`NEGATEALL`](#negateall) flag.

#### `fnmatch.NEGATEALL, fnmatch.A` {: #negateall}

`NEGATEALL` can force exclusion patterns, when no inclusion pattern is provided, to assume all files match unless the
file matches the excluded pattern. Essentially, it means if you use a pattern such as `!*.md`, it will assume two
patterns were given: `*` and `!*.md`, where `!*.md` is applied to the results of `*`.

Dot files will not be returned unless [`DOTMATCH`](#dotmatch).

#### `fnmatch.MINUSNEGATE, fnmatch.M` {: #minusnegate}

When `MINUSNEGATE` is used with [`NEGATE`](#negate), exclusion patterns are recognized by a pattern starting with
`-` instead of `!`. This plays nice with the [`EXTMATCH`](#extmatch) option.

#### `fnmatch.DOTMATCH, fnmatch.D` {: #dotmatch}

By default, [`fnmatch`](#fnmatch) and related functions will not match file or directory names that start with
dot `.` unless matched with a literal dot. `DOTMATCH` allows the meta characters (such as `*`) to match dots like any
other character. Dots will not be matched in `[]`, `*`, or `?`.

#### `fnmatch.EXTMATCH, fnmatch.E` {: #extmatch}

`EXTMATCH` enables extended pattern matching. This includes special pattern lists such as `+(...)`, `*(...)`, `?(...)`,
etc. See the [syntax overview](#syntax) for more information.

!!! tip "EXTMATCH and NEGATE"

    When using `EXTMATCH` and [`NEGATE`](#negate) together, if a pattern starts with `!(`, the pattern will not
    be treated as a [`NEGATE`](#negate) pattern (even if `!(` doesn't yield a valid `EXTMATCH` pattern). To
    negate a pattern that starts with a literal `(`, you must escape the bracket: `!\(`.

#### `fnmatch.BRACE, fnmatch.B` {: #brace}

`BRACE` enables Bash style brace expansion: `a{b,{c,d}}` --> `ab ac ad`. Brace expansion is applied before anything
else. When applied, a pattern will be expanded into multiple patterns. Each pattern will then be parsed separately.
Redundant, identical patterns are discarded[^1] by default.

For simple patterns, it may make more sense to use [`EXTMATCH`](#extmatch) which will only generate a single
pattern which will perform much better: `@(ab|ac|ad)`.

!!! warning "Massive Expansion Risk"
    1. It is important to note that each pattern is matched separately, so patterns such as `{1..100}` would generate
    **one hundred** patterns. Sometimes patterns like this are needed, so construct patterns thoughtfully and carefully.

    2. `BRACE` and [`SPLIT`](#split) both expand patterns into multiple patterns. Using these two syntaxes
    simultaneously can exponential increase in duplicate patterns:

        ```pycon3
        >>> expand('test@(this{|that,|other})|*.py', BRACE | SPLIT | EXTMATCH)
        ['test@(this|that)', 'test@(this|other)', '*.py', '*.py']
        ```

        This effect is reduced as redundant, identical patterns are optimized away[^1]. But it is useful to know if
    trying to construct efficient patterns.

[^1]: Identical patterns are only reduced by comparing case sensitively as POSIX character classes are case sensitive:
`[[:alnum:]]` =/= `[[:ALNUM:]]`.

#### `fnmatch.SPLIT, fnmatch.S` {: #split}

`SPLIT` is used to take a string of multiple patterns that are delimited by `|` and split them into separate patterns.
This is provided to help with some interfaces that might need a way to define multiple patterns in one input. It pairs
really well with [`EXTGLOB`](#extmatch) and takes into account sequences (`[]`) and extended patterns (`*(...)`)
and will not parse `|` within them.  You can also escape the delimiters if needed: `\|`.

While `SPLIT` is not as powerful as [`BRACE`](#brace), it's syntax is very easy to use, and when paired with
[`EXTMATCH`](#extmatch), it feels natural and comes a bit closer. It also much harder to create massive
expansions of patterns with it, except when paired *with* [`BRACE`](#brace). See [`BRACE`](#brace) and
it's warnings related to pairing it with `SPLIT`.

```pycon3
>>> from wcmatch import fnmatch
>>> fnmatch.fnmatch('test.txt', r'*.txt|*.py', flags=fnmatch.SPLIT)
True
>>> fnmatch.fnmatch('test.py', r'*.txt|*.py', flags=fnmatch.SPLIT)
True
```

#### `fnmatch.FORCEWIN, fnmatch.W` {: #forcewin}

`FORCEWIN` will force Windows name and case logic to be used on Linux/Unix systems. It will also cause slashes to be
normalized. This is great if you need to match Windows specific names on a Linux/Unix system.

If `FORCEWIN` is used along side [`FORCEUNIX`](#forceunix), both will be ignored.

#### `fnmatch.FORCEUNIX, fnmatch.U` {: #forceunix}

`FORCEUNIX` will force Linux/Unix name and case logic to be used on Windows systems. This is great if you need to match
Linux/Unix specific names on a Windows system.

When using `FORCEUNIX`, the names are assumed to be case sensitive, but you can use [`IGNORECASE`](#ignorecase)
to use case insensitivity.

If `FORCEUNIX` is used along side [`FORCEWIN`](#forcewin), both will be ignored.

--8<--
refs.txt
--8<--
