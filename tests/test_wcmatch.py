# -*- coding: utf-8 -*-
"""Tests for `wcmatch`."""
import unittest
import os
import wcmatch.wcmatch as wcmatch
import shutil
from wcmatch import _wcparse


# Below is general helper stuff that Python uses in `unittests`.  As these
# not meant for users, and could change without notice, include them
# ourselves so we aren't surprised later.
TESTFN = '@test'

# Disambiguate `TESTFN` for parallel testing, while letting it remain a valid
# module name.
TESTFN = "{}_{}_tmp".format(TESTFN, os.getpid())


def create_empty_file(filename):
    """Create an empty file. If the file already exists, truncate it."""

    fd = os.open(filename, os.O_WRONLY | os.O_CREAT | os.O_TRUNC)
    os.close(fd)


_can_symlink = None


def can_symlink():
    """Check if we can symlink."""

    global _can_symlink
    if _can_symlink is not None:
        return _can_symlink
    symlink_path = TESTFN + "can_symlink"
    try:
        os.symlink(TESTFN, symlink_path)
        can = True
    except (OSError, NotImplementedError, AttributeError):
        can = False
    else:
        os.remove(symlink_path)
    _can_symlink = can
    return can


def skip_unless_symlink(test):
    """Skip decorator for tests that require functional symlink."""

    ok = can_symlink()
    msg = "Requires functional symlink implementation"
    return test if ok else unittest.skip(msg)(test)


class _TestWcmatch(unittest.TestCase):
    """Test the `WcMatch` class."""

    def mktemp(self, *parts):
        """Make temp directory."""

        filename = self.norm(*parts)
        base, file = os.path.split(filename)
        if not os.path.exists(base):
            retry = 3
            while retry:
                try:
                    os.makedirs(base)
                    retry = 0
                except Exception:  # noqa: PERF203
                    retry -= 1
        create_empty_file(filename)

    def force_err(self):
        """Force an error."""

        raise TypeError

    def norm(self, *parts):
        """Normalizes file path (in relation to temp directory)."""
        tempdir = os.fsencode(self.tempdir) if isinstance(parts[0], bytes) else self.tempdir
        return os.path.join(tempdir, *parts)

    def norm_list(self, files):
        """Normalize file list."""

        return sorted([self.norm(os.path.normpath(x)) for x in files])

    def setUp(self):
        """Setup."""

        self.tempdir = TESTFN + "_dir"
        self.default_flags = wcmatch.R | wcmatch.I | wcmatch.M | wcmatch.SL
        self.errors = []
        self.skipped = 0
        self.skip_records = []
        self.error_records = []
        self.files = []

    def tearDown(self):
        """Cleanup."""

        retry = 3
        while retry:
            try:
                shutil.rmtree(self.tempdir)
                retry = 0
            except Exception:  # noqa: PERF203
                retry -= 1

    def crawl_files(self, walker):
        """Crawl the files."""

        for f in walker.match():
            if f == '<SKIPPED>':
                self.skip_records.append(f)
            elif f == '<ERROR>':
                self.error_records.append(f)
            else:
                self.files.append(f)
        self.skipped = walker.get_skipped()


