# -*- coding: utf-8 -*-
"""Tests for `fnmatch`."""
import unittest
import re
import sys
import os
import pytest
import copy
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
        [R'[\]', '\\', False, 0],
        [R'[!\]', 'a', False, 0],
        [R'[!\]', '\\', False, 0],
        [R'[\\]', '\\', True, 0],
        [R'[!\\]', 'a', True, 0],
        [R'[!\\]', '\\', False, 0],

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
        [R'usr\\bin', 'usr/bin', False, fnmatch.C | fnmatch.U],
        [R'usr\\bin', 'usr\\bin', True, fnmatch.C | fnmatch.U],

        # Case and Force Windows: slash conventions
        ['usr/bin', 'usr/bin', True, fnmatch.C | fnmatch.W],
        ['usr/bin', 'usr\\bin', True, fnmatch.C | fnmatch.W],
        [R'usr\\bin', 'usr/bin', True, fnmatch.C | fnmatch.W],
        [R'usr\\bin', 'usr\\bin', True, fnmatch.C | fnmatch.W],

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
        [R'usr\\bin', 'usr/bin', not util.is_case_sensitive(), 0],
        [R'usr\\bin', 'usr\\bin', True, 0],
        ['usr/bin', 'usr\\bin', True, fnmatch.W],
        [R'usr\\bin', 'usr/bin', True, fnmatch.W],
        ['usr/bin', 'usr\\bin', False, fnmatch.U],
        [R'usr\\bin', 'usr/bin', False, fnmatch.U],

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
        [R'\.abc', '.abc', True, 0],
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
        [R'\.abc', '.abc', True, fnmatch.D],
        ['?abc', '.abc', False, fnmatch.D],
        ['*abc', '.abc', False, fnmatch.D],
        ['[.]abc', '.abc', False, fnmatch.D],
        ['*(.)abc', '.abc', True, fnmatch.E | fnmatch.D],
        [R'*(\.)abc', '.abc', True, fnmatch.E | fnmatch.D],
        ['*(?)abc', '.abc', False, fnmatch.E | fnmatch.D],
        ['*(?|.)abc', '.abc', True, fnmatch.E | fnmatch.D],
        ['*(?|*)abc', '.abc', False, fnmatch.E | fnmatch.D],
        ['a.bc', 'a.bc', True, fnmatch.D],
        ['a?bc', 'a.bc', True, fnmatch.D],
        ['a*bc', 'a.bc', True, fnmatch.D],
        ['a[.]bc', 'a.bc', True, fnmatch.D],
        ['a*(.)bc', 'a.bc', True, fnmatch.E | fnmatch.D],
        [R'a*(\.)bc', 'a.bc', True, fnmatch.E | fnmatch.D],
        ['a*(?)bc', 'a.bc', True, fnmatch.E | fnmatch.D],
        ['a*(?|.)bc', 'a.bc', True, fnmatch.E | fnmatch.D],
        ['a*(?|*)bc', 'a.bc', True, fnmatch.E | fnmatch.D],
        ['!(test)', '.abc', False, fnmatch.D | fnmatch.E],
        ['!(test)', 'abc', True, fnmatch.D | fnmatch.E],
        ['!(test)', '..', False, fnmatch.D | fnmatch.E],

        # Negation list followed by extended list
        ['!(2)_@(foo|bar)', '1_foo', True, fnmatch.E],
        ['!(!(2|3))_@(foo|bar)', '2_foo', True, fnmatch.E],

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
        [R'!\(test)', 'test', True, fnmatch.N | fnmatch.E | fnmatch.A],
        [R'!(test)', 'test', False, fnmatch.N | fnmatch.E | fnmatch.A],
        [R'!!(test)', 'test', True, fnmatch.N | fnmatch.E | fnmatch.A],
        [R'!(test', '!(test', True, fnmatch.N | fnmatch.E | fnmatch.A],

        # Backwards ranges
        ['[a-z]', 'a', True, 0],
        ['[z-a]', 'a', False, 0],
        ['[!z-a]', 'a', True, 0],
        ['[!a-z]', 'a', False, 0],
        ['[9--]', '9', False, 0],

        # Escaped slashes are just slashes as they aren't treated special beyond normalization.
        [R'a\/b', ('a/b' if util.is_case_sensitive() else 'a\\\\b'), True, 0],
        [R'a\/b', 'a/b', True, fnmatch.U],
        [R'a\/b', 'a\\\\b', True, fnmatch.W]
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
            R'usr\\*',
            ['usr/bin', 'usr', 'usr\\lib'],
            (['usr/bin', 'usr\\lib'] if not util.is_case_sensitive() else ['usr\\lib']),
            0
        ],
        [R'te\st[ma]', ['testm', 'test\\3', 'testa'], ['testm', 'testa'], fnmatch.I],
        [R'te\st[ma]', ['testm', 'test\\3', 'testa'], ['testm', 'testa'], fnmatch.C],

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
        self.assertEqual(p1, [r'^(?s:test\[!\])$'])
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

        p1 = self.split_translate(R'test[^\\-\\&]', flags=flags)[0]
        self.assertEqual(p1, [r'^(?s:test[^\\-\\\&])$'])

        p1 = self.split_translate(R'\\*\\?\\|\\[\\]', flags=flags)[0]
        self.assertEqual(p1, [r'^(?s:\\.*?\\.\\)$', r'^(?s:\\[\\])$'])

        p1 = self.split_translate(R'\\u0300', flags=flags | fnmatch.R)[0]
        self.assertEqual(p1, [r'^(?s:\\u0300)$'])

    def test_posix_range(self):
        """Test posix range."""

        p = fnmatch.translate(R'[[:ascii:]-z]', flags=self.flags | fnmatch.U | fnmatch.C)
        self.assertEqual(p, (['^(?s:[\x00-\x7f\\-z])$'], []))

        p = fnmatch.translate(R'[a-[:ascii:]-z]', flags=self.flags | fnmatch.U | fnmatch.C)
        self.assertEqual(p, (['^(?s:[a\\-\x00-\x7f\\-z])$'], []))

    @mock.patch('wcmatch.util.is_case_sensitive')
    def test_special_escapes(self, mock__iscase_sensitive):
        """Test wildcard character notations."""

        flags = self.flags | fnmatch.U

        _wcparse._compile.cache_clear()

        p1, p2 = fnmatch.translate(
            R'test\x70\u0070\U00000070\160\N{LATIN SMALL LETTER P}', flags=flags | fnmatch.R
        )
        self.assertEqual(p1, [r'^(?s:testppppp)$'])
        self.assertEqual(p2, [])

        p1, p2 = fnmatch.translate(
            R'test[\x70][\u0070][\U00000070][\160][\N{LATIN SMALL LETTER P}]', flags=flags | fnmatch.R
        )
        self.assertEqual(p1, [r'^(?s:test[p][p][p][p][p])$'])
        self.assertEqual(p2, [])

        p1, p2 = fnmatch.translate(R'test\t\m', flags=flags | fnmatch.R)
        self.assertEqual(p1, [r'^(?s:test\	m)$'])
        self.assertEqual(p2, [])

        p1, p2 = fnmatch.translate(R'test[\\]test', flags=flags | fnmatch.R)
        self.assertEqual(p1, [r'^(?s:test[\\]test)$'])
        self.assertEqual(p2, [])

        p1, p2 = fnmatch.translate('test[\\', flags=flags)
        self.assertEqual(p1, [r'^(?s:test\[)$'])
        self.assertEqual(p2, [])

        p1, p2 = fnmatch.translate(R'test\44test', flags=flags | fnmatch.R)
        self.assertEqual(p1, [r'^(?s:test\$test)$'])
        self.assertEqual(p2, [])

        p1, p2 = fnmatch.translate(R'test\44', flags=flags | fnmatch.R)
        self.assertEqual(p1, [r'^(?s:test\$)$'])
        self.assertEqual(p2, [])

        p1, p2 = fnmatch.translate(R'test\400', flags=flags | fnmatch.R)
        self.assertEqual(p1, [r'^(?s:testĀ)$'])
        self.assertEqual(p2, [])

        with pytest.raises(SyntaxError):
            fnmatch.translate(R'test\N', flags=flags | fnmatch.R)

        with pytest.raises(SyntaxError):
            fnmatch.translate(R'test\Nx', flags=flags | fnmatch.R)

        with pytest.raises(SyntaxError):
            fnmatch.translate(R'test\N{', flags=flags | fnmatch.R)

    def test_default_compile(self):
        """Test default with exclusion."""

        self.assertTrue(fnmatch.fnmatch('name', '!test', flags=fnmatch.N | fnmatch.A))
        self.assertTrue(fnmatch.fnmatch(b'name', b'!test', flags=fnmatch.N | fnmatch.A))
        self.assertFalse(fnmatch.fnmatch('test', '!test', flags=fnmatch.N | fnmatch.A))
        self.assertFalse(fnmatch.fnmatch(b'test', b'!test', flags=fnmatch.N | fnmatch.A))

    def test_default_translate(self):
        """Test default with exclusion in translation."""

        self.assertTrue(len(fnmatch.translate('!test', flags=fnmatch.N | fnmatch.A)[0]) == 1)
        self.assertTrue(len(fnmatch.translate(b'!test', flags=fnmatch.N | fnmatch.A)[0]) == 1)


