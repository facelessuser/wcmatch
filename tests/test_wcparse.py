# -*- coding: utf-8 -*-
"""Tests for `wcparse`."""
import unittest
import re
import copy
import wcmatch._wcparse as _wcparse


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
            False,
            _wcparse.BRACE | _wcparse.SPLIT | _wcparse.EXTMATCH
        )
        self.assertEqual(sorted(results), sorted(['test@(this|that)', '*.py', 'test@(this|other)', '*.py']))
