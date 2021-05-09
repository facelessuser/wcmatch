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
import re
import functools
import bracex
import os
from . import util
from . import posix
from . _wcmatch import WcRegexp

UNICODE_RANGE = '\u0000-\U0010ffff'
ASCII_RANGE = '\x00-\xff'

PATTERN_LIMIT = 1000

RE_WIN_DRIVE_START = re.compile(r'((?:\\\\|/){2}((?:\\[^\\/]|[^\\/])+)|([\\]?[a-z][\\]?:))((?:\\\\|/)|$)', re.I)
RE_WIN_DRIVE_LETTER = re.compile(r'([a-z]:)((?:\\|/)|$)', re.I)
RE_WIN_DRIVE_PART = re.compile(r'((?:\\[^\\/]|[^\\/])+)((?:\\\\|/)|$)', re.I)
RE_WIN_DRIVE_UNESCAPE = re.compile(r'\\(.)', re.I)

RE_WIN_DRIVE = (
    re.compile(
        r'''(?x)
        (
            (?:\\\\|/){2}[?.](?:\\\\|/)(?:
                [a-z]:|
                unc(?:(?:\\\\|/)[^\\/]+){2} |
                (?:global(?:\\\\|/))+(?:[a-z]:|unc(?:(?:\\\\|/)[^\\/]+){2}|[^\\/]+)
            ) |
            (?:\\\\|/){2}[^\\/]+(?:\\\\|/)[^\\/]+|
            [a-z]:
        )((?:\\\\|/){1}|$)
        ''',
        re.I
    ),
    re.compile(
        br'''(?x)
        (
            (?:\\\\|/){2}[?.](?:\\\\|/)(?:
                [a-z]:|
                unc(?:(?:\\\\|/)[^\\/]+){2} |
                (?:global(?:\\\\|/))+(?:[a-z]:|unc(?:(?:\\\\|/)[^\\/]+){2}|[^\\/]+)
            ) |
            (?:\\\\|/){2}[^\\/]+(?:\\\\|/)[^\\/]+|
            [a-z]:
        )((?:\\\\|/){1}|$)
        ''',
        re.I
    )
)

RE_MAGIC_ESCAPE = (
    re.compile(r'([-!~*?()\[\]|{}]|(?<!\\)(?:(?:[\\]{2})*)\\(?!\\))'),
    re.compile(br'([-!~*?()\[\]|{}]|(?<!\\)(?:(?:[\\]{2})*)\\(?!\\))')
)

MAGIC_DEF = (
    frozenset("*?[]\\"),
    frozenset(b"*?[]\\")
)
MAGIC_SPLIT = (
    frozenset("|"),
    frozenset(b"|")
)
MAGIC_NEGATE = (
    frozenset('!'),
    frozenset(b'!')
)
MAGIC_MINUS_NEGATE = (
    frozenset('-'),
    frozenset(b'-')
)
MAGIC_TILDE = (
    frozenset('~'),
    frozenset(b'~')
)
MAGIC_EXTMATCH = (
    frozenset('()'),
    frozenset(b'()')
)
MAGIC_BRACE = (
    frozenset("{}"),
    frozenset(b"{}")
)

RE_MAGIC = (
    re.compile(r'([-!~*?(\[|{\\])'),
    re.compile(br'([-!~*?(\[|{\\])')
)
RE_WIN_DRIVE_MAGIC = (
    re.compile(r'([{}|]|(?<!\\)(?:(?:[\\]{2})*)\\(?!\\))'),
    re.compile(br'([{}|]|(?<!\\)(?:(?:[\\]{2})*)\\(?!\\))')
)
RE_NO_DIR = (
    re.compile(r'^(?:.*?(?:/\.{1,2}/*|/)|\.{1,2}/*)$'),
    re.compile(br'^(?:.*?(?:/\.{1,2}/*|/)|\.{1,2}/*)$')
)
RE_WIN_NO_DIR = (
    re.compile(r'^(?:.*?(?:[\\/]\.{1,2}[\\/]*|[\\/])|\.{1,2}[\\/]*)$'),
    re.compile(br'^(?:.*?(?:[\\/]\.{1,2}[\\/]*|[\\/])|\.{1,2}[\\/]*)$')
)
RE_TILDE = (
    re.compile(r'~[^/]*(?=/|$)'),
    re.compile(br'~[^/]*(?=/|$)')
)
RE_WIN_TILDE = (
    re.compile(r'~(?:\\(?![\\/])|[^\\/])*(?=\\\\|/|$)'),
    re.compile(br'~(?:\\(?![\\/])|[^\\/])*(?=\\\\|/|$)')
)

TILDE_SYM = (
    '~',
    b'~'
)

RE_ANCHOR = re.compile(r'^/+')
RE_WIN_ANCHOR = re.compile(r'^(?:\\\\|/)+')
RE_POSIX = re.compile(r':(alnum|alpha|ascii|blank|cntrl|digit|graph|lower|print|punct|space|upper|word|xdigit):\]')

