# -*- coding: utf-8 -*-
"""Tests for `fnmatch`."""
import unittest
import re
import pytest
import wcmatch.fnmatch as fnmatch
from unittest import mock
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

        # Case: General
        ['abc', 'abc', True, fnmatch.C],
        ['abc', 'AbC', False, fnmatch.C],
        ['AbC', 'abc', False, fnmatch.C],
        ['AbC', 'AbC', True, fnmatch.C],

        # Case and Force Unix: slash conventions
        ['usr/bin', 'usr/bin', True, fnmatch.C | fnmatch.U],
        ['usr/bin', 'usr\\bin', False, fnmatch.C | fnmatch.U],
        [r'usr\\bin', 'usr/bin', False, fnmatch.C | fnmatch.U],
        [r'usr\\bin', 'usr\\bin', True, fnmatch.C | fnmatch.U],

        # Case and Force Windows: slash conventions
        ['usr/bin', 'usr/bin', True, fnmatch.C | fnmatch.W],
        ['usr/bin', 'usr\\bin', True, fnmatch.C | fnmatch.W],
        [r'usr\\bin', 'usr/bin', True, fnmatch.C | fnmatch.W],
        [r'usr\\bin', 'usr\\bin', True, fnmatch.C | fnmatch.W],

        # Wildcard tests
        [b'te*', b'test', True, 0],
        [b'te*\xff', b'test\xff', True, 0],
        [b'foo*', b'foo\nbar', True, 0],

        # OS specific case behavior
        ['abc', 'abc', True, 0],
        ['abc', 'AbC', not util.is_case_sensitive(), 0],
        ['AbC', 'abc', not util.is_case_sensitive(), 0],
        ['AbC', 'AbC', True, 0],
        ['abc', 'AbC', True, fnmatch.W],
        ['abc', 'AbC', False, fnmatch.U],
        ['abc', 'AbC', True, fnmatch.U | fnmatch.I],
        ['AbC', 'abc', not util.is_case_sensitive(), fnmatch.W | fnmatch.U],  # Can't force both, just detect system

        # OS specific slash behavior
        ['usr/bin', 'usr/bin', True, 0],
        ['usr/bin', 'usr\\bin', not util.is_case_sensitive(), 0],
        [r'usr\\bin', 'usr/bin', not util.is_case_sensitive(), 0],
        [r'usr\\bin', 'usr\\bin', True, 0],
        ['usr/bin', 'usr\\bin', True, fnmatch.W],
        [r'usr\\bin', 'usr/bin', True, fnmatch.W],
        ['usr/bin', 'usr\\bin', False, fnmatch.U],
        [r'usr\\bin', 'usr/bin', False, fnmatch.U],

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
        ['!(test)', '..', True, fnmatch.E],

        # Turn off `dotmatch` cases
        ['.abc', '.abc', True, fnmatch.D],
        [r'\.abc', '.abc', True, fnmatch.D],
        ['?abc', '.abc', False, fnmatch.D],
        ['*abc', '.abc', False, fnmatch.D],
        ['[.]abc', '.abc', False, fnmatch.D],
        ['*(.)abc', '.abc', True, fnmatch.E | fnmatch.D],
        [r'*(\.)abc', '.abc', True, fnmatch.E | fnmatch.D],
        ['*(?)abc', '.abc', False, fnmatch.E | fnmatch.D],
        ['*(?|.)abc', '.abc', True, fnmatch.E | fnmatch.D],
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
        ['!(test)', '..', False, fnmatch.D | fnmatch.E],

        # POSIX style character classes
        ['[[:alnum:]]bc', 'zbc', True, 0],
        ['[[:alnum:]]bc', '1bc', True, 0],
        ['[a[:alnum:]]bc', 'zbc', True, 0],
        ['[[:alnum:][:blank:]]bc', ' bc', True, 0],
        ['*([[:word:]])', 'WoRD5_', True, fnmatch.E],

        [b'[[:alnum:]]bc', b'zbc', True, 0],
        [b'[[:alnum:]]bc', b'1bc', True, 0],
        [b'[a[:alnum:]]bc', b'zbc', True, 0],
        [b'[[:alnum:][:blank:]]bc', b' bc', True, 0],
        [b'*([[:word:]])', b'WoRD5_', True, fnmatch.E],

        # POSIX character classes are case sensitive
        ['[[:ALNUM:]]bc', 'zbc', False, 0],
        ['[[:AlNuM:]]bc', '1bc', False, 0],

        # We can't use a character class as a range.
        ['[-[:alnum:]]bc', '-bc', True, 0],
        ['[a-[:alnum:]]bc', '-bc', True, 0],
        ['[[:alnum:]-z]bc', '-bc', True, 0],

        # Negation
        ['[![:alnum:]]bc', '!bc', True, 0],
        ['[^[:alnum:]]bc', '!bc', True, 0],

        # Negation and extended glob together
        # `!` will be treated as an exclude pattern if it isn't followed by `(`.
        # `(` must be escaped to exclude a name that starts with `(`.
        # If `!(` doesn't start a valid extended glob pattern,
        # it will be treated as a literal, not an exclude pattern.
        [r'!\(test)', 'test', True, fnmatch.N | fnmatch.E | fnmatch.A],
        [r'!(test)', 'test', False, fnmatch.N | fnmatch.E | fnmatch.A],
        [r'!!(test)', 'test', True, fnmatch.N | fnmatch.E | fnmatch.A],
        [r'!(test', '!(test', True, fnmatch.N | fnmatch.E | fnmatch.A],

        # Backwards ranges
        ['[a-z]', 'a', True, 0],
        ['[z-a]', 'a', False, 0],
        ['[!z-a]', 'a', True, 0],
        ['[!a-z]', 'a', False, 0],
        ['[9--]', '9', False, 0],

        # Escaped slashes are just slashes as they aren't treated special beyond normalization.
        [r'a\/b', ('a/b' if util.is_case_sensitive() else 'a\\\\b'), True, 0],
        [r'a\/b', 'a/b', True, fnmatch.U],
        [r'a\/b', 'a\\\\b', True, fnmatch.W]
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
            fnmatch.fnmatch(case[1], case[0], flags=flags | fnmatch.SPLIT), case[2]
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
            (['usr/bin', 'usr\\lib'] if not util.is_case_sensitive() else ['usr/bin']),
            0
        ],
        [
            r'usr\\*',
            ['usr/bin', 'usr', 'usr\\lib'],
            (['usr/bin', 'usr\\lib'] if not util.is_case_sensitive() else ['usr\\lib']),
            0
        ],
        [r'te\st[ma]', ['testm', 'test\\3', 'testa'], ['testm', 'testa'], fnmatch.I],
        [r'te\st[ma]', ['testm', 'test\\3', 'testa'], ['testm', 'testa'], fnmatch.C],

        # Issue #24
        ['*.bar', ["goo.cfg", "foo.bar", "foo.bar.cfg", "foo.cfg.bar"], ["foo.bar", "foo.cfg.bar"], 0],
        [
            '*|!*.bar',
            ["goo.cfg", "foo.bar", "foo.bar.cfg", "foo.cfg.bar"],
            ["goo.cfg", "foo.bar.cfg"],
            fnmatch.N | fnmatch.S
        ]
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

        return fnmatch.translate(pattern, flags=flags | fnmatch.SPLIT)

    def test_capture_groups(self):
        """Test capture groups."""

        gpat = fnmatch.translate("test @(this) +(many) ?(meh)*(!) !(not this)@(.md)", flags=fnmatch.E)
        pat = re.compile(gpat[0][0])
        match = pat.match('test this manymanymany meh!!!!! okay.md')
        self.assertEqual(('this', 'manymanymany', 'meh', '!!!!!', 'okay', '.md'), match.groups())

    def test_nested_capture_groups(self):
        """Test nested capture groups."""

        gpat = fnmatch.translate("@(file)@(+([[:digit:]]))@(.*)", flags=fnmatch.E)
        pat = re.compile(gpat[0][0])
        match = pat.match('file33.test.txt')
        self.assertEqual(('file', '33', '33', '.test.txt'), match.groups())

    def test_list_groups(self):
        """Test capture groups with lists."""

        gpat = fnmatch.translate("+(f|i|l|e)+([[:digit:]])@(.*)", flags=fnmatch.E)
        pat = re.compile(gpat[0][0])
        match = pat.match('file33.test.txt')
        self.assertEqual(('file', '33', '.test.txt'), match.groups())

    def test_split_parsing(self):
        """Test wildcard parsing."""

        _wcparse._compile.cache_clear()

        flags = self.flags | fnmatch.FORCEUNIX

        p1, p2 = self.split_translate('*test[a-z]?|*test2[a-z]?|!test[!a-z]|!test[!-|a-z]', flags | fnmatch.N)
        self.assertEqual(p1, [r'^(?s:(?=.).*?test[a-z].)$', r'^(?s:(?=.).*?test2[a-z].)$'])
        self.assertEqual(p2, [r'^(?s:test[^a-z])$', r'^(?s:test[^\-\|a-z])$'])

        p1, p2 = self.split_translate('test[]][!][][]', flags | fnmatch.U | fnmatch.C)
        self.assertEqual(p1, [r'^(?s:test[\]][^\][]\[\])$'])
        self.assertEqual(p2, [])

        p1, p2 = self.split_translate('test[!]', flags)
        if util.PY37:
            self.assertEqual(p1, [r'^(?s:test\[!\])$'])
            self.assertEqual(p2, [])
        else:
            self.assertEqual(p1, [r'^(?s:test\[\!\])$'])
            self.assertEqual(p2, [])

        p1, p2 = self.split_translate('|test|', flags)
        self.assertEqual(p1, [r'^(?s:)$', r'^(?s:test)$'])
        self.assertEqual(p2, [])

        p1, p2 = self.split_translate('-|-test|-', flags=flags | fnmatch.N | fnmatch.M)
        self.assertEqual(p1, [])
        self.assertEqual(p2, [r'^(?s:)$', r'^(?s:test)$'])

        p1, p2 = self.split_translate('test[^chars]', flags)
        self.assertEqual(p1, [r'^(?s:test[^chars])$'])
        self.assertEqual(p2, [])

        p1 = self.split_translate(r'test[^\\-\\&]', flags=flags)[0]
        self.assertEqual(p1, [r'^(?s:test[^\\-\\\&])$'])

        p1 = self.split_translate(r'\\*\\?\\|\\[\\]', flags=flags)[0]
        self.assertEqual(p1, [r'^(?s:\\.*?\\.\\)$', r'^(?s:\\[\\])$'])

        p1 = self.split_translate(r'\\u0300', flags=flags | fnmatch.R)[0]
        self.assertEqual(p1, [r'^(?s:\\u0300)$'])

    def test_posix_range(self):
        """Test posix range."""

        p = fnmatch.translate(r'[[:ascii:]-z]', flags=self.flags | fnmatch.U | fnmatch.C)
        self.assertEqual(p, (['^(?s:[\x00-\x7f\\-z])$'], []))

        p = fnmatch.translate(r'[a-[:ascii:]-z]', flags=self.flags | fnmatch.U | fnmatch.C)
        self.assertEqual(p, (['^(?s:[a\\-\x00-\x7f\\-z])$'], []))

    @mock.patch('wcmatch.util.is_case_sensitive')
    def test_special_escapes(self, mock__iscase_sensitive):
        """Test wildcard character notations."""

        flags = self.flags | fnmatch.U

        _wcparse._compile.cache_clear()

        p1, p2 = fnmatch.translate(
            r'test\x70\u0070\U00000070\160\N{LATIN SMALL LETTER P}', flags=flags | fnmatch.R
        )
        self.assertEqual(p1, [r'^(?s:testppppp)$'])
        self.assertEqual(p2, [])

        p1, p2 = fnmatch.translate(
            r'test[\x70][\u0070][\U00000070][\160][\N{LATIN SMALL LETTER P}]', flags=flags | fnmatch.R
        )
        self.assertEqual(p1, [r'^(?s:test[p][p][p][p][p])$'])
        self.assertEqual(p2, [])

        p1, p2 = fnmatch.translate(r'test\t\m', flags=flags | fnmatch.R)
        self.assertEqual(p1, [r'^(?s:test\	m)$'])
        self.assertEqual(p2, [])

        p1, p2 = fnmatch.translate(r'test[\\]test', flags=flags | fnmatch.R)
        self.assertEqual(p1, [r'^(?s:test[\\]test)$'])
        self.assertEqual(p2, [])

        p1, p2 = fnmatch.translate('test[\\', flags=flags)
        self.assertEqual(p1, [r'^(?s:test\[\\)$'])
        self.assertEqual(p2, [])

        p1, p2 = fnmatch.translate(r'test\44test', flags=flags | fnmatch.R)
        self.assertEqual(p1, [r'^(?s:test\$test)$'])
        self.assertEqual(p2, [])

        p1, p2 = fnmatch.translate(r'test\44', flags=flags | fnmatch.R)
        self.assertEqual(p1, [r'^(?s:test\$)$'])
        self.assertEqual(p2, [])

        p1, p2 = fnmatch.translate(r'test\400', flags=flags | fnmatch.R)
        if util.PY37:
            self.assertEqual(p1, [r'^(?s:testĀ)$'])
            self.assertEqual(p2, [])
        else:
            self.assertEqual(p1, [r'^(?s:test\Ā)$'])
            self.assertEqual(p2, [])

        with pytest.raises(SyntaxError):
            fnmatch.translate(r'test\N', flags=flags | fnmatch.R)

        with pytest.raises(SyntaxError):
            fnmatch.translate(r'test\Nx', flags=flags | fnmatch.R)

        with pytest.raises(SyntaxError):
            fnmatch.translate(r'test\N{', flags=flags | fnmatch.R)

    def test_default_compile(self):
        """Test default with exclusion."""

        self.assertTrue(fnmatch.fnmatch('name', '!test', flags=fnmatch.N | fnmatch.A))
        self.assertTrue(fnmatch.fnmatch(b'name', b'!test', flags=fnmatch.N | fnmatch.A))

    def test_default_translate(self):
        """Test default with exclusion in translation."""

        self.assertTrue(len(fnmatch.translate('!test', flags=fnmatch.N | fnmatch.A)[0]) == 1)
        self.assertTrue(len(fnmatch.translate(b'!test', flags=fnmatch.N | fnmatch.A)[0]) == 1)


class TestExpansionLimit(unittest.TestCase):
    """Test expansion limits."""

    def test_limit_fnmatch(self):
        """Test expansion limit of `fnmatch`."""

        with self.assertRaises(_wcparse.PatternLimitException):
            fnmatch.fnmatch('name', '{1..11}', flags=fnmatch.BRACE, limit=10)

    def test_limit_filter(self):
        """Test expansion limit of `filter`."""

        with self.assertRaises(_wcparse.PatternLimitException):
            fnmatch.filter(['name'], '{1..11}', flags=fnmatch.BRACE, limit=10)

    def test_limit_translate(self):
        """Test expansion limit of `translate`."""

        with self.assertRaises(_wcparse.PatternLimitException):
            fnmatch.translate('{1..11}', flags=fnmatch.BRACE, limit=10)
