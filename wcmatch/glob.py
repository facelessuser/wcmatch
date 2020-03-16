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
import functools
from . import _wcparse
from . import util

__all__ = (
    "CASE", "IGNORECASE", "RAWCHARS", "DOTGLOB", "DOTMATCH",
    "EXTGLOB", "EXTMATCH", "GLOBSTAR", "NEGATE", "MINUSNEGATE", "BRACE", "NOUNIQUE",
    "REALPATH", "FOLLOW", "MATCHBASE", "MARK", "NEGATEALL", "NODIR", "FORCEWIN", "FORCEUNIX", "GLOBTILDE",
    "C", "I", "R", "D", "E", "G", "N", "M", "B", "P", "L", "S", "X", 'K', "O", "A", "W", "U", "T", "Q",
    "iglob", "glob", "globmatch", "globfilter", "escape", "raw_escape"
)

# We don't use `util.platform` only because we mock it in tests,
# and `scandir` will not work with bytes on the wrong system.
WIN = sys.platform.startswith('win')
NO_SCANDIR_WORKAROUND = util.PY36

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

K = MARK = 0x100000

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
    _wcparse._RECURSIVEMATCH |
    _wcparse._NOABSOLUTE
)


def _flag_transform(flags):
    """Transform flags to glob defaults."""

    # Enabling both cancels out
    if flags & _wcparse.FORCEUNIX and flags & _wcparse.FORCEWIN:
        flags ^= _wcparse.FORCEWIN | _wcparse.FORCEUNIX

    # Here we force `PATHNAME`.
    flags = (flags & FLAG_MASK) | _wcparse.PATHNAME
    if flags & _wcparse.REALPATH:
        if util.platform() == "windows":
            if flags & _wcparse.FORCEUNIX:
                flags ^= _wcparse.FORCEUNIX
            flags |= _wcparse.FORCEWIN
        else:
            if flags & _wcparse.FORCEWIN:
                flags ^= _wcparse.FORCEWIN

    return flags