class TestExcludes(unittest.TestCase):
    """Test expansion limits."""

    def test_translate_exclude(self):
        """Test exclusion in translation."""

        results = fnmatch.translate('*', exclude='test')
        self.assertTrue(len(results[0]) == 1 and len(results[1]) == 1)
        results = fnmatch.translate(b'*', exclude=b'test')
        self.assertTrue(len(results[0]) == 1 and len(results[1]) == 1)

    def test_translate_exclude_mix(self):
        """
        Test translate exclude mix.

        If both are given, flags are ignored.
        """

        results = fnmatch.translate(['*', '!test'], exclude=b'test', flags=fnmatch.N | fnmatch.A)
        self.assertTrue(len(results[0]) == 2 and len(results[1]) == 1)

    def test_exclude(self):
        """Test exclude parameter."""

        self.assertTrue(fnmatch.fnmatch('name', '*', exclude='test'))
        self.assertTrue(fnmatch.fnmatch(b'name', b'*', exclude=b'test'))
        self.assertFalse(fnmatch.fnmatch('test', '*', exclude='test'))
        self.assertFalse(fnmatch.fnmatch(b'test', b'*', exclude=b'test'))

    def test_exclude_mix(self):
        """
        Test exclusion flags mixed with exclusion parameter.

        If both are given, flags are ignored.
        """

        self.assertTrue(fnmatch.fnmatch('name', '*', exclude='test', flags=fnmatch.N | fnmatch.A))
        self.assertTrue(fnmatch.fnmatch(b'name', b'*', exclude=b'test', flags=fnmatch.N | fnmatch.A))
        self.assertFalse(fnmatch.fnmatch('test', '*', exclude='test', flags=fnmatch.N | fnmatch.A))
        self.assertFalse(fnmatch.fnmatch(b'test', b'*', exclude=b'test', flags=fnmatch.N | fnmatch.A))

        self.assertTrue(fnmatch.fnmatch('name', ['*', '!name'], exclude='test', flags=fnmatch.N | fnmatch.A))
        self.assertFalse(fnmatch.fnmatch('test', ['*', '!name'], exclude='test', flags=fnmatch.N | fnmatch.A))
        self.assertTrue(fnmatch.fnmatch('!name', ['*', '!name'], exclude='test', flags=fnmatch.N | fnmatch.A))

    def test_filter(self):
        """Test exclusion with filter."""

        self.assertEqual(fnmatch.filter(['name', 'test'], '*', exclude='test'), ['name'])


