"""
Wild Card Match.

A custom implementation of fnmatch.

Licensed under MIT
Copyright (c) 2013 - 2018 Isaac Muse <isaacmuse@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
documentation files (the "Software"), to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions
of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED
TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF
CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
IN THE SOFTWARE.
"""
from __future__ import unicode_literals
import os as _os
import re as _re
import functools as _functools
from .wcparse import WcMatch
from . import wcparse as _wcparse
from .file_hidden import is_hidden as _is_hidden
from . import __version__

__all__ = (
    "CASE", "IGNORECASE", "RAW_STRING_ESCAPES", "ESCAPE_CHARS", "NO_EXTRA"
    "translate", "fnmatch", "filter", "FnCrawl", "WcMatch",
    "version", "version_info"
)

version = __version__.version
version_info = __version__.version_info

CASE = _wcparse.CASE
IGNORECASE = _wcparse.IGNORECASE
RAW_STRING_ESCAPES = _wcparse.RAW_STRING_ESCAPES
ESCAPE_CHARS = _wcparse.ESCAPE_CHARS
NO_EXTRA = _wcparse.NO_EXTRA

_CASE_FLAGS = CASE | IGNORECASE


def _get_case(flags):
    """Parse flags for case sensitivity settings."""

    if not bool(flags & _CASE_FLAGS):
        case_sensitive = _wcparse._CASE_FS
    elif flags & CASE and flags & IGNORECASE:
        raise ValueError("Cannot use CASE and IGNORECASE flags together!")
    elif flags & CASE:
        case_sensitive = True
    else:
        case_sensitive = False
    return case_sensitive


@_functools.lru_cache(maxsize=256, typed=True)
def _compile(pattern, flags):  # noqa A001
    """Compile patterns."""

    case_sensitive = _get_case(flags)
    p1, p2 = translate(pattern, flags)

    flags = 0
    if not case_sensitive:
        flags |= _re.I
    if p1 is not None:
        p1 = _re.compile(p1, flags)
    if p2 is not None:
        p2 = _re.compile(p2, flags)
    return WcMatch(p1, p2)


def translate(pattern, flags=0):
    """Translate fnmatch pattern counting `|` as a separator and `-` as a negative pattern."""

    return _wcparse.Parser(pattern, flags).parse()


def fnmatch(filename, pattern, flags=0):
    """
    Check if filename matches pattern.

    By default case sensitivity is determined by the filesystem,
    but if `case_sensitive` is set, respect that instead.
    """

    return _compile(pattern, flags & _wcparse.FLAG_MASK).match(filename)


def filter(filenames, pattern, flags=0):  # noqa A001
    """Filter names using pattern."""

    matches = []

    obj = _compile(pattern, flags & _wcparse.FLAG_MASK)

    for filename in filenames:
        if obj.match(filename):
            matches.append(filename)
    return matches


class FnCrawl(object):
    """Walk the directory."""

    def __init__(self, *args, **kwargs):
        """Init the directory walker object."""

        args = list(args)
        self._skipped = 0
        self._abort = False
        self.directory = args.pop(0)
        self.file_pattern = args.pop(0) if args else kwargs.pop('file_pattern', None)
        self.folder_exclude_pattern = args.pop(0) if args else kwargs.pop('folder_exclude_pattern', None)
        self.recursive = args.pop(0) if args else kwargs.pop('recursive', False)
        self.show_hidden = args.pop(0) if args else kwargs.pop('show_hidden', True)
        self.flags = args.pop(0) if args else kwargs.pop('flags', 0)
        self.file_regex_match = args.pop(0) if args else kwargs.pop('file_regex_match', False)
        self.folder_regex_exclude_match = args.pop(0) if args else kwargs.pop('folder_regex_exclude_match', False)
        self.case_sensitive = _get_case(self.flags)

        self.on_init(*args, **kwargs)
        self.file_check, self.folder_exclude_check = self.on_compile(self.file_pattern, self.folder_exclude_pattern)

    def compile_wildcard(self, string, force_default=False):
        r"""Compile or format the wildcard inclusion\exclusion pattern."""

        pattern = None
        if not string and force_default:
            string = '*'
        return _compile(string, self.flags) if string else pattern

    def compile_regexp(self, string, force_default=False):
        r"""Compile or format the regular expression inclusion\exclusion pattern."""

        pattern = None
        if not string and force_default:
            string = r'.*'
        if string:
            flags = _re.IGNORECASE if not self.case_sensitive else 0
            pattern = _re.compile(string, flags | _re.ASCII)

        return WcMatch(pattern, None)

    def on_compile(self, file_pattern, folder_exclude_pattern):
        """Compile patterns."""

        if not isinstance(file_pattern, WcMatch):
            if self.file_regex_match:
                file_check = self.compile_regexp(file_pattern, force_default=True)
            else:
                file_check = self.compile_wildcard(file_pattern, force_default=True)

        if not isinstance(folder_exclude_pattern, WcMatch):
            if self.folder_regex_exclude_match:
                folder_exclude_check = self.compile_regexp(folder_exclude_pattern)
            else:
                folder_exclude_check = self.compile_wildcard(folder_exclude_pattern)
        return file_check, folder_exclude_check

    def _is_hidden(self, path):
        """Check if file is hidden."""

        return _is_hidden(path) if not self.show_hidden else False

    def _valid_file(self, base, name):
        """Return whether a file can be searched."""

        valid = False
        if self.file_check is not None and not self._is_hidden(_os.path.join(base, name)):
            valid = self.file_check.match(name)
        return self.on_validate_file(base, name) if valid else valid

    def on_validate_file(self, base, name):
        """Validate file override."""

        return True

    def _valid_folder(self, base, name):
        """Return whether a folder can be searched."""

        valid = True
        if not self.recursive or self._is_hidden(_os.path.join(base, name)):
            valid = False
        elif self.folder_exclude_check is not None:
            valid = not self.folder_exclude_check.match(name)
        return self.on_validate_directory(base, name) if valid else valid

    def on_init(self, **kwargs):
        """Handle custom init."""

    def on_validate_directory(self, base, name):
        """Validate folder override."""

        return True

    def on_skip(self, base, name):
        """On skip."""

        return None

    def on_error(self, base, name):
        """On error."""

        return None

    def on_match(self, base, name):
        """On match."""

        return _os.path.join(base, name)

    def get_skipped(self):
        """Get number of skipped files."""

        return self._skipped

    def kill(self):
        """Abort process."""

        self._abort = True

    def reset(self):
        """Revive class from a killed state."""

        self._abort = False

    def walk(self):
        """Start search for valid files."""

        for base, dirs, files in _os.walk(self.directory):
            # Remove child folders based on exclude rules
            for name in dirs[:]:
                try:
                    if not self._valid_folder(base, name):
                        dirs.remove(name)
                except Exception:  # pragma: no cover
                    dirs.remove(name)
                    value = self.on_error(base, name)
                    if value:
                        yield value

                if self._abort:
                    break

            # Seach files if they were found
            if len(files):
                # Only search files that are in the inlcude rules
                for name in files:
                    try:
                        valid = self._valid_file(base, name)
                    except Exception:  # pragma: no cover
                        valid = False
                        value = self.on_error(base, name)
                        if value:
                            yield value

                    if valid:
                        yield self.on_match(base, name)
                    else:
                        self._skipped += 1
                        value = self.on_skip(base, name)
                        if value:
                            yield value

                    if self._abort:
                        break

            if self._abort:
                break

    def run(self):
        """Run the directory walker."""

        self._skipped = 0
        for f in self.walk():
            yield f