SET_OPERATORS = frozenset(('&', '~', '|'))
NEGATIVE_SYM = frozenset((b'!', '!'))
MINUS_NEGATIVE_SYM = frozenset((b'-', '-'))
ROUND_BRACKET = frozenset((b'(', '('))
EXT_TYPES = frozenset(('*', '?', '+', '@', '!'))

# Common flags are found between `0x0001 - 0xffffff`
# Implementation specific (`glob` vs `fnmatch` vs `wcmatch`) are found between `0x01000000 - 0xff000000`
# Internal special flags are found at `0x100000000` and above
CASE = 0x0001
IGNORECASE = 0x0002
RAWCHARS = 0x0004
NEGATE = 0x0008
MINUSNEGATE = 0x0010
PATHNAME = 0x0020
DOTMATCH = 0x0040
EXTMATCH = 0x0080
GLOBSTAR = 0x0100
BRACE = 0x0200
REALPATH = 0x0400
FOLLOW = 0x0800
SPLIT = 0x1000
MATCHBASE = 0x2000
NODIR = 0x4000
NEGATEALL = 0x8000
FORCEWIN = 0x10000
FORCEUNIX = 0x20000
GLOBTILDE = 0x40000
NOUNIQUE = 0x80000
NODOTDIR = 0x100000

# Internal flag
_TRANSLATE = 0x100000000  # Lets us know we are performing a translation, and we just want the regex.
_ANCHOR = 0x200000000  # The pattern, if it starts with a slash, is anchored to the working directory; strip the slash.
_EXTMATCHBASE = 0x400000000  # Like `MATCHBASE`, but works for multiple directory levels.
_NOABSOLUTE = 0x800000000  # Do not allow absolute patterns
_RTL = 0x1000000000  # Match from right to left

FLAG_MASK = (
    CASE |
    IGNORECASE |
    RAWCHARS |
    NEGATE |
    MINUSNEGATE |
    PATHNAME |
    DOTMATCH |
    EXTMATCH |
    GLOBSTAR |
    BRACE |
    REALPATH |
    FOLLOW |
    MATCHBASE |
    NODIR |
    NEGATEALL |
    FORCEWIN |
    FORCEUNIX |
    GLOBTILDE |
    SPLIT |
    NOUNIQUE |
    NODOTDIR |
    _TRANSLATE |
    _ANCHOR |
    _EXTMATCHBASE |
    _RTL |
    _NOABSOLUTE
)
CASE_FLAGS = IGNORECASE | CASE

# Pieces to construct search path

# Question Mark
_QMARK = r'.'
# Star
_STAR = r'.*?'
# For paths, allow trailing /
_PATH_TRAIL = r'{}*?'
# Disallow . and .. (usually applied right after path separator when needed)
_NO_DIR = r'(?!(?:\.{{1,2}})(?:$|[{sep}]))'
# Star for `PATHNAME`
_PATH_STAR = r'[^{sep}]*?'
# Star when at start of filename during `DOTMATCH`
# (allow dot, but don't allow directory match /./ or /../)
_PATH_STAR_DOTMATCH = _NO_DIR + _PATH_STAR
# Star for `PATHNAME` when `DOTMATCH` is disabled and start is at start of file.
# Disallow . and .. and don't allow match to start with a dot.
_PATH_STAR_NO_DOTMATCH = _NO_DIR + r'(?:(?!\.){})?'.format(_PATH_STAR)
# `GLOBSTAR` during `DOTMATCH`. Avoid directory match /./ or /../
_PATH_GSTAR_DOTMATCH = r'(?:(?!(?:[{sep}]|^)(?:\.{{1,2}})($|[{sep}])).)*?'
# `GLOBSTAR` with `DOTMATCH` disabled. Don't allow a dot to follow /
_PATH_GSTAR_NO_DOTMATCH = r'(?:(?!(?:[{sep}]|^)\.).)*?'
# Special right to left matching
_PATH_GSTAR_RTL_MATCH = r'.*?'
# Next char cannot be a dot
_NO_DOT = r'(?![.])'
# Following char from sequence cannot be a separator or a dot
_PATH_NO_SLASH_DOT = r'(?![{sep}.])'
# Following char from sequence cannot be a separator
_PATH_NO_SLASH = r'(?![{sep}])'
# One or more
_ONE_OR_MORE = r'+'
# End of pattern
_EOP = r'$'
_PATH_EOP = r'(?:$|[{sep}])'
# Divider between `globstar`. Can match start or end of pattern
# in addition to slashes.
_GLOBSTAR_DIV = r'(?:^|$|{})+'
# Lookahead to see there is one character.
_NEED_CHAR_PATH = r'(?=[^{sep}])'
_NEED_CHAR = r'(?=.)'
_NEED_SEP = r'(?={})'
# Group that matches one or none
_QMARK_GROUP = r'(?:{})?'
_QMARK_CAPTURE_GROUP = r'((?#)(?:{})?)'
# Group that matches Zero or more
_STAR_GROUP = r'(?:{})*'
_STAR_CAPTURE_GROUP = r'((?#)(?:{})*)'
# Group that matches one or more
_PLUS_GROUP = r'(?:{})+'
_PLUS_CAPTURE_GROUP = r'((?#)(?:{})+)'
# Group that matches exactly one
_GROUP = r'(?:{})'
_CAPTURE_GROUP = r'((?#){})'
# Inverse group that matches none
# This is the start. Since Python can't
# do variable look behinds, we have stuff
# everything at the end that it needs to lookahead
# for. So there is an opening and a closing.
_EXCLA_GROUP = r'(?:(?!(?:{})'
_EXCLA_CAPTURE_GROUP = r'((?#)(?!(?:{})'
# Closing for inverse group
_EXCLA_GROUP_CLOSE = r'){})'
# Restrict root
_NO_ROOT = r'(?!/)'
_NO_WIN_ROOT = r'(?!(?:[\\/]|[a-zA-Z]:))'
# Restrict directories
_NO_NIX_DIR = (
    r'^(?:.*?(?:/\.{1,2}/*|/)|\.{1,2}/*)$',
    rb'^(?:.*?(?:/\.{1,2}/*|/)|\.{1,2}/*)$'
)
_NO_WIN_DIR = (
    r'^(?:.*?(?:[\\/]\.{1,2}[\\/]*|[\\/])|\.{1,2}[\\/]*)$',
    rb'^(?:.*?(?:[\\/]\.{1,2}[\\/]*|[\\/])|\.{1,2}[\\/]*)$'
)