class TestIsMagic(unittest.TestCase):
    """Test "is magic" logic."""

    def test_default(self):
        """Test default magic."""

        self.assertTrue(fnmatch.is_magic("test*"))
        self.assertTrue(fnmatch.is_magic("test["))
        self.assertTrue(fnmatch.is_magic("test]"))
        self.assertTrue(fnmatch.is_magic("test?"))
        self.assertTrue(fnmatch.is_magic("test\\"))

        self.assertFalse(fnmatch.is_magic("test~!()-/|{}"))

    def test_extmatch(self):
        """Test extended match magic."""

        self.assertTrue(fnmatch.is_magic("test*", flags=fnmatch.EXTMATCH))
        self.assertTrue(fnmatch.is_magic("test[", flags=fnmatch.EXTMATCH))
        self.assertTrue(fnmatch.is_magic("test]", flags=fnmatch.EXTMATCH))
        self.assertTrue(fnmatch.is_magic("test?", flags=fnmatch.EXTMATCH))
        self.assertTrue(fnmatch.is_magic("test\\", flags=fnmatch.EXTMATCH))
        self.assertTrue(fnmatch.is_magic("test(", flags=fnmatch.EXTMATCH))
        self.assertTrue(fnmatch.is_magic("test)", flags=fnmatch.EXTMATCH))

        self.assertFalse(fnmatch.is_magic("test~!-/|{}", flags=fnmatch.EXTMATCH))

    def test_negate(self):
        """Test negate magic."""

        self.assertTrue(fnmatch.is_magic("test*", flags=fnmatch.NEGATE))
        self.assertTrue(fnmatch.is_magic("test[", flags=fnmatch.NEGATE))
        self.assertTrue(fnmatch.is_magic("test]", flags=fnmatch.NEGATE))
        self.assertTrue(fnmatch.is_magic("test?", flags=fnmatch.NEGATE))
        self.assertTrue(fnmatch.is_magic("test\\", flags=fnmatch.NEGATE))
        self.assertTrue(fnmatch.is_magic("test!", flags=fnmatch.NEGATE))

        self.assertFalse(fnmatch.is_magic("test~()-/|{}", flags=fnmatch.NEGATE))

    def test_minusnegate(self):
        """Test minus negate magic."""

        self.assertTrue(fnmatch.is_magic("test*", flags=fnmatch.NEGATE | fnmatch.MINUSNEGATE))
        self.assertTrue(fnmatch.is_magic("test[", flags=fnmatch.NEGATE | fnmatch.MINUSNEGATE))
        self.assertTrue(fnmatch.is_magic("test]", flags=fnmatch.NEGATE | fnmatch.MINUSNEGATE))
        self.assertTrue(fnmatch.is_magic("test?", flags=fnmatch.NEGATE | fnmatch.MINUSNEGATE))
        self.assertTrue(fnmatch.is_magic("test\\", flags=fnmatch.NEGATE | fnmatch.MINUSNEGATE))
        self.assertTrue(fnmatch.is_magic("test-", flags=fnmatch.NEGATE | fnmatch.MINUSNEGATE))

        self.assertFalse(fnmatch.is_magic("test~()!/|{}", flags=fnmatch.NEGATE | fnmatch.MINUSNEGATE))

    def test_brace(self):
        """Test brace magic."""

        self.assertTrue(fnmatch.is_magic("test*", flags=fnmatch.BRACE))
        self.assertTrue(fnmatch.is_magic("test[", flags=fnmatch.BRACE))
        self.assertTrue(fnmatch.is_magic("test]", flags=fnmatch.BRACE))
        self.assertTrue(fnmatch.is_magic("test?", flags=fnmatch.BRACE))
        self.assertTrue(fnmatch.is_magic("test\\", flags=fnmatch.BRACE))
        self.assertTrue(fnmatch.is_magic("test{", flags=fnmatch.BRACE))
        self.assertTrue(fnmatch.is_magic("test}", flags=fnmatch.BRACE))

        self.assertFalse(fnmatch.is_magic("test~!-/|", flags=fnmatch.BRACE))

    def test_split(self):
        """Test split magic."""

        self.assertTrue(fnmatch.is_magic("test*", flags=fnmatch.SPLIT))
        self.assertTrue(fnmatch.is_magic("test[", flags=fnmatch.SPLIT))
        self.assertTrue(fnmatch.is_magic("test]", flags=fnmatch.SPLIT))
        self.assertTrue(fnmatch.is_magic("test?", flags=fnmatch.SPLIT))
        self.assertTrue(fnmatch.is_magic("test\\", flags=fnmatch.SPLIT))
        self.assertTrue(fnmatch.is_magic("test|", flags=fnmatch.SPLIT))

        self.assertFalse(fnmatch.is_magic("test~()-!/", flags=fnmatch.SPLIT))

    def test_all(self):
        """Test tilde magic."""

        flags = (
            fnmatch.EXTMATCH |
            fnmatch.NEGATE |
            fnmatch.BRACE |
            fnmatch.SPLIT
        )

        self.assertTrue(fnmatch.is_magic("test*", flags=flags))
        self.assertTrue(fnmatch.is_magic("test[", flags=flags))
        self.assertTrue(fnmatch.is_magic("test]", flags=flags))
        self.assertTrue(fnmatch.is_magic("test?", flags=flags))
        self.assertTrue(fnmatch.is_magic(R"te\\st", flags=flags))
        self.assertTrue(fnmatch.is_magic(R"te\st", flags=flags))
        self.assertTrue(fnmatch.is_magic("test!", flags=flags))
        self.assertTrue(fnmatch.is_magic("test|", flags=flags))
        self.assertTrue(fnmatch.is_magic("test(", flags=flags))
        self.assertTrue(fnmatch.is_magic("test)", flags=flags))
        self.assertTrue(fnmatch.is_magic("test{", flags=flags))
        self.assertTrue(fnmatch.is_magic("test}", flags=flags))
        self.assertTrue(fnmatch.is_magic("test-", flags=flags | fnmatch.MINUSNEGATE))

        self.assertFalse(fnmatch.is_magic("test-~", flags=flags))
        self.assertFalse(fnmatch.is_magic("test!~", flags=flags | fnmatch.MINUSNEGATE))

    def test_all_bytes(self):
        """Test tilde magic."""

        flags = (
            fnmatch.EXTMATCH |
            fnmatch.NEGATE |
            fnmatch.BRACE |
            fnmatch.SPLIT
        )

        self.assertTrue(fnmatch.is_magic(b"test*", flags=flags))
        self.assertTrue(fnmatch.is_magic(b"test[", flags=flags))
        self.assertTrue(fnmatch.is_magic(b"test]", flags=flags))
        self.assertTrue(fnmatch.is_magic(b"test?", flags=flags))
        self.assertTrue(fnmatch.is_magic(rb"te\\st", flags=flags))
        self.assertTrue(fnmatch.is_magic(rb"te\st", flags=flags))
        self.assertTrue(fnmatch.is_magic(b"test!", flags=flags))
        self.assertTrue(fnmatch.is_magic(b"test|", flags=flags))
        self.assertTrue(fnmatch.is_magic(b"test(", flags=flags))
        self.assertTrue(fnmatch.is_magic(b"test)", flags=flags))
        self.assertTrue(fnmatch.is_magic(b"test{", flags=flags))
        self.assertTrue(fnmatch.is_magic(b"test}", flags=flags))
        self.assertTrue(fnmatch.is_magic(b"test-", flags=flags | fnmatch.MINUSNEGATE))

        self.assertFalse(fnmatch.is_magic(b"test-~", flags=flags))
        self.assertFalse(fnmatch.is_magic(b"test!~", flags=flags | fnmatch.MINUSNEGATE))


