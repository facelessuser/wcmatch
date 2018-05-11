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
import re
import copyreg
import functools
from . import util

__all__ = (
    "EXTEND", "FORCECASE", "IGNORECASE", "RAWCHARS", "NONEGATE",
    "PATHNAME", "DOT", "GLOBSTAR", "MINUSNEGATE",
    "F", "I", "R", "N", "P", "D", "E", "G", "M",
    "translate", "fnmatch", "filter", "fnsplit", "escape", "WcMatch"
)

SET_OPERATORS = frozenset(('&', '~', '|'))

F = FORCECASE = 0x0001
I = IGNORECASE = 0x0002
R = RAWCHARS = 0x0004
N = NONEGATE = 0x0008
P = PATHNAME = 0x0010
D = DOT = 0x0020
E = EXTEND = 0x0040
G = GLOBSTAR = 0x0080
M = MINUSNEGATE = 0x0100

FLAG_MASK = (
    FORCECASE |
    IGNORECASE |
    RAWCHARS |
    NONEGATE |
    PATHNAME |
    DOT |
    EXTEND |
    GLOBSTAR |
    MINUSNEGATE
)
CASE_FLAGS = FORCECASE | IGNORECASE

RE_MAGIC = re.compile(r'(^[-!]|[*?(\[|])')
RE_BMAGIC = re.compile(r'(^[-!]|[*?(\[|])')


class PathNameException(Exception):
    """Path name exception."""


@functools.lru_cache(maxsize=256, typed=True)
def _compile(pattern, flags):  # noqa A001
    """Compile patterns."""

    p1, p2 = translate(pattern, flags)

    if p1 is not None:
        p1 = re.compile(p1)
    if p2 is not None:
        p2 = re.compile(p2)
    return WcMatch(p1, p2)


def get_case(flags):
    """Parse flags for case sensitivity settings."""

    if not bool(flags & CASE_FLAGS):
        case_sensitive = util.is_case_sensitive()
    elif flags & FORCECASE and flags & IGNORECASE:
        raise ValueError("Cannot use FORCECASE and IGNORECASE flags together!")
    elif flags & FORCECASE:
        case_sensitive = True
    else:
        case_sensitive = False
    return case_sensitive


class Split(object):
    """Class that splits patterns on |."""

    def __init__(self, pattern, flags):
        """Initialize."""

        self.pattern = pattern
        self.is_bytes = isinstance(pattern, bytes)
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


class FnMatch(object):
    """Parse the wildcard pattern."""

    def __init__(self, pattern, flags=0):
        """Initialize."""

        self.pattern = pattern
        self.negate_symbol = '-' if bool(flags & MINUSNEGATE) else '!'
        self.is_bytes = isinstance(pattern[0], bytes)
        self.negate = not bool(flags & NONEGATE)
        self.pathname = bool(flags & PATHNAME)
        self.raw_chars = bool(flags & RAWCHARS)
        self.globstar = self.pathname and bool(flags & GLOBSTAR)
        self.dot = bool(flags & DOT)
        self.extend = bool(flags & EXTEND)
        self.case_sensitive = get_case(flags)
        self.seq_dot = r'(?<![.])'
        self.in_list = False
        self.flags = flags
        if util.platform() == "windows":
            self.char_avoid = (ord('\\'), ord('/'), ord('.'))
            self.star = r'[^\\]*?'
            self.star_dot = r'(?:[^.][^\\]*?)?'
            self.seq_path = r'(?<![\\/%s])'
            self.bslash_abort = self.pathname
        else:
            self.char_avoid = (ord('/'), ord('.'))
            self.star = r'[^\/]*?'
            self.star_dot = r'(?:[^.][^\/]*?)?'
            self.seq_path = r'(?<![\/%s])'
            self.bslash_abort = False

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
                result.append(c)
            elif c in SET_OPERATORS:
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

        value = ''
        c = next(i)
        if c == '\\':
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
                if self.in_list:
                    value += self._restrict_sequence()
                i.rewind(1)
            else:
                value = re.escape(c)
        else:
            # \a, \b, \c, etc.
            value = re.escape(c)
        return value

    def _handle_star(self, i):
        """Handle star."""

        star = self.star_dot if self.after_start and self.dot else self.star
        dstar = r'(?:[^.].*?)?' if self.after_start and self.dot else r'.*?'
        value = dstar if not self.globstar and not self.in_list else star

        if self.after_start and self.globstar:
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
                    extended.append(c)
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
                current.append(c)
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
            p = util.norm_pattern(p, self.pathname, self.raw_chars)
            p = p.decode('latin-1') if self.is_bytes else p
            if self.negate and p[0:1] == self.negate_symbol:
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


def fnsplit(pattern, flags=0):
    """Split pattern by '|'."""

    return Split(pattern, flags).parse()


def translate(pattern, flags=0):
    """Translate fnmatch pattern counting `|` as a separator and `-` as a negative pattern."""

    return FnMatch(
        tuple(pattern) if not isinstance(pattern, (str, bytes)) else (pattern,),
        flags
    ).parse()


def fnmatch(filename, pattern, flags=0):
    """
    Check if filename matches pattern.

    By default case sensitivity is determined by the filesystem,
    but if `case_sensitive` is set, respect that instead.
    """

    return _compile(
        tuple(pattern) if not isinstance(pattern, (str, bytes)) else (pattern,),
        flags & FLAG_MASK
    ).match(util.norm_slash(filename))


def filter(filenames, pattern, flags=0):  # noqa A001
    """Filter names using pattern."""

    matches = []

    obj = _compile(
        tuple(pattern) if not isinstance(pattern, (str, bytes)) else (pattern,),
        flags & FLAG_MASK
    )

    for filename in filenames:
        filename = util.norm_slash(filename)
        if obj.match(filename):
            matches.append(filename)
    return matches


def escape(pattern):
    """Escape."""

    is_bytes = isinstance(pattern, bytes)

    def replace(m):
        """Replace."""

        return '[\\%s]' % m.group(0)

    return (RE_BMAGIC if is_bytes else RE_MAGIC).sub(replace, pattern)
