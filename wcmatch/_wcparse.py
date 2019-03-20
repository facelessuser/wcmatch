"""
Wild Card Match.

A custom implementation of `fnmatch`.

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
import functools
import copyreg
import bracex
from collections import namedtuple
from . import util
from backrefs import uniprops

RE_WIN_PATH = re.compile(r'((?:\\\\|/){2}[^\\/]+(?:\\\\|/){1}[^\\/]+|[a-z]:)((?:\\\\|/){1}|$)')
RE_BWIN_PATH = re.compile(br'((?:\\\\|/){2}[^\\/]+(?:\\\\|/){1}[^\\/]+|[a-z]:)((?:\\\\|/){1}|$)')
RE_WIN_MAGIC = re.compile(r'([-!*?(\[|^{]|(?<!\\)(?:(?:[\\]{2})*)\\(?!\\))')
RE_BWIN_MAGIC = re.compile(br'([-!*?(\[|^{]|(?<!\\)(?:(?:[\\]{2})*)\\(?!\\))')
RE_MAGIC = re.compile(r'([-!*?(\[|^{\\])')
RE_BMAGIC = re.compile(br'([-!*?(\[|^{\\])')
RE_POSIX = re.compile(r':(alnum|alpha|ascii|blank|cntrl|digit|graph|lower|print|punct|space|upper|xdigit):\]')

SET_OPERATORS = frozenset(('&', '~', '|'))
NEGATIVE_SYM = frozenset((b'!', '!'))
MINUS_NEGATIVE_SYM = frozenset((b'-', '-'))
EXT_TYPES = frozenset(('*', '?', '+', '@', '!'))

FORCECASE = 0x0001
IGNORECASE = 0x0002
RAWCHARS = 0x0004
NEGATE = 0x0008
MINUSNEGATE = 0x0010
PATHNAME = 0x0020
DOTMATCH = 0x0040
EXTMATCH = 0x0080
GLOBSTAR = 0x0100
BRACE = 0x0200

# Internal flag
_FORCEWIN = 0x10000

FLAG_MASK = (
    FORCECASE |
    IGNORECASE |
    RAWCHARS |
    NEGATE |
    MINUSNEGATE |
    PATHNAME |
    DOTMATCH |
    EXTMATCH |
    GLOBSTAR |
    BRACE |
    _FORCEWIN
)
CASE_FLAGS = FORCECASE | IGNORECASE

# Pieces to construct search path

# Question Mark
_QMARK = r'.'
# Star
_STAR = r'.*?'
# For paths, allow trailing /
_PATH_TRAIL = r'[%s]*?'
# Disallow . and .. (usually applied right after path separator when needed)
_NO_DIR = r'(?!(?:\.{1,2})(?:$|%(sep)s))'
# Star for `PATHNAME`
_PATH_STAR = r'[^%(sep)s]*?'
# Star when at start of filename during `DOTMATCH`
# (allow dot, but don't allow directory match /./ or /../)
_PATH_STAR_DOTMATCH = _NO_DIR + _PATH_STAR
# Star for `PATHNAME` when `DOTMATCH` is disabled and start is at start of file.
# Disallow . and .. and don't allow match to start with a dot.
_PATH_STAR_NO_DOTMATCH = _NO_DIR + (r'(?:(?!\.)%s)?' % _PATH_STAR)
# `GLOBSTAR` during `DOTMATCH`. Avoid directory match /./ or /../
_PATH_GSTAR_DOTMATCH = r'(?:(?!(?:%(sep)s|^)(?:\.{1,2})($|%(sep)s)).)*?'
# `GLOBSTAR` with `DOTMATCH` disabled. Don't allow a dot to follow /
_PATH_GSTAR_NO_DOTMATCH = r'(?:(?!(?:%(sep)s|^)\.).)*?'
# Next char cannot be a dot
_NO_DOT = r'(?![.])'
# Following char from sequence cannot be a separator or a dot
_PATH_NO_SLASH_DOT = r'(?![%(sep)s.])'
# Following char from sequence cannot be a separator
_PATH_NO_SLASH = r'(?![%(sep)s])'
# One or more
_ONE_OR_MORE = r'+'
# End of pattern
_EOP = r'$'
# Divider between `globstar`. Can match start or end of pattern
# in addition to slashes.
_GLOBSTAR_DIV = r'(?:^|$|%s)+'
# Lookahead to see there is one character.
_NEED_CHAR = r'(?=.)'
_NEED_SEP = r'(?=%s)'
# Group that matches one or none
_QMARK_GROUP = r'(?:%s)?'
# Group that matches Zero or more
_STAR_GROUP = r'(?:%s)*'
# Group that matches one or more
_PLUS_GROUP = r'(?:%s)+'
# Group that matches exactly one
_GROUP = r'(?:%s)'
# Inverse group that matches none
# This is the start. Since Python can't
# do variable look behinds, we have stuff
# everything at the end that it needs to lookahead
# for. So there is an opening and a closing.
_EXCLA_GROUP = r'(?:(?!(?:%s)'
# Closing for inverse group
_EXCLA_GROUP_CLOSE = r')%s)'


class InvPlaceholder(str):
    """Placeholder for inverse pattern !(...)."""


class WcGlob(namedtuple('WcGlob', ['pattern', 'is_magic', 'is_globstar', 'dir_only', 'is_drive'])):
    """File Glob."""


class PathNameException(Exception):
    """Path name exception."""


def is_negative(pattern, flags):
    """Check if negative pattern."""

    if flags & MINUSNEGATE:
        return flags & NEGATE and pattern[0:1] in MINUS_NEGATIVE_SYM
    else:
        return flags & NEGATE and pattern[0:1] in NEGATIVE_SYM


def expand_braces(patterns, flags):
    """Expand braces."""

    if flags & BRACE:
        for p in ([patterns] if isinstance(patterns, (str, bytes)) else patterns):
            try:
                yield from bracex.iexpand(p, keep_escapes=True)
            except Exception:  # pragma: no cover
                # We will probably never hit this as `bracex`
                # doesn't throw any specific exceptions and
                # should normally always parse, but just in case.
                yield p
    else:
        for p in ([patterns] if isinstance(patterns, (str, bytes)) else patterns):
            yield p


def get_case(flags):
    """Parse flags for case sensitivity settings."""

    if not bool(flags & CASE_FLAGS):
        case_sensitive = util.is_case_sensitive()
    elif flags & FORCECASE:
        case_sensitive = True
    else:
        case_sensitive = False
    return case_sensitive


def is_unix_style(flags):
    """Check if we should use Unix style."""

    return util.platform() != "windows" or get_case(flags)


def translate(patterns, flags):
    """Translate patterns."""

    positive = []
    negative = []
    if isinstance(patterns, (str, bytes)):
        patterns = [patterns]

    for pattern in patterns:
        for expanded in expand_braces(pattern, flags):
            (negative if is_negative(expanded, flags) else positive).append(
                WcParse(expanded, flags & FLAG_MASK).parse()
            )

    return positive, negative


def compile(patterns, flags):  # noqa A001
    """Compile patterns."""

    positive = []
    negative = []
    if isinstance(patterns, (str, bytes)):
        patterns = [patterns]

    for pattern in patterns:
        for expanded in expand_braces(pattern, flags):
            (negative if is_negative(expanded, flags) else positive).append(_compile(expanded, flags))

    return WcRegexp(tuple(positive), tuple(negative))


@functools.lru_cache(maxsize=256, typed=True)
def _compile(pattern, flags):
    """Compile the pattern to regex."""

    return re.compile(WcParse(pattern, flags & FLAG_MASK).parse())


class WcPathSplit(object):
    """
    Split glob pattern on "magic" file and directories.

    Glob pattern return a list of pieces. Each piece will either
    be consecutive literal file parts or individual glob parts.
    Each part will will contain info regarding whether they are
    a directory pattern or a file pattern and whether the part
    is "magic": ["pattern", is_magic, is_directory]. Is directory
    is determined by a trailing OS separator on the part.

    Example:

        "**/this/is_literal/*magic?/@(magic|part)"

        Would  become:

        [
            ["**", True, True],
            ["this/is_literal/", False, True],
            ["*magic?", True, True],
            ["@(magic|part)", True, True]
        ]
    """

    def __init__(self, pattern, flags):
        """Initialize."""

        self.unix = is_unix_style(flags) and not flags & _FORCEWIN
        self.flags = flags
        self.pattern = util.norm_pattern(pattern, not self.unix, flags & RAWCHARS)
        if is_negative(self.pattern, flags):  # pragma: no cover
            # This isn't really used, but we'll keep it around
            # in case we find a reason to directly send inverse patterns
            # Through here.
            self.pattern = self.pattern[0:1]
        if flags & NEGATE:
            flags ^= NEGATE
        self.flags = flags
        self.is_bytes = isinstance(pattern, bytes)
        self.extend = bool(flags & EXTMATCH)
        if not self.unix:
            self.win_drive_detect = True
            self.bslash_abort = True
            self.sep = '\\'
        else:
            self.win_drive_detect = False
            self.bslash_abort = False
            self.sep = '/'
        # Once split, Windows file names will never have `\\` in them,
        # so we can use the Unix magic detect
        self.re_magic = RE_MAGIC if not self.is_bytes else RE_BMAGIC
        self.magic = False

    def is_magic(self, name):
        """Check if name contains magic characters."""

        return self.re_magic.search(name) is not None

    def _sequence(self, i):
        """Handle character group."""

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
                raise StopIteration
            c = next(i)

    def _references(self, i, sequence=False):
        """Handle references."""

        value = ''

        c = next(i)
        if c == '\\':
            # \\
            if sequence and self.bslash_abort:
                raise PathNameException
            value = c
        elif c == '/':
            # \/
            if sequence:
                raise PathNameException
            i.rewind(1)
        else:
            # \a, \b, \c, etc.
            pass
        return value

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

                if self.extend and c in EXT_TYPES and self.parse_extend(c, i):
                    continue

                if c == '\\':
                    try:
                        self._references(i)
                    except StopIteration:
                        pass
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

    def store(self, value, l, dir_only):
        """Group patterns by literals and potential magic patterns."""

        if l and value in (b'', ''):
            return

        globstar = value in (b'**', '**')
        magic = self.is_magic(value)
        if magic:
            value = compile(value, self.flags)
        l.append(WcGlob(value, magic, globstar, dir_only, False))

    def split(self):
        """Start parsing the pattern."""

        split_index = []
        parts = []
        start = -1

        pattern = self.pattern.decode('latin-1') if self.is_bytes else self.pattern

        i = util.StringIter(pattern)
        iter(i)

        # Detect and store away windows drive as a literal
        if self.win_drive_detect:
            m = RE_WIN_PATH.match(pattern)
            if m:
                drive = m.group(0).replace('\\\\', '\\')
                if self.is_bytes:
                    drive = drive.encode('latin-1')
                parts.append(WcGlob(drive, False, False, True, True))
                start = m.end(0) - 1
                i.advance(start + 1)

        for c in i:
            if self.extend and c in EXT_TYPES and self.parse_extend(c, i):
                continue

            if c == '\\':
                index = i.index
                value = ''
                try:
                    value = self._references(i)
                    if self.bslash_abort and value == '\\':
                        split_index.append((i.index - 2, 1))
                except StopIteration:
                    i.rewind(i.index - index)
                    if self.bslash_abort:
                        split_index.append((i.index - 1, 0))
            elif c == '/':
                split_index.append((i.index - 1, 0))
            elif c == '[':
                index = i.index
                try:
                    self._sequence(i)
                except StopIteration:
                    i.rewind(i.index - index)

        for split, offset in split_index:
            if self.is_bytes:
                value = pattern[start + 1:split].encode('latin-1')
            else:
                value = pattern[start + 1:split]
            self.store(value, parts, True)
            start = split + offset

        if start < len(pattern):
            if self.is_bytes:
                value = pattern[start + 1:].encode('latin-1')
            else:
                value = pattern[start + 1:]
            if value:
                self.store(value, parts, False)
        if len(pattern) == 0:
            parts.append(WcGlob(pattern.encode('latin-1') if self.is_bytes else pattern, False, False, False, False))

        return parts


class WcSplit(object):
    """Class that splits patterns on |."""

    def __init__(self, pattern, flags):
        """Initialize."""

        self.pattern = pattern
        self.is_bytes = isinstance(pattern, bytes)
        self.pathname = bool(flags & PATHNAME)
        self.extend = bool(flags & EXTMATCH)
        self.unix = is_unix_style(flags) and not flags & _FORCEWIN
        self.bslash_abort = not self.unix

    def _sequence(self, i):
        """Handle character group."""

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

                if self.extend and c in EXT_TYPES and self.parse_extend(c, i):
                    continue

                if c == '\\':
                    try:
                        self._references(i)
                    except StopIteration:
                        pass
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
            if self.extend and c in EXT_TYPES and self.parse_extend(c, i):
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
            p = pattern[start + 1:split]
            parts.append(p.encode('latin-1') if self.is_bytes else p)
            start = split

        if start < len(pattern):
            p = pattern[start + 1:]
            parts.append(p.encode('latin-1') if self.is_bytes else p)

        return tuple(parts)


class WcParse(object):
    """Parse the wildcard pattern."""

    def __init__(self, pattern, flags=0):
        """Initialize."""

        self.pattern = pattern
        self.braces = bool(flags & BRACE)
        self.is_bytes = isinstance(pattern, bytes)
        self.pathname = bool(flags & PATHNAME)
        self.raw_chars = bool(flags & RAWCHARS)
        self.globstar = self.pathname and bool(flags & GLOBSTAR)
        self.dot = bool(flags & DOTMATCH)
        self.extend = bool(flags & EXTMATCH)
        self.case_sensitive = get_case(flags)
        self.in_list = False
        self.flags = flags
        self.inv_ext = 0
        self.unix = is_unix_style(self.flags) and not self.flags & _FORCEWIN
        if not self.unix:
            self.win_drive_detect = self.pathname
            self.char_avoid = (ord('\\'), ord('/'), ord('.'))
            self.bslash_abort = self.pathname
            self.sep = '\\'
        else:
            self.win_drive_detect = False
            self.char_avoid = (ord('/'), ord('.'))
            self.bslash_abort = False
            self.sep = '/'
        sep = {"sep": re.escape(self.sep)}
        self.seq_path = _PATH_NO_SLASH % sep
        self.seq_path_dot = _PATH_NO_SLASH_DOT % sep
        self.path_star = _PATH_STAR % sep
        self.path_star_dot1 = _PATH_STAR_DOTMATCH % sep
        self.path_star_dot2 = _PATH_STAR_NO_DOTMATCH % sep
        self.path_gstar_dot1 = _PATH_GSTAR_DOTMATCH % sep
        self.path_gstar_dot2 = _PATH_GSTAR_NO_DOTMATCH % sep

    def set_after_start(self):
        """Set tracker for character after the start of a directory."""

        self.after_start = True
        self.dir_start = False

    def set_start_dir(self):
        """Set directory start."""

        self.dir_start = True
        self.after_start = False

    def reset_dir_track(self):
        """Reset directory tracker."""

        self.dir_start = False
        self.after_start = False

    def update_dir_state(self):
        """
        Update the directory state.

        If we are at the directory start,
        update to after start state (the character right after).
        If at after start, reset state.
        """

        if self.dir_start and not self.after_start:
            self.set_after_start()
        elif not self.dir_start and self.after_start:
            self.reset_dir_track()

    def _restrict_sequence(self):
        """Restrict sequence."""

        if self.pathname:
            value = self.seq_path_dot if self.after_start and not self.dot else self.seq_path
        else:
            value = _NO_DOT if self.after_start and not self.dot else ""
        self.reset_dir_track()

        return value

    def _sequence_range_check(self, result, last):
        """
        If range backwards, remove it.

        A bad range will cause the regular expression to fail,
        so we need to remove it, but return that we removed it
        so the caller can know the sequence wasn't empty.
        Caller will have to craft a sequence that makes sense
        if empty at the end with either an impossible sequence
        for inclusive sequences or a sequence that matches
        everything for an exclusive sequence.
        """

        removed = False
        first = result[-2]
        v1 = ord(first[1:2] if len(first) > 1 else first)
        v2 = ord(last[1:2] if len(last) > 1 else last)
        if v2 < v1:
            result.pop()
            result.pop()
            removed = True
        else:
            result.append(last)
        return removed

    def _handle_posix(self, i, result, end_range):
        """Handle posix classes."""

        last_posix = False
        m = i.match(RE_POSIX)
        if m:
            last_posix = True
            # Cannot do range with posix class
            # so escape last `-` if we think this
            # is the end of a range.
            if end_range and i.index - 1 >= end_range:
                result[-1] = '\\' + result[-1]
            posix_type = uniprops.POSIX_BYTES if self.is_bytes else uniprops.POSIX
            result.append(uniprops.get_posix_property(m.group(1), posix_type))
        return last_posix

    def _sequence(self, i):
        """Handle character group."""

        result = ['[']
        end_range = 0
        escape_hyphen = -1
        removed = False
        last_posix = False

        c = next(i)
        if c in ('!', '^'):
            # Handle negate char
            result.append('^')
            c = next(i)
        if c == '[':
            last_posix = self._handle_posix(i, result, 0)
            if not last_posix:
                result.append(re.escape(c))
            c = next(i)
        elif c in ('-', ']'):
            result.append(re.escape(c))
            c = next(i)

        while c != ']':
            if c == '-':
                if last_posix:
                    result.append('\\' + c)
                    last_posix = False
                elif i.index - 1 > escape_hyphen:
                    # Found a range delimiter.
                    # Mark the next two characters as needing to be escaped if hyphens.
                    # The next character would be the end char range (s-e),
                    # and the one after that would be the potential start char range
                    # of a new range (s-es-e), so neither can be legitimate range delimiters.
                    result.append(c)
                    escape_hyphen = i.index + 1
                    end_range = i.index
                elif end_range and i.index - 1 >= end_range:
                    if self._sequence_range_check(result, '\\' + c):
                        removed = True
                    end_range = 0
                else:
                    result.append('\\' + c)
                c = next(i)
                continue
            last_posix = False

            if c == '[':
                last_posix = self._handle_posix(i, result, end_range)
                if last_posix:
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
                if self._sequence_range_check(result, value):
                    removed = True
                end_range = 0
            else:
                result.append(value)

            c = next(i)

        result.append(']')
        # Bad range removed.
        if removed:
            value = "".join(result)
            if value == '[]':
                # We specified some ranges, but they are all
                # out of reach.  Create an impossible sequence to match.
                result = ['[^%s]' % ('\x00-\xff' if self.is_bytes else uniprops.UNICODE_RANGE)]
            elif value == '[^]':
                # We specified some range, but hey are all
                # out of reach. Since this is exclusive
                # that means we can match *anything*.
                result = ['[%s]' % ('\x00-\xff' if self.is_bytes else uniprops.UNICODE_RANGE)]
            else:
                result = [value]

        if self.pathname or (self.after_start and not self.dot):
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
                    value = self.get_path_sep() + _ONE_OR_MORE
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
                    value = self._restrict_sequence() + value
                i.rewind(1)
            else:
                value = re.escape(c)
        elif self.in_list and not sequence and self.after_start and c == '.':
            value = _NO_DOT + re.escape(c)
        else:
            # \a, \b, \c, etc.
            value = re.escape(c)
        return value

    def _handle_star(self, i, current):
        """Handle star."""

        if self.pathname:
            if self.after_start and not self.dot:
                star = self.path_star_dot2
                globstar = self.path_gstar_dot2
            elif self.after_start:
                star = self.path_star_dot1
                globstar = self.path_gstar_dot1
            else:
                star = self.path_star
                globstar = self.path_gstar_dot1
        else:
            if self.after_start and not self.dot:
                star = _NO_DOT + _STAR
            else:
                star = _STAR
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
            value = _NEED_CHAR + value
            # Consume duplicate starts
            try:
                c = next(i)
                while c == '*':
                    c = next(i)
                i.rewind(1)
            except StopIteration:
                pass

        self.reset_dir_track()
        if value == globstar:
            sep = _GLOBSTAR_DIV % self.get_path_sep()
            # Check if the last entry was a `globstar`
            # If so, don't bother adding another.
            if current[-1] != sep:
                if current[-1] == '':
                    # At the beginning of the pattern
                    current[-1] = value
                else:
                    # Replace the last path separator
                    current[-1] = _NEED_SEP % self.get_path_sep()
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
        `extmatch`: `*(!(...))`. And of course on path separators (when path mode is on): `!(...)/stuff`.
        Lastly we make sure all is accounted for when finishing the pattern at the end.  If there is nothing
        to store, we store `$`: `(?:(?!(?:this|that)$))[^/]*?)`.
        """

        if not self.inv_ext:
            return

        if default is None:
            default = ''

        index = len(current) - 1
        while index >= 0:
            if isinstance(current[index], InvPlaceholder):
                content = current[index + 1:]
                current[index] = (''.join(content) if content else default) + (_EXCLA_GROUP_CLOSE % str(current[index]))
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

                if self.extend and c in EXT_TYPES and self.parse_extend(c, i, extended):
                    # Nothing more to do
                    pass
                elif c == '*':
                    self._handle_star(i, extended)
                elif c == '.' and not self.dot and self.after_start:
                    extended.append(_NO_DOT + re.escape(c))
                    self.reset_dir_track()
                elif c == '?':
                    extended.append(self._restrict_sequence() + _QMARK)
                elif c == '/':
                    if self.pathname:
                        extended.append(self._restrict_sequence())
                    extended.append(re.escape(c))
                elif c == "|":
                    self.clean_up_inverse(extended)
                    extended.append(c)
                    if temp_after_start:
                        self.set_start_dir()
                elif c == '\\':
                    try:
                        extended.append(self._references(i))
                    except StopIteration:
                        # We've reached the end.
                        # Do nothing because this is going to abort the `extmatch` anyways.
                        pass
                elif c == '[':
                    subindex = i.index
                    try:
                        extended.append(self._sequence(i))
                    except StopIteration:
                        i.rewind(i.index - subindex)
                        extended.append(r'\[')
                elif c != ')':
                    extended.append(re.escape(c))

                self.update_dir_state()

            self.clean_up_inverse(extended)
            if list_type == '?':
                current.append(_QMARK_GROUP % ''.join(extended))
            elif list_type == '*':
                current.append(_STAR_GROUP % ''.join(extended))
            elif list_type == '+':
                current.append(_PLUS_GROUP % ''.join(extended))
            elif list_type == '@':
                current.append(_GROUP % ''.join(extended))
            elif list_type == '!':
                self.inv_ext += 1
                # If pattern is at the end, anchor the match to the end.
                current.append(_EXCLA_GROUP % ''.join(extended))
                if self.pathname:
                    if temp_after_start and not self.dot:
                        star = self.path_star_dot2
                    elif temp_after_start:
                        star = self.path_star_dot1
                    else:
                        star = self.path_star
                else:
                    if temp_after_start and not self.dot:
                        star = _NO_DOT + _STAR
                    else:
                        star = _STAR
                if temp_after_start:
                    star = _NEED_CHAR + star
                # Place holder for closing, but store the proper star
                # so we know which one to use
                current.append(InvPlaceholder(star))

        except StopIteration:
            success = False
            self.inv_ext = temp_inv_ext
            i.rewind(i.index - index)

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
                if drive.endswith('\\'):
                    slash = True
                drive = drive[:-1]
                current.append(re.escape(drive))
                if slash:
                    current.append(self.get_path_sep() + _ONE_OR_MORE)
                i.advance(m.end(0))
                self.consume_path_sep(i)

        for c in i:

            index = i.index
            if self.extend and c in EXT_TYPES and self.parse_extend(c, i, current):
                # Nothing to do
                pass
            elif c == '*':
                self._handle_star(i, current)
            elif c == '?':
                current.append(self._restrict_sequence() + _QMARK)
            elif c == '/':
                if self.pathname:
                    self.set_start_dir()
                    self.clean_up_inverse(current)
                    current.append(self.get_path_sep() + _ONE_OR_MORE)
                    self.consume_path_sep(i)
                else:
                    current.append(re.escape(c))
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
                    current.append(re.escape(c))
            elif c == '[':
                index = i.index
                try:
                    current.append(self._sequence(i))
                except StopIteration:
                    i.rewind(i.index - index)
                    current.append(re.escape(c))
            else:
                current.append(re.escape(c))

            self.update_dir_state()

        self.clean_up_inverse(current, default=_EOP)
        if self.pathname:
            current.append(_PATH_TRAIL % self.get_path_sep())

    def parse(self):
        """Parse pattern list."""

        result = ['']
        negative = False

        p = util.norm_pattern(self.pattern, not self.unix, self.raw_chars)

        p = p.decode('latin-1') if self.is_bytes else p
        if is_negative(p, self.flags):
            negative = True
            p = p[1:]

        self.root(p, result)

        case_flag = 'i' if not self.case_sensitive else ''
        if util.PY36:
            pattern = (r'^(?!(?s%s:%s)$).*?$' if negative else r'^(?s%s:%s)$') % (case_flag, ''.join(result))
        else:
            pattern = (r'(?s%s)^(?!(?:%s)$).*?$' if negative else r'(?s%s)^(?:%s)$') % (case_flag, ''.join(result))

        if self.is_bytes:
            pattern = pattern.encode('latin-1')

        return pattern


class WcRegexp(util.Immutable):
    """File name match object."""

    __slots__ = ("_include", "_exclude", "_hash")

    def __init__(self, include, exclude=None):
        """Initialization."""

        super(WcRegexp, self).__init__(
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
            isinstance(other, WcRegexp) and
            self._include == other._include and
            self._exclude == other._exclude
        )

    def __ne__(self, other):
        """Equal."""

        return (
            not isinstance(other, WcRegexp) or
            self._include != other._include or
            self._exclude != other._exclude
        )

    def match(self, filename):
        """Match filename."""

        matched = False
        for x in self._include:
            if x.fullmatch(filename):
                matched = True
                break

        if not self._include and self._exclude:
            matched = True

        if matched:
            matched = True
            if self._exclude:
                for x in self._exclude:
                    if not x.fullmatch(filename):
                        matched = False
                        break
        return matched


def _pickle(p):
    return WcRegexp, (p._include, p._exclude)


copyreg.pickle(WcRegexp, _pickle)
