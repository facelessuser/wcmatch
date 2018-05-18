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
import bracex
from . import util

__all__ = (
    "EXTEND", "FORCECASE", "IGNORECASE", "RAWCHARS", "NEGATE",
    "PATHNAME", "DOT", "GLOBSTAR", "MINUSNEGATE", "BRACE",
    "F", "I", "R", "N", "P", "D", "E", "G", "M",
    "translate", "fnmatch", "filter", "fnsplit", "FnMatch"
)

SET_OPERATORS = frozenset(('&', '~', '|'))

F = FORCECASE = 0x0001
I = IGNORECASE = 0x0002
R = RAWCHARS = 0x0004
N = NEGATE = 0x0008
P = PATHNAME = 0x0010
D = DOT = 0x0020
E = EXTEND = 0x0040
G = GLOBSTAR = 0x0080
M = MINUSNEGATE = 0x0100
B = BRACE = 0x0200

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
CASE_FLAGS = FORCECASE | IGNORECASE

RE_WIN_PATH = re.compile(r'(\\{4}[^\\]+\\{2}[^\\]+|[a-z]:)(\\{2}|$)')


class PathNameException(Exception):
    """Path name exception."""


@functools.lru_cache(maxsize=256, typed=True)
def _compile(patterns, flags):  # noqa A001
    """Compile patterns."""

    p1, p2 = FnParse(patterns, flags & FLAG_MASK).parse()

    if p1 is not None:
        p1 = re.compile(p1)
    if p2 is not None:
        p2 = re.compile(p2)
    return FnMatch(p1, p2)


def get_case(flags):
    """Parse flags for case sensitivity settings."""

    if not bool(flags & CASE_FLAGS):
        case_sensitive = util.is_case_sensitive()
    elif flags & FORCECASE:
        case_sensitive = True
    else:
        case_sensitive = False
    return case_sensitive


class FnSplit(object):
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

    def split(self):
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


