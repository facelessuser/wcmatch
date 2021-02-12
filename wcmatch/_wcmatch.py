"""Handle path matching."""
import re
import os
import copyreg
from . import util


RE_WIN_MOUNT = (
    re.compile(r'\\|[a-z]:(?:\\|$)', re.I),
    re.compile(br'\\|[a-z]:(?:\\|$)', re.I)
)
RE_MOUNT = (
    re.compile(r'/'),
    re.compile(br'/')
)


class _Match:
    """Match the given pattern."""

    def __init__(self, filename, include, exclude, real, path, follow, root_dir=None):
        """Initialize."""

        self.filename = filename
        self.include = include
        self.exclude = exclude
        self.real = real
        self.path = path
        self.follow = follow
        self.is_bytes = isinstance(self.filename, bytes)
        self.ptype = util.BYTES if self.is_bytes else util.UNICODE
        self.root_dir = root_dir

    def _fs_match(self, pattern, filename, is_dir, sep, follow, symlinks, root):
        """
        Match path against the pattern.

        Since `globstar` doesn't match symlinks (unless `FOLLOW` is enabled), we must look for symlinks.
        If we identify a symlink in a `globstar` match, we know this result should not actually match.

        We only check for the symlink if we know we are looking at a directory.
        And we only call `lstat` if we can't find it in the cache.

        We know it's a directory if:

        1. If the base is a directory, all parts are directories.
        2. If we are not the last part of the `globstar`, the part is a directory.
        3. If the base is a file, but the part is not at the end, it is a directory.

        """

        matched = False

        end = len(filename)
        base = None
        m = pattern.fullmatch(filename)
        if m:
            matched = True
            # Lets look at the captured `globstar` groups and see if that part of the path
            # contains symlinks.
            if not follow:
                last = len(m.groups())
                for i, star in enumerate(m.groups(), 1):
                    if star:
                        at_end = m.end(i) == end
                        parts = star.strip(sep).split(sep)
                        if base is None:
                            base = os.path.join(root, filename[:m.start(i)])
                        for part in parts:
                            base = os.path.join(base, part)
                            if is_dir or i != last or not at_end:
                                is_link = symlinks.get(base, None)
                                if is_link is not None:
                                    matched = not is_link
                                else:
                                    is_link = os.path.islink(base)
                                    symlinks[base] = is_link
                                    matched = not is_link
                                if not matched:
                                    break
                    if not matched:
                        break
        return matched

    def _match_real(self, symlinks, root):
        """Match real filename includes and excludes."""

        sep = '\\' if util.platform() == "windows" else '/'
        if isinstance(self.filename, bytes):
            sep = os.fsencode(sep)

        is_dir = self.filename.endswith(sep)
        try:
            is_file_dir = os.path.isdir(os.path.join(root, self.filename))
        except OSError:  # pragma: no cover
            is_file_dir = False

        if not is_dir and is_file_dir:
            is_dir = True
            filename = self.filename + sep
        else:
            filename = self.filename

        matched = False
        for pattern in self.include:
            if self._fs_match(pattern, filename, is_dir, sep, self.follow, symlinks, root):
                matched = True
                break

        if matched:
            if self.exclude:
                for pattern in self.exclude:
                    if self._fs_match(pattern, filename, is_dir, sep, True, symlinks, root):
                        matched = False
                        break

        return matched

    def match(self):
        """Match."""

        if self.real:
            root = self.root_dir if self.root_dir else (b'.' if self.is_bytes else '.')

            if not isinstance(self.filename, type(root)):
                raise TypeError(
                    "The filename and root directory should be of the same type, not {} and {}".format(
                        type(self.filename), type(self.root_dir)
                    )
                )

            if self.include and not isinstance(self.include[0].pattern, type(self.filename)):
                raise TypeError(
                    "The filename and pattern should be of the same type, not {} and {}".format(
                        type(self.filename), type(self.include[0].pattern)
                    )
                )

            mount = RE_WIN_MOUNT[self.ptype] if util.platform() == "windows" else RE_MOUNT[self.ptype]

            if not mount.match(self.filename):
                exists = os.path.lexists(os.path.join(root, self.filename))
            else:
                exists = os.path.lexists(self.filename)

            if exists:
                symlinks = {}
                return self._match_real(symlinks, root)
            else:
                return False

        matched = False
        for pattern in self.include:
            if pattern.fullmatch(self.filename):
                matched = True
                break

        if matched:
            matched = True
            if self.exclude:
                for pattern in self.exclude:
                    if pattern.fullmatch(self.filename):
                        matched = False
                        break
        return matched


class WcRegexp(util.Immutable):
    """File name match object."""

    __slots__ = ("_include", "_exclude", "_real", "_path", "_follow", "_hash")

    def __init__(self, include, exclude=None, real=False, path=False, follow=False):
        """Initialization."""

        super(WcRegexp, self).__init__(
            _include=include,
            _exclude=exclude,
            _real=real,
            _path=path,
            _follow=follow,
            _hash=hash(
                (
                    type(self),
                    type(include), include,
                    type(exclude), exclude,
                    type(real), real,
                    type(path), path,
                    type(follow), follow
                )
            )
        )

    def __hash__(self):
        """Hash."""

        return self._hash

    def __len__(self):
        """Length."""

        return len(self._include) + (len(self._exclude) if self._exclude is not None else 0)

    def __eq__(self, other):
        """Equal."""

        return (
            isinstance(other, WcRegexp) and
            self._include == other._include and
            self._exclude == other._exclude and
            self._real == other._real and
            self._path == other._path and
            self._follow == other._follow
        )

    def __ne__(self, other):
        """Equal."""

        return (
            not isinstance(other, WcRegexp) or
            self._include != other._include or
            self._exclude != other._exclude or
            self._real != other._real or
            self._path != other._path or
            self._follow != other._follow
        )

    def match(self, filename, root_dir=None):
        """Match filename."""

        return _Match(
            filename,
            self._include,
            self._exclude,
            self._real,
            self._path,
            self._follow,
            root_dir=root_dir
        ).match()


def _pickle(p):
    return WcRegexp, (p._include, p._exclude, p._real, p._path, p._follow)


copyreg.pickle(WcRegexp, _pickle)
