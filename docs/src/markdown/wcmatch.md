# wcmatch.wcmatch

```py3
from wcmatch import wcmatch
```

## Overview

`wcmatch.WcMatch` was originally written to provide a simple user interface for searching specific files in [Rummage](https://github.com/facelessuser/Rummage). A class was needed to facilitate a user interface where a user could select a base path, define one or more file patterns they wanted to search for, and provide folders to exclude if needed. It needed to be aware of hidden files on different systems, not just ignoring files that start with `.`. It also needed to be extendable so we could further filter returned files by size, creation date, or whatever else was decided. While `glob` is a fantastic file and folder search tool, it just didn't make sense for such a user interface.

## wcmatch.WcMatch

`WcMatch` is an extendable file search class. It allows you to specify a base path, file patterns, and optional folder exclude patterns. You can specify whether you want to see hidden files and whether the search should be recursive. You can also derive from the class and tap into specific hooks to change what is returned or done when a file is matched, skipped, or when there is an error. There are also hooks where you can inject additional, custom filtering.

Parameter         | Default       | Description
----------------- | ------------- | -----------
`directory`       |               | The base directory to search.
`file_pattern`    | `#!py3 '*'`   | One or more patterns separated by `|`. You can define exceptions by starting a pattern with `!` (or `-` if [`MINUSNEGATE`](#wcmatchminusnegate) is set).
`exclude_pattern` | `#!py3 ''`    | Zero or more folder exclude patterns separated by `|`. You can define exceptions by starting a pattern with `!` (or `-` if [`MINUSNEGATE`](#wcmatchminusnegate) is set).
`recursive`       | `#!py3 False` | Whether search should be recursive.
`show_hidden`     | `#!py3 False` | Whether hidden files should be shown.
`flags`           | `#!py3 0`     | Flags to alter behavior of folder and file matching. See [Flags](#flags) for more info.

!!! note
    Dots are not treated special. When `show_hidden` is disabled, dot files won't show up anyways, so it is expected that if `show_hidden` is enabled, that `*`, `?`, `[]`, etc. should match `.`.

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
>>> wcmatch.WcMatch('.', '*.md|*.txt', recursive=True).match()
['./LICENSE.md', './README.md', './docs/src/markdown/changelog.md', './docs/src/markdown/fnmatch.md', './docs/src/markdown/glob.md', './docs/src/markdown/index.md', './docs/src/markdown/installation.md', './docs/src/markdown/license.md', './docs/src/markdown/wcmatch.md', './docs/src/markdown/_snippets/abbr.md', './docs/src/markdown/_snippets/links.md', './docs/src/markdown/_snippets/refs.md', './requirements/docs.txt', './requirements/lint.txt', './requirements/setup.txt', './requirements/test.txt']
```

Excluding directories:

```pycon3
>>> from wcmatch import wcmatch
>>> wcmatch.WcMatch('.', '*.md|*.txt', 'docs', recursive=True).match()
['./LICENSE.md', './README.md', './requirements/docs.txt', './requirements/lint.txt', './requirements/setup.txt', './requirements/test.txt']
```

Using file negation patterns:

```pycon3
>>> from wcmatch import wcmatch
>>> wcmatch.WcMatch('.', '*.md|*.txt|!README*', 'docs', recursive=True).match()
['./LICENSE.md', './requirements/docs.txt', './requirements/lint.txt', './requirements/setup.txt', './requirements/test.txt']
```

You can also use negation patterns in directory exclude. Here we avoid all folders with `*`, but add an exception for `requirements`. It should be noted that you cannot add an exception for the child of an excluded folder.

```pycon3
>>> from wcmatch import wcmatch
>>> wcmatch.WcMatch('.', '*.md|*.txt', '*|!requirements', recursive=True).match()
['./LICENSE.md', './README.md', './requirements/docs.txt', './requirements/lint.txt', './requirements/setup.txt', './requirements/test.txt']
```

Negative patterns can be given by themselves.

```pycon3
>>> from wcmatch import wcmatch
>>> wcmatch.WcMatch('.', '*.md|*.txt', '!requirements', recursive=True).match()
['./LICENSE.md', './README.md', './requirements/docs.txt', './requirements/lint.txt', './requirements/setup.txt', './requirements/test.txt']
```

Enabling hidden files:

```pycon3
>>> from wcmatch import wcmatch
>>> wcmatch.WcMatch('.', '*.yml').match()
['./appveyor.yml', './mkdocs.yml']
>>> wcmatch.WcMatch('.', '*.yml', show_hidden=True).match()
['./.codecov.yml', './.travis.yml', './appveyor.yml', './mkdocs.yml']
```

## Methods

#### WcMatch.match

Perform match returning files that match the patterns.

```pycon3
>>> from wcmatch import wcmatch
>>> wcmatch.WcMatch('.', '*.md|*.txt').match()
['./LICENSE.md', './README.md']
```

#### WcMatch.imatch

Perform match returning an iterator of files that match the patterns.

```pycon3
>>> from wcmatch import wcmatch
>>> list(wcmatch.WcMatch('.', '*.md|*.txt').imatch())
['./LICENSE.md', './README.md']
```

#### WcMatch.kill

If searching with `imatch`, this provides a way to kill the internal searching.

```pycon3
>>> from wcmatch import wcmatch
>>> wcm = wcmatch.WcMatch('.', '*.md|*.txt')
>>> for f in wcm.imatch():
...     print(f)
...     wcm.kill()
...
./LICENSE.md
```

#### WcMatch.reset

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

#### WcMatch.get_skipped

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

#### WcMatch.on_init

```py3
   def on_init(self, *args, **kwargs):
        """Handle custom init."""
```

Any arguments or keyword arguments not processed by the main initializer are sent to `on_init`. This allows you to specify additional arguments when deriving from `WcMatch`.

#### WcMatch.on_validate_directory

```py3
    def on_validate_directory(self, base, name):
        """Validate folder override."""

        return True
```

When validating a directory, if the directory passes validation, it will be sent to `on_validate_directory` which can be overridden to provide additional validation if required.

#### WcMatch.on_validate_file

```py3
    def on_validate_file(self, base, name):
        """Validate file override."""

        return True
```

When validating a file, if the file passes validation, it will be sent to `on_validate_file` which can be overridden to provide additional validation if required.

#### WcMatch.on_skip

```py3
    def on_skip(self, base, name):
        """On skip."""

        return None
```

When a file that must be skipped is encountered (a file that doesn't pass validation), it is sent to `on_skip`. Here you could abort the search, store away information, or even create a special skip record to return. It is advised to create a special type for skip returns so that you can identify them when they are returned via `match` or `imatch`.

#### WcMatch.on_error

```py3
    def on_error(self, base, name):
        """On error."""

        return None
```

When accessing or processing a file throws an error, it is sent to `on_error`. Here you could abort the search, store away information, or even create a special error record to return. It is advised to create a special type for error returns so that you can identify them when they are returned via `match` or `imatch`.

#### WcMatch.on_match

```py3
    def on_match(self, base, name):
        """On match."""

        return os.path.join(base, name)
```

On match returns the path of the matched file.  You can override `on_match` and change what is returned.  You could return just the base, you could parse the file and return the content, or return a special match record with additional file meta data. `on_match` must return something, and all results will be returned via `match` or `imatch`.

## Flags

#### wcmatch.FORCECASE

`FORCECASE` forces cased searches. `FORCECASE` has higher priority than [`IGNORECASE`](#wcmatchignorecase). This does **not** affect path normalization. All paths are normalized for the host as it is required to properly access the file system.

#### wcmatch.IGNORECASE

`IGNORECASE` forces case insensitive searches. `FORCECASE` has higher priority than [`IGNORECASE`](#wcmatchignorecase).

#### wcmatch.RAWCHARS

`RAWCHARS` causes string character syntax to be parsed in raw strings: `#!py3 r'\u0040'` --> `#!py3 r'@'`. This will handled standard string escapes and Unicode (including `#!py3 r'\N{CHAR NAME}'`).

#### wcmatch.EXTGLOB

`EXTMATCH` enables extended pattern matching which includes special pattern lists such as `+(...)`, `*(...)`, `?(...)`, etc.

#### wcmatch.BRACE

`BRACE` enables Bash style brace expansion: `a{b,{c,d}}` --> `ab ac ad`. Brace expansion is applied before anything else. When applied, a pattern will be expanded into multiple patterns. Each pattern will then be parsed separately.

For simple patterns, it may make more sense to use [`EXTMATCH`](#fnmatchextmatch) which will only generate a single pattern: `@(ab|ac|ad)`.

Be careful with patterns such as `{1..100}` which would generate one hundred patterns that will all get individually parsed. Sometimes you really need such a pattern, but be mindful that it will be slower as you generate larger sets of patterns.

#### wcmatch.MINUSNEGATE

`MINUSNEGATE` requires negation patterns to use `-` instead of `!`.

#### wcmatch.DIRPATHNAME

`DIRPATHNAME` will enable path name searching for excluded folder patterns, but it will not apply to file patterns. This is mainly provided for cases where you may have multiple folders with the same name, but you want to target a specific folder to exclude. The path name compared will be the entire path relative to the base path.  So if the provided base folder was `.`, and the folder under evaluation is `./some/folder`, `some/folder` will be matched against the pattern.

```pycon3
>>> from wcmatch import wcmatch
>>> wcmatch.WcMatch('.', '*.md|*.txt', 'docs/src/markdown', recursive=True, flags=wcmatch.DIRPATHNAME).match()
['./LICENSE.md', './README.md', './requirements/docs.txt', './requirements/lint.txt', './requirements/setup.txt', './requirements/test.txt']
```

#### wcmatch.FILEPATHNAME

`FILEPATHNAME` will enable path name searching for the file patterns, but it will not apply to directory exclude patterns. The path name compared will be the entire path relative to the base path.  So if the provided base folder was `.`, and the file under evaluation is `./some/file.txt`, `some/file.txt` will be matched against the pattern.

```pycon3
>>> from wcmatch import wcmatch
>>> wcmatch.WcMatch('.', '**/*.md|!**/_snippets/*', recursive=True, flags=wcmatch.FILEPATHNAME | wcmatch.GLOBSTAR).match()
['./LICENSE.md', './README.md', './docs/src/markdown/changelog.md', './docs/src/markdown/fnmatch.md', './docs/src/markdown/glob.md', './docs/src/markdown/index.md', './docs/src/markdown/license.md', './docs/src/markdown/wcmatch.md']
```

#### wcmatch.PATHNAME

`PATHNAME` enables both [`DIRPATHNAME`](#wcmatchdirpathname) and [`FILEPATHNAME`](#wcmathfilepathname). It is provided for convenience.

#### wcmatch.GLOBSTAR

When the [`PATHNAME`](#wcmatchpathname) flag is provided, you can also enable `GLOBSTAR` to enable the recursive directory pattern matches wth `**`.

```pycon3
>>> from wcmatch import wcmatch
>>> wcmatch.WcMatch('.', '*.md|*.txt', '**/markdown', recursive=True, flags=wcmatch.DIRPATHNAME | wcmatch.GLOBSTAR).match()
['./LICENSE.md', './README.md', './requirements/docs.txt', './requirements/lint.txt', './requirements/setup.txt', './requirements/test.txt']
```

--8<--
refs.md
--8<--
