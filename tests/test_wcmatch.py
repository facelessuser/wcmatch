# -*- coding: utf-8 -*-
"""Tests for rumcore."""
from __future__ import unicode_literals
import unittest
import pytest
import os
import mock
import wcmatch as wcm
from wcmatch import util


class TestWildcard(unittest.TestCase):
    """Test wildcard pattern parsing."""

    @mock.patch('wcmatch.util.platform')
    @mock.patch('wcmatch.wcparse._is_case_sensitive')
    def test_wildcard_path_parsing_windows(self, mock__iscase_sensitive, mock_platform):
        """Test wildcard parsing."""

        mock_platform.return_value = "windows"
        mock__iscase_sensitive.return_value = False
        wcm._compile.cache_clear()

        self.assertTrue(
            wcm.fnmatch(
                'some/name/with/named/file/test.py', '**/named/file/*.py', wcm.P
            )
        )
        self.assertTrue(
            wcm.fnmatch(
                'some/name/with/na[/]med/file/test.py', '**/na[/]med/file/*.py', wcm.P
            )
        )
        self.assertTrue(
            wcm.fnmatch(
                'some/name/with/na[/]med\\/file/test.py', '**/na[/]med\\/file/*.py', wcm.P
            )
        )
        self.assertTrue(
            wcm.fnmatch(
                'some/name/with/na[\\]med/file/test.py', r'**/na[\]med/file/*.py', wcm.P | wcm.R
            )
        )
        self.assertTrue(
            wcm.fnmatch(
                'some\\name\\with\\na[\\]med\\file\\test.py', r'**/na[\]med/file/*.py', wcm.P | wcm.R
            )
        )
        self.assertTrue(
            wcm.fnmatch(
                'some\\name\\with\\na[\\]med\\file\\test.py', r'**\\na[\]med\\file\*.py', wcm.P | wcm.R
            )
        )
        self.assertTrue(
            wcm.fnmatch(
                'some\\name\\with\\na[\\]med\\file\\test.py', r'**\\na[\\]m\ed\\file\\*.py', wcm.P | wcm.R | wcm.E
            )
        )
        self.assertTrue(
            wcm.fnmatch(
                'some\\name\\with\\na[\\]med\\\\file\\test.py', r'**\\na[\\]m\ed\\/file\\*.py', wcm.P | wcm.R | wcm.E
            )
        )
        self.assertTrue(
            wcm.fnmatch(
                'some\\name\\with\\na[\\\\]med\\\\file\\test.py', r'**\\na[\/]m\ed\/file\\*.py', wcm.P | wcm.R | wcm.E
            )
        )

    @mock.patch('wcmatch.util.platform')
    @mock.patch('wcmatch.wcparse._is_case_sensitive')
    def test_wildcard_path_parsing(self, mock__iscase_sensitive, mock_platform):
        """Test wildcard parsing."""

        mock_platform.return_value = "linux"
        mock__iscase_sensitive.return_value = True
        wcm._compile.cache_clear()

        self.assertTrue(
            wcm.fnmatch(
                'some/name/with/named/file/test.py', '**/named/file/*.py', wcm.P
            )
        )
        self.assertTrue(
            wcm.fnmatch(
                'some/name/with/na[/]med/file/test.py', '**/na[/]med/file/*.py', wcm.P
            )
        )
        self.assertTrue(
            wcm.fnmatch(
                'some/name/with/na[/]med\\/file/test.py', '**/na[/]med\\/file/*.py', wcm.P
            )
        )
        self.assertTrue(
            wcm.fnmatch(
                'some/name/with/na\\med/file/test.py', r'**/na[\]med/file/*.py', wcm.P | wcm.R
            )
        )
        self.assertTrue(
            wcm.fnmatch(
                'some/name/with/na[\\/]med\\/file/test.py', r'**/na[\/]med\/file/*.py', wcm.P | wcm.R
            )
        )

    def test_wildcard_parsing(self):
        """Test wildcard parsing."""

        wcm._compile.cache_clear()

        p1, p2 = wcm.translate('*test[a-z]?|*test2[a-z]?|-test[!a-z]|-test[!-|a-z]', wcm.F)
        if util.PY36:
            self.assertEqual(p1, r'(?s:.*test[a-z].|.*test2[a-z].)\Z')
            self.assertEqual(p2, r'(?s:test[^a-z]|test[^\-\|a-z])\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:.*test[a-z].|.*test2[a-z].)\Z')
            self.assertEqual(p2, r'(?ms)(?:test[^a-z]|test[^\-\|a-z])\Z')

        p1, p2 = wcm.translate('test[]][!][][]', wcm.F)
        if util.PY36:
            self.assertEqual(p1, r'(?s:test[]][^][]\[\])\Z')
            self.assertEqual(p2, r'(?s:)\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:test[]][^][]\[\])\Z')
            self.assertEqual(p2, r'(?ms)(?:)\Z')

        p1, p2 = wcm.translate('test[!]', wcm.F)
        if util.PY36:
            self.assertEqual(p1, r'(?s:test\[\!\])\Z')
            self.assertEqual(p2, r'(?s:)\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:test\[\!\])\Z')
            self.assertEqual(p2, r'(?ms)(?:)\Z')

        p1, p2 = wcm.translate('|test|', wcm.F)
        if util.PY36:
            self.assertEqual(p1, r'(?s:|test|)\Z')
            self.assertEqual(p2, r'(?s:)\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:|test|)\Z')
            self.assertEqual(p2, r'(?ms)(?:)\Z')

        p1, p2 = wcm.translate('-|-test|-', wcm.F)
        if util.PY36:
            self.assertEqual(p1, r'(?s:.*)\Z')
            self.assertEqual(p2, r'(?s:|test|)\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:.*)\Z')
            self.assertEqual(p2, r'(?ms)(?:|test|)\Z')

        p1, p2 = wcm.translate('test[^chars]', wcm.F)
        if util.PY36:
            self.assertEqual(p1, r'(?s:test[\^chars])\Z')
            self.assertEqual(p2, r'(?s:)\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:test[\^chars])\Z')
            self.assertEqual(p2, r'(?ms)(?:)\Z')

        p1 = wcm.translate(r'test[^\-\&]', wcm.F)[0]
        if util.PY36:
            self.assertEqual(p1, r'(?s:test[\^\\-\\\&])\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:test[\^\\-\\\&])\Z')

        p1 = wcm.translate(r'\*\?\|\[\]', wcm.F)[0]
        if util.PY36:
            self.assertEqual(p1, r'(?s:\\.*\\.\\|\\[\\])\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:\\.*\\.\\|\\[\\])\Z')

        p1 = wcm.translate(r'\\u0300', wcm.F | wcm.R)[0]
        if util.PY36:
            self.assertEqual(p1, r'(?s:\\u0300)\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:\\u0300)\Z')

        self.assertTrue(
            wcm.filter(['test\\m', 'test\\3', 'test\\a'], r'test\m', wcm.I),
            ['test\\m', 'test\\a']
        )

        self.assertTrue(wcm.fnmatch('test\test', r'test\test', wcm.R))
        self.assertTrue(wcm.fnmatch('test\\test', r'test\test'))
        self.assertTrue(wcm.fnmatch('test\\test', r'test\\test', wcm.R))
        self.assertTrue(wcm.fnmatch('test\\\\test', r'test\\test'))
        self.assertTrue(wcm.fnmatch('test\\m', r'test\m'))
        self.assertTrue(wcm.fnmatch('test\\b', r'test\[a-z]'))
        self.assertTrue(wcm.fnmatch('test\\b', r'test\\[a-z]', wcm.R))
        self.assertTrue(wcm.fnmatch('test\\\\b', r'test\\[a-z]'))
        self.assertTrue(wcm.fnmatch('[', '[[]'))
        self.assertTrue(wcm.fnmatch('&', '[a&&b]'))
        self.assertTrue(wcm.fnmatch('|', '[a||b]'))
        self.assertTrue(wcm.fnmatch('~', '[a~~b]'))
        self.assertTrue(wcm.fnmatch(',', '[a-z+--A-Z]'))
        self.assertTrue(wcm.fnmatch('.', '[a-z--/A-Z]'))

    def test_byte_wildcard_parsing(self):
        """Test byte_wildcard parsing."""

        wcm._compile.cache_clear()

        p1, p2 = wcm.translate(b'*test[a-z]?|*test2[a-z]?|-test[!a-z]|-test[!-|a-z]', wcm.F)
        if util.PY36:
            self.assertEqual(p1, br'(?s:.*test[a-z].|.*test2[a-z].)\Z')
            self.assertEqual(p2, br'(?s:test[^a-z]|test[^\-\|a-z])\Z')
        else:
            self.assertEqual(p1, br'(?ms)(?:.*test[a-z].|.*test2[a-z].)\Z')
            self.assertEqual(p2, br'(?ms)(?:test[^a-z]|test[^\-\|a-z])\Z')

        p1, p2 = wcm.translate(b'test[]][!][][]', wcm.F)
        if util.PY36:
            self.assertEqual(p1, br'(?s:test[]][^][]\[\])\Z')
            self.assertEqual(p2, br'(?s:)\Z')
        else:
            self.assertEqual(p1, br'(?ms)(?:test[]][^][]\[\])\Z')
            self.assertEqual(p2, br'(?ms)(?:)\Z')

        p1, p2 = wcm.translate(b'test[!]', wcm.F)
        if util.PY36:
            self.assertEqual(p1, br'(?s:test\[\!\])\Z')
            self.assertEqual(p2, br'(?s:)\Z')
        else:
            self.assertEqual(p1, br'(?ms)(?:test\[\!\])\Z')
            self.assertEqual(p2, br'(?ms)(?:)\Z')

        p1, p2 = wcm.translate(b'|test|', wcm.F)
        if util.PY36:
            self.assertEqual(p1, br'(?s:|test|)\Z')
            self.assertEqual(p2, br'(?s:)\Z')
        else:
            self.assertEqual(p1, br'(?ms)(?:|test|)\Z')
            self.assertEqual(p2, br'(?ms)(?:)\Z')

        p1, p2 = wcm.translate(b'-|-test|-', wcm.F)
        if util.PY36:
            self.assertEqual(p1, br'(?s:.*)\Z')
            self.assertEqual(p2, br'(?s:|test|)\Z')
        else:
            self.assertEqual(p1, br'(?ms)(?:.*)\Z')
            self.assertEqual(p2, br'(?ms)(?:|test|)\Z')

        p1, p2 = wcm.translate(b'test[^chars]', wcm.F)
        if util.PY36:
            self.assertEqual(p1, br'(?s:test[\^chars])\Z')
            self.assertEqual(p2, br'(?s:)\Z')
        else:
            self.assertEqual(p1, br'(?ms)(?:test[\^chars])\Z')
            self.assertEqual(p2, br'(?ms)(?:)\Z')

        p1 = wcm.translate(br'test[^\-\&]', wcm.F)[0]
        if util.PY36:
            self.assertEqual(p1, br'(?s:test[\^\\-\\\&])\Z')
        else:
            self.assertEqual(p1, br'(?ms)(?:test[\^\\-\\\&])\Z')

        p1 = wcm.translate(br'\*\?\|\[\]', wcm.F)[0]
        if util.PY36:
            self.assertEqual(p1, br'(?s:\\.*\\.\\|\\[\\])\Z')
        else:
            self.assertEqual(p1, br'(?ms)(?:\\.*\\.\\|\\[\\])\Z')

        p1 = wcm.translate(br'\\u0300', wcm.F | wcm.R)[0]
        if util.PY36:
            self.assertEqual(p1, br'(?s:\\u0300)\Z')
        else:
            self.assertEqual(p1, br'(?ms)(?:\\u0300)\Z')

        self.assertTrue(
            wcm.filter([b'test\\m', b'test\\3', b'test\\a'], br'test\m'),
            [b'test\\m', b'test\\a']
        )

        self.assertTrue(wcm.fnmatch(b'test\test', br'test\test', wcm.R))
        self.assertTrue(wcm.fnmatch(b'test\\test', br'test\test'))
        self.assertTrue(wcm.fnmatch(b'test\\test', br'test\\test', wcm.R))
        self.assertTrue(wcm.fnmatch(b'test\\\\test', br'test\\test'))
        self.assertTrue(wcm.fnmatch(b'test\\m', br'test\m'))
        self.assertTrue(wcm.fnmatch(b'test\\b', br'test\[a-z]'))
        self.assertTrue(wcm.fnmatch(b'test\\b', br'test\\[a-z]', wcm.R))
        self.assertTrue(wcm.fnmatch(b'test\\\\b', br'test\\[a-z]'))
        self.assertTrue(wcm.fnmatch(b'[', b'[[]'))
        self.assertTrue(wcm.fnmatch(b'&', b'[a&&b]'))
        self.assertTrue(wcm.fnmatch(b'|', b'[a||b]'))
        self.assertTrue(wcm.fnmatch(b'~', b'[a~~b]'))
        self.assertTrue(wcm.fnmatch(b',', b'[a-z+--A-Z]'))
        self.assertTrue(wcm.fnmatch(b'.', b'[a-z--/A-Z]'))

    def test_wildcard_character_notation(self):
        """Test wildcard character notations."""

        wcm._compile.cache_clear()

        p1, p2 = wcm.translate(r'test\x70\u0070\U00000070\160\N{LATIN SMALL LETTER P}', wcm.F | wcm.R)
        if util.PY36:
            self.assertEqual(p1, r'(?s:test\160\160\160\160\160)\Z')
            self.assertEqual(p2, r'(?s:)\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:test\160\160\160\160\160)\Z')
            self.assertEqual(p2, r'(?ms)(?:)\Z')

        p1, p2 = wcm.translate(r'test[\x70][\u0070][\U00000070][\160][\N{LATIN SMALL LETTER P}]', wcm.F | wcm.R)
        if util.PY36:
            self.assertEqual(p1, r'(?s:test[\160][\160][\160][\160][\160])\Z')
            self.assertEqual(p2, r'(?s:)\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:test[\160][\160][\160][\160][\160])\Z')
            self.assertEqual(p2, r'(?ms)(?:)\Z')

        p1, p2 = wcm.translate(r'test\t\m', wcm.F | wcm.R)
        if util.PY36:
            self.assertEqual(p1, r'(?s:test\t\\m)\Z')
            self.assertEqual(p2, r'(?s:)\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:test\t\\m)\Z')
            self.assertEqual(p2, r'(?ms)(?:)\Z')

        p1, p2 = wcm.translate(r'test[\]test', wcm.F | wcm.R)
        if util.PY36:
            self.assertEqual(p1, r'(?s:test[\\]test)\Z')
            self.assertEqual(p2, r'(?s:)\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:test[\\]test)\Z')
            self.assertEqual(p2, r'(?ms)(?:)\Z')

        p1, p2 = wcm.translate('test[\\', wcm.F)
        if util.PY36:
            self.assertEqual(p1, r'(?s:test\[\\)\Z')
            self.assertEqual(p2, r'(?s:)\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:test\[\\)\Z')
            self.assertEqual(p2, r'(?ms)(?:)\Z')

        p1, p2 = wcm.translate(r'test\33test', wcm.F | wcm.R)
        if util.PY36:
            self.assertEqual(p1, r'(?s:test\033test)\Z')
            self.assertEqual(p2, r'(?s:)\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:test\033test)\Z')
            self.assertEqual(p2, r'(?ms)(?:)\Z')

        p1, p2 = wcm.translate(r'test\33', wcm.F | wcm.R)
        if util.PY36:
            self.assertEqual(p1, r'(?s:test\033)\Z')
            self.assertEqual(p2, r'(?s:)\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:test\033)\Z')
            self.assertEqual(p2, r'(?ms)(?:)\Z')

        p1, p2 = wcm.translate(r'test\400', wcm.F | wcm.R)
        if util.PY36:
            self.assertEqual(p1, r'(?s:testĀ)\Z')
            self.assertEqual(p2, r'(?s:)\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:testĀ)\Z')
            self.assertEqual(p2, r'(?ms)(?:)\Z')

        with pytest.raises(SyntaxError):
            wcm.translate(r'test\N', wcm.R)

        with pytest.raises(SyntaxError):
            wcm.translate(r'test\Nx', wcm.R)

        with pytest.raises(SyntaxError):
            wcm.translate(r'test\N{', wcm.R)


