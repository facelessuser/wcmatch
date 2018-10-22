"""
Wild Card Match.

A custom implementation of `glob`.

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
import os
import sys
import functools
from . import _wcparse
from . import util

__all__ = (
    "FORCECASE", "IGNORECASE", "RAWCHARS", "DOTGLOB", "DOTMATCH",
    "EXTGLOB", "EXTMATCH", "GLOBSTAR", "NEGATE", "MINUSNEGATE", "BRACE",
    "F", "I", "R", "D", "E", "G", "N", "M",
    "iglob", "glob", "globsplit", "globmatch", "globfilter", "escape"
)

# We don't use `util.platform` only because we mock it in tests,
# and `scandir` will not work with bytes on the wrong system.
WIN = sys.platform.startswith('win')
NO_SCANDIR_WORKAROUND = util.PY36

F = FORCECASE = _wcparse.FORCECASE
I = IGNORECASE = _wcparse.IGNORECASE
R = RAWCHARS = _wcparse.RAWCHARS
D = DOTGLOB = DOTMATCH = _wcparse.DOTMATCH
E = EXTGLOB = EXTMATCH = _wcparse.EXTMATCH
G = GLOBSTAR = _wcparse.GLOBSTAR
N = NEGATE = _wcparse.NEGATE
M = MINUSNEGATE = _wcparse.MINUSNEGATE
B = BRACE = _wcparse.BRACE

FLAG_MASK = (
    FORCECASE |
    IGNORECASE |
    RAWCHARS |
    DOTMATCH |
    EXTMATCH |
    GLOBSTAR |
    NEGATE |
    MINUSNEGATE |
    BRACE
)


def _flag_transform(flags):
    """Transform flags to glob defaults."""

    # Here we force `PATHNAME` and disable negation `NEGATE`
    flags = (flags & FLAG_MASK) | _wcparse.PATHNAME
    return flags


class Glob(object):
    """Glob patterns."""

    def __init__(self, pattern, flags=0):
        """Initialize the directory walker object."""

        self.flags = _flag_transform(flags)
        self.dot = bool(self.flags & DOTMATCH)
        self.negate = bool(self.flags & NEGATE)
        self.globstar = bool(self.flags & _wcparse.GLOBSTAR)
        self.braces = bool(self.flags & _wcparse.BRACE)
        self.case_sensitive = _wcparse.get_case(self.flags) and not util.platform() == "windows"
        self.is_bytes = isinstance(pattern[0], bytes)
        self.specials = (b'.', b'..') if self.is_bytes else ('.', '..')
        self.empty = b'' if self.is_bytes else ''
        self.current = b'.' if self.is_bytes else '.'
        self._parse_patterns(pattern)
        if util.platform() == "windows":
            self.flags |= _wcparse._FORCEWIN
            self.sep = (b'\\', '\\')
        else:
            self.sep = (b'/', '/')

    def _parse_patterns(self, pattern):
        """Parse patterns."""

        self.pattern = []
        self.npattern = []
        for p in pattern:
            if _wcparse.is_negative(p, self.flags):
                self.npattern.append(
                    _wcparse.compile(list(_wcparse.expand_braces(p, self.flags)), self.flags)
                )
            else:
                self.pattern.extend(
                    _wcparse.WcPathSplit(x, self.flags).split() for x in _wcparse.expand_braces(p, self.flags)
                )
        if not self.pattern and self.npattern:
            self.pattern.append(_wcparse.WcPathSplit((b'**' if self.is_bytes else '**'), self.flags).split())

    def _is_hidden(self, name):
        """Check if is file hidden."""

        return not self.dot and name[0:1] in (b'.', '.')

    def _is_this(self, name):
        """Check if "this" directory `.`."""

        return name in (b'.', '.') or name in self.sep

    def _is_parent(self, name):
        """Check if `..`."""

        return name in (b'..', '..')

    def _is_excluded(self, path):
        """Check if file is excluded."""

        excluded = False
        for n in self.npattern:
            excluded = not n.match(path)
            if excluded:
                break
        return excluded

    def _match_literal(self, a, b=None):
        """Match two names."""

        return a.lower() == b if not self.case_sensitive else a == b

    def _get_matcher(self, target):
        """Get deep match."""

        if target is None:
            matcher = None
        elif isinstance(target, (str, bytes)):
            # Plain text match
            if not self.case_sensitive:
                match = target.lower()
            else:
                match = target
            matcher = functools.partial(self._match_literal, b=match)
        else:
            # File match pattern
            matcher = target.match
        return matcher

    def _glob_shallow(self, curdir, matcher, dir_only=False):
        """Non recursive directory glob."""

        scandir = self.current if not curdir else curdir

        # Python will never return . or .., so fake it.
        if os.path.isdir(scandir):
            for special in self.specials:
                if matcher(special):
                    yield os.path.join(curdir, special)

        try:
            if NO_SCANDIR_WORKAROUND:
                # Our current directory can be empty if the path starts with magic,
                # But we don't want to return paths with '.', so just use it to list
                # files, but use '' when constructing the path.
                with os.scandir(scandir) as scan:
                    for f in scan:
                        try:
                            if (not dir_only or f.is_dir()) and matcher(f.name):
                                yield os.path.join(curdir, f.name)
                        except OSError:  # pragma: no cover
                            pass
            else:
                for f in os.listdir(scandir):
                    is_dir = os.path.isdir(os.path.join(curdir, f))
                    if (not dir_only or is_dir) and matcher(f):
                        yield os.path.join(curdir, f)
        except OSError:  # pragma: no cover
            pass

    def _glob_deep(self, curdir, matcher, dir_only=False):
        """Recursive directory glob."""

        scandir = self.current if not curdir else curdir

        # Python will never return . or .., so fake it.
        if os.path.isdir(scandir) and matcher is not None:
            for special in self.specials:
                if matcher(special):
                    yield os.path.join(curdir, special)

        try:
            if NO_SCANDIR_WORKAROUND:
                # Our current directory can be empty if the path starts with magic,
                # But we don't want to return paths with '.', so just use it to list
                # files, but use '' when constructing the path.
                with os.scandir(scandir) as scan:
                    for f in scan:
                        try:
                            # Quicker to just test this way than to run through `fnmatch`.
                            if self._is_hidden(f.name):
                                continue
                            path = os.path.join(curdir, f.name)
                            if (not dir_only or f.is_dir()) and (matcher is None or matcher(f.name)):
                                yield path
                            if f.is_dir():
                                yield from self._glob_deep(path, matcher, dir_only)
                        except OSError:  # pragma: no cover
                            pass
            else:
                for f in os.listdir(scandir):
                    # Quicker to just test this way than to run through `fnmatch`.
                    if self._is_hidden(f):
                        continue
                    path = os.path.join(curdir, f)
                    is_dir = os.path.isdir(path)
                    if (not dir_only or is_dir) and (matcher is None or matcher(f)):
                        yield path
                    if is_dir:
                        yield from self._glob_deep(path, matcher, dir_only)
        except OSError:  # pragma: no cover
            pass

    def _glob(self, curdir, this, rest):
        """
        Handle glob flow.

        There are really only a couple of cases:

        - File name.
        - File name pattern (magic).
        - Directory.
        - Directory name pattern (magic).
        - Extra slashes `////`.
        - `globstar` `**`.
        """

        is_magic = this.is_magic
        dir_only = this.dir_only
        target = this.pattern
        is_globstar = this.is_globstar

        if is_magic and is_globstar:
            # Glob star directory `**`.

            # Throw away multiple consecutive `globstars`
            # and acquire the pattern after the `globstars` if available.
            this = rest.pop(0) if rest else None
            globstar_end = this is None
            while this and not globstar_end:
                if this:
                    dir_only = this.dir_only
                    target = this.pattern
                if this and this.is_globstar:
                    this = rest.pop(0) if rest else None
                    if this is None:
                        globstar_end = True
                else:
                    break

            if globstar_end:
                target = None

            # We match `**/next` during `_glob_deep`, so what ever comes back,
            # we will send back through `_glob` with pattern after `next` (`**/next/after`).
            # So grab `after` if available.
            this = rest.pop(0) if rest else None

            # Deep searching is the unique case where we
            # might feed in a `None` for the next pattern to match.
            # Deep glob will account for this.
            matcher = self._get_matcher(target)

            # If our pattern ends with `curdir/**`, but does not start with `**` it matches zero or more,
            # so it should return `curdir/`, signifying `curdir` + no match.
            # If a pattern follows `**/something`, we always get the appropriate
            # return already, so this isn't needed in that case.
            # There is one quirk though with Bash, if `curdir` had magic before `**`, Bash
            # omits the trailing `/`. We don't worry about that.
            if globstar_end and curdir:
                yield os.path.join(curdir, self.empty)

            # Search
            for path in self._glob_deep(curdir, matcher, dir_only):
                if this:
                    yield from self._glob(path, this, rest[:])
                else:
                    yield path

        elif not dir_only:
            # Files: no need to recursively search at this point as we are done.
            matcher = self._get_matcher(target)
            yield from self._glob_shallow(curdir, matcher)

        else:
            # Directory: search current directory against pattern
            # and feed the results back through with the next pattern.
            this = rest.pop(0) if rest else None
            matcher = self._get_matcher(target)
            for path in self._glob_shallow(curdir, matcher, True):
                if this:
                    yield from self._glob(path, this, rest[:])
                else:
                    yield path

    def _get_starting_paths(self, curdir):
        """
        Get the starting location.

        For case sensitive paths, we have to "glob" for
        it first as Python doesn't like for its users to
        think about case. By scanning for it, we can get
        the actual casing and then compare.
        """

        results = [curdir]

        if not self._is_parent(curdir) and not self._is_this(curdir):
            fullpath = os.path.abspath(curdir)
            basename = os.path.basename(fullpath)
            dirname = os.path.dirname(fullpath)
            if basename:
                matcher = self._get_matcher(basename)
                results = [os.path.basename(name) for name in self._glob_shallow(dirname, matcher, self)]

        return results

    def glob(self):
        """Starts off the glob iterator."""

        if self.is_bytes:
            curdir = bytes(os.curdir, 'ASCII')
        else:
            curdir = os.curdir

        for pattern in self.pattern:
            # If the pattern ends with `/` we return the files ending with `/`.
            dir_only = pattern[-1].dir_only if pattern else False

            if pattern:
                if not pattern[0].is_magic:
                    # Path starts with normal plain text
                    # Lets verify the case of the starting directory (if possible)
                    this = pattern[0]

                    curdir = this[0]

                    if not os.path.isdir(curdir) and not os.path.lexists(curdir):
                        return

                    # Make sure case matches, but running case insensitive
                    # on a case sensitive file system may return more than
                    # one starting location.
                    results = [curdir] if this.is_drive else self._get_starting_paths(curdir)
                    if not results:
                        if not dir_only and os.path.lexists(curdir):
                            # There is no directory with this name,
                            # but we have a file and no directory restriction
                            yield curdir
                        return

                    if this.dir_only:
                        # Glob these directories if they exists
                        for start in results:
                            if os.path.isdir(start):
                                rest = pattern[1:]
                                if rest:
                                    this = rest.pop(0)
                                    for match in self._glob(curdir, this, rest):
                                        if not self._is_excluded(match):
                                            yield os.path.join(match, self.empty) if dir_only else match
                                elif not self._is_excluded(curdir):
                                    yield os.path.join(curdir, self.empty) if dir_only else curdir
                    else:
                        # Return the file(s) and finish.
                        for start in results:
                            if os.path.lexists(start) and not self._is_excluded(start):
                                yield os.path.join(start, self.empty) if dir_only else start
                else:
                    # Path starts with a magic pattern, let's get globbing
                    rest = pattern[:]
                    this = rest.pop(0)
                    for match in self._glob(curdir if not curdir == self.current else self.empty, this, rest):
                        if not self._is_excluded(match):
                            yield os.path.join(match, self.empty) if dir_only else match


def iglob(patterns, *, flags=0):
    """Glob."""

    yield from Glob(util.to_tuple(patterns), flags).glob()


def glob(patterns, *, flags=0):
    """Glob."""

    return list(iglob(util.to_tuple(patterns), flags=flags))


def globsplit(pattern, *, flags=0):
    """Split pattern by '|'."""

    return _wcparse.WcSplit(pattern, _flag_transform(flags)).split()


def translate(patterns, *, flags=0):
    """Translate glob pattern."""

    return _wcparse.translate(patterns, _flag_transform(flags))


def globmatch(filename, patterns, *, flags=0):
    """
    Check if filename matches pattern.

    By default case sensitivity is determined by the file system,
    but if `case_sensitive` is set, respect that instead.
    """

    flags = _flag_transform(flags)
    if not _wcparse.is_unix_style(flags):
        filename = util.norm_slash(filename)
    return _wcparse.compile(patterns, flags).match(filename)


def globfilter(filenames, patterns, *, flags=0):
    """Filter names using pattern."""

    matches = []

    flags = _flag_transform(flags)
    unix = _wcparse.is_unix_style(flags)
    obj = _wcparse.compile(patterns, flags)

    for filename in filenames:
        if not unix:
            filename = util.norm_slash(filename)
        if obj.match(filename):
            matches.append(filename)
    return matches


def raw_escape(pattern, unix=False):
    """Apply raw character transform before applying escape."""

    pattern = util.norm_pattern(pattern, False, True)
    return escape(pattern, unix)


def escape(pattern, unix=False):
    """Escape."""

    is_bytes = isinstance(pattern, bytes)
    replace = br'\\\1' if is_bytes else r'\\\1'
    win = util.platform() == "windows"
    if win and not unix:
        magic = _wcparse.RE_BWIN_MAGIC if is_bytes else _wcparse.RE_WIN_MAGIC
    else:
        magic = _wcparse.RE_BMAGIC if is_bytes else _wcparse.RE_MAGIC

    # Handle windows drives special.
    # Windows drives are handled special internally.
    # So we shouldn't escape them as we'll just have to
    # detect and undo it later.
    drive = b'' if is_bytes else ''
    if win and not unix:
        m = (_wcparse.RE_BWIN_PATH if is_bytes else _wcparse.RE_WIN_PATH).match(pattern)
        if m:
            drive = m.group(0)
    pattern = pattern[len(drive):]

    return drive + magic.sub(replace, pattern)
