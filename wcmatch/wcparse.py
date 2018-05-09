"""Wildcard parsing."""
from __future__ import unicode_literals
import os
import re
import unicodedata
import copyreg
from . import util

__all__ = (
    "EXTEND", "FORCECASE", "IGNORECASE", "RAWCHARS", "NONEGATE", "PATHNAME", "FLAG_MASK",
    "Parser", "Splitter", "WcMatch"
)

_OCTAL = frozenset(('0', '1', '2', '3', '4', '5', '6', '7'))
_STANDARD_ESCAPES = frozenset(('a', 'b', 'f', 'n', 'r', 't', 'v'))
_CHAR_ESCAPES = frozenset(('x',))
_UCHAR_ESCAPES = frozenset(('u', 'U'))
_SET_OPERATORS = frozenset(('&', '~', '|'))
_HEX = frozenset(('a', 'b', 'c', 'd', 'e', 'f', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9'))
_EXTEND = frozenset(('?', '*', '+', '@', '!'))

_CASE_FS = os.path.normcase('A') != os.path.normcase('a')
FORCECASE = 0x0001
IGNORECASE = 0x0002
RAWCHARS = 0x0004
NONEGATE = 0x0008
PATHNAME = 0x0010
DOT = 0x0020
EXTEND = 0x0040

FLAG_MASK = 0x7F
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


class Splitter(object):
    """Split patterns on |."""

    def __init__(self, pattern, flags):
        """Initialize."""

        self.pattern = pattern
        self.is_bytes = isinstance(pattern, bytes)
        self.char_escapes = bool(flags & RAWCHARS)
        self.pathname = bool(flags & PATHNAME)
        self.extend = bool(flags & EXTEND)
        self.bslash_abort = self.pathname if util.platform() == "windows" else False

    def _sequence(self, i):
        """Handle fnmatch character group."""

        c = next(i)
        if c == '!':
            c = next(i)
        if c in ('^', '-', '['):
            c = next(i)

        while c != ']':
            if c == '\\':
                # Handle escapes
                subindex = i.index
                try:
                    self._references(i, True)
                except PathNameException:
                    raise StopIteration
                except StopIteration:
                    i.rewind(i.index - subindex)
            elif c == '/':
                if self.pathname:
                    raise StopIteration
            c = next(i)

    def _references(self, i, sequence=False):
        """Handle references."""

        c = next(i)
        if c == '\\':
            # \\
            if sequence and self.bslash_abort:
                raise PathNameException
        elif c == '/':
            # \/
            if sequence and self.pathname:
                raise PathNameException
            elif self.pathname:
                i.rewind(1)
        else:
            # \a, \b, \c, etc.
            pass

    def parse_extend(self, c, i):
        """Parse extended pattern lists."""

        # Start list parsing
        success = True
        index = i.index
        list_type = c
        try:
            c = next(i)
            if c != '(':
                raise StopIteration
            while c != ')':
                c = next(i)

                if self.extend and self.parse_extend(c, i):
                    continue

                if c == '\\':
                    index = i.index
                    try:
                        self._references(i)
                    except StopIteration:
                        i.rewind(i.index - index)
                elif c == '[':
                    index = i.index
                    try:
                        self._sequence(i)
                    except StopIteration:
                        i.rewind(i.index - index)

        except StopIteration:
            success = False
            c = list_type
            i.rewind(i.index - index)

        return success

    def parse(self):
        """Start parsing the pattern."""

        split_index = []
        parts = []

        pattern = self.pattern.decode('latin-1') if self.is_bytes else self.pattern

        i = util.StringIter(pattern)
        iter(i)
        for c in i:
            if self.extend and self.parse_extend(c, i):
                continue

            if c == '|':
                split_index.append(i.index - 1)
            elif c == '\\':
                index = i.index
                try:
                    self._references(i)
                except StopIteration:
                    i.rewind(i.index - index)
            elif c == '[':
                index = i.index
                try:
                    self._sequence(i)
                except StopIteration:
                    i.rewind(i.index - index)

        start = -1
        for split in split_index:
            if self.is_bytes:
                parts.append(pattern[start + 1:split].encode('latin-1'))
            else:
                parts.append(pattern[start + 1:split])
            start = split

        if start < len(pattern):
            if self.is_bytes:
                parts.append(pattern[start + 1:].encode('latin-1'))
            else:
                parts.append(pattern[start + 1:])

        return tuple(parts)


class Parser(object):
    """Parse the wildcard pattern."""

    def __init__(self, pattern, flags):
        """Initialize."""

        self.pattern = pattern
        self.is_bytes = isinstance(pattern[0], bytes)
        self.char_escapes = bool(flags & RAWCHARS)
        self.negate = not bool(flags & NONEGATE)
        self.pathname = bool(flags & PATHNAME)
        self.dot = bool(flags & DOT)
        self.extend = bool(flags & EXTEND)
        self.case_sensitive = _get_case(flags)
        self.seq_dot = r'(?<![.])'
        self.in_list = False
        if util.platform() == "windows":
            self.char_avoid = (ord('\\'), ord('/'), ord('.'))
            self.star = r'[^\\]*?'
            self.star_dot = r'(?:[^.][^\\]*?)?'
            self.seq_path = r'(?<![\\%s])'
            self.bslash_abort = self.pathname
            self.norm_slash = '\\'
        else:
            self.char_avoid = (ord('/'), ord('.'))
            self.star = r'[^\/]*?'
            self.star_dot = r'(?:[^.][^\/]*?)?'
            self.seq_path = r'(?<![\/%s])'
            self.bslash_abort = False
            self.norm_slash = '/'

    def set_after_start(self):
        """Set tracker for character after the start of a directory."""

        self.after_start = True
        self.dir_start = False

    def set_start_dir(self):
        """Set directory start."""

        self.dir_start = True
        self.after_start = False

    def reset_dir_track(self):
        """Reset dir tracker."""

        self.dir_start = False
        self.after_start = False

    def _restrict_sequence(self):
        """Restrict sequence."""

        if self.pathname:
            value = self.seq_path % ('.' if self.after_start and self.dot else '')
        else:
            value = self.seq_dot
        self.reset_dir_track()

        return value

    def _convert_value(self, value, sequence=True):
        """Convert char value."""

        if sequence or not (self.pathname or (self.after_start and self.dot)) or value not in self.char_avoid:
            return '\\%03o' % value if value <= 0xFF else chr(value)
        else:
            return ('[%s]' % re.escape(chr(value))) + self._restrict_sequence()

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

    def _sequence(self, i):
        """Handle fnmatch character group."""

        result = ['[']

        c = next(i)
        if c == '!':
            # Handle negate char
            result.append('^')
            c = next(i)
        if c in ('^', '-', '[', ']'):
            result.append(re.escape(c))
            c = next(i)

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

        result.append(']')
        if self.pathname or (self.after_start and self.dot):
            result.append(self._restrict_sequence())

        return ''.join(result)

    def _references(self, i, sequence=False):
        """Handle references."""

        index = i.index
        value = ''
        c = next(i)
        if not self.is_bytes and self.char_escapes and c in 'N':
            # \N{Name}
            value = self._convert_value(self._get_unicode_name(index, i), sequence)
        elif self.char_escapes and c in _OCTAL:
            # \000
            value = self._convert_value(self._get_octal(c, i), sequence)
        elif not self.is_bytes and self.char_escapes and c in _UCHAR_ESCAPES:
            # \u, \U,
            value = self._convert_value(self._get_unicode(i, c == "U"), sequence)
        elif self.char_escapes and c in _CHAR_ESCAPES:
            # \x
            value = self._convert_value(self._get_byte(i), sequence)
        elif self.char_escapes and c in _STANDARD_ESCAPES:
            # \n, \v, etc. and \x.
            value = '\\' + c
        elif c == '\\':
            # \\
            if sequence and self.bslash_abort:
                raise PathNameException
            value = r'\\'
            if self.bslash_abort:
                if not self.in_list:
                    self.set_start_dir()
                else:
                    value += self._restrict_sequence()
        elif c == '/':
            # \/
            if sequence and self.pathname:
                raise PathNameException
            if self.pathname:
                value = r'\\'
                if self.bslash_abort and not self.in_list:
                    self.set_start_dir()
                if self.in_list:
                    value += self._restrict_sequence()
                i.rewind(1)
            else:
                c = self.norm_slash
                value = re.escape(c)
        else:
            # \a, \b, \c, etc.
            value = re.escape(c)
        return value

    def _handle_star(self, i):
        """Handle star."""

        star = self.star_dot if self.after_start and self.dot else self.star
        dstar = r'(?:[^.].*?)?' if self.after_start and self.dot else r'.*?'
        value = dstar if not self.pathname and not self.in_list else star
        if self.after_start and self.pathname:
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
                if c == '\\':
                    try:
                        self._references(i, True)
                        # Was not what we expected
                        # Assume two single stars
                        value += self.star
                    except PathNameException:
                        # Looks like escape was a valid slash
                        # Store pattern accordingly
                        value = r'.*?'
                    except StopIteration:
                        # Ran out of characters so assume backslash
                        # count as a double star
                        if self.slash == '\\':
                            value = dstar
                        else:
                            value += self.star
                elif c == '/':
                    # Found slash
                    value = dstar
                else:
                    # There was no start of next directory
                    # Assume two single stars
                    value += self.star
                # Backout and handle slashes later
                i.rewind(i.index - index)
            except StopIteration:
                # Could not acquire directory slash due to no more characters
                # Use double star
                value = dstar
        self.reset_dir_track()

        return value

    def parse_extend(self, c, i, current):
        """Parse extended pattern lists."""

        # Save state
        temp_dir_start = self.dir_start
        temp_after_start = self.after_start
        temp_in_list = self.in_list
        self.in_list = True

        # Start list parsing
        success = True
        index = i.index
        list_type = c
        extended = []
        try:
            c = next(i)
            if c != '(':
                raise StopIteration
            while c != ')':
                c = next(i)

                if self.extend and self.parse_extend(c, i, extended):
                    # Track when next char needs special dot logic
                    if self.dir_start and not self.after_start:
                        self.set_after_start()
                    elif not self.dir_start and self.after_start:
                        self.reset_dir_track()
                    continue

                if c == '*':
                    extended.append(self._handle_star(i))
                elif c == '?':
                    if not self.pathname:
                        extended.append('.' + self._restrict_sequence())
                    else:
                        extended.append('[^.]' if self.after_start and self.dot else '.')
                        self.reset_dir_track()
                elif c == '/':
                    extended.append(re.escape(self.norm_slash))
                    if self.pathname:
                        extended.append(self._restrict_sequence())
                elif c == "|":
                    extended.append(c)
                    if self.pathname and temp_after_start:
                        self.set_start_dir()
                elif c == '\\':
                    subindex = i.index
                    try:
                        extended.append(self._references(i))
                    except StopIteration:
                        i.rewind(i.index - subindex)
                        extended.append(r'\\')
                        if self.pathname and self.bslash_abort:
                            extended.append(self._restrict_sequence())
                elif c == '[':
                    subindex = i.index
                    try:
                        extended.append(self._sequence(i))
                    except StopIteration:
                        i.rewind(i.index - subindex)
                        extended.append(r'\[')
                elif c != ')':
                    extended.append(re.escape(c))

                # Track when next char needs special dot logic
                if self.dir_start and not self.after_start:
                    self.set_after_start()
                elif not self.dir_start and self.after_start:
                    self.reset_dir_track()

            if list_type == '?':
                current.append('(?:%s)?' % ''.join(extended))
            elif list_type == '*':
                current.append('(?:%s)*?' % ''.join(extended))
            elif list_type == '+':
                current.append('(?:%s)+' % ''.join(extended))
            elif list_type == '@':
                current.append('(?:%s)' % ''.join(extended))
            elif list_type == '!':
                star = self.star_dot if temp_after_start and self.dot else self.star
                current.append('(?:(?!(?:%s))%s)' % (''.join(extended), star))

        except StopIteration:
            success = False
            i.rewind(i.index - index)
            assert i.index == index, "%d | %d" % (i.index, index)

        # Either restore if extend parsing failed, or reset if it worked
        if not temp_in_list:
            self.in_list = False
        if success:
            self.reset_dir_track()
        else:
            self.dir_start = temp_dir_start
            self.after_start = temp_after_start

        return success

    def root(self, pattern, current):
        """Start parsing the pattern."""

        self.set_after_start()
        i = util.StringIter(pattern)
        iter(i)
        for c in i:

            index = i.index
            if self.extend and self.parse_extend(c, i, current):
                # Track when next char needs special dot logic
                if self.dir_start and not self.after_start:
                    self.set_after_start()
                elif not self.dir_start and self.after_start:
                    self.reset_dir_track()
                continue
            assert i.index == index, "%d | %d" % (i.index, index)

            if c == '*':
                current.append(self._handle_star(i))
            elif c == '?':
                if self.pathname:
                    current.append('.' + self._restrict_sequence())
                else:
                    current.append('[^.]' if self.after_start and self.dot else '.')
                    self.reset_dir_track()
            elif c == '/':
                current.append(re.escape(self.norm_slash))
                if self.pathname:
                    self.set_start_dir()
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

            # Track when next char needs special dot logic
            if self.dir_start and not self.after_start:
                self.set_after_start()
            elif not self.dir_start and self.after_start:
                self.reset_dir_track()

    def parse(self):
        """Parse pattern list."""

        result = []
        exclude_result = []
        empty_include = True
        empty_exclude = True

        for p in self.pattern:
            p = p.decode('latin-1') if self.is_bytes else p
            if self.negate and p[0:1] == '-':
                current = exclude_result
                p = p[1:]
                current.append('|' if not empty_exclude else '')
            else:
                current = result
                current.append('|' if not empty_include else '')

            if current is result:
                empty_include = False
            else:
                empty_exclude = False

            self.root(p, current)

        if exclude_result and not result:
            result.append('.*?')
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
