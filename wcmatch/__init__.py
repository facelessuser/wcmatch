"""
Wild Card Match.

A custom implementation of fnmatch.

Licensed under MIT
Copyright (c) 2018 Isaac Muse <isaacmuse@gmail.com>

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
from . import util as _util
from . import __version__

__all__ = (
    "EXTEND", "FORCECASE", "IGNORECASE", "RAWCHARS", "NONEGATE", "PATHNAME", "DOT", "GLOBSTAR",
    "E", "I", "C", "N", "P", "D", "G",
    "translate", "fnmatch", "filter", "split", "FnCrawl", "WcMatch",
    "version", "version_info"
)

version = __version__.version
version_info = __version__.version_info

EXTEND = _wcparse.EXTEND
FORCECASE = _wcparse.FORCECASE
IGNORECASE = _wcparse.IGNORECASE
RAWCHARS = _wcparse.RAWCHARS
NONEGATE = _wcparse.NONEGATE
PATHNAME = _wcparse.PATHNAME
DOT = _wcparse.DOT
GLOBSTAR = _wcparse.GLOBSTAR

E = EXTEND
F = FORCECASE
I = IGNORECASE
C = RAWCHARS
N = NONEGATE
P = PATHNAME
D = DOT
G = GLOBSTAR


def split(pattern, flags=0):
    """Split pattern by '|'."""

    return _wcparse.Split(pattern, flags).parse()


@_functools.lru_cache(maxsize=256, typed=True)
def _compile(pattern, flags):  # noqa A001
    """Compile patterns."""

    p1, p2 = translate(pattern, flags)

    if p1 is not None:
        p1 = _re.compile(p1)
    if p2 is not None:
        p2 = _re.compile(p2)
    return WcMatch(p1, p2)


def translate(pattern, flags=0):
    """Translate fnmatch pattern counting `|` as a separator and `-` as a negative pattern."""

    return _wcparse.Parser(
        tuple(pattern) if not isinstance(pattern, (str, bytes)) else (pattern,),
        flags
    ).parse()


def fnmatch(filename, pattern, flags=0):
    """
    Check if filename matches pattern.

    By default case sensitivity is determined by the filesystem,
    but if `case_sensitive` is set, respect that instead.
    """

    return _compile(
        tuple(pattern) if not isinstance(pattern, (str, bytes)) else (pattern,),
        flags & _wcparse.FLAG_MASK
    ).match(_wcparse._norm_slash(filename))


def filter(filenames, pattern, flags=0):  # noqa A001
    """Filter names using pattern."""

    matches = []

    obj = _compile(
        tuple(pattern) if not isinstance(pattern, (str, bytes)) else (pattern,),
        flags & _wcparse.FLAG_MASK
    )

    for filename in filenames:
        filename = _wcparse._norm_slash(filename)
        if obj.match(filename):
            matches.append(filename)
    return matches


def iglob(pattern, flags):
    """Glob."""

    yield from Glob(pattern, flags).glob()


def glob(pattern, flags):
    """Glob."""

    return list(Glob(pattern, flags).glob())


class Glob(object):
    """Glob patterns."""

    def __init__(self, pattern, flags=0):
        """Init the directory walker object."""

        self.flags = flags | PATHNAME
        if self.flags & NONEGATE:
            self.flags ^= NONEGATE
        self.globstar = bool(self.flags & GLOBSTAR)
        self.is_bytes = isinstance(pattern, bytes)
        self.pattern = _wcparse.GlobSplit(pattern, flags).parse()

    def _is_globstar(self, name):
        """Check if rescursive globstar."""

        return self.globstar and name in (b'**', '**')

    def _glob_shallow(self, curdir, dir_only=False):
        """Non recursive directory glob."""

        try:
            if _util.PY36:
                with _os.scandir(curdir) as scan:
                    for f in scan:
                        try:
                            if not dir_only or f.is_dir():
                                yield f.name
                        except OSError:
                            pass
            else:
                for f in _os.listdir(curdir):
                    is_dir = _os.path.isdir(_os.path.join(curdir, f))
                    if not dir_only or is_dir:
                        yield f
        except OSError:
            pass

    def _glob_deep(self, curdir, dir_only=False):
        """Recursive directory glob."""

        try:
            if _util.PY36:
                with _os.scandir(curdir) as scan:
                    for f in scan:
                        try:
                            if not dir_only or f.is_dir():
                                yield curdir, f.name
                            if f.is_dir():
                                yield from self._glob_deep(_os.path.join(curdir, f.name), dir_only)
                        except OSError:
                            pass
            else:
                for f in _os.listdir(curdir):
                    path = _os.path.join(curdir, f)
                    is_dir = _os.path.isdir(path)
                    if not dir_only or is_dir:
                        yield curdir, f
                    if is_dir:
                        yield from self._glob_deep(path, dir_only)
        except OSError:
            pass

    def _glob(self, curdir, this, rest):
        """Handle glob flow."""

        is_magic = this[1]
        is_dir = this[2]
        target = this[0]

        if not is_dir:
            if is_magic:
                if self._is_globstar(target):
                    for dirname, base in self._glob_deep(curdir):
                        yield _os.path.join(dirname, base)
                else:
                    targets = tuple(self._glob_shallow(curdir))
                    for f in filter(targets, target, self.flags):
                        yield _os.path.join(curdir, f)
            else:
                path = _os.path.join(curdir, target)
                if _os.path.lexists(path):
                    yield path
        else:
            this = rest.pop(0) if rest else None
            if is_magic:
                if self._is_globstar(target):
                    for dirname, base in self._glob_deep(curdir, True):
                        path = _os.path.join(dirname, base)
                        if this:
                            yield from self._glob(path, this, rest[:])
                        else:
                            yield path
                else:
                    targets = list(self._glob_shallow(curdir, True))
                    for f in filter(targets, target, self.flags):
                        path = _os.path.join(curdir, f)
                        if this:
                            yield from self._glob(path, this, rest)
                        else:
                            yield path
            else:
                path = _os.path.join(curdir, target)
                if _os.path.isdir(path):
                    if this:
                        yield from self._glob(path, this, rest)
                    else:
                        yield path

    def glob(self):
        """Starts off the glob iterator."""
        if self.is_bytes:
            curdir = bytes(_os.curdir, 'ASCII')
        else:
            curdir = _os.curdir

        if self.pattern:
            if not self.pattern[0][1]:
                # Is Directory
                this = self.pattern[0]
                curdir = this[0]
                if this[2]:
                    # Glob this directory if it exists
                    if _os.path.isdir(curdir):
                        rest = self.pattern[1:]
                        this = rest.pop(0)
                        yield from self._glob(curdir, this, rest)
                else:
                    # Return file if exits and finish.
                    if _os.path.lexists(curdir):
                        yield curdir
            else:
                rest = self.pattern[:]
                this = rest.pop(0)
                yield from self._glob(curdir, this, rest)


class FnCrawl(object):
    """Walk the directory."""

    def __init__(self, *args, **kwargs):
        """Init the directory walker object."""

        args = list(args)
        self._skipped = 0
        self._abort = False
        self.directory = _wcparse._norm_slash(args.pop(0))
        self.file_pattern = args.pop(0) if args else kwargs.pop('file_pattern', '')
        self.exclude_pattern = args.pop(0) if args else kwargs.pop('exclude_pattern', '')
        self.recursive = args.pop(0) if args else kwargs.pop('recursive', False)
        self.show_hidden = args.pop(0) if args else kwargs.pop('show_hidden', True)
        self.flags = args.pop(0) if args else kwargs.pop('flags', 0)
        self.pathname = bool(self.flags & PATHNAME)
        if self.pathname:
            self.flags ^= PATHNAME

        self.on_init(*args, **kwargs)
        self.file_check, self.folder_exclude_check = self._compile(self.file_pattern, self.exclude_pattern)

    def _compile_wildcard(self, patterns, force_default=False, pathname=False):
        """Compile or format the wildcard inclusion/exclusion pattern."""

        pattern = None
        flags = self.flags
        if self.pathname:
            flags |= PATHNAME
        return _compile(tuple(patterns), self.flags) if patterns else pattern

    def _compile(self, file_pattern, folder_exclude_pattern):
        """Compile patterns."""

        if not isinstance(file_pattern, WcMatch):
            # Ensure file pattern is not empty
            if (
                file_pattern is None or
                (isinstance(file_pattern, (str, bytes)) and not file_pattern)
            ):
                file_pattern = ('*',)

            # Ensure if pattern is a string that it is wrapped in something iterable
            if isinstance(file_pattern, (str, bytes)):
                file_pattern = (file_pattern,)

            # If it is an array of empty strings, assign a good default.
            if not any(file_pattern):
                file_pattern = ('*',)

            file_pattern = self._compile_wildcard(file_pattern)

        if not isinstance(folder_exclude_pattern, WcMatch):

            # Ensure if pattern is a string that it is wrapped in something iterable
            if folder_exclude_pattern and isinstance(folder_exclude_pattern, (str, bytes)):
                folder_exclude_pattern = (folder_exclude_pattern,)

            folder_exclude_pattern = self._compile_wildcard(folder_exclude_pattern)

        return file_pattern, folder_exclude_pattern

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
        fullpath = _os.path.join(base, name)
        if not self.recursive or self._is_hidden(fullpath):
            valid = False
        elif self.folder_exclude_check is not None:
            valid = not self.folder_exclude_check.match(fullpath if self.pathname else name)
        return self.on_validate_directory(base, name) if valid else valid

    def on_init(self, *args, **kwargs):
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

    def match(self):
        """Run the directory walker."""

        return list(self.imatch())

    def imatch(self):
        """Run the directory walker as iterator."""

        self._skipped = 0
        for f in self.walk():
            yield f