class FnParse(object):
    """Parse the wildcard pattern."""

    def __init__(self, pattern, flags=0):
        """Initialize."""

        self.pattern = pattern
        self.braces = bool(flags & BRACE)
        self.negate_symbol = '-' if bool(flags & MINUSNEGATE) else '!'
        self.is_bytes = isinstance(pattern[0], bytes)
        self.negate = bool(flags & NEGATE)
        self.pathname = bool(flags & PATHNAME)
        self.raw_chars = bool(flags & RAWCHARS)
        self.globstar = self.pathname and bool(flags & GLOBSTAR)
        self.dot = bool(flags & DOT)
        self.extend = bool(flags & EXTEND)
        self.case_sensitive = get_case(flags)
        self.seq_dot = r'(?<![.])'
        self.in_list = False
        self.flags = flags
        self.inv_ext = 0
        if util.platform() == "windows":
            self.win_drive_detect = self.pathname
            self.char_avoid = (ord('\\'), ord('/'), ord('.'))
            self.path_star = r'[^\\]*?'
            self.path_star_dot1 = r'(?!(?:\.{1,2})(?:$|\\))' + self.path_star
            self.path_star_dot2 = r'(?!(?:\.{1,2})(?:$|\\))' + r'(?:(?!\.)[^\\]*?)?'
            self.path_gstar_dot1 = r'(?:(?!(?:\\|^)(?:\.{1,2})($|\\)).)*?'
            self.path_gstar_dot2 = r'(?:(?!(?:\\|^)\.).)*?'
            self.seq_path = r'(?![\\/%s])'
            self.bslash_abort = self.pathname
            self.sep = '\\'
        else:
            self.win_drive_detect = False
            self.char_avoid = (ord('/'), ord('.'))
            self.path_star = r'[^\/]*?'
            self.path_star_dot1 = r'(?!(?:\.{1,2})(?:$|\/))' + self.path_star
            self.path_star_dot2 = r'(?!(?:\.{1,2})(?:$|\/))' + r'(?:(?!\.)[^\/]*?)?'
            self.path_gstar_dot1 = r'(?:(?!(?:\/|^)(?:\.{1,2})($|\/)).)*?'
            self.path_gstar_dot2 = r'(?:(?!(?:\/|^)\.).)*?'
            self.seq_path = r'(?![\/%s])'
            self.bslash_abort = False
            self.sep = '/'

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

    def _sequence_range_check(self, result, last):
        """Swap range if backwards in sequence."""

        first = result[-2]
        v1 = ord(first[1:2] if len(first) > 1 else first)
        v2 = ord(last[1:2] if len(last) > 1 else last)
        if v2 < v1:
            result[-2] = '\\' + last
            result.append(first)
        else:
            result.append(last)

    def _sequence(self, i):
        """Handle fnmatch character group."""

        result = ['[']

        c = next(i)
        if c in ('!', '^'):
            # Handle negate char
            result.append('^')
            c = next(i)
        if c in ('-', '[', ']'):
            result.append(re.escape(c))
            c = next(i)

        end_range = 0
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
                    end_range = i.index
                elif end_range and i.index - 1 >= end_range:
                    self._sequence_range_check(result, '\\' + c)
                    end_range = 0
                else:
                    result.append('\\' + c)
                c = next(i)
                continue

            if c == '\\':
                # Handle escapes
                subindex = i.index
                try:
                    value = self._references(i, True)
                except PathNameException:
                    raise StopIteration
                except StopIteration:
                    i.rewind(i.index - subindex)
                    value = r'\\'
            elif c == '/':
                if self.pathname:
                    raise StopIteration
                value = c
            elif c in SET_OPERATORS:
                # Escape &, |, and ~ to avoid &&, ||, and ~~
                value = '\\' + c
            else:
                # Anything else
                value = c

            if end_range and i.index - 1 >= end_range:
                self._sequence_range_check(result, value)
                end_range = 0
            else:
                result.append(value)

            c = next(i)

        result.append(']')
        if self.pathname or (self.after_start and self.dot):
            return self._restrict_sequence() + ''.join(result)

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
                    value = self.get_path_sep() + '+'
                    self.set_start_dir()
                else:
                    value = self._restrict_sequence() + value
        elif c == '/':
            # \/
            if sequence and self.pathname:
                raise PathNameException
            if self.pathname:
                value = r'\\'
                if self.in_list:
                    value = value + self._restrict_sequence()
                i.rewind(1)
            else:
                value = re.escape(c)
        else:
            # \a, \b, \c, etc.
            value = re.escape(c)
        return value

    def _handle_star(self, i, current):
        """Handle star."""

        if self.pathname:
            if self.after_start and self.dot:
                star = self.path_star_dot2
                globstar = self.path_gstar_dot2
            elif self.after_start:
                star = self.path_star_dot1
                globstar = self.path_gstar_dot1
            else:
                star = self.path_star
                globstar = self.path_gstar_dot1
        else:
            star = '.*?'
            globstar = ''
        value = star

        if self.after_start and self.globstar and not self.in_list:
            skip = False
            try:
                c = next(i)
                if c != '*':
                    i.rewind(1)
                    raise StopIteration
            except StopIteration:
                # Could not acquire a second star, so assume single star pattern
                skip = True

            if not skip:
                try:
                    index = i.index
                    c = next(i)
                    if c == '\\':
                        try:
                            self._references(i, True)
                            # Was not what we expected
                            # Assume two single stars
                        except PathNameException:
                            # Looks like escape was a valid slash
                            # Store pattern accordingly
                            value = globstar
                        except StopIteration:
                            # Ran out of characters so assume backslash
                            # count as a double star
                            if self.sep == '\\':
                                value = globstar
                    elif c == '/' and not self.bslash_abort:
                        value = globstar

                    if value != globstar:
                        i.rewind(i.index - index)
                except StopIteration:
                    # Could not acquire directory slash due to no more characters
                    # Use double star
                    value = globstar

        if self.after_start and value != globstar:
            value = '(?=.)' + value

        self.reset_dir_track()
        if value == globstar:
            sep = '(?:^|$|%s)+' % self.get_path_sep()
            if current[-1] == '|':
                # Special case following `|` in a extglob group.
                # We can't follow a path separator in this scenario,
                # so we're safe.
                current.append(value)
            elif current[-1] == '':
                # At the beginning of the pattern
                current[-1] = value
            else:
                # Replace the last path separator
                current[-1] = '(?=.)'
                current.append(value)
            self.consume_path_sep(i)
            current.append(sep)
            self.set_start_dir()
        else:
            current.append(value)

    def clean_up_inverse(self, current, default=None):
        """
        Clean up current.

        Python doesn't have variable lookbehinds, so we have to do negative lookaheads.
        !(...) when converted to regular expression is atomic, so once it matches, that's it.
        So we use the pattern `(?:(?!(?:stuff|to|exclude)<x>))[^/]*?)` where <x> is everything
        that comes after the negative group. `!(this|that)other` --> `(?:(?!(?:this|that)other))[^/]*?)`.

        We have to update the list before | in nested cases: *(!(...)|stuff). Before we close a parent
        extglob: `*(!(...))`. And of course on path separators (when path mode is on): `!(...)/stuff`.
        Lastly we make sure all is accounted for when finishing the pattern at the end.  If there is nothing
        to store, we store `$`: `(?:(?!(?:this|that)$))[^/]*?)`.
        """

        if not self.inv_ext:
            return

        if default is None:
            default = ''

        index = len(current) - 1
        while index >= 0:
            if current[index] is None:
                content = current[index + 1:]
                current[index] = (''.join(content) if content else default) + (')[^%s]*?)' % self.get_path_sep())
            index -= 1
        self.inv_ext = 0

    def parse_extend(self, c, i, current):
        """Parse extended pattern lists."""

        # Save state
        temp_dir_start = self.dir_start
        temp_after_start = self.after_start
        temp_in_list = self.in_list
        temp_inv_ext = self.inv_ext
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
                    self._handle_star(i, extended)
                elif c == '?':
                    if not self.pathname:
                        extended.append(self._restrict_sequence() + '.')
                    else:
                        if self.after_start:
                            extended.append('[^.]' if self.dot else '.')
                        else:
                            extended.append('.')
                        self.reset_dir_track()
                elif c == '/':
                    if self.pathname:
                        extended.append(self._restrict_sequence())
                    extended.append(c)
                elif c == "|":
                    self.clean_up_inverse(extended)
                    extended.append(c)
                    if self.pathname and temp_after_start:
                        self.set_start_dir()
                elif c == '\\':
                    subindex = i.index
                    try:
                        extended.append(self._references(i))
                    except StopIteration:
                        i.rewind(i.index - subindex)
                        if self.bslash_abort:
                            extended.append(self._restrict_sequence())
                        extended.append(r'\\')
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

            self.clean_up_inverse(extended)
            if list_type == '?':
                current.extend(['(?:'] + extended + [')?'])
            elif list_type == '*':
                current.extend(['(?:'] + extended + [')*'])
            elif list_type == '+':
                current.extend(['(?:'] + extended + [')+'])
            elif list_type == '@':
                current.extend(['(?:'] + extended + [')'])
            elif list_type == '!':
                self.inv_ext += 1
                # If pattern is at the end, anchor the match to the end.
                current.extend(['(?:(?!(?:'] + extended + [')'])
                current.append(None)

        except StopIteration:
            success = False
            self.inv_ext = temp_inv_ext
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

    def get_path_sep(self):
        """Get path separator."""

        return re.escape(self.sep)

    def consume_path_sep(self, i):
        """Consume any consecutive path separators are they count as one."""

        try:
            if self.bslash_abort:
                count = -1
                c = '\\'
                while c == '\\':
                    count += 1
                    c = next(i)
                i.rewind(1)
                # Rewind one more if we have an odd number (escape): \\\*
                if count > 0 and count % 2:
                    i.rewind(1)
            else:
                c = '/'
                while c == '/':
                    c = next(i)
                i.rewind(1)
        except StopIteration:
            pass

    def root(self, pattern, current):
        """Start parsing the pattern."""

        self.set_after_start()
        i = util.StringIter(pattern)
        iter(i)
        if self.win_drive_detect:
            m = RE_WIN_PATH.match(pattern)
            if m:
                drive = m.group(0).replace('\\\\', '\\')
                current.append(re.escape(drive))
                i.advance(m.end(0))
                self.consume_path_sep(i)

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
                self._handle_star(i, current)
            elif c == '?':
                if self.pathname:
                    current.append(self._restrict_sequence() + '.')
                else:
                    if self.after_start:
                        current.append('[^.]' if self.dot else '.')
                    else:
                        current.append('.')
                    self.reset_dir_track()
            elif c == '/':
                if self.pathname:
                    self.set_start_dir()
                    self.clean_up_inverse(current)
                    current.append(self.get_path_sep() + '+')
                    self.consume_path_sep(i)
                else:
                    current.append(self.get_path_sep())
            elif c == '\\':
                index = i.index
                try:
                    value = self._references(i)
                    if self.dir_start:
                        self.clean_up_inverse(current)
                        self.consume_path_sep(i)
                    current.append(value)
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
        self.clean_up_inverse(current, default='$')
        if self.pathname:
            current.append('[' + re.escape(self.sep) + ']*?')

    def parse(self):
        """Parse pattern list."""

        result = []
        exclude_result = []
        empty_include = True
        empty_exclude = True
        exclude_pattern = None
        pattern = None

        for pat in self.pattern:
            pat = util.norm_pattern(pat, self.pathname, self.raw_chars)

            try:
                expanded = bracex.expand(pat, keep_escapes=True) if self.braces else [pat]
            except Exception as e:
                expanded = [pat]

            for p in expanded:
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
            pattern = r'^(?s%s:%s)$' % (case_flag, ''.join(result))
            if exclude_result:
                exclude_pattern = r'^(?s%s:%s)$' % (case_flag, ''.join(exclude_result))
        else:
            pattern = r'(?ms%s)^(?:%s)$' % (case_flag, ''.join(result))
            if exclude_result:
                exclude_pattern = r'(?ms%s)^(?:%s)$' % (case_flag, ''.join(exclude_result))

        if self.is_bytes:
            if pattern is not None:
                pattern = pattern.encode('latin-1')
            if exclude_pattern is not None:
                exclude_pattern = exclude_pattern.encode('latin-1')
        return pattern, exclude_pattern


