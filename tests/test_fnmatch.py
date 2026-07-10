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

        # Nested extended list reduction cases
        ['!(!(2|3))_@(foo|bar)', '2_foo', True, fnmatch.E],
        ['@(!(2))_!(!(foo|bar))', '1_foo', True, fnmatch.E],
        ['@(!(2))_!(!(foo|bar)_test)', '1_foo_test', True, fnmatch.E],

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
        ['[!^]bc', '!bc', True, 0],
        ['[^!]bc', '^bc', True, 0],

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
        [R'a\/b', 'a\\\\b', True, fnmatch.W],

        # Empty string cases
        ['*(a|b|c)', '', True, fnmatch.E],
        ['', '', True, 0]
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

        gpat = fnmatch.translate("test @(this) +(many) ?(meh)*(!) !(not this)@(.md)", flags=fnmatch.E | fnmatch.TC)
        pat = re.compile(gpat[0][0])
        match = pat.match('test this manymanymany meh!!!!! okay.md')
        self.assertEqual(('this', 'manymanymany', 'meh', '!!!!!', 'okay', '.md'), match.groups())

    def test_nested_capture_groups(self):
        """Test nested capture groups."""

        gpat = fnmatch.translate("@(file)@(+([[:digit:]]))@(.*)", flags=fnmatch.E | fnmatch.TC)
        pat = re.compile(gpat[0][0])
        match = pat.match('file33.test.txt')
        self.assertEqual(('file', '33', '33', '.test.txt'), match.groups())

    def test_list_groups(self):
        """Test capture groups with lists."""

        gpat = fnmatch.translate("+(f|i|l|e)+([[:digit:]])@(.*)", flags=fnmatch.E | fnmatch.TC)
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

        p1 = self.split_translate('test[[:upper:]|]', flags=flags)[0]
        self.assertEqual(p1, ['^(?s:test[A-Z\\|])$'])

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


