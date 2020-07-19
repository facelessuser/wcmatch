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
   shells (such as Zsh) that do not return `.` and `..` except with a literal pattern requesting `.` and `..` is
   provided. This is because a lot of people agree that matching `.` and `..` in these scenarios isn't that helpful.
   Even Python's default glob doesn't return `.` and `..`.

1. Python's `pathlib`, which Wildcard Match's `pathlib` is derived from, normalizes paths by stripping out `.`
   directories and trimming off trailing slashes.  This means patterns such as `**/.*` which would normally match both
   `.hidden` and `.hidden/.` would normalize those results to return two `.hidden` results. This is generally unhelpful
   and unintuitive.

3. Python's `scandir`, wich is used to crawl the file system, doesnt actually return `.` and `..`. In order to do this
   in the past, we had to inject them into the results.

For the majority of people, this is most likely an improvement vs a hindrance, but if the old behavior is desired, you
can use the new option [`SCANDOTDIR`](../glob.md#scandotdir) to bring this behavior back. Due to the way
[`pathlib`](../pathlib.md) normalizes paths, it [`SCANDOTDIR`](../glob.md#scandotdir) is probably not recommended with
[`pathlib`](../pathlib.md).

### Windows Drive Detection

Improvements with handling Windows drive and UNC paths have been added. This glob patterns will now properly respect
extended UNC paths usch as `//?/UNC/LOCALHOSt/c$` and others. This is good because now you can specify these type of
paths and not have to worry about escaping meta characters within the drive name. Also, since we don't scan all
available drives and mounts, meta characters such as `*` are not helpful anyways.

While UNC mounts and drives are not subject to glob meta characters, pattern expansion characters such as `{}` (when
using [`BRACE`](../glob.md#brace)) or `|` (when using [`SPLIT`](../glob.md#split)) do affect Windows drives/mounts. This
is due to the fact that pattern expansion occurs before the a pattern is evaluated as an actual glob pattern.

Starting in 7.0 glob patterns can have `{`, `}` and `|` escaped in the Windows drive or mount portion of the pattern.
Additionally, both the [`escape`](../glob.md#escape) and [`raw_escape`](../glob.md#raw_escape) functions will properly
escape these characters. This means you can use patterns such as Windows volumes with GUIDs safely with 
[`BRACE`](../glob.md#brace):

```pycon3
>>> from wmcatch import glob
>>> glob.escape('//./Volume{b75e2c83-0000-0000-0000-602f00000000}\Test\Foo.txt', unix=False)
'//./Volume\\{b75e2c83-0000-0000-0000-602f00000000\\}\\\\Test\\\\Foo.txt'
```

### `pathlib` Duplicate Results

In general, glob should return only unique results for a singular inclusive pattern. If given multiple patterns, or if
given a pattern that is expanded into multiple via [`BRACE`](../glob.md#brace) or [`SPLIT`](../glob.md#split), then
multiple patterns are actually possible. In 6.0, duplicate patterns are stripped out by default in multiple pattern
cases (unless [`NOUNIQUE`](../glob.md#nounique) is provided), but due to some quirks of `pathlib`, duplicates could
still slip through.

Due to `pathlib` file path normalization, `.` directories are stripped out, and trailing slashes are stripped off paths.
With the changes noted in [Globbing](#globbing) single pattern cases no longer return duplicate paths, but results
across multiple patterns still could. If three different patterns returned `file/./path`, `file/path/.` and `file/path`,
you'd get three identical results of `file/path`. These cases will now properly get caught and filtered out by during
file globbing.

As always, this uinque behavior can be disabled via [`NOUNIQUE`](../glob.md#nounique).
