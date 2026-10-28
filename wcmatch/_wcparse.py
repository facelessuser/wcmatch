"""Wildcard parsing."""
from __future__ import annotations
import re
import functools
import bracex
import os
from . import util
from . import posix
from . _wcmatch import WcRegexp
from typing import AnyStr, Iterable, Pattern, Generic, Sequence, Iterator

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
    {"*", "?", "[", "]", "\\"},
    {b"*", b"?", b"[", b"]", b"\\"}
)
MAGIC_SPLIT = (
    {"|"},
    {b"|"}
)
MAGIC_NEGATE = (
    {'!'},
    {b'!'}
)
MAGIC_MINUS_NEGATE = (
    {'-'},
    {b'-'}
)
MAGIC_TILDE = (
    {'~'},
    {b'~'}
)
MAGIC_EXTMATCH = (
    {'(', ')'},
    {b'(', b')'}
)
MAGIC_NUMRANGE = (
    {'<', '>'},
    {b'<', b'>'}
)
MAGIC_BRACE = (
    {"{", "}"},
    {b"{", b"}"}
)
MAGIC_WIN_DRIVE = (
    {"\\"},
    {b"\\"}
)
MAGIC_UNIX_DRIVE = (
    set(),
    set()
)  # type: tuple[set[str], set[bytes]]

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
RE_POSIX = re.compile(r'\[:(alnum|alpha|ascii|blank|cntrl|digit|graph|lower|print|punct|space|upper|word|xdigit):\]')
RE_NUM_RANGE = re.compile(r'([0-9]*-[0-9]*)>')
RE_EMPTY_EXT_SLOTS = re.compile(r'[|]+')
# Stars that are only followed by the end of an extended group's pattern, or by groups that can match nothing
RE_ALT_END = re.compile(r'\**(?:[?*]\([^()]*\))*[|)]')
RE_EXT_GROUP = re.compile(r'[@*+?!]\(')
# Marks the spot in an inverse group's lookahead where the text following its enclosing group goes. It is a regular
# expression comment, and `re.escape()` always escapes `(`, `?`, and `#`, so it can never be confused with pattern
# content. Should one ever be left behind, it does nothing.
RE_TAIL = re.compile(r'\(\?#tail[0-9]+\)')

# The most regular expression a table of lengths may hold, past this we stop tracking the lengths of a group
MAX_LENGTH_TABLE = 4000

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
GLOBSTARLONG = 0x200000
NUMRANGE = 0x400000
CAPTURE = 0x800000

# Internal flag
_TRANSLATE = 0x100000000  # Lets us know we are performing a translation, and we just want the regex.
_ANCHOR = 0x200000000  # The pattern, if it starts with a slash, is anchored to the working directory; strip the slash.
_EXTMATCHBASE = 0x400000000  # Like `MATCHBASE`, but works for multiple directory levels.
_NOABSOLUTE = 0x800000000  # Do not allow absolute patterns
_NO_GLOBSTAR_CAPTURE = 0x1000000000  # Disallow `GLOBSTAR` capturing groups.

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
    GLOBSTARLONG |
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
    NUMRANGE |
    CAPTURE |
    _TRANSLATE |
    _ANCHOR |
    _EXTMATCHBASE |
    _NOABSOLUTE |
    _NO_GLOBSTAR_CAPTURE
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
_NO_DIR = r'(?!(?:(?<=[{sep}])|(?<=^))(?:\.{{1,2}})(?:$|[{sep}]))'
# Star for `PATHNAME`
_PATH_STAR = r'[^{sep}]*?'
# Extended pattern start that will not capture dots or path separators.
_EXT_PATH_NO_DOT_STAR = r'(?:(?!(?:(?<=[{sep}])|(?<=^))\.)[^{sep}]*?|)'
# Star when at start of filename during `DOTMATCH`
# (allow dot, but don't allow directory match /./ or /../)
_PATH_STAR_DOTMATCH = _NO_DIR + _PATH_STAR
# Star for `PATHNAME` when `DOTMATCH` is disabled and start is at start of file.
# Disallow . and .. and don't allow match to start with a dot.
_PATH_STAR_NO_DOTMATCH = _NO_DIR + fr'(?!\.){_PATH_STAR}'
# `GLOBSTAR` during `DOTMATCH`. Avoid directory match /./ or /../
_PATH_GSTAR_DOTMATCH = r'(?:(?!(?:[{sep}]|^)(?:\.{{1,2}})($|[{sep}])).)*?'
# `GLOBSTAR` with `DOTMATCH` disabled. Don't allow a dot to follow /
_PATH_GSTAR_NO_DOTMATCH = r'(?:(?!(?:[{sep}]|^)\.).)*?'
# Next char cannot be a dot
_NO_DOT = r'(?![.])'
# Extended pattern start that will not capture dots.
_EXT_NO_DOT_STAR = r'(?:(?!(?<=^)\.).*?|)'
# Restrict dot in an extended group
_GROUP_NO_DOT = r'(?!(?<=^)\.)'
# Restrict dot in an extended path group
_PATH_GROUP_NO_DOT = r'(?!(?:(?<=[{sep}])|(?<=^))\.)'
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
_QMARK_GUARD_GROUP = r'(?:{}(?:{}))?'
_QMARK_CAPTURE_GROUP = r'((?#)(?:{})?)'
_QMARK_GUARD_CAPTURE_GROUP = r'((?#)(?:{}(?:{}))?)'
# Group that matches Zero or more
_STAR_GROUP = r'(?:{})*'
_STAR_GUARD_GROUP = r'(?:{}(?:{}))*'
_STAR_CAPTURE_GROUP = r'((?#)(?:{})*)'
_STAR_GUARD_CAPTURE_GROUP = r'((?#)(?:{}(?:{}))*)'
# Group that matches one or more
_PLUS_GROUP = r'{}(?:{})+'
_PLUS_CAPTURE_GROUP = r'((?#){}(?:{})+)'
# Group that matches exactly one
_GROUP = r'{}(?:{})'
_CAPTURE_GROUP = r'{}((?#){})'
# Inverse group that matches none
# This is the start. Since Python can't
# do variable look behinds, we have stuff
# everything at the end that it needs to lookahead
# for. So there is an opening and a closing.
_EXCLA_GROUP = r'(?:(?!(?:{})'
_EXCLA_CAPTURE_GROUP = r'((?#)(?!(?:{})'
# Closing for inverse group
_EXCLA_GROUP_CLOSE = '){})'
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

# Mapping describing if an extended group can be appended to the parent group,
# e.g. `@(a|@(b|c))` -> `@(a|b|c)`.
# Some groups cannot be appended to the parent without an empty group.
# e.g. `+(a|*(b|c))` -> `+(a|b|c|)`.
# `{child: **}`
EXT_REDUCE = {
    '@': {'parent': {'@', '?', '*', '+', '!'}, 'empty': set()},
    '?': {'parent': {'@', '?', '*', '+', '!'}, 'empty': {'@', '+', '!'}},
    '*': {'parent': {'*', '+'}, 'empty': {'+',}},
    '+': {'parent': {'*', '+'}, 'empty': set()},
    '!': {'parent': set(), 'empty': set()}
}  # type: dict[str, dict[str, set[str]]]

# Mapping describing group promotion.
# If the only child of a group is another group, it is possible that the
# parent can take on the identity of the child group.
# e.g. `!(!(a|b))` -> `@(a|b)`.
# `{parent: {child: new_parent}}`
EXT_PROMOTE = {
    '@': {'?': '?', '*': '*', '+': '+', '!': '!'},
    '?': {'@': '?', '*': '*', '+': '*'},
    '*': {'@': '*'},
    '+': {'@': '+', '?': '*', '*': '*'},
    '!': {'@': '!', '!': '@'}
}


class PathNameException(Exception):
    """Path name exception."""


class DotException(Exception):
    """Dot exception."""


class PatternLimitException(Exception):
    """Pattern limit exception."""


class ExtPromote(str):
    """Promote extended group object."""


class InvPlaceholder(str):
    """Placeholder for inverse pattern `!(...)`, and the tail token of the group its contents are in."""

    token: str
    shortcut: bool

    def __new__(cls, value: str, token: str = '', shortcut: bool = False) -> InvPlaceholder:
        """Create the placeholder."""

        placeholder = super().__new__(cls, value)
        placeholder.token = token
        placeholder.shortcut = shortcut
        return placeholder


