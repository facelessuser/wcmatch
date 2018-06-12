# -*- coding: utf-8 -*-
"""Tests for rumcore."""
import unittest
import pytest
import mock
import wcmatch.fnmatch as fnmatch
from wcmatch import util
import wcmatch._wcparse as _wcparse


class TestFnMatch(unittest.TestCase):
    """Test fnmatch."""

    cases = [
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

        # these test that '\' is handled correctly in character sets;
        [r'[\]', '\\', False, 0],
        [r'[!\]', 'a', False, 0],
        [r'[!\]', '\\', False, 0],
        [r'[\\]', '\\', True, 0],
        [r'[!\\]', 'a', True, 0],
        [r'[!\\]', '\\', False, 0],

        # test that filenames with newlines in them are handled correctly.
        ['foo*', 'foo\nbar', True, 0],
        ['foo*', 'foo\nbar\n', True, 0],
        ['foo*', '\nfoo', False, 0],
        ['*', '\n', True, 0],

        "Force Case",
        ['abc', 'abc', True, fnmatch.F],
        ['abc', 'AbC', False, fnmatch.F],
        ['AbC', 'abc', False, fnmatch.F],
        ['AbC', 'AbC', True, fnmatch.F],

        ['usr/bin', 'usr/bin', True, fnmatch.F],
        ['usr/bin', 'usr\\bin', False, fnmatch.F],
        [r'usr\\bin', 'usr/bin', False, fnmatch.F],
        [r'usr\\bin', 'usr\\bin', True, fnmatch.F],

        [b'te*', b'test', True, 0],
        [b'te*\xff', b'test\xff', True, 0],
        [b'foo*', b'foo\nbar', True, 0],

        "OS Case",
        ['abc', 'abc', True, 0],
        ['abc', 'AbC', not util.is_case_sensitive(), 0],
        ['AbC', 'abc', not util.is_case_sensitive(), 0],
        ['AbC', 'AbC', True, 0],

        ['usr/bin', 'usr/bin', True, 0],
        ['usr/bin', 'usr\\bin', not util.is_case_sensitive(), 0],
        [r'usr\\bin', 'usr/bin', not util.is_case_sensitive(), 0],
        [r'usr\\bin', 'usr\\bin', True, 0],

        ['[[]', '[', True, 0],
        ['[a&&b]', '&', True, 0],
        ['[a||b]', '|', True, 0],
        ['[a~~b]', '~', True, 0],
        ['[a-z+--A-Z]', ',', True, 0],
        ['[a-z--/A-Z]', '.', True, 0],

        ['.abc', '.abc', True, 0],
        [r'\.abc', '.abc', True, 0],
        ['?abc', '.abc', True, 0],
        ['*abc', '.abc', True, 0],
        ['[.]abc', '.abc', True, 0],
        ['*(.)abc', '.abc', True, fnmatch.E],
        ['*(?)abc', '.abc', True, fnmatch.E],
        ['*(?|.)abc', '.abc', True, fnmatch.E],
        ['*(?|*)abc', '.abc', True, fnmatch.E],

        "Period",
        ['.abc', '.abc', True, fnmatch.P],
        [r'\.abc', '.abc', True, fnmatch.P],
        ['?abc', '.abc', False, fnmatch.P],
        ['*abc', '.abc', False, fnmatch.P],
        ['[.]abc', '.abc', False, fnmatch.P],
        ['*(.)abc', '.abc', False, fnmatch.E | fnmatch.P],
        [r'*(\.)abc', '.abc', False, fnmatch.E | fnmatch.P],
        ['*(?)abc', '.abc', False, fnmatch.E | fnmatch.P],
        ['*(?|.)abc', '.abc', False, fnmatch.E | fnmatch.P],
        ['*(?|*)abc', '.abc', False, fnmatch.E | fnmatch.P],
        ['a.bc', 'a.bc', True, fnmatch.P],
        ['a?bc', 'a.bc', True, fnmatch.P],
        ['a*bc', 'a.bc', True, fnmatch.P],
        ['a[.]bc', 'a.bc', True, fnmatch.P],
        ['a*(.)bc', 'a.bc', True, fnmatch.E | fnmatch.P],
        [r'a*(\.)bc', 'a.bc', True, fnmatch.E | fnmatch.P],
        ['a*(?)bc', 'a.bc', True, fnmatch.E | fnmatch.P],
        ['a*(?|.)bc', 'a.bc', True, fnmatch.E | fnmatch.P],
        ['a*(?|*)bc', 'a.bc', True, fnmatch.E | fnmatch.P],

        "POSIX style character classes",
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

        "Backwards ranges",
        ['[a-z]', 'a', True, 0],
        ['[z-a]', 'a', False, 0],
        ['[!z-a]', 'a', True, 0],
        ['[!a-z]', 'a', False, 0]
    ]

    filter_cases = [
        ['P*', ['Python', 'Ruby', 'Perl', 'Tcl'], ['Python', 'Perl'], 0],
        [b'P*', [b'Python', b'Ruby', b'Perl', b'Tcl'], [b'Python', b'Perl'], 0],
        [
            '*.p*',
            ['Test.py', 'Test.rb', 'Test.PL'],
            (['Test.py', 'Test.PL'] if not util.is_case_sensitive() else ['Test.PL']),
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
        ]
    ]

    def test_matches(self):
        """Test matches."""

        for case in self.cases:
            if isinstance(case, str):
                print(case, '\n')
            else:
                print("PATTERN: ", case[0])
                print("FILE: ", case[1])
                print("FLAGS: ", bin(case[3]))
                print("TEST: ", case[2], '\n')
                self.assertEqual(fnmatch.fnmatch(case[1], case[0], flags=case[3]), case[2])

    def test_filters(self):
        """Test filters."""

        for case in self.cases:
            if isinstance(case, str):
                print(case, '\n')
            else:
                print("PATTERN: ", case[0])
                print("FILES: ", case[1])
                print("FLAGS: ", bin(case[3]))
                value = fnmatch.fnmatch(case[1], case[0], flags=case[3])
                print("TEST: ", value, '<=>', case[2], '\n')
                self.assertEqual(value, case[2])

    @mock.patch('wcmatch.util.is_case_sensitive')
    def test_split_parsing(self, mock__iscase_sensitive):
        """Test wildcard parsing."""

        mock__iscase_sensitive.return_value = True

        _wcparse._compile.cache_clear()

        p1, p2 = fnmatch.translate(
            fnmatch.fnsplit('*test[a-z]?|*test2[a-z]?|!test[!a-z]|!test[!-|a-z]'), flags=fnmatch.N
        )
        if util.PY36:
            self.assertEqual(p1, [r'^(?s:(?=.).*?test[a-z].)$', r'^(?s:(?=.).*?test2[a-z].)$'])
            self.assertEqual(p2, [r'^(?!(?s:test[^a-z])).*?$', r'^(?!(?s:test[^\-\|a-z])).*?$'])
        else:
            self.assertEqual(p1, [r'(?s)^(?:(?=.).*?test[a-z].)$', r'(?s)^(?:(?=.).*?test2[a-z].)$'])
            self.assertEqual(p2, [r'(?s)^(?!(?:test[^a-z])).*?$', r'(?s)^(?!(?:test[^\-\|a-z])).*?$'])

        p1, p2 = fnmatch.translate(fnmatch.fnsplit('test[]][!][][]', flags=fnmatch.F), flags=fnmatch.F)
        if util.PY36:
            self.assertEqual(p1, [r'^(?s:test[\]][^\][]\[\])$'])
            self.assertEqual(p2, [])
        else:
            self.assertEqual(p1, [r'(?s)^(?:test[\]][^\][]\[\])$'])
            self.assertEqual(p2, [])

        p1, p2 = fnmatch.translate(fnmatch.fnsplit('test[!]'))
        if util.PY37:
            self.assertEqual(p1, [r'^(?s:test\[!\])$'])
            self.assertEqual(p2, [])
        elif util.PY36:
            self.assertEqual(p1, [r'^(?s:test\[\!\])$'])
            self.assertEqual(p2, [])
        else:
            self.assertEqual(p1, [r'(?s)^(?:test\[\!\])$'])
            self.assertEqual(p2, [])

        p1, p2 = fnmatch.translate(fnmatch.fnsplit('|test|'))
        if util.PY36:
            self.assertEqual(p1, [r'^(?s:)$', r'^(?s:test)$', r'^(?s:)$'])
            self.assertEqual(p2, [])
        else:
            self.assertEqual(p1, [r'(?s)^(?:)$', r'(?s)^(?:test)$', r'(?s)^(?:)$'])
            self.assertEqual(p2, [])

        p1, p2 = fnmatch.translate(fnmatch.fnsplit('-|-test|-'), flags=fnmatch.N | fnmatch.M)
        if util.PY36:
            self.assertEqual(p1, [])
            self.assertEqual(p2, [r'^(?!(?s:)).*?$', r'^(?!(?s:test)).*?$', r'^(?!(?s:)).*?$'])
        else:
            self.assertEqual(p1, [])
            self.assertEqual(p2, [r'(?s)^(?!(?:)).*?$', r'(?s)^(?!(?:test)).*?$', r'(?s)^(?!(?:)).*?$'])

        p1, p2 = fnmatch.translate(fnmatch.fnsplit('test[^chars]'))
        if util.PY36:
            self.assertEqual(p1, [r'^(?s:test[^chars])$'])
            self.assertEqual(p2, [])
        else:
            self.assertEqual(p1, [r'(?s)^(?:test[^chars])$'])
            self.assertEqual(p2, [])

        p1 = fnmatch.translate(fnmatch.fnsplit(r'test[^\\-\\&]'))[0]
        if util.PY36:
            self.assertEqual(p1, [r'^(?s:test[^\\-\\\&])$'])
        else:
            self.assertEqual(p1, [r'(?s)^(?:test[^\\-\\\&])$'])

        p1 = fnmatch.translate(fnmatch.fnsplit(r'\\*\\?\\|\\[\\]'))[0]
        if util.PY36:
            self.assertEqual(p1, [r'^(?s:\\.*?\\.\\)$', r'^(?s:\\[\\])$'])
        else:
            self.assertEqual(p1, [r'(?s)^(?:\\.*?\\.\\)$', r'(?s)^(?:\\[\\])$'])

        p1 = fnmatch.translate(fnmatch.fnsplit(r'\\u0300', flags=fnmatch.R), flags=fnmatch.R)[0]
        if util.PY36:
            self.assertEqual(p1, [r'^(?s:\\u0300)$'])
        else:
            self.assertEqual(p1, [r'(?s)^(?:\\u0300)$'])

    def test_posix_range(self):
        """Test posix range."""

        p = fnmatch.translate(r'[[:ascii:]-z]', flags=fnmatch.F)
        if util.PY36:
            self.assertEqual(p, (['^(?s:[\x00-\x7f\\-z])$'], []))
        else:
            self.assertEqual(p, (['(?s)^(?:[\x00-\x7f\\-z])$'], []))

        p = fnmatch.translate(r'[a-[:ascii:]-z]', flags=fnmatch.F)
        if util.PY36:
            self.assertEqual(p, (['^(?s:[a\\-\x00-\x7f\\-z])$'], []))
        else:
            self.assertEqual(p, (['(?s)^(?:[a\\-\x00-\x7f\\-z])$'], []))

    def test_filter(self):
        """Test filter."""

        self.assertEqual(
            fnmatch.filter(['testm', 'test\\3', 'testa'], fnmatch.fnsplit(r'te\st[ma]'), flags=fnmatch.I),
            ['testm', 'testa']
        )

        self.assertEqual(
            fnmatch.filter(['testm', 'test\\3', 'testa'], fnmatch.fnsplit(r'te\st[ma]'), flags=fnmatch.F),
            ['testm', 'testa']
        )

    @mock.patch('wcmatch.util.is_case_sensitive')
    def test_special_escapes(self, mock__iscase_sensitive):
        """Test wildcard character notations."""

        mock__iscase_sensitive.return_value = True

        _wcparse._compile.cache_clear()

        p1, p2 = fnmatch.translate(r'test\x70\u0070\U00000070\160\N{LATIN SMALL LETTER P}', flags=fnmatch.R)
        if util.PY36:
            self.assertEqual(p1, [r'^(?s:testppppp)$'])
            self.assertEqual(p2, [])
        else:
            self.assertEqual(p1, [r'(?s)^(?:testppppp)$'])
            self.assertEqual(p2, [])

        p1, p2 = fnmatch.translate(r'test[\x70][\u0070][\U00000070][\160][\N{LATIN SMALL LETTER P}]', flags=fnmatch.R)
        if util.PY36:
            self.assertEqual(p1, [r'^(?s:test[p][p][p][p][p])$'])
            self.assertEqual(p2, [])
        else:
            self.assertEqual(p1, [r'(?s)^(?:test[p][p][p][p][p])$'])
            self.assertEqual(p2, [])

        p1, p2 = fnmatch.translate(r'test\t\m', flags=fnmatch.R)
        if util.PY36:
            self.assertEqual(p1, [r'^(?s:test\	m)$'])
            self.assertEqual(p2, [])
        else:
            self.assertEqual(p1, [r'(?s)^(?:test\	m)$'])
            self.assertEqual(p2, [])

        p1, p2 = fnmatch.translate(r'test[\\]test', flags=fnmatch.R)
        if util.PY36:
            self.assertEqual(p1, [r'^(?s:test[\\]test)$'])
            self.assertEqual(p2, [])
        else:
            self.assertEqual(p1, [r'(?s)^(?:test[\\]test)$'])
            self.assertEqual(p2, [])

        p1, p2 = fnmatch.translate('test[\\')
        if util.PY36:
            self.assertEqual(p1, [r'^(?s:test\[\\)$'])
            self.assertEqual(p2, [])
        else:
            self.assertEqual(p1, [r'(?s)^(?:test\[\\)$'])
            self.assertEqual(p2, [])

        p1, p2 = fnmatch.translate(r'test\44test', flags=fnmatch.R)
        if util.PY36:
            self.assertEqual(p1, [r'^(?s:test\$test)$'])
            self.assertEqual(p2, [])
        else:
            self.assertEqual(p1, [r'(?s)^(?:test\$test)$'])
            self.assertEqual(p2, [])

        p1, p2 = fnmatch.translate(r'test\44', flags=fnmatch.R)
        if util.PY36:
            self.assertEqual(p1, [r'^(?s:test\$)$'])
            self.assertEqual(p2, [])
        else:
            self.assertEqual(p1, [r'(?s)^(?:test\$)$'])
            self.assertEqual(p2, [])

        p1, p2 = fnmatch.translate(r'test\400', flags=fnmatch.R)
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
            fnmatch.translate(r'test\N', flags=fnmatch.R)

        with pytest.raises(SyntaxError):
            fnmatch.translate(r'test\Nx', flags=fnmatch.R)

        with pytest.raises(SyntaxError):
            fnmatch.translate(r'test\N{', flags=fnmatch.R)
