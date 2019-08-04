# Changelog

## 4.2.0

- **NEW**: Add flags `FORCEWIN` and `FORCEUNIX` to force Windows or Linux/Unix path logic on commands that do not access the file system: `translate`, `fnmatch`, `filter`, `globmatch`, `globfilter`, etc. These flags will not work with `glob`, `iglob` or with the `WcMatch` class. It also will not work when using the `REALPATH` flag with things like `fnmatch`, `filter`, `globmatch`, `globfilter`.
- **FIX**: `glob` corner case where the first folder, if defined as a literal name (not a magic pattern), would not be treated properly if `IGNORECASE` was enabled in Linux.

## 4.1.0

- **NEW**: Add `WcMatch.is_aborted`.
- **FIX**: Remove deprecation of `kill` and `reset` in `WcMatch`. There are legitimate reasons to not deprecate killing via `kill` instead of simply breaking.
- **FIX**: If for any reason, a file exists, but fails "is directory" check, consider it as a file.

## 4.0.1

- **FIX**: Fix regression with exclusion patterns that use braces in `glob`.
- **FIX**: Translate functions should have `NODIR` patterns exclude if matched not exclude if not matched.

## 4.0.0

- **NEW**: Deprecated `WcMatch` class methods `kill` and `reset`. `WcMatch` should be broken with a simple `break` statement instead.
- **NEW**: Add a new flag `MARK` to force `glob` to return directories with a trailing slash.
- **NEW**: Add `MATCHBASE` that causes glob glob related functions and `WcMatch`, when the pattern has no slashes in it, to seek for any file anywhere in the tree with a matching basename.
- **NEW**: Add `NODIR` that causes `glob` matchers and crawlers to only match and return files.
- **NEW**: Exclusion patterns (enabled with `NEGATE`) now always enable `DOTALL` in the exclusion patterns. They also will match symlinks in `**` patterns. Only non `NEGATE` patterns that are paired with a `NEGATE` pattern are subject to symlinks and dot rules. Exclusion patterns themselves allow dots and symlinks to make filtering easier.
- **NEW**: Exclusion patterns no longer provide a default inclusion pattern if one is not specified. Exclusion patterns are meant to filter the results of inclusion patterns. You can either use the `SPLIT` flag and provide an inclusion pattern with your default ('default_pattern|!exclusion'), or feed in a list of multiple patterns instead of a single string (`['inclusion', '!exclusion']`). If you really need the old behavior, you can use the `NEGATEALL` flag which will provide a default inclusion pattern that matches all files.
- **NEW**: Translate now outputs exclusion patterns so that if they match, the file is excluded. This is opposite logic to how it used to be, but is more efficient.
- **FIX**: An empty pattern in `glob` should not match slashes.

## 3.0.2

- **FIX**: Fix an offset issue when processing an absolute path pattern in `glob` on Linux or macOS.
- **FIX**: Fix an issue where the `glob` command would use `GLOBSTAR` logic on `**` even when `GLOBSTAR` was disabled.

## 3.0.1

- **FIX**: In the `WcMatch` class, defer hidden file check until after the file or directory is compared against patterns to potentially avoid calling hidden if the pattern doesn't match. The reduced `lstat` calls improve performance.

## 3.0.0

- **NEW**: `globsplit` and `fnsplit` have been deprecated. Users are encouraged to use the new `SPLIT` flag to allow functions to use multiple wildcard paths delimited by `|`.
- **NEW**: `globmatch` and `globfilter` will now parse provided paths as real paths if the new `REALPATH` flag is set. This has the advantage of allowing the commands to be aware of symlinks and properly apply related logic (whether to follow the links or not). It also helps to clarify ambiguous cases where it isn't clear if a file path references a directory because the trailing slash was omitted. It also allows the command to be aware of Windows drives evaluate the path in proper context compared to the current working directory.
- **NEW**: `WcMatch` class no longer accepts the `recursive` or `show_hidden` parameter, instead the `RECURSIVE` or `HIDDEN` flag must be used.
- **NEW**: `WcMatch` class now can search symlink directories with the new `SYMLINK` flag.
- **NEW**: `glob` and `iglob` functions now behave like Bash 5.0 in regards to symlinks in `GLOBSTAR` (`**`). `GLOBSTAR` will ignore symlink directories. This affects other functions such as `globmatch` and `globfilter` when the `REALPATH` flag is enabled.
- **NEW**: New flag called `FOLLOW` was added to force related `glob` commands to recognize and follow symlink directories.
- **FIX**: Fix `glob` regression where inverse patterns such as `!**/test/**` would allow a directory `base/test` to match when it should have excluded it.
- **FIX**: `glob` should handle root paths (`/`) properly, and on Windows, it should assume the drive of the current working directory.

