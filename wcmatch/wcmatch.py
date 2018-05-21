"""
Wild Card Match.

A custom implementation of glob.

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
import os
from .file_hidden import is_hidden as _is_hidden
from . import _wcparse
from . import util

__all__ = (
    "FORCECASE", "IGNORECASE", "RAWCHARS", "PATHNAME", "EXTGLOB", "GLOBSTAR", "BRACE",
    "F", "I", "R", "P", "E", "G",
    "WcMatch"
)

F = FORCECASE = _wcparse.FORCECASE
I = IGNORECASE = _wcparse.IGNORECASE
R = RAWCHARS = _wcparse.RAWCHARS
P = PATHNAME = _wcparse.PATHNAME
E = EXTGLOB = _wcparse.EXTGLOB
G = GLOBSTAR = _wcparse.GLOBSTAR
B = BRACE = _wcparse.BRACE

FLAG_MASK = (
    FORCECASE |
    IGNORECASE |
    RAWCHARS |
    PATHNAME |
    EXTGLOB |
    GLOBSTAR |
    BRACE
)


class WcMatch(object):
    """Finds files by wildcard."""

    def __init__(self, *args, **kwargs):
        """Init the directory walker object."""

        args = list(args)
        self._skipped = 0
        self._abort = False
        self.directory = util.norm_slash(args.pop(0))
        self.file_pattern = args.pop(0) if args else kwargs.pop('file_pattern', '')
        self.exclude_pattern = args.pop(0) if args else kwargs.pop('exclude_pattern', '')
        self.recursive = args.pop(0) if args else kwargs.pop('recursive', False)
        self.show_hidden = args.pop(0) if args else kwargs.pop('show_hidden', True)
        self.flags = (args.pop(0) if args else kwargs.pop('flags', 0)) & FLAG_MASK
        self.flags |= _wcparse.NEGATE | _wcparse.DOTGLOB
        self.pathname = bool(self.flags & PATHNAME)
        if self.pathname:
            self.flags ^= PATHNAME

        self.on_init(*args, **kwargs)
        self.file_check, self.folder_exclude_check = self._compile(self.file_pattern, self.exclude_pattern)

    def _compile_wildcard(self, pattern, force_default=False, pathname=False):
        """Compile or format the wildcard inclusion/exclusion pattern."""

        patterns = None
        flags = self.flags
        if self.pathname:
            flags |= PATHNAME
        if pattern:
            patterns = tuple(_wcparse.WcSplit(pattern, flags=self.flags).split())
        return _wcparse._compile(patterns, self.flags) if patterns else patterns

    def _compile(self, file_pattern, folder_exclude_pattern):
        """Compile patterns."""

        if not isinstance(file_pattern, _wcparse.WcRegexp):
            # Ensure file pattern is not empty
            if file_pattern is None:
                file_pattern = '*'

            file_pattern = self._compile_wildcard(file_pattern)

        if not isinstance(folder_exclude_pattern, _wcparse.WcRegexp):

            folder_exclude_pattern = self._compile_wildcard(folder_exclude_pattern)

        return file_pattern, folder_exclude_pattern

    def _is_hidden(self, path):
        """Check if file is hidden."""

        return _is_hidden(path) if not self.show_hidden else False

    def _valid_file(self, base, name):
        """Return whether a file can be searched."""

        valid = False
        if self.file_check is not None and not self._is_hidden(os.path.join(base, name)):
            valid = self.file_check.match(name)
        return self.on_validate_file(base, name) if valid else valid

    def on_validate_file(self, base, name):
        """Validate file override."""

        return True

    def _valid_folder(self, base, name):
        """Return whether a folder can be searched."""

        valid = True
        fullpath = os.path.join(base, name)
        if not self.recursive or self._is_hidden(fullpath):
            valid = False
        elif self.folder_exclude_check is not None:
            valid = not self.folder_exclude_check.match(fullpath if self.pathname else name)
        return self.on_validate_directory(base, name) if valid else valid

    def on_init(self, *args, **kwargs):
        """Handle custom init."""

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

    def get_skipped(self):
        """Get number of skipped files."""

        return self._skipped

    def kill(self):
        """Abort process."""

        self._abort = True

    def reset(self):
        """Revive class from a killed state."""

        self._abort = False

    def walk(self):
        """Start search for valid files."""

        for base, dirs, files in os.walk(self.directory):
            # Remove child folders based on exclude rules
            for name in dirs[:]:
                try:
                    if not self._valid_folder(base, name):
                        dirs.remove(name)
                except Exception:  # pragma: no cover
                    dirs.remove(name)
                    value = self.on_error(base, name)
                    if value:
                        yield value

                if self._abort:
                    break

            # Seach files if they were found
            if len(files):
                # Only search files that are in the inlcude rules
                for name in files:
                    try:
                        valid = self._valid_file(base, name)
                    except Exception:  # pragma: no cover
                        valid = False
                        value = self.on_error(base, name)
                        if value:
                            yield value

                    if valid:
                        yield self.on_match(base, name)
                    else:
                        self._skipped += 1
                        value = self.on_skip(base, name)
                        if value:
                            yield value

                    if self._abort:
                        break

            if self._abort:
                break

    def match(self):
        """Run the directory walker."""

        return list(self.imatch())

    def imatch(self):
        """Run the directory walker as iterator."""

        self._skipped = 0
        for f in self.walk():
            yield f
