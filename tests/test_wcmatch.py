# -*- coding: utf-8 -*-
"""Tests for rumcore."""
import unittest
import pytest
import os
import mock
import wcmatch.fnmatch as fnmatch
import wcmatch.wcfind as wcfind
from wcmatch import util


class TestWildcard(unittest.TestCase):
    """Test wildcard pattern parsing."""

    @mock.patch('wcmatch.util.platform')
    @mock.patch('wcmatch.util.is_case_sensitive')
    def test_wildcard_path_parsing_windows(self, mock__iscase_sensitive, mock_platform):
        """Test wildcard parsing."""

        mock_platform.return_value = "windows"
        mock__iscase_sensitive.return_value = False
        fnmatch._compile.cache_clear()

        self.assertTrue(
            fnmatch.fnmatch(
                'some/name/with/named/file/test.py',
                '**/named/file/*.py',
                fnmatch.P | fnmatch.G
            )
        )
        self.assertTrue(
            fnmatch.fnmatch(
                'some/name/with/na[/]med/file/test.py',
                '**/na[/]med/file/*.py',
                fnmatch.P | fnmatch.G
            )
        )
        self.assertTrue(
            fnmatch.fnmatch(
                'some/name/with/na[/]med\\/file/test.py',
                '**/na[/]med\\/file/*.py',
                fnmatch.P | fnmatch.G
            )
        )
        self.assertTrue(
            fnmatch.fnmatch(
                'some/name/with/na[\\]med/file/test.py',
                r'**/na[\\]med/file/*.py', fnmatch.P | fnmatch.R | fnmatch.G
            )
        )
        self.assertTrue(
            fnmatch.fnmatch(
                'some\\name\\with\\na[\\]med\\file\\test.py',
                r'**/na[\\]med/file/*.py',
                fnmatch.P | fnmatch.R | fnmatch.G
            )
        )
        self.assertTrue(
            fnmatch.fnmatch(
                'some\\name\\with\\na[\\]med\\file*.py',
                r'**\\na[\\]med\\file\*.py',
                fnmatch.P | fnmatch.R | fnmatch.G
            )
        )
        self.assertTrue(
            fnmatch.fnmatch(
                'some\\name\\with\\na[\\]med\\file\\test.py',
                r'**\\na[\\]m\ed\\file\\*.py',
                fnmatch.P | fnmatch.R | fnmatch.G
            )
        )
        self.assertTrue(
            fnmatch.fnmatch(
                'some\\name\\with\\na[\\]med\\\\file\\test.py',
                r'**\\na[\\]m\ed\\/file\\*.py',
                fnmatch.P | fnmatch.R | fnmatch.G
            )
        )
        self.assertTrue(
            fnmatch.fnmatch(
                'some\\name\\with\\na[\\\\]med\\\\file\\test.py',
                r'**\\na[\/]m\ed\/file\\*.py',
                fnmatch.P | fnmatch.R | fnmatch.G
            )
        )

    @mock.patch('wcmatch.util.platform')
    @mock.patch('wcmatch.util.is_case_sensitive')
    def test_wildcard_path_parsing(self, mock__iscase_sensitive, mock_platform):
        """Test wildcard parsing."""

        mock_platform.return_value = "linux"
        mock__iscase_sensitive.return_value = True
        fnmatch._compile.cache_clear()

        self.assertTrue(
            fnmatch.fnmatch(
                'some/name/with/named/file/test.py',
                '**/named/file/*.py',
                fnmatch.P | fnmatch.G
            )
        )
        self.assertTrue(
            fnmatch.fnmatch(
                'some/name/with/na[/]med/file/test.py',
                '**/na[/]med/file/*.py',
                fnmatch.P | fnmatch.G
            )
        )
        self.assertTrue(
            fnmatch.fnmatch(
                'some/name/with/na[/]med\\/file/test.py',
                '**/na[/]med\\/file/*.py',
                fnmatch.P | fnmatch.G
            )
        )
        self.assertTrue(
            fnmatch.fnmatch(
                'some/name/with/na\\med/file/test.py',
                r'**/na[\\]med/file/*.py',
                fnmatch.P | fnmatch.R | fnmatch.G
            )
        )
        self.assertTrue(
            fnmatch.fnmatch(
                'some/name/with/na[\\/]med\\/file/test.py',
                r'**/na[\/]med\/file/*.py',
                fnmatch.P | fnmatch.R | fnmatch.G
            )
        )

    @mock.patch('wcmatch.util.is_case_sensitive')
    def test_wildcard_parsing(self, mock__iscase_sensitive):
        """Test wildcard parsing."""

        mock__iscase_sensitive.return_value = True

        fnmatch._compile.cache_clear()

        p1, p2 = fnmatch.translate(fnmatch.fnsplit('*test[a-z]?|*test2[a-z]?|!test[!a-z]|!test[!-|a-z]'))
        if util.PY36:
            self.assertEqual(p1, r'(?s:.*?test[a-z].|.*?test2[a-z].)\Z')
            self.assertEqual(p2, r'(?s:test[^a-z]|test[^\-\|a-z])\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:.*?test[a-z].|.*?test2[a-z].)\Z')
            self.assertEqual(p2, r'(?ms)(?:test[^a-z]|test[^\-\|a-z])\Z')

        p1, p2 = fnmatch.translate(fnmatch.fnsplit('*test[a-z]?|*test2[a-z]?|-test[!a-z]|-test[!-|a-z]'), fnmatch.M)
        if util.PY36:
            self.assertEqual(p1, r'(?s:.*?test[a-z].|.*?test2[a-z].)\Z')
            self.assertEqual(p2, r'(?s:test[^a-z]|test[^\-\|a-z])\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:.*?test[a-z].|.*?test2[a-z].)\Z')
            self.assertEqual(p2, r'(?ms)(?:test[^a-z]|test[^\-\|a-z])\Z')

        p1, p2 = fnmatch.translate(fnmatch.fnsplit('test[]][!][][]', fnmatch.F), fnmatch.F)
        if util.PY36:
            self.assertEqual(p1, r'(?s:test[\]][^\][]\[\])\Z')
            self.assertEqual(p2, r'(?s:)\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:test[\]][^\][]\[\])\Z')
            self.assertEqual(p2, r'(?ms)(?:)\Z')

        p1, p2 = fnmatch.translate(fnmatch.fnsplit('test[!]'))
        if util.PY36:
            self.assertEqual(p1, r'(?s:test\[\!\])\Z')
            self.assertEqual(p2, r'(?s:)\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:test\[\!\])\Z')
            self.assertEqual(p2, r'(?ms)(?:)\Z')

        p1, p2 = fnmatch.translate(fnmatch.fnsplit('|test|'))
        if util.PY36:
            self.assertEqual(p1, r'(?s:|test|)\Z')
            self.assertEqual(p2, r'(?s:)\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:|test|)\Z')
            self.assertEqual(p2, r'(?ms)(?:)\Z')

        p1, p2 = fnmatch.translate(fnmatch.fnsplit('!|!test|!'))
        if util.PY36:
            self.assertEqual(p1, r'(?s:.*?)\Z')
            self.assertEqual(p2, r'(?s:|test|)\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:.*?)\Z')
            self.assertEqual(p2, r'(?ms)(?:|test|)\Z')

        p1, p2 = fnmatch.translate(fnmatch.fnsplit('-|-test|-'), fnmatch.M)
        if util.PY36:
            self.assertEqual(p1, r'(?s:.*?)\Z')
            self.assertEqual(p2, r'(?s:|test|)\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:.*?)\Z')
            self.assertEqual(p2, r'(?ms)(?:|test|)\Z')

        p1, p2 = fnmatch.translate(fnmatch.fnsplit('test[^chars]'))
        if util.PY36:
            self.assertEqual(p1, r'(?s:test[\^chars])\Z')
            self.assertEqual(p2, r'(?s:)\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:test[\^chars])\Z')
            self.assertEqual(p2, r'(?ms)(?:)\Z')

        p1 = fnmatch.translate(fnmatch.fnsplit(r'test[^\\-\\&]'))[0]
        if util.PY36:
            self.assertEqual(p1, r'(?s:test[\^\\-\\\&])\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:test[\^\\-\\\&])\Z')

        # BROKEN
        p1 = fnmatch.translate(fnmatch.fnsplit(r'\\*\\?\\|\\[\\]'))[0]
        if util.PY36:
            self.assertEqual(p1, r'(?s:\\.*?\\.\\|\\[\\])\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:\\.*?\\.\\|\\[\\])\Z')

        p1 = fnmatch.translate(fnmatch.fnsplit(r'\\u0300', fnmatch.R), fnmatch.R)[0]
        if util.PY36:
            self.assertEqual(p1, r'(?s:\\u0300)\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:\\u0300)\Z')

        self.assertEqual(
            fnmatch.filter(['testm', 'test\\3', 'testa'], fnmatch.fnsplit(r'te\st[ma]')),
            ['testm', 'testa']
        )

        self.assertTrue(fnmatch.fnmatch('test\test', r'test\test', fnmatch.R))
        self.assertTrue(fnmatch.fnmatch('testtest', r'test\test'))
        self.assertTrue(fnmatch.fnmatch('test\\test', r'test\\test', fnmatch.R))
        self.assertTrue(fnmatch.fnmatch('test\\test', r'test\\test'))
        self.assertTrue(fnmatch.fnmatch('test\\m', r'test\\m'))
        self.assertTrue(fnmatch.fnmatch('test\\b', r'test\\[a-z]'))
        self.assertTrue(fnmatch.fnmatch('test\\b', r'test\\[a-z]', fnmatch.R))
        self.assertTrue(fnmatch.fnmatch('test\\b', r'test\\[a-z]'))
        self.assertTrue(fnmatch.fnmatch('[', '[[]'))
        self.assertTrue(fnmatch.fnmatch('&', '[a&&b]'))
        self.assertTrue(fnmatch.fnmatch('|', '[a||b]'))
        self.assertTrue(fnmatch.fnmatch('~', '[a~~b]'))
        self.assertTrue(fnmatch.fnmatch(',', '[a-z+--A-Z]'))
        self.assertTrue(fnmatch.fnmatch('.', '[a-z--/A-Z]'))

    @mock.patch('wcmatch.util.is_case_sensitive')
    def test_byte_wildcard_parsing(self, mock__iscase_sensitive):
        """Test byte_wildcard parsing."""

        mock__iscase_sensitive.return_value = True

        fnmatch._compile.cache_clear()

        p1, p2 = fnmatch.translate(fnmatch.fnsplit(b'*test[a-z]?|*test2[a-z]?|!test[!a-z]|!test[!-|a-z]'))
        if util.PY36:
            self.assertEqual(p1, br'(?s:.*?test[a-z].|.*?test2[a-z].)\Z')
            self.assertEqual(p2, br'(?s:test[^a-z]|test[^\-\|a-z])\Z')
        else:
            self.assertEqual(p1, br'(?ms)(?:.*?test[a-z].|.*?test2[a-z].)\Z')
            self.assertEqual(p2, br'(?ms)(?:test[^a-z]|test[^\-\|a-z])\Z')

        p1, p2 = fnmatch.translate(fnmatch.fnsplit(b'*test[a-z]?|*test2[a-z]?|-test[!a-z]|-test[!-|a-z]'), fnmatch.M)
        if util.PY36:
            self.assertEqual(p1, br'(?s:.*?test[a-z].|.*?test2[a-z].)\Z')
            self.assertEqual(p2, br'(?s:test[^a-z]|test[^\-\|a-z])\Z')
        else:
            self.assertEqual(p1, br'(?ms)(?:.*?test[a-z].|.*?test2[a-z].)\Z')
            self.assertEqual(p2, br'(?ms)(?:test[^a-z]|test[^\-\|a-z])\Z')

        p1, p2 = fnmatch.translate(fnmatch.fnsplit(b'test[]][!][][]'))
        if util.PY36:
            self.assertEqual(p1, br'(?s:test[\]][^\][]\[\])\Z')
            self.assertEqual(p2, br'(?s:)\Z')
        else:
            self.assertEqual(p1, br'(?ms)(?:test[\]][^\][]\[\])\Z')
            self.assertEqual(p2, br'(?ms)(?:)\Z')

        p1, p2 = fnmatch.translate(fnmatch.fnsplit(b'test[!]'))
        if util.PY36:
            self.assertEqual(p1, br'(?s:test\[\!\])\Z')
            self.assertEqual(p2, br'(?s:)\Z')
        else:
            self.assertEqual(p1, br'(?ms)(?:test\[\!\])\Z')
            self.assertEqual(p2, br'(?ms)(?:)\Z')

        p1, p2 = fnmatch.translate(fnmatch.fnsplit(b'|test|'))
        if util.PY36:
            self.assertEqual(p1, br'(?s:|test|)\Z')
            self.assertEqual(p2, br'(?s:)\Z')
        else:
            self.assertEqual(p1, br'(?ms)(?:|test|)\Z')
            self.assertEqual(p2, br'(?ms)(?:)\Z')

        p1, p2 = fnmatch.translate(fnmatch.fnsplit(b'!|!test|!'))
        if util.PY36:
            self.assertEqual(p1, br'(?s:.*?)\Z')
            self.assertEqual(p2, br'(?s:|test|)\Z')
        else:
            self.assertEqual(p1, br'(?ms)(?:.*?)\Z')
            self.assertEqual(p2, br'(?ms)(?:|test|)\Z')

        p1, p2 = fnmatch.translate(fnmatch.fnsplit(b'-|-test|-'), fnmatch.M)
        if util.PY36:
            self.assertEqual(p1, br'(?s:.*?)\Z')
            self.assertEqual(p2, br'(?s:|test|)\Z')
        else:
            self.assertEqual(p1, br'(?ms)(?:.*?)\Z')
            self.assertEqual(p2, br'(?ms)(?:|test|)\Z')

        p1, p2 = fnmatch.translate(fnmatch.fnsplit(b'test[^chars]'))
        if util.PY36:
            self.assertEqual(p1, br'(?s:test[\^chars])\Z')
            self.assertEqual(p2, br'(?s:)\Z')
        else:
            self.assertEqual(p1, br'(?ms)(?:test[\^chars])\Z')
            self.assertEqual(p2, br'(?ms)(?:)\Z')

        p1 = fnmatch.translate(fnmatch.fnsplit(br'test[^\\-\\&]'))[0]
        if util.PY36:
            self.assertEqual(p1, br'(?s:test[\^\\-\\\&])\Z')
        else:
            self.assertEqual(p1, br'(?ms)(?:test[\^\\-\\\&])\Z')

        # BROKEN
        p1 = fnmatch.translate(fnmatch.fnsplit(br'\\*\\?\\|\\[\\]'))[0]
        if util.PY36:
            self.assertEqual(p1, br'(?s:\\.*?\\.\\|\\[\\])\Z')
        else:
            self.assertEqual(p1, br'(?ms)(?:\\.*?\\.\\|\\[\\])\Z')

        p1 = fnmatch.translate(fnmatch.fnsplit(br'\\u0300'), fnmatch.R)[0]
        if util.PY36:
            self.assertEqual(p1, br'(?s:\\u0300)\Z')
        else:
            self.assertEqual(p1, br'(?ms)(?:\\u0300)\Z')

        self.assertEqual(
            fnmatch.filter([b'testm', b'test\\3', b'testa'], fnmatch.fnsplit(br'te\st[ma]')),
            [b'testm', b'testa']
        )

        self.assertTrue(fnmatch.fnmatch(b'test\test', br'test\test', fnmatch.R))
        self.assertTrue(fnmatch.fnmatch(b'testtest', br'test\test'))
        self.assertTrue(fnmatch.fnmatch(b'test\\test', br'test\\test', fnmatch.R))
        self.assertTrue(fnmatch.fnmatch(b'test\\test', br'test\\test'))
        self.assertTrue(fnmatch.fnmatch(b'test\\m', br'test\\m'))
        self.assertTrue(fnmatch.fnmatch(b'test\\b', br'test\\[a-z]'))
        self.assertTrue(fnmatch.fnmatch(b'test\\b', br'test\\[a-z]', fnmatch.R))
        self.assertTrue(fnmatch.fnmatch(b'test\\b', br'test\\[a-z]'))
        self.assertTrue(fnmatch.fnmatch(b'[', b'[[]'))
        self.assertTrue(fnmatch.fnmatch(b'&', b'[a&&b]'))
        self.assertTrue(fnmatch.fnmatch(b'|', b'[a||b]'))
        self.assertTrue(fnmatch.fnmatch(b'~', b'[a~~b]'))
        self.assertTrue(fnmatch.fnmatch(b',', b'[a-z+--A-Z]'))
        self.assertTrue(fnmatch.fnmatch(b'.', b'[a-z--/A-Z]'))

    @mock.patch('wcmatch.util.is_case_sensitive')
    def test_wildcard_character_notation(self, mock__iscase_sensitive):
        """Test wildcard character notations."""

        mock__iscase_sensitive.return_value = True

        fnmatch._compile.cache_clear()

        p1, p2 = fnmatch.translate(r'test\x70\u0070\U00000070\160\N{LATIN SMALL LETTER P}', fnmatch.R)
        if util.PY36:
            self.assertEqual(p1, r'(?s:testppppp)\Z')
            self.assertEqual(p2, r'(?s:)\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:testppppp)\Z')
            self.assertEqual(p2, r'(?ms)(?:)\Z')

        p1, p2 = fnmatch.translate(r'test[\x70][\u0070][\U00000070][\160][\N{LATIN SMALL LETTER P}]', fnmatch.R)
        if util.PY36:
            self.assertEqual(p1, r'(?s:test[p][p][p][p][p])\Z')
            self.assertEqual(p2, r'(?s:)\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:test[p][p][p][p][p])\Z')
            self.assertEqual(p2, r'(?ms)(?:)\Z')

        p1, p2 = fnmatch.translate(r'test\t\m', fnmatch.R)
        if util.PY36:
            self.assertEqual(p1, r'(?s:test\	m)\Z')
            self.assertEqual(p2, r'(?s:)\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:test\	m)\Z')
            self.assertEqual(p2, r'(?ms)(?:)\Z')

        p1, p2 = fnmatch.translate(r'test[\\]test', fnmatch.R)
        if util.PY36:
            self.assertEqual(p1, r'(?s:test[\\]test)\Z')
            self.assertEqual(p2, r'(?s:)\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:test[\\]test)\Z')
            self.assertEqual(p2, r'(?ms)(?:)\Z')

        p1, p2 = fnmatch.translate('test[\\')
        if util.PY36:
            self.assertEqual(p1, r'(?s:test\[\\)\Z')
            self.assertEqual(p2, r'(?s:)\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:test\[\\)\Z')
            self.assertEqual(p2, r'(?ms)(?:)\Z')

        p1, p2 = fnmatch.translate(r'test\44test', fnmatch.R)
        if util.PY36:
            self.assertEqual(p1, r'(?s:test\$test)\Z')
            self.assertEqual(p2, r'(?s:)\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:test\$test)\Z')
            self.assertEqual(p2, r'(?ms)(?:)\Z')

        p1, p2 = fnmatch.translate(r'test\44', fnmatch.R)
        if util.PY36:
            self.assertEqual(p1, r'(?s:test\$)\Z')
            self.assertEqual(p2, r'(?s:)\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:test\$)\Z')
            self.assertEqual(p2, r'(?ms)(?:)\Z')

        p1, p2 = fnmatch.translate(r'test\400', fnmatch.R)
        if util.PY36:
            self.assertEqual(p1, r'(?s:test\Ā)\Z')
            self.assertEqual(p2, r'(?s:)\Z')
        else:
            self.assertEqual(p1, r'(?ms)(?:test\Ā)\Z')
            self.assertEqual(p2, r'(?ms)(?:)\Z')

        with pytest.raises(SyntaxError):
            fnmatch.translate(r'test\N', fnmatch.R)

        with pytest.raises(SyntaxError):
            fnmatch.translate(r'test\Nx', fnmatch.R)

        with pytest.raises(SyntaxError):
            fnmatch.translate(r'test\N{', fnmatch.R)


class TestDirWalker(unittest.TestCase):
    """Test the _DirWalker class."""

    def setUp(self):
        """Setup the tests."""

        self.default_flags = wcfind.R | wcfind.I | wcfind.M
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

        walker = wcfind.WcFind(
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

        walker = wcfind.WcFind(
            'tests/dir_walker',
            fnmatch.fnsplit('*.*|-*.file', self.default_flags), None,
            False, False, self.default_flags
        )

        self.crawl_files(walker)

        self.assertEqual(self.skipped, 2)
        self.assertEqual(len(self.files), 2)

    def test_recursive(self):
        """Test non-recursive search."""

        walker = wcfind.WcFind(
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

        walker = wcfind.WcFind(
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

        walker = wcfind.WcFind(
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

        walker = wcfind.WcFind(
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

        walker = wcfind.WcFind(
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

        walker = wcfind.WcFind(
            'tests/dir_walker',
            '*.txt*', None,
            True, True, self.default_flags
        )

        walker.kill()
        records = 0
        for f in walker.imatch():
            records += 1

        self.assertTrue(records == 1 or walker.get_skipped() == 1)
