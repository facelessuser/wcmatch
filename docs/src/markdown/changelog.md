# Changelog

## 3.0.0

- **NEW**: `globmatch` and `globfilter` will now parse a file path as real path if the new `REALPATH` flag is set. Also affects glob pattern splitting as well.
- **NEW**: `WcMatch` class no longer accepts the `recursive` or `show_hidden` parameter, instead the `RECURSIVE` or `HIDDEN` flag must be used.
- **NEW**: `WcMatch` class now can search symlink directories with the new `SYMLINK` flag.
- **NEW**: `glob` and `iglob` functions now behave like Bash 5.0 in regards to symlinks in `GLOBSTAR` (`**`). `GLOBSTAR` will ignore symlink directories. This affects other functions such as `globmatch` and `globfilter` when `REALPATH` flag is enabled.
- **NEW**: New flag called `FOLLOW` was added to force `glob` and `iglob` to recognize and follow symlink directories to restore previous behavior if desired.
- **FIX**: Fix `glob` regression where inverse patterns such as `**/test/**` would match a directory `base/test` when it should have excluded it.

## 2.2.1

- **FIX**: `EXTMATCH`/`EXTGLOB` should allow literal dots and should not treat dots like sequences do.
- **FIX**: Fix `!(...)` extended match patterns in `glob` and `globmatch` so that they properly match `.` and `..` if their pattern starts with `.`.
- **FIX**: Fix `!(...)` extended match patterns so that they handle path separators correctly.
- **FIX**: Patterns such as `?` or `[.]` should not trigger matching directories `.` and `..` in `glob` and `globmatch`.

## 2.2.0

- **NEW**: Officially support Python 3.8.

## 2.1.0

- **NEW**: Deprecate `version` and `version_info` in favor of the more standard `__version__` and `__version_info__`.
- **FIX**: Fix issue where negated patterns would trigger before end of path.
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
