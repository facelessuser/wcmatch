# `wcmatch.wcmatch`

```py3
from wcmatch import wcmatch
```

## Overview

`wcmatch.WcMatch` was originally written to provide a simple user interface for searching specific files in
[Rummage](https://github.com/facelessuser/Rummage). A class was needed to facilitate a user interface where a user could
select a root directory, define one or more file patterns they wanted to search for, and provide folders to exclude if
needed. It needed to be aware of hidden files on different systems, not just ignoring files that start with `.`. It also
needed to be extendable so we could further filter returned files by size, creation date, or whatever else was decided.
While [`glob`](./glob.md) is a fantastic file and folder search tool, it just didn't make sense for such a user
interface.

## `wcmatch.WcMatch` {: #wcmatch}

```py3
class WcMatch:
    """Finds files by wildcard."""

    def __init__(self, root_dir=".", file_pattern=None, **kwargs):
        """Initialize the directory walker object."""
```

`WcMatch` is an extendable file search class. It allows you to specify a root directory path, file patterns, and
optional folder exclude patterns. You can specify whether you want to see hidden files and whether the search should be
recursive. You can also derive from the class and tap into specific hooks to change what is returned or done when a file
is matched, skipped, or when there is an error. There are also hooks where you can inject additional, custom filtering.

Parameter         | Default       | Description
----------------- | ------------- | -----------
`root_dir`        |               | The root directory to search.
`file_pattern`    | `#!py3 ''`    | One or more patterns separated by `|`. You can define exceptions by starting a pattern with `!` (or `-` if [`MINUSNEGATE`](#minusnegate) is set). The default is an empty string, but if an empty string is used, all files will be matched.
`exclude_pattern` | `#!py3 ''`    | Zero or more folder exclude patterns separated by `|`. You can define exceptions by starting a pattern with `!` (or `-` if [`MINUSNEGATE`](#minusnegate) is set).
`flags`           | `#!py3 0`     | Flags to alter behavior of folder and file matching. See [Flags](#flags) for more info.
`limit`           | `#!py3 1000`  | Allows configuring the [max pattern limit](#multi-pattern-limits).

!!! note
    Dots are not treated special in `wcmatch`. When the `HIDDEN` flag is not included, all hidden files (system and dot
    files) are excluded from the crawling processes, so there is no risk of `*` matching a dot file as it will not show
    up in the crawl. If the `HIDDEN` flag is included, `*`, `?`, and `[.]` will then match dot files.

!!! new "New 6.0"
    `limit` was added in 6.0.

### Multi-Pattern Limits

The `WcMatch` class allow expanding a pattern into multiple patterns by using `|` and by using [`BRACE`](#brace).
The number of allowed patterns is limited `1000`, but you can raise or lower this limit via the keyword option
`limit`. If you set `limit` to `0`, there will be no limit.

!!! new "New 6.0"
    The imposed pattern limit and corresponding `limit` option was introduced in 6.0.

### Examples

Searching for files:

```pycon3
>>> from wcmatch import wcmatch
>>> wcmatch.WcMatch('.', '*.md|*.txt').match()
['./LICENSE.md', './README.md']
```

Recursively searching for files:

```pycon3
>>> from wcmatch import wcmatch
>>> wcmatch.WcMatch('.', '*.md|*.txt', flags=wcmatch.RECURSIVE).match()
['./LICENSE.md', './README.md', './docs/src/markdown/changelog.md', './docs/src/markdown/fnmatch.md', './docs/src/markdown/glob.md', './docs/src/markdown/index.md', './docs/src/markdown/installation.md', './docs/src/markdown/license.md', './docs/src/markdown/wcmatch.md', './docs/src/markdown/_snippets/abbr.md', './docs/src/markdown/_snippets/links.md', './docs/src/markdown/_snippets/refs.md', './requirements/docs.txt', './requirements/lint.txt', './requirements/setup.txt', './requirements/test.txt']
```

Excluding directories:

```pycon3
>>> from wcmatch import wcmatch
>>> wcmatch.WcMatch('.', '*.md|*.txt', exclude_pattern='docs', flags=wcmatch.RECURSIVE).match()
['./LICENSE.md', './README.md', './requirements/docs.txt', './requirements/lint.txt', './requirements/setup.txt', './requirements/test.txt']
```

Using file negation patterns:

```pycon3
>>> from wcmatch import wcmatch
>>> wcmatch.WcMatch('.', '*.md|*.txt|!README*', exclude_pattern='docs', flags=wcmatch.RECURSIVE).match()
['./LICENSE.md', './requirements/docs.txt', './requirements/lint.txt', './requirements/setup.txt', './requirements/test.txt']
```

You can also use negation patterns in directory exclude. Here we avoid all folders with `*`, but add an exception for
`requirements`. It should be noted that you cannot add an exception for the child of an excluded folder.

```pycon3
>>> from wcmatch import wcmatch
>>> wcmatch.WcMatch('.', '*.md|*.txt', exclude_pattern='*|!requirements', flags=wcmatch.RECURSIVE).match()
['./LICENSE.md', './README.md', './requirements/docs.txt', './requirements/lint.txt', './requirements/setup.txt', './requirements/test.txt']
```

Negative patterns can be given by themselves.

```pycon3
>>> from wcmatch import wcmatch
>>> wcmatch.WcMatch('.', '*.md|*.txt', exclude_pattern='!requirements', flags=wcmatch.RECURSIVE).match()
['./LICENSE.md', './README.md', './requirements/docs.txt', './requirements/lint.txt', './requirements/setup.txt', './requirements/test.txt']
```

Enabling hidden files:

```pycon3
>>> from wcmatch import wcmatch
>>> wcmatch.WcMatch('.', '*.yml').match()
['./appveyor.yml', './mkdocs.yml']
>>> wcmatch.WcMatch('.', '*.yml', flags=wcmatch.HIDDEN).match()
['./.codecov.yml', './.travis.yml', './appveyor.yml', './mkdocs.yml']
```

## Methods

#### `WcMatch.match` {: #match}

Perform match returning files that match the patterns.

```pycon3
>>> from wcmatch import wcmatch
>>> wcmatch.WcMatch('.', '*.md|*.txt').match()
['./LICENSE.md', './README.md']
```

#### `WcMatch.imatch` {: #imatch}

Perform match returning an iterator of files that match the patterns.

```pycon3
>>> from wcmatch import wcmatch
>>> list(wcmatch.WcMatch('.', '*.md|*.txt').imatch())
['./LICENSE.md', './README.md']
```

#### `WcMatch.kill` {: #kill}

If searching with [`imatch`](#imatch), this provides a way to gracefully kill the internal searching. Internally,
you can call [`is_aborted`](#is_aborted) to check if a request to abort has been made. So if work on a file is
being done in an [`on_match`](#on_match), you can check if there has been a request to kill the process, and tie
up loose ends gracefully.

```pycon3
>>> from wcmatch import wcmatch
>>> wcm = wcmatch.WcMatch('.', '*.md|*.txt')
>>> for f in wcm.imatch():
...     print(f)
...     wcm.kill()
...
./LICENSE.md
```

Once a "kill" has been issued, the class will remain in an aborted state. To clear the "kill" state, you must call
[`reset`](#reset). This allows a process to define a `Wcmatch` class and reuse it. If a process receives an early
kill and sets it before the match is started, when the match is started, it will immediately abort. This helps with race
conditions depending on how you are using `WcMatch`.

#### `WcMatch.reset` {: #reset}

Resets the abort state after running `kill`.

```pycon3
>>> from wcmatch import wcmatch
>>> wcm = wcmatch.WcMatch('.', '*.md|*.txt')
>>> for f in wcm.imatch():
...     print(f)
...     wcm.kill()
...
./LICENSE.md
>>> wcm.reset()
>>> list(wcm.imatch())
['./LICENSE.md', './README.md']
```

#### `WcMatch.is_aborted` {: #is_aborted}

Checks if an abort has been issued.

```pycon3
>>> from wcmatch import wcmatch
>>> wcm = wcmatch.WcMatch('.', '*.md|*.txt')
>>> for f in wcm.imatch():
...     wcm.kill()
...
>>> wcm.is_aborted()
True
```

#### `WcMatch.get_skipped` {: #get_skipped}

Returns the number of skipped files. Files in skipped folders are not included in the count.

```pycon3
>>> from wcmatch import wcmatch
>>> wcm = wcmatch.WcMatch('.', '*.md|*.txt')
>>> list(wcm.imatch())
['./LICENSE.md', './README.md']
>>> wcm.get_skipped()
10
```

## Hooks

#### `WcMatch.on_init` {: #on_init}

```py3
   def on_init(self, **kwargs):
        """Handle custom init."""
```

Any keyword arguments not processed by the main initializer are sent to `on_init`. This allows you to
specify additional arguments when deriving from `WcMatch`.

!!! new "Changed 8.0"
    Starting in 8.0, `on_init` only accepts keyword arguments as now `WcMatch` requires all parameters (except
    `root_dir` and `file_pattern`) to be keyword parameters and must explicitly be specified in the form `key=value`.

#### `WcMatch.on_validate_directory` {: #on_validate_directory}

```py3
    def on_validate_directory(self, base, name):
        """Validate folder override."""

        return True
```

When validating a directory, if the directory passes validation, it will be sent to `on_validate_directory` which can be
overridden to provide additional validation if required.

#### `WcMatch.on_validate_file` {: #on_validate_file}

```py3
    def on_validate_file(self, base, name):
        """Validate file override."""

        return True
```

When validating a file, if the file passes validation, it will be sent to `on_validate_file` which can be overridden to
provide additional validation if required.

#### `WcMatch.on_skip` {: #on_skip}

```py3
    def on_skip(self, base, name):
        """On skip."""

        return None
```

When a file that must be skipped is encountered (a file that doesn't pass validation), it is sent to `on_skip`. Here you
could abort the search, store away information, or even create a special skip record to return. It is advised to create
a special type for skip returns so that you can identify them when they are returned via [`match`](#match) or
[`imatch`](#imatch).

#### `WcMatch.on_error` {: #on_error}

```py3
    def on_error(self, base, name):
        """On error."""

        return None
```

When accessing or processing a file throws an error, it is sent to `on_error`. Here you could abort the search, store
away information, or even create a special error record to return. It is advised to create a special type for error
returns so that you can identify them when they are returned via [`match`](#match) or [`imatch`](#imatch).

#### `WcMatch.on_match` {: #on_match}

```py3
    def on_match(self, base, name):
        """On match."""

        return os.path.join(base, name)
```

On match returns the path of the matched file.  You can override `on_match` and change what is returned.  You could
return just the base, you could parse the file and return the content, or return a special match record with additional
file meta data. `on_match` must return something, and all results will be returned via [`match`](#match) or
[`imatch`](#imatch).

#### `WcMatch.on_reset` {: #on_reset}

```py3
    def on_reset(self):
        """On reset."""
        pass
```

`on_reset` is a hook to provide a way to reset any custom logic in classes that have derived from `WcMatch`. `on_reset`
is called on every new [`match`](#match) call.

## Flags

#### `wcmatch.RECURSIVE, wcmatch.RV` {: #recursive}

`RECURSIVE` forces a recursive search that will crawl all subdirectories.

#### `wcmatch.HIDDEN, wcmatch.HD` {: #hidden}

`HIDDEN` enables the crawling of hidden directories and will return hidden files if the wildcard pattern matches. This
enables not just dot files, but system hidden files as well.

#### `wcmatch.SYMLINK, wcmatch.SL` {: #symlink}

`SYMLINK` enables the crawling of symlink directories. By default, symlink directories are ignored during the file
crawl.

#### `wcmatch.CASE, wcmatch.C` {: #case}

`CASE` forces case sensitivity. `CASE` has higher priority than [`IGNORECASE`](#ignorecase).

#### `wcmatch.IGNORECASE, wcmatch.I` {: #ignorecase}

`IGNORECASE` forces case insensitive searches. [`CASE`](#case) has higher priority than `IGNORECASE`.

#### `wcmatch.RAWCHARS, wcmatch.R` {: #rawchars}

`RAWCHARS` causes string character syntax to be parsed in raw strings: `#!py3 r'\u0040'` --> `#!py3 r'@'`. This will
handle standard string escapes and Unicode (including `#!py3 r'\N{CHAR NAME}'`).

#### `wcmatch.EXTMATCH, wcmatch.E` {: #extmatch}

`EXTMATCH` enables extended pattern matching which includes special pattern lists such as `+(...)`, `*(...)`, `?(...)`,
etc.

!!! tip "EXTMATCH and NEGATE"

    When using `EXTMATCH` and [`NEGATE`](#negate) together, if a pattern starts with `!(`, the pattern will not
    be treated as a [`NEGATE`](#negate) pattern (even if `!(` doesn't yield a valid `EXTMATCH` pattern). To
    negate a pattern that starts with a literal `(`, you must escape the bracket: `!\(`.

#### `wcmatch.BRACE, wcmatch.B` {: #brace}

`BRACE` enables Bash style brace expansion: `a{b,{c,d}}` --> `ab ac ad`. Brace expansion is applied before anything
else. When applied, a pattern will be expanded into multiple patterns. Each pattern will then be parsed separately.
Redundant, identical patterns are discarded[^1] by default.

For simple patterns, it may make more sense to use [`EXTMATCH`](#extmatch) which will only generate a single
pattern which will perform much better: `@(ab|ac|ad)`.

!!! warning "Massive Expansion Risk"
    1. It is important to note that each pattern is matched separately, so patterns such as `{1..100}` would generate
    **one hundred** patterns. Since [`WcMatch`](#wcmatch_1) class is able to crawl the file system one pass
    accounting for all the patterns, the performance isn't as bad as it may be with [`glob`](./glob.md), but it can
    still impact performance as each file must get compared against many patterns until one is matched. Sometimes
    patterns like this are needed, so construct patterns thoughtfully and carefully.

    2. Splitting patterns with `|` is built into [`WcMatch`](#wcmatch_1). `BRACE` and and splitting with `|` both
    expand patterns into multiple patterns. Using these two syntaxes simultaneously can exponential increase in
    duplicate patterns:

        ```pycon3
        >>> expand('test@(this{|that,|other})|*.py', BRACE | SPLIT | EXTMATCH)
        ['test@(this|that)', 'test@(this|other)', '*.py', '*.py']
        ```

        This effect is reduced as redundant, identical patterns are optimized away[^1]. But it is useful to know if
    trying to construct efficient patterns.

[^1]: Identical patterns are only reduced by comparing case sensitively as POSIX character classes are case sensitive:
`[[:alnum:]]` =/= `[[:ALNUM:]]`.

#### `wcmatch.MINUSNEGATE, wcmatch.M` {: #minusnegate}

`MINUSNEGATE` requires negation patterns to use `-` instead of `!`.

#### `wcmatch.DIRPATHNAME, wcmatch.DP` {: #dirpathname}

`DIRPATHNAME` will enable path name searching for excluded folder patterns, but it will not apply to file patterns. This
is mainly provided for cases where you may have multiple folders with the same name, but you want to target a specific
folder to exclude. The path name compared will be the entire path relative to the root directory.  So if the provided
root directory folder was `.`, and the folder under evaluation is `./some/folder`, `some/folder` will be matched against
the pattern.

```pycon3
>>> from wcmatch import wcmatch
>>> wcmatch.WcMatch('.', '*.md|*.txt', 'docs/src/markdown', flags=wcmatch.DIRPATHNAME | wcmatch.RECURSIVE).match()
['./LICENSE.md', './README.md', './requirements/docs.txt', './requirements/lint.txt', './requirements/setup.txt', './requirements/test.txt']
```

#### `wcmatch.FILEPATHNAME, wcmatch.FP` {: #filepathname}

`FILEPATHNAME` will enable path name searching for the file patterns, but it will not apply to directory exclude
patterns. The path name compared will be the entire path relative to the root directory path.  So if the provided root
directory was `.`, and the file under evaluation is `./some/file.txt`, `some/file.txt` will be matched against the
pattern.

```pycon3
>>> from wcmatch import wcmatch
>>> wcmatch.WcMatch('.', '**/*.md|!**/_snippets/*', flags=wcmatch.FILEPATHNAME | wcmatch.GLOBSTAR | wcmatch.RECURSIVE).match()
['./LICENSE.md', './README.md', './docs/src/markdown/changelog.md', './docs/src/markdown/fnmatch.md', './docs/src/markdown/glob.md', './docs/src/markdown/index.md', './docs/src/markdown/license.md', './docs/src/markdown/wcmatch.md']
```

#### `wcmatch.PATHNAME, wcmatch.P` {: #pathname}

`PATHNAME` enables both [`DIRPATHNAME`](#dirpathname) and [`FILEPATHNAME`](#wcmathfilepathname). It is provided
for convenience.

#### `wcmatch.MATCHBASE, wcmatch.X` {: #matchbase}

When [`FILEPATHNAME`](#filepathname) or [`DIRPATHNAME`](#dirpathname) is enabled, `MATCHBASE` will ensure
that that the respective file or directory pattern, when there are no slashes in the pattern, seeks for any file
anywhere in the tree with a matching basename. This is essentially the behavior when
[`FILEPATHNAME`](#filepathname) and [`DIRPATHNAME`](#dirpathname) is disabled, but with `MATCHBASE`, you
can toggle the behavior by including slashes in your pattern.

When we include no slashes:

```pycon3
>>> wcmatch.WcMatch('.', '*.md', flags=wcmatch.FILEPATHNAME | wcmatch.GLOBSTAR | wcmatch.MATCHBASE | wcmatch.RECURSIVE).match()
['./LICENSE.md', './README.md', './docs/src/markdown/changelog.md', './docs/src/markdown/fnmatch.md', './docs/src/markdown/glob.md', './docs/src/markdown/index.md', './docs/src/markdown/license.md', './docs/src/markdown/wcmatch.md']
```

If we include slashes in the pattern, the path, not the basename, must match the pattern:

```pycon3
>>> wcmatch.WcMatch('.', 'docs/**/*.md', flags=wcmatch.FILEPATHNAME | wcmatch.GLOBSTAR | wcmatch.MATCHBASE | wcmatch.RECURSIVE).match()
['./docs/src/markdown/changelog.md', './docs/src/markdown/fnmatch.md', './docs/src/markdown/glob.md', './docs/src/markdown/index.md', './docs/src/markdown/license.md', './docs/src/markdown/wcmatch.md']
```

If we have a leading slash, the pattern will not perform a match on the basename, but will instead be a normal path
pattern that is anchored to the current base path, in this case `.`.

```pycon3
>>> wcmatch.WcMatch('.', '/*.md', flags=wcmatch.FILEPATHNAME | wcmatch.GLOBSTAR | wcmatch.MATCHBASE | wcmatch.RECURSIVE).match()
['./LICENSE.md', './README.md']
```

#### `wcmatch.GLOBSTAR, wcmatch.G` {: #globstar}

When the [`PATHNAME`](#pathname) flag is provided, you can also enable `GLOBSTAR` to enable the recursive
directory pattern matches with `**`.

```pycon3
>>> from wcmatch import wcmatch
>>> wcmatch.WcMatch('.', '*.md|*.txt', '**/markdown', flags=wcmatch.DIRPATHNAME | wcmatch.GLOBSTAR | wcmatch.RECURSIVE).match()
['./LICENSE.md', './README.md', './requirements/docs.txt', './requirements/lint.txt', './requirements/setup.txt', './requirements/test.txt']
```

--8<--
refs.txt
--8<--
