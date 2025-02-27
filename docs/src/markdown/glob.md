# `wcmatch.glob`

```py
from wcmatch import glob
```

## Syntax

The `glob` library provides methods for traversing the file system and returning files that matched a defined set of
glob patterns.  The library also provides a function called [`globmatch`](#globmatch) for matching file paths which
is similar to [`fnmatch`](./fnmatch.md#fnmatch), but for paths. In short, [`globmatch`](#globmatch) matches
what [`glob`](#glob) globs :slight_smile:.

/// tip
When using backslashes, it is helpful to use raw strings. In a raw string, a single backslash is used to escape a
character `#!py r'\?'`.  If you want to represent a literal backslash, you must use two: `#!py r'some\\path'`.
///  

Pattern           | Meaning
----------------- | -------
`*`               | Matches everything except slashes.  On Windows it will avoid matching backslashes as well as slashes.
`**`              | Matches zero or more directories, but will never match the directories ` . ` and `..`. Requires the [`GLOBSTAR`](#globstar) flag.
`***`             | Like `**` but will also recurse symlinks. Requires the [`GLOBSTARLONG`](#globstarlong) flag.
`?`               | Matches any single character.
`[seq]`           | Matches any character in seq.
`[!seq]`          | Matches any character not in seq. Will also accept character exclusions in the form of `[^seq]`.
`[[:alnum:]]`     | POSIX style character classes inside sequences. See [POSIX Character Classes](#posix-character-classes) for more info.
`\`               | Escapes characters. If applied to a meta character or non-meta characters, the character will be treated as a literal character. If applied to another escape, the backslash will be a literal backslash.
`!`               | When used at the start of a pattern, the pattern will be an exclusion pattern. Requires the [`NEGATE`](#negate) flag. If also using the [`MINUSNEGATE`](#minusnegate) flag, `-` will be used instead of `!`.
`?(pattern_list)` | The pattern matches if zero or one occurrences of any of the patterns in the `pattern_list` match the input string. Requires the [`EXTGLOB`](#extglob) flag.
`*(pattern_list)` | The pattern matches if zero or more occurrences of any of the patterns in the `pattern_list` match the input string. Requires the [`EXTGLOB`](#extglob) flag.
`+(pattern_list)` | The pattern matches if one or more occurrences of any of the patterns in the `pattern_list` match the input string. Requires the [`EXTGLOB`](#extglob) flag.
`@(pattern_list)` | The pattern matches if exactly one occurrence of any of the patterns in the `pattern_list` match the input string. Requires the [`EXTGLOB`](#extglob) flag.
`!(pattern_list)` | The pattern matches if the input string cannot be matched with any of the patterns in the `pattern_list`. Requires the [`EXTGLOB`](#extglob) flag.
`{}`              | Bash style brace expansions.  This is applied to patterns before anything else. Requires the [`BRACE`](#brace) flag.
`~/pattern`       | User path expansion via `~/pattern` or `~user/pattern`. Requires the [`GLOBTILDE`](#globtilde) flag.

-   Slashes are generally treated special in glob related methods. Slashes are not matched in `[]`, `*`, `?`, or extended
    patterns like `*(...)`. Slashes can be matched by `**` if [`GLOBSTAR`](#globstar) is set.

-   Slashes on Windows are normalized. `/` will match both `/` and `\\`. There is no need to explicitly use `\\` in
    patterns on Windows, but if you do, they must be escaped to specify a literal `\\`. If a backslash is escaped, it will
    match all valid windows separators, just like `/` does.

-   On Windows, drives are treated special and must come at the beginning of the pattern and cannot be matched with `*`,
    `[]`, `?`, or even extended match patterns like `+(...)`.

-   Windows drives are recognized as either `C:/` and `//Server/mount/`. If a path uses an ambiguous root (`/some/path`),
    the system will assume the drive of the current working directory.

-   Meta characters have no effect when inside a UNC path: `//Server?/mount*/`. The one exception is pattern expansion
    characters like `{}` which are used by [brace expansion](#brace) and `|` used by [pattern splitting](#split).
    Pattern expansion characters are the only characters that can be escaped in a Windows drive/mount.

-   If [`FORCEUNIX`](#forceunix) is applied on a Windows system, match and filter commands that do not touch the file
    system will **not** have slashes normalized. In addition, drive letters will also not be handled. Essentially, paths
    will be treated as if on a Linux/Unix system. Commands that do touch the file system ([`glob`](#glob) and
    [`iglob`](#iglob)) will ignore [`FORCEUNIX`](#forceunix) and [`FORCEWIN`](#forcewin).
    [`globmatch`](#globmatch) and [`globfilter`](#globfilter), will also ignore [`FORCEUNIX`](#forceunix) and
    [`FORCEWIN`](#forcewin) if the [`REALPATH`](#realpath) flag is enabled.

    [`FORCEWIN`](#forcewin) will do the opposite on a Linux/Unix system, and will force Windows logic on a
    Linux/Unix system. Like with [`FORCEUNIX`](#forceunix), it only applies to commands that don't touch the file
    system.

-   By default, file and directory names starting with `.` are only matched with literal `.`.  The patterns `*`, `**`,
    `?`, and `[]` will not match a leading `.`.  To alter this behavior, you can use the [`DOTGLOB`](#dotglob) flag.

-   [`NEGATE`](#negate) will always enable [`DOTGLOB`](#dotglob) in exclude patterns.

-   Even with [`DOTGLOB`](#dotglob) enabled, special tokens will not match a special directory (`.` or `..`).  But
    when a literal `.` is used at the start of the pattern (`.*`, `.`, `..`, etc.), `.` and `..` can potentially be
    matched.

-   In general, Wildcard Match's behavior is modeled off of Bash's, and prior to version 7.0, unlike Python's default
    [`glob`][glob], Wildcard Match's [`glob`](#glob) would match and return `.` and `..` for magic patterns like `.*`.
    This is because our directory scanning logic inserts `.` and `..` into results to be faithful to Bash. While this
    emulates Bash's behavior, it can be surprising to the user, especially if they are used to Python's default glob. In
    7.0 we now avoid returning `.` and `..` in our directory scanner. This does not affect how patterns are matched, just
    what is returned via our directory scan logic. You can once again enable the old Bash-like behavior with the flag
    [`SCANDOTDIR`](#scandotdir) if this old behavior is desired.

    Python's default:

    ```pycon3
    >>> import glob
    >>> glob.glob('docs/.*')
    []
    ```

    Wildcard Match:

    ```pycon3
    >>> from wcmatch import glob
    >>> glob.glob('docs/.*')
    []
    ```

    Bash:

    ```shell-session
    $ echo docs/.*
    docs/. docs/..
    ```

    Bash-like behavior restored in Wildcard Match [`SCANDOTDIR`](#scandotdir):

    ```pycon3
    >>> from wcmatch import glob
    >>> glob.glob('docs/.*', flags=glob.SCANDOTDIR)
    ['docs/.', 'docs/..']
    ```

    It is important to stress that this logic only relates to directory scanning and does not fundamentally alter glob
    patterns.  We can still match a path of `..` with `.*` when strictly doing a match:

    ```pycon3
    >>> from wcmatch import glob
    >>> glob.globmatch('..', '.*')
    True
    ```

    Nor does it affect exclude results as they are used to filter the results after directory scanning:

    ```pycon3
    >>> from wcmatch import glob
    >>> glob.glob('..')
    ['..']
    >>> glob.glob(['..', '!.*'], flags=glob.NEGATE)
    []
    ```

    If we wish to fundamentally alter the pattern matching behavior, we can use [`NODOTDIR`](#nodotdir). This would
    provide a more Zsh feel.

    ```pycon3
    >>> from wcmatch import glob
    >>> glob.glob(['..', '!.*'], flags=glob.NEGATE | glob.NODOTDIR)
    ['..']
    >>> glob.glob(['..', '!..'], flags=glob.NEGATE | glob.NODOTDIR)
    []
    >>> glob.globmatch('..', '.*', flags=glob.NODOTDIR)
    False
    ```

    /// new | Changes 7.0
    Prior to 7.0 `.` and `..` would get returned by our directory scanner. This is no longer the default.
    ///

    /// new | New 7.0
    Legacy behavior of directory scanning, in relation to `.` and `..`, can be restored via [`SCANDOTDIR`](#scandotdir).

    [`NODOTDIR`](#nodotdir) was added in 7.0.
    ///

--8<-- "posix.md"

## Windows Separators

On Windows, it is not required to use backslashes for path separators as `/` will match path separators for all systems.
The following will work on Windows and Linux/Unix systems.

```python
glob.glob('docs/.*')
```

With that said, you can match Windows separators with backslashes as well. Keep in mind that Wildcard Match allows
escaped characters in patterns, so to match a literal backslash separator, you must escape the backslash. It is advised
to use raw strings when using backslashes to make the patterns more readable, but either of the below will work.

```python
glob.glob(r'docs\\.*')
glob.glob('docs\\\\.*')
```

## Multi-Pattern Limits

Many of the API functions allow passing in multiple patterns or using either [`BRACE`](#brace) or
[`SPLIT`](#split) to expand a pattern in to more patterns. The number of allowed patterns is limited `1000`, but you
can raise or lower this limit via the keyword option `limit`. If you set `limit` to `0`, there will be
no limit.

/// new | New 6.0
The imposed pattern limit and corresponding `limit` option was introduced in 6.0.
///

## Precompiling

While patterns are often cached, auto expanding patterns, such as `'file{a, b, c}'` will have each individual
permutation cached (up to the cache limit), but not the entire pattern. This is to prevent the cache from exploding with
really large patterns such as `{1..100}`. Essentially, individual patterns are cached, but not the expansion of a
pattern into many patterns.

If it is planned to reuse a pattern and the performance hit of recompiling is not desired, you can precompile a matcher
object via [`glob.compile`](#compile) which returns a [`WcMatcher`](#wcmatcher) object.

```py
>>> import wcmatch.glob as glob
>>> m = glob.compile('**/*.py', flags=glob.GLOBSTAR)
>>> m.match('wcmatch/__init__.py')
True
>>> m.filter(['wcmatch/__init__.py', 'wcmatch/glob.py', 'README.md'])
['wcmatch/__init__.py', 'wcmatch/glob.py']
```

## API

#### `glob.glob` {: #glob}

```py
def glob(patterns, *, flags=0, root_dir=None, dir_fd=None, limit=1000, exclude=None):
```

`glob` takes a pattern (or list of patterns), flags, and an optional root directory (string or path-like object) and/or
directory file descriptor. It also allows configuring the [max pattern limit](#multi-pattern-limits). Exclusion patterns
can be specified via the `exclude` parameter which takes a pattern or a list of patterns.When executed it will crawl the
file system returning matching files.

/// warning | Path-like Input Support
Path-like object input support is only available in Python 3.6+ as the path-like protocol was added in Python 3.6.
///

```pycon3
>>> from wcmatch import glob
>>> glob.glob('**/*.md')
['docs/src/markdown/_snippets/abbr.md', 'docs/src/markdown/_snippets/links.md', 'docs/src/markdown/_snippets/refs.md', 'docs/src/markdown/changelog.md', 'docs/src/markdown/fnmatch.md', 'docs/src/markdown/glob.md', 'docs/src/markdown/index.md', 'docs/src/markdown/installation.md', 'docs/src/markdown/license.md', 'README.md']
```

Using a list, we can add exclusion patterns and also exclude directories and/or files:

```pycon3
>>> from wcmatch import glob
>>> glob.glob(['**/*.md', '!README.md', '!**/_snippets'], flags=glob.NEGATE)
['docs/src/markdown/changelog.md', 'docs/src/markdown/fnmatch.md', 'docs/src/markdown/glob.md', 'docs/src/markdown/index.md', 'docs/src/markdown/installation.md', 'docs/src/markdown/license.md']
```

When a glob pattern ends with a slash, it will only return directories:

```pycon3
>>> from wcmatch import glob
>>> glob.glob('**/')
['__pycache__/', 'docs/', 'docs/src/', 'docs/src/markdown/', 'docs/src/markdown/_snippets/', 'docs/theme/', 'requirements/', 'stuff/', 'tests/', 'tests/__pycache__/', 'wcmatch/', 'wcmatch/__pycache__/']
```

When providing a list, all patterns are run in the same context, but will not be run in the same pass. Each pattern is
run in a separate pass, except for exclusion patterns (see the [`NEGATE`](#negate) flag) which are applied as
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

If we wanted to completely match Bash's results, we would turn off unique results with the [`NOUNIQUE`](#nounique)
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

Features like [`BRACE`](#brace) and [`SPLIT`](#split) actually take a single string and breaks them up into
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

You can resolve user paths with `~` if the [`GLOBTILDE`](#globtilde) flag is enabled. You can also target specific
users with `~user`.

```pycon3
>>> from wcmatch import glob
>>> glob.glob('~', flags=glob.GLOBTILDE)
['/home/facelessuser']
>>> glob.glob('~root', flags=glob.GLOBTILDE)
['/root']
```

By default, `glob` uses the current working directory to evaluate relative patterns. Normally you'd have to use
`#!py os.chdir('/new/path')` to evaluate patterns relative to a different path. By setting `root_dir` parameter you can
change the root path without using `os.chdir`.

```pycon3
>>> from wcmatch import glob
>>> glob.glob('*')
['appveyor.yml', 'docs', 'LICENSE.md', 'MANIFEST.in', 'mkdocs.yml', 'README.md', 'requirements', 'setup.cfg', 'setup.py', 'tests', 'tox.ini', 'wcmatch']
>>> glob.glob('*', root_dir='docs/src')
['dictionary', 'markdown']
```

Additionally, you can use `dir_fd` and specify a root directory with a directory file descriptor.

```pycon3
>>> import os
>>> from wcmatch import glob
>>> dir_fd = os.open('docs/src', os.O_RDONLY | os.O_DIRECTORY)
>>> glob.glob('*', dir_fd=dir_fd)
['markdown', 'dictionary']
```

/// warning | Support for Directory Descriptors
Directory descriptors may not be supported on all systems. You can check whether or not `dir_fd` is supported for a
your platform referencing the attribute `#!py glob.SUPPORT_DIR_FD` which will be `#!py True` if it is supported.

Additionally, the `#!py os.O_DIRECTORY` may not be defined on some systems. You can likely just use
`#!py os.O_RDONLY`.
///

/// new | New 5.1
`root_dir` was added in 5.1.0.
///

/// new | New 6.0
`limit` was added in 6.0.
///

/// new | New 8.2
`dir_fd` parameter was added in 8.2.
///

/// new | New 8.4
`exclude` parameter was added.
///

#### `glob.iglob` {: #iglob}

```py
def iglob(patterns, *, flags=0, root_dir=None, dir_fd=None, limit=1000, exclude=None):
```

`iglob` is just like [`glob`](#glob) except it returns an iterator.

```pycon3
>>> from wcmatch import glob
>>> list(glob.iglob('**/*.md'))
['docs/src/markdown/_snippets/abbr.md', 'docs/src/markdown/_snippets/links.md', 'docs/src/markdown/_snippets/refs.md', 'docs/src/markdown/changelog.md', 'docs/src/markdown/fnmatch.md', 'docs/src/markdown/glob.md', 'docs/src/markdown/index.md', 'docs/src/markdown/installation.md', 'docs/src/markdown/license.md', 'README.md']
```

/// new | New 5.1
`root_dir` was added in 5.1.0.
///

/// new | New 6.0
`limit` was added in 6.0.
///

/// new | New 8.2
`dir_fd` parameter was added in 8.2.
///

/// new | New 8.4
`exclude` parameter was added.
///

#### `glob.globmatch` {: #globmatch}

```py
def globmatch(filename, patterns, *, flags=0, root_dir=None, dir_fd=None, limit=1000, exclude=None):
```

`globmatch` takes a file name (string or path-like object), a pattern (or list of patterns), flags, and an optional root
directory and/or file descriptor.  It also allows configuring the [max pattern limit](#multi-pattern-limits). Exclusion
patterns can be specified via the `exclude` parameter which takes a pattern or a list of patterns. It will return a
boolean indicating whether the file path was matched by the pattern(s).

```pycon3
>>> from wcmatch import glob
>>> glob.globmatch('some/path/test.txt', '**/*/@(*.txt|*.py)', flags=glob.EXTGLOB)
True
```

When applying multiple patterns, a file path matches if it matches any of the patterns:

```pycon3
>>> from wcmatch import glob
>>> glob.globmatch('some/path/test.txt', ['**/*/*.txt', '**/*/*.py'])
True
```

Exclusion patterns are allowed as well. When exclusion patterns are used in conjunction with other patterns, a path will
be considered matched if one of the positive patterns match **and** none of the exclusion patterns match. If an
exclusion pattern is given without any inclusion patterns, the pattern will match nothing. Exclusion patterns are meant
to filter other patterns, not match anything by themselves.

```pycon3
>>> from wcmatch import glob
>>> glob.globmatch('some/path/test.py', '**|!**/*.txt', flags=glob.NEGATE | glob.GLOBSTAR | glob.SPLIT)
True
>>> glob.globmatch('some/path/test.txt', '**|!**/*.txt', flags=glob.NEGATE | glob.GLOBSTAR | glob.SPLIT)
False
>>> glob.globmatch('some/path/test.txt', ['*/*/*.txt', '!*/*/avoid.txt'], flags=glob.NEGATE)
True
>>> glob.globmatch('some/path/avoid.txt', ['*/*/*.txt', '!*/*/avoid.txt'], flags=glob.NEGATE)
False
```

As mentioned, exclusion patterns need to be applied to a inclusion pattern to work, but if it is desired, you can force
exclusion patterns to assume all files should be filtered with the exclusion pattern(s) with the
[`NEGATEALL`](#negateall) flag. Essentially, it means if you use a pattern such as `!*.md`, it means if you use a
pattern such as `!*.md`, it will assume two pattern were given: `*` and `!*.md` (where `**` is specifically treated as
if [`GLOBSTAR`](#globstar) was enabled).

```pycon3
>>> from wcmatch import glob
>>> glob.globmatch('some/path/test.py', '!**/*.txt', flags=glob.NEGATE | glob.GLOBSTAR | glob.NEGATEALL)
True
>>> glob.globmatch('some/path/test.txt', '!**/*.txt', flags=glob.NEGATE | glob.GLOBSTAR | glob.NEGATEALL)
False
```

By default, `globmatch` and [`globfilter`](#globfilter) do not operate on the file system. This is to allow you to
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

If you would like for `globmatch` (or [`globfilter`](#globfilter)) to operate on your current filesystem directly,
simply pass in the [`REALPATH`](#realpath) flag. When enabled, the path under consideration will be analyzed and
will use that context to determine if the file exists, if it is a directory, does it's context make sense compared to
what the pattern is looking vs the current working directory, or if it has symlinks that should not be traversed by
[`GLOBSTAR`](#globstar).

Here we use [`REALPATH`](#realpath) and can see that `globmatch` now knows that `doc` is a directory.

```pycon3
>>> from wcmatch import glob
>>> glob.globmatch('docs', '*/', flags=glob.REALPATH)
True
```

It also can tell if a file doesn't exist or is out of scope compared to what is being asked. For instance, the below
example fails because the pattern is looking for any folder that is relative to the current path, which `/usr` is not.
When we disable [`REALPATH`](#realpath), it will match just fine. Both cases can be useful depending on how you plan
to use `globmatch`.

```pycon3
>>> from wcmatch import glob
>>> glob.globmatch('/usr', '**/', flags=glob.G | glob.REALPATH)
False
>>> glob.globmatch('/usr', '**/', flags=glob.G)
True
```

If you are using [`REALPATH`](#realpath) and want to evaluate the paths relative to a different directory, you can
set the `root_dir` parameter.

```pycon3
>>> from wcmatch import glob
>>> glob.globmatch('markdown', 'markdown', flags=glob.REALPATH)
False
>>> glob.globmatch('markdown', 'markdown', flags=glob.REALPATH, root_dir='docs/src')
True
```

Additionally, you could also provide a root directory using a file descriptor.

```pycon3
>>> import os
>>> from wcmatch import glob
>>> dir_fd = os.open('docs/src', os.O_RDONLY | os.O_DIRECTORY)
>>> glob.globmatch('markdown', 'markdown', flags=glob.REALPATH)
False
>>> glob.globmatch('markdown', 'markdown', flags=glob.REALPATH, dir_fd=dir_fd)
True
```

/// warning | Support for Directory Descriptors
Directory descriptors may not be supported on all systems. You can check whether or not `dir_fd` is supported for a
your platform referencing the attribute `#!py glob.SUPPORT_DIR_FD` which will be `#!py True` if it is supported.

Additionally, the `#!py os.O_DIRECTORY` may not be defined on some systems. You can likely just use
`#!py os.O_RDONLY`.
///

/// new | New 5.1
-   `root_dir` was added in 5.1.0.
-   path-like object support for file path inputs was added in 5.1.0
///

/// new | New 6.0
`limit` was added in 6.0.
///

/// new | New 8.2
`dir_fd` parameter was added in 8.2.
///

/// new | New 8.4
`exclude` parameter was added.
///

#### `glob.globfilter` {: #globfilter}

```py
def globfilter(filenames, patterns, *, flags=0, root_dir=None, dir_fd=None, limit=1000, method=None):
```

`globfilter` takes a list of file paths (strings or path-like objects), a pattern (or list of patterns), flags, and an
optional root directory and/or directory file descriptor. It also allows configuring the 
[max pattern limit](#multi-pattern-limits). Exclusion patterns can be specified via the `exclude` parameter which takes
a pattern or a list of patterns.It returns a list of all files paths that matched the pattern(s). The same logic used
for [`globmatch`](#globmatch) is used for `globfilter`, albeit more efficient for processing multiple files.

/// warning | Path-like Input Support
Path-like object input support is only available in Python 3.6+ as the path-like protocol was added in Python 3.6.
///

```pycon3
>>> from wcmatch import glob
>>> glob.globfilter(['some/path/a.txt', 'b.txt', 'another/path/c.py'], '**/*.txt')
['some/path/a.txt', 'b.txt']
```

Like [`globmatch`](#globmatch), `globfilter` does not operate directly on the file system, with all the caveats
associated. But you can enable the [`REALPATH`](#realpath) flag and `globfilter` will use the filesystem to gain
context such as: whether the file exists, whether it is a directory or not, or whether it has symlinks that should not
be traversed by `GLOBSTAR`. See [`globmatch`](#globmatch) for examples.

/// new | New 5.1
-   `root_dir` was added in 5.1.0.
-   path-like object support for file path inputs was added in 5.1.0
///

/// new | New 6.0
`limit` was added in 6.0.
///

/// new | New 8.2
`dir_fd` parameter was added in 8.2.
///

/// new | New 8.4
`exclude` parameter was added.
///

#### `glob.translate` {: #translate}

```py
def translate(patterns, *, flags=0, limit=1000, exclude=None):
```

`translate` takes a file pattern (or list of patterns) and flags. It also allows configuring the [max pattern
limit](#multi-pattern-limits). Exclusion patterns can be specified via the `exclude` parameter which takes a pattern or
a list of patterns. It returns two lists: one for inclusion patterns and one for exclusion patterns. The lists contain
the regular expressions used for matching the given patterns. It should be noted that a file is considered matched if it
matches at least one inclusion pattern and matches **none** of the exclusion patterns.

```pycon3
>>> from wcmatch import glob
>>> glob.translate('**/*.{py,txt}')
(['^(?s:(?=[^/])(?!(?:\\.{1,2})(?:$|[/]))(?:(?!\\.)[^/]*?)?[/]+(?=[^/])(?!(?:\\.{1,2})(?:$|[/]))(?:(?!\\.)[^/]*?)?\\.\\{py,txt\\}[/]*?)$'], [])
>>> glob.translate('**|!**/*.{py,txt}', flags=glob.NEGATE | glob.SPLIT)
(['^(?s:(?=[^/])(?!(?:\\.{1,2})(?:$|[/]))(?:(?!\\.)[^/]*?)?[/]*?)$'], ['^(?s:(?=[^/])(?!(?:\\.{1,2})(?:$|[/]))[^/]*?[/]+(?=[^/])(?!(?:\\.{1,2})(?:$|[/]))[^/]*?\\.\\{py,txt\\}[/]*?)$'])
```

When using [`EXTGLOB`](#extglob) patterns, patterns will be returned with capturing groups around the groups:

While in regex patterns like `#!py r'(a)+'` would capture only the last character, even though multiple where matched,
we wrap the entire group to be captured: `#!py '+(a)'` --> `#!py r'((a)+)'`.

```pycon3
>>> from wcmatch import glob
>>> import re
>>> gpat = glob.translate("@(file)+([[:digit:]])@(.*)", flags=glob.EXTGLOB)
>>> pat = re.compile(gpat[0][0])
>>> pat.match('file33.test.txt').groups()
('file', '33', '.test.txt')
```

/// new | New 6.0
`limit` was added in 6.0.
///

/// new | New 7.1
Translate patterns now provide capturing groups for [`EXTGLOB`](#extglob) groups.
///

/// new | New 8.4
`exclude` parameter was added.
///

#### `glob.compile` {: #compile}

```py
def compile(patterns, *, flags=0, limit=1000, exclude=None):
```

The `compile` function takes a file pattern (or list of patterns) and flags. It also allows configuring the [max pattern
limit](#multi-pattern-limits). Exclusion patterns can be specified via the `exclude` parameter which takes a pattern or
a list of patterns. It returns a [`WcMatcher`](#wcmatcher) object which can match or filter file paths depending on
which method is called. 

```pycon3
>>> import wcmatch.glob as glob
>>> m = glob.compile('**/*.py', flags=glob.GLOBSTAR)
>>> m.match('wcmatch/__init__.py')
True
>>> m.filter(['wcmatch/__init__.py', 'wcmatch/glob.py', 'README.md'])
['wcmatch/__init__.py', 'wcmatch/glob.py']
```

#### `glob.WcMatcher` {: #wcmatcher}

The `WcMatcher` class is returned when a pattern is precompiled with [`compile`](#compile). It has two methods: `match`
and `filter`.

```py
def match(self, filename, *, root_dir=None, dir_fd=None):
```

This `match` method allows for matching against a precompiled pattern.

```pycon3
>>> import wcmatch.glob as glob
>>> m = glob.compile('**/*.py', flags=glob.GLOBSTAR)
>>> m.match('wcmatch/__init__.py')
True
```

```py
def filter(self, filenames, *, root_dir=None, dir_fd=None):
```

The `filter` method allows for filtering paths against a precompiled pattern.

```pycon3
>>> import wcmatch.glob as glob
>>> m = glob.compile('**/*.py', flags=glob.GLOBSTAR)
>>> m.filter(['wcmatch/__init__.py', 'wcmatch/glob.py', 'README.md'])
['wcmatch/__init__.py', 'wcmatch/glob.py']
```

#### `glob.escape` {: #escape}

```py
def escape(pattern, unix=None):
```

The `escape` function will conservatively escape `-`, `!`, `*`, `?`, `(`, `)`, `[`, `]`, `|`, `{`, `}`, and `\` with
backslashes, regardless of what feature is or is not enabled. It is meant to escape path parts (filenames, Windows
drives, UNC sharepoints) or full paths.

```pycon3
>>> from wcmatch import glob
>>> glob.escape('some/path?/**file**{}.txt')
'some/path\\?/\\*\\*file\\*\\*\\{}.txt'
>>> glob.globmatch('some/path?/**file**{}.txt', glob.escape('some/path?/**file**{}.txt'))
True
```

`escape` can also handle Windows style paths with `/` or `\` path separators. It is usually recommended to use `/` as
Windows backslashes are only supported via a special escape, but `\` will be expanded to an escaped backslash
(represented in a raw string as `#!py r'\\'` or a normal string as `#!py '\\\\'`).

```pycon3
>>> from wmcatch import glob
>>> glob.escape('some\\path?\\**file**{}.txt', unix=False)
'some\\\\path\\?\\\\\\*\\*file\\*\\*\\{\\}.txt'
>>> glob.globmatch('some\\path?\\**file**{}.txt', glob.escape('some\\path?\\**file**{}.txt'), flags=glob.FORCEWIN)
True
>>> glob.escape('some/path?/**file**{}.txt', unix=False)
'some/path\\?/\\*\\*file\\*\\*\\{\\}.txt'
>>> glob.globmatch('some\\path?\\**file**{}.txt', glob.escape('some/path?/**file**{}.txt'), flags=glob.FORCEWIN)
True
```

On a Windows system, meta characters are not processed in drives or UNC sharepoints except for pattern expansion meta
characters. `{` and `}` (when using [`BRACE`](#brace)) and `|` (when using [`SPLIT`](#split)) are the only meta
characters that can affect drives and UNC sharepoints; therefore, they are the only characters that need to be escaped.
`escape`, when it detects or is informed that it is processing a Windows path, `escape` will properly find and handle
drives and UNC sharepoints.

```pycon3
>>> from wmcatch import glob
>>> glob.escape('//./Volume{b75e2c83-0000-0000-0000-602f00000000}\Test\Foo.txt', unix=False)
'//./Volume\\{b75e2c83-0000-0000-0000-602f00000000\\}\\\\Test\\\\Foo.txt'
```

`escape` will detect the system it is running on and pick Windows escape logic or Linux/Unix logic. Since
[`globmatch`](#globmatch) allows you to match Unix style paths on a Windows system and vice versa, you can force
Unix style escaping or Windows style escaping via the `unix` parameter. When `unix` is `None`, the escape style will be
detected, when `unix` is `True` Linux/Unix style escaping will be used, and when `unix` is `False` Windows style
escaping will be used.

```pycon3
>>> glob.escape('some/path?/**file**{}.txt', unix=True)
```

/// new | New 5.0
The `unix` parameter is now `None` by default. Set to `True` to force Linux/Unix style escaping or set to `False` to
force Windows style escaping.
///

/// new | New 7.0
`{`, `}`, and `|` will be escaped in Windows drives. Additionally, users can escape these characters in Windows
drives manually in their match patterns as well.
///

### `glob.is_magic` {: #is_magic}

```py
def is_magic(pattern, *, flags=0):
    """Check if the pattern is likely to be magic."""
```

This checks a given path or `pattern` or to see if "magic" symbols are present or not. The check is based on the enabled
features via `flags`. Paths and patterns are expected to be/target full paths, full filenames, full drive names, or full
UNC sharepoints. If `is_magic` is run on a Windows path it will always flag it as "magic" unless you convert the
directory separators to `/` as `\` is a "magic" symbol.

```pycon3
>>> glob.is_magic('test')
False
>>> glob.is_magic('[test]ing?')
True
```

When `is_magic` is called, the system it is called on is detected automatically and/or inferred from flags such as
[`FORCEUNIX`](#forceunix) or [`FORCEWIN`](#forcewin). If the pattern is checked against a Windows system, UNC
sharepoints will be detected and treated differently. Wildcard Match cannot detect and glob all possible connected
sharepoints, so they are treated differently and cannot contain magic except in three cases:

1.  The drive or sharepoint is using backslashes as backslashes are treated as magic.
2.  [`BRACE`](#brace) is enabled and either `{` or `}` are found in the drive name or UNC sharepoint.
3.  [`SPLIT`](#split) is enabled and `|` is found in the drive name or UNC sharepoint.

```pycon3
>>> glob.is_magic('//?/UNC/server/mount{}/', flags=glob.FORCEWIN)
False
>>> glob.is_magic('//?/UNC/server/mount{}/', flags=glob.FORCEWIN | glob.BRACE)
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
[`GLOBTILDE`](#globtilde)     | `~`

/// new | New 8.1
Added `is_magic` in 8.1.
///

## Flags

#### `glob.CASE, glob.C` {: #case}

`CASE` forces case sensitivity. `CASE` has higher priority than [`IGNORECASE`](#ignorecase).

On Windows, drive letters (`C:`) and UNC sharepoints (`//host/share`) portions of a path will still be treated case
insensitively, but the rest of the path will have case sensitive logic applied.

#### `glob.IGNORECASE, glob.I` {: #ignorecase}

`IGNORECASE` forces case insensitivity. [`CASE`](#case) has higher priority than `IGNORECASE`.

#### `glob.RAWCHARS, glob.R` {: #rawchars}

`RAWCHARS` causes string character syntax to be parsed in raw strings: `#!py r'\u0040'` --> `#!py r'@'`. This will
handle standard string escapes and Unicode including `#!py r'\N{CHAR NAME}'`.

#### `glob.NEGATE, glob.N` {: #negate}

`NEGATE` causes patterns that start with `!` to be treated as exclusion patterns. A pattern of `!*.py` exclude any
Python files. Exclusion patterns cannot be used by themselves though, and must be paired with a normal, inclusion
pattern, either by utilizing the [`SPLIT`](#split) flag, or providing multiple patterns in a list. Assuming the
[`SPLIT`](#split) flag, this means using it in a pattern such as `inclusion|!exclusion`.

If it is desired, you can force exclusion patterns, when no inclusion pattern is provided, to assume all files match
unless the file matches the excluded pattern. This is done with the [`NEGATEALL`](#negateall) flag.

`NEGATE` enables [`DOTGLOB`](#dotglob) in all exclude patterns, this cannot be disabled. This will not affect the
inclusion patterns.

If `NEGATE` is set and exclusion patterns are passed via a matching or glob function's `exclude` parameter, `NEGATE`
will be ignored and the `exclude` patterns will be used instead. Either `exclude` or `NEGATE` should be used, not both.

#### `glob.NEGATEALL, glob.A` {: #negateall}

`NEGATEALL` can force exclusion patterns, when no inclusion pattern is provided, to assume all files match unless the
file matches the excluded pattern. Essentially, it means if you use a pattern such as `!*.md`, it will assume two
patterns were given: `**` and `!*.md`, where `!*.md` is applied to the results of `**`, and `**` is specifically treated
as if [`GLOBSTAR`](#globstar) was enabled.

Dot files will not be returned unless [`DOTGLOB`](#dotglob) is enabled. Symlinks will also not be traversed unless
[`FOLLOW`](#follow) is enabled.

#### `glob.MINUSNEGATE, glob.M` {: #minusnegate}

When `MINUSNEGATE` is used with [`NEGATE`](#negate), exclusion patterns are recognized by a pattern starting with
`-` instead of `!`. This plays nice with the extended glob feature which already uses `!` in patterns such as `!(...)`.

#### `glob.GLOBSTAR, glob.G` {: #globstar}

`GLOBSTAR` enables the feature where `**` matches zero or more directories.

#### `glob.GLOBSTARLONG, glob.GL` {: #globstarlong}

/// new | New 10.0
///

When `GLOBSTARLONG` is enabled `***` will act like `**`, but will cause symlinks to be traversed as well.

Enabling `GLOBSTARLONG` automatically enables [`GLOBSTAR`](#globstar).

[`FOLLOW`](#follow) will be ignored and `***` will be required to traverse a symlink. But it should be noted that when
using [`MATCHBASE`](#matchbase) and [`FOLLOW`](#follow) with `GLOBSTARLONG`, that [`FOLLOW`](#follow) will cause the
implicit leading `**` that [`MATCHBASE`](#matchbase) applies to act as an implicit `***`.

#### `glob.FOLLOW, glob.L` {: #follow}

`FOLLOW` will cause [`GLOBSTAR`](#globstar) patterns (`**`) to traverse symlink directories.

`FOLLOW` will have no affect if using [`GLOBSTARLONG`](#globstarlong) and an explicit `***` will be required to traverse
a symlink. `FOLLOW` will have an affect if enabled with [`GLOBSTARLONG`](#globstarlong) and [`MATCHBASE`](#matchbase)
and will cause the implicit leading `**` that `MATCHBASE` applies to act as an implicit `***`.

#### `glob.REALPATH, glob.P` {: #realpath}

In the past, only [`glob`](#glob) and [`iglob`](#iglob) operated on the filesystem, but with `REALPATH`, other
functions will now operate on the filesystem as well: [`globmatch`](#globmatch) and [`globfilter`](#globfilter).

Normally, functions such as [`globmatch`](#globmatch) would simply match a path with regular expression and return
the result. The functions were not concerned with whether the path existed or not. It didn't care if it was even valid
for the operating system.

`REALPATH` forces [`globmatch`](#globmatch) and [`globfilter`](#globfilter) to treat the string path as a real
file path for the given system it is running on. It will augment the patterns used to match files and enable additional
logic so that the path must meet the following in order to match:

-   Path must exist.
-   Directories that are symlinks will not be traversed by [`GLOBSTAR`](#globstar) patterns (`**`) unless the
    [`FOLLOW`](#follow) flag is enabled.
-   If [`GLOBSTARLONG`](#globstarlong) is enabled, `***` will traverse symlinks, [`FOLLOW`](#follow) will be ignored
    except if [`MATCHBASE`](#matchbase) is also enabled, in that case, the implicit leading `**` added by
    [`MATCHBASE`](#matchbase) will act as `***`.
-   When presented with a pattern where the match must be a directory, but the file path being compared doesn't indicate
    the file is a directory with a trailing slash, the command will look at the filesystem to determine if it is a
    directory.
-   Paths must match in relation to the current working directory unless the pattern is constructed in a way to indicates
    an absolute path.

Since `REALPATH` causes the file system to be referenced when matching a path, flags such as
[`FORCEUNIX`](#forceunix) and [`FORCEWIN`](#forcewin) are not allowed with this flag and will be ignored.

#### `glob.DOTGLOB, glob.D` {: #dotglob}

By default, [`glob`](#glob) and [`globmatch`](#globmatch) will not match file or directory names that start with
dot `.` unless matched with a literal dot. `DOTGLOB` allows the meta characters (such as `*`) to glob dots like any
other character. Dots will not be matched in `[]`, `*`, or `?`.

Alternatively `DOTMATCH` will also be accepted for consistency with the other provided libraries. Both flags are exactly
the same and are provided as a convenience in case the user finds one more intuitive than the other since `DOTGLOB` is
often the name used in Bash.

#### `glob.NODOTDIR, glob.Z` {: #globnodotdir}

`NOTDOTDIR` fundamentally changes how glob patterns deal with `.` and `..`. This is great if you'd prefer a more Zsh
feel when it comes to special directory matching. When `NODOTDIR` is enabled, "magic" patterns, such as `.*`, will not
match the special directories of `.` and `..`. In order to match these special directories, you will have to use
literal glob patterns of `.` and `..`. This can be used in all glob API functions that accept flags, and will affect
inclusion patterns as well as exclusion patterns.

```pycon3
>>> from wcmatch import glob
>>> glob.globfilter(['.', '..'], '.*')
['.', '..']
>>> glob.globfilter(['.', '..'], '.*', flags=glob.NODOTDIR)
[]
>>> glob.globfilter(['.', '..'], '.', flags=glob.NODOTDIR)
['.']
>>> glob.globfilter(['.', '..'], '..', flags=glob.NODOTDIR)
['..']
```

Also affects exclusion patterns:

```pycon3
>>> from wcmatch import glob
>>> glob.glob(['..', '!.*'], flags=glob.NEGATE)
[]
>>> glob.glob(['..', '!.*'], flags=glob.NEGATE | glob.NODOTDIR)
['..']
>>> glob.glob(['..', '!..'], flags=glob.NEGATE | glob.NODOTDIR)
[]
```

/// new | New 7.0
`NODOTDIR` was added in 7.0.
///

#### `glob.SCANDOTDIR, glob.SD` {: #scandotdir}

`SCANDOTDIR` controls the directory scanning behavior of [`glob`](#glob) and [`iglob`](#iglob). The directory scanner
of these functions do not return `.` and `..` in their results. This means that unless you use an explicit `.` or `..`
in your glob pattern, `.` and `..` will not be returned. When `SCANDOTDIR` is enabled, `.` and `..` will be returned
when a directory is scanned causing "magic" patterns, such as `.*`, to match `.` and `..`.

This only controls the directory scanning behavior and not how glob patterns behave. Exclude patterns, which filter
the returned results via [`NEGATE`](#negate), can still match `.` and `..` with "magic" patterns such as `.*` regardless
of whether `SCANDOTDIR` is enabled or not. It will also have no affect on [`globmatch`](#globmatch). To fundamentally
change how glob patterns behave, you can use [`NODOTDIR`](#nodotdir).

```pycon3
>>> from wcmatch import glob
>>> glob.glob('.*')
['.codecov.yml', '.tox', '.coverage', '.coveragerc', '.gitignore', '.github', '.pyspelling.yml', '.git']
>>> glob.glob('.*', flags=glob.SCANDOTDIR)
['.', '..', '.codecov.yml', '.tox', '.coverage', '.coveragerc', '.gitignore', '.github', '.pyspelling.yml', '.git']
```

/// new | New 7.0
`SCANDOTDIR` was added in 7.0.
///

#### `glob.EXTGLOB, glob.E` {: #extglob}

`EXTGLOB` enables extended pattern matching which includes special pattern lists such as `+(...)`, `*(...)`, `?(...)`,
etc. Pattern lists allow for multiple patterns within them separated by `|`. See the globbing [syntax overview](#syntax)
for more information.

Alternatively `EXTMATCH` will also be accepted for consistency with the other provided libraries. Both flags are exactly
the same and are provided as a convenience in case the user finds one more intuitive than the other since `EXTGLOB` is
often the name used in Bash.

/// tip | EXTGLOB and NEGATE
When using `EXTGLOB` and [`NEGATE`](#negate) together, if a pattern starts with `!(`, the pattern will not
be treated as a [`NEGATE`](#negate) pattern (even if `!(` doesn't yield a valid `EXTGLOB` pattern). To negate
a pattern that starts with a literal `(`, you must escape the bracket: `!\(`.
///

#### `glob.BRACE, glob.B` {: #brace}

`BRACE` enables Bash style brace expansion: `a{b,{c,d}}` --> `ab ac ad`. Brace expansion is applied before anything
else. When applied, a pattern will be expanded into multiple patterns. Each pattern will then be parsed separately.

Duplicate patterns will be discarded[^1] by default, and `glob` and `iglob` will return only unique results. If you need
[`glob`](#glob) or [`iglob`](#iglob) to behave more like Bash and return all results, you can set
[`NOUNIQUE`](#nounique). [`NOUNIQUE`](#nounique) has no effect on matching functions such as
[`globmatch`](#globmatch) and [`globfilter`](#globfilter).

For simple patterns, it may make more sense to use [`EXTGLOB`](#extglob) which will only generate a single pattern
which will perform much better: `@(ab|ac|ad)`.

/// warning | Massive Expansion Risk
1.  It is important to note that each pattern is crawled separately, so patterns such as `{1..100}` would generate
    **one hundred** patterns. In a match function ([`globmatch`](#globmatch)), that would cause a hundred compares,
    and in a file crawling function ([`glob`](#glob)), it would cause the file system to be crawled one hundred
    times. Sometimes patterns like this are needed, so construct patterns thoughtfully and carefully.

2.  `BRACE` and [`SPLIT`](#split) both expand patterns into multiple patterns. Using these two syntaxes
    simultaneously can exponential increase duplicate patterns:

    ```pycon3
    >>> expand('test@(this{|that,|other})|*.py', BRACE | SPLIT | EXTMATCH)
    ['test@(this|that)', 'test@(this|other)', '*.py', '*.py']
    ```

    This effect is reduced as redundant, identical patterns are optimized away[^1], but when using crawling
    functions (like [`glob`](#glob)) *and* [`NOUNIQUE`](#nounique) that optimization is removed, and all of
    those patterns will be crawled. For this reason, especially when using functions like [`glob`](#glob), it is
    recommended to use one syntax or the other.
///

[^1]: Identical patterns are only reduced by comparing case sensitively as POSIX character classes are case sensitive:
`[[:alnum:]]` =/= `[[:ALNUM:]]`.

#### `glob.SPLIT, glob.S` {: #split}

`SPLIT` is used to take a string of multiple patterns that are delimited by `|` and split them into separate patterns.
This is provided to help with some interfaces that might need a way to define multiple patterns in one input. It pairs
really well with [`EXTGLOB`](#extglob) and takes into account sequences (`[]`) and extended patterns (`*(...)`) and
will not parse `|` within them.  You can also escape the delimiters if needed: `\|`.

Duplicate patterns will be discarded[^1] by default, and `glob` and `iglob` will return only unique results. If you need
[`glob`](#glob) or [`iglob`](#iglob) to behave more like Bash and return all results, you can set
[`NOUNIQUE`](#nounique). [`NOUNIQUE`](#nounique) has no effect on matching functions such as
[`globmatch`](#globmatch) and [`globfilter`](#globfilter).

While `SPLIT` is not as powerful as [`BRACE`](#brace), it's syntax is very easy to use, and when paired with
[`EXTGLOB`](#extglob), it feels natural and comes a bit closer. It is also much harder to create massive expansions
of patterns with it, except when paired *with* [`BRACE`](#brace). See [`BRACE`](#brace) and its warnings
related to pairing it with `SPLIT`.

```pycon3
>>> from wcmatch import glob
>>> glob.globmatch('test.txt', '*.txt|*.py', flags=fnmatch.SPLIT)
True
>>> glob.globmatch('test.py', '*.txt|*.py', flags=fnmatch.SPLIT)
True
```

#### `glob.NOUNIQUE, glob.Q` {: #nounique}

`NOUNIQUE` is used to disable Wildcard Match's unique results return. This mimics Bash's output behavior if that is
desired.

```pycon3
>>> from wcmatch import glob
>>> glob.glob('{*,README}.md', flags=glob.BRACE | glob.NOUNIQUE)
['LICENSE.md', 'README.md', 'README.md']
>>> glob.glob('{*,README}.md', flags=glob.BRACE )
['LICENSE.md', 'README.md']
```

By default, only unique paths are returned in [`glob`](#glob) and [`iglob`](#iglob). Normally this is what a
programmer would want from such a library, so input patterns are reduced to unique patterns[^1] to reduce excessive
matching with redundant patterns and excessive crawls through the file system. Also, as two different patterns that have
been fed into [`glob`](#glob) may match the same file, the results are also filtered as to not return the
duplicates.

Unique results is are accomplished by filtering out duplicate patterns and by retaining an internal set of returned
files to determine duplicates. The internal set of files is not retained if only a single, inclusive pattern is
provided. Exclusive patterns via [`NEGATE`](#negate) will not trigger the logic. Singular inclusive patterns that
use pattern expansions due to [`BRACE`](#brace) or [`SPLIT`](#split) will act as if multiple patterns were
provided, and will trigger the duplicate filtering logic. This is mentioned as functions such as [`iglob`](#iglob),
which normally are expected to not retain results in memory, will be forced to retain a set to ensure unique results if
multiple inclusive patterns are provided.

`NOUNIQUE` disables all of the aforementioned "unique" optimizations, but only for [`glob`](#glob) and
[`iglob`](#iglob). Functions like [`globmatch`](#globmatch) and [`globfilter`](#globfilter) would get no
benefit from disabling "unique" optimizations as they only match what they are given.

/// new | New in 6.0
"Unique" optimizations were added in 6.0, along with `NOUNIQUE`.
///

#### `glob.GLOBTILDE, glob.T` {: #globtilde}

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

`GLOBTILDE` can also be used in things like [`globfilter`](#globfilter) or [`globmatch`](#globmatch), but you must
be using [`REALPATH`](#realpath) or the user path will not be expanded.

```pycon3
from wcmatch import glob
>>> glob.globmatch('/home/facelessuser/', '~', flags=glob.GLOBTILDE | glob.REALPATH)
True
```

/// new | New 6.0
Tilde expansion with `GLOBTILDE` was added in version 6.0.
///

#### `glob.MARK, glob.K` {: #mark}

`MARK` ensures that [`glob`](#glob) and [`iglob`](#iglob) to return all directories with a trailing slash. This
makes it very clear which paths are directories and allows you to save calling `os.path.isdir` as you can simply check
for a path separator at the end of the path. This flag only applies to calls to `glob` or `iglob`.

If you are passing the returned files from `glob` to [`globfilter`](#globfilter) or [`globmatch`](#globmatch),
it is important to ensure directory paths have trailing slashes as these functions have no way of telling the path is a
directory otherwise (except when [`REALPATH`](#realpath) is enabled). If you have [`REALPATH`](#realpath)
enabled, ensuring the files have trailing slashes can still save you a call to `os.path.isdir` as
[`REALPATH`](#realpath) resorts to calling it if there is no trailing slash.

```pycon3
>>> from wcmatch import glob
>>> glob.glob('*', flags=glob.MARK)
['appveyor.yml', 'base.patch', 'basematch.diff', 'docs/', 'LICENSE.md', 'MANIFEST.in', 'mkdocs.yml', 'README.md', 'requirements/', 'setup.cfg', 'setup.py', 'tests/', 'tools/', 'tox.ini', 'wcmatch/']
>>> glob.glob('*')
['appveyor.yml', 'base.patch', 'basematch.diff', 'docs', 'LICENSE.md', 'MANIFEST.in', 'mkdocs.yml', 'README.md', 'requirements', 'setup.cfg', 'setup.py', 'tests', 'tools', 'tox.ini', 'wcmatch']
```

#### `glob.MATCHBASE, glob.X` {: #matchbase}

`MATCHBASE`, when a pattern has no slashes in it, will cause [`glob`](#glob) and [`iglob`](#iglob) to seek for
any file anywhere in the tree with a matching basename. When enabled for [`globfilter`](#globfilter) and
[`globmatch`](#globmatch), any path whose basename matches. `MATCHBASE` is sensitive to files and directories that
start with `.` and will not match such files and directories if [`DOTGLOB`](#dotglob) is not enabled.


```pycon3
>>> from wcmatch import glob
>>> glob.glob('*.txt', flags=glob.MATCHBASE)
['docs/src/dictionary/en-custom.txt', 'docs/src/markdown/_snippets/abbr.txt', 'docs/src/markdown/_snippets/links.txt', 'docs/src/markdown/_snippets/posix.txt', 'docs/src/markdown/_snippets/refs.txt', 'requirements/docs.txt', 'requirements/lint.txt', 'requirements/setup.txt', 'requirements/test.txt', 'requirements/tools.txt']
```

#### `glob.NODIR, glob.O` {: #nodir}

`NODIR` will cause [`glob`](#glob), [`iglob`](#iglob), [`globmatch`](#globmatch), and [`globfilter`](#globfilter) to return only matched files.

```pycon3
>>> from wcmatch import glob
>>> glob.glob('*', flags=glob.NODIR)
['appveyor.yml', 'LICENSE.md', 'MANIFEST.in', 'mkdocs.yml', 'README.md', 'setup.cfg', 'setup.py', 'spell.log', 'tox.ini']
>>> glob.glob('*')
['appveyor.yml', 'docs', 'LICENSE.md', 'MANIFEST.in', 'mkdocs.yml', 'README.md', 'requirements', 'setup.cfg', 'setup.py', 'spell.log', 'tests', 'tools', 'tox.ini', 'wcmatch']
```

#### `glob.FORCEWIN, glob.W` {: #forcewin}

`FORCEWIN` will force Windows path and case logic to be used on Linux/Unix systems. It will also cause slashes to be
normalized and Windows drive syntax to be handled special. This is great if you need to match Windows specific paths on
a Linux/Unix system. This will only work on commands that do not access the file system: [`translate`](#translate),
[`globmatch`](#globmatch), [`globfilter`](#globfilter), etc. These flags will not work with [`glob`](#glob)
or [`iglob`](#iglob). It also will not work when using the [`REALPATH`](#realpath) flag with things like
[`globmatch`](#globmatch) and [`globfilter`](#globfilter).

If `FORCEWIN` is used along side [`FORCEUNIX`](#forceunix), both will be ignored.

#### `glob.FORCEUNIX, glob.U` {: #forceunix}

`FORCEUNIX` will force Linux/Unix path and case logic to be used on Windows systems. This is great if you need to match
Linux/Unix specific paths on a Windows system. This will only work on commands that do not access the file system:
[`translate`](#translate), [`globmatch`](#globmatch), [`globfilter`](#globfilter), etc. These flags will not
work with [`glob`](#glob) or [`iglob`](#iglob). It also will not work when using the [`REALPATH`](#realpath)
flag with things like [`globmatch`](#globmatch) and [`globfilter`](#globfilter).

When using `FORCEUNIX`, the paths are assumed to be case sensitive, but you can use [`IGNORECASE`](#ignorecase) to
use case insensitivity.

If `FORCEUNIX` is used along side [`FORCEWIN`](#forcewin), both will be ignored.