class TestZSHNumbers(unittest.TestCase):
    """Test ZSH numbers."""

    def range_check(self, min_val=None, max_val=None, ceiling = 2000) -> None:
        """Check cases."""

        print('')

        mn = str(min_val) if min_val is not None else ''
        mx = str(max_val) if max_val is not None else ''

        p = f'test<{mn}-{mx}>.txt'
        print('CASE:', p)

        pattern = fnmatch.compile(p, flags=fnmatch.ZN)
        for n in range(0, ceiling):
            if max_val is None and min_val is None:
                expected = 0 <= n
            elif max_val is None:
                expected = min_val <= n
            elif min_val is None:
                expected = 0 <= n <= max_val
            else:
                expected = min_val <= n <= max_val
            actual = pattern.match(f'test{n}.txt')
            self.assertEqual(actual, expected)

            actual = pattern.match(f'test00{n}.txt')
            self.assertEqual(actual, expected)

        if max_val is None and min_val:
            # spot-check some very large numbers well beyond ceiling
            for n in [10**6, 10**6 + 1, 10**9, 10**9 - 1, 10**12]:
                expected = n >= (min_val if min_val is not None else 0)
                actual = pattern.match(f'test{n}.txt')
                self.assertEqual(actual, expected)

        if min_val is not None and max_val is not None:
            # also check some non-numeric / malformed inputs never match
            for bad in ["", "-5", "1a", " 5", "5 ", "007" if min_val > 7 or max_val < 7 else "abc"]:
                self.assertFalse(pattern.match(bad))

    def test_range(self):
        """Test number range."""

        test_ranges = [
            (1, 9), (0, 9), (5, 9), (1, 100), (5, 1200), (10, 99),
            (100, 999), (1, 1), (7, 7), (0, 0), (1, 15), (99, 101),
            (999, 1001), (1, 1000), (250, 750), (1, 3), (17, 5000),
        ]
        for lo, hi in test_ranges:
            self.range_check(lo, hi, ceiling=max(hi + 50, 2000))

    def test_fuzz(self):
        """Test fuzzed number range."""

        import random

        random.seed(0)
        for _ in range(200):
            a = random.randint(0, 5000)
            b = random.randint(0, 5000)
            lo, hi = min(a, b), max(a, b)
            self.range_check(lo, hi, ceiling=5100)

    def test_uncapped_high(self):
        """Test uncapped high value."""

        for lo in [0, 1, 5, 9, 10, 17, 99, 100, 250, 999, 1000, 4321]:
            self.range_check(lo, ceiling=6000)

    def test_uncapped_high_fuzz(self):
        """Test fuzzed uncapped high values."""

        import random

        for _ in range(100):
            lo = random.randint(0, 6000)
            self.range_check(lo, ceiling=6100)

    def test_uncapped_low(self):
        """Test uncapped low value."""

        for hi in [0, 1, 5, 9, 10, 17, 99, 100, 250, 999, 1000, 4321]:
            self.range_check(max_val=hi, ceiling=6000)

    def test_uncapped_low_fuzz(self):
        """Test fuzzed uncapped low values."""

        import random

        for _ in range(100):
            hi = random.randint(0, 6000)
            self.range_check(max_val=hi, ceiling=6100)


    def test_uncapped_low_high(self):
        """Test uncapped low and high value."""

        self.range_check(ceiling=6000)

    def test_bad_syntax(self):
        """Test bad syntax."""

        self.assertTrue(fnmatch.fnmatch('test<3-.txt', 'test<3-.txt', flags=fnmatch.ZN))

    def test_escaped(self):
        """Test bad syntax."""

        self.assertTrue(fnmatch.fnmatch('test<0-9>.txt', R'test<0-9\>.txt', flags=fnmatch.ZN))
        self.assertTrue(fnmatch.fnmatch('test<0-9>.txt', R'test\<0-9>.txt', flags=fnmatch.ZN))

    def test_bad_range(self):
        """Test bad range."""

        self.assertFalse(fnmatch.fnmatch('test3.txt', 'test<9-0>.txt', flags=fnmatch.ZN))

    def test_exmatch(self):
        """Test within `EXTMATCH`."""

        self.assertTrue(fnmatch.fnmatch('test3.txt', '@(test|test<0-9>).txt', flags=fnmatch.ZN | fnmatch.E))

    def test_truncate(self):
        """Test number truncation."""

        tmax = 0xffff_ffff_ffff_ffff
        self.assertFalse(fnmatch.fnmatch(f'test{tmax}.txt', f'test<{0}-{tmax}>.txt', flags=fnmatch.ZN))
        self.assertTrue(fnmatch.fnmatch(f'test{0xFFFF_FFFF}.txt', f'test<{0}-{tmax}>.txt', flags=fnmatch.ZN))
        self.assertTrue(fnmatch.fnmatch(f'test{tmax}.txt', f'test<{tmax}->.txt', flags=fnmatch.ZN))
        self.assertFalse(fnmatch.fnmatch(f'test{0xFFFF_FFFF}.txt', f'test<{tmax}->.txt', flags=fnmatch.ZN))
        self.assertFalse(fnmatch.fnmatch(f'test{0xFFFF_FFFF}.txt', f'test<{tmax}-{tmax}>.txt', flags=fnmatch.ZN))
        self.assertFalse(fnmatch.fnmatch(f'test{tmax + 10}.txt', f'test<{tmax}-{tmax}>.txt', flags=fnmatch.ZN))
        self.assertFalse(fnmatch.fnmatch(f'test{tmax}.txt', f'test<{tmax}-{tmax}>.txt', flags=fnmatch.ZN))
        self.assertTrue(fnmatch.fnmatch(f'test{str(tmax)[:19]}.txt', f'test<{tmax}-{tmax}>.txt', flags=fnmatch.ZN))


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