class TestWcmatch(_TestWcmatch):
    """Test the `WcMatch` class."""

    def setUp(self):
        """Setup."""

        self.tempdir = TESTFN + "_dir"
        self.mktemp('.hidden', 'a.txt')
        self.mktemp('.hidden', 'b.file')
        self.mktemp('.hidden_file')
        self.mktemp('a.txt')
        self.mktemp('b.file')
        self.mktemp('c.txt.bak')

        self.default_flags = wcmatch.R | wcmatch.I | wcmatch.M | wcmatch.SL
        self.errors = []
        self.skipped = 0
        self.skip_records = []
        self.error_records = []
        self.files = []

    def test_full_path_exclude(self):
        """Test full path exclude."""

        walker = wcmatch.WcMatch(
            self.tempdir,
            '*.txt', exclude_pattern='**/.hidden',
            flags=self.default_flags | wcmatch.DIRPATHNAME | wcmatch.GLOBSTAR | wcmatch.RECURSIVE | wcmatch.HIDDEN
        )

        self.crawl_files(walker)

        self.assertEqual(sorted(self.files), self.norm_list(['a.txt']))

    def test_full_file(self):
        """Test full file."""

        walker = wcmatch.WcMatch(
            self.tempdir,
            '**/*.txt|-**/.hidden/*',
            flags=self.default_flags | wcmatch.FILEPATHNAME | wcmatch.GLOBSTAR | wcmatch.RECURSIVE | wcmatch.HIDDEN
        )

        self.crawl_files(walker)

        self.assertEqual(sorted(self.files), self.norm_list(['a.txt']))

    def test_non_recursive(self):
        """Test non-recursive search."""

        walker = wcmatch.WcMatch(
            self.tempdir,
            '*.txt',
            flags=self.default_flags
        )

        self.crawl_files(walker)
        self.assertEqual(self.skipped, 3)
        self.assertEqual(sorted(self.files), self.norm_list(['a.txt']))

    def test_non_recursive_inverse(self):
        """Test non-recursive inverse search."""

        walker = wcmatch.WcMatch(
            self.tempdir,
            '*.*|-*.file',
            flags=self.default_flags
        )

        self.crawl_files(walker)
        self.assertEqual(self.skipped, 2)
        self.assertEqual(sorted(self.files), self.norm_list(['a.txt', 'c.txt.bak']))

    def test_recursive(self):
        """Test non-recursive search."""

        walker = wcmatch.WcMatch(
            self.tempdir,
            '*.txt',
            flags=self.default_flags | wcmatch.RECURSIVE
        )

        self.crawl_files(walker)
        self.assertEqual(self.skipped, 3)
        self.assertEqual(sorted(self.files), self.norm_list(['a.txt']))

    def test_recursive_bytes(self):
        """Test non-recursive search."""

        walker = wcmatch.WcMatch(
            os.fsencode(self.tempdir),
            b'*.txt',
            flags=self.default_flags | wcmatch.RECURSIVE
        )

        self.crawl_files(walker)
        self.assertEqual(self.skipped, 3)
        self.assertEqual(sorted(self.files), self.norm_list([b'a.txt']))

    def test_recursive_hidden(self):
        """Test non-recursive search."""

        walker = wcmatch.WcMatch(
            self.tempdir,
            '*.txt',
            flags=self.default_flags | wcmatch.RECURSIVE | wcmatch.HIDDEN
        )

        self.crawl_files(walker)
        self.assertEqual(self.skipped, 4)
        self.assertEqual(sorted(self.files), self.norm_list(['.hidden/a.txt', 'a.txt']))

    def test_recursive_hidden_bytes(self):
        """Test non-recursive search with byte strings."""

        walker = wcmatch.WcMatch(
            os.fsencode(self.tempdir),
            b'*.txt',
            flags=self.default_flags | wcmatch.RECURSIVE | wcmatch.HIDDEN
        )

        self.crawl_files(walker)
        self.assertEqual(self.skipped, 4)
        self.assertEqual(sorted(self.files), self.norm_list([b'.hidden/a.txt', b'a.txt']))

    def test_recursive_hidden_folder_exclude(self):
        """Test non-recursive search."""

        walker = wcmatch.WcMatch(
            self.tempdir,
            '*.txt', exclude_pattern='.hidden',
            flags=self.default_flags | wcmatch.RECURSIVE | wcmatch.HIDDEN
        )

        self.crawl_files(walker)
        self.assertEqual(self.skipped, 3)
        self.assertEqual(sorted(self.files), self.norm_list(['a.txt']))

    def test_recursive_hidden_folder_exclude_inverse(self):
        """Test non-recursive search with inverse."""

        walker = wcmatch.WcMatch(
            self.tempdir,
            '*.txt', exclude_pattern='*|-.hidden',
            flags=self.default_flags | wcmatch.RECURSIVE | wcmatch.HIDDEN
        )

        self.crawl_files(walker)
        self.assertEqual(self.skipped, 4)
        self.assertEqual(sorted(self.files), self.norm_list(['.hidden/a.txt', 'a.txt']))

    def test_abort(self):
        """Test aborting."""

        walker = wcmatch.WcMatch(
            self.tempdir,
            '*.txt',
            flags=self.default_flags | wcmatch.RECURSIVE | wcmatch.HIDDEN
        )

        records = 0
        for _f in walker.imatch():
            records += 1
            walker.kill()
        self.assertEqual(records, 1)

        # Reset our test tracker along with the walker object
        self.errors = []
        self.skipped = 0
        self.files = []
        records = 0
        walker.reset()

        self.crawl_files(walker)
        self.assertEqual(sorted(self.files), self.norm_list(['.hidden/a.txt', 'a.txt']))

    def test_abort_early(self):
        """Test aborting early."""

        walker = wcmatch.WcMatch(
            self.tempdir,
            '*.txt*',
            flags=self.default_flags | wcmatch.RECURSIVE | wcmatch.HIDDEN
        )

        walker.kill()
        records = 0
        for _f in walker.imatch():
            records += 1

        self.assertTrue(records == 0 or walker.get_skipped() == 0)

    def test_empty_string_dir(self):
        """Test when directory is an empty string."""

        target = '.' + os.sep
        walker = wcmatch.WcMatch(
            '',
            '*.txt*',
            flags=self.default_flags | wcmatch.RECURSIVE | wcmatch.HIDDEN
        )
        self.assertEqual(walker._root_dir, target)

        walker = wcmatch.WcMatch(
            b'',
            b'*.txt*',
            flags=self.default_flags | wcmatch.RECURSIVE | wcmatch.HIDDEN
        )
        self.assertEqual(walker._root_dir, os.fsencode(target))

    def test_empty_string_file(self):
        """Test when file pattern is an empty string."""

        walker = wcmatch.WcMatch(
            self.tempdir,
            '',
            flags=self.default_flags | wcmatch.RECURSIVE | wcmatch.HIDDEN
        )
        self.crawl_files(walker)
        self.assertEqual(
            sorted(self.files),
            self.norm_list(
                ['a.txt', '.hidden/a.txt', '.hidden/b.file', 'b.file', '.hidden_file', 'c.txt.bak']
            )
        )

    def test_skip_override(self):
        """Test `on_skip` override."""

        walker = wcmatch.WcMatch(
            self.tempdir,
            '*.txt',
            flags=self.default_flags | wcmatch.RECURSIVE | wcmatch.HIDDEN
        )

        walker.on_skip = lambda base, name: '<SKIPPED>'

        self.crawl_files(walker)
        self.assertEqual(len(self.skip_records), 4)

    def test_errors(self):
        """Test errors."""

        walker = wcmatch.WcMatch(
            self.tempdir,
            '*.txt',
            flags=self.default_flags | wcmatch.RECURSIVE | wcmatch.HIDDEN
        )

        walker.on_validate_file = lambda base, name: self.force_err()

        self.crawl_files(walker)
        self.assertEqual(sorted(self.files), self.norm_list([]))

        self.errors = []
        self.skipped = 0
        self.files = []

        walker = wcmatch.WcMatch(
            self.tempdir,
            '*.txt',
            flags=self.default_flags | wcmatch.RECURSIVE | wcmatch.HIDDEN
        )

        walker.on_validate_directory = lambda base, name: self.force_err()

        self.crawl_files(walker)
        self.assertEqual(sorted(self.files), self.norm_list(['a.txt']))

    def test_error_override(self):
        """Test `on_eror` override."""

        walker = wcmatch.WcMatch(
            self.tempdir,
            '*.txt',
            flags=self.default_flags | wcmatch.RECURSIVE | wcmatch.HIDDEN
        )

        walker.on_validate_file = lambda base, name: self.force_err()
        walker.on_error = lambda base, name: '<ERROR>'

        self.crawl_files(walker)
        self.assertEqual(len(self.error_records), 2)

    def test_match_base_filepath(self):
        """Test `MATCHBASE` with filepath."""

        walker = wcmatch.WcMatch(
            self.tempdir,
            '*.txt',
            flags=self.default_flags | wcmatch.RECURSIVE | wcmatch.HIDDEN | wcmatch.FILEPATHNAME | wcmatch.MATCHBASE
        )
        self.crawl_files(walker)
        self.assertEqual(
            sorted(self.files),
            self.norm_list(
                ['a.txt', '.hidden/a.txt']
            )
        )

    def test_match_base_absolute_filepath(self):
        """Test `MATCHBASE` with filepath and an absolute path."""

        walker = wcmatch.WcMatch(
            self.tempdir,
            '.hidden/*.txt',
            flags=self.default_flags | wcmatch.RECURSIVE | wcmatch.HIDDEN | wcmatch.FILEPATHNAME | wcmatch.MATCHBASE
        )
        self.crawl_files(walker)
        self.assertEqual(
            sorted(self.files),
            self.norm_list(
                ['.hidden/a.txt']
            )
        )

    def test_match_base_anchored_filepath(self):
        """Test `MATCHBASE` with filepath and an anchored pattern."""

        walker = wcmatch.WcMatch(
            self.tempdir,
            '/*.txt',
            flags=self.default_flags | wcmatch.RECURSIVE | wcmatch.HIDDEN | wcmatch.FILEPATHNAME | wcmatch.MATCHBASE
        )
        self.crawl_files(walker)
        self.assertEqual(
            sorted(self.files),
            self.norm_list(
                ['a.txt']
            )
        )

    def test_match_insensitive(self):
        """Test case insensitive."""

        walker = wcmatch.WcMatch(
            self.tempdir,
            'A.TXT',
            flags=self.default_flags | wcmatch.RECURSIVE | wcmatch.FILEPATHNAME | wcmatch.IGNORECASE
        )
        self.crawl_files(walker)
        self.assertEqual(
            sorted(self.files),
            self.norm_list(
                ['a.txt']
            )
        )

    def test_nomatch_sensitive(self):
        """Test case sensitive does not match."""

        walker = wcmatch.WcMatch(
            self.tempdir,
            'A.TXT',
            flags=self.default_flags | wcmatch.RECURSIVE | wcmatch.FILEPATHNAME | wcmatch.CASE
        )
        self.crawl_files(walker)
        self.assertEqual(
            sorted(self.files),
            self.norm_list(
                []
            )
        )

    def test_match_sensitive(self):
        """Test case sensitive."""

        walker = wcmatch.WcMatch(
            self.tempdir,
            'a.txt',
            flags=self.default_flags | wcmatch.RECURSIVE | wcmatch.FILEPATHNAME | wcmatch.CASE
        )
        self.crawl_files(walker)
        self.assertEqual(
            sorted(self.files),
            self.norm_list(
                ['a.txt']
            )
        )


