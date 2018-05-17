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
    "NOEXTEND", "NOGLOBSTAR", "NEGATE", "MINUSNEGATE", "NOBRACE",
    "F", "I", "R", "D", "E", "G", "N", "M",
    "iglob", "glob", "globsplit", "globmatch", "globfilter", "escape"
)

# We don't use util.platform only because we mock it in tests,
# and scandir will not work with bytes on the wrong system.
WIN = sys.platform.startswith('win')
NO_SCANDIR_WORKAROUND = util.PY36 or (util.PY35 and not WIN)

F = FORCECASE = fnmatch.FORCECASE
I = IGNORECASE = fnmatch.IGNORECASE
R = RAWCHARS = fnmatch.RAWCHARS
D = NODOT = fnmatch.DOT
E = NOEXTEND = fnmatch.EXTEND
G = NOGLOBSTAR = fnmatch.GLOBSTAR
N = NEGATE = fnmatch.NEGATE
M = MINUSNEGATE = fnmatch.MINUSNEGATE
B = NOBRACE = fnmatch.BRACE

FLAG_MASK = (
    FORCECASE |
    IGNORECASE |
    RAWCHARS |
    NODOT |        # Inverse
    NOEXTEND |     # Inverse
    NOGLOBSTAR |   # Inverse
    NEGATE |
    MINUSNEGATE |
    NOBRACE        # Inverse
)

FS_FLAG_MASK = FLAG_MASK ^ (NEGATE | MINUSNEGATE)

RE_MAGIC = re.compile(r'([-!*?(\[|^{\\])')
RE_BMAGIC = re.compile(r'([-!*?(\[|^{\\])')


def _flag_transform(flags, full=False):
    """Transform flags to glob defaults."""

    if not full:
        # Here we force PATHNAME and disable negation NEGATE
        flags = (flags & FS_FLAG_MASK) | fnmatch.PATHNAME
    else:
        flags = (flags & FLAG_MASK) | fnmatch.PATHNAME
    # Enable by default (flipped logic for fnmatch which disables it by default)
    flags ^= NOGLOBSTAR
    flags ^= NOBRACE
    flags ^= NODOT
    flags ^= NOEXTEND
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
        self.extend = not bool(flags & NOEXTEND)
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

        return self.re_magic.search(name) is not None

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

    def store(self, value, l, directory):
        """Group patterns by literals and potential magic patterns."""

        relative_dir = value in ('.', '..')
        magic = self.is_magic(value)
        l.append([value + (self.sep if directory and not magic and not relative_dir else ''), magic, directory])

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
            self.store(value, parts, True)
            start = split + offset

        if start < len(pattern):
            if self.is_bytes:
                value = pattern[start + 1:].encode('latin-1')
            else:
                value = pattern[start + 1:]
            if value:
                self.store(value, parts, False)

        return parts


