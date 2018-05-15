"""
Wild Card Match.

A custom implementation of glob.

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
import re
from . import fnmatch
from . import util

__all__ = (
    "FORCECASE", "IGNORECASE", "RAWCHARS", "NODOT",
    "EXTEND", "GLOBSTAR", "NONEGATE", "MINUSNEGATE",
    "F", "I", "R", "D", "E", "G", "N", "M",
    "iglob", "glob", "globsplit", "globmatch", "globfilter", "escape"
)

# We don't use util.platform only because we mock it in tests,
# and scandir will not work with bytes on the wrong system.
SCANDIR_WORKAROUND = util.PY36 or (util.PY35 and not sys.platform.startswith('win'))

F = FORCECASE = fnmatch.FORCECASE
I = IGNORECASE = fnmatch.IGNORECASE
R = RAWCHARS = fnmatch.RAWCHARS
D = NODOT = fnmatch.DOT
E = EXTEND = fnmatch.EXTEND
G = GLOBSTAR = fnmatch.GLOBSTAR
N = NONEGATE = fnmatch.NONEGATE
M = MINUSNEGATE = fnmatch.MINUSNEGATE
B = NOBRACE = fnmatch.NOBRACE

FLAG_MASK = (
    FORCECASE |
    IGNORECASE |
    RAWCHARS |
    NODOT |
    EXTEND |
    GLOBSTAR |
    NONEGATE |
    MINUSNEGATE |
    NOBRACE
)

FS_FLAG_MASK = FLAG_MASK ^ (NONEGATE | MINUSNEGATE)

RE_MAGIC = re.compile(r'(^[-!]|[*?(\[|^])')
RE_BMAGIC = re.compile(r'(^[-!]|[*?(\[|^])')


def _flag_transform(flags, full=False):
    """Transform flags to glob defaults."""

    # Here we force PATHNAME and disable negaton with NONEGATE
    if not full:
        flags = (flags & FS_FLAG_MASK) | fnmatch.PATHNAME | NONEGATE
    else:
        flags = (flags & FLAG_MASK) | fnmatch.PATHNAME
    # Enable DOT by default (flipped logic for fnmatch which disables it by default)
    flags ^= NODOT
    return flags


def _magicsplit(pattern, flags):
    """Split on magic sub directory patterns."""

    return Split(pattern, flags).split()


class Split(object):
    """
    Split glob pattern on "magic" file and directories.

    Glob pattern return a list of pieces. Each piece will either
    be consecutive literal file parts or individual glob parts.
    Each part will will contain info regarding whether they are
    a directory pattern or a file pattern and whether the part
    is "magic": ["pattern", is_magic, is_directory]. Is directory
    is determined by a trailing OS separator on the part.

    Example:

        "**/this/is_literal/*magic?/@(magic|part)"

        Would  become:

        [
            ["**", True, True],
            ["this/is_literal/", False, True],
            ["*magic?", True, True],
            ["@(magic|part)", True, True]
        ]
    """

    def __init__(self, pattern, flags):
        """Initialize."""

        self.flags = _flag_transform(flags)
        self.pattern = util.norm_pattern(pattern, True, self.flags & RAWCHARS)
        self.is_bytes = isinstance(pattern, bytes)
        self.extend = bool(flags & EXTEND)
        if util.platform() == "windows":
            self.win_drive_detect = True
            self.bslash_abort = True
            self.sep = '\\'
        else:
            self.win_drive_detect = False
            self.bslash_abort = False
            self.sep = '/'
        self.magic = False
        self.re_magic = RE_MAGIC if not self.is_bytes else RE_BMAGIC

    def is_magic(self, name):
        """Check if name contains magic characters."""

        return self.re_magic.search(name)

    def _sequence(self, i):
        """Handle fnmatch character group."""

        c = next(i)
        if c == '!':
            c = next(i)
        if c in ('^', '-', '['):
            c = next(i)

        while c != ']':
            if c == '\\':
                # Handle escapes
                subindex = i.index
                try:
                    self._references(i, True)
                except fnmatch.PathNameException:
                    raise StopIteration
                except StopIteration:
                    i.rewind(i.index - subindex)
            elif c == '/':
                raise StopIteration
            c = next(i)

    def _references(self, i, sequence=False):
        """Handle references."""

        value = ''

        c = next(i)
        if c == '\\':
            # \\
            if sequence and self.bslash_abort:
                raise fnmatch.PathNameException
            value = c
        elif c == '/':
            # \/
            if sequence:
                raise fnmatch.PathNameException
            i.rewind(1)
        else:
            # \a, \b, \c, etc.
            pass
        return value

    def parse_extend(self, c, i):
        """Parse extended pattern lists."""

        # Start list parsing
        success = True
        index = i.index
        list_type = c
        try:
            c = next(i)
            if c != '(':
                raise StopIteration
            while c != ')':
                c = next(i)

                if self.extend and self.parse_extend(c, i):
                    continue

                if c == '\\':
                    index = i.index
                    try:
                        self._references(i)
                    except StopIteration:
                        i.rewind(i.index - index)
                elif c == '[':
                    index = i.index
                    try:
                        self._sequence(i)
                    except StopIteration:
                        i.rewind(i.index - index)

        except StopIteration:
            success = False
            c = list_type
            i.rewind(i.index - index)

        return success

    def group_by_magic(self, value, l, directory):
        """Group patterns by literals and potential magic patterns."""

        sep = self.sep if directory else ''
        if self.is_magic(value):
            l.append([value, True, directory])
            self.magic = True
        elif self.magic:
            self.magic = False
            l.append([value + sep, False, directory])
        elif l:
            l[-1][0] += value + sep
            l[-1][2] = directory
        else:
            l.append([value + sep, False, directory])

    def split(self):
        """Start parsing the pattern."""

        split_index = []
        parts = []
        start = -1

        pattern = self.pattern.decode('latin-1') if self.is_bytes else self.pattern

        i = util.StringIter(pattern)
        iter(i)
        if self.win_drive_detect:
            m = fnmatch.RE_WIN_PATH.match(pattern)
            if m:
                drive = m.group(0).replace('\\\\', '\\')
                parts.append([drive, False, drive.endswith('\\')])
                start = m.end(0) - 1
                i.advance(start + 1)
        for c in i:

            if self.extend and self.parse_extend(c, i):
                continue

            if c == '\\':
                index = i.index
                value = ''
                try:
                    value = self._references(i)
                    if self.bslash_abort and value == '\\':
                        split_index.append((i.index - 2, 1))
                except StopIteration:
                    i.rewind(i.index - index)
                    if self.bslash_abort and value == '\\':
                        split_index.append((i.index - 1, 0))
            elif c == '/':
                split_index.append((i.index - 1, 0))
            elif c == '[':
                index = i.index
                try:
                    self._sequence(i)
                except StopIteration:
                    i.rewind(i.index - index)

        for split, offset in split_index:
            if self.is_bytes:
                value = pattern[start + 1:split].encode('latin-1')
            else:
                value = pattern[start + 1:split]
            self.group_by_magic(value, parts, True)
            start = split + offset

        if start < len(pattern):
            if self.is_bytes:
                value = pattern[start + 1:].encode('latin-1')
            else:
                value = pattern[start + 1:]
            if value:
                self.group_by_magic(value, parts, False)

        return parts


class Glob(object):
    """Glob patterns."""

    def __init__(self, pattern, flags=0):
        """Init the directory walker object."""

        self.flags = _flag_transform(flags)
        self.dot = bool(self.flags & fnmatch.DOT)
        self.globstar = bool(self.flags & GLOBSTAR)
        self.is_bytes = isinstance(pattern, bytes)
        self.pattern = _magicsplit(pattern, self.flags)
        self.scandir = util.PY36 or (util.PY35 and util.platform() != "windows")

    def _is_globstar(self, name):
        """Check if rescursive globstar."""

        return self.globstar and name in (b'**', '**')

    def _is_hidden(self, name):

        return self.dot and name[0:1] in (b'.', '.')

    def _glob_shallow(self, curdir, matcher, dir_only=False):
        """Non recursive directory glob."""

        try:
            if SCANDIR_WORKAROUND:
                with os.scandir(curdir) as scan:
                    for f in scan:
                        try:
                            if (not dir_only or f.is_dir()) and matcher.match(f.name):
                                yield os.path.join(curdir, f.name)
                        except OSError:
                            pass
            else:
                for f in os.listdir(curdir):
                    is_dir = os.path.isdir(os.path.join(curdir, f))
                    if (not dir_only or is_dir) and matcher.match(f):
                        yield os.path.join(curdir, f)
        except OSError:
            pass

    def _glob_deep(self, curdir, dir_only=False):
        """Recursive directory glob."""

        try:
            if SCANDIR_WORKAROUND:
                with os.scandir(curdir) as scan:
                    for f in scan:
                        try:
                            # Quicker to just test this way than to run through fnmatch.
                            if self._is_hidden(f.name):
                                continue
                            if not dir_only or f.is_dir():
                                yield curdir, f.name
                            if f.is_dir():
                                yield from self._glob_deep(os.path.join(curdir, f.name), dir_only)
                        except OSError:
                            pass
            else:
                for f in os.listdir(curdir):
                    # Quicker to just test this way than to run through fnmatch.
                    if self._is_hidden(f):
                        continue
                    path = os.path.join(curdir, f)
                    is_dir = os.path.isdir(path)
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
                        yield os.path.join(dirname, base)
                else:
                    matcher = fnmatch._compile((target,), self.flags)
                    yield from self._glob_shallow(curdir, matcher)
            else:
                path = os.path.join(curdir, target)
                if os.path.lexists(path):
                    yield path
        else:
            this = rest.pop(0) if rest else None
            if is_magic:
                if self._is_globstar(target):
                    for dirname, base in self._glob_deep(curdir, True):
                        path = os.path.join(dirname, base)
                        if this:
                            yield from self._glob(path, this, rest[:])
                        else:
                            yield path
                else:
                    matcher = fnmatch._compile((target,), self.flags)
                    for path in self._glob_shallow(curdir, matcher, True):
                        if this:
                            yield from self._glob(path, this, rest)
                        else:
                            yield path
            else:
                path = os.path.join(curdir, target)
                if os.path.isdir(path):
                    if this:
                        yield from self._glob(path, this, rest)
                    else:
                        yield path

    def glob(self):
        """Starts off the glob iterator."""
        if self.is_bytes:
            curdir = bytes(os.curdir, 'ASCII')
        else:
            curdir = os.curdir

        if self.pattern:
            if not self.pattern[0][1]:
                # Is Directory
                this = self.pattern[0]
                curdir = this[0]
                if this[2]:
                    # Glob this directory if it exists
                    if os.path.isdir(curdir):
                        rest = self.pattern[1:]
                        this = rest.pop(0)
                        yield from self._glob(curdir, this, rest)
                else:
                    # Return file if exits and finish.
                    if os.path.lexists(curdir):
                        yield curdir
            else:
                rest = self.pattern[:]
                this = rest.pop(0)
                yield from self._glob(curdir, this, rest)


def iglob(pattern, *, flags=0):
    """Glob."""

    yield from Glob(pattern, flags).glob()


def glob(pattern, *, flags=0):
    """Glob."""

    return list(Glob(pattern, flags).glob())


def globsplit(pattern, *, flags=0):
    """Split pattern by '|'."""

    return fnmatch.fnsplit(pattern, flags=_flag_transform(flags, True))


def globmatch(filename, pattern, *patterns, flags=0):
    """
    Check if filename matches pattern.

    By default case sensitivity is determined by the filesystem,
    but if `case_sensitive` is set, respect that instead.
    """

    return fnmatch.fnmatch(filename, pattern, *patterns, flags=_flag_transform(flags, True))


def globfilter(filenames, pattern, *patterns, flags=0):
    """Filter names using pattern."""

    return fnmatch.filter(filenames, pattern, *patterns, flags=_flag_transform(flags, True))


def escape(pattern):
    """Escape."""

    is_bytes = isinstance(pattern, bytes)
    drive = b'' if is_bytes else ''

    if util.platform() == "windows":
        m = fnmatch.RE_WIN_PATH.match(pattern)
        if m:
            drive = m.group(0)

    pattern = pattern[len(drive):]
    replace = br'[\\\1]' if is_bytes else r'[\\\1]'

    return drive + (RE_BMAGIC if is_bytes else RE_MAGIC).sub(replace, pattern)
