# -*- coding: utf-8 -*-
"""Tests for rumcore."""
from __future__ import unicode_literals
import unittest
import pytest
import os
import re
import codecs
import tempfile
import textwrap
import wcmatch as wcm
from wcmatch import util


class TestWildcard(unittest.TestCase):
    """Test wildcard pattern parsing."""

    def test_wildcard_parsing(self):
        """Test wildcard parsing."""

        p1, p2 = wcm.translate('*test[a-z]?|*test2[a-z]?|-test[!a-z]|-test[!-|a-z]')
        if util.PY36:
            self.assertEqual(p1, r'(?s:.*test[a-z].|.*test2[a-z].)\Z')
            self.assertEqual(p2, r'(?s:test[^a-z]|test[^\-\|a-z])\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:.*test[a-z].|.*test2[a-z].)\Z')
            self.assertEqual(p2, r'(?ms)(?:test[^a-z]|test[^\-\|a-z])\Z')

        p1, p2 = wcm.translate('test[]][!][][]')
        if util.PY36:
            self.assertEqual(p1, r'(?s:test[]][^][]\[\])\Z')
            self.assertEqual(p2, r'(?s:)\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:test[]][^][]\[\])\Z')
            self.assertEqual(p2, r'(?ms)(?:)\Z')

        p1, p2 = wcm.translate('test[!]')
        if util.PY36:
            self.assertEqual(p1, r'(?s:test\[\!\])\Z')
            self.assertEqual(p2, r'(?s:)\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:test\[\!\])\Z')
            self.assertEqual(p2, r'(?ms)(?:)\Z')

        p1, p2 = wcm.translate('|test|')
        if util.PY36:
            self.assertEqual(p1, r'(?s:|test|)\Z')
            self.assertEqual(p2, r'(?s:)\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:|test|)\Z')
            self.assertEqual(p2, r'(?ms)(?:)\Z')

        p1, p2 = wcm.translate('-|-test|-')
        if util.PY36:
            self.assertEqual(p1, r'(?s:.*)\Z')
            self.assertEqual(p2, r'(?s:|test|)\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:.*)\Z')
            self.assertEqual(p2, r'(?ms)(?:|test|)\Z')

        p1, p2 = wcm.translate('test[^chars]')
        if util.PY36:
            self.assertEqual(p1, r'(?s:test[\^chars])\Z')
            self.assertEqual(p2, r'(?s:)\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:test[\^chars])\Z')
            self.assertEqual(p2, r'(?ms)(?:)\Z')

        p1 = wcm.translate(r'test[^\-\&]')[0]
        if util.PY36:
            self.assertEqual(p1, r'(?s:test[\^\\-\\\&])\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:test[\^\\-\\\&])\Z')

        p1 = wcm.translate(r'\*\?\|\[\]')[0]
        if util.PY36:
            self.assertEqual(p1, r'(?s:\\.*\\.\\|\\[\\])\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:\\.*\\.\\|\\[\\])\Z')

        p1 = wcm.translate(r'\\u0300', wcm.RAW_STRING_ESCAPES)[0]
        if util.PY36:
            self.assertEqual(p1, r'(?s:\\u0300)\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:\\u0300)\Z')

        self.assertTrue(
            wcm.filter(['test\\m', 'test\\3', 'test\\a'], r'test\m', wcm.IGNORECASE),
            ['test\\m', 'test\\a']
        )

        self.assertTrue(wcm.fnmatch('test\test', r'test\test', wcm.IGNORECASE | wcm.RAW_STRING_ESCAPES))
        self.assertTrue(wcm.fnmatch('test\\test', r'test\test', wcm.IGNORECASE))
        self.assertTrue(wcm.fnmatch('test\\test', r'test\\test', wcm.IGNORECASE | wcm.RAW_STRING_ESCAPES))
        self.assertTrue(wcm.fnmatch('test\\\\test', r'test\\test', wcm.IGNORECASE))
        self.assertTrue(wcm.fnmatch('test\\m', r'test\m', wcm.IGNORECASE))
        self.assertTrue(wcm.fnmatch('test\\b', r'test\[a-z]', wcm.IGNORECASE))
        self.assertTrue(wcm.fnmatch('test\\b', r'test\\[a-z]', wcm.IGNORECASE | wcm.RAW_STRING_ESCAPES))
        self.assertTrue(wcm.fnmatch('test\\\\b', r'test\\[a-z]', wcm.IGNORECASE))
        self.assertTrue(wcm.fnmatch('[', '[[]', wcm.IGNORECASE))
        self.assertTrue(wcm.fnmatch('&', '[a&&b]', wcm.IGNORECASE))
        self.assertTrue(wcm.fnmatch('|', '[a||b]', wcm.IGNORECASE))
        self.assertTrue(wcm.fnmatch('~', '[a~~b]', wcm.IGNORECASE))
        self.assertTrue(wcm.fnmatch(',', '[a-z+--A-Z]', wcm.IGNORECASE))
        self.assertTrue(wcm.fnmatch('.', '[a-z--/A-Z]', wcm.IGNORECASE))

    def test_byte_wildcard_parsing(self):
        """Test byte_wildcard parsing."""

        p1, p2 = wcm.translate(b'*test[a-z]?|*test2[a-z]?|-test[!a-z]|-test[!-|a-z]')
        if util.PY36:
            self.assertEqual(p1, br'(?s:.*test[a-z].|.*test2[a-z].)\Z')
            self.assertEqual(p2, br'(?s:test[^a-z]|test[^\-\|a-z])\Z')
        else:
            self.assertEqual(p1, br'(?ms)(?:.*test[a-z].|.*test2[a-z].)\Z')
            self.assertEqual(p2, br'(?ms)(?:test[^a-z]|test[^\-\|a-z])\Z')

        p1, p2 = wcm.translate(b'test[]][!][][]')
        if util.PY36:
            self.assertEqual(p1, br'(?s:test[]][^][]\[\])\Z')
            self.assertEqual(p2, br'(?s:)\Z')
        else:
            self.assertEqual(p1, br'(?ms)(?:test[]][^][]\[\])\Z')
            self.assertEqual(p2, br'(?ms)(?:)\Z')

        p1, p2 = wcm.translate(b'test[!]')
        if util.PY36:
            self.assertEqual(p1, br'(?s:test\[\!\])\Z')
            self.assertEqual(p2, br'(?s:)\Z')
        else:
            self.assertEqual(p1, br'(?ms)(?:test\[\!\])\Z')
            self.assertEqual(p2, br'(?ms)(?:)\Z')

        p1, p2 = wcm.translate(b'|test|')
        if util.PY36:
            self.assertEqual(p1, br'(?s:|test|)\Z')
            self.assertEqual(p2, br'(?s:)\Z')
        else:
            self.assertEqual(p1, br'(?ms)(?:|test|)\Z')
            self.assertEqual(p2, br'(?ms)(?:)\Z')

        p1, p2 = wcm.translate(b'-|-test|-')
        if util.PY36:
            self.assertEqual(p1, br'(?s:.*)\Z')
            self.assertEqual(p2, br'(?s:|test|)\Z')
        else:
            self.assertEqual(p1, br'(?ms)(?:.*)\Z')
            self.assertEqual(p2, br'(?ms)(?:|test|)\Z')

        p1, p2 = wcm.translate(b'test[^chars]')
        if util.PY36:
            self.assertEqual(p1, br'(?s:test[\^chars])\Z')
            self.assertEqual(p2, br'(?s:)\Z')
        else:
            self.assertEqual(p1, br'(?ms)(?:test[\^chars])\Z')
            self.assertEqual(p2, br'(?ms)(?:)\Z')

        p1 = wcm.translate(br'test[^\-\&]')[0]
        if util.PY36:
            self.assertEqual(p1, br'(?s:test[\^\\-\\\&])\Z')
        else:
            self.assertEqual(p1, br'(?ms)(?:test[\^\\-\\\&])\Z')

        p1 = wcm.translate(br'\*\?\|\[\]')[0]
        if util.PY36:
            self.assertEqual(p1, br'(?s:\\.*\\.\\|\\[\\])\Z')
        else:
            self.assertEqual(p1, br'(?ms)(?:\\.*\\.\\|\\[\\])\Z')

        p1 = wcm.translate(br'\\u0300', wcm.RAW_STRING_ESCAPES)[0]
        if util.PY36:
            self.assertEqual(p1, br'(?s:\\u0300)\Z')
        else:
            self.assertEqual(p1, br'(?ms)(?:\\u0300)\Z')

        self.assertTrue(
            wcm.filter([b'test\\m', b'test\\3', b'test\\a'], br'test\m', wcm.IGNORECASE),
            [b'test\\m', b'test\\a']
        )

        self.assertTrue(wcm.fnmatch(b'test\test', br'test\test', wcm.IGNORECASE | wcm.RAW_STRING_ESCAPES))
        self.assertTrue(wcm.fnmatch(b'test\\test', br'test\test', wcm.IGNORECASE))
        self.assertTrue(wcm.fnmatch(b'test\\test', br'test\\test', wcm.IGNORECASE | wcm.RAW_STRING_ESCAPES))
        self.assertTrue(wcm.fnmatch(b'test\\\\test', br'test\\test', wcm.IGNORECASE))
        self.assertTrue(wcm.fnmatch(b'test\\m', br'test\m', wcm.IGNORECASE))
        self.assertTrue(wcm.fnmatch(b'test\\b', br'test\[a-z]', wcm.IGNORECASE))
        self.assertTrue(wcm.fnmatch(b'test\\b', br'test\\[a-z]', wcm.IGNORECASE | wcm.RAW_STRING_ESCAPES))
        self.assertTrue(wcm.fnmatch(b'test\\\\b', br'test\\[a-z]', wcm.IGNORECASE))
        self.assertTrue(wcm.fnmatch(b'[', b'[[]', wcm.IGNORECASE))
        self.assertTrue(wcm.fnmatch(b'&', b'[a&&b]', wcm.IGNORECASE))
        self.assertTrue(wcm.fnmatch(b'|', b'[a||b]', wcm.IGNORECASE))
        self.assertTrue(wcm.fnmatch(b'~', b'[a~~b]', wcm.IGNORECASE))
        self.assertTrue(wcm.fnmatch(b',', b'[a-z+--A-Z]', wcm.IGNORECASE))
        self.assertTrue(wcm.fnmatch(b'.', b'[a-z--/A-Z]', wcm.IGNORECASE))

    def test_wildcard_character_notation(self):
        """Test wildcard character notations."""

        p1, p2 = wcm.translate(r'test\x70\u0070\160\N{LATIN SMALL LETTER P}', wcm.RAW_STRING_ESCAPES)
        if util.PY36:
            self.assertEqual(p1, r'(?s:test\x70\u0070\160\160)\Z')
            self.assertEqual(p2, r'(?s:)\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:test\x70\u0070\160\160)\Z')
            self.assertEqual(p2, r'(?ms)(?:)\Z')

        p1, p2 = wcm.translate(r'test[\x70][\u0070][\160][\N{LATIN SMALL LETTER P}]', wcm.RAW_STRING_ESCAPES)
        if util.PY36:
            self.assertEqual(p1, r'(?s:test[\x70][\u0070][\160][\160])\Z')
            self.assertEqual(p2, r'(?s:)\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:test[\x70][\u0070][\160][\160])\Z')
            self.assertEqual(p2, r'(?ms)(?:)\Z')

        p1, p2 = wcm.translate(r'test\t\m', wcm.RAW_STRING_ESCAPES)
        if util.PY36:
            self.assertEqual(p1, r'(?s:test\t\\m)\Z')
            self.assertEqual(p2, r'(?s:)\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:test\t\\m)\Z')
            self.assertEqual(p2, r'(?ms)(?:)\Z')

        p1, p2 = wcm.translate(r'test[\]test', wcm.RAW_STRING_ESCAPES)
        if util.PY36:
            self.assertEqual(p1, r'(?s:test[\\]test)\Z')
            self.assertEqual(p2, r'(?s:)\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:test[\\]test)\Z')
            self.assertEqual(p2, r'(?ms)(?:)\Z')

        p1, p2 = wcm.translate('test[\\')
        if util.PY36:
            self.assertEqual(p1, r'(?s:test\[\\)\Z')
            self.assertEqual(p2, r'(?s:)\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:test\[\\)\Z')
            self.assertEqual(p2, r'(?ms)(?:)\Z')

        p1, p2 = wcm.translate(r'test\33test', wcm.RAW_STRING_ESCAPES)
        if util.PY36:
            self.assertEqual(p1, r'(?s:test\033test)\Z')
            self.assertEqual(p2, r'(?s:)\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:test\033test)\Z')
            self.assertEqual(p2, r'(?ms)(?:)\Z')

        p1, p2 = wcm.translate(r'test\33', wcm.RAW_STRING_ESCAPES)
        if util.PY36:
            self.assertEqual(p1, r'(?s:test\033)\Z')
            self.assertEqual(p2, r'(?s:)\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:test\033)\Z')
            self.assertEqual(p2, r'(?ms)(?:)\Z')

        p1, p2 = wcm.translate(r'test\400', wcm.RAW_STRING_ESCAPES)
        if util.PY36:
            self.assertEqual(p1, r'(?s:testĀ)\Z')
            self.assertEqual(p2, r'(?s:)\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:testĀ)\Z')
            self.assertEqual(p2, r'(?ms)(?:)\Z')

        with pytest.raises(SyntaxError):
            wcm.translate(r'test\N', wcm.RAW_STRING_ESCAPES)

        with pytest.raises(SyntaxError):
            wcm.translate(r'test\Nx', wcm.RAW_STRING_ESCAPES)

        with pytest.raises(SyntaxError):
            wcm.translate(r'test\N{', wcm.RAW_STRING_ESCAPES)


