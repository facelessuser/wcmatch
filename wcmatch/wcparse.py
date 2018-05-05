"""Wildcard parsing."""
from __future__ import unicode_literals
import os
import re
import unicodedata
import copyreg
from . import util

__all__ = (
    "CASE", "IGNORECASE", "STRING_ESCAPES", "ESCAPE_CHARS", "NO_EXTRA", "FLAG_MASK",
    "Parser", "WcMatch"
)

_OCTAL = frozenset(('0', '1', '2', '3', '4', '5', '6', '7'))
_STANDARD_ESCAPES = frozenset(('a', 'b', 'f', 'n', 'r', 't', 'v', '\\'))
_CHAR_ESCAPES = frozenset(('x',))
_UCHAR_ESCAPES = frozenset(('u', 'U'))
_SET_OPERATORS = frozenset(('&', '~', '|'))
_WILDCARD_CHARS = frozenset(('-', '[', ']', '*', '?', '|'))

_CASE_FS = os.path.normcase('A') != os.path.normcase('a')
CASE = 0x0001
IGNORECASE = 0x0002
RAW_STRING_ESCAPES = 0x0004
ESCAPE_CHARS = 0x0008
NO_EXTRA = 0x0010

FLAG_MASK = 0x1F


class Parser(object):
    """Parse the wildcard pattern."""

    def __init__(self, pattern, flags):
        """Initialize."""

        self.pattern = pattern
        if isinstance(pattern, bytes):
            self.is_bytes = True
        else:
            self.is_bytes = False
        self.string_escapes = flags & RAW_STRING_ESCAPES
        self.escape_chars = flags & ESCAPE_CHARS
        self.extra = not (flags & NO_EXTRA)

    def _sequence(self, i):
        """Handle fnmatch character group."""

        result = ['[']

        c = next(i)
        if c == '!':
            # Handle negate char
            result.append('^')
            c = next(i)
        if c == '^':
            # Escape regular expression negate character
            result.append('\\' + c)
            c = next(i)
        if c in ('-', '['):
            # Escape opening bracket or hyphen
            result.append('\\' + c)
            c = next(i)
        elif c == ']':
            # Handle closing as first character
            result.append(c)
            c = next(i)

        end_stored = False
        escape_hypen = -1
        while c != ']':
            if c == '-':
                if i.index - 1 > escape_hypen:
                    # Found a range delimiter.
                    # Mark the next two characters as needing to be escaped if hypens.
                    # The next character would be the end char range (s-e),
                    # and the one after that would be the potential start char range
                    # of a new range (s-es-e), so neither can be legitimate range delimiters.
                    result.append(c)
                    escape_hypen = i.index + 1
                else:
                    result.append('\\' + c)
            elif c == '\\':
                # Handle escapes
                subindex = i.index
                try:
                    result.append(self._references(i))
                    if not self.escape_chars and i.previous() == ']':
                        end_stored = True
                        break
                except StopIteration:
                    i.rewind(i.index - subindex)
                    result.append('\\\\')
            elif c in _SET_OPERATORS:
                # Escape &, |, and ~ to avoid &&, ||, and ~~
                result.append('\\' + c)
            else:
                # Anything else
                result.append(c)
            c = next(i)

        if not end_stored:
            result.append(']')

        return ''.join(result)

    def _references(self, i):
        """Handle references."""

        index = i.index
        value = ''
        c = next(i)
        if not self.is_bytes and self.string_escapes and c in 'N':
            # \N{name}
            try:
                c = next(i)
                if c != '{':
                    raise SyntaxError("Missing '{' in named Unicode character format at position %d!" % (i.index - 1))
                name = []
                c = next(i)
                while c != '}':
                    name.append(c)
                    c = next(i)
            except StopIteration:
                raise SyntaxError('Incomplete named Unicode character at position %d!' % (index - 1))
            nval = ord(unicodedata.lookup(''.join(name)))
            value = '\\%03o' % nval if nval <= 0xFF else chr(nval)
        elif self.string_escapes and c in _OCTAL:
            # \octal
            digit = [c]
            try:
                for x in range(2):
                    c = next(i)
                    if c in _OCTAL:
                        digit.append(c)
                    else:
                        i.rewind(1)
                        break
            except StopIteration:
                pass
            digit = int(''.join(digit), 8)
            if digit <= 0xFF:
                value = '\\%03o' % digit
            elif not self.is_bytes:
                value = chr(digit)
            else:
                raise ValueError("octal escape value outside of range 0-0o377!")
        elif not self.is_bytes and self.string_escapes and c in _UCHAR_ESCAPES:
            # \u, \U,
            value = '\\' + c
        elif self.string_escapes and (c in _STANDARD_ESCAPES or c in _CHAR_ESCAPES):
            # \n, \v, etc. and \x.
            value = '\\' + c
        elif self.escape_chars:
            value = re.escape(c)
        elif not self.string_escapes and c == '\\':
            value = '\\\\'
            i.rewind(1)
        elif c in _SET_OPERATORS or c in _WILDCARD_CHARS:
            value = '\\\\'
            i.rewind(1)
        else:
            # Anything else
            value = '\\\\' + c
        return value

    def parse(self):
        """Start parsing the pattern."""

        result = []
        exclude_result = []

        pattern = self.pattern.decode('latin-1') if self.is_bytes else self.pattern

        if self.extra and pattern[0:1] == '-':
            current = exclude_result
            pattern = pattern[1:]
            current.append('')
        else:
            current = result
            current.append('')

        i = util.StringIter(pattern)
        iter(i)
        for c in i:
            if c == '*':
                current.append('.*')
            elif c == '?':
                current.append('.')
            elif self.extra and c == '|':
                try:
                    c = next(i)
                    if c == '-':
                        current = exclude_result
                    else:
                        current = result
                        i.rewind(1)
                except StopIteration:
                    # No need to append | as we are at the end.
                    current = result
                # Only append if we've already started the pattern
                # This is to avoid adding a leading | to something
                # like the exclude pattern on transition from normal
                # to exclude pattern.
                if current:
                    current.append('|')
            elif c == '\\':
                index = i.index
                try:
                    current.append(self._references(i))
                except StopIteration:
                    i.rewind(i.index - index)
                    current.append('\\\\')
            elif c == '[':
                index = i.index
                try:
                    current.append(self._sequence(i))
                except StopIteration:
                    i.rewind(i.index - index)
                    current.append('\\[')
            else:
                current.append(re.escape(c))
        if not result:
            result.append('.*')
        if util.PY36:
            pattern = r'(?s:%s)\Z' % ''.join(result)
            exclude_pattern = r'(?s:%s)\Z' % ''.join(exclude_result)
        else:
            pattern = r'(?ms)(?:%s)\Z' % ''.join(result)
            exclude_pattern = r'(?ms)(?:%s)\Z' % ''.join(exclude_result)

        if self.is_bytes:
            if pattern is not None:
                pattern = pattern.encode('latin-1')
            if exclude_pattern is not None:
                exclude_pattern = exclude_pattern.encode('latin-1')

        return pattern, exclude_pattern


class WcMatch(util.Immutable):
    """File name match object."""

    __slots__ = ("_include", "_exclude", "_hash")

    def __init__(self, include, exclude):
        """Initialization."""

        super(WcMatch, self).__init__(
            _include=include,
            _exclude=exclude,
            _hash=hash((type(self), type(include), include, type(exclude), exclude))
        )

    def __hash__(self):
        """Hash."""

        return self._hash

    def __eq__(self, other):
        """Equal."""

        return (
            isinstance(other, WcMatch) and
            self._include == other._include and
            self._exclude == other._exclude
        )

    def __ne__(self, other):
        """Equal."""

        return (
            not isinstance(other, WcMatch) or
            self._include != other._include or
            self._exclude != other._exclude
        )

    def match(self, filename):
        """Match filename."""

        valid = self._include.fullmatch(filename) is not None
        if valid and self._exclude is not None and self._exclude.fullmatch(filename) is not None:
            valid = False
        return valid


def _pickle(p):
    return WcMatch, (p._include, p._exclude)


copyreg.pickle(WcMatch, _pickle)
