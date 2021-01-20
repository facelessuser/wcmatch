# Release Notes

## Upgrade to 8.0 {: #upgrade-to-\8.0}

Notable changes are minor and will affect very few. This should clarify breaking changes and how to migrate if
applicable.

### `WcMatch` class Initialization Hook

The [`WcMatch`](../wcmatch.md#wcmatch) class `on_init` hook was cleaned up. Prior to 8.0, it accepted both `*args` and
`**kwargs` which is quite difficult to maintain and honestly for users to use.

Moving forward, the `WcMatch` class will restrict all parameters to `**kwargs`. If you are using the `on_init` hook,
you will simply need to change your override to accept arguments as `**kwargs`:

```py3
# Excplicitly named
def on_init(self, key1=value, key2=value):

# Or just use `**kwargs`
def on_init(self, **kwargs):
```

Lastly, only pass your custom variables in as keyword arguments:

```py3
CustomWcmatch('.', '*.md|*.txt', flags=wcmatch.RECURSIVE, custom_key=value)
```

## Upgrade to 7.0 {: #upgrade-to-\7.0}

Notable changes will be highlighted here to help with migration to 7.0.

### Globbing Special Directories

File globbing with [`glob.glob`](../glob.md#glob),  [`glob.iglob`](../glob.md#iglob),
[`pathlib.path.glob`](../pathlib.md#glob), and [`pathlib.Path.rglob`](../pathlib.md#rglob) no longer inject `.` and `..`
into results when scanning directories. This *only* affects the results of a scanned directory and does not
fundamentally change how glob patterns evaluate a path.

Python's default glob does not return `.` or `..` for any "magic" (non-literal) patterns in `glob`. This is because
magic patterns trigger glob to iterate over a directory in an attempt to find a file that can match the given "magic"
pattern. Since `.` and `..` are not returned by Python's implementation of `scandir`, `.` and `..` never get evaluated.
Literal patterns can side step the directory iteration with a simple check to see if the file exists. What this means is
that a "magic" pattern of `.*` will not match `.` or `..`, because it is not returned in the scan, but a literal pattern
of `.` or `..` will as the literal patterns are simply checked to see if they exist.

This is common behavior for a number of libraries, Python, [node-glob], etc., but not all. Moving forward, we have
chosen to adopt the Python's behavior as our default behavior, with the option of forcing Bash's behavior of returning
`.` and `..` in a directory scan if desired.

These examples will illustrate the behavior. In the first example, Python's `pathlib` is used to glob a
directory. We can note that not a single entry in the results is `.` or `..`.

```pycon3
>>> import pathlib
>>> list(pathlib.Path('.').glob('.*'))
[PosixPath('.DS_Store'), PosixPath('.codecov.yml'), PosixPath('.tox'), PosixPath('.coverage'), PosixPath('.coveragerc'), PosixPath('.gitignore'), PosixPath('.github'), PosixPath('.pyspelling.yml'), PosixPath('.git')]
```

We can also show that if we search for the literal pattern of `..` that glob will then return `..` in the results.

```pycon3
>>> import pathlib
>>> list(pathlib.Path('.').glob('..'))
[PosixPath('..')]
```

When using the `match` function, we see that the pattern can match `..` just fine. This illustrates that it is not the
pattern logic that restricts this, but a result of the behavior exhibited by `scandir`.

```pycon3
>>> import pathlib
>>> pathlib.Path('..').match('.*')
True
```

While our algorithm is different due to some of the features we support, and it may oversimplify things to say we
now turn off injecting `.` and `..` into `scandir` results, but for all intents and purposes, all of our file system
globbing functions exhibit the same behavior as Python's default glob now.


```pycon3
>>> from wcmatch import glob
>>> glob.glob('.*')
['.DS_Store', '.codecov.yml', '.tox', '.coverage', '.coveragerc', '.gitignore', '.github', '.pyspelling.yml', '.git']
>>> glob.glob('..')
['..']
>>> glob.globmatch('..', '.*')
True
```

Because this change only affects how files are returned when iterating the directories, we can notice that exclude
patterns, which are used to filter the results, can match `.` or `..` with `.*`:

```pycon3
>>> from wcmatch import glob
>>> glob.glob('..')
['..']
>>> glob.glob(['..', '!.*'], flags=glob.NEGATE)
[]
```

If we want to modify the pattern matcher, and not just the the directory scanner, we can use the flag
[`NODITDIR`](../glob.md#nodotdir).

```pycon3
>>> from wcmatch import glob
>>> glob.glob(['..', '!.*'], flags=glob.NEGATE | glob.NODOTDIR)
['..']
>>> glob.glob(['..', '!..'], flags=glob.NEGATE | glob.NODOTDIR)
[]
```

These changes were done for a couple of reasons:

1. Generally, it is rare to specifically want `.` and `..`, so often when people glob with something like `**/.*`, they
   are just trying to get hidden files. While we generally model our behavior off Bash, there are many alternative
   shells (such as Zsh) that do not return or match `.` and `..` with magic patterns by design, regardless of what
   directory scanner returns.

2. Many people who come to use our library are probably coming from having experience with Python's glob. By mirroring
   this behavior out of the box, it may help people adapt to the library easier.

3. Python's `pathlib`, which Wildcard Match's `pathlib` is derived from, normalizes paths by stripping out `.`
   directories and trimming off trailing slashes.  This means patterns such as `**/.*`, which would normally match both
   `.hidden` and `.hidden/.`, would normalize those results to return two `.hidden` results. Mirroring this behavior
   helps provide more sane results and prevent confusing duplicates when using `pathlib`.

4. This is not unique behavior to Python's glob and our implementation. For example, let's take a look at
   [`node-glob`](https://github.com/isaacs/node-glob) and its underlying match library called
   [`minimatch`](https://github.com/isaacs/minimatch).

    ```js
    > glob('.*', {}, function (er, files) {
    ... console.log(files)
    ... })
    > [
      '.codecov.yml',
      '.coverage',
      '.coveragerc',
      '.DS_Store',
      '.git',
      '.github',
      '.gitignore',
      '.pyspelling.yml',
      '.tox'
    ]
    ```

    We also see that the file matching library has no issues matching `.` or `..` with `.*`.


    ```js
    > minimatch("..", ".*")
    true
    ```

    We can also see that ignore patterns, just like our ignore patterns, are applied to the results, and are unaffected
    by the underlying behavior of the directory scanner:

    ```js
    > glob('..', {}, function (er, files) {
    ... console.log(files)
    ... })
    > [ '..' ]
    > glob('..', {ignore: ['.*']}, function (er, files) {
    ... console.log(files)
    ... })
    > []
    ```

For the majority of people, this is most likely an improvement rather than a hindrance, but if the old behavior is
desired, you can use the new option [`SCANDOTDIR`](../glob.md#scandotdir) which restores the logic that emulates the
feel of `scandir` returning `.` and `..` when iterating a directory.

Due to the way [`pathlib`](../pathlib.md) normalizes paths, [`SCANDOTDIR`](../glob.md#scandotdir) is not recommended to
be used with [`pathlib`](../pathlib.md).

### Windows Drive Handling

It is not practical to scan a system for all mounted drives and available network paths. Just like with Python's
default globbing, we do not scan all available drives, and so wildcard patterns do not apply to these drives.
Unfortunately, our implementation used to only handle very basic UNC cases, and if patterns with extended UNC paths
were attempted, failure was likely.

7.0 brings improvements related to Windows drives and UNC paths. Glob patterns will now properly respect extended UNC
paths such as `//?/UNC/LOCALHOST/c$` and others. This means you can use these patterns without issues. And just like
simple cases (`//server/mount`), extended cases do not require escaping meta characters, except when using pattern
expansion syntax that is available via [`BRACE`](../glob.md#brace) and [`SPLIT`](../glob.md#split).

### Glob Escaping

Because it can be problematic trying to mix Windows drives that use characters such as `{` and `}` with the
[`BRACE`](../glob.md#brace) flag, you can now escape these meta characters in drives if required. Prior to 7.0, such
escaping was disallowed, but now you can safely escape `{` and `}` to ensure optimal brace handling. While you can
safely escape other meta characters in drives as well, it is never actually needed.

Additionally, [`glob.escape`](../glob.md#escape) and [`glob.raw_escape`](../glob.md#raw_escape) will automatically
escape `{`, `}` and `|` to avoid complications with [`BRACE`](../glob.md#brace) and [`SPLIT`](../glob.md#split).

In general, a lot of corner cases with [`glob.escape`](../glob.md#escape) and [`glob.raw_escape`](../glob.md#raw_escape)
were cleaned up.

[`glob.escape`](../glob.md#escape) is meant to handle the escaping of normal paths so that they can be used in patterns.

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

By default, [`glob.raw_escape`](../glob.md#raw_escape) always translates Python character back references into actual
characters, but if this is not needed, a new option called `raw_chars` (`True` by default) has been added to disable
this behavior:

```pycon3
>>> glob.raw_escape(r'my\\file-\x31.txt', unix=False)
'my\\\\file\\-1.txt'
>>> glob.raw_escape(r'my\\file-\x31.txt', unix=False, raw_chars=False)
'my\\\\file\\-\\\\x31.txt'
```

### Reduction of `pathlib` Duplicate Results

In general, glob should return only unique results for a single inclusive pattern (exclusion patterns are not
considered). If given multiple patterns, or if given a pattern that is expanded into multiple via
[`BRACE`](../glob.md#brace) or [`SPLIT`](../glob.md#split), then duplicate results are actually possible.

In 6.0, logic to strip redundant patterns and to filter out duplicate results was added. This deduping is performed by
default if more than a single inclusive pattern is provided, even if they are indirectly provided via pattern expansion.
The [`NOUNIQUE`](../glob.md#nounique) flag disables this behavior if desired.

In general, this works well, but due to `pathlib`'s path normalization quirks, there were cases where duplicate results
would still be returned for multiple patterns, and even a case where duplicates were returned for a single pattern.

Due to `pathlib` file path normalization, `.` directories are stripped out, and trailing slashes are stripped off paths.
With the changes noted in [Globbing](#globbing-special-directories) single pattern cases no longer return duplicate
paths, but results across multiple patterns still could. For instance, it is possible that three different patterns,
provided at the same time (or through pattern expansion) could match the following paths: `file/./path`, `file/path/.`,
and `file/path`. Each of these results are unique as far as glob is concerned, but due to the `pathlib` normalization of
`.` and trailing slashes, `pathlib` glob will return all three of these results as `file/path`, giving three identical
results.

In 7.0, logic was added to detect `pathlib` normalization cases and ensure that redundant results are not returned.

```pycon3
>>> glob.glob(['docs/./src', 'docs/src/.', 'docs/src'])
['docs/./src', 'docs/src/.', 'docs/src']
>>> list(pathlib.Path('.').glob(['docs/./src', 'docs/src/.', 'docs/src']))
[PosixPath('docs/src')]
>>> list(pathlib.Path('.').glob(['docs/./src', 'docs/src/.', 'docs/src'], flags=pathlib.NOUNIQUE))
[PosixPath('docs/src'), PosixPath('docs/src'), PosixPath('docs/src')]
```
