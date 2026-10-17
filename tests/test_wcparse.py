# -*- coding: utf-8 -*-
"""Tests for `wcparse`."""
import unittest
import re
import copy
import pytest
import wcmatch._wcparse as _wcparse


@pytest.mark.parametrize('parse', [_wcparse.compile_pattern, _wcparse.translate])
@pytest.mark.parametrize('limit', [0, -1])
@pytest.mark.parametrize('binary', [False, True])
def test_unlimited_patterns_with_exclusions(parse, limit, binary):
    """Exclusions must not enable a limit for later brace expansions."""

    patterns = ['a', '{b,c}', '{d,e}']
    exclude = ['x', '{y,z}']
    if binary:
        patterns = [p.encode() for p in patterns]
        exclude = [p.encode() for p in exclude]
    positive, negative = parse(patterns, _wcparse.BRACE, limit, exclude=exclude)
    assert len(positive) == 5
    assert len(negative) == 3


@pytest.mark.parametrize('parse', [_wcparse.compile_pattern, _wcparse.translate])
@pytest.mark.parametrize('pattern', ['a', '{a,b}'])
@pytest.mark.parametrize('binary', [False, True])
def test_exclusions_exhaust_pattern_limit(parse, pattern, binary):
    """An exhausted finite budget must not become the unlimited sentinel."""

    exclude = 'x'
    if binary:
        pattern = pattern.encode()
        exclude = exclude.encode()
    with pytest.raises(_wcparse.PatternLimitException):
        parse(pattern, _wcparse.BRACE, 1, exclude=exclude)


@pytest.mark.parametrize('parse', [_wcparse.compile_pattern, _wcparse.translate])
@pytest.mark.parametrize('binary', [False, True])
def test_combined_pattern_limit_boundary(parse, binary):
    """Include and exclude patterns share a finite budget."""

    patterns = ['a', '{b,c}']
    exclude = 'x'
    if binary:
        patterns = [p.encode() for p in patterns]
        exclude = exclude.encode()
    positive, negative = parse(patterns, _wcparse.BRACE, 4, exclude=exclude)
    assert len(positive) == 3
    assert len(negative) == 1
    with pytest.raises(_wcparse.PatternLimitException):
        parse(patterns, _wcparse.BRACE, 3, exclude=exclude)


@pytest.mark.parametrize('parse', [_wcparse.compile_pattern, _wcparse.translate])
@pytest.mark.parametrize('binary', [False, True])
def test_exclusion_only_at_pattern_limit(parse, binary):
    """Using the entire budget is valid when there are no include patterns."""

    positive, negative = parse([], 0, 1, exclude=b'x' if binary else 'x')
    assert positive == []
    assert len(negative) == 1


