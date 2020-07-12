"""Pathlib implementation that uses our own glob."""
import pathlib
import os
import re
from . import glob
from . import util
from . import _wcparse

__all__ = (
    "CASE", "IGNORECASE", "RAWCHARS", "DOTGLOB", "DOTMATCH",
    "EXTGLOB", "EXTMATCH", "NEGATE", "MINUSNEGATE", "BRACE",
    "REALPATH", "FOLLOW", "MATCHBASE", "NEGATEALL", "NODIR", "NOUNIQUE",
    "C", "I", "R", "D", "E", "G", "N", "B", "M", "P", "L", "S", "X", "O", "A", "Q",
    "Path", "PurePath", "WindowsPath", "PosixPath", "PurePosixPath", "PureWindowsPath"
)

C = CASE = glob.CASE
I = IGNORECASE = glob.IGNORECASE
R = RAWCHARS = glob.RAWCHARS
D = DOTGLOB = DOTMATCH = glob.DOTMATCH
E = EXTGLOB = EXTMATCH = glob.EXTMATCH
G = GLOBSTAR = _wcparse.GLOBSTAR
N = NEGATE = glob.NEGATE
B = BRACE = glob.BRACE
M = MINUSNEGATE = glob.MINUSNEGATE
P = REALPATH = glob.REALPATH
L = FOLLOW = glob.FOLLOW
S = SPLIT = glob.SPLIT
X = MATCHBASE = glob.MATCHBASE
O = NODIR = glob.NODIR
A = NEGATEALL = glob.NEGATEALL
Q = NOUNIQUE = glob.NOUNIQUE
Z = NOSPECIAL = glob.NOSPECIAL

# Internal flags
_EXTMATCHBASE = _wcparse._EXTMATCHBASE
_RTL = _wcparse._RTL
_NOABSOLUTE = _wcparse._NOABSOLUTE
_PATHNAME = _wcparse.PATHNAME
_FORCEWIN = _wcparse.FORCEWIN
_FORCEUNIX = _wcparse.FORCEUNIX

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
    NOUNIQUE |
    NOSPECIAL |
    _EXTMATCHBASE |
    _RTL |
    _NOABSOLUTE
)

_RE_PATHLIB_STRIP = [
    re.compile(r'(?:^(?:\./)*|(?:/\.)*(?:/$)?)'),
    re.compile(br'(?:^(?:\./)*|(?:/\.)*(?:/$)?)')

]

_RE_WIN_PATHLIB_STRIP = [
    re.compile(r'(?:^(?:\.[\\/])*|(?:[\\/]\.)*(?:[\\/]$)?)'),
    re.compile(br'(?:^(?:\.[\\/])*|(?:[\\/]\.)*(?:[\\/]$)?)')
]


class _PathlibGlob(glob.Glob):
    """Specialized glob for `pathlib`."""

    def __init__(self, pattern, flags=0, root_dir=None, limit=_wcparse.PATTERN_LIMIT):
        """Initialize."""

        super().__init__(pattern, flags, root_dir, limit)

        if self.flags & _FORCEWIN:
            self.pathlib_strip = _RE_WIN_PATHLIB_STRIP[_wcparse.BYTES if self.is_bytes else _wcparse.UNICODE]
        else:
            self.pathlib_strip = _RE_PATHLIB_STRIP[_wcparse.BYTES if self.is_bytes else _wcparse.UNICODE]

    def is_unique(self, path):
        """Test if path is unique."""

        if self.nounique:
            return True

        # `pathlib` will normalize out `.` directories, so when we compare unique paths,
        # strip out `.` as `parent/./child` and `parent/child` will both appear as
        # `parent/child` in `pathlib` results.
        path = self.pathlib_strip.sub(self.empty, path)

        unique = False
        if (path.lower() if self.case_sensitive else path) not in self.seen:
            self.seen.add(path)
            unique = True
        return unique