@skip_unless_symlink
class TestWcmatchSymlink(_TestWcmatch):
    """Test symlinks."""

    def mksymlink(self, original, link):
        """Make symlink."""

        if not os.path.lexists(link):
            os.symlink(original, link)

    def setUp(self):
        """Setup."""

        self.tempdir = TESTFN + "_dir"
        self.mktemp('.hidden', 'a.txt')
        self.mktemp('.hidden', 'b.file')
        self.mktemp('.hidden_file')
        self.mktemp('a.txt')
        self.mktemp('b.file')
        self.mktemp('c.txt.bak')
        self.can_symlink = can_symlink()
        if self.can_symlink:
            self.mksymlink('.hidden', self.norm('sym1'))
            self.mksymlink(os.path.join('.hidden', 'a.txt'), self.norm('sym2'))

        self.default_flags = wcmatch.R | wcmatch.I | wcmatch.M
        self.errors = []
        self.skipped = 0
        self.skip_records = []
        self.error_records = []
        self.files = []

    def test_symlinks(self):
        """Test symlinks."""

        walker = wcmatch.WcMatch(
            self.tempdir,
            '*.txt',
            flags=self.default_flags | wcmatch.RECURSIVE | wcmatch.HIDDEN | wcmatch.SYMLINKS
        )

        self.crawl_files(walker)
        self.assertEqual(
            sorted(self.files),
            self.norm_list(
                ['a.txt', '.hidden/a.txt', 'sym1/a.txt']
            )
        )

    def test_avoid_symlinks(self):
        """Test avoiding symlinks."""

        walker = wcmatch.WcMatch(
            self.tempdir,
            '*.txt',
            flags=self.default_flags | wcmatch.RECURSIVE | wcmatch.HIDDEN
        )

        self.crawl_files(walker)
        self.assertEqual(
            sorted(self.files),
            self.norm_list(
                ['a.txt', '.hidden/a.txt']
            )
        )


class TestExpansionLimit(unittest.TestCase):
    """Test expansion limits."""

    def test_limit_wcmatch(self):
        """Test expansion limit of `globmatch`."""

        with self.assertRaises(_wcparse.PatternLimitException):
            wcmatch.WcMatch('.', '{1..11}', flags=wcmatch.BRACE, limit=10)
