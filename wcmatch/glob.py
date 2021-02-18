"""
Wild Card Match.

A custom implementation of `glob`.

Licensed under MIT
Copyright (c) 2018 - 2020 Isaac Muse <isaacmuse@gmail.com>

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
import functools
from collections import namedtuple
from . import _wcparse
from . import util

__all__ = (
    "CASE", "IGNORECASE", "RAWCHARS", "DOTGLOB", "DOTMATCH",
    "EXTGLOB", "EXTMATCH", "GLOBSTAR", "NEGATE", "MINUSNEGATE", "BRACE", "NOUNIQUE",
    "REALPATH", "FOLLOW", "MATCHBASE", "MARK", "NEGATEALL", "NODIR", "FORCEWIN", "FORCEUNIX", "GLOBTILDE",
    "NODOTDIR", "SCANDOTDIR",
    "C", "I", "R", "D", "E", "G", "N", "M", "B", "P", "L", "S", "X", 'K', "O", "A", "W", "U", "T", "Q", "Z", "SD",
    "iglob", "glob", "globmatch", "globfilter", "escape", "raw_escape", "is_magic"
)

# We don't use `util.platform` only because we mock it in tests,
# and `scandir` will not work with bytes on the wrong system.
WIN = sys.platform.startswith('win')

C = CASE = _wcparse.CASE
I = IGNORECASE = _wcparse.IGNORECASE
R = RAWCHARS = _wcparse.RAWCHARS
D = DOTGLOB = DOTMATCH = _wcparse.DOTMATCH
E = EXTGLOB = EXTMATCH = _wcparse.EXTMATCH
G = GLOBSTAR = _wcparse.GLOBSTAR
N = NEGATE = _wcparse.NEGATE
M = MINUSNEGATE = _wcparse.MINUSNEGATE
B = BRACE = _wcparse.BRACE
P = REALPATH = _wcparse.REALPATH
L = FOLLOW = _wcparse.FOLLOW
S = SPLIT = _wcparse.SPLIT
X = MATCHBASE = _wcparse.MATCHBASE
O = NODIR = _wcparse.NODIR
A = NEGATEALL = _wcparse.NEGATEALL
W = FORCEWIN = _wcparse.FORCEWIN
U = FORCEUNIX = _wcparse.FORCEUNIX
T = GLOBTILDE = _wcparse.GLOBTILDE
Q = NOUNIQUE = _wcparse.NOUNIQUE
Z = NODOTDIR = _wcparse.NODOTDIR

K = MARK = 0x1000000
SD = SCANDOTDIR = 0x2000000

_PATHLIB = 0x8000000

# Internal flags
_EXTMATCHBASE = _wcparse._EXTMATCHBASE
_RTL = _wcparse._RTL
_NOABSOLUTE = _wcparse._NOABSOLUTE
_PATHNAME = _wcparse.PATHNAME

FLAG_MASK = (
    CASE |
    IGNORECASE |
    RAWCHARS |
    DOTMATCH |
    EXTMATCH |
    GLOBSTAR |
    NEGATE |
    MINUSNEGATE |
    BRACE |
    REALPATH |
    FOLLOW |
    SPLIT |
    MATCHBASE |
    NODIR |
    NEGATEALL |
    FORCEWIN |
    FORCEUNIX |
    GLOBTILDE |
    NOUNIQUE |
    NODOTDIR |
    _EXTMATCHBASE |
    _RTL |
    _NOABSOLUTE
)

_RE_PATHLIB_DOT_NORM = [
    re.compile(r'(?:((?<=^)|(?<=/))\.(?:/|$))+'),
    re.compile(br'(?:((?<=^)|(?<=/))\.(?:/|$))+')

]

_RE_WIN_PATHLIB_DOT_NORM = [
    re.compile(r'(?:((?<=^)|(?<=[\\/]))\.(?:[\\/]|$))+'),
    re.compile(br'(?:((?<=^)|(?<=[\\/]))\.(?:[\\/]|$))+')
]


def _flag_transform(flags):
    """Transform flags to glob defaults."""

    # Enabling both cancels out
    if flags & FORCEUNIX and flags & FORCEWIN:
        flags ^= FORCEWIN | FORCEUNIX

    # Here we force `PATHNAME`.
    flags = (flags & FLAG_MASK) | _PATHNAME
    if flags & REALPATH:
        if util.platform() == "windows":
            if flags & FORCEUNIX:
                flags ^= FORCEUNIX
            flags |= FORCEWIN
        else:
            if flags & FORCEWIN:
                flags ^= FORCEWIN

    return flags


class _GlobPart(namedtuple('_GlobPart', ['pattern', 'is_magic', 'is_globstar', 'dir_only', 'is_drive'])):
    """File Glob."""


class _GlobSplit(object):
    """
    Split glob pattern on "magic" file and directories.

    Glob pattern return a list of patterns broken down at the directory
    boundary. Each piece will either be a literal file part or a magic part.
    Each part will will contain info regarding whether they are
    a directory pattern or a file pattern and whether the part
    is "magic", etc.: `["pattern", is_magic, is_globstar, dir_only, is_drive]`.

    Example:
        `"**/this/is_literal/*magic?/@(magic|part)"`

        Would  become:

        ```
        [
            ["**", True, True, False, False],
            ["this", False, False, True, False],
            ["is_literal", False, False, True, False],
            ["*magic?", True, False, True, False],
            ["@(magic|part)", True, False, False, False]
        ]
        ```

    """

    def __init__(self, pattern, flags):
        """Initialize."""

        self.unix = _wcparse.is_unix_style(flags)
        self.flags = flags
        self.pattern = pattern
        self.no_abs = bool(flags & _wcparse._NOABSOLUTE)
        self.globstar = bool(flags & GLOBSTAR)
        self.matchbase = bool(flags & MATCHBASE)
        self.extmatchbase = bool(flags & _wcparse._EXTMATCHBASE)
        self.tilde = bool(flags & GLOBTILDE)
        if _wcparse.is_negative(self.pattern, flags):  # pragma: no cover
            # This isn't really used, but we'll keep it around
            # in case we find a reason to directly send inverse patterns
            # Through here.
            self.pattern = self.pattern[0:1]
        if flags & NEGATE:
            flags ^= NEGATE
        self.flags = flags
        self.is_bytes = isinstance(pattern, bytes)
        self.extend = bool(flags & EXTMATCH)
        if not self.unix:
            self.win_drive_detect = True
            self.bslash_abort = True
            self.sep = '\\'
        else:
            self.win_drive_detect = False
            self.bslash_abort = False
            self.sep = '/'
        # Once split, Windows file names will never have `\\` in them,
        # so we can use the Unix magic detect
        ptype = util.BYTES if self.is_bytes else util.UNICODE
        self.magic_symbols = _wcparse._get_magic_symbols(ptype, self.unix, self.flags)[0]

    def is_magic(self, name):
        """Check if name contains magic characters."""

        for c in self.magic_symbols:
            if c in name:
                return True
        return False

    def _sequence(self, i):
        """Handle character group."""

        c = next(i)
        if c == '!':
            c = next(i)
        if c in ('^', '-', '['):
            c = next(i)

        while c != ']':
            if c == '\\':
                # Handle escapes
                try:
                    self._references(i, True)
                except _wcparse.PathNameException:
                    raise StopIteration
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
                raise _wcparse.PathNameException
            value = c
        elif c == '/':
            # \/
            if sequence:
                raise _wcparse.PathNameException
            value = c
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

                if self.extend and c in _wcparse.EXT_TYPES and self.parse_extend(c, i):
                    continue

                if c == '\\':
                    try:
                        self._references(i)
                    except StopIteration:
                        pass
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

    def store(self, value, l, dir_only):
        """Group patterns by literals and potential magic patterns."""

        if l and value in (b'', ''):
            return

        globstar = value in (b'**', '**') and self.globstar
        magic = self.is_magic(value)
        if magic:
            value = _wcparse._compile(value, self.flags)
        if globstar and l and l[-1].is_globstar:
            l[-1] = _GlobPart(value, magic, globstar, dir_only, False)
        else:
            l.append(_GlobPart(value, magic, globstar, dir_only, False))

    def split(self):
        """Start parsing the pattern."""

        split_index = []
        parts = []
        start = -1

        pattern = self.pattern.decode('latin-1') if self.is_bytes else self.pattern

        i = util.StringIter(pattern)
        iter(i)

        # Detect and store away windows drive as a literal
        if self.win_drive_detect:
            root_specified, drive, slash, end = _wcparse._get_win_drive(pattern)
            if drive is not None:
                if self.is_bytes:
                    drive = drive.encode('latin-1')
                parts.append(_GlobPart(drive, False, False, True, True))
                start = end - 1
                i.advance(start)
            elif drive is None and root_specified:
                parts.append(_GlobPart(b'\\' if self.is_bytes else '\\', False, False, True, True))
                start = 1
                i.advance(2)
        elif not self.win_drive_detect and pattern.startswith('/'):
            parts.append(_GlobPart(b'/' if self.is_bytes else '/', False, False, True, True))
            start = 0
            i.advance(1)

        for c in i:
            if self.extend and c in _wcparse.EXT_TYPES and self.parse_extend(c, i):
                continue

            if c == '\\':
                index = i.index
                value = ''
                try:
                    value = self._references(i)
                    if (self.bslash_abort and value == '\\') or value == '/':
                        split_index.append((i.index - 2, 1))
                except StopIteration:
                    i.rewind(i.index - index)
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

        if len(pattern) == 0:
            parts.append(_GlobPart(pattern.encode('latin-1') if self.is_bytes else pattern, False, False, False, False))

        if (
            (self.extmatchbase and not parts[0].is_drive) or
            (self.matchbase and len(parts) == 1 and not parts[0].dir_only)
        ):
            self.globstar = True
            parts.insert(0, _GlobPart(b'**' if self.is_bytes else '**', True, True, True, False))

        if self.no_abs and parts and parts[0].is_drive:
            raise ValueError('The pattern must be a relative path pattern')

        return parts


class Glob(object):
    """Glob patterns."""

    def __init__(self, pattern, flags=0, root_dir=None, limit=_wcparse.PATTERN_LIMIT):
        """Initialize the directory walker object."""

        self.seen = set()
        self.is_bytes = isinstance(pattern[0], bytes)
        self.current = b'.' if self.is_bytes else '.'
        self.root_dir = os.fspath(root_dir) if root_dir is not None else self.current
        self.nounique = bool(flags & NOUNIQUE)
        self.mark = bool(flags & MARK)
        # Only scan for `.` and `..` if it is specifically requested.
        self.scandotdir = flags & SCANDOTDIR
        if self.mark:
            flags ^= MARK
        self.negateall = bool(flags & NEGATEALL)
        if self.negateall:
            flags ^= NEGATEALL
        self.nodir = bool(flags & NODIR)
        if self.nodir:
            flags ^= NODIR
        self.pathlib = bool(flags & _PATHLIB)
        if self.pathlib:
            flags ^= _PATHLIB
        # Right to left searching is only for matching
        if flags & _RTL:  # pragma: no cover
            flags ^= _RTL
        self.flags = _flag_transform(flags | REALPATH)
        self.negate_flags = self.flags
        if not self.scandotdir and not self.flags & NODOTDIR:
            self.flags |= NODOTDIR
        self.raw_chars = bool(self.flags & RAWCHARS)
        self.follow_links = bool(self.flags & FOLLOW)
        self.dot = bool(self.flags & DOTMATCH)
        self.unix = not bool(self.flags & FORCEWIN)
        self.negate = bool(self.flags & NEGATE)
        self.globstar = bool(self.flags & GLOBSTAR)
        self.braces = bool(self.flags & BRACE)
        self.matchbase = bool(self.flags & MATCHBASE)
        self.case_sensitive = _wcparse.get_case(self.flags)
        self.specials = (b'.', b'..') if self.is_bytes else ('.', '..')
        self.empty = b'' if self.is_bytes else ''
        self.stars = b'**' if self.is_bytes else '**'
        self.limit = limit
        if self.flags & FORCEWIN:
            self.sep = b'\\' if self.is_bytes else '\\'
            self.seps = (b'/' if self.is_bytes else '/', self.sep)
            self.re_pathlib_norm = _RE_WIN_PATHLIB_DOT_NORM[util.BYTES if self.is_bytes else util.UNICODE]
            self.re_no_dir = _wcparse.RE_WIN_NO_DIR[util.BYTES if self.is_bytes else util.UNICODE]
        else:
            self.sep = b'/' if self.is_bytes else '/'
            self.seps = (self.sep,)
            self.re_pathlib_norm = _RE_PATHLIB_DOT_NORM[util.BYTES if self.is_bytes else util.UNICODE]
            self.re_no_dir = _wcparse.RE_NO_DIR[util.BYTES if self.is_bytes else util.UNICODE]
        self._parse_patterns(pattern)

        if (
            (self.is_bytes and not isinstance(self.root_dir, bytes)) or
            (not self.is_bytes and not isinstance(self.root_dir, str))
        ):
            raise TypeError(
                'Pattern and root_dir should be of the same type, not {} and {}'.format(
                    type(pattern[0]), type(self.root_dir)
                )
            )

    def _iter_patterns(self, patterns):
        """Iterate expanded patterns."""

        seen = set()
        try:
            current_limit = self.limit
            total = 0
            for p in patterns:
                p = util.norm_pattern(p, not self.unix, self.raw_chars)
                count = 0
                for count, expanded in enumerate(_wcparse.expand(p, self.flags, current_limit), 1):
                    total += 1
                    if 0 < self.limit < total:
                        raise _wcparse.PatternLimitException(
                            "Pattern limit exceeded the limit of {:d}".format(self.limit)
                        )
                    # Filter out duplicate patterns. If `NOUNIQUE` is enabled,
                    # we only want to filter on negative patterns as they are
                    # only filters.
                    is_neg = _wcparse.is_negative(expanded, self.flags)
                    if not self.nounique or is_neg:
                        if expanded in seen:
                            continue
                        seen.add(expanded)

                    yield is_neg, expanded
                if self.limit:
                    current_limit -= count
                    if current_limit < 1:
                        current_limit = 1
        except _wcparse.bracex.ExpansionLimitException:
            raise _wcparse.PatternLimitException(
                "Pattern limit exceeded the limit of {:d}".format(self.limit)
            )

    def _parse_patterns(self, patterns):
        """Parse patterns."""

        self.pattern = []
        self.npatterns = []
        for is_neg, p in self._iter_patterns(patterns):
            if is_neg:
                # Treat the inverse pattern as a normal pattern if it matches, we will exclude.
                # This is faster as compiled patterns usually compare the include patterns first,
                # and then the exclude, but glob will already know it wants to include the file.
                self.npatterns.append(_wcparse._compile(p, self.negate_flags))
            else:
                self.pattern.append(_GlobSplit(p, self.flags).split())

        if not self.pattern and self.npatterns:
            if self.negateall:
                default = self.stars
                self.pattern.append(_GlobSplit(default, self.flags | GLOBSTAR).split())

        if self.nodir:
            self.npatterns.append(self.re_no_dir)

        # A single positive pattern will not find multiples of the same file
        # disable unique mode so that we won't waste time or memory computing unique returns.
        if (
            len(self.pattern) <= 1 and
            not self.flags & NODOTDIR and
            not self.nounique and
            not (self.pathlib and self.scandotdir)
        ):
            self.nounique = True

    def _is_hidden(self, name):
        """Check if is file hidden."""

        return not self.dot and name[0:1] == self.specials[0]

    def _is_this(self, name):
        """Check if "this" directory `.`."""

        return name == self.specials[0] or name == self.sep

    def _is_parent(self, name):
        """Check if `..`."""

        return name == self.specials[1]

    def _match_excluded(self, filename, is_dir):
        """Check if file should be excluded."""

        if is_dir and not filename.endswith(self.sep):
            filename += self.sep

        matched = False
        for pattern in self.npatterns:
            if pattern.fullmatch(filename):
                matched = True
                break

        return matched

    def _is_excluded(self, path, is_dir):
        """Check if file is excluded."""

        return self.npatterns and self._match_excluded(path, is_dir)

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

    def prepend_base(self, path):
        """Join path to base if pattern is not absolute."""

        if self.is_abs_pattern:
            return path
        else:
            return os.path.join(self.root_dir, path)

    def _iter(self, curdir, dir_only, deep):
        """Iterate the directory."""

        if not curdir:
            scandir = self.root_dir
        elif self.is_abs_pattern:
            scandir = curdir
        else:
            scandir = os.path.join(self.root_dir, curdir)

        # Python will never return . or .., so fake it.
        for special in self.specials:
            yield special, True, True, False

        try:
            # Our current directory can be empty if the path starts with magic,
            # But we don't want to return paths with '.', so just use it to list
            # files, but use '' when constructing the path.
            with os.scandir(scandir) as scan:
                for f in scan:
                    try:
                        hidden = self._is_hidden(f.name)
                        try:
                            is_dir = f.is_dir()
                        except OSError:  # pragma: no cover
                            is_dir = False
                        if is_dir:
                            is_link = f.is_symlink()
                        else:
                            # We don't care if a file is a link
                            is_link = False
                        if (not dir_only or is_dir):
                            yield f.name, is_dir, hidden, is_link
                    except OSError:  # pragma: no cover
                        pass
        except OSError:  # pragma: no cover
            pass

    def _glob_dir(self, curdir, matcher, dir_only=False, deep=False):
        """Recursive directory glob."""

        files = list(self._iter(curdir, dir_only, deep))
        for file, is_dir, hidden, is_link in files:
            if file in self.specials:
                if matcher is not None and matcher(file):
                    yield os.path.join(curdir, file), True
                continue

            path = os.path.join(curdir, file)
            follow = not is_link or self.follow_links
            if (matcher is None and not hidden and (follow or not deep)) or (matcher and matcher(file)):
                yield path, is_dir

            if deep and not hidden and is_dir and follow:
                yield from self._glob_dir(path, matcher, dir_only, deep)

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

            # Acquire the pattern after the `globstars` if available.
            # If not, mark that the `globstar` is the end.
            this = rest.pop(0) if rest else None
            globstar_end = this is None
            if this:
                dir_only = this.dir_only
                target = this.pattern

            if globstar_end:
                target = None

            # We match `**/next` during a deep glob, so what ever comes back,
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
                yield os.path.join(curdir, self.empty), True

            # Search
            for path, is_dir in self._glob_dir(curdir, matcher, dir_only, deep=True):
                if this:
                    yield from self._glob(path, this, rest[:])
                else:
                    yield path, is_dir

        elif not dir_only:
            # Files: no need to recursively search at this point as we are done.
            matcher = self._get_matcher(target)
            yield from self._glob_dir(curdir, matcher)

        else:
            # Directory: search current directory against pattern
            # and feed the results back through with the next pattern.
            this = rest.pop(0) if rest else None
            matcher = self._get_matcher(target)
            for path, is_dir in self._glob_dir(curdir, matcher, True):
                if this:
                    yield from self._glob(path, this, rest[:])
                else:
                    yield path, is_dir

    def _get_starting_paths(self, curdir, dir_only):
        """
        Get the starting location.

        For case sensitive paths, we have to "glob" for
        it first as Python doesn't like for its users to
        think about case. By scanning for it, we can get
        the actual casing and then compare.
        """

        if not self.is_abs_pattern and not self._is_parent(curdir) and not self._is_this(curdir):
            results = []
            matcher = self._get_matcher(curdir)
            files = list(self._iter(None, dir_only, False))
            for file, is_dir, hidden, is_link in files:
                if file not in self.specials and (matcher is None or matcher(file)):
                    results.append((file, is_dir))
        else:
            results = [(curdir, True)]
        return results

    def is_unique(self, path):
        """Test if path is unique."""

        if self.nounique:
            return True

        unique = False
        if (path.lower() if not self.case_sensitive else path) not in self.seen:
            self.seen.add(path)
            unique = True
        return unique

    def _pathlib_norm(self, path):
        """Normalize path as `pathlib` does."""

        path = self.re_pathlib_norm.sub(self.empty, path)
        return path[:-1] if len(path) > 1 and path[-1:] in self.seps else path

    def format_path(self, path, is_dir, dir_only):
        """Format path."""

        path = os.path.join(path, self.empty) if dir_only or (self.mark and is_dir) else path
        if self.is_unique(self._pathlib_norm(path) if self.pathlib else path):
            yield path

    def glob(self):
        """Starts off the glob iterator."""

        curdir = self.current

        for pattern in self.pattern:
            # If the pattern ends with `/` we return the files ending with `/`.
            dir_only = pattern[-1].dir_only if pattern else False
            self.is_abs_pattern = pattern[0].is_drive if pattern else False

            if pattern:
                if not pattern[0].is_magic:
                    # Path starts with normal plain text
                    # Lets verify the case of the starting directory (if possible)
                    this = pattern[0]
                    curdir = this[0]

                    # Abort if we cannot find the drive, or if current directory is empty
                    if not curdir or (self.is_abs_pattern and not os.path.lexists(self.prepend_base(curdir))):
                        continue

                    # Make sure case matches, but running case insensitive
                    # on a case sensitive file system may return more than
                    # one starting location.
                    results = self._get_starting_paths(curdir, dir_only)
                    if not results:
                        continue

                    if this.dir_only:
                        # Glob these directories if they exists
                        for start, is_dir in results:
                            rest = pattern[1:]
                            if rest:
                                this = rest.pop(0)
                                for match, is_dir in self._glob(start, this, rest):
                                    if not self._is_excluded(match, is_dir):
                                        yield from self.format_path(match, is_dir, dir_only)
                            elif not self._is_excluded(start, is_dir):
                                yield from self.format_path(start, is_dir, dir_only)
                    else:
                        # Return the file(s) and finish.
                        for match, is_dir in results:
                            if os.path.lexists(self.prepend_base(match)) and not self._is_excluded(match, is_dir):
                                yield from self.format_path(match, is_dir, dir_only)
                else:
                    # Path starts with a magic pattern, let's get globbing
                    rest = pattern[:]
                    this = rest.pop(0)
                    for match, is_dir in self._glob(curdir if not curdir == self.current else self.empty, this, rest):
                        if not self._is_excluded(match, is_dir):
                            yield from self.format_path(match, is_dir, dir_only)


def iglob(patterns, *, flags=0, root_dir=None, limit=_wcparse.PATTERN_LIMIT):
    """Glob."""

    yield from Glob(util.to_tuple(patterns), flags, root_dir, limit).glob()


def glob(patterns, *, flags=0, root_dir=None, limit=_wcparse.PATTERN_LIMIT):
    """Glob."""

    return list(iglob(patterns, flags=flags, root_dir=root_dir, limit=limit))


def translate(patterns, *, flags=0, limit=_wcparse.PATTERN_LIMIT):
    """Translate glob pattern."""

    flags = _flag_transform(flags)
    return _wcparse.translate(patterns, flags, limit)


def globmatch(filename, patterns, *, flags=0, root_dir=None, limit=_wcparse.PATTERN_LIMIT):
    """
    Check if filename matches pattern.

    By default case sensitivity is determined by the file system,
    but if `case_sensitive` is set, respect that instead.
    """

    if root_dir is not None:
        root_dir = os.fspath(root_dir)

    flags = _flag_transform(flags)
    filename = os.fspath(filename)
    return _wcparse.compile(patterns, flags, limit).match(filename, root_dir=root_dir)


def globfilter(filenames, patterns, *, flags=0, root_dir=None, limit=_wcparse.PATTERN_LIMIT):
    """Filter names using pattern."""

    if root_dir is not None:
        root_dir = os.fspath(root_dir)

    matches = []
    flags = _flag_transform(flags)
    obj = _wcparse.compile(patterns, flags, limit)

    for filename in filenames:
        temp = os.fspath(filename)
        if obj.match(temp, root_dir):
            matches.append(filename)
    return matches


@util.deprecated("This function will be removed in 9.0.")
def raw_escape(pattern, unix=None, raw_chars=True):
    """Apply raw character transform before applying escape."""

    return _wcparse.escape(util.norm_pattern(pattern, False, raw_chars, True), unix=unix, pathname=True, raw=True)


def escape(pattern, unix=None):
    """Escape."""

    return _wcparse.escape(pattern, unix=unix)


def is_magic(pattern, *, flags=0):
    """Check if the pattern is likely to be magic."""

    flags = _flag_transform(flags)
    return _wcparse.is_magic(pattern, flags)
