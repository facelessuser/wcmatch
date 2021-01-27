"""Compatibility module."""
from __future__ import unicode_literals
import sys
import os
import stat
import re
import unicodedata
from functools import wraps
import warnings
import typing
from . import types

PY37 = (3, 7) <= sys.version_info

CASE_FS = os.path.normcase('A') != os.path.normcase('a')

RE_NORM = re.compile(
    r'''(?x)
    (/|\\/)|
    (\\[abfnrtv\\])|
    (\\(?:U[\da-fA-F]{8}|u[\da-fA-F]{4}|x[\da-fA-F]{2}|([0-7]{1,3})))|
    (\\N\{[^}]*?\})|
    (\\[^NUux]) |
    (\\[NUux])
    '''
)

RE_BNORM = re.compile(
    br'''(?x)
    (/|\\/)|
    (\\[abfnrtv\\])|
    (\\(?:x[\da-fA-F]{2}|([0-7]{1,3})))|
    (\\[^x]) |
    (\\[x])
    '''
)

BACK_SLASH_TRANSLATION = {
    r"\a": '\a',
    r"\b": '\b',
    r"\f": '\f',
    r"\r": '\r',
    r"\t": '\t',
    r"\n": '\n',
    r"\v": '\v',
    r"\\": r'\\',
    br"\a": b'\a',
    br"\b": b'\b',
    br"\f": b'\f',
    br"\r": b'\r',
    br"\t": b'\t',
    br"\n": b'\n',
    br"\v": b'\v',
    br"\\": br'\\'
}

if sys.platform.startswith('win'):
    _PLATFORM = "windows"
elif sys.platform == "darwin":  # pragma: no cover
    _PLATFORM = "osx"
else:
    _PLATFORM = "linux"


def platform() -> types.Strings:
    """Get platform."""

    return _PLATFORM


def is_case_sensitive() -> bool:
    """Check if case sensitive."""

    return CASE_FS


def to_tuple(values):
    """Combine values."""

    return (values,) if isinstance(values, (str, bytes)) else tuple(values)


def norm_pattern(
    pattern: types.Strings, normalize: bool, is_raw_chars: bool, ignore_escape: bool = False
) -> types.Strings:
    r"""
    Normalize pattern.

    - For windows systems we want to normalize slashes to \.
    - If raw string chars is enabled, we want to also convert
      encoded string chars to literal characters.
    - If `normalize` is enabled, take care to convert \/ to \\\\.
    """

    is_bytes = isinstance(pattern, bytes)

    if not normalize and not is_raw_chars and not ignore_escape:
        return pattern

    def norm_char(token) -> types.Strings:
        """Normalize slash."""

        if normalize and token in ('/', b'/'):
            token = br'\\' if is_bytes else r'\\'
        return token

    def norm(m: typing.Match) -> types.Strings:
        """Normalize the pattern."""

        if m.group(1):
            char = m.group(1)
            if normalize:
                char = br'\\\\' if is_bytes else r'\\\\' if len(char) > 1 else norm_char(char)
        elif m.group(2):
            char = norm_char(BACK_SLASH_TRANSLATION[m.group(2)] if is_raw_chars else m.group(2))
        elif is_raw_chars and m.group(4):
            char = norm_char(bytes([int(m.group(4), 8) & 0xFF]) if is_bytes else chr(int(m.group(4), 8)))
        elif is_raw_chars and m.group(3):
            char = norm_char(bytes([int(m.group(3)[2:], 16)]) if is_bytes else chr(int(m.group(3)[2:], 16)))
        elif is_raw_chars and not is_bytes and m.group(5):
            char = norm_char(unicodedata.lookup(m.group(5)[3:-1]))
        elif not is_raw_chars or m.group(5 if is_bytes else 6):
            char = m.group(0)
            if ignore_escape:
                char = (b'\\' if is_bytes else '\\') + char
        else:
            value = m.group(6) if is_bytes else m.group(7)
            pos = m.start(6) if is_bytes else m.start(7)
            raise SyntaxError("Could not convert character value %s at position %d" % (value, pos))
        return char

    if is_bytes:
        return RE_BNORM.sub(norm, pattern)
    else:
        return RE_NORM.sub(norm, pattern)