class TestWcparse(unittest.TestCase):
    """Test `wcparse`."""

    def test_hash(self):
        """Test hashing of search."""

        p1 = re.compile('test')
        p2 = re.compile('test')
        p3 = re.compile('test', re.X)
        p4 = re.compile(b'test')

        w1 = _wcparse.WcRegexp((p1,))
        w2 = _wcparse.WcRegexp((p2,))
        w3 = _wcparse.WcRegexp((p3,))
        w4 = _wcparse.WcRegexp((p4,))
        w5 = _wcparse.WcRegexp((p1,), (p3,))

        self.assertTrue(w1 == w2)
        self.assertTrue(w1 != w3)
        self.assertTrue(w1 != w4)
        self.assertTrue(w1 != w5)

        w6 = copy.copy(w1)
        self.assertTrue(w1 == w6)
        self.assertTrue(w6 in {w1})

    def test_preprocessor_sequence(self):
        """Test the integrity of the order of preprocessors."""

        results = _wcparse.expand(
            'test@(this{|that,|other})|*.py',
            _wcparse.BRACE | _wcparse.SPLIT | _wcparse.EXTMATCH,
            0
        )
        self.assertEqual(sorted(results), sorted(['test@(this|that)', 'test@(this|other)', '*.py', '*.py']))

    def test_compile_expansion_okay(self):
        """Test expansion is okay."""

        self.assertEqual(len(_wcparse.compile(['{1..10}'], _wcparse.BRACE)), 10)

    def test_compile_unique_optimization_okay(self):
        """Test that redundant patterns are reduced in compile."""

        self.assertEqual(len(_wcparse.compile(['|'.join(['a'] * 10)], _wcparse.SPLIT, 10)), 1)

    def test_translate_expansion_okay(self):
        """Test expansion is okay."""

        p1, p2 = _wcparse.translate(['{1..10}'], _wcparse.BRACE, 10)
        count = len(p1) + len(p2)
        self.assertEqual(count, 10)

    def test_translate_unique_optimization_okay(self):
        """Test that redundant patterns are reduced in translate."""
        p1, p2 = _wcparse.translate(['|'.join(['a'] * 10)], _wcparse.SPLIT, 10)
        count = len(p1) + len(p2)
        self.assertEqual(count, 1)

    def test_expansion_limt(self):
        """Test expansion limit."""

        with self.assertRaises(_wcparse.PatternLimitException):
            _wcparse.compile(['{1..11}'], _wcparse.BRACE, 10)

        with self.assertRaises(_wcparse.PatternLimitException):
            _wcparse.compile(['|'.join(['a'] * 11)], _wcparse.SPLIT, 10)

        with self.assertRaises(_wcparse.PatternLimitException):
            _wcparse.compile(
                ['{{{},{}}}'.format('|'.join(['a'] * 6), '|'.join(['a'] * 5))],
                _wcparse.SPLIT | _wcparse.BRACE, 10
            )

        with self.assertRaises(_wcparse.PatternLimitException):
            _wcparse.compile(
                ['|'.join(['a'] * 10), '|'.join(['a'] * 5)],
                _wcparse.SPLIT | _wcparse.BRACE, 10
            )

    def test_expansion_limt_translation(self):
        """Test expansion limit."""

        with self.assertRaises(_wcparse.PatternLimitException):
            _wcparse.translate(['{1..11}'], _wcparse.BRACE, 10)

        with self.assertRaises(_wcparse.PatternLimitException):
            _wcparse.translate(['|'.join(['a'] * 11)], _wcparse.SPLIT, 10)

        with self.assertRaises(_wcparse.PatternLimitException):
            _wcparse.translate(
                ['{{{},{}}}'.format('|'.join(['a'] * 6), '|'.join(['a'] * 5))],
                _wcparse.SPLIT | _wcparse.BRACE, 10
            )

        with self.assertRaises(_wcparse.PatternLimitException):
            _wcparse.translate(
                ['|'.join(['a'] * 10), '|'.join(['a'] * 5)],
                _wcparse.SPLIT | _wcparse.BRACE, 10
            )

    def test_expansion_no_limit_compile(self):
        """Test no expansion limit compile."""

        self.assertEqual(len(_wcparse.compile(['{1..11}'], _wcparse.BRACE, -1)), 11)

    def test_expansion_no_limit_translate(self):
        """Test no expansion limit translate."""

        p1, p2 = _wcparse.translate(['{1..11}'], _wcparse.BRACE, 0)
        count = len(p1) + len(p2)
        self.assertEqual(count, 11)

    def test_tilde_pos_none(self):
        """Test that tilde position gives -1 when no tilde found."""

        self.assertEqual(_wcparse.tilde_pos('pattern', _wcparse.GLOBTILDE | _wcparse.REALPATH), -1)

    def test_tilde_pos_normal(self):
        """Test that tilde position gives 0 when tilde found."""

        self.assertEqual(_wcparse.tilde_pos('~pattern', _wcparse.GLOBTILDE | _wcparse.REALPATH), 0)

    def test_tilde_pos_negative_normal(self):
        """Test that tilde position gives 0 when tilde is found and `NEGATE` is enabled."""

        self.assertEqual(_wcparse.tilde_pos('~pattern', _wcparse.GLOBTILDE | _wcparse.REALPATH | _wcparse.NEGATE), 0)

    def test_tilde_pos_negative_negate(self):
        """Test that tilde position gives 1 when tilde is found and `NEGATE` is enabled."""

        self.assertEqual(_wcparse.tilde_pos('!~pattern', _wcparse.GLOBTILDE | _wcparse.REALPATH | _wcparse.NEGATE), 1)

    def test_unc_pattern(self):
        """Test UNC pattern."""

        self.assertEqual(_wcparse.RE_WIN_DRIVE[0].match('//?/UNC/server/mount').group(0), '//?/UNC/server/mount')
        self.assertEqual(_wcparse.RE_WIN_DRIVE[0].match('//?/UNC/server/mount/').group(0), '//?/UNC/server/mount/')
        self.assertEqual(_wcparse.RE_WIN_DRIVE[0].match('//?/UNC/server/mount/path').group(0), '//?/UNC/server/mount/')
        self.assertEqual(_wcparse.RE_WIN_DRIVE[0].match('//./UNC/server/mount/path').group(0), '//./UNC/server/mount/')
        self.assertEqual(_wcparse.RE_WIN_DRIVE[0].match('//?/UNC/c:').group(0), '//?/UNC/')
        self.assertEqual(_wcparse.RE_WIN_DRIVE[0].match('//?/UNC/c:/').group(0), '//?/UNC/')
        self.assertEqual(_wcparse.RE_WIN_DRIVE[0].match('//?/c:').group(0), '//?/c:')
        self.assertEqual(_wcparse.RE_WIN_DRIVE[0].match('//?/c:/').group(0), '//?/c:/')
        self.assertEqual(_wcparse.RE_WIN_DRIVE[0].match('//?/what').group(0), '//?/what')
        self.assertEqual(_wcparse.RE_WIN_DRIVE[0].match('//server/mount').group(0), '//server/mount')
        self.assertEqual(_wcparse.RE_WIN_DRIVE[0].match('//server/mount/').group(0), '//server/mount/')
        self.assertIsNone(_wcparse.RE_WIN_DRIVE[0].match('//server'))
        self.assertEqual(
            _wcparse.RE_WIN_DRIVE[0].match('//?/GLOBAL/UNC/server/mount/temp').group(0),
            '//?/GLOBAL/UNC/server/mount/'
        )

    def test_bad_root_dir(self):
        """Test bad root directory."""

        with self.assertRaises(TypeError):
            _wcparse.compile(['string'], _wcparse.PATHNAME | _wcparse.REALPATH, 0).match('string', b'rdir', None)
