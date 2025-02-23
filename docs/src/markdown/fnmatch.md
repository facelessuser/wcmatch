# `wcmatch.fnmatch`

```py
from wcmatch import fnmatch
```

## Syntax

The `fnmatch` library is similar to the builtin [`fnmatch`][fnmatch], but with some enhancements and some differences.
It is mainly used for matching filenames with glob patterns. For path names, Wildcard Match's
[`globmatch`](./glob.md#globmatch) is a more appropriate choice. Not all of the features listed below are enabled by
default. See [flags](#flags) for more information.

/// tip | Backslashes
When using backslashes, it is helpful to use raw strings. In a raw string, a single backslash is used to escape a
character `#!py r'\?'`.  If you want to represent a literal backslash, you must use two: `#!py r'some\\path'`.
///

Pattern           | Meaning
----------------- | -------
`*`               | Matches everything.
`?`               | Matches any single character.
`[seq]`           | Matches any character in seq.
`[!seq]`          | Matches any character not in seq. Will also accept character exclusions in the form of `[^seq]`.
`[[:alnum:]]`     | POSIX style character classes inside sequences. See [POSIX Character Classes](#posix-character-classes) for more info.
`\`               | Escapes characters. If applied to a meta character or non-meta characters, the character will be treated as a literal character. If applied to another escape, the backslash will be a literal backslash.
`!`               | When used at the start of a pattern, the pattern will be an exclusion pattern. Requires the [`NEGATE`](#negate) flag. If also using the [`MINUSNEGATE`](#minusnegate) flag, `-` will be used instead of `!`.
`?(pattern_list)` | The pattern matches if zero or one occurrences of any of the patterns in the `pattern_list` match the input string. Requires the [`EXTMATCH`](#extmatch) flag.
`*(pattern_list)` | The pattern matches if zero or more occurrences of any of the patterns in the `pattern_list` match the input string. Requires the [`EXTMATCH`](#extmatch) flag.
`+(pattern_list)` | The pattern matches if one or more occurrences of any of the patterns in the `pattern_list` match the input string. Requires the [`EXTMATCH`](#extmatch) flag.
`@(pattern_list)` | The pattern matches if exactly one occurrence of any of the patterns in the `pattern_list` match the input string. Requires the [`EXTMATCH`](#extmatch) flag.
`!(pattern_list)` | The pattern matches if the input string cannot be matched with any of the patterns in the `pattern_list`. Requires the [`EXTMATCH`](#extmatch) flag.
`{}`              | Bash style brace expansions.  This is applied to patterns before anything else. Requires the [`BRACE`](#brace) flag.

-   Slashes are generally treated as normal characters, but on windows they are normalized. On Windows, `/` will match
    both `/` and `\\`. There is no need to explicitly use `\\` in patterns on Windows, but if you do, they must be escaped
    to specify a literal `\\`. If a backslash is escaped, it will match all valid windows separators, just like `/` does.
-   By default, `.` is *not* matched by `*`, `?`, and `[]`. See the [`DOTMATCH`](#dotmatch) flag to match `.` at
    the start of a filename without a literal `.`.

--8<-- "posix.md"

## Multi-Pattern Limits

Many of the API functions allow passing in multiple patterns or using either [`BRACE`](#brace) or
[`SPLIT`](#split) to expand a pattern in to more patterns. The number of allowed patterns is limited `1000`, but
you can raise or lower this limit via the keyword option `limit`. If you set `limit` to `0`, there will
be no limit.

/// new | New 6.0
The imposed pattern limit and corresponding `limit` option was introduced in 6.0.
///

## Precompiling

While patterns are often cached, auto expanding patterns, such as `'file{a, b, c}'` will have each individual
permutation cached (up to the cache limit), but not the entire pattern. This is to prevent the cache from exploding with
really large patterns such as `{1..100}`. Essentially, individual patterns are cached, but not the expansion of a
pattern into many patterns.

If it is planned to reuse a pattern and the performance hit of recompiling is not desired, you can precompile a matcher
object via [`fnmatch.compile`](#compile) which returns a [`WcMatcher`](#wcmatcher) object.

```py
>>> import wcmatch.fnmatch as fnmatch
>>> m = fnmatch.compile('*.md')
>>> m.match('README.md')
True
>>> m.filter(['test.txt', 'file.md', 'README.md'])
['file.md', 'README.md']
```

## API

#### `fnmatch.fnmatch` {: #fnmatch}

```py
def fnmatch(filename, patterns, *, flags=0, limit=1000, exclude=None)
```

`fnmatch` takes a file name, a pattern (or list of patterns), and flags.  It also allows configuring the [max pattern
limit](#multi-pattern-limits). Exclusion patterns can be specified via the `exclude` parameter which takes a pattern or
a list of patterns. It will return a boolean indicating whether the file name was matched by the pattern(s).

```pycon3
>>> from wcmatch import fnmatch
>>> fnmatch.fnmatch('test.txt', '@(*.txt|*.py)', flags=fnmatch.EXTMATCH)
True
```

When applying multiple patterns, a file matches if it matches any of the patterns:

```pycon3
>>> from wcmatch import fnmatch
>>> fnmatch.fnmatch('test.txt', ['*.txt', '*.py'], flags=fnmatch.EXTMATCH)
True
```

Exclusions can be used by taking advantage of the `exclude` parameter. It takes a single exclude pattern or a list of
patterns. Files that match the exclude pattern will not be matched.

```pycon3
>>> from wcmatch import fnmatch
>>> fnmatch.fnmatch('test.py', '*', exclude='*.py')
False
>>> fnmatch.fnmatch('test.txt', '*', exclude='*.py')
True
```

Inline exclusion patterns are allowed as well. When exclusion patterns are used in conjunction with inclusion patterns,
a file will be considered matched if one of the inclusion patterns match **and** none of the exclusion patterns match.
If an exclusion pattern is given without any inclusion patterns, the pattern will match nothing. Exclusion patterns are
meant to filter other patterns, not match anything by themselves.

```pycon3
>>> from wcmatch import fnmatch
>>> fnmatch.fnmatch('test.py', '*|!*.py', flags=fnmatch.NEGATE | fnmatch.SPLIT)
False
>>> fnmatch.fnmatch('test.txt', '*|!*.py', flags=fnmatch.NEGATE | fnmatch.SPLIT)
True
>>> fnmatch.fnmatch('test.txt', ['*.txt', '!avoid.txt'], flags=fnmatch.NEGATE)
True
>>> fnmatch.fnmatch('avoid.txt', ['*.txt', '!avoid.txt'], flags=fnmatch.NEGATE)
False
```

As mentioned, exclusion patterns need to be applied to a inclusion pattern to work, but if it is desired, you can force
exclusion patterns to assume all files should be filtered with the exclusion pattern(s) with the
[`NEGATEALL`](#negateall) flag. Essentially, it means if you use a pattern such as `!*.md`, it will assume two
pattern were given: `*` and `!*.md`.

```pycon3
>>> from wcmatch import fnmatch
>>> fnmatch.fnmatch('test.py', '!*.py', flags=fnmatch.NEGATE | fnmatch.NEGATEALL)
False
>>> fnmatch.fnmatch('test.txt', '!*.py', flags=fnmatch.NEGATE | fnmatch.NEGATEALL)
True
```

/// new | New 6.0
`limit` was added in 6.0.
///

/// new | New 8.4
`exclude` parameter was added.
///

#### `fnmatch.filter` {: #filter}

```py
def filter(filenames, patterns, *, flags=0, limit=1000, exclude=None):
```

`filter` takes a list of filenames, a pattern (or list of patterns), and flags. It also allows configuring the [max 
pattern limit](#multi-pattern-limits). Exclusion patterns can be specified via the `exclude` parameter which takes a
pattern or a list of patterns.It returns a list of all files that matched the pattern(s). The same logic used for
[`fnmatch`](#fnmatch) is used for `filter`, albeit more efficient for processing multiple files.

```pycon3
>>> from wcmatch import fnmatch
>>> fnmatch.filter(['a.txt', 'b.txt', 'c.py'], '*.txt')
['a.txt', 'b.txt']
```

/// new | New 6.0
`limit` was added in 6.0.
///

/// new | New 8.4
`exclude` parameter was added.
///

#### `fnmatch.compile` {: #compile}

```py
def compile(patterns, *, flags=0, limit=1000, exclude=None):
```

The `compile` function takes a file pattern (or list of patterns) and flags. It also allows configuring the [max pattern
limit](#multi-pattern-limits). Exclusion patterns can be specified via the `exclude` parameter which takes a pattern or
a list of patterns. It returns a [`WcMatcher`](#wcmatcher) object which can match or filter file paths depending on
which method is called.

```pycon3
>>> import wcmatch.fnmatch as fnmatch
>>> m = fnmatch.compile('*.md')
>>> m.match('README.md')
True
>>> m.filter(['test.txt', 'file.md', 'README.md'])
['file.md', 'README.md']
```

#### `fnmatch.WcMatcher` {: #wcmatcher}

The `WcMatcher` class is returned when a pattern is precompiled with [`compile`](#compile). It has two methods: `match`
and `filter`.

```py
def match(self, filename):
```

This `match` method allows for matching against a precompiled pattern.

```pycon3
>>> import wcmatch.fnmatch as fnmatch
>>> m = fnmatch.compile('*.md')
>>> m.match('README.md')
True
```

```py
def filter(self, filenames):
```

The `filter` method allows for filtering paths against a precompiled pattern.

```pycon3
>>> import wcmatch.fnmatch as fnmatch
>>> m = fnmatch.compile('*.md')
>>> m.filter(['test.txt', 'file.md', 'README.md'])
['file.md', 'README.md']
```

#### `fnmatch.translate` {: #translate}

```py
def translate(patterns, *, flags=0, limit=1000, exclude=None):
```

`translate` takes a file pattern (or list of patterns) and flags. It also allows configuring the [max pattern
limit](#multi-pattern-limits). Exclusion patterns can be specified via the `exclude` parameter which takes a pattern or
a list of patterns. It returns two lists: one for inclusion patterns and one for exclusion patterns. The lists contain
the regular expressions used for matching the given patterns. It should be noted that a file is considered matched if it
matches at least one inclusion pattern and matches **none** of the exclusion patterns.

```pycon3
>>> from wcmatch import fnmatch
>>> fnmatch.translate('*.{a,{b,c}}', flags=fnmatch.BRACE)
(['^(?s:(?=.)(?![.]).*?\\.a)$', '^(?s:(?=.)(?![.]).*?\\.b)$', '^(?s:(?=.)(?![.]).*?\\.c)$'], [])
>>> fnmatch.translate('**|!*.{a,{b,c}}', flags=fnmatch.BRACE | fnmatch.NEGATE | fnmatch.SPLIT)
(['^(?s:(?=.)(?![.]).*?)$'], ['^(?s:(?=.).*?\\.a)$', '^(?s:(?=.).*?\\.b)$', '^(?s:(?=.).*?\\.c)$'])
```

When using [`EXTMATCH`](#extmatch) patterns, patterns will be returned with capturing groups around the groups:

While in regex patterns like `#!py r'(a)+'` would capture only the last character, even though multiple where matched,
we wrap the entire group to be captured: `#!py '+(a)'` --> `#!py r'((a)+)'`.

```pycon3
>>> from wcmatch import fnmatch
>>> import re
>>> gpat = fnmatch.translate("@(file)+([[:digit:]])@(.*)", flags=fnmatch.EXTMATCH)
>>> pat = re.compile(gpat[0][0])
>>> pat.match('file33.test.txt').groups()
('file', '33', '.test.txt')
```

/// new | New 6.0
`limit` was added in 6.0.
///

/// new | New 7.1
Translate patterns now provide capturing groups for [`EXTMATCH`](#extmatch) groups.
///

/// new | New 8.4
`exclude` parameter was added.
///

#### `fnmatch.escape` {: #escape}

```py
def escape(pattern):
```

The `escape` function will conservatively escape `-`, `!`, `*`, `?`, `(`, `)`, `[`, `]`, `|`, `{`, `}`, and `\` with
backslashes, regardless of what feature is or is not enabled. It is meant to escape filenames.

```pycon3
>>> from wcmatch import fnmatch
>>> fnmatch.escape('**file**{}.txt')
'\\*\\*file\\*\\*\\{\\}.txt'
>>> fnmatch.fnmatch('**file**{}.txt', fnmatch.escape('**file**{}.txt'))
True
```

/// new | New 8.1
An `escape` variant for `fnmatch` was made available in 8.1.
///

### `fnmatch.is_magic` {: #is_magic}

```py
def is_magic(pattern, *, flags=0):
    """Check if the pattern is likely to be magic."""
```

This checks a given filename or `pattern` to see if it is "magic" or not. The check is based on the enabled features via
`flags`. Filenames or patterns are expected to be/target full names. This variant of `is_magic` is meant to be run on
filenames or patterns for file names only. If you need to check patterns with full paths, particularly Windows paths
that include drive names or UNC sharepoints (which require special logic), it is recommended to use the
[`glob.escape`](./glob.md#escape) function.

```pycon3
>>> fnmatch.is_magic('test')
False
>>> fnmatch.is_magic('[test]ing?')
True
```

The table below illustrates which symbols are searched for based on the given feature. Each feature adds to the
"default". In the case of [`NEGATE`](#negate), if [`MINUSNEGATE`](#minusnegate) is also enabled,
[`MINUSNEGATE`](#minusnegate)'s symbols will be searched instead of [`NEGATE`](#negate)'s symbols.

Features                      | Symbols
----------------------------- | -------
Default                       | `?*[]\`
[`EXTMATCH`](#extmatch)       | `()`
[`BRACE`](#brace)             | `{}`
[`NEGATE`](#negate)           | `!`
[`MINUSNEGATE`](#minusnegate) | `-`
[`SPLIT`](#split)             | `|`

/// new | New 8.1
Added `is_magic` in 8.1.
///

## Flags

#### `fnmatch.CASE, fnmatch.C` {: #case}

`CASE` forces case sensitivity. `CASE` has higher priority than [`IGNORECASE`](#ignorecase).

#### `fnmatch.IGNORECASE, fnmatch.I` {: #ignorecase}

`IGNORECASE` forces case insensitivity. [`CASE`](#case) has higher priority than `IGNORECASE`.

#### `fnmatch.RAWCHARS, fnmatch.R` {: #rawchars}

`RAWCHARS` causes string character syntax to be parsed in raw strings: `#!py r'\u0040'` --> `#!py r'@'`. This will
handle standard string escapes and Unicode including `#!py r'\N{CHAR NAME}'`.

#### `fnmatch.NEGATE, fnmatch.N` {: #negate}

`NEGATE` causes patterns that start with `!` to be treated as exclusion patterns. A pattern of `!*.py` would match any
file but Python files. Exclusion patterns cannot be used by themselves though, and must be paired with a normal,
inclusion pattern, either by utilizing the [`SPLIT`](#split) flag, or providing multiple patterns in a list.
Assuming the `SPLIT` flag, this means using it in a pattern such as `inclusion|!exclusion`.

If it is desired, you can force exclusion patterns, when no inclusion pattern is provided, to assume all files match
unless the file matches the excluded pattern. This is done with the [`NEGATEALL`](#negateall) flag.

`NEGATE` enables [`DOTMATCH`](#dotglob) in all exclude patterns, this cannot be disabled. This will not affect the
inclusion patterns.

If `NEGATE` is set and exclusion patterns are passed via a matching function's `exclude` parameter, `NEGATE` will be
ignored and the `exclude` patterns will be used instead. Either `exclude` or `NEGATE` should be used, not both.

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

/// tip | EXTMATCH and NEGATE
When using `EXTMATCH` and [`NEGATE`](#negate) together, if a pattern starts with `!(`, the pattern will not
be treated as a [`NEGATE`](#negate) pattern (even if `!(` doesn't yield a valid `EXTMATCH` pattern). To
negate a pattern that starts with a literal `(`, you must escape the bracket: `!\(`.
///

#### `fnmatch.BRACE, fnmatch.B` {: #brace}

`BRACE` enables Bash style brace expansion: `a{b,{c,d}}` --> `ab ac ad`. Brace expansion is applied before anything
else. When applied, a pattern will be expanded into multiple patterns. Each pattern will then be parsed separately.
Redundant, identical patterns are discarded[^1] by default.

For simple patterns, it may make more sense to use [`EXTMATCH`](#extmatch) which will only generate a single
pattern which will perform much better: `@(ab|ac|ad)`.

/// warning | Massive Expansion Risk
1.  It is important to note that each pattern is matched separately, so patterns such as `{1..100}` would generate
    **one hundred** patterns. Sometimes patterns like this are needed, so construct patterns thoughtfully and carefully.

2.  `BRACE` and [`SPLIT`](#split) both expand patterns into multiple patterns. Using these two syntaxes
    simultaneously can exponential increase in duplicate patterns:

    ```pycon3
    >>> expand('test@(this{|that,|other})|*.py', BRACE | SPLIT | EXTMATCH)
    ['test@(this|that)', 'test@(this|other)', '*.py', '*.py']
    ```

    This effect is reduced as redundant, identical patterns are optimized away[^1]. But it is useful to know if
    trying to construct efficient patterns.
///

[^1]: Identical patterns are only reduced by comparing case sensitively as POSIX character classes are case sensitive:
`[[:alnum:]]` =/= `[[:ALNUM:]]`.

#### `fnmatch.SPLIT, fnmatch.S` {: #split}

`SPLIT` is used to take a string of multiple patterns that are delimited by `|` and split them into separate patterns.
This is provided to help with some interfaces that might need a way to define multiple patterns in one input. It pairs
really well with [`EXTMATCH`](#extmatch) and takes into account sequences (`[]`) and extended patterns (`*(...)`)
and will not parse `|` within them.  You can also escape the delimiters if needed: `\|`.

While `SPLIT` is not as powerful as [`BRACE`](#brace), it's syntax is very easy to use, and when paired with
[`EXTMATCH`](#extmatch), it feels natural and comes a bit closer. It also much harder to create massive
expansions of patterns with it, except when paired *with* [`BRACE`](#brace). See [`BRACE`](#brace) and
it's warnings related to pairing it with `SPLIT`.

```pycon3
>>> from wcmatch import fnmatch
>>> fnmatch.fnmatch('test.txt', '*.txt|*.py', flags=fnmatch.SPLIT)
True
>>> fnmatch.fnmatch('test.py', '*.txt|*.py', flags=fnmatch.SPLIT)
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
