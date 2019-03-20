# -*- coding: utf-8 -*-
"""Tests for `fnmatch`."""
import unittest
import pytest
import mock
import wcmatch.fnmatch as fnmatch
from wcmatch import util
import wcmatch._wcparse as _wcparse


class TestFnMatch:
    """
    Test `fnmatch`.

    Each entry in `cases` is run through the `fnmatch`.  They are also run through
    `fnsplit` and then `fnmatch` as a separate operation to ensure `fnsplit` adds
    no unintended side effects.

    Each case entry is an array of 4 parameters.

    * Pattern
    * File name
    * Expected result (boolean of whether pattern matched file name)
    * Flags

    The default flags are `DOTMATCH`. Any flags passed through via entry are XORed.
    So if `DOTMATCH` is passed via an entry, it will actually disable the default `DOTMATCH`.
    """

    cases = [
        # Basic test of traditional features
        ['abc', 'abc', True, 0],
        ['?*?', 'abc', True, 0],
        ['???*', 'abc', True, 0],
        ['*???', 'abc', True, 0],
        ['???', 'abc', True, 0],
        ['*', 'abc', True, 0],
        ['ab[cd]', 'abc', True, 0],
        ['ab[!de]', 'abc', True, 0],
        ['ab[de]', 'abc', False, 0],
        ['??', 'a', False, 0],
        ['b', 'a', False, 0],

        # Test that '\' is handled correctly in character sets;
        [r'[\]', '\\', False, 0],
        [r'[!\]', 'a', False, 0],
        [r'[!\]', '\\', False, 0],
        [r'[\\]', '\\', True, 0],
        [r'[!\\]', 'a', True, 0],
        [r'[!\\]', '\\', False, 0],

        # Test that filenames with newlines in them are handled correctly.
        ['foo*', 'foo\nbar', True, 0],
        ['foo*', 'foo\nbar\n', True, 0],
        ['foo*', '\nfoo', False, 0],
        ['*', '\n', True, 0],

        # Force case: General
        ['abc', 'abc', True, fnmatch.F],
        ['abc', 'AbC', False, fnmatch.F],
        ['AbC', 'abc', False, fnmatch.F],
        ['AbC', 'AbC', True, fnmatch.F],

        # Force case: slash conventions
        ['usr/bin', 'usr/bin', True, fnmatch.F],
        ['usr/bin', 'usr\\bin', False, fnmatch.F],
        [r'usr\\bin', 'usr/bin', False, fnmatch.F],
        [r'usr\\bin', 'usr\\bin', True, fnmatch.F],

        # Wildcard tests
        [b'te*', b'test', True, 0],
        [b'te*\xff', b'test\xff', True, 0],
        [b'foo*', b'foo\nbar', True, 0],

        # OS specific case behavior
        ['abc', 'abc', True, 0],
        ['abc', 'AbC', not util.is_case_sensitive(), 0],
        ['AbC', 'abc', not util.is_case_sensitive(), 0],
        ['AbC', 'AbC', True, 0],

        # OS specific slash behavior
        ['usr/bin', 'usr/bin', True, 0],
        ['usr/bin', 'usr\\bin', not util.is_case_sensitive(), 0],
        [r'usr\\bin', 'usr/bin', not util.is_case_sensitive(), 0],
        [r'usr\\bin', 'usr\\bin', True, 0],

        # Ensure that we don't fail on regular expression related symbols
        # such as &&, ||, ~~, --, or [.  Currently re doesn't do anything with
        # && etc., but they are handled special in re as there are plans to utilize them.
        ['[[]', '[', True, 0],
        ['[a&&b]', '&', True, 0],
        ['[a||b]', '|', True, 0],
        ['[a~~b]', '~', True, 0],
        ['[a-z+--A-Z]', ',', True, 0],
        ['[a-z--/A-Z]', '.', True, 0],

        # `Dotmatch` cases
        ['.abc', '.abc', True, 0],
        [r'\.abc', '.abc', True, 0],
        ['?abc', '.abc', True, 0],
        ['*abc', '.abc', True, 0],
        ['[.]abc', '.abc', True, 0],
        ['*(.)abc', '.abc', True, fnmatch.E],
        ['*(?)abc', '.abc', True, fnmatch.E],
        ['*(?|.)abc', '.abc', True, fnmatch.E],
        ['*(?|*)abc', '.abc', True, fnmatch.E],
        ['!(test)', '.abc', True, fnmatch.E],

        # Turn off `dotmatch` cases
        ['.abc', '.abc', True, fnmatch.D],
        [r'\.abc', '.abc', True, fnmatch.D],
        ['?abc', '.abc', False, fnmatch.D],
        ['*abc', '.abc', False, fnmatch.D],
        ['[.]abc', '.abc', False, fnmatch.D],
        ['*(.)abc', '.abc', False, fnmatch.E | fnmatch.D],
        [r'*(\.)abc', '.abc', False, fnmatch.E | fnmatch.D],
        ['*(?)abc', '.abc', False, fnmatch.E | fnmatch.D],
        ['*(?|.)abc', '.abc', False, fnmatch.E | fnmatch.D],
        ['*(?|*)abc', '.abc', False, fnmatch.E | fnmatch.D],
        ['a.bc', 'a.bc', True, fnmatch.D],
        ['a?bc', 'a.bc', True, fnmatch.D],
        ['a*bc', 'a.bc', True, fnmatch.D],
        ['a[.]bc', 'a.bc', True, fnmatch.D],
        ['a*(.)bc', 'a.bc', True, fnmatch.E | fnmatch.D],
        [r'a*(\.)bc', 'a.bc', True, fnmatch.E | fnmatch.D],
        ['a*(?)bc', 'a.bc', True, fnmatch.E | fnmatch.D],
        ['a*(?|.)bc', 'a.bc', True, fnmatch.E | fnmatch.D],
        ['a*(?|*)bc', 'a.bc', True, fnmatch.E | fnmatch.D],
        ['!(test)', '.abc', False, fnmatch.D | fnmatch.E],
        ['!(test)', 'abc', True, fnmatch.D | fnmatch.E],

        # POSIX style character classes
        ['[[:alnum:]]bc', 'zbc', True, 0],
        ['[[:alnum:]]bc', '1bc', True, 0],
        ['[a[:alnum:]]bc', 'zbc', True, 0],
        ['[[:alnum:][:blank:]]bc', ' bc', True, 0],

        # We can't use a character class as a range.
        ['[-[:alnum:]]bc', '-bc', True, 0],
        ['[a-[:alnum:]]bc', '-bc', True, 0],
        ['[[:alnum:]-z]bc', '-bc', True, 0],

        # Negation
        ['[![:alnum:]]bc', '!bc', True, 0],
        ['[^[:alnum:]]bc', '!bc', True, 0],

        # Backwards ranges
        ['[a-z]', 'a', True, 0],
        ['[z-a]', 'a', False, 0],
        ['[!z-a]', 'a', True, 0],
        ['[!a-z]', 'a', False, 0],
        ['[9--]', '9', False, 0],

        # Escaped slashes are just slashes as they aren't treated special beyond normalization.
        [r'a\/b', ('a/b' if util.is_case_sensitive() else 'a\\\\b'), True, 0]
    ]

    @classmethod
    def setup_class(cls):
        """Setup the tests."""

        cls.flags = fnmatch.DOTMATCH

    @staticmethod
    def assert_equal(a, b):
        """Assert equal."""

        assert a == b, "Comparison between objects yielded False."

    @classmethod
    def evaluate(cls, case):
        """Evaluate matches."""

        flags = case[3]
        flags = cls.flags ^ flags
        print("PATTERN: ", case[0])
        print("FILE: ", case[1])
        print("FLAGS: ", bin(flags))
        print("TEST: ", case[2], '\n')
        cls.assert_equal(fnmatch.fnmatch(case[1], case[0], flags=flags), case[2])
        cls.assert_equal(
            fnmatch.fnmatch(case[1], fnmatch.fnsplit(case[0], flags=flags), flags=flags), case[2]
        )

    @pytest.mark.parametrize("case", cases)
    def test_cases(self, case):
        """Test case."""

        self.evaluate(case)


