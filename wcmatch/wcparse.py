"""Wildcard parsing."""
from __future__ import unicode_literals
import os
import re
import unicodedata
import copyreg
from . import util

__all__ = (
    "FORCECASE", "IGNORECASE", "RAWSTRING", "ESCAPES", "NOEXTRA", "PATHNAME", "FLAG_MASK",
    "Parser", "WcMatch"
)

_OCTAL = frozenset(('0', '1', '2', '3', '4', '5', '6', '7'))
_STANDARD_ESCAPES = frozenset(('a', 'b', 'f', 'n', 'r', 't', 'v'))
_CHAR_ESCAPES = frozenset(('x',))
_UCHAR_ESCAPES = frozenset(('u', 'U'))
_SET_OPERATORS = frozenset(('&', '~', '|'))
_WILDCARD_CHARS = frozenset(('-', '[', ']', '*', '?', '|'))
_HEX = frozenset(('a', 'b', 'c', 'd', 'e', 'f', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9'))

_CASE_FS = os.path.normcase('A') != os.path.normcase('a')
FORCECASE = 0x0001
IGNORECASE = 0x0002
RAWSTRING = 0x0004
ESCAPES = 0x0008
NOEXTRA = 0x0010
PATHNAME = 0x0020

FLAG_MASK = 0x3F
_CASE_FLAGS = FORCECASE | IGNORECASE


class PathNameException(Exception):
    """Path name exception."""


def _is_case_sensitive():
    """Check if case sensitive."""

    return _CASE_FS


def _get_case(flags):
    """Parse flags for case sensitivity settings."""

    if not bool(flags & _CASE_FLAGS):
        case_sensitive = _is_case_sensitive()
    elif flags & FORCECASE and flags & IGNORECASE:
        raise ValueError("Cannot use FORCECASE and IGNORECASE flags together!")
    elif flags & FORCECASE:
        case_sensitive = True
    else:
        case_sensitive = False
    return case_sensitive


class Parser(object):
    """Parse the wildcard pattern."""

    def __init__(self, pattern, flags):
        """Initialize."""

        self.pattern = pattern
        if isinstance(pattern, bytes):
            self.is_bytes = True
        else:
            self.is_bytes = False
        self.string_escapes = flags & RAWSTRING
        self.escape_chars = flags & ESCAPES
        self.extra = not (flags & NOEXTRA)
        self.pathname = flags & PATHNAME
        self.case_sensitive = _get_case(flags)
        if util.platform() == "windows":
            self.slash_val = (ord('\\'), ord('/'))
            self.star = r'[^\\]*'
            self.seq_path = r'(?<![\\])'
            self.bslash_abort = self.pathname
            self.norm_slash = '\\'
        else:
            self.slash_val = (ord('/'),)
            self.star = r'[^\/]*'
            self.seq_path = r'(?<![\/])'
            self.bslash_abort = False
            self.norm_slash = '/'

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
                    result.append(self._references(i, True))
                    if not self.escape_chars and i.previous() == ']':
                        if self.pathname:
                            result.append(self.seq_path)
                        end_stored = True
                        break
                except PathNameException:
                    raise StopIteration
                except StopIteration:
                    i.rewind(i.index - subindex)
                    result.append(r'\\')
            elif c == '/':
                if self.pathname:
                    raise StopIteration
                result.append(re.escape(self.norm_slash))
            elif c in _SET_OPERATORS:
                # Escape &, |, and ~ to avoid &&, ||, and ~~
                result.append('\\' + c)
            else:
                # Anything else
                result.append(c)
            c = next(i)

        if not end_stored:
            result.append(']')
            if self.pathname:
                result.append(self.seq_path)

        return ''.join(result)

    def _convert_value(self, value, sequence=True):
        """Convert char value."""

        if sequence or not self.pathname or value not in self.slash_val:
            return '\\%03o' % value if value <= 0xFF else chr(value)
        else:
            return ('[%s]' % re.escape(chr(value))) + self.seq_path

    def _get_unicode_name(self, index, i):
        """Get Unicode name."""

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
        return nval

    def _get_wide_unicode(self, i):
        """Get narrow Unicode."""

        value = []
        for x in range(3):
            c = next(i)
            if c == '0':
                value.append(c)
            else:  # pragma: no cover
                raise SyntaxError('Invalid wide Unicode character at %d!' % (i.index - 1))

        c = next(i)
        if c in ('0', '1'):
            value.append(c)
        else:  # pragma: no cover
            raise SyntaxError('Invalid wide Unicode character at %d!' % (i.index - 1))

        for x in range(4):
            c = next(i)
            if c.lower() in _HEX:
                value.append(c)
            else:  # pragma: no cover
                raise SyntaxError('Invalid wide Unicode character at %d!' % (i.index - 1))
        return int(''.join(value), 16)

    def _get_narrow_unicode(self, i):
        """Get narrow Unicode."""

        value = []
        for x in range(4):
            c = next(i)
            if c.lower() in _HEX:
                value.append(c)
            else:  # pragma: no cover
                raise SyntaxError('Invalid Unicode character at %d!' % (i.index - 1))
        return int(''.join(value), 16)

    def _get_unicode(self, i, wide=False):
        """Parse Unicode."""

        return self._get_wide_unicode(i) if wide else self._get_narrow_unicode(i)

    def _get_byte(self, i):
        """Get byte."""

        value = []
        for x in range(2):
            c = next(i)
            if c.lower() in _HEX:
                value.append(c)
            else:  # pragma: no cover
                raise SyntaxError('Invalid byte character at %d!' % (i.index - 1))
        return int(''.join(value), 16)

    def _get_octal(self, c, i):
        """Get octal value."""

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
        value = int(''.join(digit), 8)
        if value > 0xFF and self.is_bytes:
            raise ValueError("octal escape value outside of range 0-0o377!")
        return value

    def _references(self, i, sequence=False):
        """Handle references."""

        index = i.index
        value = ''
        c = next(i)
        if not self.is_bytes and self.string_escapes and c in 'N':
            # \N{Name}
            value = self._convert_value(self._get_unicode_name(index, i), sequence)
        elif self.string_escapes and c in _OCTAL:
            # \000
            value = self._convert_value(self._get_octal(c, i), sequence)
        elif not self.is_bytes and self.string_escapes and c in _UCHAR_ESCAPES:
            # \u, \U,
            value = self._convert_value(self._get_unicode(i, c == "U"), sequence)
        elif self.string_escapes and c in _CHAR_ESCAPES:
            # \x
            value = self._convert_value(self._get_byte(i), sequence)
        elif self.string_escapes and c in _STANDARD_ESCAPES:
            # \n, \v, etc. and \x.
            value = '\\' + c
        elif c == '\\':
            # \\
            if sequence and self.bslash_abort:
                raise PathNameException
            value = r'\\'
            if not self.string_escapes and not self.escape_chars:
                i.rewind(1)
        elif c == '/':
            # \/
            if sequence and self.pathname:
                raise PathNameException
            elif self.pathname:
                value = r'\\'
                i.rewind(1)
            elif self.escape_chars or self.string_escapes:
                c = self.norm_slash
                value = re.escape(c)
        elif self.escape_chars:
            # \a, \b, \c, etc.
            value = re.escape(c)
        elif c in _SET_OPERATORS or c in _WILDCARD_CHARS:
            # \?, \&, \[, etc
            if sequence and self.bslash_abort:
                raise PathNameException
            value = r'\\'
            i.rewind(1)
        else:
            # Anything else
            if sequence and self.bslash_abort:
                raise PathNameException
            value = r'\\' + c
        return value

    # def _handle_tilde(self, i, directory_start=False):
    #     """Directory start."""

    #     value = '~'
    #     if directory_start and self.pathname:
    #         try:
    #             index = i.index
    #             c = next(i)
    #             if c == '\\' and (self.bslash_abort or self.escape_chars):
    #                 try:
    #                     self._references(i, True)
    #                     # Was not what we expected
    #                     # Backout and assume not a home directory
    #                 except PathNameException:
    #                     # Looks like escape was a valid slash
    #                     # Store pattern accordingly
    #                     if self.is_bytes:
    #                         value = os.path.expanduser(b'~').encode('latin-1')
    #                     else:
    #                         value = os.path.expanduser('~')
    #                 except StopIteration:
    #                     # Ran out of characters so assume backslash
    #                     # count as a double star
    #                     if self.slash == '\\':
    #                         if self.is_bytes:
    #                             value = os.path.expanduser(b'~').encode('latin-1')
    #                         else:
    #                             value = os.path.expanduser('~')
    #             elif c == '/':
    #                 # Found slash
    #                 if self.is_bytes:
    #                     value = os.path.expanduser(b'~').encode('latin-1')
    #                 else:
    #                     value = os.path.expanduser('~')
    #             # Backout and hanlde slashes later
    #             i.rewind(i.index - index)
    #         except StopIteration:
    #             # Could not acquire directory slash due to no more characters
    #             # Use double star
    #             if self.is_bytes:
    #                 value = os.path.expanduser(b'~').encode('latin-1')
    #             else:
    #                 value = os.path.expanduser('~')
    #     return value

    def _handle_star(self, i, directory_start=False):
        """Handle star."""

        value = '.*' if not self.pathname else self.star
        if directory_start and self.pathname:
            try:
                c = next(i)
                if c != '*':
                    i.rewind(1)
                    raise StopIteration
            except StopIteration:
                # Could not acquire a second star, so assume single star pattern
                return value

            try:
                index = i.index
                c = next(i)
                if c == '\\' and (self.bslash_abort or self.escape_chars):
                    try:
                        self._references(i, True)
                        # Was not what we expected
                        # Assume two single stars
                        value += value
                    except PathNameException:
                        # Looks like escape was a valid slash
                        # Store pattern accordingly
                        value = r'.*'
                    except StopIteration:
                        # Ran out of characters so assume backslash
                        # count as a double star
                        if self.slash == '\\':
                            value = r'.*'
                        else:
                            value += value
                elif c == '/':
                    # Found slash
                    value = r'.*'
                else:
                    # There was no start of next directory
                    # Assume two single stars
                    value += value
                # Backout and handle slashes later
                i.rewind(i.index - index)
            except StopIteration:
                # Could not acquire directory slash due to no more characters
                # Use double star
                value = '.*'

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

        first = True
        i = util.StringIter(pattern)
        iter(i)
        for c in i:
            if c == '*':
                current.append(self._handle_star(i, first))
            # elif c == '~' and first:
            #     current.append(self._handle_tilde(i, first))
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
                first = True
                continue
            elif c == '/':
                current.append(re.escape(self.norm_slash))
            elif c == '\\':
                index = i.index
                try:
                    current.append(self._references(i))
                except StopIteration:
                    i.rewind(i.index - index)
                    current.append(r'\\')
            elif c == '[':
                index = i.index
                try:
                    current.append(self._sequence(i))
                except StopIteration:
                    i.rewind(i.index - index)
                    current.append(r'\[')
            else:
                current.append(re.escape(c))
            first = False
        if not result:
            result.append('.*')
        case_flag = 'i' if not self.case_sensitive else ''
        if util.PY36:
            pattern = r'(?s%s:%s)\Z' % (case_flag, ''.join(result))
            exclude_pattern = r'(?s%s:%s)\Z' % (case_flag, ''.join(exclude_result))
        else:
            pattern = r'(?ms%s)(?:%s)\Z' % (case_flag, ''.join(result))
            exclude_pattern = r'(?ms%s)(?:%s)\Z' % (case_flag, ''.join(exclude_result))

        if self.is_bytes:
            if pattern is not None:
                pattern = pattern.encode('latin-1')
            if exclude_pattern is not None:
                exclude_pattern = exclude_pattern.encode('latin-1')

        return pattern, exclude_pattern


class WcMatch(util.Immutable):
    """File name match object."""

    __slots__ = ("_include", "_exclude", "_hash")

    def __init__(self, include, exclude=None):
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