class Path(pathlib.Path):
    """Special pathlike object (which accesses the filesystem) that uses our own glob methods."""

    __slots__ = ()

    def __new__(cls, *args, **kwargs):
        """New."""

        if cls is Path:
            cls = WindowsPath if os.name == 'nt' else PosixPath
        self = cls._from_parts(args, init=False)
        if not self._flavour.is_supported:
            raise NotImplementedError("Cannot instantiate {!r} on your system".format(cls.__name__))
        self._init()
        return self

    def glob(self, patterns, *, flags=0, limit=_wcparse.PATTERN_LIMIT):
        """
        Search the file system.

        `GLOBSTAR` is enabled by default in order match the default behavior of `pathlib`.

        """

        if self.is_dir():
            flags = self._translate_flags(flags | _NOABSOLUTE) | NOSPECIAL
            for filename in _PathlibGlob(util.to_tuple(patterns), flags, str(self), limit).glob():
                yield self.joinpath(filename)

    def rglob(self, patterns, *, flags=0, limit=_wcparse.PATTERN_LIMIT):
        """
        Recursive glob.

        This uses the same recursive logic that the default `pathlib` object uses.
        Folders and files are essentially matched from right to left.

        `GLOBSTAR` is enabled by default in order match the default behavior of `pathlib`.

        """

        yield from self.glob(patterns, flags=flags | _EXTMATCHBASE, limit=limit)


class PurePath(pathlib.PurePath):
    """Special pure pathlike object that uses our own glob methods."""

    __slots__ = ()

    def __new__(cls, *args):
        """New."""

        if cls is PurePath:
            cls = PureWindowsPath if os.name == 'nt' else PurePosixPath
        return cls._from_parts(args)

    def _translate_flags(self, flags):
        """Translate flags for the current `pathlib` object."""

        flags = (flags & FLAG_MASK) | _PATHNAME
        if flags & REALPATH:
            flags |= _FORCEWIN if os.name == 'nt' else _FORCEUNIX
        if isinstance(self, PureWindowsPath):
            if flags & _FORCEUNIX:
                raise ValueError("Windows pathlike objects cannot be forced to behave like a Posix path")
            flags |= _FORCEWIN
        elif isinstance(self, PurePosixPath):
            if flags & _FORCEWIN:
                raise ValueError("Posix pathlike objects cannot be forced to behave like a Windows path")
            flags |= _FORCEUNIX
        return flags

    def _translate_path(self):
        """Translate the object to a path string and ensure trailing slash for non-pure paths that are directories."""

        sep = ''
        name = str(self)
        if isinstance(self, Path) and name and self.is_dir():
            sep = self._flavour.sep

        return name + sep

    def match(self, patterns, *, flags=0, limit=_wcparse.PATTERN_LIMIT):
        """
        Match patterns using `globmatch`, but also using the same right to left logic that the default `pathlib` uses.

        This uses the same right to left logic that the default `pathlib` object uses.
        Folders and files are essentially matched from right to left.

        `GLOBSTAR` is enabled by default in order match the default behavior of `pathlib`.

        """

        return self.globmatch(patterns, flags=flags | _RTL, limit=limit)

    def globmatch(self, patterns, *, flags=0, limit=_wcparse.PATTERN_LIMIT):
        """
        Match patterns using `globmatch`, but without the right to left logic that the default `pathlib` uses.

        `GLOBSTAR` is enabled by default in order match the default behavior of `pathlib`.

        """

        return glob.globmatch(
            self._translate_path(),
            patterns,
            flags=self._translate_flags(flags),
            limit=limit
        )


class PurePosixPath(PurePath):
    """Pure Posix path."""

    _flavour = pathlib._posix_flavour
    __slots__ = ()


class PureWindowsPath(PurePath):
    """Pure Windows path."""

    _flavour = pathlib._windows_flavour
    __slots__ = ()


class PosixPath(Path, PurePosixPath):
    """Posix path."""

    __slots__ = ()


class WindowsPath(Path, PureWindowsPath):
    """Windows path."""

    __slots__ = ()
