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
    "EXTMATCH", "FORCECASE", "IGNORECASE", "RAWCHARS", "NEGATE", "PERIOD", "BRACE",
    "F", "I", "R", "N", "P", "E",
    "translate", "fnmatch", "filter", "fnsplit"
)

F = FORCECASE = _wcparse.FORCECASE
I = IGNORECASE = _wcparse.IGNORECASE
R = RAWCHARS = _wcparse.RAWCHARS
N = NEGATE = _wcparse.NEGATE
P = PERIOD = _wcparse.DOTGLOB
E = EXTMATCH = _wcparse.EXTGLOB
B = BRACE = _wcparse.BRACE

FLAG_MASK = (
    FORCECASE |
    IGNORECASE |
    RAWCHARS |
    NEGATE |
    PERIOD |       # Inverse
    EXTMATCH |
    BRACE
)


def _flag_transform(flags):
    """Transform flags to glob defaults."""

    flags = (flags & FLAG_MASK)
    # Enable by default (flipped logic as the underlying library disables it by default).
    flags ^= PERIOD
    return flags


def fnsplit(pattern, *, flags=0):
    """Split pattern by '|'."""

    return _wcparse.WcSplit(pattern, _flag_transform(flags)).split()


def translate(patterns, *, flags=0):
    """Translate fnmatch pattern."""

    return _wcparse.WcParse(util.to_tuple(patterns), _flag_transform(flags)).parse()


def fnmatch(filename, patterns, *, flags=0):
    """
    Check if filename matches pattern.

    By default case sensitivity is determined by the filesystem,
    but if `case_sensitive` is set, respect that instead.
    """

    flags = _flag_transform(flags)
    if not _wcparse.get_case(flags):
        filename = util.norm_slash(filename)
    return _wcparse._compile(util.to_tuple(patterns), flags).match(filename)


def filter(filenames, patterns, *, flags=0):  # noqa A001
    """Filter names using pattern."""

    matches = []

    flags = _flag_transform(flags)
    case_sensitive = _wcparse.get_case(flags)
    obj = _wcparse._compile(util.to_tuple(patterns), flags)

    for filename in filenames:
        if not case_sensitive:
            filename = util.norm_slash(filename)
        if obj.match(filename):
            matches.append(filename)
    return matches
