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
                'some/name/with/named/file/test.py', '**/named/file/*.py', wcm.P | wcm.G
            )
        )
        self.assertTrue(
            wcm.fnmatch(
                'some/name/with/na[/]med/file/test.py', '**/na[/]med/file/*.py', wcm.P | wcm.G
            )
        )
        self.assertTrue(
            wcm.fnmatch(
                'some/name/with/na[/]med\\/file/test.py', '**/na[/]med\\/file/*.py', wcm.P | wcm.G
            )
        )
        self.assertTrue(
            wcm.fnmatch(
                'some/name/with/na[\\]med/file/test.py', r'**/na[\\]med/file/*.py', wcm.P | wcm.C | wcm.G
            )
        )
        self.assertTrue(
            wcm.fnmatch(
                'some\\name\\with\\na[\\]med\\file\\test.py', r'**/na[\\]med/file/*.py', wcm.P | wcm.C | wcm.G
            )
        )
        self.assertTrue(
            wcm.fnmatch(
                'some\\name\\with\\na[\\]med\\file*.py', r'**\\na[\\]med\\file\*.py', wcm.P | wcm.C | wcm.G
            )
        )
        self.assertTrue(
            wcm.fnmatch(
                'some\\name\\with\\na[\\]med\\file\\test.py', r'**\\na[\\]m\ed\\file\\*.py', wcm.P | wcm.C | wcm.G
            )
        )
        self.assertTrue(
            wcm.fnmatch(
                'some\\name\\with\\na[\\]med\\\\file\\test.py', r'**\\na[\\]m\ed\\/file\\*.py', wcm.P | wcm.C | wcm.G
            )
        )
        self.assertTrue(
            wcm.fnmatch(
                'some\\name\\with\\na[\\\\]med\\\\file\\test.py', r'**\\na[\/]m\ed\/file\\*.py', wcm.P | wcm.C | wcm.G
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
                'some/name/with/named/file/test.py', '**/named/file/*.py', wcm.P | wcm.G
            )
        )
        self.assertTrue(
            wcm.fnmatch(
                'some/name/with/na[/]med/file/test.py', '**/na[/]med/file/*.py', wcm.P | wcm.G
            )
        )
        self.assertTrue(
            wcm.fnmatch(
                'some/name/with/na[/]med\\/file/test.py', '**/na[/]med\\/file/*.py', wcm.P | wcm.G
            )
        )
        self.assertTrue(
            wcm.fnmatch(
                'some/name/with/na\\med/file/test.py', r'**/na[\\]med/file/*.py', wcm.P | wcm.C | wcm.G
            )
        )
        self.assertTrue(
            wcm.fnmatch(
                'some/name/with/na[\\/]med\\/file/test.py', r'**/na[\/]med\/file/*.py', wcm.P | wcm.C | wcm.G
            )
        )

    @mock.patch('wcmatch.wcparse._is_case_sensitive')
    def test_wildcard_parsing(self, mock__iscase_sensitive):
        """Test wildcard parsing."""

        mock__iscase_sensitive.return_value = True

        wcm._compile.cache_clear()

        p1, p2 = wcm.translate(wcm.split('*test[a-z]?|*test2[a-z]?|-test[!a-z]|-test[!-|a-z]'))
        if util.PY36:
            self.assertEqual(p1, r'(?s:.*?test[a-z].|.*?test2[a-z].)\Z')
            self.assertEqual(p2, r'(?s:test[^a-z]|test[^\-\|a-z])\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:.*?test[a-z].|.*?test2[a-z].)\Z')
            self.assertEqual(p2, r'(?ms)(?:test[^a-z]|test[^\-\|a-z])\Z')

        p1, p2 = wcm.translate(wcm.split('test[]][!][][]', wcm.F), wcm.F)
        if util.PY36:
            self.assertEqual(p1, r'(?s:test[\]][^\][]\[\])\Z')
            self.assertEqual(p2, r'(?s:)\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:test[\]][^\][]\[\])\Z')
            self.assertEqual(p2, r'(?ms)(?:)\Z')

        p1, p2 = wcm.translate(wcm.split('test[!]'))
        if util.PY36:
            self.assertEqual(p1, r'(?s:test\[\!\])\Z')
            self.assertEqual(p2, r'(?s:)\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:test\[\!\])\Z')
            self.assertEqual(p2, r'(?ms)(?:)\Z')

        p1, p2 = wcm.translate(wcm.split('|test|'))
        if util.PY36:
            self.assertEqual(p1, r'(?s:|test|)\Z')
            self.assertEqual(p2, r'(?s:)\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:|test|)\Z')
            self.assertEqual(p2, r'(?ms)(?:)\Z')

        p1, p2 = wcm.translate(wcm.split('-|-test|-'))
        if util.PY36:
            self.assertEqual(p1, r'(?s:.*?)\Z')
            self.assertEqual(p2, r'(?s:|test|)\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:.*?)\Z')
            self.assertEqual(p2, r'(?ms)(?:|test|)\Z')

        p1, p2 = wcm.translate(wcm.split('test[^chars]'))
        if util.PY36:
            self.assertEqual(p1, r'(?s:test[\^chars])\Z')
            self.assertEqual(p2, r'(?s:)\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:test[\^chars])\Z')
            self.assertEqual(p2, r'(?ms)(?:)\Z')

        p1 = wcm.translate(wcm.split(r'test[^\\-\\&]'))[0]
        if util.PY36:
            self.assertEqual(p1, r'(?s:test[\^\\-\\\&])\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:test[\^\\-\\\&])\Z')

        # BROKEN
        p1 = wcm.translate(wcm.split(r'\\*\\?\\|\\[\\]'))[0]
        if util.PY36:
            self.assertEqual(p1, r'(?s:\\.*?\\.\\|\\[\\])\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:\\.*?\\.\\|\\[\\])\Z')

        p1 = wcm.translate(wcm.split(r'\\u0300', wcm.C), wcm.C)[0]
        if util.PY36:
            self.assertEqual(p1, r'(?s:\\u0300)\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:\\u0300)\Z')

        self.assertEqual(
            wcm.filter(['testm', 'test\\3', 'testa'], wcm.split(r'te\st[ma]')),
            ['testm', 'testa']
        )

        self.assertTrue(wcm.fnmatch('test\test', r'test\test', wcm.C))
        self.assertTrue(wcm.fnmatch('testtest', r'test\test'))
        self.assertTrue(wcm.fnmatch('test\\test', r'test\\test', wcm.C))
        self.assertTrue(wcm.fnmatch('test\\test', r'test\\test'))
        self.assertTrue(wcm.fnmatch('test\\m', r'test\\m'))
        self.assertTrue(wcm.fnmatch('test\\b', r'test\\[a-z]'))
        self.assertTrue(wcm.fnmatch('test\\b', r'test\\[a-z]', wcm.C))
        self.assertTrue(wcm.fnmatch('test\\b', r'test\\[a-z]'))
        self.assertTrue(wcm.fnmatch('[', '[[]'))
        self.assertTrue(wcm.fnmatch('&', '[a&&b]'))
        self.assertTrue(wcm.fnmatch('|', '[a||b]'))
        self.assertTrue(wcm.fnmatch('~', '[a~~b]'))
        self.assertTrue(wcm.fnmatch(',', '[a-z+--A-Z]'))
        self.assertTrue(wcm.fnmatch('.', '[a-z--/A-Z]'))

    @mock.patch('wcmatch.wcparse._is_case_sensitive')
    def test_byte_wildcard_parsing(self, mock__iscase_sensitive):
        """Test byte_wildcard parsing."""

        mock__iscase_sensitive.return_value = True

        wcm._compile.cache_clear()

        p1, p2 = wcm.translate(wcm.split(b'*test[a-z]?|*test2[a-z]?|-test[!a-z]|-test[!-|a-z]'))
        if util.PY36:
            self.assertEqual(p1, br'(?s:.*?test[a-z].|.*?test2[a-z].)\Z')
            self.assertEqual(p2, br'(?s:test[^a-z]|test[^\-\|a-z])\Z')
        else:
            self.assertEqual(p1, br'(?ms)(?:.*?test[a-z].|.*?test2[a-z].)\Z')
            self.assertEqual(p2, br'(?ms)(?:test[^a-z]|test[^\-\|a-z])\Z')

        p1, p2 = wcm.translate(wcm.split(b'test[]][!][][]'))
        if util.PY36:
            self.assertEqual(p1, br'(?s:test[\]][^\][]\[\])\Z')
            self.assertEqual(p2, br'(?s:)\Z')
        else:
            self.assertEqual(p1, br'(?ms)(?:test[\]][^\][]\[\])\Z')
            self.assertEqual(p2, br'(?ms)(?:)\Z')

        p1, p2 = wcm.translate(wcm.split(b'test[!]'))
        if util.PY36:
            self.assertEqual(p1, br'(?s:test\[\!\])\Z')
            self.assertEqual(p2, br'(?s:)\Z')
        else:
            self.assertEqual(p1, br'(?ms)(?:test\[\!\])\Z')
            self.assertEqual(p2, br'(?ms)(?:)\Z')

        p1, p2 = wcm.translate(wcm.split(b'|test|'))
        if util.PY36:
            self.assertEqual(p1, br'(?s:|test|)\Z')
            self.assertEqual(p2, br'(?s:)\Z')
        else:
            self.assertEqual(p1, br'(?ms)(?:|test|)\Z')
            self.assertEqual(p2, br'(?ms)(?:)\Z')

        p1, p2 = wcm.translate(wcm.split(b'-|-test|-'))
        if util.PY36:
            self.assertEqual(p1, br'(?s:.*?)\Z')
            self.assertEqual(p2, br'(?s:|test|)\Z')
        else:
            self.assertEqual(p1, br'(?ms)(?:.*?)\Z')
            self.assertEqual(p2, br'(?ms)(?:|test|)\Z')

        p1, p2 = wcm.translate(wcm.split(b'test[^chars]'))
        if util.PY36:
            self.assertEqual(p1, br'(?s:test[\^chars])\Z')
            self.assertEqual(p2, br'(?s:)\Z')
        else:
            self.assertEqual(p1, br'(?ms)(?:test[\^chars])\Z')
            self.assertEqual(p2, br'(?ms)(?:)\Z')

        p1 = wcm.translate(wcm.split(br'test[^\\-\\&]'))[0]
        if util.PY36:
            self.assertEqual(p1, br'(?s:test[\^\\-\\\&])\Z')
        else:
            self.assertEqual(p1, br'(?ms)(?:test[\^\\-\\\&])\Z')

        # BROKEN
        p1 = wcm.translate(wcm.split(br'\\*\\?\\|\\[\\]'))[0]
        if util.PY36:
            self.assertEqual(p1, br'(?s:\\.*?\\.\\|\\[\\])\Z')
        else:
            self.assertEqual(p1, br'(?ms)(?:\\.*?\\.\\|\\[\\])\Z')

        p1 = wcm.translate(wcm.split(br'\\u0300'), wcm.C)[0]
        if util.PY36:
            self.assertEqual(p1, br'(?s:\\u0300)\Z')
        else:
            self.assertEqual(p1, br'(?ms)(?:\\u0300)\Z')

        self.assertEqual(
            wcm.filter([b'testm', b'test\\3', b'testa'], wcm.split(br'te\st[ma]')),
            [b'testm', b'testa']
        )

        self.assertTrue(wcm.fnmatch(b'test\test', br'test\test', wcm.C))
        self.assertTrue(wcm.fnmatch(b'testtest', br'test\test'))
        self.assertTrue(wcm.fnmatch(b'test\\test', br'test\\test', wcm.C))
        self.assertTrue(wcm.fnmatch(b'test\\test', br'test\\test'))
        self.assertTrue(wcm.fnmatch(b'test\\m', br'test\\m'))
        self.assertTrue(wcm.fnmatch(b'test\\b', br'test\\[a-z]'))
        self.assertTrue(wcm.fnmatch(b'test\\b', br'test\\[a-z]', wcm.C))
        self.assertTrue(wcm.fnmatch(b'test\\b', br'test\\[a-z]'))
        self.assertTrue(wcm.fnmatch(b'[', b'[[]'))
        self.assertTrue(wcm.fnmatch(b'&', b'[a&&b]'))
        self.assertTrue(wcm.fnmatch(b'|', b'[a||b]'))
        self.assertTrue(wcm.fnmatch(b'~', b'[a~~b]'))
        self.assertTrue(wcm.fnmatch(b',', b'[a-z+--A-Z]'))
        self.assertTrue(wcm.fnmatch(b'.', b'[a-z--/A-Z]'))

    @mock.patch('wcmatch.wcparse._is_case_sensitive')
    def test_wildcard_character_notation(self, mock__iscase_sensitive):
        """Test wildcard character notations."""

        mock__iscase_sensitive.return_value = True

        wcm._compile.cache_clear()

        p1, p2 = wcm.translate(r'test\x70\u0070\U00000070\160\N{LATIN SMALL LETTER P}', wcm.C)
        if util.PY36:
            self.assertEqual(p1, r'(?s:testppppp)\Z')
            self.assertEqual(p2, r'(?s:)\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:testppppp)\Z')
            self.assertEqual(p2, r'(?ms)(?:)\Z')

        p1, p2 = wcm.translate(r'test[\x70][\u0070][\U00000070][\160][\N{LATIN SMALL LETTER P}]', wcm.C)
        if util.PY36:
            self.assertEqual(p1, r'(?s:test[p][p][p][p][p])\Z')
            self.assertEqual(p2, r'(?s:)\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:test[p][p][p][p][p])\Z')
            self.assertEqual(p2, r'(?ms)(?:)\Z')

        p1, p2 = wcm.translate(r'test\t\m', wcm.C)
        if util.PY36:
            self.assertEqual(p1, r'(?s:test\	m)\Z')
            self.assertEqual(p2, r'(?s:)\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:test\	m)\Z')
            self.assertEqual(p2, r'(?ms)(?:)\Z')

        p1, p2 = wcm.translate(r'test[\\]test', wcm.C)
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

        p1, p2 = wcm.translate(r'test\44test', wcm.C)
        if util.PY36:
            self.assertEqual(p1, r'(?s:test\$test)\Z')
            self.assertEqual(p2, r'(?s:)\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:test\$test)\Z')
            self.assertEqual(p2, r'(?ms)(?:)\Z')

        p1, p2 = wcm.translate(r'test\44', wcm.C)
        if util.PY36:
            self.assertEqual(p1, r'(?s:test\$)\Z')
            self.assertEqual(p2, r'(?s:)\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:test\$)\Z')
            self.assertEqual(p2, r'(?ms)(?:)\Z')

        p1, p2 = wcm.translate(r'test\400', wcm.C)
        if util.PY36:
            self.assertEqual(p1, r'(?s:test\Ā)\Z')
            self.assertEqual(p2, r'(?s:)\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:test\Ā)\Z')
            self.assertEqual(p2, r'(?ms)(?:)\Z')

        with pytest.raises(SyntaxError):
            wcm.translate(r'test\N', wcm.C)

        with pytest.raises(SyntaxError):
            wcm.translate(r'test\Nx', wcm.C)

        with pytest.raises(SyntaxError):
            wcm.translate(r'test\N{', wcm.C)


class TestDirWalker(unittest.TestCase):
    """Test the _DirWalker class."""

    def setUp(self):
        """Setup the tests."""

        self.default_flags = wcm.C | wcm.I
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
            wcm.split('*.*|-*.file', self.default_flags), None,
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