class InvPlaceholder(str):
    """Placeholder for inverse pattern !(...)."""


class PathNameException(Exception):
    """Path name exception."""


class DotException(Exception):
    """Dot exception."""


class PatternLimitException(Exception):
    """Pattern limit exception."""


def escape(pattern, unix=None, pathname=True, raw=False):
    """
    Escape.

    `unix`: use Unix style path logic.
    `pathname`: Use path logic.
    `raw`: Handle raw strings (deprecated)

    """

    if isinstance(pattern, bytes):
        drive_pat = RE_WIN_DRIVE[util.BYTES]
        magic = RE_MAGIC_ESCAPE[util.BYTES]
        drive_magic = RE_WIN_DRIVE_MAGIC[util.BYTES]
        replace = br'\\\1'
        slash = b'\\'
        double_slash = b'\\\\'
        drive = b''
    else:
        drive_pat = RE_WIN_DRIVE[util.UNICODE]
        magic = RE_MAGIC_ESCAPE[util.UNICODE]
        drive_magic = RE_WIN_DRIVE_MAGIC[util.UNICODE]
        replace = r'\\\1'
        slash = '\\'
        double_slash = '\\\\'
        drive = ''

    if not raw:
        pattern = pattern.replace(slash, double_slash)

    # Handle windows drives special.
    # Windows drives are handled special internally.
    # So we shouldn't escape them as we'll just have to
    # detect and undo it later.
    length = 0
    if pathname and ((unix is None and util.platform() == "windows") or unix is False):
        m = drive_pat.match(pattern)
        if m:
            # Replace splitting magic chars
            drive = m.group(0)
            length = len(drive)
            drive = drive_magic.sub(replace, m.group(0))
    pattern = pattern[length:]

    return drive + magic.sub(replace, pattern)


def _get_win_drive(pattern, regex=False, case_sensitive=False):
    """Get Windows drive."""

    drive = None
    slash = False
    end = 0
    root_specified = False
    m = RE_WIN_DRIVE_START.match(pattern)
    if m:
        end = m.end(0)
        if m.group(3) and RE_WIN_DRIVE_LETTER.match(m.group(0)):
            if regex:
                drive = escape_drive(RE_WIN_DRIVE_UNESCAPE.sub(r'\1', m.group(3)), case_sensitive)
            else:
                drive = RE_WIN_DRIVE_UNESCAPE.sub(r'\1', m.group(0))
            slash = bool(m.group(4))
            root_specified = True
        elif m.group(2):
            root_specified = True
            part = [RE_WIN_DRIVE_UNESCAPE.sub(r'\1', m.group(2))]
            is_special = part[-1].lower() in ('.', '?')
            complete = 1
            first = 1
            count = 0
            for count, m in enumerate(RE_WIN_DRIVE_PART.finditer(pattern, m.end(0)), 1):
                end = m.end(0)
                part.append(RE_WIN_DRIVE_UNESCAPE.sub(r'\1', m.group(1)))
                slash = bool(m.group(2))
                if is_special:
                    if count == first and part[-1].lower() == 'unc':
                        complete += 2
                    elif count == first and part[-1].lower() == 'global':
                        first += 1
                        complete += 1
                if count == complete:
                    break
            if count == complete:
                if not regex:
                    drive = '\\\\{}{}'.format('\\'.join(part), '\\' if slash else '')
                else:
                    drive = r'[\\/]{2}' + r'[\\/]'.join([escape_drive(p, case_sensitive) for p in part])
    elif pattern.startswith(('\\\\', '/')):
        root_specified = True

    return root_specified, drive, slash, end