class TestExtendedCases(unittest.TestCase):
    """Test extended match cases."""

    def assert_group_equal(self, pat1, pat2):
        """Compare equivalent groups."""

        regex1 = fnmatch.translate(pat1, flags=fnmatch.E)[0][0]
        regex2 = fnmatch.translate(pat2, flags=fnmatch.E)[0][0]
        try:
            self.assertEqual(regex1, regex2)
        except Exception:
            print(f"{pat1} <=> {pat2}")
            raise

    def test_and(self):
        """Test reduction of the `@` group and other groups."""

        self.assert_group_equal('@(@(a|b)|c|d)', '@(a|b|c|d)')
        self.assert_group_equal('@(a|@(b|c)|d)', '@(a|b|c|d)')
        self.assert_group_equal('@(a|b|@(c|d))', '@(a|b|c|d)')

        self.assert_group_equal('?(@(a|b)|c|d)', '?(a|b|c|d)')
        self.assert_group_equal('?(a|@(b|c)|d)', '?(a|b|c|d)')
        self.assert_group_equal('?(a|b|@(c|d))', '?(a|b|c|d)')

        self.assert_group_equal('*(@(a|b)|c|d)', '*(a|b|c|d)')
        self.assert_group_equal('*(a|@(b|c)|d)', '*(a|b|c|d)')
        self.assert_group_equal('*(a|b|@(c|d))', '*(a|b|c|d)')

        self.assert_group_equal('+(@(a|b)|c|d)', '+(a|b|c|d)')
        self.assert_group_equal('+(a|@(b|c)|d)', '+(a|b|c|d)')
        self.assert_group_equal('+(a|b|@(c|d))', '+(a|b|c|d)')

        self.assert_group_equal('!(@(a|b)|c|d)', '!(a|b|c|d)')
        self.assert_group_equal('!(a|@(b|c)|d)', '!(a|b|c|d)')
        self.assert_group_equal('!(a|b|@(c|d))', '!(a|b|c|d)')

        self.assert_group_equal('@(@(a|b|c))', '@(a|b|c)')
        self.assert_group_equal('?(@(a|b|c))', '?(a|b|c)')
        self.assert_group_equal('*(@(a|b|c))', '*(a|b|c)')
        self.assert_group_equal('+(@(a|b|c))', '+(a|b|c)')
        self.assert_group_equal('!(@(a|b|c))', '!(a|b|c)')

    def test_one_or_none(self):
        """Test reduction of the `?` group and other groups."""

        self.assert_group_equal('@(?(a|b)|c|d)', '@(a|b||c|d)')
        self.assert_group_equal('@(a|?(b|c)|d)', '@(a|b|c||d)')
        self.assert_group_equal('@(a|b|?(c|d))', '@(a|b|c|d|)')

        self.assert_group_equal('?(?(a|b)|c|d)', '?(a|b|c|d)')
        self.assert_group_equal('?(a|?(b|c)|d)', '?(a|b|c|d)')
        self.assert_group_equal('?(a|b|?(c|d))', '?(a|b|c|d)')

        self.assert_group_equal('*(?(a|b)|c|d)', '*(a|b|c|d)')
        self.assert_group_equal('*(a|?(b|c)|d)', '*(a|b|c|d)')
        self.assert_group_equal('*(a|b|?(c|d))', '*(a|b|c|d)')

        self.assert_group_equal('+(?(a|b)|c|d)', '+(a|b||c|d)')
        self.assert_group_equal('+(a|?(b|c)|d)', '+(a|b|c||d)')
        self.assert_group_equal('+(a|b|?(c|d))', '+(a|b|c|d|)')

        self.assert_group_equal('!(?(a|b)|c|d)', '!(a|b||c|d)')
        self.assert_group_equal('!(a|?(b|c)|d)', '!(a|b|c||d)')
        self.assert_group_equal('!(a|b|?(c|d))', '!(a|b|c|d|)')

        self.assert_group_equal('@(?(a|b|c))', '?(a|b|c)')
        self.assert_group_equal('?(?(a|b|c))', '?(a|b|c)')
        self.assert_group_equal('*(?(a|b|c))', '*(a|b|c)')
        self.assert_group_equal('+(?(a|b|c))', '*(a|b|c)')

    def test_more_or_none(self):
        """Test reduction of the `*` group and other groups."""

        self.assert_group_equal('*(*(a|b)|c|d)', '*(a|b|c|d)')
        self.assert_group_equal('*(a|*(b|c)|d)', '*(a|b|c|d)')
        self.assert_group_equal('*(a|b|*(c|d))', '*(a|b|c|d)')

        self.assert_group_equal('+(*(a|b)|c|d)', '+(a|b||c|d)')
        self.assert_group_equal('+(a|*(b|c)|d)', '+(a|b|c||d)')
        self.assert_group_equal('+(a|b|*(c|d))', '+(a|b|c|d|)')

        self.assert_group_equal('@(*(a|b|c))', '*(a|b|c)')

    def test_one_or_more(self):
        """Test reduction of the `+` group and other groups."""

        self.assert_group_equal('*(+(a|b)|c|d)', '*(a|b|c|d)')
        self.assert_group_equal('*(a|+(b|c)|d)', '*(a|b|c|d)')
        self.assert_group_equal('*(a|b|+(c|d))', '*(a|b|c|d)')

        self.assert_group_equal('+(+(a|b)|c|d)', '+(a|b|c|d)')
        self.assert_group_equal('+(a|+(b|c)|d)', '+(a|b|c|d)')
        self.assert_group_equal('+(a|b|+(c|d))', '+(a|b|c|d)')

        self.assert_group_equal('@(+(a|b|c))', '+(a|b|c)')
        self.assert_group_equal('?(+(a|b|c))', '*(a|b|c)')
        self.assert_group_equal('*(+(a|b|c))', '*(a|b|c)')

    def test_not(self):
        """Test reduction of the `!` group and other groups."""

        self.assert_group_equal('@(!(a|b|c))', '!(a|b|c)')
        self.assert_group_equal('!(!(a|b|c))', '@(a|b|c)')

    def test_mixed(self):
        """Test mixed cases."""

        self.assert_group_equal(
            '!(!(@(@(a|b)|?(@(c|d)|?(e|f))|*(@(f|h)|?(i|j)|*(k|l)|+(m|n)))))',
            '@(a|b|c|d|e|f||*(f|h|i|j|k|l|m|n))'
        )

    def test_empty_slots(self):
        """Test empty slot reduction."""

        self.assert_group_equal('+(||?(a|b)|c|d)', '+(|a|b|c|d)')
        self.assert_group_equal('+(a|b|?(c|d)|||e)', '+(a|b|c|d||e)')
        self.assert_group_equal('+(a|b||||?(c|d)|e)', '+(a|b||c|d|e)')
        self.assert_group_equal('+(a|b|?(c|d)|||)', '+(a|b|c|d|)')

        self.assert_group_equal('@(||||)', '@(|)')
        self.assert_group_equal('@(|||a|b)', '@(|a|b)')
        self.assert_group_equal('@(a|b|||)', '@(a|b|)')
        self.assert_group_equal('@(a||||b)', '@(a||b)')

    def test_parse_halt_split(self):
        """Test halting of parsing."""

        # Top level
        p1 = '@(test+(a|b)'
        p2 = R'@\(test+\(a|b\)'
        self.assert_group_equal(p1, p2)

        self.assertEqual(
            len(fnmatch.translate(p1, flags=fnmatch.E | fnmatch.S)[0]),
            len(fnmatch.translate(p2, flags=fnmatch.E | fnmatch.S)[0])
        )

        # Nested
        p1 = '@(@(test+(a|b)'
        p2 = R'@\(@\(test+\(a|b\)'
        self.assert_group_equal(p1, p2)

        self.assertEqual(
            len(fnmatch.translate(p1, flags=fnmatch.E | fnmatch.S)[0]),
            len(fnmatch.translate(p2, flags=fnmatch.E | fnmatch.S)[0])
        )

        # Deeply nested
        p1 = '@(@(@(test+(a|b)'
        p2 = R'@\(@\(@\(test+\(a|b\)'
        self.assert_group_equal(p1, p2)

        self.assertEqual(
            len(fnmatch.translate(p1, flags=fnmatch.E | fnmatch.S)[0]),
            len(fnmatch.translate(p2, flags=fnmatch.E | fnmatch.S)[0])
        )


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