class FnMatch(util.Immutable):
    """File name match object."""

    __slots__ = ("_include", "_exclude", "_hash")

    def __init__(self, include, exclude=None):
        """Initialization."""

        super(FnMatch, self).__init__(
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
            isinstance(other, FnMatch) and
            self._include == other._include and
            self._exclude == other._exclude
        )

    def __ne__(self, other):
        """Equal."""

        return (
            not isinstance(other, FnMatch) or
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
    return FnMatch, (p._include, p._exclude)


copyreg.pickle(FnMatch, _pickle)


def fnsplit(pattern, *, flags=0):
    """Split pattern by '|'."""

    return FnSplit(pattern, flags).split()


def translate(patterns, *, flags=0):
    """Translate fnmatch pattern counting `|` as a separator and `-` as a negative pattern."""

    return FnParse(util.to_tuple(patterns), flags & FLAG_MASK).parse()


def fnmatch(filename, patterns, *, flags=0):
    """
    Check if filename matches pattern.

    By default case sensitivity is determined by the filesystem,
    but if `case_sensitive` is set, respect that instead.
    """

    return _compile(util.to_tuple(patterns), flags & FLAG_MASK).match(util.norm_slash(filename))


def filter(filenames, patterns, *, flags=0):  # noqa A001
    """Filter names using pattern."""

    matches = []

    obj = _compile(util.to_tuple(patterns), flags & FLAG_MASK)

    for filename in filenames:
        filename = util.norm_slash(filename)
        if obj.match(filename):
            matches.append(filename)
    return matches
