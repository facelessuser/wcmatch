"""
Wild Card Match.

A custom implementation of fnmatch.

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
from . import util
from . import _wcparse

__all__ = (
    "EXTEND", "FORCECASE", "IGNORECASE", "RAWCHARS", "NEGATE",
    "PATHNAME", "DOT", "GLOBSTAR", "MINUSNEGATE", "BRACE",
    "F", "I", "R", "N", "P", "D", "E", "G", "M",
    "translate", "fnmatch", "filter", "fnsplit"
)

F = FORCECASE = _wcparse.FORCECASE
I = IGNORECASE = _wcparse.IGNORECASE
R = RAWCHARS = _wcparse.RAWCHARS
N = NEGATE = _wcparse.NEGATE
P = PATHNAME = _wcparse.PATHNAME
D = DOT = _wcparse.DOT
E = EXTEND = _wcparse.EXTEND
G = GLOBSTAR = _wcparse.GLOBSTAR
M = MINUSNEGATE = _wcparse.MINUSNEGATE
B = BRACE = _wcparse.BRACE

FLAG_MASK = (
    FORCECASE |
    IGNORECASE |
    RAWCHARS |
    NEGATE |
    PATHNAME |
    DOT |
    EXTEND |
    GLOBSTAR |
    MINUSNEGATE |
    BRACE
)


def fnsplit(pattern, *, flags=0):
    """Split pattern by '|'."""

    return _wcparse.WcSplit(pattern, flags).split()


def translate(patterns, *, flags=0):
    """Translate fnmatch pattern counting `|` as a separator and `-` as a negative pattern."""

    return _wcparse.WcParse(util.to_tuple(patterns), flags & FLAG_MASK).parse()


def fnmatch(filename, patterns, *, flags=0):
    """
    Check if filename matches pattern.

    By default case sensitivity is determined by the filesystem,
    but if `case_sensitive` is set, respect that instead.
    """

    return _wcparse._compile(util.to_tuple(patterns), flags & FLAG_MASK).match(util.norm_slash(filename))


def filter(filenames, patterns, *, flags=0):  # noqa A001
    """Filter names using pattern."""

    matches = []

    obj = _wcparse._compile(util.to_tuple(patterns), flags & FLAG_MASK)

    for filename in filenames:
        filename = util.norm_slash(filename)
        if obj.match(filename):
            matches.append(filename)
    return matches
