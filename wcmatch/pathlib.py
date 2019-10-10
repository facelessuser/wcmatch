"""Pathlib implementation that uses our own glob."""
import pathlib
import os
from . import glob
from . import _wcparse
from . import util

__all__ = (
    "CASE", "FORCECASE", "IGNORECASE", "RAWCHARS", "DOTGLOB", "DOTMATCH",
    "EXTGLOB", "EXTMATCH", "NEGATE", "MINUSNEGATE", "BRACE",
    "REALPATH", "FOLLOW", "MATCHBASE", "NEGATEALL", "NODIR",
    "C", "F", "I", "R", "D", "E", "N", "B", "M", "P", "L", "S", "X", "O", "A",
    "escape", "raw_escape",
    "Path", "PurePath", "WindowsPath", "PosixPath", "PurePosixPath", "PureWindowsPath",
    "AUTO", "WINDOWS", "UNIX"
)

C = CASE = glob.CASE
F = FORCECASE = glob.FORCECASE
I = IGNORECASE = glob.IGNORECASE
R = RAWCHARS = glob.RAWCHARS
D = DOTGLOB = DOTMATCH = glob.DOTMATCH
E = EXTGLOB = EXTMATCH = glob.EXTMATCH
N = NEGATE = glob.NEGATE
M = MINUSNEGATE = glob.MINUSNEGATE
B = BRACE = glob.BRACE
P = REALPATH = glob.REALPATH
L = FOLLOW = glob.FOLLOW
S = SPLIT = glob.SPLIT
X = MATCHBASE = glob.MATCHBASE
O = NODIR = glob.NODIR
A = NEGATEALL = glob.NEGATEALL

AUTO = glob.AUTO
WINDOWS = glob.WINDOWS
UNIX = glob.UNIX

FLAG_MASK = (
    CASE |
    FORCECASE |
    IGNORECASE |
    RAWCHARS |
    DOTMATCH |
    EXTMATCH |
    NEGATE |
    MINUSNEGATE |
    BRACE |
    REALPATH |
    FOLLOW |
    SPLIT |
    MATCHBASE |
    NODIR |
    NEGATEALL |
    _wcparse._RECURSIVEMATCH |
    _wcparse.GLOBSTAR |
    _wcparse.PATHNAME
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

    def glob(self, patterns, *, flags=0):
        """
        Search the file system.

        `GLOBSTAR` is enabled by default in order match the default behavior of `pathlib`.

        """

        if self.is_dir():
            flags = self._translate_flags(flags)
            for filename in glob.Glob(util.to_tuple(patterns), flags, curdir=str(self), pathlib=True).glob():
                yield self / filename

    def rglob(self, patterns, *, flags=0):
        """
        Recursive glob.

        This uses the same recursive logic that the default `pathlib` object uses.
        Folders and files are essentially matched from right to left.

        `GLOBSTAR` is enabled by default in order match the default behavior of `pathlib`.

        """

        yield from self.glob(patterns, flags=flags | _wcparse._RECURSIVEMATCH)


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

        flags = (flags & FLAG_MASK) | _wcparse.GLOBSTAR
        if isinstance(self, PureWindowsPath):
            if flags & _wcparse.FORCEUNIX:
                raise ValueError("Windows pathlike objects cannot be forced to behave like a Posix path")
            flags |= _wcparse.FORCEWIN
        elif isinstance(self, PurePosixPath):
            if flags & _wcparse.FORCEWIN:
                raise ValueError("Posix pathlike objects cannot be forced to behave like a Windows path")
            flags |= _wcparse.FORCEUNIX
        return flags

    def _translate_path(self):
        """Translate the object to a path string and ensure trailing slash for non-pure paths that are directories."""

        sep = ''
        if isinstance(self, Path) and self.is_dir():
            sep = self._flavour.sep

        return str(self) + sep

    def match(self, patterns, *, flags=0):
        """
        Match patterns using `globmatch`, but also using the same recursive logic that the default `pathlib` uses.

        This uses the same recursive logic that the default `pathlib` object uses.
        Folders and files are essentially matched from right to left.

        `GLOBSTAR` is enabled by default in order match the default behavior of `pathlib`.

        """

        return glob.globmatch(
            self._translate_path(),
            patterns,
            flags=self._translate_flags(flags | _wcparse._RECURSIVEMATCH)
        )

    def globmatch(self, patterns, *, flags=0):
        """
        Match patterns using `globmatch`, but without the recursive logic that the default `pathlib` uses.

        `GLOBSTAR` is enabled by default in order match the default behavior of `pathlib`.

        """

        return glob.globmatch(
            self._translate_path(),
            patterns,
            flags=self._translate_flags(flags)
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


def raw_escape(pattern, *, platform=AUTO):
    """Apply raw character transform before applying escape."""

    return glob.raw_escape(pattern, platform=platform)


def escape(pattern, *, platform=AUTO):
    """Escape."""

    return glob.escape(pattern, platform=platform)