class Glob(object):
    """Glob patterns."""

    def __init__(self, pattern, flags=0, root_dir=None, limit=_wcparse.PATTERN_LIMIT):
        """Initialize the directory walker object."""

        self.seen = set()
        self.is_bytes = isinstance(pattern[0], bytes)
        self.current = b'.' if self.is_bytes else '.'
        self.root_dir = util.fscodec(root_dir, self.is_bytes) if root_dir is not None else self.current
        self.mark = bool(flags & MARK)
        self.nounique = bool(flags & NOUNIQUE)
        if self.mark:
            flags ^= MARK
        self.negateall = bool(flags & NEGATEALL)
        if self.negateall:
            flags ^= NEGATEALL
        self.nodir = bool(flags & _wcparse.NODIR)
        if self.nodir:
            flags ^= _wcparse.NODIR
        self.flags = _flag_transform(flags | _wcparse.REALPATH)
        self.raw_chars = bool(self.flags & RAWCHARS)
        self.follow_links = bool(self.flags & FOLLOW)
        self.dot = bool(self.flags & DOTMATCH)
        self.unix = not bool(self.flags & _wcparse.FORCEWIN)
        self.negate = bool(self.flags & NEGATE)
        self.globstar = bool(self.flags & _wcparse.GLOBSTAR)
        self.braces = bool(self.flags & _wcparse.BRACE)
        self.matchbase = bool(self.flags & _wcparse.MATCHBASE)
        self.case_sensitive = _wcparse.get_case(self.flags)
        self.specials = (b'.', b'..') if self.is_bytes else ('.', '..')
        self.empty = b'' if self.is_bytes else ''
        self.limit = limit
        self._parse_patterns(pattern)
        if self.flags & _wcparse.FORCEWIN:
            self.sep = b'\\' if self.is_bytes else '\\'
        else:
            self.sep = b'/' if self.is_bytes else '/'

    def _iter_patterns(self, patterns):
        """Iterate expanded patterns."""

        count = 1
        seen = set()
        for p in patterns:
            p = util.norm_pattern(p, not self.unix, self.raw_chars)
            for expanded in _wcparse.expand(p, self.flags):
                if 0 < self.limit < count:
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
                count += 1

    def _parse_patterns(self, patterns):
        """Parse patterns."""

        self.pattern = []
        self.npatterns = []
        nflags = self.flags | _wcparse.REALPATH
        for is_neg, p in self._iter_patterns(patterns):
            if is_neg:
                # Treat the inverse pattern as a normal pattern if it matches, we will exclude.
                # This is faster as compiled patterns usually compare the include patterns first,
                # and then the exclude, but glob will already know it wants to include the file.
                self.npatterns.append(_wcparse._compile(p, nflags))
            else:
                self.pattern.append(_wcparse.WcPathSplit(p, self.flags).split())

        if not self.pattern and self.npatterns:
            if self.negateall:
                default = '**'
                if self.is_bytes:
                    default = os.fsencode(default)
                self.pattern.append(_wcparse.WcPathSplit(default, self.flags | GLOBSTAR).split())

        if self.nodir:
            ptype = _wcparse.BYTES if self.is_bytes else _wcparse.UNICODE
            nodir = _wcparse.RE_WIN_NO_DIR[ptype] if self.flags & _wcparse.FORCEWIN else _wcparse.RE_NO_DIR[ptype]
            self.npatterns.append(nodir)

        # A single positive pattern will not find multiples of the same file
        # disable unique mode so that we won't waste time or memory computing unique returns.
        if len(self.pattern) <= 1 and not self.nounique:
            self.nounique = True

    def _is_hidden(self, name):
        """Check if is file hidden."""

        return not self.dot and name[0:1] in (b'.', '.')

    def _is_this(self, name):
        """Check if "this" directory `.`."""

        return name in (b'.', '.') or name == self.sep

    def _is_parent(self, name):
        """Check if `..`."""

        return name in (b'..', '..')

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
            yield special, True

        try:
            if NO_SCANDIR_WORKAROUND:
                # Our current directory can be empty if the path starts with magic,
                # But we don't want to return paths with '.', so just use it to list
                # files, but use '' when constructing the path.
                with os.scandir(scandir) as scan:
                    for f in scan:
                        try:
                            # Quicker to just test this way than to run through `fnmatch`.
                            if deep and self._is_hidden(f.name):
                                continue
                            try:
                                is_dir = f.is_dir()
                            except OSError:  # pragma: no cover
                                is_dir = False
                            if is_dir:
                                is_link = f.is_symlink()
                            else:
                                # We don't care if a file is a link
                                is_link = False
                            if deep and not self.follow_links and is_link:
                                continue
                            if (not dir_only or is_dir):
                                yield f.name, is_dir
                        except OSError:  # pragma: no cover
                            pass
            else:
                for f in os.listdir(scandir):
                    # Quicker to just test this way than to run through `fnmatch`.
                    if deep and self._is_hidden(f):
                        continue
                    path = os.path.join(scandir, f)
                    try:
                        is_dir = os.path.isdir(path)
                    except OSError:  # pragma: no cover
                        is_dir = False
                    if is_dir:
                        is_link = os.path.islink(path)
                    else:
                        is_link = False
                    if deep and not self.follow_links and is_link:
                        continue
                    if (not dir_only or is_dir):
                        yield f, is_dir

        except OSError:  # pragma: no cover
            pass

    def _glob_dir(self, curdir, matcher, dir_only=False, deep=False):
        """Recursive directory glob."""

        files = list(self._iter(curdir, dir_only, deep))
        for file, is_dir in files:
            if file in self.specials:
                if matcher is not None and matcher(file):
                    yield os.path.join(curdir, file), True
                continue

            path = os.path.join(curdir, file)
            if matcher is None or matcher(file):
                yield path, is_dir

            if deep and is_dir:
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

        results = [(curdir, True)]

        if not self._is_parent(curdir) and not self._is_this(curdir):
            fullpath = os.path.abspath(self.prepend_base(curdir))
            basename = os.path.basename(fullpath)
            dirname = os.path.dirname(fullpath)
            if basename:
                matcher = self._get_matcher(basename)
                results = [
                    (os.path.basename(name), is_dir) for name, is_dir in self._glob_dir(dirname, matcher, dir_only)
                ]

        return results

    def is_unique(self, path):
        """Test if path is unique."""

        if self.nounique:
            return True

        unique = False
        if (path.lower() if self.case_sensitive else path) not in self.seen:
            self.seen.add(path)
            unique = True
        return unique

    def format_path(self, path, is_dir, dir_only):
        """Format path."""

        path = os.path.join(path, self.empty) if dir_only or (self.mark and is_dir) else path
        if self.is_unique(path):
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
                    results = [(curdir, True)] if self.is_abs_pattern else self._get_starting_paths(curdir, dir_only)
                    if not results:
                        continue

                    if this.dir_only:
                        # Glob these directories if they exists
                        for start, is_dir in results:
                            if is_dir:
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

    is_bytes = isinstance(patterns[0], bytes) if not isinstance(patterns, (bytes, str)) else isinstance(patterns, bytes)
    if root_dir is not None:
        root_dir = util.fscodec(root_dir, is_bytes)

    flags = _flag_transform(flags)
    filename = util.fscodec(filename, is_bytes)
    if not _wcparse.is_unix_style(flags):
        filename = _wcparse.norm_slash(filename, flags)
    return _wcparse.compile(patterns, flags, limit).match(filename, root_dir=root_dir)


def globfilter(filenames, patterns, *, flags=0, root_dir=None, limit=_wcparse.PATTERN_LIMIT):
    """Filter names using pattern."""

    is_bytes = isinstance(patterns[0], bytes) if not isinstance(patterns, (bytes, str)) else isinstance(patterns, bytes)
    if root_dir is not None:
        root_dir = util.fscodec(root_dir, is_bytes)

    matches = []
    flags = _flag_transform(flags)
    unix = _wcparse.is_unix_style(flags)
    obj = _wcparse.compile(patterns, flags, limit)

    for filename in filenames:
        temp = util.fscodec(filename, is_bytes)
        if not unix:
            temp = _wcparse.norm_slash(temp, flags)
        if obj.match(temp, root_dir):
            matches.append(filename)
    return matches


def raw_escape(pattern, unix=None):
    """Apply raw character transform before applying escape."""

    return _wcparse.raw_escape(pattern, unix)


def escape(pattern, unix=None):
    """Escape."""

    return _wcparse.escape(pattern, unix)
