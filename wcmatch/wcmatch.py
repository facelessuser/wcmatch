"""
Wild Card Match.

A module for performing wild card matches.

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
import os
import re
from . import _wcparse
from . import util

__all__ = (
    "CASE", "IGNORECASE", "RAWCHARS", "FILEPATHNAME", "DIRPATHNAME", "PATHNAME",
    "EXTMATCH", "GLOBSTAR", "BRACE", "MINUSNEGATE", "SYMLINKS", "HIDDEN", "RECURSIVE",
    "MATCHBASE",
    "C", "I", "R", "P", "E", "G", "M", "DP", "FP", "SL", "HD", "RV", "X", "B",
    "WcMatch"
)

C = CASE = _wcparse.CASE
I = IGNORECASE = _wcparse.IGNORECASE
R = RAWCHARS = _wcparse.RAWCHARS
E = EXTMATCH = _wcparse.EXTMATCH
G = GLOBSTAR = _wcparse.GLOBSTAR
B = BRACE = _wcparse.BRACE
M = MINUSNEGATE = _wcparse.MINUSNEGATE
X = MATCHBASE = _wcparse.MATCHBASE

# Control `PATHNAME` individually for folder exclude and files
DP = DIRPATHNAME = 0x1000000
FP = FILEPATHNAME = 0x2000000
SL = SYMLINKS = 0x4000000
HD = HIDDEN = 0x8000000
RV = RECURSIVE = 0x10000000

# Internal flags
_ANCHOR = _wcparse._ANCHOR
_NEGATE = _wcparse.NEGATE
_DOTMATCH = _wcparse.DOTMATCH
_NEGATEALL = _wcparse.NEGATEALL
_SPLIT = _wcparse.SPLIT
_FORCEWIN = _wcparse.FORCEWIN
_PATHNAME = _wcparse.PATHNAME

# Control `PATHNAME` for file and folder
P = PATHNAME = DIRPATHNAME | FILEPATHNAME

FLAG_MASK = (
    CASE |
    IGNORECASE |
    RAWCHARS |
    EXTMATCH |
    GLOBSTAR |
    BRACE |
    MINUSNEGATE |
    DIRPATHNAME |
    FILEPATHNAME |
    SYMLINKS |
    HIDDEN |
    RECURSIVE |
    MATCHBASE
)


class WcMatch:
    """Finds files by wildcard."""

    def __init__(self, root_dir, file_pattern=None, exclude_pattern=None, flags=0, limit=_wcparse.PATHNAME, **kwargs):
        """Initialize the directory walker object."""

        self._abort = False
        self._skipped = 0
        self._directory = _wcparse.norm_slash(root_dir, 0)
        self.is_bytes = isinstance(self._directory, bytes)
        if not self._directory:
            if self.is_bytes:
                curdir = bytes(os.curdir, 'ASCII')
            else:
                curdir = os.curdir
        else:
            curdir = self._directory
        self.sep = os.fsencode(os.sep) if self.is_bytes else os.sep
        self._root_dir = curdir if curdir.endswith(self.sep) else curdir + self.sep
        self.file_pattern = file_pattern
        if not self.file_pattern:
            self.file_pattern = _wcparse.WcRegexp(
                (re.compile(br'^.*$', re.DOTALL),) if self.is_bytes else (re.compile(r'^.*$', re.DOTALL),)
            )
        self.exclude_pattern = exclude_pattern if exclude_pattern is not None else (b'' if self.is_bytes else '')
        self._parse_flags(flags)
        self.limit = limit
        self.on_init(**kwargs)
        self.file_check, self.folder_exclude_check = self._compile(self.file_pattern, self.exclude_pattern)

    def _parse_flags(self, flags):
        """Parse flags."""

        self.flags = flags & FLAG_MASK
        self.flags |= _NEGATE | _DOTMATCH | _NEGATEALL | _SPLIT
        self.follow_links = bool(self.flags & SYMLINKS)
        self.show_hidden = bool(self.flags & HIDDEN)
        self.recursive = bool(self.flags & RECURSIVE)
        self.dir_pathname = bool(self.flags & DIRPATHNAME)
        self.file_pathname = bool(self.flags & FILEPATHNAME)
        self.matchbase = bool(self.flags & MATCHBASE)
        if util.platform() == "windows":
            self.flags |= _FORCEWIN
        self.flags = self.flags & (_wcparse.FLAG_MASK ^ MATCHBASE)

    def _compile_wildcard(self, pattern, pathname=False):
        """Compile or format the wildcard inclusion/exclusion pattern."""

        flags = self.flags
        if pathname:
            flags |= _PATHNAME | _ANCHOR
            if self.matchbase:
                flags |= MATCHBASE

        return _wcparse.compile(pattern, flags, self.limit) if pattern else None

    def _compile(self, file_pattern, folder_exclude_pattern):
        """Compile patterns."""

        if not isinstance(file_pattern, _wcparse.WcRegexp):
            file_pattern = self._compile_wildcard(file_pattern, self.file_pathname)

        if not isinstance(folder_exclude_pattern, _wcparse.WcRegexp):
            folder_exclude_pattern = self._compile_wildcard(folder_exclude_pattern, self.dir_pathname)

        return file_pattern, folder_exclude_pattern

    def _valid_file(self, base, name):
        """Return whether a file can be searched."""

        valid = False
        fullpath = os.path.join(base, name)
        if self.file_check is not None and self.compare_file(fullpath[self._base_len:] if self.file_pathname else name):
            valid = True
        if valid and (not self.show_hidden and util.is_hidden(fullpath)):
            valid = False
        return self.on_validate_file(base, name) if valid else valid

    def compare_file(self, filename):
        """Compare filename."""

        return self.file_check.match(filename)

    def on_validate_file(self, base, name):
        """Validate file override."""

        return True

    def _valid_folder(self, base, name):
        """Return whether a folder can be searched."""

        valid = True
        fullpath = os.path.join(base, name)
        if (
            not self.recursive or
            (
                self.folder_exclude_check is not None and
                not self.compare_directory(fullpath[self._base_len:] if self.dir_pathname else name)
            )
        ):
            valid = False
        if valid and (not self.show_hidden and util.is_hidden(fullpath)):
            valid = False
        return self.on_validate_directory(base, name) if valid else valid

    def compare_directory(self, directory):
        """Compare folder."""

        return not self.folder_exclude_check.match(directory + self.sep if self.dir_pathname else directory)

    def on_init(self, **kwargs):
        """Handle custom initialization."""

    def on_validate_directory(self, base, name):
        """Validate folder override."""

        return True

    def on_skip(self, base, name):
        """On skip."""

        return None

    def on_error(self, base, name):
        """On error."""

        return None

    def on_match(self, base, name):
        """On match."""

        return os.path.join(base, name)

    def on_reset(self):
        """On reset."""

    def get_skipped(self):
        """Get number of skipped files."""

        return self._skipped

    def kill(self):
        """Abort process."""

        self._abort = True

    def is_aborted(self):
        """Check if process has been aborted."""

        return self._abort

    def reset(self):
        """Revive class from a killed state."""

        self._abort = False

    def _walk(self):
        """Start search for valid files."""

        self._base_len = len(self._root_dir)

        for base, dirs, files in os.walk(self._root_dir, followlinks=self.follow_links):
            if self.is_aborted():
                break

            # Remove child folders based on exclude rules
            for name in dirs[:]:
                try:
                    if not self._valid_folder(base, name):
                        dirs.remove(name)
                except Exception:
                    dirs.remove(name)
                    value = self.on_error(base, name)
                    if value is not None:  # pragma: no cover
                        yield value

                if self.is_aborted():  # pragma: no cover
                    break

            # Search files if they were found
            if files:
                # Only search files that are in the include rules
                for name in files:
                    try:
                        valid = self._valid_file(base, name)
                    except Exception:
                        valid = False
                        value = self.on_error(base, name)
                        if value is not None:
                            yield value

                    if valid:
                        yield self.on_match(base, name)
                    else:
                        self._skipped += 1
                        value = self.on_skip(base, name)
                        if value is not None:
                            yield value

                    if self.is_aborted():
                        break

    def match(self):
        """Run the directory walker."""

        return list(self.imatch())

    def imatch(self):
        """Run the directory walker as iterator."""

        self.on_reset()
        self._skipped = 0
        for f in self._walk():
            yield f