class TestDirWalker(unittest.TestCase):
    """Test the _DirWalker class."""

    def setUp(self):
        """Setup the tests."""

        self.default_flags = wcm.R | wcm.I
        self.errors = []
        self.skipped = 0
        self.files = []

    def crawl_files(self, walker):
        """Crawl the files."""

        for f in walker.match():
            self.files.append(f)
        self.skipped = walker.get_skipped()

    def test_non_recursive(self):
        """Test non-recursive search."""

        walker = wcm.FnCrawl(
            'tests/dir_walker',
            '*.txt', None,
            False, False, self.default_flags
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
            False, False, self.default_flags
        )

        self.crawl_files(walker)

        self.assertEqual(self.skipped, 2)
        self.assertEqual(len(self.files), 2)

    def test_recursive(self):
        """Test non-recursive search."""

        walker = wcm.FnCrawl(
            'tests/dir_walker',
            '*.txt', None,
            True, False, self.default_flags
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
            True, True, self.default_flags
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
            True, True, self.default_flags
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
            True, True, self.default_flags
        )

        self.crawl_files(walker)

        self.assertEqual(self.skipped, 4)
        self.assertEqual(len(self.files), 2)
        self.assertEqual(os.path.basename(sorted(self.files)[0]), 'a.txt')

    def test_abort(self):
        """Test aborting."""

        walker = wcm.FnCrawl(
            'tests/dir_walker',
            '*.txt', None,
            True, True, self.default_flags
        )

        records = 0
        for f in walker.imatch():
            records += 1
            walker.kill()

        self.assertEqual(records, 1)

    def test_abort_early(self):
        """Test aborting early."""

        walker = wcm.FnCrawl(
            'tests/dir_walker',
            '*.txt*', None,
            True, True, self.default_flags
        )

        walker.kill()
        records = 0
        for f in walker.imatch():
            records += 1

        self.assertTrue(records == 1 or walker.get_skipped() == 1)