def _get_magic_symbols(ptype, unix, flags):
    """Get magic symbols."""

    if ptype == util.BYTES:
        slash = b'\\'
    else:
        slash = '\\'

    magic = set()
    magic_drive = set() if unix else set(slash)

    magic |= MAGIC_DEF[ptype]
    if flags & BRACE:
        magic |= MAGIC_BRACE[ptype]
        magic_drive |= MAGIC_BRACE[ptype]
    if flags & SPLIT:
        magic |= MAGIC_SPLIT[ptype]
        magic_drive |= MAGIC_SPLIT[ptype]
    if flags & GLOBTILDE:
        magic |= MAGIC_TILDE[ptype]
    if flags & EXTMATCH:
        magic |= MAGIC_EXTMATCH[ptype]
    if flags & NEGATE:
        if flags & MINUSNEGATE:
            magic |= MAGIC_MINUS_NEGATE[ptype]
        else:
            magic |= MAGIC_NEGATE[ptype]

    return magic, magic_drive


def is_magic(pattern, flags=0):
    """Check if pattern is magic."""

    magical = False
    unix = is_unix_style(flags)

    ptype = util.BYTES if isinstance(pattern, bytes) else util.UNICODE
    drive_pat = RE_WIN_DRIVE[ptype]

    magic, magic_drive = _get_magic_symbols(ptype, unix, flags)
    is_path = flags & PATHNAME

    length = 0
    if is_path and ((unix is None and util.platform() == "windows") or unix is False):
        m = drive_pat.match(pattern)
        if m:
            drive = m.group(0)
            length = len(drive)
            for c in magic_drive:
                if c in drive:
                    magical = True
                    break

    if not magical:
        pattern = pattern[length:]
        for c in magic:
            if c in pattern:
                magical = True
                break

    return magical


def is_negative(pattern, flags):
    """Check if negative pattern."""

    if flags & MINUSNEGATE:
        return flags & NEGATE and pattern[0:1] in MINUS_NEGATIVE_SYM
    elif flags & EXTMATCH:
        return flags & NEGATE and pattern[0:1] in NEGATIVE_SYM and pattern[1:2] not in ROUND_BRACKET
    else:
        return flags & NEGATE and pattern[0:1] in NEGATIVE_SYM


def tilde_pos(pattern, flags):
    """Is user folder."""

    pos = -1
    if flags & GLOBTILDE and flags & REALPATH:
        if flags & NEGATE:
            if pattern[0:1] in TILDE_SYM:
                pos = 0
            elif pattern[0:1] in NEGATIVE_SYM and pattern[1:2] in TILDE_SYM:
                pos = 1
        elif pattern[0:1] in TILDE_SYM:
            pos = 0
    return pos


def expand_braces(patterns, flags, limit):
    """Expand braces."""

    if flags & BRACE:
        for p in ([patterns] if isinstance(patterns, (str, bytes)) else patterns):
            try:
                # Turn off limit as we are handling it ourselves.
                yield from bracex.iexpand(p, keep_escapes=True, limit=limit)
            except bracex.ExpansionLimitException:
                raise
            except Exception:  # pragma: no cover
                # We will probably never hit this as `bracex`
                # doesn't throw any specific exceptions and
                # should normally always parse, but just in case.
                yield p
    else:
        for p in ([patterns] if isinstance(patterns, (str, bytes)) else patterns):
            yield p


def expand_tilde(pattern, is_unix, flags):
    """Expand tilde."""

    pos = tilde_pos(pattern, flags)

    if pos > -1:
        string_type = util.BYTES if isinstance(pattern, bytes) else util.UNICODE
        tilde = TILDE_SYM[string_type]
        re_tilde = RE_WIN_TILDE[string_type] if not is_unix else RE_TILDE[string_type]
        m = re_tilde.match(pattern, pos)
        if m:
            expanded = os.path.expanduser(m.group(0))
            if not expanded.startswith(tilde) and os.path.exists(expanded):
                pattern = (pattern[0] if pos else pattern[0:0]) + escape(expanded, is_unix) + pattern[m.end(0):]
    return pattern


def expand(pattern, flags, limit):
    """Expand and normalize."""

    for expanded in expand_braces(pattern, flags, limit):
        for splitted in split(expanded, flags):
            yield expand_tilde(splitted, is_unix_style(flags), flags)


def is_case_sensitive(flags):
    """Is case sensitive."""

    if bool(flags & FORCEWIN):
        case_sensitive = False
    elif bool(flags & FORCEUNIX):
        case_sensitive = True
    else:
        case_sensitive = util.is_case_sensitive()
    return case_sensitive


def get_case(flags):
    """Parse flags for case sensitivity settings."""

    if not bool(flags & CASE_FLAGS):
        case_sensitive = is_case_sensitive(flags)
    elif flags & CASE:
        case_sensitive = True
    else:
        case_sensitive = False
    return case_sensitive