class AtomicStar(str):
    """Track `*` as needing to be an atomic `*`."""


class Lengths(dict[int, str]):
    """
    The lengths of text that a piece can match, with a regular expression for text of each length.

    Most pieces have a longest text they can match, and `open_from` is `None`. An inverse group does not: it matches
    any text past the longest text its own patterns match. Then `open_from` is the length from which it matches any
    text, only the lengths below it are listed, and a length below it that is not listed matches nothing.
    """

    open_from: int | None = None

    @property
    def empty_only(self) -> bool:
        """Check if the lengths are just the empty string."""

        return self.open_from is None and self == {0: ''}


class ExtGroup(str):
    """Track a top level extended glob group, and the lengths of text it can match when they are known."""

    lens: Lengths | None = None
    # The group always matches at least a character, as far as we can tell. This is only set for `+` and `@` groups.
    non_empty = False
    # The group can match nothing, such as `?(...)` and `*(...)`
    optional = False


class Sized(str):
    """A piece of pattern that matches exactly one character."""

    lens: Lengths

    def __new__(cls, value: str) -> Sized:
        """Create the piece, its lengths are a single length of one that maps to itself."""

        sized = super().__new__(cls, value)
        sized.lens = Lengths({1: str(value)})
        return sized


def join_lengths(table: dict[int, list[str]], open_from: int | None = None) -> Lengths | None:
    """Turn the ways of matching each length into one regular expression, or give up if there are too many."""

    result = Lengths()
    result.open_from = open_from
    size = 0
    for length, ways in table.items():
        unique = list(dict.fromkeys(ways))
        result[length] = unique[0] if len(unique) == 1 else f'(?:{"|".join(unique)})'
        size += len(result[length])
    return result if size <= MAX_LENGTH_TABLE else None


def concat_lengths(first: Lengths, second: Lengths) -> Lengths | None:
    """
    Get the lengths that can be matched by `first` followed by `second`.

    If either side matches any text from some length on, the other side must only match empty text, as we cannot track
    any other result.
    """

    if first.open_from is not None or second.open_from is not None:
        if first.empty_only:
            return second
        if second.empty_only:
            return first
        return None

    table = {}  # type: dict[int, list[str]]
    for length1, regex1 in first.items():
        for length2, regex2 in second.items():
            table.setdefault(length1 + length2, []).append(regex1 + regex2)
    return join_lengths(table)


def union_lengths(first: Lengths, second: Lengths) -> Lengths | None:
    """Get the lengths that can be matched by `first` or `second`."""

    starts = [lens.open_from for lens in (first, second) if lens.open_from is not None]
    open_from = min(starts) if starts else None
    table = {}  # type: dict[int, list[str]]
    for lengths in (first, second):
        for length, regex in lengths.items():
            if open_from is None or length < open_from:
                table.setdefault(length, []).append(regex)
    return join_lengths(table, open_from)


def iter_patterns(patterns: AnyStr | Sequence[AnyStr]) -> Iterable[AnyStr]:
    """Return a simple string sequence."""

    if isinstance(patterns, (str, bytes)):
        yield patterns
    else:
        yield from patterns


def escape(pattern: AnyStr, unix: bool | None = None, pathname: bool = True) -> AnyStr:
    """
    Escape.

    `unix`: use Unix style path logic.
    `pathname`: Use path logic.
    """

    if isinstance(pattern, bytes):
        drive_pat = RE_WIN_DRIVE[util.BYTES]  # type: Pattern[AnyStr]
        magic = RE_MAGIC_ESCAPE[util.BYTES]  # type: Pattern[AnyStr]
        drive_magic = RE_WIN_DRIVE_MAGIC[util.BYTES]  # type: Pattern[AnyStr]
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


def _get_win_drive(
    pattern: str,
    regex: bool = False,
    case_sensitive: bool = False
) -> tuple[bool, str | None, bool, int]:
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
                drive = escape_drive(RE_WIN_DRIVE_UNESCAPE.sub(r'\1', m.group(3)).replace('/', '\\'), case_sensitive)
            else:
                drive = RE_WIN_DRIVE_UNESCAPE.sub(r'\1', m.group(0)).replace('/', '\\')
            slash = bool(m.group(4))
            root_specified = True
        elif m.group(2):
            root_specified = True
            part = [RE_WIN_DRIVE_UNESCAPE.sub(r'\1', m.group(2))]
            is_special = part[-1].lower() in ('.', '?')
            complete = 1
            first = 1
            count = 0
            for count, m2 in enumerate(RE_WIN_DRIVE_PART.finditer(pattern, m.end(0)), 1):
                end = m2.end(0)
                part.append(RE_WIN_DRIVE_UNESCAPE.sub(r'\1', m2.group(1)))
                slash = bool(m2.group(2))
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
                    bslash = "\\"
                    drive = f'\\\\{bslash.join(part)}{bslash if slash else ""}'
                else:
                    drive = r'[\\/]{2}' + r'[\\/]'.join([escape_drive(p, case_sensitive) for p in part])
    elif pattern.startswith(('\\\\', '/')):
        root_specified = True

    return root_specified, drive, slash, end


def _get_magic_symbols(
    pattern: AnyStr,
    unix: bool,
    flags: int
) -> tuple[set[AnyStr], set[AnyStr]]:
    """Get magic symbols."""

    ptype = util.BYTES if isinstance(pattern, bytes) else util.UNICODE
    magic_drive = set(MAGIC_UNIX_DRIVE[ptype] if unix else MAGIC_WIN_DRIVE[ptype])
    magic = set(MAGIC_DEF[ptype])
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
    if flags & NUMRANGE:
        magic |= MAGIC_NUMRANGE[ptype]
    if flags & NEGATE:
        if flags & MINUSNEGATE:
            magic |= MAGIC_MINUS_NEGATE[ptype]
        else:
            magic |= MAGIC_NEGATE[ptype]

    return magic, magic_drive


def is_magic(pattern: AnyStr, flags: int = 0) -> bool:
    """Check if pattern is magic."""

    magical = False
    unix = is_unix_style(flags)

    if isinstance(pattern, bytes):
        ptype = util.BYTES
    else:
        ptype = util.UNICODE

    drive_pat = RE_WIN_DRIVE[ptype]  # type: Pattern[AnyStr]

    magic, magic_drive = _get_magic_symbols(pattern, unix, flags)
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


def is_negative(pattern: AnyStr, flags: int) -> bool:
    """Check if negative pattern."""

    if flags & MINUSNEGATE:
        return bool(flags & NEGATE and pattern[0:1] in MINUS_NEGATIVE_SYM)
    elif flags & EXTMATCH:
        return bool(flags & NEGATE and pattern[0:1] in NEGATIVE_SYM and pattern[1:2] not in ROUND_BRACKET)
    else:
        return bool(flags & NEGATE and pattern[0:1] in NEGATIVE_SYM)


def tilde_pos(pattern: AnyStr, flags: int) -> int:
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


def expand_braces(patterns: AnyStr, flags: int, limit: int) -> Iterable[AnyStr]:
    """Expand braces."""

    if flags & BRACE:
        for p in ([patterns] if isinstance(patterns, (str, bytes)) else patterns):
            try:
                # Turn off limit as we are handling it ourselves.
                yield from bracex.iexpand(p, keep_escapes=True, limit=limit, return_empty=True)
            except bracex.ExpansionLimitException:  # noqa: PERF203
                raise
            except Exception:  # pragma: no cover
                # We will probably never hit this as `bracex`
                # doesn't throw any specific exceptions and
                # should normally always parse, but just in case.
                yield p
    else:
        for p in ([patterns] if isinstance(patterns, (str, bytes)) else patterns):
            yield p


def expand_tilde(pattern: AnyStr, is_unix: bool, flags: int) -> AnyStr:
    """Expand tilde."""

    pos = tilde_pos(pattern, flags)

    if pos > -1:
        string_type = util.BYTES if isinstance(pattern, bytes) else util.UNICODE
        tilde = TILDE_SYM[string_type]  # type: AnyStr
        re_tilde = RE_WIN_TILDE[string_type] if not is_unix else RE_TILDE[string_type]  # type: Pattern[AnyStr]
        m = re_tilde.match(pattern, pos)
        if m:
            expanded = os.path.expanduser(m.group(0))
            if not expanded.startswith(tilde) and os.path.exists(expanded):
                pattern = (pattern[0:1] if pos else pattern[0:0]) + escape(expanded, is_unix) + pattern[m.end(0):]
    return pattern


