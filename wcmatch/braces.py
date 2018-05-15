"""
A Bash like brace expander.

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
from . import util
import itertools
import re

__all__ = ('expand', 'iexpand')

_alpha = [chr(x) if x != 0x5c else '' for x in range(ord('A'), ord('z') + 1)]
_nalpha = list(reversed(_alpha))

RE_INT_ITER = re.compile(r'(-?\d+)\.{2}(-?\d+)(?:\.{2}(-?\d+))?(?=\})')
RE_CHR_ITER = re.compile(r'([A-Za-z])\.{2}([A-Za-z])(?:\.{2}(-?\d+))?(?=\})')


def expand(pattern, strip_escapes=False):
    """Expand braces."""

    return list(iexpand(pattern, strip_escapes))


def iexpand(pattern, strip_escapes=False):
    """Expand braces and return an iterator."""

    if isinstance(pattern, bytes):
        is_bytes = True
        pattern = pattern.decode('latin-1')

    else:
        is_bytes = False

    if is_bytes:
        return (entry.encode('latin-1') for entry in ExpandBrace().expand(pattern))

    else:
        return (entry for entry in ExpandBrace(strip_escapes).expand(pattern))


class ExpandBrace(object):
    """Expand braces like in Bash."""

    def __init__(self, strip_escapes=False):
        """Initialize."""

        self.detph = 0
        self.expanding = False
        self.strip_escapes = strip_escapes
        self.skip_index = []

    def set_expanding(self):
        """Set that we are expanding a sequence, and return whether a release is required by the caller."""

        status = not self.expanding
        if status:
            self.expanding = True
        return status

    def is_expanding(self):
        """Get status of whether we are expanding."""

        return self.expanding

    def release_expanding(self, release):
        """Release the expand status."""

        if release:
            self.expanding = False

    def get_escape(self, c, i):
        """Get an escape."""

        try:
            escaped = next(i)
        except StopIteration:
            escaped = ''
        return c + escaped if not self.strip_escapes else escaped

    def squash(self, a, b):
        """
        Squash the two arrays as one flat array.

        ~~~
        ['this', 'that'], [[' and', ' or']] => ['this and', 'this or', 'that and', 'that or']
        ~~~
        """

        return ((''.join(x) if isinstance(x, tuple) else x) for x in itertools.product(a, b))

    def get_literals(self, c, i):
        """
        Get a string literal.

        Gather all the literal chars up to opening curly or closing brace.
        Also gather chars between braces and commas within a group (is_expanding).
        """

        result = ['']

        try:
            while c:

                if c == '\\':
                    c = [self.get_escape(c, i)]

                elif c == '{':
                    # Try and get the group
                    index = i.index
                    try:
                        seq = self.get_sequence(next(i), i)
                        if seq:
                            c = seq
                    except StopIteration:
                        # Searched to end of string
                        # and still didn't find it.
                        i.rewind(i.index - index)

                elif self.is_expanding() and (c == ',' or (c == '}' and i.index not in self.skip_index)):
                    # We are Expanding within a group and found a group delimiter
                    # Retrun what we gathered before the group delimiters.
                    i.rewind(1)
                    return result

                # Squash the current set of literals.
                result = self.squash(result, [c] if isinstance(c, str) else c)

                c = next(i)
        except StopIteration:
            if self.is_expanding():
                return None

        return result

    def get_sequence(self, c, i):
        """
        Get the sequence.

        Get sequence between `{}`, such as: `{a,b}`, `{1..2[..inc]}`, etc.
        It will basically crawl to the end or find a valid series.
        """

        self.depth += 1
        result = []
        release = self.set_expanding()
        has_comma = False  # Used to indicate validity of group (`{1..2}` are an exception).
        is_empty = True  # Tracks whether the current slot is empty `{slot,slot,slot}`.
        index = i.index

        i.rewind(1)
        item = self.get_range(i)
        i.advance(1)
        if item is not None:
            self.release_expanding(release)
            self.depth -= 1
            return item

        try:
            while c:
                # Bash has some special top level logic. if `}` follows `{` but hasn't matched
                # a group yet, keep going except when the first 2 bytes are `{}` which gets
                # completely ignored.
                if (
                    c == '}' and
                    not (i.index == index and not i.index == 2 and self.depth == 1) and
                    not (self.depth == 1 and not has_comma and not i.index) and
                    i.index not in self.skip_index
                ):
                    # If there is no comma, we know the sequence is bogus.
                    if is_empty:
                        result.append('')
                    if not has_comma:
                        result = ['{' + literal + '}' for literal in result]
                    self.release_expanding(release)
                    self.depth -= 1
                    return result

                elif c == ',':
                    # Must be the first element in the list.
                    has_comma = True
                    if is_empty:
                        result.append('')
                    else:
                        is_empty = True

                else:
                    if c == '}':
                        # Top level: Aggressively keep searching for a group
                        value = None
                        while value is None and i.index not in self.skip_index:
                            self.skip_index.append(i.index)
                            i.rewind(i.index - index)
                            try:
                                value = self.get_literals(c, i)
                            except StopIteration:
                                # Clean up
                                self.skip_index.clear()
                                raise
                        if value is not None:
                            result.extend(value)
                            is_empty = False
                    else:
                        # Lower level: Try to find group, but give up if cannot acquire.
                        value = self.get_literals(c, i)
                        if value is not None:
                            result.extend(value)
                            is_empty = False

                c = next(i)
        except StopIteration:
            self.release_expanding(release)
            self.depth -= 1
            raise

    def get_range(self, i):
        """
        Check and retrieve range if value is a valid range.

        Here we are looking to see if the value is series or range.
        We look for `{1..2[..inc]}` or `{a..z[..inc]}` (negative numbers are fine).
        """

        try:
            m = i.match(RE_INT_ITER)
            if m:
                return list(self.get_int_range(*m.groups()))

            m = i.match(RE_CHR_ITER)
            if m:
                return list(self.get_char_range(*m.groups()))
        except ValueError:
            pass

        return None

    def format_value(self, value, padding):
        """Get padding adjusting for negative values."""

        # padding = padding - 1 if value < 0 and padding > 0 else padding
        # prefix = '-' if value < 0 else ''

        if padding:
            return "{:0{pad}d}".format(value, pad=padding)

        else:
            return str(value)

    def get_int_range(self, start, end, increment=None):
        """Get an integer range between start and end and increments of increment."""

        first, last = int(start), int(end)
        increment = int(increment) if increment is not None else 1
        max_length = max(len(start), len(end))

        if increment == 0:
            raise ValueError

        if start[0] == '-':
            start = start[1:]

        if end[0] == '-':
            end = end[1:]

        if (len(start) > 1 and start[0] == '0') or (len(end) > 1 and end[0] == '0'):
            padding = max_length

        else:
            padding = 0

        if first < last:
            r = range(first, last + 1, -increment if increment < 0 else increment)

        else:
            r = range(first, last - 1, increment if increment < 0 else -increment)

        return (self.format_value(value, padding) for value in r)

    def get_char_range(self, start, end, increment=None):
        """Get a range of alphabetic characters."""

        increment = int(increment) if increment else 1
        if increment < 0:
            increment = -increment

        if increment == 0:
            raise ValueError

        inverse = start > end
        alpha = _nalpha if inverse else _alpha

        start = alpha.index(start)
        end = alpha.index(end)

        if start < end:
            return alpha[start:end + 1:increment]

        else:
            return alpha[end:start + 1:increment]

    def expand(self, pattern):
        """Expand."""

        self.depth = 0
        self.expanding = False
        i = iter(util.StringIter(pattern))
        return self.get_literals(next(i), i)