class TestFnMatchFilter:
    """
    Test filter.

    `cases` is used in conjunction with the `filter` command
    which takes a list of file names and returns only those which match.

    * Pattern
    * List of filenames
    * Expected result (list of filenames that matched the pattern)
    * Flags

    The default flags are `DOTMATCH`. Any flags passed through via entry are XORed.
    So if `DOTMATCH` is passed via an entry, it will actually disable the default `DOTMATCH`.
    """

    cases = [
        ['P*', ['Python', 'Ruby', 'Perl', 'Tcl'], ['Python', 'Perl'], 0],
        [b'P*', [b'Python', b'Ruby', b'Perl', b'Tcl'], [b'Python', b'Perl'], 0],
        [
            '*.p*',
            ['Test.py', 'Test.rb', 'Test.PL'],
            (['Test.py', 'Test.PL'] if not util.is_case_sensitive() else ['Test.py']),
            0
        ],
        [
            '*.P*',
            ['Test.py', 'Test.rb', 'Test.PL'],
            (['Test.py', 'Test.PL'] if not util.is_case_sensitive() else ['Test.PL']),
            0
        ],
        [
            'usr/*',
            ['usr/bin', 'usr', 'usr\\lib'],
            (['usr\\bin', 'usr\\lib'] if not util.is_case_sensitive() else ['usr/bin']),
            0
        ],
        [
            r'usr\\*',
            ['usr/bin', 'usr', 'usr\\lib'],
            (['usr\\bin', 'usr\\lib'] if not util.is_case_sensitive() else ['usr\\lib']),
            0
        ],
        [r'te\st[ma]', ['testm', 'test\\3', 'testa'], ['testm', 'testa'], fnmatch.I],
        [r'te\st[ma]', ['testm', 'test\\3', 'testa'], ['testm', 'testa'], fnmatch.F],

        # Issue #24
        ['*.bar', ["goo.cfg", "foo.bar", "foo.bar.cfg", "foo.cfg.bar"], ["foo.bar", "foo.cfg.bar"], 0],
        ['!*.bar', ["goo.cfg", "foo.bar", "foo.bar.cfg", "foo.cfg.bar"], ["goo.cfg", "foo.bar.cfg"], fnmatch.N]
    ]

    @classmethod
    def setup_class(cls):
        """Setup the tests."""

        cls.flags = fnmatch.DOTMATCH

    @staticmethod
    def assert_equal(a, b):
        """Assert equal."""

        assert a == b, "Comparison between objects yielded False."

    @classmethod
    def evaluate(cls, case):
        """Evaluate matches."""

        flags = case[3]
        flags = cls.flags ^ flags
        print("PATTERN: ", case[0])
        print("FILES: ", case[1])
        print("FLAGS: ", bin(flags))
        value = fnmatch.filter(case[1], case[0], flags=flags)
        print("TEST: ", value, '<=>', case[2], '\n')
        cls.assert_equal(value, case[2])

    @pytest.mark.parametrize("case", cases)
    def test_cases(self, case):
        """Test case."""

        self.evaluate(case)