def expand(pattern: AnyStr, flags: int, limit: int) -> Iterable[AnyStr]:
    """Expand and normalize."""

    for expanded in expand_braces(pattern, flags, limit):
        for splitted in split(expanded, flags):
            yield expand_tilde(splitted, is_unix_style(flags), flags)


def is_case_sensitive(flags: int) -> bool:
    """Is case sensitive."""

    if bool(flags & FORCEWIN):
        case_sensitive = False
    elif bool(flags & FORCEUNIX):
        case_sensitive = True
    else:
        case_sensitive = util.is_case_sensitive()
    return case_sensitive


def get_case(flags: int) -> bool:
    """Parse flags for case sensitivity settings."""

    if not bool(flags & CASE_FLAGS):
        case_sensitive = is_case_sensitive(flags)
    elif flags & CASE:
        case_sensitive = True
    else:
        case_sensitive = False
    return case_sensitive


def escape_drive(drive: str, case: bool) -> str:
    """Escape drive."""

    return f'(?i:{re.escape(drive)})' if case else re.escape(drive)


def is_unix_style(flags: int) -> bool:
    """Check if we should use Unix style."""

    return (
        (
            (util.platform() != "windows") or
            (not bool(flags & REALPATH) and bool(flags & FORCEUNIX))
        ) and
        not flags & FORCEWIN
    )


def no_negate_flags(flags: int) -> int:
    """No negation."""

    if flags & NEGATE:
        flags ^= NEGATE
    if flags & NEGATEALL:
        flags ^= NEGATEALL
    return flags


def translate(
    patterns: AnyStr | Sequence[AnyStr],
    flags: int,
    limit: int = PATTERN_LIMIT,
    exclude: AnyStr | Sequence[AnyStr] | None = None
) -> tuple[list[AnyStr], list[AnyStr]]:
    """Translate patterns."""

    positive = []  # type: list[AnyStr]
    negative = []  # type: list[AnyStr]

    if exclude is not None:
        flags = no_negate_flags(flags)
        negative = translate(
            exclude,
            flags=flags | DOTMATCH | _NO_GLOBSTAR_CAPTURE,
            limit=limit
        )[0]

    flags = (flags | _TRANSLATE) & FLAG_MASK
    is_unix = is_unix_style(flags)
    seen = set()

    try:
        total = len(negative)
        current_limit = max(1, limit - total) if limit > 0 else limit
        for pattern in iter_patterns(patterns):
            pattern = util.norm_pattern(pattern, not is_unix, bool(flags & RAWCHARS))
            count = 0
            for expanded in expand(pattern, flags, current_limit):
                count += 1
                total += 1
                if 0 < limit < total:
                    raise PatternLimitException(f"Pattern limit exceeded the limit of {limit:d}")
                if expanded not in seen:
                    seen.add(expanded)
                    if is_negative(expanded, flags):
                        negative.append(WcParse(expanded[1:], flags | _NO_GLOBSTAR_CAPTURE | DOTMATCH).parse())
                    else:
                        positive.append(WcParse(expanded, flags).parse())
            if limit > 0:
                current_limit -= count
                if current_limit < 1:
                    current_limit = 1
    except bracex.ExpansionLimitException as e:
        raise PatternLimitException(f"Pattern limit exceeded the limit of {limit:d}") from e

    if negative and not positive:
        if flags & NEGATEALL:
            default = b'**' if isinstance(negative[0], bytes) else '**'
            positive.append(WcParse(default, flags | (GLOBSTAR if flags & PATHNAME else 0)).parse())

    if positive and flags & NODIR:
        index = util.BYTES if isinstance(positive[0], bytes) else util.UNICODE
        negative.append(_NO_NIX_DIR[index] if is_unix else _NO_WIN_DIR[index])

    return positive, negative


def split(pattern: AnyStr, flags: int) -> Iterable[AnyStr]:
    """Split patterns."""

    if flags & SPLIT:
        yield from WcSplit(pattern, flags).split()
    else:
        yield pattern


def compile_pattern(
    patterns: AnyStr | Sequence[AnyStr],
    flags: int,
    limit: int = PATTERN_LIMIT,
    exclude: AnyStr | Sequence[AnyStr] | None = None
) -> tuple[list[Pattern[AnyStr]], list[Pattern[AnyStr]]]:
    """Compile the patterns."""

    positive = []  # type: list[Pattern[AnyStr]]
    negative = []  # type: list[Pattern[AnyStr]]

    if exclude is not None:
        flags = no_negate_flags(flags)
        negative = compile_pattern(exclude, flags=flags | DOTMATCH | _NO_GLOBSTAR_CAPTURE, limit=limit)[0]

    is_unix = is_unix_style(flags)
    seen = set()

    try:
        total = len(negative)
        current_limit = max(1, limit - total) if limit > 0 else limit
        for pattern in iter_patterns(patterns):
            pattern = util.norm_pattern(pattern, not is_unix, bool(flags & RAWCHARS))
            count = 0
            for expanded in expand(pattern, flags, current_limit):
                count += 1
                total += 1
                if 0 < limit < total:
                    raise PatternLimitException(f"Pattern limit exceeded the limit of {limit:d}")
                if expanded not in seen:
                    seen.add(expanded)
                    if is_negative(expanded, flags):
                        negative.append(_compile(expanded[1:], flags | _NO_GLOBSTAR_CAPTURE | DOTMATCH))
                    else:
                        positive.append(_compile(expanded, flags))
            if limit > 0:
                current_limit -= count
                if current_limit < 1:
                    current_limit = 1
    except bracex.ExpansionLimitException as e:
        raise PatternLimitException(f"Pattern limit exceeded the limit of {limit:d}") from e

    if negative and not positive:
        if flags & NEGATEALL:
            default = b'**' if isinstance(negative[0].pattern, bytes) else '**'
            positive.append(_compile(default, flags | (GLOBSTAR if flags & PATHNAME else 0)))

    if positive and flags & NODIR:
        ptype = util.BYTES if isinstance(positive[0].pattern, bytes) else util.UNICODE
        negative.append(RE_NO_DIR[ptype] if is_unix else RE_WIN_NO_DIR[ptype])

    return positive, negative


def compile(  # noqa: A001
    patterns: AnyStr | Sequence[AnyStr],
    flags: int,
    limit: int = PATTERN_LIMIT,
    exclude: AnyStr | Sequence[AnyStr] | None = None
) -> WcRegexp[AnyStr]:
    """Compile patterns."""

    positive, negative = compile_pattern(patterns, flags, limit, exclude)
    return WcRegexp(
        tuple(positive), tuple(negative),
        bool(flags & REALPATH), bool(flags & PATHNAME), bool(flags & FOLLOW) and not bool(flags & GLOBSTARLONG)
    )


@functools.lru_cache(maxsize=256, typed=True)
def _compile(pattern: AnyStr, flags: int) -> Pattern[AnyStr]:
    """Compile the pattern to regex."""

    return re.compile(WcParse(pattern, flags & FLAG_MASK).parse())


