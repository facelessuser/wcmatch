# Release Notes

## Upgrade to 7.0

Notable changes will be highlighted here to help with migration to 7.0.

### Globbing

File globbing with [`glob.glob`](../glob.md#glob),  [`glob.iglob`](../glob.md#iglob),
[`pathlib.path.glob`](../pathlib.md#glob), and [`pathlib.Path.rglob`](../pathlib.md#rglob) no longer return `.` and `..`
unless a literal pattern of `.` or `..`  is used. You cannot glob these special directories with something like `**/.*`
anymore.

File matching functions such as [`glob.globmatch`](../glob.md#globmatch) are more lenient and do not enforce this logic
on pattern matching, but if desired, [`NODOTDIR`](../glob.md#nodotdir) can be used to mirror the behavior in matching
functions as well.

These changes were done for a couple of reasons:

1. Generally, it is rare to specifically want `.` and `..`, so often when people glob with something like `**/.*`, they
   are just trying to get hidden files. While we generally model our behavior off Bash, there are many alternative
   shells (such as Zsh) that do not return `.` and `..` except when a literal pattern of `.` and `..` is
   provided. Even Python's default glob doesn't return `.` and `..`.

1. Python's `pathlib`, which Wildcard Match's `pathlib` is derived from, normalizes paths by stripping out `.`
   directories and trimming off trailing slashes.  This means patterns such as `**/.*` which would normally match both
   `.hidden` and `.hidden/.` would normalize those results to return two `.hidden` results. This is generally unhelpful
   and unintuitive. This normalization cannot be be avoided without rewriting portions of `pathlib`. Our intention is to
   provide better globbing and matching, not to rewrite `pathlib`.

3. Python's `scandir`, which is used to crawl the file system, doesn't actually return `.` and `..`. In order to do this
   in the past, we had to inject them into the results.

For the majority of people, this is most likely an improvement vs a hindrance, but if the old behavior is desired, you
can use the new option [`SCANDOTDIR`](../glob.md#scandotdir) to bring this behavior back. Due to the way
[`pathlib`](../pathlib.md) normalizes paths, it [`SCANDOTDIR`](../glob.md#scandotdir) is probably not recommended with
[`pathlib`](../pathlib.md).

### Windows Drive Handling

It is not practical to scan a system for all mounted drives and available network paths. Just like with Python's
default globbing, we do not scan all available drives, and so wildcard patterns do not apply to these drives.
Unfortunately, our implementation used to only handle very basic UNC cases, and if patterns with extended UNC paths
were attempted, failure was likely.

7.0 brings improvements related to Windows drives and UNC paths. Glob patterns will now properly respect extended UNC
paths such as `//?/UNC/LOCALHOSt/c$` and others. This means you can use these patterns without issues. And just like
simple cases (`//server/mount`), extended case do not require escaping meta characters, except when using pattern
expansion syntax that is available via [`BRACE`](../glob.md#brace) and [`SPLIT`](../glob.md#split).

### Glob Escaping

Because it can be problematic trying to mix Windows drives that use characters such as `{` and `}` with the
[`BRACE`](../glob.md#brace) flag, you can now escape these meta characters in drives if required. Prior to 7.0, such
escaping was disallowed, but now you can safely escape `{` and `}` to ensure optimal brace handling. While you can
safely escape other meta characters in drive as well, it is never actually needed.

Additionally, [`glob.escape`](../glob.md#escape) and [`glob.raw_escape`](../glob.md#raw_escape) will automatically
escape `{`, `}` and `|` to avoid in complications [`BRACE`](../glob.md#brace) and [`SPLIT`](../glob.md#split).

In general, a lot of corner cases with [`glob.escape`](../glob.md#escape) and [`glob.raw_escape`](../glob.md#raw_escape)
were cleaned up. [`glob.escape`](../glob.md#escape) is meant to handle the escaping of normal paths, into strings that
can be used in patterns. For instance, to use back slashes in a glob pattern, you must use escaped back slashes because
you can also escape meta characters:

```pycon3
>>> glob.escape(r'my\file-[work].txt', unix=False)
'my\\\\file\\-\\[work\\].txt'
```
If you are accepting an input from a source that is giving you a representation of a Python string (where `\` is
represented by two `\`), then [`glob.raw_escape`](../glob.md#raw_escape) is what you want:

```pycon3
>>> glob.raw_escape(r'my\\file-[work].txt', unix=False)
'my\\\\file\\-\\[work\\].txt'
```

By default [`glob.raw_escape`](../glob.md#raw_escape) always translates Python character back references into actual
characters, but if this is not needed, a new option called `raw_chars` (`True` by default) has been added to disable
this behavior:

```pycon3
>>> glob.raw_escape(r'my\\file-\x31.txt', unix=False)
'my\\\\file\\-1.txt'
>>> glob.raw_escape(r'my\\file-\x31.txt', unix=False, raw_chars=False)
'my\\\\file\\-\\\\x31.txt'
```

### `pathlib` Duplicate Results

In general, glob should return only unique results for a single inclusive pattern (exclusion patterns are not
considered). If given multiple patterns, or if given a pattern that is expanded into multiple via
[`BRACE`](../glob.md#brace) or [`SPLIT`](../glob.md#split), then duplicate results are actually possible.

In 6.0, logic to strip redundant patterns and to filter out duplicate results was added. This deduping is performed by
default if more than a single inclusive pattern is provided, even if they are indirectly provided via pattern expansion.
The [`NOUNIQUE`](../glob.md#nounique) flag disables this behavior if desired.

In general, this works well, but due to `pathlib`'s path normalization quirks, there were cases where duplicate results
would still be returned for multiple patterns, and even a case where duplicates were returned for a single pattern.

Due to `pathlib` file path normalization, `.` directories are stripped out, and trailing slashes are stripped off paths.
With the changes noted in [Globbing](#globbing) single pattern cases no longer return duplicate paths, but results
across multiple patterns still could. For instance, it is possible that three different patterns, provided at the same
time (or through pattern expansion) could match the following paths: `file/./path`, `file/path/.` and `file/path`. Each
of these results are unique as far as glob is concerned, but due to the `pathlib` normalization of `.` and trailing
slashes, `pathlib` glob will return all three of these results as `file/path`, giving three identical results.

In 7.0, logic was added to detect `pathlib` normalization cases and ensure that redundant results are not returned.

```pycon3
>>> glob.glob(['docs/./src', 'docs/src/.', 'docs/src'])
['docs/./src', 'docs/src/.', 'docs/src']
>>> list(pathlib.Path('.').glob(['docs/./src', 'docs/src/.', 'docs/src']))
[PosixPath('docs/src')]
>>> list(pathlib.Path('.').glob(['docs/./src', 'docs/src/.', 'docs/src'], flags=pathlib.NOUNIQUE))
[PosixPath('docs/src'), PosixPath('docs/src'), PosixPath('docs/src')]
```
