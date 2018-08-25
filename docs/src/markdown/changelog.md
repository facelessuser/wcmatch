# Changelog

## 2.0.0

!!! danger "Breaking Changes"
    Version 2.0.0 introduces breaking changes in regards to flags.  This is meant to bring about consistency amongst the provided libraries. Flag names have been changed in some cases, and logic has been inverted in some cases.

- **NEW**: Glob's `NOBRACE`, `NOGLOBSTAR`, and `NOEXTGLOB` flags are now `BRACE`, `GLOBSTAR`, and `EXTGLOB` and now enable the features instead of disabling the features. This logic matches the provided fnmatch and wcmatch.
- **NEW**: Fnmatch's `PERIOD` flag has been replaced with `DOTMATCH` (and the alias `DOTGLOB`) with inverted logic from what was originally provided.
- **NEW**: The libraries glob, fnmatch, and wcmatch libraries allow for the flag `EXTGLOB` or the alias `EXTMATCH` and the flag `DOTGLOB` or alias `DOTMATCH` (where applicable). If people are used to using `EXTMATCH` for fnmatch and `EXTGLOB` for glob, they are free to do so, or they could use `EXTMATCH` for all of the libraries, etc.

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