def escape_drive(drive, case):
    """Escape drive."""

    return '(?i:{})'.format(re.escape(drive)) if case else re.escape(drive)


def is_unix_style(flags):
    """Check if we should use Unix style."""

    return (
        (
            (util.platform() != "windows") or
            (not bool(flags & REALPATH) and bool(flags & FORCEUNIX))
        ) and
        not flags & FORCEWIN
    )


def translate(patterns, flags, limit=PATTERN_LIMIT):
    """Translate patterns."""

    positive = []
    negative = []
    if isinstance(patterns, (str, bytes)):
        patterns = [patterns]

    flags = (flags | _TRANSLATE) & FLAG_MASK
    is_unix = is_unix_style(flags)
    seen = set()

    try:
        current_limit = limit
        total = 0
        for pattern in patterns:
            pattern = util.norm_pattern(pattern, not is_unix, flags & RAWCHARS)
            count = 0
            for count, expanded in enumerate(expand(pattern, flags, current_limit), 1):
                total += 1
                if 0 < limit < total:
                    raise PatternLimitException("Pattern limit exceeded the limit of {:d}".format(limit))
                if expanded not in seen:
                    seen.add(expanded)
                    (negative if is_negative(expanded, flags) else positive).append(WcParse(expanded, flags).parse())
            if limit:
                current_limit -= count
                if current_limit < 1:
                    current_limit = 1
    except bracex.ExpansionLimitException:
        raise PatternLimitException("Pattern limit exceeded the limit of {:d}".format(limit))

    if patterns and negative and not positive:
        if flags & NEGATEALL:
            default = b'**' if isinstance(patterns[0], bytes) else '**'
            positive.append(WcParse(default, flags | (GLOBSTAR if flags & PATHNAME else 0)).parse())

    if patterns and flags & NODIR:
        index = util.BYTES if isinstance(patterns[0], bytes) else util.UNICODE
        exclude = _NO_NIX_DIR[index] if is_unix else _NO_WIN_DIR[index]
        negative.append(exclude)

    return positive, negative


def split(pattern, flags):
    """Split patterns."""

    if flags & SPLIT:
        yield from WcSplit(pattern, flags).split()
    else:
        yield pattern


def compile(patterns, flags, limit=PATTERN_LIMIT):  # noqa A001
    """Compile patterns."""

    positive = []
    negative = []
    if isinstance(patterns, (str, bytes)):
        patterns = [patterns]

    is_unix = is_unix_style(flags)
    seen = set()

    try:
        current_limit = limit
        total = 0
        for pattern in patterns:
            pattern = util.norm_pattern(pattern, not is_unix, flags & RAWCHARS)
            count = 0
            for count, expanded in enumerate(expand(pattern, flags, current_limit), 1):
                total += 1
                if 0 < limit < total:
                    raise PatternLimitException("Pattern limit exceeded the limit of {:d}".format(limit))
                if expanded not in seen:
                    seen.add(expanded)
                    (negative if is_negative(expanded, flags) else positive).append(_compile(expanded, flags))
            if limit:
                current_limit -= count
                if current_limit < 1:
                    current_limit = 1
    except bracex.ExpansionLimitException:
        raise PatternLimitException("Pattern limit exceeded the limit of {:d}".format(limit))

    if patterns and negative and not positive:
        if flags & NEGATEALL:
            default = b'**' if isinstance(patterns[0], bytes) else '**'
            positive.append(_compile(default, flags | (GLOBSTAR if flags & PATHNAME else 0)))

    if patterns and flags & NODIR:
        ptype = util.BYTES if isinstance(patterns[0], bytes) else util.UNICODE
        negative.append(RE_NO_DIR[ptype] if is_unix else RE_WIN_NO_DIR[ptype])

    return WcRegexp(tuple(positive), tuple(negative), flags & REALPATH, flags & PATHNAME, flags & FOLLOW)


@functools.lru_cache(maxsize=256, typed=True)
def _compile(pattern, flags):
    """Compile the pattern to regex."""

    return re.compile(WcParse(pattern, flags & FLAG_MASK).parse())


class WcSplit(object):
    """Class that splits patterns on |."""

    def __init__(self, pattern, flags):
        """Initialize."""

        self.pattern = pattern
        self.is_bytes = isinstance(pattern, bytes)
        self.pathname = bool(flags & PATHNAME)
        self.extend = bool(flags & EXTMATCH)
        self.unix = is_unix_style(flags)
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
                try:
                    self._references(i, True)
                except PathNameException:
                    raise StopIteration
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

        pattern = self.pattern.decode('latin-1') if self.is_bytes else self.pattern

        start = -1
        i = util.StringIter(pattern)
        iter(i)
        for c in i:
            if self.extend and c in EXT_TYPES and self.parse_extend(c, i):
                continue

            if c == '|':
                split = i.index - 1
                p = pattern[start + 1:split]
                yield p.encode('latin-1') if self.is_bytes else p
                start = split
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

        if start < len(pattern):
            p = pattern[start + 1:]
            yield p.encode('latin-1') if self.is_bytes else p


