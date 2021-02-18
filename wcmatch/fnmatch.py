"""
Wild Card Match.

A custom implementation of `fnmatch`.

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
from . import _wcparse

__all__ = (
    "CASE", "EXTMATCH", "IGNORECASE", "RAWCHARS",
    "NEGATE", "MINUSNEGATE", "DOTMATCH", "BRACE", "SPLIT",
    "NEGATEALL", "FORCEWIN", "FORCEUNIX",
    "C", "I", "R", "N", "M", "D", "E", "S", "B", "A", "W", "U",
    "translate", "fnmatch", "filter", "escape", "is_magic"
)

C = CASE = _wcparse.CASE
I = IGNORECASE = _wcparse.IGNORECASE
R = RAWCHARS = _wcparse.RAWCHARS
N = NEGATE = _wcparse.NEGATE
M = MINUSNEGATE = _wcparse.MINUSNEGATE
D = DOTMATCH = _wcparse.DOTMATCH
E = EXTMATCH = _wcparse.EXTMATCH
B = BRACE = _wcparse.BRACE
S = SPLIT = _wcparse.SPLIT
A = NEGATEALL = _wcparse.NEGATEALL
W = FORCEWIN = _wcparse.FORCEWIN
U = FORCEUNIX = _wcparse.FORCEUNIX

FLAG_MASK = (
    CASE |
    IGNORECASE |
    RAWCHARS |
    NEGATE |
    MINUSNEGATE |
    DOTMATCH |
    EXTMATCH |
    BRACE |
    SPLIT |
    NEGATEALL |
    FORCEWIN |
    FORCEUNIX
)


def _flag_transform(flags):
    """Transform flags to glob defaults."""

    # Enabling both cancels out
    if flags & FORCEUNIX and flags & FORCEWIN:
        flags ^= FORCEWIN | FORCEUNIX

    return (flags & FLAG_MASK)


def translate(patterns, *, flags=0, limit=_wcparse.PATTERN_LIMIT):
    """Translate `fnmatch` pattern."""

    flags = _flag_transform(flags)
    return _wcparse.translate(patterns, flags, limit)


def fnmatch(filename, patterns, *, flags=0, limit=_wcparse.PATTERN_LIMIT):
    """
    Check if filename matches pattern.

    By default case sensitivity is determined by the file system,
    but if `case_sensitive` is set, respect that instead.
    """

    flags = _flag_transform(flags)
    return _wcparse.compile(patterns, flags, limit).match(filename)


def filter(filenames, patterns, *, flags=0, limit=_wcparse.PATTERN_LIMIT):  # noqa A001
    """Filter names using pattern."""

    matches = []

    flags = _flag_transform(flags)
    obj = _wcparse.compile(patterns, flags, limit)

    for filename in filenames:
        if obj.match(filename):
            matches.append(filename)
    return matches


def escape(pattern):
    """Escape."""

    return _wcparse.escape(pattern, pathname=False)


def is_magic(pattern, *, flags=0):
    """Check if the pattern is likely to be magic."""

    flags = _flag_transform(flags)
    return _wcparse.is_magic(pattern, flags)