class WcSplit(Generic[AnyStr]):
    """Class that splits patterns on |."""

    def __init__(self, pattern: AnyStr, flags: int) -> None:
        """Initialize."""

        self.pattern = pattern  # type: AnyStr
        self.pathname = bool(flags & PATHNAME)
        self.extend = bool(flags & EXTMATCH)
        self.unix = is_unix_style(flags)
        self.bslash_abort = not self.unix
        self.bad_sequence = -1

    def _sequence(self, i: util.StringIter) -> None:
        """Handle character group."""

        c = next(i)
        if c in ('!', '^'):
            c = next(i)
        if c in ('-', ']'):
            c = next(i)

        try:
            while c != ']':
                if c == '\\':
                    # Handle escapes
                    self._references(i, True)
                elif c == '/':
                    if self.pathname:
                        raise StopIteration
                elif c == '[':
                    m = i.match(RE_POSIX)
                    if m:
                        i.advance(m.end(0) - i.index)
                c = next(i)
        except PathNameException as e:
            raise StopIteration from e

    def _references(self, i: util.StringIter, sequence: bool = False) -> None:
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

    def parse_extend(self, c: str, i: util.StringIter) -> bool:
        """Parse extended pattern lists."""

        index = i.index

        if not i.match(RE_EXT_GROUP):
            i.rewind(i.index - index)
            return False

        success = True
        bad_sequence = self.bad_sequence

        # Start list parsing
        try:
            while c != ')':
                c = next(i)

                if not self.extend:
                    raise StopIteration

                #See if we should parse a nested extended pattern.
                if c in EXT_TYPES:
                    if self.parse_extend(c, i):
                        continue

                if c == '\\':
                    try:
                        self._references(i)
                    except StopIteration:
                        pass
                elif c == '[' and (self.bad_sequence == -1 or i.index > self.bad_sequence):
                    index2 = i.index
                    try:
                        self._sequence(i)
                    except StopIteration:
                        self.bad_sequence = i.index
                        i.rewind(i.index - index2)

        except StopIteration:
            success = False
            i.rewind(i.index - index)
            self.bad_sequence = bad_sequence
            self.extend = False

        return success

    def _split(self, pattern: str) -> Iterable[str]:
        """Split the pattern."""

        start = -1
        i = util.StringIter(pattern)

        for c in i:
            if self.extend and c in EXT_TYPES and self.parse_extend(c, i):
                continue

            if c == '|':
                split = i.index - 1
                p = pattern[start + 1:split]
                yield p
                start = split
            elif c == '\\':
                index = i.index
                try:
                    self._references(i)
                except StopIteration:
                    i.rewind(i.index - index)
            elif c == '[' and (self.bad_sequence == -1 or i.index > self.bad_sequence):
                index = i.index
                try:
                    self._sequence(i)
                except StopIteration:
                    self.bad_sequence = i.index
                    i.rewind(i.index - index)

        if start < len(pattern):
            yield pattern[start + 1:]

    def split(self) -> Iterable[AnyStr]:
        """Split the pattern."""

        if isinstance(self.pattern, bytes):
            for p in self._split(self.pattern.decode('latin-1')):
                yield p.encode('latin-1')
        else:
            yield from self._split(self.pattern)