class WcParse(object):
    """Parse the wildcard pattern."""

    def __init__(self, pattern, flags=0):
        """Initialize."""

        self.pattern = pattern
        self.no_abs = bool(flags & _NOABSOLUTE)
        self.braces = bool(flags & BRACE)
        self.is_bytes = isinstance(pattern, bytes)
        self.pathname = bool(flags & PATHNAME)
        self.raw_chars = bool(flags & RAWCHARS)
        self.globstar = self.pathname and bool(flags & GLOBSTAR)
        self.realpath = bool(flags & REALPATH) and self.pathname
        self.translate = bool(flags & _TRANSLATE)
        self.negate = bool(flags & NEGATE)
        self.globstar_capture = self.realpath and not self.translate
        self.dot = bool(flags & DOTMATCH)
        self.extend = bool(flags & EXTMATCH)
        self.matchbase = bool(flags & MATCHBASE)
        self.extmatchbase = bool(flags & _EXTMATCHBASE)
        self.rtl = bool(flags & _RTL)
        self.anchor = bool(flags & _ANCHOR)
        self.nodotdir = bool(flags & NODOTDIR)
        self.capture = self.translate
        self.case_sensitive = get_case(flags)
        self.in_list = False
        self.inv_nest = False
        self.flags = flags
        self.inv_ext = 0
        self.unix = is_unix_style(self.flags)
        if not self.unix:
            self.win_drive_detect = self.pathname
            self.char_avoid = (ord('\\'), ord('/'), ord('.'))
            self.bslash_abort = self.pathname
            sep = {"sep": re.escape('\\/')}
        else:
            self.win_drive_detect = False
            self.char_avoid = (ord('/'), ord('.'))
            self.bslash_abort = False
            sep = {"sep": re.escape('/')}
        self.bare_sep = sep['sep']
        self.sep = '[{}]'.format(self.bare_sep)
        self.path_eop = _PATH_EOP.format(**sep)
        self.no_dir = _NO_DIR.format(**sep)
        self.seq_path = _PATH_NO_SLASH.format(**sep)
        self.seq_path_dot = _PATH_NO_SLASH_DOT.format(**sep)
        self.path_star = _PATH_STAR.format(**sep)
        self.path_star_dot1 = _PATH_STAR_DOTMATCH.format(**sep)
        self.path_star_dot2 = _PATH_STAR_NO_DOTMATCH.format(**sep)
        self.path_gstar_dot1 = _PATH_GSTAR_DOTMATCH.format(**sep)
        self.path_gstar_dot2 = _PATH_GSTAR_NO_DOTMATCH.format(**sep)
        if self.pathname:
            self.need_char = _NEED_CHAR_PATH.format(**sep)
        else:
            self.need_char = _NEED_CHAR

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

    def _restrict_extended_slash(self):
        """Restrict extended slash."""

        return self.seq_path if self.pathname else ''

    def _restrict_sequence(self):
        """Restrict sequence."""

        if self.pathname:
            value = self.seq_path_dot if self.after_start and not self.dot else self.seq_path
            if self.after_start:
                value = self.no_dir + value
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
            result.append(posix.get_posix_property(m.group(1), self.is_bytes))
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
                try:
                    value = self._references(i, True)
                except DotException:
                    value = re.escape(next(i))
                except PathNameException:
                    raise StopIteration
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
                result = ['[^{}]'.format(ASCII_RANGE if self.is_bytes else UNICODE_RANGE)]
            elif value == '[^]':
                # We specified some range, but hey are all
                # out of reach. Since this is exclusive
                # that means we can match *anything*.
                result = ['[{}]'.format(ASCII_RANGE if self.is_bytes else UNICODE_RANGE)]
            else:
                result = [value]

        if self.pathname or self.after_start:
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
                    value = self.sep + _ONE_OR_MORE
                    self.set_start_dir()
                else:
                    value = self._restrict_extended_slash() + self.sep
            elif not self.unix:
                value = self.sep if not sequence else self.bare_sep
        elif c == '/':
            # \/
            if sequence and self.pathname:
                raise PathNameException
            if self.pathname:
                if not self.in_list:
                    value = self.sep + _ONE_OR_MORE
                    self.set_start_dir()
                else:
                    value = self._restrict_extended_slash() + self.sep
            else:
                value = self.sep if not sequence else self.bare_sep
        elif c == '.':
            # Let dots be handled special
            i.rewind(1)
            raise DotException
        else:
            # \a, \b, \c, etc.
            value = re.escape(c)

        return value

    def _handle_dot(self, i, current):
        """Handle dot."""

        is_current = True
        is_previous = False

        if self.after_start and self.pathname and self.nodotdir:
            try:
                index = i.index
                while True:
                    c = next(i)
                    if c == '.' and is_current:
                        is_previous = True
                        is_current = False
                    elif c == '.' and is_previous:
                        is_previous = False
                        raise StopIteration
                    elif c in ('|', ')') and self.in_list:
                        raise StopIteration
                    elif c == '\\':
                        try:
                            self._references(i, True)
                            # Was not what we expected
                            is_current = False
                            is_previous = False
                            raise StopIteration
                        except DotException:
                            if is_current:
                                is_previous = True
                                is_current = False
                                c = next(i)
                            else:
                                is_previous = False
                                raise StopIteration
                        except PathNameException:
                            raise StopIteration
                    elif c == '/':
                        raise StopIteration
                    else:
                        is_current = False
                        is_previous = False
                        raise StopIteration
            except StopIteration:
                i.rewind(i.index - index)

        if not is_current and not is_previous:
            current.append(r'(?!\.[.]?{})\.'.format(self.path_eop))
        else:
            current.append(re.escape('.'))

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
            if self.globstar_capture:
                globstar = '({})'.format(globstar)
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
                        except DotException:
                            pass
                        except PathNameException:
                            # Looks like escape was a valid slash
                            # Store pattern accordingly
                            value = globstar
                            self.matchbase = False
                        except StopIteration:
                            # Escapes nothing, ignore and assume double star
                            value = globstar
                    elif c == '/':
                        value = globstar
                        self.matchbase = False

                    if value != globstar:
                        i.rewind(i.index - index)
                except StopIteration:
                    # Could not acquire directory slash due to no more characters
                    # Use double star
                    value = globstar

        if self.after_start and value != globstar:
            value = self.need_char + value
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
            sep = _GLOBSTAR_DIV.format(self.sep)
            # Check if the last entry was a `globstar`
            # If so, don't bother adding another.
            if current[-1] != sep:
                if current[-1] == '':
                    # At the beginning of the pattern
                    current[-1] = value
                else:
                    # Replace the last path separator
                    current[-1] = _NEED_SEP.format(self.sep)
                    current.append(value)
                self.consume_path_sep(i)
                current.append(sep)
            self.set_start_dir()
        else:
            current.append(value)

    def clean_up_inverse(self, current, nested=False):
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

        index = len(current) - 1
        while index >= 0:
            if isinstance(current[index], InvPlaceholder):
                content = current[index + 1:]
                if not nested:
                    content.append(_EOP if not self.pathname else self.path_eop)
                current[index] = (
                    (''.join(content).replace('(?#)', '?:') if self.capture else ''.join(content)) +
                    (_EXCLA_GROUP_CLOSE.format(str(current[index])))
                )
            index -= 1
        self.inv_ext = 0

    def parse_extend(self, c, i, current, reset_dot=False):
        """Parse extended pattern lists."""

        # Save state
        temp_dir_start = self.dir_start
        temp_after_start = self.after_start
        temp_in_list = self.in_list
        temp_inv_ext = self.inv_ext
        temp_inv_nest = self.inv_nest
        self.in_list = True
        self.inv_nest = c == '!'

        if reset_dot:
            self.match_dot_dir = False

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
                elif c == '.':
                    self._handle_dot(i, extended)
                    if self.after_start:
                        self.match_dot_dir = self.dot and not self.nodotdir
                        self.reset_dir_track()
                elif c == '?':
                    extended.append(self._restrict_sequence() + _QMARK)
                elif c == '/':
                    if self.pathname:
                        extended.append(self._restrict_extended_slash())
                    extended.append(self.sep)
                elif c == "|":
                    self.clean_up_inverse(extended, temp_inv_nest and self.inv_nest)
                    extended.append(c)
                    if temp_after_start:
                        self.set_start_dir()
                elif c == '\\':
                    try:
                        extended.append(self._references(i))
                    except DotException:
                        continue
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

            if list_type == '?':
                current.append((_QMARK_CAPTURE_GROUP if self.capture else _QMARK_GROUP).format(''.join(extended)))
            elif list_type == '*':
                current.append((_STAR_CAPTURE_GROUP if self.capture else _STAR_GROUP).format(''.join(extended)))
            elif list_type == '+':
                current.append((_PLUS_CAPTURE_GROUP if self.capture else _PLUS_GROUP).format(''.join(extended)))
            elif list_type == '@':
                current.append((_CAPTURE_GROUP if self.capture else _GROUP).format(''.join(extended)))
            elif list_type == '!':
                self.inv_ext += 1
                # If pattern is at the end, anchor the match to the end.
                current.append((_EXCLA_CAPTURE_GROUP if self.capture else _EXCLA_GROUP).format(''.join(extended)))
                if self.pathname:
                    if not temp_after_start or self.match_dot_dir:
                        star = self.path_star
                    elif temp_after_start and not self.dot:
                        star = self.path_star_dot2
                    else:
                        star = self.path_star_dot1
                else:
                    if not temp_after_start or self.dot:
                        star = _STAR
                    else:
                        star = _NO_DOT + _STAR

                if temp_after_start:
                    star = self.need_char + star
                # Place holder for closing, but store the proper star
                # so we know which one to use
                current.append(InvPlaceholder(star))

            if temp_in_list:
                self.clean_up_inverse(current, temp_inv_nest and self.inv_nest)

        except StopIteration:
            success = False
            self.inv_ext = temp_inv_ext
            i.rewind(i.index - index)

        # Either restore if extend parsing failed, or reset if it worked
        if not temp_in_list:
            self.in_list = False
        if not temp_inv_nest:
            self.inv_nest = False

        if success:
            self.reset_dir_track()
        else:
            self.dir_start = temp_dir_start
            self.after_start = temp_after_start

        return success

    def consume_path_sep(self, i):
        """Consume any consecutive path separators as they count as one."""

        try:
            if self.bslash_abort:
                count = -1
                c = '\\'
                while c in ('\\', '/'):
                    if c != '/' or count % 2:
                        count += 1
                    else:
                        count += 2
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
        root_specified = False
        if self.win_drive_detect:
            root_specified, drive, slash, end = _get_win_drive(pattern, True, self.case_sensitive)
            if drive is not None:
                current.append(drive)
                if slash:
                    current.append(self.sep + _ONE_OR_MORE)
                i.advance(end)
                self.consume_path_sep(i)
            elif drive is None and root_specified:
                root_specified = True
        elif not self.win_drive_detect and self.pathname and pattern.startswith('/'):
            root_specified = True

        if self.no_abs and root_specified:
            raise ValueError('The pattern must be a relative path pattern')

        if root_specified:
            self.matchbase = False
            self.extmatchbase = False
            self.rtl = False

        if not root_specified and self.realpath:
            current.append(_NO_WIN_ROOT if self.win_drive_detect else _NO_ROOT)
            current.append('')

        for c in i:

            index = i.index
            if self.extend and c in EXT_TYPES and self.parse_extend(c, i, current, True):
                # Nothing to do
                pass
            elif c == '.':
                self._handle_dot(i, current)
            elif c == '*':
                self._handle_star(i, current)
            elif c == '?':
                current.append(self._restrict_sequence() + _QMARK)
            elif c == '/':
                if self.pathname:
                    self.set_start_dir()
                    self.clean_up_inverse(current)
                    current.append(self.sep + _ONE_OR_MORE)
                    self.consume_path_sep(i)
                    self.matchbase = False
                else:
                    current.append(self.sep)
            elif c == '\\':
                index = i.index
                try:
                    value = self._references(i)
                    if self.dir_start:
                        self.clean_up_inverse(current)
                        self.consume_path_sep(i)
                        self.matchbase = False
                    current.append(value)
                except DotException:
                    continue
                except StopIteration:
                    # Escapes nothing, ignore
                    i.rewind(i.index - index)
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

        self.clean_up_inverse(current)

        if self.pathname:
            current.append(_PATH_TRAIL.format(self.sep))

    def parse(self):
        """Parse pattern list."""

        result = ['']
        prepend = ['']
        self.negative = False

        p = self.pattern

        if is_negative(p, self.flags):
            self.negative = True
            p = p[1:]

        p = p.decode('latin-1') if self.is_bytes else p

        if self.negative:
            # TODO: Do we prevent `NODOTDIR` for negative patterns?
            self.globstar_capture = False
            self.dot = True

        if self.anchor:
            p, number = (RE_ANCHOR if not self.win_drive_detect else RE_WIN_ANCHOR).subn('', p)
            if number:
                self.matchbase = False
                self.extmatchbase = False
                self.rtl = False

        if self.matchbase or self.extmatchbase:
            globstar = self.globstar
            self.globstar = True
            self.root('**', prepend)
            self.globstar = globstar

        elif self.rtl:
            # Add a `**` that can capture anything: dots, special directories, symlinks, etc.
            # We are simulating right to left, so everything on the left should be accepted without
            # question.
            globstar = self.globstar
            dot = self.dot
            gstar = self.path_gstar_dot1
            globstar_capture = self.globstar_capture
            self.path_gstar_dot1 = _PATH_GSTAR_RTL_MATCH
            self.dot = True
            self.globstar = True
            self.globstar_capture = False
            self.root('**', prepend)
            self.globstar = globstar
            self.dot = dot
            self.path_gstar_dot1 = gstar
            self.globstar_capture = globstar_capture

        # We have an escape, but it escapes nothing
        if p == '\\':
            p = ''

        if p:
            self.root(p, result)

        if p and (self.matchbase or self.extmatchbase or self.rtl):
            result = prepend + result

        case_flag = 'i' if not self.case_sensitive else ''
        pattern = r'^(?s{}:{})$'.format(case_flag, ''.join(result))

        if self.capture:
            # Strip out unnecessary regex comments
            pattern = pattern.replace('(?#)', '')

        if self.is_bytes:
            pattern = pattern.encode('latin-1')

        return pattern
