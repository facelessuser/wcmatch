# Changelog

## 10.1

-   **NEW**: Drop support for Python 3.8 which is "end of life".
-   **NEW**: Add support for Python 3.14.
-   **NEW**: Add `wcmatch.glob.compile(pattern)` and `wcmatch.fnmatch.compile(pattern)` to allow for precompiled matcher
    objects that can be reused.

## 10.0

-   **NEW**: Added `GLOBSTARLONG` which adds support for the Zsh style `***` which acts like `**` with `GLOBSTAR` but
    traverses symlinks.
-   **NEW**: `pathlib.match` will respect symlink rules (when the `REALPATH` flag is given). Hidden file rules will
    be respected at all times. Enable `DOTALL` to match hidden files.
-   **NEW**: Symlinks should not be traversed when `GLOBSTAR` is enabled unless `FOLLOW` is also enabled, but they
    should still be matched. Prior to this change, symlinks were not traversed _and_ they were ignored from matching
    which contradicts how Bash works and could be confusing to users.
-   **FIX**: Fix some inconsistencies with `globmatch` and symlink handling when `REALPATH` is enabled.

## 9.0

-   **NEW**: Remove deprecated function `glob.raw_escape`.
-   **NEW**: Officially support Python 3.13.

## 8.5.2

-   **FIX**: Fix `pathlib` issue with inheritance on Python versions greater than 3.12.
-   **FIX**: Fix `EXTMATCH` case with `!(...)` patterns.

## 8.5.1

-   **FIX**: Fix issue with type check failure in `wcmatch.glob`.

## 8.5

-   **NEW**: Formally support Python 3.11 (no change).
-   **NEW**: Add support for Python 3.12 (`pathlib` changes).
-   **NEW**: Drop Python 3.7 support.
-   **FIX**: Fix handling of current directory when magic and non-magic patterns are mixed in `glob` pattern list.

## 8.4.1

-   **FIX**: Windows drive path separators should normalize like other path separators.
-   **FIX**: Fix a Windows pattern parsing issue that caused absolute paths with ambiguous drives to not parse
    correctly.

## 8.4

-   **NEW**: Drop support for Python 3.6.
-   **NEW**: Switch to Hatch backend instead of Setuptools.
-   **NEW**: Add new `exclude` option to `fnmatch`, `pathlib`, and `glob` methods that allows exclusion patterns to be
    specified directly without needing to enable `NEGATE` and prepend patterns with `!`. `exclude` accepts a separate
    pattern or pattern list. `exclude` should not be used in conjunction with `NEGATE`. One or the other should be used.

## 8.3

-   **NEW**: Officially support Python 3.10.
-   **NEW**: Provide type hints for API.
-   **FIX**: Gracefully handle calls with an empty pattern list.

## 8.2

-   **NEW**: Add support for `dir_fd` in glob patterns.
-   **FIX**: Small fix for Python 3.10 Beta 1 and `pathlib`.

## 8.1.2

-   **FIX**: `fnmatch.translate` no longer requires user to normalize their Windows paths for comparison. Previously,
    portions of the `translate` regex handled both `/` and `\\`, while other portions did not. This inconsistent
    handling forced users to normalize paths for reliable matching. Now all of the generated regex should handle both
    `/` and `\\`.
-   **FIX**: On Linux/Unix systems, a backslash should not be assumed literal if it is followed by a forward slash.
    Backslash is magic on all systems, and an escaped forward slash is still counted as a forward slash, not a backslash
    and forward slash.
-   **FIX**: A trailing backslash that is not escaped via another backslash should not be assumed as a backslash. Since
    it is escaping nothing, it will be ignored. Literal backslashes on any system must be escaped.

## 8.1.1