class Glob(object):
    """Glob patterns."""

    def __init__(self, pattern, flags=0):
        """Init the directory walker object."""

        self.flags = _flag_transform(flags)
        self.dot = bool(self.flags & NODOT)
        self.globstar = bool(self.flags & fnmatch.GLOBSTAR)
        self.case_sensitive = fnmatch.get_case(self.flags)
        self.is_bytes = isinstance(pattern, bytes)
        self.pattern = _magicsplit(pattern, self.flags)
        if not self.case_sensitive and WIN:
            for p in self.pattern:
                p[0] = p[0].lower()
        if util.platform() == "windows":
            self.sep = (b'\\', '\\')
        else:
            self.sep = (b'/', '/')
        self.scandir = util.PY36 or (util.PY35 and util.platform() != "windows")

    def _is_globstar(self, name):
        """Check if name is a rescursive globstar."""

        return self.globstar and name in (b'**', '**')

    def _is_hidden(self, name):
        """
        Check if is file hidden.

        REMOVE: Should just use standard dot convention and remove this.
        """

        return self.dot and name[0:1] in (b'.', '.')

    def _is_this(self, name):
        """Check if "this" directory `.`."""

        return name in (b'.', '.') or name in self.sep

    def _is_parent(self, name):
        """Check if `..`."""

        return name in (b'..', '..')

    def match(self, name):
        """Do a simple match."""

        return ((name.lower().rstrip(os.sep) if not self.case_sensitive else name)) == self._match.rstrip(os.sep)

    def _glob_shallow(self, curdir, matcher, dir_only=False):
        """Non recursive directory glob."""

        try:
            if NO_SCANDIR_WORKAROUND:
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
            if NO_SCANDIR_WORKAROUND:
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
        """
        Handle glob flow.

        There are really only a couple of cases:

        - File name
        - File name pattern (magic)
        - Directory
        - Directory name pattern (magic)
        - Relative indicators `.` and `..`
        - Lastyl globstar `**`.
        """

        is_magic = this[1]
        is_dir = this[2]
        target = this[0]

        # Handle relative directories: `\\` (windows), `/`, `.`, and `..`.
        # We want to append these to the current directory and get the next
        # file or folder name or pattern we need to check against.
        while curdir not in self.sep and (self._is_this(target) or self._is_parent(target)):
            if target in self.sep:
                curdir += target
            else:
                curdir = os.path.join(curdir, target)
            if not os.path.isdir(curdir):
                # Can't find this directory.
                return
            if rest:
                # Get the next target.
                this = rest.pop(0)
                target, is_magic, is_dir = this
            elif is_dir:
                # Nothing left to append, but nothing left to search.
                yield curdir
                return

        if not is_dir:
            # Files
            if is_magic:
                # File pattern
                matcher = fnmatch._compile((target,), self.flags)

            else:
                # Normal file
                matcher = self
                self._match = target

            yield from self._glob_shallow(curdir, matcher)

        else:
            # Directories
            this = rest.pop(0) if rest else None
            if is_magic and self._is_globstar(target):
                # Glob star directory pattern `**`.
                for dirname, base in self._glob_deep(curdir, True):
                    path = os.path.join(dirname, base)
                    if this:
                        yield from self._glob(path, this, rest[:])
                    else:
                        yield path

            else:
                if is_magic:
                    # Normal directory pattern
                    matcher = fnmatch._compile((target,), self.flags)

                else:
                    # Normal directory
                    matcher = self
                    self._match = target

                for path in self._glob_shallow(curdir, matcher, True):
                    if this:
                        yield from self._glob(path, this, rest[:])
                    else:
                        yield path

    def get_starting_paths(self, curdir):
        """
        Get the starting location.

        For case sensitive paths, we have to "glob" for
        it first as Python doesn't like for its users to
        think about case. By scanning for it, we can get
        the actual casing and then compare.
        """

        if not self._is_parent(curdir) and not self._is_this(curdir):
            fullpath = os.path.abspath(curdir)
            basename = os.path.basename(fullpath)
            dirname = os.path.dirname(fullpath)
            if basename:
                self._match = basename
                results = [os.path.basename(name) for name in self._glob_shallow(dirname, self)]
            else:
                results = [curdir]
        else:
            results = [curdir]
        return results

    def glob(self):
        """Starts off the glob iterator."""

        if self.is_bytes:
            curdir = bytes(os.curdir, 'ASCII')
        else:
            curdir = os.curdir

        if self.pattern:
            if not self.pattern[0][1]:
                # Path starts with normal plain text
                # Lets verify the case of the starting directory (if possible)
                this = self.pattern[0]

                curdir = this[0]

                if not os.path.isdir(curdir) and not os.lexists(curdir):
                    return

                # Make sure case matches, but running case insensitive
                # on a case sensitive file system may return more than
                # one starting location.
                results = self.get_starting_paths(curdir)
                if not results:
                    # Nothing to do.
                    return

                if this[2]:
                    # Glob these directories if they exists
                    rest = self.pattern[1:]
                    this = rest.pop(0)
                    for start in results:
                        if os.path.isdir(start):
                            yield from self._glob(curdir, this, rest)
                else:
                    # Return the file(s) and finish.
                    for start in results:
                        if os.path.lexists(start):
                            yield curdir
            else:
                # Path starts with a magic pattern, let's get globbing
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


def globmatch(filename, patterns, *, flags=0):
    """
    Check if filename matches pattern.

    By default case sensitivity is determined by the filesystem,
    but if `case_sensitive` is set, respect that instead.
    """

    return fnmatch.fnmatch(filename, patterns, flags=_flag_transform(flags, True))


def globfilter(filenames, patterns, *, flags=0):
    """Filter names using pattern."""

    return fnmatch.filter(filenames, patterns, flags=_flag_transform(flags, True))


def escape(pattern):
    """Escape."""

    is_bytes = isinstance(pattern, bytes)
    replace = br'\\\1' if is_bytes else r'\\\1'
    magic = RE_BMAGIC if is_bytes else RE_MAGIC

    # Handle windows drives special.
    # Windows drives are handled special internally.
    # So we shouldn't escape them as we'll just have to
    # detect and undo it later.
    drive = b'' if is_bytes else ''
    if util.platform() == "windows":
        m = fnmatch.RE_WIN_PATH.match(pattern)
        if m:
            drive = m.group(0)
    pattern = pattern[len(drive):]

    return drive + magic.sub(replace, pattern)