class StringIter(object):
    """Preprocess replace tokens."""

    def __init__(self, string: str) -> None:
        """Initialize."""

        self._string = string
        self._index = 0

    def __iter__(self) -> "StringIter":
        """Iterate."""

        return self

    def __next__(self) -> str:
        """Python 3 iterator compatible next."""

        return self.iternext()

    def match(self, pattern: typing.Pattern) -> typing.Optional[typing.Match]:
        """Perform regex match at index."""

        m = pattern.match(self._string, self._index)
        if m:
            self._index = m.end()
        return m

    @property
    def index(self) -> int:
        """Get current index."""

        return self._index

    def previous(self) -> str:  # pragma: no cover
        """Get previous char."""

        return self._string[self._index - 1]

    def advance(self, count: int) -> None:  # pragma: no cover
        """Advanced the index."""

        self._index += count

    def rewind(self, count: int) -> None:
        """Rewind index."""

        if count > self._index:  # pragma: no cover
            raise ValueError("Can't rewind past beginning!")

        self._index -= count

    def iternext(self) -> str:
        """Iterate through characters of the string."""

        try:
            char = self._string[self._index]
            self._index += 1
        except IndexError:  # pragma: no cover
            raise StopIteration

        return char


class Immutable(object):
    """Immutable."""

    __slots__: typing.Tuple[typing.Any, ...] = tuple()

    def __init__(self, **kwargs: typing.Any) -> None:
        """Initialize."""

        for k, v in kwargs.items():
            super(Immutable, self).__setattr__(k, v)

    def __setattr__(self, name: str, value: typing.Any) -> None:  # pragma: no cover
        """Prevent mutability."""

        raise AttributeError('Class is immutable!')


def is_hidden(path: types.Strings) -> bool:
    """Check if file is hidden."""

    hidden = False
    f = os.path.basename(path)
    if f[:1] in ('.', b'.'):
        # Count dot file as hidden on all systems
        hidden = True
    elif _PLATFORM == 'windows':
        # On Windows, look for `FILE_ATTRIBUTE_HIDDEN`
        FILE_ATTRIBUTE_HIDDEN = 0x2
        results = os.lstat(path)
        hidden = bool(results.st_file_attributes & FILE_ATTRIBUTE_HIDDEN)  # type: ignore
    elif _PLATFORM == "osx":  # pragma: no cover
        # On macOS, look for `UF_HIDDEN`
        results = os.lstat(path)
        hidden = bool(results.st_flags & stat.UF_HIDDEN)  # type: ignore
    return hidden


RT = typing.TypeVar('RT')


def deprecated(
    message: str, stacklevel: int = 2
) -> typing.Callable[[typing.Callable[[typing.Any], RT]], typing.Callable[[typing.Any], RT]]:  # pragma: no cover
    """
    Raise a `DeprecationWarning` when wrapped function/method is called.

    Borrowed from https://stackoverflow.com/a/48632082/866026
    """

    def _decorator(func) -> typing.Callable[..., RT]:
        @wraps(func)
        def _func(*args: typing.Any, **kwargs: typing.Any) -> RT:
            warnings.warn(
                "'{}' is deprecated. {}".format(func.__name__, message),
                category=DeprecationWarning,
                stacklevel=stacklevel
            )
            return func(*args, **kwargs)
        return _func
    return _decorator


def warn_deprecated(message: str, stacklevel: int = 2) -> None:  # pragma: no cover
    """Warn deprecated."""

    warnings.warn(
        message,
        category=DeprecationWarning,
        stacklevel=stacklevel
    )


def fscodec(path: types.Paths, encode: bool = False) -> types.Strings:
    """
    Provide common interface when using to translate path-like files.

    Python 3.5 does not support `os.PathLike` interfaces, so we only return strings and bytes.
    """

    if not isinstance(path, (str, bytes)):
        path = os.fsencode(path) if encode else os.fsdecode(path)
    return path
