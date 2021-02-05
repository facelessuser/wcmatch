"""Pathlib implementation that uses our own glob."""
import pathlib
import os
from . import glob
from . import _wcparse

__all__ = (
    "CASE", "IGNORECASE", "RAWCHARS", "DOTGLOB", "DOTMATCH",
    "EXTGLOB", "EXTMATCH", "NEGATE", "MINUSNEGATE", "BRACE",
    "REALPATH", "FOLLOW", "MATCHBASE", "NEGATEALL", "NODIR", "NOUNIQUE",
    "NODOTDIR", "SCANDOTDIR",
    "C", "I", "R", "D", "E", "G", "N", "B", "M", "P", "L", "S", "X", "O", "A", "Q", "Z", "SD",
    "Path", "PurePath", "WindowsPath", "PosixPath", "PurePosixPath", "PureWindowsPath"
)

C = CASE = glob.CASE
I = IGNORECASE = glob.IGNORECASE
R = RAWCHARS = glob.RAWCHARS
D = DOTGLOB = DOTMATCH = glob.DOTMATCH
E = EXTGLOB = EXTMATCH = glob.EXTMATCH
G = GLOBSTAR = glob.GLOBSTAR
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
Z = NODOTDIR = glob.NODOTDIR

SD = SCANDOTDIR = glob.SCANDOTDIR

# Internal flags
_EXTMATCHBASE = _wcparse._EXTMATCHBASE
_RTL = _wcparse._RTL
_NOABSOLUTE = _wcparse._NOABSOLUTE
_PATHNAME = _wcparse.PATHNAME
_FORCEWIN = _wcparse.FORCEWIN
_FORCEUNIX = _wcparse.FORCEUNIX

_PATHLIB = glob._PATHLIB

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
    NODOTDIR |
    _EXTMATCHBASE |
    _RTL |
    _NOABSOLUTE
)


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
            scandotdir = flags & SCANDOTDIR
            flags = self._translate_flags(flags | _NOABSOLUTE) | ((_PATHLIB | SCANDOTDIR) if scandotdir else _PATHLIB)
            for filename in glob.iglob(patterns, flags=flags, root_dir=str(self), limit=limit):
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