class TestFnMatchEscapes(unittest.TestCase):
    """Test escaping."""

    def check_escape(self, arg, expected, unix=None, raw_chars=True):
        """Verify escapes."""

        flags = 0
        if unix is False:
            flags = fnmatch.FORCEWIN
        elif unix is True:
            flags = fnmatch.FORCEUNIX

        self.assertEqual(fnmatch.escape(arg), expected)
        self.assertEqual(fnmatch.escape(os.fsencode(arg)), os.fsencode(expected))
        self.assertTrue(
            fnmatch.fnmatch(
                arg,
                fnmatch.escape(arg),
                flags=flags
            )
        )

    def test_escape(self):
        """Test path escapes."""

        check = self.check_escape
        check('abc', 'abc')
        check('[', R'\[')
        check('?', R'\?')
        check('*', R'\*')
        check('[[_/*?*/_]]', R'\[\[_/\*\?\*/_\]\]')
        check('/[[_/*?*/_]]/', R'/\[\[_/\*\?\*/_\]\]/')

    @unittest.skipUnless(sys.platform.startswith('win'), "Windows specific test")
    def test_escape_windows(self):
        """Test windows escapes."""

        check = self.check_escape
        # `fnmatch` doesn't care about drives
        check('a:\\?', R'a:\\\?')
        check('b:\\*', R'b:\\\*')
        check('\\\\?\\c:\\?', R'\\\\\?\\c:\\\?')
        check('\\\\*\\*\\*', R'\\\\\*\\\*\\\*')
        check('//?/c:/?', R'//\?/c:/\?')
        check('//*/*/*', R'//\*/\*/\*')
        check('//[^what]/name/temp', R'//\[^what\]/name/temp')

    def test_escape_forced_windows(self):
        """Test forced windows escapes."""

        check = self.check_escape
        # `fnmatch` doesn't care about drives
        check('a:\\?', R'a:\\\?', unix=False)
        check('b:\\*', R'b:\\\*', unix=False)
        check('\\\\?\\c:\\?', R'\\\\\?\\c:\\\?', unix=True)
        check('\\\\*\\*\\*', R'\\\\\*\\\*\\\*', unix=True)
        check('//?/c:/?', R'//\?/c:/\?', unix=True)
        check('//*/*/*', R'//\*/\*/\*', unix=True)
        check('//[^what]/name/temp', R'//\[^what\]/name/temp', unix=True)

    def test_escape_forced_unix(self):
        """Test forced windows Unix."""

        check = self.check_escape
        # `fnmatch` doesn't care about drives
        check('a:\\?', R'a:\\\?', unix=True)
        check('b:\\*', R'b:\\\*', unix=True)
        check('\\\\?\\c:\\?', R'\\\\\?\\c:\\\?', unix=True)
        check('\\\\*\\*\\*', R'\\\\\*\\\*\\\*', unix=True)
        check('//?/c:/?', R'//\?/c:/\?', unix=True)
        check('//*/*/*', R'//\*/\*/\*', unix=True)
        check('//[^what]/name/temp', R'//\[^what\]/name/temp', unix=True)


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


