"""Pathlib implementation that uses our own glob."""
import pathlib
import os
from . import glob
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
    _wcparse._RECURSIVEMATCH |
    _wcparse._NOABSOLUTE
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
            flags = self._translate_flags(flags | _wcparse._NOABSOLUTE)
            for filename in glob.iglob(patterns, flags=flags, root_dir=str(self), limit=limit):
                yield self.joinpath(filename)

    def rglob(self, patterns, *, flags=0, limit=_wcparse.PATTERN_LIMIT):
        """
        Recursive glob.

        This uses the same recursive logic that the default `pathlib` object uses.
        Folders and files are essentially matched from right to left.

        `GLOBSTAR` is enabled by default in order match the default behavior of `pathlib`.

        """

        yield from self.glob(patterns, flags=flags | _wcparse._RECURSIVEMATCH, limit=limit)


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

        flags = (flags & FLAG_MASK) | _wcparse.PATHNAME
        if flags & REALPATH:
            flags |= _wcparse.FORCEWIN if os.name == 'nt' else _wcparse.FORCEUNIX
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
        name = str(self)
        if isinstance(self, Path) and name and self.is_dir():
            sep = self._flavour.sep

        return name + sep

    def match(self, patterns, *, flags=0, limit=_wcparse.PATTERN_LIMIT):
        """
        Match patterns using `globmatch`, but also using the same recursive logic that the default `pathlib` uses.

        This uses the same recursive logic that the default `pathlib` object uses.
        Folders and files are essentially matched from right to left.

        `GLOBSTAR` is enabled by default in order match the default behavior of `pathlib`.

        """

        return self.globmatch(patterns, flags=flags | _wcparse._RECURSIVEMATCH, limit=limit)

    def globmatch(self, patterns, *, flags=0, limit=_wcparse.PATTERN_LIMIT):
        """
        Match patterns using `globmatch`, but without the recursive logic that the default `pathlib` uses.

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