## 2.2.1

- **FIX**: `EXTMATCH`/`EXTGLOB` should allow literal dots and should not treat dots like sequences do.
- **FIX**: Fix `!(...)` extended match patterns in `glob` and `globmatch` so that they properly match `.` and `..` if their pattern starts with `.`.
- **FIX**: Fix `!(...)` extended match patterns so that they handle path separators correctly.
- **FIX**: Patterns such as `?` or `[.]` should not trigger matching directories `.` and `..` in `glob` and `globmatch`.

## 2.2.0

- **NEW**: Officially support Python 3.8.

## 2.1.0

- **NEW**: Deprecate `version` and `version_info` in favor of the more standard `__version__` and `__version_info__`.
- **FIX**: Fix issue where exclusion patterns would trigger before end of path.
- **FIX**: Fix `GLOBSTAR` regular expression pattern issues.

## 2.0.3

- **FIX**: In `glob`, properly handle files in the current working directory when give a literal pattern that matches it.

## 2.0.2

- **FIX**: `wcmatch` override events (`on_error` and `on_skip`) should verify the return  is **not None** and not **not falsy**.

## 2.0.1

- **FIX**: Can't install due to requirements being assigned to setup opposed to install.

## 2.0.0

!!! danger "Breaking Changes"
    Version 2.0.0 introduces breaking changes in regards to flags.  This is meant to bring about consistency amongst the provided libraries. Flag names have been changed in some cases, and logic has been inverted in some cases.

- **NEW**: Glob's `NOBRACE`, `NOGLOBSTAR`, and `NOEXTGLOB` flags are now `BRACE`, `GLOBSTAR`, and `EXTGLOB` and now enable the features instead of disabling the features. This logic matches the provided `fnmatch` and `wcmatch`.
- **NEW**: Glob's `DOTGLOB` and `EXTGLOB` also have the respective aliases `DOTMATCH` and `EXTMATCH` to provide consistent flags across provided libraries, but the `GLOB` variants that match Bash's feature names can still be used.
- **NEW**: `fnmatch`'s `PERIOD` flag has been replaced with `DOTMATCH` with inverted logic from what was originally provided.
- **NEW**: Documentation exposes the shorthand form of flags: `FORCECASE` --> `F`, etc.
- **FIX**: Wcmatch always documented that it had the flag named `EXTMATCH`, but internally it was actually `EXTGLOB`, this was a bug though. `EXTMATCH` is now the documented and the actual flag to use.

## 1.0.2

- **FIX**: Officially support Python 3.7.

## 1.0.1

- **FIX**: Ensure that all patterns in `glob` that have a directory preceding `**` but also end with `**` returns the preceding directory.
- **FIX**: Fix byte conversion in path normalization.
- **FIX**: Ensure POSIX character classes, when at the start of a sequence, properly have hyphens escaped following it. `[[:ascii:]-z]` should convert to `[\x00-\x7f\\-b]` not `[\x00-\x7f-b]`.
- **FIX**: Fix an issue where we would fail because we couldn't covert raw characters even though raw character parsing was disabled.
- **FIX**: Better default for file patterns.  Before if no pattern was provided for files, `'*'` was assumed, now it is `''`, and if `''` is used, all files will be matched. This works better for when full path is enabled as you get the same file matching logic.

## 1.0.0

- Initial release

--8<-- "refs.txt"