-   **FIX**: When tracking unique glob paths, the unique cache had inverted logic for case sensitive vs case insensitive
    comparison. (#164)

## 8.1

-   **NEW**: Add `is_magic` function to the `glob` and `fnmatch` library.
-   **NEW**: `fnmatch` now has `escape` available via its API. The `fnmatch` variant uses filename logic instead of path
    logic.
-   **NEW**: Deprecate `raw_escape` in `glob` as it is very niche and the same can be accomplished simply by using
    `codecs.decode(string, 'unicode_escape')` and then using `escape`.
-   **FIX**: Use `os.fspath` to convert path-like objects to string/bytes, whatever the return from `__fspath__` is what
    Wildcard Match will accept. Don't try to convert paths via `__str__` or `__bytes__` as not all path-like objects may
    implement both.
-   **FIX**: Better checking of types to ensure consistent failure if the path, pattern, or root directory of are not
    all of type `str` or `bytes`.
-   **FIX**: Some internal fixes and refactoring.
-   **FIX**: Refactor code to take advantage of `bracex`'s ability to abort parsing on extremely large pattern
    expansions. Patterns like `{1..10000000}` will now abort dramatically quicker. Require `bracex` 2.1.1 which aborts
    much quicker.
-   **FIX**: Fix some corner cases where limit would not abort correctly.

## 8.0.1

-   **FIX**: Small bug in `[:alpha:]` range.

## 8.0

-   **NEW**: `WcMatch`'s `on_init` hook now only accepts `kwargs` and not `args`.
-   **NEW**: Cosmetic change of referring to the first `__init__` parameter as `root_dir` instead of `base`. This is to
    make it more clear when we are talking about the overall root directory that all paths are relative to vs the base
    path of a file which is relative to the root directory and the actual file name.
-   **NEW**: Internal attribute of `WcMatch` changed from `base` to `_root_dir`. This attribute is not really meant to be
    referenced by users and as been marked as private.
-   **NEW**: Drop requirement for `backrefs` and update documentation to note that POSIX properties never actually
    enabled the use of Unicode properties. While the documentation stated this and it was probably intended, it was
    never actually enabled. Currently, Wildcard match has chosen to keep with the ASCII definition for now as it has
    been since the feature was introduced. This may change in the future if there is demand for it.
-   **NEW**: Add `[:word:]` POSIX character class.

## 7.2

-   **NEW**: Drop Python 3.5 support.
-   **NEW**: Formally support Python 3.9 support.
-   **FIX**: Small fix for regular expression output to ensure `NODIR` pattern looks at both `/` and `\\` on Windows.

## 7.1

-   **NEW**: Translate functions will now use capturing groups for `EXTGLOB`/`EXTMATCH` groups in the returned regular
    expression patterns.

## 7.0.1

-   **FIX**: Ensure that when using `REALPATH` that all symlinks are evaluated.
-   **FIX**: Fix issue where an extended pattern can't follow right behind an inverse extended pattern.
-   **FIX**: Fix issues related to nested inverse glob patterns.

## 7.0

Check out [Release Notes](./release.md#upgrade-to-7.0) to learn more about upgrading to 7.0.

-   **NEW**: Recognize extended UNC paths.
-   **NEW**: Allow escaping any character in Windows drives for better compatibility with `SPLIT` and `BRACE` which
    requires a user to escape `{`, `}` and `|` to avoid expanding a pattern.
-   **NEW**: `raw_escape` now accepts the `raw_chars` parameter so that translation of Python character back references
    can be disabled.
-   **NEW**: Search functions that use `scandir` will not return `.` and `..` for wildcard patterns that require
    iterating over a directory to match the files against a pattern. This matches Python's glob and is most likely what
    most users expect. Pattern matching logic is unaffected.
-   **NEW**: Add `SCANDOTDIR` flag to enable previous behavior of injecting `.` and `..` in `scandir` results.
    `SCANDOTDIR` has no affect on match functions such as `globmatch` which don't use directory scanning.
-   **NEW**: Flag `NODOTDIR` has been added to disable patterns such as `.*` from matching `.` and `..`. When enabled,
    matching logic is changed to require a literal pattern of `.` and `..` to match the special directories `.` and `..`.
    This is more Zsh like.
-   **FIX**: Negative extended glob patterns (`!(...)`) incorrectly allowed for hidden files to be returned when one of
    the subpatterns started with `.`, even when `DOTMATCH`/`DOTGLOB` was not enabled.
-   **FIX**: When `NOUNIQUE` is enabled and `pathlib` is being used, you could still get non-unique results across
    patterns expanded with `BRACE` or `SPLIT` (or even by simply providing a list of patterns). Ensure that unique
    results are only returned when `NOUNIQUE` is not enabled.
-   **FIX**: Fix corner cases with `escape` and `raw_escape` with back slashes.
-   **FIX**: Ensure that `globmatch` does not match `test//` with pattern `test/*`.
-   **FIX**: `pathlib.match` should not evaluate symlinks that are on the left hand side of what was matched.

## 6.1

-   **NEW**: `EXTMATCH`/`EXTGLOB` can now be used with `NEGATE` without needing `MINUSNEGATE`. If a pattern starts with
    `!(`, and `NEGATE` and `EXTMATCH`/`EXTGLOB` are both enabled, the pattern will not be treated as a `NEGATE` pattern
    (even if `!(` doesn't yield a valid `EXTGLOB` pattern). To negate a pattern that starts with a literal `(`, you must
    escape the bracket: `!\(`.
-   **FIX**: Support Python 3.9.
-   **FIX**: Adjust pattern limit logic of `glob` to be consistent with other functions.

## 6.0.3

-   **FIX**: Fix issue where when `FOLLOW` and `GLOBSTAR` were used, a pattern like `**/*` would not properly match
    a directory which was a symlink. While Bash does not return a symlinked folder with `**`, `*` (and other patterns),
    should properly find the symlinked directory.
-   **FIX**: `pathlib` clearly states that the `match` method, if the pattern is relative, matches from the right.
    Wildcard Match used the same implementation that `rglob` used, which prepends `**/` to a relative pattern. This is
    essentially like `MATCHBASE`, but allows for multiple directory levels. This means that dot files (and special
    folders such as `.` and `..`) on the left side could prevent the path from matching depending on flags that were
    set. `match` will now be evaluated in such a way as to give the same right to left matching feel that Python's
    `pathlib` uses.

## 6.0.2

-   **FIX**: Fix logic related to dot files and `GLOBSTAR`. Recursive directory search should return all dot files,
    which should then be filtered by the patterns. They should not be excluded before being filtered by the pattern.

## 6.0.1

-   **FIX**: If we only have one pattern (exclusion patterns not included) we can disable unique path filtering on
    returns as you cannot have a duplicate path with only one inclusion pattern.

## 6.0

-   **NEW**: Tilde user expansion support via the new `GLOBTILDE` flag.
-   **NEW**: `glob` by default now returns only unique results, regardless of whether multiple patterns that match the
    same file were provided, or even when `BRACE` or `SPLIT` expansion produces new patterns that match the same file.
-   **NEW**: A new flag called `NOUNIQUE` has been added that makes `glob` act like Bash, which will return the same
    file multiple times if multiple patterns match it, whether provided directly or due to the result of `BRACE` or
    `SPLIT` expansion.
-   **NEW**: Limit number of patterns that can be processed (expanded and otherwise) to 1000. Allow user to change this
    value via an optional `limit` parameter in related API functions.
-   **FIX**: Matching functions that receive multiple patterns, or that receive a single pattern that expands to
    multiple, will filter out duplicate patterns in order avoid redundant matching. While the `WcMatch` class crawls the
    file system, it utilizes the aforementioned matching functions in it's operation, and indirectly takes advantage of
    this. `glob` (and related functions: `rglob`, `iglob`, etc.) will also filter redundant patterns except when
    `NOUNIQUE` is enabled, this is so they can better act like Bash when `NOUNIQUE` is enabled.
-   **FIX**: `BRACE` is now processed before `SPLIT` in order to fix a number of edge cases.
-   **FIX**: `RAWCHARS` was inconsistently applied at different times depending on what was calling it. It is now
    applied first followed by `BRACE`, `SPLIT`, and finally `GLOBTILDE`.

## 5.1.0

-   **NEW**: Add new parameter to `glob` related functions (except in `pathlib`) called `root_dir` that allows a user to
    specify a different working directory with either a string or path-like object. Path-like inputs are only supported
    on Python 3.6+.
-   **NEW**: Support path-like objects for `globmatch` and `globfilter` path inputs. Path-like inputs are only supported
    on Python 3.6+.
-   **FIX**: Filter functions should not alter the slashes of files it filters. Filtered strings and paths should be
    returned unaltered.

## 5.0.3

-   **FIX**: Rework `glob` relative path handling so internally it is indistinguishable from when it is given no
    relative path and uses the current working directory. This fixes an issue where `pathlib` couldn't handle negate
    patterns properly (`!negate`).

## 5.0.2

-   **FIX**: Fix case where a `GLOBSTAR` pattern, followed by a slash, was not disabling `MATCHBASE`.
-   **FIX**: Fix `pathlib` relative path resolution in glob implementations.

## 5.0.1

-   **FIX**: In `glob`, avoid using up too many file descriptors by acquiring all file/folder names under a directory in
    one batch before recursing into other folders.

## 5.0

-   **NEW**: Add `wcmatch.pathlib` which contains `pathlib` variants that uses `wcmatch.glob` instead of the default
    Python glob.
-   **NEW**: `escape` and `raw_escape` can manually be forced to use Windows or Linux/Unix logic via the keyword only
    argument by setting to `False` or `True` respectively. The default is `None` which will auto detect the system.
-   **NEW**: The deprecated flag `FORCECASE` has now been removed.
-   **NEW**: The deprecated functions `globsplit` and `fnsplit` have been removed.
-   **NEW**: The deprecated variables `version` and `version_info` have been removed.

## 4.3.1

-   **FIX**: Regression for root level literal matches in `glob`.
-   **FIX**: Bug where `glob` would mistakenly abort if a pattern started with a literal file or directory and could not
    match a file or directory. This caused subsequent patterns in the chain to not get evaluated.

## 4.3.0

-   **NEW**: Add `CASE` flag which allows for case sensitive paths on Linux, macOS, and Windows. Windows drive letters
    and UNC `//host-name/share-name/` portion are still treated insensitively, but all directories will be treated with
    case sensitivity.
-   **NEW**: With the recent addition of `CASE` and `FORCEUNIX`, `FORCECASE` is no longer needed. Deprecate `FORCECASE`
    which will be removed at some future point.

## 4.2.0

-   **NEW**: Drop Python 3.4 support.
-   **NEW**: Add flags `FORCEWIN` and `FORCEUNIX` to force Windows or Linux/Unix path logic on commands that do not
    access the file system: `translate`, `fnmatch`, `filter`, `globmatch`, `globfilter`, etc. These flags will not work
    with `glob`, `iglob` or with the `WcMatch` class. It also will not work when using the `REALPATH` flag with things
    like `fnmatch`, `filter`, `globmatch`, `globfilter`.
-   **FIX**: `glob` corner case where the first folder, if defined as a literal name (not a magic pattern), would not be
    treated properly if `IGNORECASE` was enabled in Linux.

## 4.1.0

-   **NEW**: Add `WcMatch.is_aborted`.
-   **FIX**: Remove deprecation of `kill` and `reset` in `WcMatch`. There are legitimate reasons to not deprecate
    killing via `kill` instead of simply breaking.
-   **FIX**: If for any reason, a file exists, but fails "is directory" check, consider it as a file.

## 4.0.1

-   **FIX**: Fix regression with exclusion patterns that use braces in `glob`.
-   **FIX**: Translate functions should have `NODIR` patterns exclude if matched not exclude if not matched.

## 4.0

-   **NEW**: Deprecated `WcMatch` class methods `kill` and `reset`. `WcMatch` should be broken with a simple `break`
    statement instead.
-   **NEW**: Add a new flag `MARK` to force `glob` to return directories with a trailing slash.
-   **NEW**: Add `MATCHBASE` that causes glob related functions and `WcMatch`, when the pattern has no slashes in it, to
    seek for any file anywhere in the tree with a matching basename.
-   **NEW**: Add `NODIR` that causes `glob` matchers and crawlers to only match and return files.
-   **NEW**: Exclusion patterns (enabled with `NEGATE`) now always enable `DOTALL` in the exclusion patterns. They also
    will match symlinks in `**` patterns. Only non `NEGATE` patterns that are paired with a `NEGATE` pattern are subject
    to symlinks and dot rules. Exclusion patterns themselves allow dots and symlinks to make filtering easier.
-   **NEW**: Exclusion patterns no longer provide a default inclusion pattern if one is not specified. Exclusion
    patterns are meant to filter the results of inclusion patterns. You can either use the `SPLIT` flag and provide an
    inclusion pattern with your default ('default_pattern|!exclusion'), or feed in a list of multiple patterns instead
    of a single string (`['inclusion', '!exclusion']`). If you really need the old behavior, you can use the `NEGATEALL`
    flag which will provide a default inclusion pattern that matches all files.
-   **NEW**: Translate now outputs exclusion patterns so that if they match, the file is excluded. This is opposite
    logic to how it used to be, but is more efficient.
-   **FIX**: An empty pattern in `glob` should not match slashes.

## 3.0.2

-   **FIX**: Fix an offset issue when processing an absolute path pattern in `glob` on Linux or macOS.
-   **FIX**: Fix an issue where the `glob` command would use `GLOBSTAR` logic on `**` even when `GLOBSTAR` was disabled.

## 3.0.1

-   **FIX**: In the `WcMatch` class, defer hidden file check until after the file or directory is compared against
    patterns to potentially avoid calling hidden if the pattern doesn't match. The reduced `lstat` calls improve
    performance.

## 3.0

-   **NEW**: `globsplit` and `fnsplit` have been deprecated. Users are encouraged to use the new `SPLIT` flag to allow
    functions to use multiple wildcard paths delimited by `|`.
-   **NEW**: `globmatch` and `globfilter` will now parse provided paths as real paths if the new `REALPATH` flag is set.
    This has the advantage of allowing the commands to be aware of symlinks and properly apply related logic (whether to
    follow the links or not). It also helps to clarify ambiguous cases where it isn't clear if a file path references a
    directory because the trailing slash was omitted. It also allows the command to be aware of Windows drives evaluate
    the path in proper context compared to the current working directory.
-   **NEW**: `WcMatch` class no longer accepts the `recursive` or `show_hidden` parameter, instead the `RECURSIVE` or
    `HIDDEN` flag must be used.
-   **NEW**: `WcMatch` class now can search symlink directories with the new `SYMLINK` flag.
-   **NEW**: `glob` and `iglob` functions now behave like Bash 5.0 in regards to symlinks in `GLOBSTAR` (`**`).
    `GLOBSTAR` will ignore symlink directories. This affects other functions such as `globmatch` and `globfilter` when
    the `REALPATH` flag is enabled.
-   **NEW**: New flag called `FOLLOW` was added to force related `glob` commands to recognize and follow symlink
    directories.
-   **FIX**: Fix `glob` regression where inverse patterns such as `!**/test/**` would allow a directory `base/test` to
    match when it should have excluded it.
-   **FIX**: `glob` should handle root paths (`/`) properly, and on Windows, it should assume the drive of the current
    working directory.

## 2.2.1

-   **FIX**: `EXTMATCH`/`EXTGLOB` should allow literal dots and should not treat dots like sequences do.
-   **FIX**: Fix `!(...)` extended match patterns in `glob` and `globmatch` so that they properly match `.` and `..` if
    their pattern starts with `.`.
-   **FIX**: Fix `!(...)` extended match patterns so that they handle path separators correctly.
-   **FIX**: Patterns such as `?` or `[.]` should not trigger matching directories `.` and `..` in `glob` and
    `globmatch`.

## 2.2.0

-   **NEW**: Officially support Python 3.8.

## 2.1.0

-   **NEW**: Deprecate `version` and `version_info` in favor of the more standard `__version__` and `__version_info__`.
-   **FIX**: Fix issue where exclusion patterns would trigger before end of path.
-   **FIX**: Fix `GLOBSTAR` regular expression pattern issues.

## 2.0.3

-   **FIX**: In `glob`, properly handle files in the current working directory when give a literal pattern that matches
    it.

## 2.0.2

-   **FIX**: `wcmatch` override events (`on_error` and `on_skip`) should verify the return  is **not None** and not
    **not falsy**.

## 2.0.1

-   **FIX**: Can't install due to requirements being assigned to setup opposed to install.

## 2.0

/// danger | Breaking Changes
Version 2.0 introduces breaking changes in regards to flags.  This is meant to bring about consistency amongst the
provided libraries. Flag names have been changed in some cases, and logic has been inverted in some cases.
///

-   **NEW**: Glob's `NOBRACE`, `NOGLOBSTAR`, and `NOEXTGLOB` flags are now `BRACE`, `GLOBSTAR`, and `EXTGLOB` and now
    enable the features instead of disabling the features. This logic matches the provided `fnmatch` and `wcmatch`.
-   **NEW**: Glob's `DOTGLOB` and `EXTGLOB` also have the respective aliases `DOTMATCH` and `EXTMATCH` to provide
    consistent flags across provided libraries, but the `GLOB` variants that match Bash's feature names can still be
    used.
-   **NEW**: `fnmatch`'s `PERIOD` flag has been replaced with `DOTMATCH` with inverted logic from what was originally
    provided.
-   **NEW**: Documentation exposes the shorthand form of flags: `FORCECASE` --> `F`, etc.
-   **FIX**: Wcmatch always documented that it had the flag named `EXTMATCH`, but internally it was actually `EXTGLOB`,
    this was a bug though. `EXTMATCH` is now the documented and the actual flag to use.

## 1.0.2

-   **FIX**: Officially support Python 3.7.

## 1.0.1

-   **FIX**: Ensure that all patterns in `glob` that have a directory preceding `**` but also end with `**` returns the
    preceding directory.
-   **FIX**: Fix byte conversion in path normalization.
-   **FIX**: Ensure POSIX character classes, when at the start of a sequence, properly have hyphens escaped following
    it. `[[:ascii:]-z]` should convert to `[\x00-\x7f\\-b]` not `[\x00-\x7f-b]`.
-   **FIX**: Fix an issue where we would fail because we couldn't covert raw characters even though raw character
    parsing was disabled.
-   **FIX**: Better default for file patterns.  Before if no pattern was provided for files, `'*'` was assumed, now it
    is `''`, and if `''` is used, all files will be matched. This works better for when full path is enabled as you get
    the same file matching logic.

## 1.0

-   **NEW**: Initial release