class WcParse(Generic[AnyStr]):
    """Parse the wildcard pattern."""

    def __init__(self, pattern: AnyStr, flags: int = 0) -> None:
        """Initialize."""

        self.pattern = pattern  # type: AnyStr
        self.no_abs = bool(flags & _NOABSOLUTE)
        self.braces = bool(flags & BRACE)
        self.is_bytes = isinstance(pattern, bytes)
        self.pathname = bool(flags & PATHNAME)
        self.raw_chars = bool(flags & RAWCHARS)
        self.globstarlong = self.pathname and bool(flags & GLOBSTARLONG)
        self.globstar = self.pathname and (self.globstarlong or bool(flags & GLOBSTAR))
        self.follow = bool(flags & FOLLOW)
        self.realpath = bool(flags & REALPATH) and self.pathname
        self.translate = bool(flags & _TRANSLATE)
        self.negate = bool(flags & NEGATE)
        self.globstar_capture = self.realpath and not self.translate and not bool(flags & _NO_GLOBSTAR_CAPTURE)
        self.dot = bool(flags & DOTMATCH)
        self.extend = bool(flags & EXTMATCH)
        self.matchbase = bool(flags & MATCHBASE)
        self.extmatchbase = bool(flags & _EXTMATCHBASE)
        self.anchor = bool(flags & _ANCHOR)
        self.nodotdir = bool(flags & NODOTDIR)
        self.numrange = bool(flags & NUMRANGE)
        self.capture = self.translate and bool(flags & CAPTURE)
        self.case_sensitive = get_case(flags)
        self.in_list = False
        self.emitted_star = -1
        self.flags = flags
        self.inv_ext = 0
        self.tail_id = 0
        self.tails_open = False
        self.in_inv = 0
        self.group_has_dot = False
        self.unix = is_unix_style(self.flags)
        self.bad_sequence = -1
        self.ext_empty = False
        if not self.unix:
            self.win_drive_detect = self.pathname
            self.char_avoid = (ord('\\'), ord('/'), ord('.'))  # type: tuple[int, ...]
            self.bslash_abort = self.pathname
            sep = {"sep": re.escape('\\/')}
        else:
            self.win_drive_detect = False
            self.char_avoid = (ord('/'), ord('.'))
            self.bslash_abort = False
            sep = {"sep": re.escape('/')}
        self.bare_sep = sep['sep']
        self.sep = f'[{self.bare_sep}]'
        self.path_eop = _PATH_EOP.format(**sep)
        self.no_dir = _NO_DIR.format(**sep)
        self.seq_path = _PATH_NO_SLASH.format(**sep)
        self.seq_path_dot = _PATH_NO_SLASH_DOT.format(**sep)
        self.seq_path_group_dot = _PATH_GROUP_NO_DOT.format(**sep)
        self.path_star = _PATH_STAR.format(**sep)
        self.path_ext_star = _EXT_PATH_NO_DOT_STAR.format(**sep)
        self.path_star_dot1 = _PATH_STAR_DOTMATCH.format(**sep)
        self.path_star_dot2 = _PATH_STAR_NO_DOTMATCH.format(**sep)
        self.path_gstar_dot1 = _PATH_GSTAR_DOTMATCH.format(**sep)
        self.path_gstar_dot2 = _PATH_GSTAR_NO_DOTMATCH.format(**sep)
        if self.pathname:
            self.need_char = _NEED_CHAR_PATH.format(**sep)
        else:
            self.need_char = _NEED_CHAR

    def set_after_start(self) -> None:
        """Set tracker for character after the start of a directory."""

        self.after_start = True
        self.dir_start = False

    def set_start_dir(self) -> None:
        """Set directory start."""

        self.dir_start = True
        self.after_start = False

    def reset_dir_track(self) -> None:
        """Reset directory tracker."""

        self.dir_start = False
        self.after_start = False

    def update_dir_state(self) -> None:
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

    def _resolve_tails(self, items: list[str], tail: str, skip: str = '') -> None:
        """
        Fill in the tail of inverse groups that sit inside groups.

        An inverse group inside a group is closed once its slot ends, but the text that follows the enclosing group
        is not known yet, so a tail token was left in its place. For every group in `items` that has such a token,
        the token becomes the rest of the slot after that group followed by `tail`. Tokens that match `skip` belong
        to the group that owns `items` and are resolved by the group's parent.
        """

        if not self.tails_open:
            return

        for k in range(len(items) - 1, -1, -1):
            item = items[k]
            if '(?#tail' not in item:
                continue
            end = k + 1
            while end < len(items) and items[end] != '|':
                end += 1
            rest = ''.join(items[k + 1:end]) + tail
            if self.capture:
                # The tail only goes inside a lookahead, which must not capture
                rest = rest.replace('(?#)', '?:')
            items[k] = type(item)(self._fill_tail(item, rest, skip))

    @staticmethod
    def _fill_tail(item: str, rest: str, skip: str) -> str:
        """Replace every tail token in `item` with `rest`, except for the one that matches `skip`."""

        def replace(m: re.Match[str]) -> str:
            return m.group(0) if m.group(0) == skip else rest

        return RE_TAIL.sub(replace, item)

    @staticmethod
    def _retoken(items: list[str], token: str, new_token: str) -> None:
        """Replace one tail token with another, as the group that owned `token` has been merged into its parent."""

        for k, item in enumerate(items):
            if token in item:
                items[k] = type(item)(item.replace(token, new_token))

    def _finish_group(self, extended: list[str], token: str) -> None:
        """Close the inverse groups that sit directly in the slots of a group that is now complete."""

        self.clean_up_inverse(extended, token)
        self._resolve_tails(extended, token, token)

    def _close_root(self, current: list[str]) -> None:
        """Close the inverse groups at the end of a path segment or pattern."""

        self.clean_up_inverse(current)
        self._resolve_tails(current, _EOP if not self.pathname else self.path_eop)
        self.tails_open = False

    @staticmethod
    def _maybe_empty(extended: list[str]) -> bool:
        """
        Check if the patterns of a group may match nothing.

        A pattern can only be shown to match something if one of its pieces always matches a character.
        """

        non_empty = False
        for item in [*extended, '|']:
            if item == '|':
                if not non_empty:
                    return True
                non_empty = False
                continue
            lens = getattr(item, 'lens', None)
            if getattr(item, 'non_empty', False) or (lens is not None and 0 not in lens):
                non_empty = True
        return False

    @staticmethod
    def _group_lengths(extended: list[str]) -> Lengths | None:
        """
        Get the lengths of text that the patterns of a group can match, with a regular expression for each length.

        The result is `None` if the lengths of any piece in any pattern are not known, or if tracking them would take
        too much space.
        """

        result = None  # type: Lengths | None
        slot = Lengths({0: ''})
        for item in [*extended, '|']:
            if item == '|':
                result = slot if result is None else union_lengths(result, slot)
                if result is None:
                    return None
                slot = Lengths({0: ''})
                continue
            lens = getattr(item, 'lens', None)
            if lens is None:
                return None
            new_slot = concat_lengths(slot, lens)
            if new_slot is None:
                return None
            slot = new_slot
        return result

    def _exact_inverse(
        self,
        lens: Lengths | None,
        star: str,
        extended: list[str]
    ) -> tuple[str, Lengths] | None:
        """
        Build an inverse group that does not depend on what follows it, or return `None` if that is not possible.

        This needs the lengths of text that the group's patterns can match. The patterns either have a longest text
        they can match, or they match any text from some length on, as an inverse group does. The group is decided one
        length at a time, shortest first:

        - If the patterns cannot match text of a length, the group matches any text of that length.
        - If they can, the group matches text of that length only if the patterns' regular expression for that length
          does not match it.
        - For text longer than any length listed, the group matches any text if the patterns have a longest text they
          can match, and no text if they match any text from some length on.

        The lengths that the group itself can match are returned with its regular expression, so an inverse group
        around this one can use them. If the patterns have a longest text they can match, this group matches any text
        from some length on. If they match any text from some length on, this group has a longest text it can match.
        """

        base = self.path_star if self.pathname else _STAR
        if lens is None or not star.endswith(base):
            return None

        char = self.path_star[:-2] if self.pathname else '.'
        # The length from which the patterns match all text, if they do
        all_from = lens.open_from
        limit = max(lens) + 1 if all_from is None else all_from
        pieces = []
        table = {}  # type: dict[int, list[str]]
        run = None  # type: list[int] | None
        for length in range(limit):
            exact = self._length_range(char, length, length)
            if length not in lens:
                # Any text of this length, and adjacent lengths like it can share one piece
                table[length] = [exact]
                if run is None:
                    run = [length, length]
                run[1] = length
                continue
            if run is not None:
                pieces.append(self._length_range(char, run[0], run[1]))
                run = None
            # If the patterns can match nothing, the group cannot, and there is no piece to add for a length of zero
            if length:
                regex = lens[length].replace('(?#)', '?:') if self.capture else lens[length]
                pieces.append(f'(?!(?:{regex})){exact}')
                table[length] = [f'(?!(?:{lens[length]})){exact}']
        if run is not None:
            pieces.append(self._length_range(char, run[0], run[1]))
        if all_from is None:
            pieces.append(f'{char}{{{limit},}}?')
        elif not pieces:
            # The patterns match all text, so the group can match nothing
            pieces.append('(?!)')

        # If the patterns have a longest text they can match, the group matches all text longer than that
        group_lens = join_lengths(table, limit if all_from is None else None)
        if group_lens is None:
            return None

        body = star[:-len(base)] + f'(?:{"|".join(pieces)})'
        if not self.capture:
            return f'(?:{body})', group_lens

        # With `CAPTURE`, every extended group must still be a capturing group, in the order of the pattern. The
        # patterns above were copied as non-capturing groups, so keep the originals in a branch that can never match.
        original = ''.join(extended)
        unused = f'(?:(?!)(?:{original})|)' if '(?#)' in original else ''
        return f'((?#){unused}{body})', group_lens

    @staticmethod
    def _length_range(char: str, low: int, high: int) -> str:
        """Match from `low` to `high` characters."""

        if low == high:
            return '' if not low else char if low == 1 else f'{char}{{{low}}}'
        return f'{char}{{{low},{high}}}?'

    def _restrict_extended_slash(self) -> str:
        """Restrict extended slash."""

        return self.seq_path if self.pathname else ''

    def _restrict_sequence(self, current: list[str]) -> str:
        """Restrict sequence."""

        # An extended group may consume nothing, leaving the wildcard at the start of a name.
        # Group slots do not know what came before the group, so they check the position at match time.
        after_ext = bool(current and isinstance(current[-1], ExtGroup))
        check_start = (after_ext or self.in_list) and not self.dot
        if self.pathname:
            if self.after_start and not self.dot:
                value = self.seq_path_dot if not self.in_list else self.seq_path_group_dot + self.seq_path
            elif check_start:
                value = self.seq_path_group_dot + self.seq_path
            else:
                value = self.seq_path
            if self.after_start and not after_ext:
                value = self.no_dir + value
        else:
            value = (_NO_DOT if not self.in_list else _GROUP_NO_DOT) if self.after_start and not self.dot else ""
            if check_start and not self.after_start:
                value = _GROUP_NO_DOT

        self.reset_dir_track()

        return value

    def _sequence_range_check(self, result: list[str], last: str) -> bool:
        """
        If range is backwards, remove it.

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

    def _handle_posix(self, i: util.StringIter, result: list[str], end_range: int) -> bool:
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

    def _digit_range_parts(self, lo: str, hi: str) -> Iterator[str]:
        """Take two equal-length integer strings, return a list of regex fragments that combine to match the numbers."""

        # Single digit number
        if len(lo) == 1:
            # Range of an exact numb
            if lo == hi:
                yield lo

            # Range of single digit numbers.
            else:
                yield f"[{lo}-{hi}]"

        # Range of an exact number.
        elif lo == hi:
            yield lo

        # Two different, multi-digit numbers.
        else:

            lo_digit, lo_rest = lo[0], lo[1:]
            hi_digit, hi_rest = hi[0], hi[1:]

            # Identical digits
            if lo_digit == hi_digit:
                yield from ((lo_digit + s) for s in self._digit_range_parts(lo_rest, hi_rest))

            # Different digits
            else:
                rest_len = len(lo_rest)
                all_zeros = "0" * rest_len
                all_nines = "9" * rest_len

                # Low piece: `lo_digit` followed by `[lo_rest .. 999...9]`
                # If `lo_digit` already covers the full span for the tail, fold it into middle.
                if lo_rest == all_zeros:
                    low_start = lo_digit
                else:
                    yield from (lo_digit + s for s in self._digit_range_parts(lo_rest, all_nines))
                    low_start = str(int(lo_digit) + 1)

                # High piece: `hi_digit` followed by `[000...0 .. hi_rest]`
                # If `hi_digit` already covers the full span for the tail, fold it into middle.
                if hi_rest == all_nines:
                    high_end = hi_digit
                else:
                    yield from (hi_digit + s for s in self._digit_range_parts(all_zeros, hi_rest))
                    high_end = str(int(hi_digit) - 1)

                # Middle piece: any digit strictly between the adjusted bounds.
                if low_start <= high_end:
                    digit_part = low_start if low_start == high_end else f"[{low_start}-{high_end}]"
                    if rest_len == 1:
                        tail = "[0-9]"
                    else:
                        tail = f"[0-9]{{{rest_len}}}"
                    yield digit_part + tail

    def range_to_regex(
        self,
        mn: int | None = None,
        mx: int | None = None,
        leading_zeros: bool = True,
        limit: int = 19
    ) -> str:
        """
        Convert a non-negative minimum and maximum into a regular expression that matches the range.

        A missing minimum is assumed to be zero and a missing maximum is any number greater than the
        minimum. Leading zeros are automatically gathered as well.

        A minimum that is greater than the maximum will return an impossible match.

        Explicit values with greater than 19 digits will be truncated.
        """

        # If no start, zero is the start
        if mn is None:
            mn = 0

        # Minimum should be less than the maximum, if not, return an impossible match.
        if mx is not None and mn > mx:
            return '(?!)'

        # Minimum range up to an unspecified large number
        if mx is None:
            lo = str(mn)
            lo_len = len(lo)

            # Truncate to 19 digits like ZSH to prevent insanity
            if lo_len > limit:
                lo = lo[:limit]
                lo_len = limit

            parts = [part for part in self._digit_range_parts(lo, "9" * lo_len)]
            parts.append(f"[1-9][0-9]{{{lo_len},}}")

        # Bounded minimum and maximum
        else:
            lo, hi = str(mn), str(mx)
            lo_len, hi_len = len(lo), len(hi)

            # Truncate to 19 digits like ZSH to prevent insanity
            if lo_len > limit:
                lo = lo[:limit]
                lo_len = limit
            if hi_len > limit:
                hi = hi[:limit]
                hi_len = limit

            if lo_len == hi_len:
                ranges = [(lo, hi)]
            else:
                ranges = [(lo, "9" * lo_len)]
                for length in range(lo_len + 1, hi_len):
                    ranges.append(("1" + "0" * (length - 1), "9" * length))
                ranges.append(("1" + "0" * (hi_len - 1), hi))

            parts = []
            for lo, hi in ranges:
                parts.extend([part for part in self._digit_range_parts(lo, hi)])

        # Join the parts together and wrap in a group if needed.
        pattern = "|".join(parts)
        if len(parts) > 1:
            pattern = f"(?:{pattern})"

        # Allow leading zeros.
        if leading_zeros:
            pattern = f"0*?{pattern}"

        return pattern

    def _handle_numrange(self, i: util.StringIter) -> str:
        """Handle ZSH style number range."""

        m = i.match_next(RE_NUM_RANGE)
        if m:
            start, end = [x.strip() for x in m.group(1).split('-')]
            return self.range_to_regex(int(start) if start else None, int(end) if end else None)
        return re.escape('<')

    def _sequence(self, i: util.StringIter, current: list[str]) -> str:
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
                except PathNameException as e:
                    raise StopIteration from e
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
                result = ['(?!)']
            elif value == '[^]':
                # We specified some range, but they are all
                # out of reach. Since this is exclusive
                # that means we can match *anything*.
                result = [r'[\s\S]']
            else:
                result = [value]

        if self.pathname or self.after_start or self.in_list or (current and isinstance(current[-1], ExtGroup)):
            return self._restrict_sequence(current) + ''.join(result)

        return ''.join(result)

    def _references(self, i: util.StringIter, sequence: bool = False) -> str:
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

    def _handle_dot(self, i: util.StringIter, current: list[str]) -> None:
        """Handle dot."""

        is_current = True
        is_previous = False

        if self.after_start and self.pathname and self.nodotdir:
            index = 0
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
                        except DotException as e:
                            if is_current:
                                is_previous = True
                                is_current = False
                                c = next(i)
                            else:
                                is_previous = False
                                raise StopIteration from e
                        except PathNameException as e:
                            raise StopIteration from e
                    elif c == '/':
                        raise StopIteration
                    else:
                        is_current = False
                        is_previous = False
                        raise StopIteration
            except StopIteration:
                i.rewind(i.index - index)

        if not is_current and not is_previous:
            current.append(rf'(?!\.[.]?{self.path_eop})\.')
        else:
            current.append(re.escape('.'))

    def _group_start(self, in_list: bool, has_dot: bool) -> str:
        """
        Get what keeps a group from starting on a leading dot.

        A group that has an alternative that starts with a dot can start on one.
        """

        if in_list or has_dot or self.dot:
            return ''
        return self.seq_path_group_dot if self.pathname else _GROUP_NO_DOT

    @staticmethod
    def _alt_start(extended: list[str]) -> bool:
        """Check if only groups that can match nothing come before this point in the alternative."""

        for item in reversed(extended):
            if item == '|':
                break
            if not (isinstance(item, ExtGroup) and item.optional):
                return False
        return True

    def _handle_star(self, i: util.StringIter, current: list[str]) -> bool:
        """Handle a star and report whether it consumed a directory separator."""

        after_ext = bool(current and isinstance(current[-1], ExtGroup))
        check_start = (after_ext or self.in_list) and not self.dot
        # A star that ends its pattern in an extended group can match nothing at the start of a name
        alt_end = self.in_list and i.match_next(RE_ALT_END, False) is not None
        if self.pathname:
            if self.after_start and not self.dot:
                if self.in_list:
                    star = self.no_dir + (self.path_ext_star if alt_end else self.seq_path_group_dot + self.path_star)
                else:
                    star = self.path_star_dot2
                globstar = self.path_gstar_dot2
            elif self.after_start:
                star = self.path_star_dot1
                globstar = self.path_gstar_dot1
            else:
                star = self.path_star
                if check_start:
                    if alt_end and self.in_list:
                        star = self.path_ext_star
                    else:
                        current.append(self.seq_path_group_dot)
                globstar = self.path_gstar_dot1
            capture = self.globstar_capture
        else:
            if self.after_start and not self.dot:
                star = _NO_DOT + _STAR if not self.in_list else _EXT_NO_DOT_STAR if alt_end else _GROUP_NO_DOT + _STAR
            elif check_start:
                if alt_end and self.in_list:
                    star = _EXT_NO_DOT_STAR
                else:
                    current.append(_GROUP_NO_DOT)
                    star = _STAR
            else:
                star = _STAR
            globstar = ''
        value = star
        directory = False

        if self.after_start and self.globstar and not self.in_list:
            skip = True
            try:
                c = next(i)
                if c != '*' or (self.extend and i.match(RE_EXT_GROUP, False)):
                    i.rewind(1)
                    raise StopIteration
                skip = False

                # Test for triple star. If found, do not make a capturing group.
                # Capturing groups are used to filter out symlinks, but triple stars force symlinks.
                if self.globstarlong:
                    c = next(i)
                    if c != '*' or (self.extend and i.match(RE_EXT_GROUP, False)):
                        i.rewind(1)
                        raise StopIteration
                    capture = False

            except StopIteration:
                # Could not acquire a second star, so assume single star pattern
                pass

            if capture:
                globstar = f'({globstar})'

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
                            directory = True
                            self.matchbase = False
                        except StopIteration:
                            # Escapes nothing, ignore and assume double star
                            value = globstar
                    elif c == '/':
                        value = globstar
                        directory = True
                        self.matchbase = False

                    if value != globstar:
                        i.rewind(i.index - index)
                except StopIteration:
                    # Could not acquire directory slash due to no more characters
                    # Use double star
                    value = globstar

        if value != globstar:
            if self.after_start:
                value = self.need_char + value

            # Consume duplicate starts, but leave a star that opens an extended group
            try:
                c = next(i)
                while c == '*' and not (self.extend and i.match(RE_EXT_GROUP, False)):
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
            if not self.in_list:
                if self.emitted_star == -1:
                    self.emitted_star = len(current)
                value = AtomicStar(value)
            current.append(value)

        return directory

    def clean_up_inverse(self, current: list[str], token: str | None = None) -> None:
        """
        Clean up current.

        Python doesn't have variable lookbehinds, so we have to do negative lookaheads.
        `!(...)`, when converted to regular expression, is atomic, so once it matches, that's it.
        So we use the pattern `(?:(?!(?:stuff|to|exclude)<x>))[^/]*?)` where <x> is everything
        that comes after the negative group. `!(this|that)other` --> `(?:(?!(?:this|that)other))[^/]*?)`.

        We have to update the list before | for groups in groups: *(!(...)|stuff). Before we close a parent
        `extmatch`: `*(!(...))`. And of course on path separators (when path mode is on): `!(...)/stuff`.
        Lastly we make sure all is accounted for when finishing the pattern at the end.  If there is nothing
        to store, we store `$`: `(?:(?!(?:this|that)$))[^/]*?)`.

        When the inverse group is inside another group, what comes after the enclosing group is not known yet.
        A token is stored in its place, and replaced once it is. Groups inside the inverse group's own patterns
        are followed by the same thing as the inverse group itself, so they use the same token, which is replaced
        with the text of the lookahead.
        """

        if not self.inv_ext:
            return

        index = len(current) - 1
        while index >= 0:
            holder = current[index]
            if isinstance(holder, InvPlaceholder):
                content = current[index + 1:]
                if token is not None:
                    # Tail is not known yet, it is filled in when the text after the enclosing group is known
                    tail = token
                    self.tails_open = True
                else:
                    tail = _EOP if not self.pathname else self.path_eop
                # Groups after this one are copied into the lookahead, so they must know what follows them first
                self._resolve_tails(content, tail, token or '')
                content.append(tail)
                value = ''.join(content)
                if self.capture:
                    value = value.replace('(?#)', '?:')
                if index and holder.token and holder.token in current[index - 1]:
                    # Groups in the inverse group's own patterns are followed by the same thing
                    current[index - 1] = type(current[index - 1])(current[index - 1].replace(holder.token, value))
                if holder.shortcut:
                    # The patterns cannot match nothing, so the group matches nothing if the rest of the pattern
                    # matches. Matching nothing has the same restrictions as matching anything, like a leading dot.
                    base = self.path_star if self.pathname else _STAR
                    opening = current[index - 1]
                    size = len('((?#)') if opening.startswith('((?#)') else len('(?:')
                    current[index - 1] = type(opening)(
                        opening[:size] + str(holder)[:-len(base)] + '(?=' + value + ')|' + opening[size:]
                    )
                current[index] = value + _EXCLA_GROUP_CLOSE.format(str(holder))
                self.inv_ext -= 1
            index -= 1

    def _sized(self, value: str) -> str:
        """Track that a piece matches a single character, which is only needed in the patterns of an inverse group."""

        return Sized(value) if self.in_inv else value

    def parse_extend(
        self,
        c: str,
        i: util.StringIter,
        current: list[str],
        reset_dot: bool = False,
        parent: str = '',
        parent_token: str = ''
    ) -> bool:
        """Parse extended pattern lists."""

        list_type = c
        index = i.index

        if not i.match(RE_EXT_GROUP):
            i.rewind(i.index - index)
            return False

        gtoken = '(?#tail%d)' % self.tail_id
        self.tail_id += 1

        # Save state
        temp_ext_empty = self.ext_empty
        bad_sequence = self.bad_sequence
        temp_dir_start = self.dir_start
        temp_after_start = self.after_start
        temp_in_list = self.in_list
        temp_inv_ext = self.inv_ext
        temp_in_inv = self.in_inv
        self.ext_empty = False
        self.in_list = True
        if list_type == '!':
            self.in_inv += 1

        # Whether an alternative of this group starts with a dot, directly or through a nested group that starts it
        has_dot = False

        if reset_dot:
            self.match_dot_dir = False

        # Start list parsing
        success = True
        extended = []  # type: list[str]

        try:
            while c != ')':
                c = next(i)

                if not self.extend:
                    raise StopIteration

                # See if we should parse a nested extended pattern.
                if c in EXT_TYPES:
                    alt_start = self._alt_start(extended)
                    if self.parse_extend(c, i, extended, parent=list_type, parent_token=gtoken):
                        if alt_start and self.group_has_dot:
                            has_dot = True
                        continue

                if c == '*':
                    self._handle_star(i, extended)
                elif c == '.':
                    if self._alt_start(extended):
                        has_dot = True
                    size = len(extended)
                    self._handle_dot(i, extended)
                    if len(extended) == size + 1:
                        extended[-1] = self._sized(extended[-1])
                    if self.after_start:
                        self.match_dot_dir = self.dot and not self.nodotdir
                        self.reset_dir_track()
                elif c == '?':
                    extended.append(self._sized(self._restrict_sequence(extended) + _QMARK))
                elif c == '/':
                    if self.pathname:
                        extended.append(self._restrict_extended_slash())
                    extended.append(self.sep)
                elif c == '|':
                    self.clean_up_inverse(extended, gtoken)
                    # Add a new slot, but avoid adding more empty slots if we have a known one
                    if not extended or extended[-1] == '|':
                        if not self.ext_empty:
                            extended.append(c)
                            self.ext_empty = True
                    else:
                        extended.append(c)
                    # Gobble up any empty slots, but avoid adding redundant empty slots
                    if i.match_next(RE_EMPTY_EXT_SLOTS) and not self.ext_empty:
                        extended.append('|')
                        self.ext_empty = True
                    if temp_after_start:
                        self.set_start_dir()
                elif self.numrange and c == '<':
                    extended.append(self._handle_numrange(i))
                elif c == '\\':
                    try:
                        value = self._references(i)
                        # Escaped path separators are not a character
                        extended.append(value if i.previous() in ('\\', '/') else self._sized(value))
                    except DotException:
                        continue
                    except StopIteration:
                        # We've reached the end.
                        # Do nothing because this is going to abort the `extmatch` anyways.
                        pass
                elif c == '[' and (self.bad_sequence == -1 or i.index > self.bad_sequence):
                    subindex = i.index
                    try:
                        extended.append(self._sized(self._sequence(i, extended)))
                    except StopIteration:
                        self.bad_sequence = i.index
                        i.rewind(i.index - subindex)
                        extended.append(self._sized(r'\['))
                elif c != ')':
                    extended.append(self._sized(re.escape(c)))

                self.update_dir_state()

            # Pop extra pipe if we get an extra one.
            if len(extended) > 1 and (extended[-1] == '|' == extended[-2]):
                extended.pop(-1)

            # See if the current content is going into it's own slot, by itself
            # Additionally, determine if this group is the only child.

            # At the start of a slot?
            group_start = not current
            slot_start = group_start or current[-1] == '|'
            group_end = slot_end = False
            try:
                end = next(i)
                group_end = end == ')'
                slot_end = group_end or end == '|'
                i.rewind(1)
            except StopIteration:
                pass
            empty_slot = slot_start and slot_end
            only_child = parent and group_start and group_end
            promote_ext = EXT_PROMOTE.get(parent, {})

            # Promote the group type to a different type before final processing.
            # Child content has already been reduced into this parent.
            if not self.capture and extended and isinstance(extended[-1], ExtPromote):
                t = str(extended.pop(-1))
                list_type = t

            ext_reduce = EXT_REDUCE[list_type]

            # Extended groups cannot match `.` or `..` ever.
            if not temp_in_list and temp_after_start:
                current.append(self.no_dir)

            # Reduce child group into the parent and notify the parent type should change.
            # Groups must be compatible. e.g. `!(!(a|b))` -> `@(a|b)`.
            if not self.capture and only_child and list_type in promote_ext:
                self._retoken(extended, gtoken, parent_token)
                current.extend(extended)
                t = promote_ext[list_type]
                current.append(ExtPromote(t))
                temp_in_list = False

            # Reduce current group into parent group.
            # When reducing extended groups  `+(a|@(b|c)|d)` -> `+(a|b|c|d)` for
            # more efficient regular expressions. Nested group must occupy it's own
            # slot. e.g. `+(a|@(b|c)|d)` not `+(a|test@(b|c)|d)`.
            # Certain groups cannot be reduced without adding a blank entry.
            elif not self.capture and parent in ext_reduce['parent'] and empty_slot:
                self._retoken(extended, gtoken, parent_token)
                current.extend(extended)
                if parent in ext_reduce['empty'] and not temp_ext_empty:
                    current.append('|')
                    if not group_end:
                        current.append('|')
                    temp_ext_empty = True

            # Finalize groups of varying types.
            # Groups at the top level are tracked so atomic `*` segments can avoid them.
            elif list_type == '?':
                self._finish_group(extended, gtoken)
                prefix = self._group_start(temp_in_list, has_dot)
                if prefix:
                    template = _QMARK_GUARD_CAPTURE_GROUP if self.capture else _QMARK_GUARD_GROUP
                    group = ExtGroup(template.format(prefix, ''.join(extended)))
                else:
                    group = ExtGroup((_QMARK_CAPTURE_GROUP if self.capture else _QMARK_GROUP).format(''.join(extended)))
                # The lengths and whether a group can be empty are only used by an inverse group around the group
                if self.in_inv:
                    lens = self._group_lengths(extended)
                    group.lens = None if lens is None else union_lengths(lens, Lengths({0: ''}))
                group.optional = True
                current.append(group)
            elif list_type == '*':
                self._finish_group(extended, gtoken)
                prefix = self._group_start(temp_in_list, has_dot)
                if prefix:
                    template = _STAR_GUARD_CAPTURE_GROUP if self.capture else _STAR_GUARD_GROUP
                    group = ExtGroup(template.format(prefix, ''.join(extended)))
                else:
                    group = ExtGroup((_STAR_CAPTURE_GROUP if self.capture else _STAR_GROUP).format(''.join(extended)))
                group.optional = True
                current.append(group)
            elif list_type == '+':
                self._finish_group(extended, gtoken)
                prefix = self._group_start(temp_in_list, has_dot)
                template = _PLUS_CAPTURE_GROUP if self.capture else _PLUS_GROUP
                group = ExtGroup(template.format(prefix, ''.join(extended)))
                if self.in_inv:
                    group.non_empty = not self._maybe_empty(extended)
                current.append(group)
            elif list_type == '@':
                self._finish_group(extended, gtoken)
                prefix = self._group_start(temp_in_list, has_dot)
                group = ExtGroup((_CAPTURE_GROUP if self.capture else _GROUP).format(prefix, ''.join(extended)))
                if self.in_inv:
                    group.lens = self._group_lengths(extended)
                    group.non_empty = not self._maybe_empty(extended)
                current.append(group)
            elif list_type == '!':
                # The star may land at the start of a name when it is in a group slot or follows a group.
                check_start = (temp_in_list or bool(current and isinstance(current[-1], ExtGroup))) and not self.dot
                if self.pathname:
                    if not temp_after_start or self.match_dot_dir:
                        star = (self.seq_path_group_dot if check_start else '') + self.path_star
                    elif temp_after_start and not self.dot:
                        if temp_in_list:
                            star = self.no_dir + self.seq_path_group_dot + self.path_star
                        else:
                            star = self.path_star_dot2
                    else:
                        star = self.path_star_dot1
                else:
                    if self.dot:
                        star = _STAR
                    elif not temp_after_start:
                        star = (_GROUP_NO_DOT if check_start else '') + _STAR
                    else:
                        star = (_NO_DOT if not temp_in_list else _GROUP_NO_DOT) + _STAR

                if temp_after_start:
                    star = self.need_char + star

                # If the text that the patterns can match is of known lengths, what the group matches does not depend on
                # what follows it.
                exact = self._exact_inverse(self._group_lengths(extended), star, extended)
                if exact is not None:
                    group = ExtGroup(exact[0])
                    if temp_in_inv:
                        group.lens = exact[1]
                    current.append(group)
                else:
                    self._finish_group(extended, gtoken)
                    self.inv_ext += 1
                    # If pattern is at the end, anchor the match to the end.
                    current.append(
                        ExtGroup((_EXCLA_CAPTURE_GROUP if self.capture else _EXCLA_GROUP).format(''.join(extended)))
                    )
                    # Place holder for closing, but store the proper star
                    # so we know which one to use
                    shortcut = (
                        not temp_in_inv and star.endswith(self.path_star if self.pathname else _STAR) and
                        not self._maybe_empty(extended)
                    )
                    current.append(InvPlaceholder(star, gtoken, shortcut))

        except StopIteration:
            success = False
            i.rewind(i.index - index)
            self.extend = False
            self.inv_ext = temp_inv_ext
            self.bad_sequence = bad_sequence
            self.dir_start = temp_dir_start
            self.after_start = temp_after_start

        self.in_list = temp_in_list
        self.in_inv = temp_in_inv
        self.ext_empty = temp_ext_empty

        self.group_has_dot = has_dot
        if success:
            self.reset_dir_track()

        return success

    def consume_path_sep(self, i: util.StringIter) -> None:
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

    def atomic_stars(self, parts: list[str]) -> None:
        """
        Wrap non-extended-glob single stars, except the last, in atomic groups.

        Similar to CPython's `fnmatch` fix for multi-`*` backtracking.

        A star and everything up to the next star is made atomic only if it is of fixed length.
        Only then is the first match of the segment guaranteed to be as good as any other,
        as the next star can absorb any difference.

        Extended glob patterns are variable by nature, so if the segments contains
        extended glob groups, the star is left as is.
        """

        # No stars were emitted; nothing to do.
        if self.emitted_star == -1:
            return

        # Create atomic groups that contain the current star up to the next star
        start = -1
        for r in range(self.emitted_star, len(parts)):
            part = parts[r]
            # Start an atomic star
            if start == -1:
                if isinstance(part, AtomicStar):
                    start = r
            # Reject a segment if it contains extended glob groups
            elif isinstance(part, ExtGroup):
                parts[start] = str(parts[start])
                start = -1
            # Found next star; complete atomic group and start next atomic star
            elif isinstance(part, AtomicStar):
                end = r - 1
                parts[start] = f'(?>{parts[start]}'
                parts[end] = f'{parts[end]})'
                start = r

        # Current star is the last star; no need to create an atomic star
        if start > -1:
            parts[start] = str(parts[start])

        # All valid atomic stars handled
        self.emitted_star = -1

    def root(self, pattern: str, current: list[str]) -> None:
        """Start parsing the pattern."""

        self.set_after_start()
        i = util.StringIter(pattern)
        trailing_globstar_directory = False

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
        elif self.pathname and pattern.startswith('/'):
            root_specified = True

        if self.no_abs and root_specified:
            raise ValueError('The pattern must be a relative path pattern')

        if root_specified:
            self.matchbase = False
            self.extmatchbase = False

        if not root_specified and self.realpath:
            current.append(_NO_WIN_ROOT if self.win_drive_detect else _NO_ROOT)
            current.append('')

        for c in i:

            index = i.index

            if self.extend and c in EXT_TYPES and self.parse_extend(c, i, current, True):
                self.update_dir_state()
                continue

            if c == '.':
                self._handle_dot(i, current)
            elif c == '*':
                trailing_globstar_directory = self._handle_star(i, current)
            elif c == '?':
                current.append(self._restrict_sequence(current) + _QMARK)
            elif c == '/':
                if self.pathname:
                    self.set_start_dir()
                    self.atomic_stars(current)
                    self._close_root(current)
                    current.append(self.sep + _ONE_OR_MORE)
                    self.consume_path_sep(i)
                    self.matchbase = False
                else:
                    current.append(self.sep)
            elif self.numrange and c == '<':
                current.append(self._handle_numrange(i))
            elif c == '\\':
                index = i.index
                try:
                    value = self._references(i)
                    if self.dir_start:
                        self.atomic_stars(current)
                        self._close_root(current)
                        self.consume_path_sep(i)
                        self.matchbase = False
                    current.append(value)
                except DotException:
                    continue
                except StopIteration:
                    # Escapes nothing, ignore
                    i.rewind(i.index - index)
            elif c == '[' and (self.bad_sequence == -1 or i.index > self.bad_sequence):
                index = i.index
                try:
                    current.append(self._sequence(i, current))
                except StopIteration:
                    self.bad_sequence = i.index
                    i.rewind(i.index - index)
                    current.append(re.escape(c))
            else:
                current.append(re.escape(c))

            self.update_dir_state()

        self.atomic_stars(current)
        self._close_root(current)

        if self.pathname:
            if trailing_globstar_directory and current[-1] == _GLOBSTAR_DIV.format(self.sep):
                # A terminal star may match the end, but an explicit slash still requires a directory.
                current.append(f'(?<={self.sep})')
            current.append(_PATH_TRAIL.format(self.sep))

    def _parse(self, p: str) -> str:
        """Parse pattern."""

        result = ['']
        prepend = ['']

        if self.anchor:
            p, number = (RE_ANCHOR if not self.win_drive_detect else RE_WIN_ANCHOR).subn('', p)
            if number:
                self.matchbase = False
                self.extmatchbase = False

        if self.matchbase or self.extmatchbase:
            if self.globstarlong and self.follow:
                self.root('***', prepend)
            else:
                globstar = self.globstar
                self.globstar = True
                self.root('**', prepend)
                self.globstar = globstar

        # We have an escape, but it escapes nothing
        if p == '\\':
            p = ''

        if p:
            self.root(p, result)

        if p and (self.matchbase or self.extmatchbase):
            result = prepend + result

        case_flag = 'i' if not self.case_sensitive else ''
        pattern = Rf'^(?s{case_flag}:{"".join(result)})$'

        if self.capture:
            # Strip out unnecessary regex comments
            pattern = pattern.replace('(?#)', '')

        return pattern

    def parse(self) -> AnyStr:
        """Parse pattern list."""

        if isinstance(self.pattern, bytes):
            pattern = self._parse(self.pattern.decode('latin-1')).encode('latin-1')
        else:
            pattern = self._parse(self.pattern)

        return pattern