class TestTypes(unittest.TestCase):
    """Test basic sequences."""

    def test_match_set(self):
        """Test `set` matching."""

        self.assertTrue(fnmatch.fnmatch('a', {'a'}))

    def test_match_tuple(self):
        """Test `tuple` matching."""

        self.assertTrue(fnmatch.fnmatch('a', ('a',)))

    def test_match_list(self):
        """Test `list` matching."""

        self.assertTrue(fnmatch.fnmatch('a', ['a']))


class TestPrecompile(unittest.TestCase):
    """Test precompiled match objects."""

    def test_precompiled_match(self):
        """Test precompiled matching."""

        m = fnmatch.compile('*file')
        self.assertTrue(m.match('testfile'))

    def test_precompiled_match_empty(self):
        """Test precompiled matching with empty input."""

        m = fnmatch.compile('*file')
        self.assertFalse(m.match(''))

    def test_precompiled_filter(self):
        """Test precompiled filtering."""

        m = fnmatch.compile('*file')
        self.assertEqual(m.filter(['testfile', 'test_2_file', 'nope']), ['testfile', 'test_2_file'])

    def test_precompiled_filter_empty(self):
        """Test precompiled filtering with empty input."""

        m = fnmatch.compile('*file')
        self.assertEqual(m.filter([]), [])

    def test_hash(self):
        """Test hashing."""

        m1 = fnmatch.compile('test', flags=fnmatch.C)
        m2 = fnmatch.compile('test', flags=fnmatch.C)
        m3 = fnmatch.compile('test', flags=fnmatch.I)
        m4 = fnmatch.compile(b'test', flags=fnmatch.C)

        self.assertTrue(m1 == m2)
        self.assertTrue(m1 != m3)
        self.assertTrue(m1 != m4)

        m5 = copy.copy(m1)
        self.assertTrue(m1 == m5)
        self.assertTrue(m5 in {m1})