class TestFnMatchTranslate(unittest.TestCase):
    """
    Test translation cases.

    All these cases assume `DOTMATCH` is enabled.
    """

    def setUp(self):
        """Setup the tests."""

        self.flags = fnmatch.DOTMATCH

    def split_translate(self, pattern, flags):
        """Translate pattern to regex after splitting."""

        return fnmatch.translate(fnmatch.fnsplit(pattern, flags=flags), flags=flags)

    @mock.patch('wcmatch.util.is_case_sensitive')
    def test_split_parsing(self, mock__iscase_sensitive):
        """Test wildcard parsing."""

        mock__iscase_sensitive.return_value = True

        _wcparse._compile.cache_clear()

        flags = self.flags
        p1, p2 = self.split_translate('*test[a-z]?|*test2[a-z]?|!test[!a-z]|!test[!-|a-z]', flags | fnmatch.N)
        if util.PY36:
            self.assertEqual(p1, [r'^(?s:(?=.).*?test[a-z].)$', r'^(?s:(?=.).*?test2[a-z].)$'])
            self.assertEqual(p2, [r'^(?!(?s:test[^a-z])$).*?$', r'^(?!(?s:test[^\-\|a-z])$).*?$'])
        else:
            self.assertEqual(p1, [r'(?s)^(?:(?=.).*?test[a-z].)$', r'(?s)^(?:(?=.).*?test2[a-z].)$'])
            self.assertEqual(p2, [r'(?s)^(?!(?:test[^a-z])$).*?$', r'(?s)^(?!(?:test[^\-\|a-z])$).*?$'])

        p1, p2 = self.split_translate('test[]][!][][]', flags | fnmatch.F)
        if util.PY36:
            self.assertEqual(p1, [r'^(?s:test[\]][^\][]\[\])$'])
            self.assertEqual(p2, [])
        else:
            self.assertEqual(p1, [r'(?s)^(?:test[\]][^\][]\[\])$'])
            self.assertEqual(p2, [])

        p1, p2 = self.split_translate('test[!]', flags)
        if util.PY37:
            self.assertEqual(p1, [r'^(?s:test\[!\])$'])
            self.assertEqual(p2, [])
        elif util.PY36:
            self.assertEqual(p1, [r'^(?s:test\[\!\])$'])
            self.assertEqual(p2, [])
        else:
            self.assertEqual(p1, [r'(?s)^(?:test\[\!\])$'])
            self.assertEqual(p2, [])

        p1, p2 = self.split_translate('|test|', flags)
        if util.PY36:
            self.assertEqual(p1, [r'^(?s:)$', r'^(?s:test)$', r'^(?s:)$'])
            self.assertEqual(p2, [])
        else:
            self.assertEqual(p1, [r'(?s)^(?:)$', r'(?s)^(?:test)$', r'(?s)^(?:)$'])
            self.assertEqual(p2, [])

        p1, p2 = self.split_translate('-|-test|-', flags=flags | fnmatch.N | fnmatch.M)
        if util.PY36:
            self.assertEqual(p1, [])
            self.assertEqual(p2, [r'^(?!(?s:)$).*?$', r'^(?!(?s:test)$).*?$', r'^(?!(?s:)$).*?$'])
        else:
            self.assertEqual(p1, [])
            self.assertEqual(p2, [r'(?s)^(?!(?:)$).*?$', r'(?s)^(?!(?:test)$).*?$', r'(?s)^(?!(?:)$).*?$'])

        p1, p2 = self.split_translate('test[^chars]', flags)
        if util.PY36:
            self.assertEqual(p1, [r'^(?s:test[^chars])$'])
            self.assertEqual(p2, [])
        else:
            self.assertEqual(p1, [r'(?s)^(?:test[^chars])$'])
            self.assertEqual(p2, [])

        p1 = self.split_translate(r'test[^\\-\\&]', flags=flags)[0]
        if util.PY36:
            self.assertEqual(p1, [r'^(?s:test[^\\-\\\&])$'])
        else:
            self.assertEqual(p1, [r'(?s)^(?:test[^\\-\\\&])$'])

        p1 = self.split_translate(r'\\*\\?\\|\\[\\]', flags=flags)[0]
        if util.PY36:
            self.assertEqual(p1, [r'^(?s:\\.*?\\.\\)$', r'^(?s:\\[\\])$'])
        else:
            self.assertEqual(p1, [r'(?s)^(?:\\.*?\\.\\)$', r'(?s)^(?:\\[\\])$'])

        p1 = self.split_translate(r'\\u0300', flags=flags | fnmatch.R)[0]
        if util.PY36:
            self.assertEqual(p1, [r'^(?s:\\u0300)$'])
        else:
            self.assertEqual(p1, [r'(?s)^(?:\\u0300)$'])

    def test_posix_range(self):
        """Test posix range."""

        p = fnmatch.translate(r'[[:ascii:]-z]', flags=self.flags | fnmatch.F)
        if util.PY36:
            self.assertEqual(p, (['^(?s:[\x00-\x7f\\-z])$'], []))
        else:
            self.assertEqual(p, (['(?s)^(?:[\x00-\x7f\\-z])$'], []))

        p = fnmatch.translate(r'[a-[:ascii:]-z]', flags=self.flags | fnmatch.F)
        if util.PY36:
            self.assertEqual(p, (['^(?s:[a\\-\x00-\x7f\\-z])$'], []))
        else:
            self.assertEqual(p, (['(?s)^(?:[a\\-\x00-\x7f\\-z])$'], []))

    @mock.patch('wcmatch.util.is_case_sensitive')
    def test_special_escapes(self, mock__iscase_sensitive):
        """Test wildcard character notations."""

        mock__iscase_sensitive.return_value = True

        _wcparse._compile.cache_clear()

        p1, p2 = fnmatch.translate(
            r'test\x70\u0070\U00000070\160\N{LATIN SMALL LETTER P}', flags=self.flags | fnmatch.R
        )
        if util.PY36:
            self.assertEqual(p1, [r'^(?s:testppppp)$'])
            self.assertEqual(p2, [])
        else:
            self.assertEqual(p1, [r'(?s)^(?:testppppp)$'])
            self.assertEqual(p2, [])

        p1, p2 = fnmatch.translate(
            r'test[\x70][\u0070][\U00000070][\160][\N{LATIN SMALL LETTER P}]', flags=self.flags | fnmatch.R
        )
        if util.PY36:
            self.assertEqual(p1, [r'^(?s:test[p][p][p][p][p])$'])
            self.assertEqual(p2, [])
        else:
            self.assertEqual(p1, [r'(?s)^(?:test[p][p][p][p][p])$'])
            self.assertEqual(p2, [])

        p1, p2 = fnmatch.translate(r'test\t\m', flags=self.flags | fnmatch.R)
        if util.PY36:
            self.assertEqual(p1, [r'^(?s:test\	m)$'])
            self.assertEqual(p2, [])
        else:
            self.assertEqual(p1, [r'(?s)^(?:test\	m)$'])
            self.assertEqual(p2, [])

        p1, p2 = fnmatch.translate(r'test[\\]test', flags=self.flags | fnmatch.R)
        if util.PY36:
            self.assertEqual(p1, [r'^(?s:test[\\]test)$'])
            self.assertEqual(p2, [])
        else:
            self.assertEqual(p1, [r'(?s)^(?:test[\\]test)$'])
            self.assertEqual(p2, [])

        p1, p2 = fnmatch.translate('test[\\', flags=self.flags)
        if util.PY36:
            self.assertEqual(p1, [r'^(?s:test\[\\)$'])
            self.assertEqual(p2, [])
        else:
            self.assertEqual(p1, [r'(?s)^(?:test\[\\)$'])
            self.assertEqual(p2, [])

        p1, p2 = fnmatch.translate(r'test\44test', flags=self.flags | fnmatch.R)
        if util.PY36:
            self.assertEqual(p1, [r'^(?s:test\$test)$'])
            self.assertEqual(p2, [])
        else:
            self.assertEqual(p1, [r'(?s)^(?:test\$test)$'])
            self.assertEqual(p2, [])

        p1, p2 = fnmatch.translate(r'test\44', flags=self.flags | fnmatch.R)
        if util.PY36:
            self.assertEqual(p1, [r'^(?s:test\$)$'])
            self.assertEqual(p2, [])
        else:
            self.assertEqual(p1, [r'(?s)^(?:test\$)$'])
            self.assertEqual(p2, [])

        p1, p2 = fnmatch.translate(r'test\400', flags=self.flags | fnmatch.R)
        if util.PY37:
            self.assertEqual(p1, [r'^(?s:testĀ)$'])
            self.assertEqual(p2, [])
        elif util.PY36:
            self.assertEqual(p1, [r'^(?s:test\Ā)$'])
            self.assertEqual(p2, [])
        else:
            self.assertEqual(p1, [r'(?s)^(?:test\Ā)$'])
            self.assertEqual(p2, [])

        with pytest.raises(SyntaxError):
            fnmatch.translate(r'test\N', flags=self.flags | fnmatch.R)

        with pytest.raises(SyntaxError):
            fnmatch.translate(r'test\Nx', flags=self.flags | fnmatch.R)

        with pytest.raises(SyntaxError):
            fnmatch.translate(r'test\N{', flags=self.flags | fnmatch.R)