class TestDirWalker(unittest.TestCase):
    """Test the _DirWalker class."""

    def setUp(self):
        """Setup the tests."""

        self.default_flags = wcm.RAW_STRING_ESCAPES | wcm.IGNORECASE
        self.errors = []
        self.skipped = 0
        self.files = []

    def crawl_files(self, walker):
        """Crawl the files."""

        for f in walker.run():
            self.files.append(f)
        self.skipped = walker.get_skipped()

    def test_non_recursive(self):
        """Test non-recursive search."""

        walker = wcm.FnCrawl(
            'tests/dir_walker',
            '*.txt', None,
            False, False, self.default_flags,
            False, False
        )

        self.crawl_files(walker)

        self.assertEqual(self.skipped, 3)
        self.assertEqual(len(self.files), 1)
        self.assertEqual(os.path.basename(self.files[0]), 'a.txt')

    def test_non_recursive_inverse(self):
        """Test non-recursive inverse search."""

        walker = wcm.FnCrawl(
            'tests/dir_walker',
            '*.*|-*.file', None,
            False, False, self.default_flags,
            False, False
        )

        self.crawl_files(walker)

        self.assertEqual(self.skipped, 2)
        self.assertEqual(len(self.files), 2)

    def test_recursive(self):
        """Test non-recursive search."""

        walker = wcm.FnCrawl(
            'tests/dir_walker',
            '*.txt', None,
            True, False, self.default_flags,
            False, False
        )

        self.crawl_files(walker)

        self.assertEqual(self.skipped, 3)
        self.assertEqual(len(self.files), 1)
        self.assertEqual(os.path.basename(self.files[0]), 'a.txt')

    def test_recursive_hidden(self):
        """Test non-recursive search."""

        walker = wcm.FnCrawl(
            'tests/dir_walker',
            '*.txt', None,
            True, True, self.default_flags,
            False, False
        )

        self.crawl_files(walker)

        self.assertEqual(self.skipped, 4)
        self.assertEqual(len(self.files), 2)
        self.assertEqual(os.path.basename(sorted(self.files)[0]), 'a.txt')

    def test_recursive_hidden_folder_exclude(self):
        """Test non-recursive search."""

        walker = wcm.FnCrawl(
            'tests/dir_walker',
            '*.txt', '.hidden',
            True, True, self.default_flags,
            False, False
        )

        self.crawl_files(walker)

        self.assertEqual(self.skipped, 3)
        self.assertEqual(len(self.files), 1)
        self.assertEqual(os.path.basename(self.files[0]), 'a.txt')

    def test_recursive_hidden_folder_exclude_inverse(self):
        """Test non-recursive search with inverse."""

        walker = wcm.FnCrawl(
            'tests/dir_walker',
            '*.txt', '*|-.hidden',
            True, True, self.default_flags,
            False, False
        )

        self.crawl_files(walker)

        self.assertEqual(self.skipped, 4)
        self.assertEqual(len(self.files), 2)
        self.assertEqual(os.path.basename(sorted(self.files)[0]), 'a.txt')

    def test_recursive_hidden_re_folder_exclude(self):
        """Test non-recursive search."""

        walker = wcm.FnCrawl(
            'tests/dir_walker',
            '*.txt', r'\.hidden',
            True, True, self.default_flags,
            False, True
        )

        self.crawl_files(walker)

        self.assertEqual(len(self.errors), 0)
        self.assertEqual(self.skipped, 3)
        self.assertEqual(len(self.files), 1)
        self.assertEqual(os.path.basename(self.files[0]), 'a.txt')

    def test_abort(self):
        """Test aborting."""

        walker = wcm.FnCrawl(
            'tests/dir_walker',
            '*.txt', None,
            True, True, self.default_flags,
            False, False
        )

        records = 0
        for f in walker.run():
            records += 1
            walker.kill()

        self.assertEqual(records, 1)

    def test_abort_early(self):
        """Test aborting early."""

        walker = wcm.FnCrawl(
            'tests/dir_walker',
            '*.txt*', None,
            True, True, self.default_flags,
            False, False
        )

        walker.kill()
        records = 0
        for f in walker.run():
            records += 1

        self.assertTrue(records == 1 or walker.get_skipped() == 1)
