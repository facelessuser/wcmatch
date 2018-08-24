"""
These test cases are taken straight from cpython to ensure our glob works as good as the builtin.

Matches close to the normal glob implementation, but there are a few consciously
made difference in implementation.

1. Our glob will often return things like `.` and `..` matching Bash's behavior.
2. We do not normalize out `.` and `..`, so the norm function below just joins.
3. We escape with backslashes not `[]`.
4. A Window's path separator will be two backslashes in a pattern due to escape logic, not one.
"""
import contextlib
from wcmatch import glob
from wcmatch import util
import os
import shutil
import sys
import unittest
import warnings

# Below is general helper stuff that Python uses in unittests.  As these
# not meant for users, and could change without notice, include them
# ourselves so we aren't surprised later.
TESTFN = '@test'

# Disambiguate TESTFN for parallel testing, while letting it remain a valid
# module name.
TESTFN = "{}_{}_tmp".format(TESTFN, os.getpid())


@contextlib.contextmanager
def change_cwd(path, quiet=False):
    """
    Return a context manager that changes the current working directory.

    Arguments:
      path: the directory to use as the temporary current working directory.
      quiet: if False (the default), the context manager raises an exception
        on error.  Otherwise, it issues only a warning and keeps the current
        working directory the same.
    """

    saved_dir = os.getcwd()
    try:
        os.chdir(path)
    except OSError as exc:
        if not quiet:
            raise
        warnings.warn('tests may fail, unable to change CWD to: ' + path,
                      RuntimeWarning, stacklevel=3)
    try:
        yield os.getcwd()
    finally:
        os.chdir(saved_dir)


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


class GlobTests(unittest.TestCase):
    """General glob tests."""

    DEFAULT_FLAGS = glob.BRACE | glob.EXTGLOB | glob.GLOBSTAR

    def norm(self, *parts):
        """Normalizes file path (in relation to temp dir)."""

        return os.path.join(self.tempdir, *parts)

    def globnorm(self, *parts):
        """Normalizes glob path (in relation to temp dir)."""

        return self.globsep.join([self.tempdir] + list(parts))

    def globjoin(self, *parts):
        """Joins glob path."""

        sep = os.fsencode(self.globsep) if isinstance(parts[0], bytes) else self.globsep
        return sep.join(list(parts))

    def joins(self, *tuples):
        """Joins path."""

        return [os.path.join(self.tempdir, *parts) for parts in tuples]

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
                except Exception:
                    retry -= 1
        create_empty_file(filename)

    def setUp(self):
        """Setup."""

        if os.sep == '/':
            self.globsep = os.sep
        else:
            self.globsep = r'\\'
        self.tempdir = TESTFN + "_dir"
        self.mktemp('a', 'D')
        self.mktemp('aab', 'F')
        self.mktemp('.aa', 'G')
        self.mktemp('.bb', 'H')
        self.mktemp('aaa', 'zzzF')
        self.mktemp('ZZZ')
        self.mktemp('EF')
        self.mktemp('a', 'bcd', 'EF')
        self.mktemp('a', 'bcd', 'efg', 'ha')
        self.can_symlink = can_symlink()
        if self.can_symlink:
            os.symlink(self.norm('broken'), self.norm('sym1'))
            os.symlink('broken', self.norm('sym2'))
            os.symlink(os.path.join('a', 'bcd'), self.norm('sym3'))

    def tearDown(self):
        """Cleanup."""

        retry = 3
        while retry:
            try:
                shutil.rmtree(self.tempdir)
                retry = 0
            except Exception:
                retry -= 1

    def glob(self, *parts, **kwargs):
        """Perform a glob with validation."""

        if parts:
            if len(parts) == 1:
                pattern = parts[0]
            else:
                pattern = self.globjoin(*parts)
            p = self.globjoin(self.tempdir, pattern)
        else:
            p = self.tempdir
        res = glob.glob(p, **kwargs)
        self.assertCountEqual(glob.iglob(p, **kwargs), res)
        bres = [os.fsencode(x) for x in res]
        self.assertCountEqual(glob.glob(os.fsencode(p), **kwargs), bres)
        self.assertCountEqual(glob.iglob(os.fsencode(p), **kwargs), bres)
        return res

    def nglob(self, *parts, **kwargs):
        """Perform a glob with validation."""

        if len(parts) == 1:
            pattern = parts[0]
        else:
            pattern = self.globjoin(*parts)
        p = self.globjoin(self.tempdir, pattern)
        p = b'!' + p if isinstance(p, bytes) else '!' + p
        p = [self.globjoin(self.tempdir, '**'), p]
        res = glob.glob(p, **kwargs)
        self.assertCountEqual(glob.iglob(p, **kwargs), res)
        bres = [os.fsencode(x) for x in res]
        self.assertCountEqual(glob.glob([os.fsencode(x) for x in p], **kwargs), bres)
        self.assertCountEqual(glob.iglob([os.fsencode(x) for x in p], **kwargs), bres)
        return res

    def assertSequencesEqual_noorder(self, l1, l2):
        """Verify lists match (unordered)."""

        l1 = list(l1)
        l2 = list(l2)
        self.assertEqual(set(l1), set(l2))
        self.assertEqual(sorted(l1), sorted(l2))

    def test_glob_literal(self):
        """Test glob literal."""

        eq = self.assertSequencesEqual_noorder
        eq(self.glob('a', flags=self.DEFAULT_FLAGS), [self.norm('a')])
        eq(self.glob('a', 'D', flags=self.DEFAULT_FLAGS), [self.norm('a', 'D')])
        eq(self.glob('aab', flags=self.DEFAULT_FLAGS), [self.norm('aab')])
        eq(self.glob('zymurgy', flags=self.DEFAULT_FLAGS), [])

        res = glob.glob('*', flags=self.DEFAULT_FLAGS)
        self.assertEqual({type(r) for r in res}, {str})
        res = glob.glob(self.globjoin(os.curdir, '*'), flags=self.DEFAULT_FLAGS)
        self.assertEqual({type(r) for r in res}, {str})

        res = glob.glob(b'*', flags=self.DEFAULT_FLAGS)
        self.assertEqual({type(r) for r in res}, {bytes})
        res = glob.glob(self.globjoin(os.fsencode(os.curdir), b'*'), flags=self.DEFAULT_FLAGS)
        self.assertEqual({type(r) for r in res}, {bytes})

    def test_glob_one_directory(self):
        """Test glob directory."""

        eq = self.assertSequencesEqual_noorder
        eq(self.glob('a*', flags=self.DEFAULT_FLAGS), map(self.norm, ['a', 'aab', 'aaa']))
        eq(self.glob('*a', flags=self.DEFAULT_FLAGS), map(self.norm, ['a', 'aaa']))
        eq(self.glob('.*', flags=self.DEFAULT_FLAGS), map(self.norm, ['.', '..', '.aa', '.bb']))
        eq(self.glob('?aa', flags=self.DEFAULT_FLAGS), map(self.norm, ['aaa']))
        eq(self.glob('aa?', flags=self.DEFAULT_FLAGS), map(self.norm, ['aaa', 'aab']))
        eq(self.glob('aa[ab]', flags=self.DEFAULT_FLAGS), map(self.norm, ['aaa', 'aab']))
        eq(self.glob('*q', flags=self.DEFAULT_FLAGS), [])

    def test_glob_inverse(self):
        """Test glob inverse."""

        eq = self.assertSequencesEqual_noorder
        nfiles = [
            ['EF'],
            ['ZZZ'],
            ['']
        ]
        if self.can_symlink:
            nfiles.extend(
                [
                    ['sym1'],
                    ['sym3'],
                    ['sym2'],
                    ['sym3', 'efg'],
                    ['sym3', 'efg', 'ha'],
                    ['sym3', 'EF']
                ]
            )
        eq(self.nglob('a*', flags=self.DEFAULT_FLAGS | glob.NEGATE), map(lambda x: self.norm(*x), nfiles))

    def test_glob_inverse_only(self):
        """Test that when providing an inverse list without providing a positive list that it still works."""

        eq = self.assertSequencesEqual_noorder
        nfiles = [
            ['EF'],
            ['ZZZ']
        ]
        if self.can_symlink:
            nfiles.extend(
                [
                    ['sym1'],
                    ['sym3'],
                    ['sym2'],
                    ['sym3', 'efg'],
                    ['sym3', 'efg', 'ha'],
                    ['sym3', 'EF']
                ]
            )

        with change_cwd(self.tempdir):
            eq(
                map(self.norm, glob.glob('!a*', flags=self.DEFAULT_FLAGS | glob.NEGATE)),
                map(lambda x: self.norm(*x), nfiles)
            )

    def test_glob_file_direct(self):
        """Test the file directly -- without magic."""

        eq = self.assertSequencesEqual_noorder
        eq(self.glob(flags=self.DEFAULT_FLAGS), [self.tempdir])

    def test_glob_nested_directory(self):
        """Test nested glob directory."""

        eq = self.assertSequencesEqual_noorder
        if os.path.normcase("abCD") == "abCD":
            # case-sensitive filesystem
            eq(self.glob('a', 'bcd', 'E*', flags=self.DEFAULT_FLAGS), [self.norm('a', 'bcd', 'EF')])
        else:
            # case insensitive filesystem
            eq(self.glob('a', 'bcd', 'E*', flags=self.DEFAULT_FLAGS), [self.norm('a', 'bcd', 'EF'),
                                                                       self.norm('a', 'bcd', 'efg')])
        eq(self.glob('a', 'bcd', '*g', flags=self.DEFAULT_FLAGS), [self.norm('a', 'bcd', 'efg')])

    def test_glob_directory_names(self):
        """Test glob directory names."""

        eq = self.assertSequencesEqual_noorder
        eq(self.glob('*', 'D', flags=self.DEFAULT_FLAGS), [self.norm('a', 'D')])
        eq(self.glob('*', '*a', flags=self.DEFAULT_FLAGS), [])
        eq(self.glob('a', '*', '*', '*a', flags=self.DEFAULT_FLAGS),
           [self.norm('a', 'bcd', 'efg', 'ha')])
        eq(self.glob('?a?', '*F', flags=self.DEFAULT_FLAGS), [self.norm('aaa', 'zzzF'),
                                                              self.norm('aab', 'F')])

    def test_glob_only_directory(self):
        """Test only directories."""

        files = [self.norm('aab', ''),
                 self.norm('aaa', ''),
                 self.norm('a', '')]

        if self.can_symlink:
            files.append(self.norm('sym3', ''))

        eq = self.assertSequencesEqual_noorder
        eq(self.glob('*', '', flags=self.DEFAULT_FLAGS), files)

        if not util.is_case_sensitive():
            eq(self.glob('*\\', flags=self.DEFAULT_FLAGS), files)

    def test_extglob(self):
        """Test extglob."""

        eq = self.assertSequencesEqual_noorder
        eq(self.glob('@(a|aa*(a|b))', flags=self.DEFAULT_FLAGS), [self.norm('aab'),
                                                                  self.norm('aaa'),
                                                                  self.norm('a')])

    def test_seq(self):
        """Test extglob."""

        eq = self.assertSequencesEqual_noorder
        eq(self.glob('[a]', flags=self.DEFAULT_FLAGS), [self.norm('a')])
        eq(self.glob('[!b]', flags=self.DEFAULT_FLAGS), [self.norm('a')])
        eq(self.glob('[^b]', flags=self.DEFAULT_FLAGS), [self.norm('a')])
        eq(self.glob(r'@([\a]|\aaa)', flags=self.DEFAULT_FLAGS), [self.norm('a'),
                                                                  self.norm('aaa')])

    def test_empty(self):
        """Test empty."""

        eq = self.assertSequencesEqual_noorder
        eq(glob.glob('', flags=self.DEFAULT_FLAGS), [])

    def test_glob_directory_with_trailing_slash(self):
        """Patterns ending with a slash shouldn't match non-dirs."""

        res = glob.glob(self.globnorm('Z*Z') + self.globsep, flags=self.DEFAULT_FLAGS)
        self.assertEqual(res, [])
        res = glob.glob(self.globnorm('ZZZ') + self.globsep, flags=self.DEFAULT_FLAGS)
        self.assertEqual(res, [])
        # When there is a wildcard pattern which ends with os.sep, glob()
        # doesn't blow up.
        res = glob.glob(self.globnorm('aa*') + self.globsep, flags=self.DEFAULT_FLAGS)
        self.assertEqual(len(res), 2)
        # either of these results is reasonable
        self.assertIn(set(res), [
                      {self.norm('aaa'), self.norm('aab')},
                      {self.norm('aaa') + os.sep, self.norm('aab') + os.sep},
                      ])

    def test_glob_bytes_directory_with_trailing_slash(self):
        """
        Test glob byte directory with trailing slash.

        Same as test_glob_directory_with_trailing_slash, but with a
        bytes argument.
        """

        res = glob.glob(os.fsencode(self.globnorm('Z*Z') + self.globsep), flags=self.DEFAULT_FLAGS)
        self.assertEqual(res, [])
        res = glob.glob(os.fsencode(self.globnorm('ZZZ') + self.globsep), flags=self.DEFAULT_FLAGS)
        self.assertEqual(res, [])
        res = glob.glob(os.fsencode(self.globnorm('aa*') + self.globsep), flags=self.DEFAULT_FLAGS)
        self.assertEqual(len(res), 2)
        # either of these results is reasonable
        self.assertIn(set(res), [
                      {os.fsencode(self.norm('aaa')),
                       os.fsencode(self.norm('aab'))},
                      {os.fsencode(self.norm('aaa') + os.sep),
                       os.fsencode(self.norm('aab') + os.sep)},
                      ])

    @skip_unless_symlink
    def test_glob_symlinks(self):
        """Test glob symlinks."""

        eq = self.assertSequencesEqual_noorder
        eq(self.glob('sym3', flags=self.DEFAULT_FLAGS), [self.norm('sym3')])
        eq(self.glob('sym3', '*', flags=self.DEFAULT_FLAGS), [self.norm('sym3', 'EF'),
                                                              self.norm('sym3', 'efg')])
        self.assertIn(self.glob('sym3' + self.globsep, flags=self.DEFAULT_FLAGS),
                      [[self.norm('sym3')], [self.norm('sym3') + os.sep]])
        eq(self.glob('*', '*F', flags=self.DEFAULT_FLAGS),
           [self.norm('aaa', 'zzzF'),
            self.norm('aab', 'F'), self.norm('sym3', 'EF')])

    @skip_unless_symlink
    def test_glob_broken_symlinks(self):
        """Test broken symlinks."""

        eq = self.assertSequencesEqual_noorder
        eq(self.glob('sym*', flags=self.DEFAULT_FLAGS), [self.norm('sym1'), self.norm('sym2'),
                                                         self.norm('sym3')])
        eq(self.glob('sym1', flags=self.DEFAULT_FLAGS), [self.norm('sym1')])
        eq(self.glob('sym2', flags=self.DEFAULT_FLAGS), [self.norm('sym2')])

    @unittest.skipUnless(sys.platform == "win32", "Win32 specific test")
    def test_glob_magic_in_drive(self):
        """Test glob magic in drive name."""

        eq = self.assertSequencesEqual_noorder
        eq(glob.glob('*:', flags=self.DEFAULT_FLAGS), [])
        eq(glob.glob(b'*:', flags=self.DEFAULT_FLAGS), [])
        eq(glob.glob('?:', flags=self.DEFAULT_FLAGS), [])
        eq(glob.glob(b'?:', flags=self.DEFAULT_FLAGS), [])
        eq(glob.glob(r'\\\\?\\c:\\', flags=self.DEFAULT_FLAGS), ['\\\\?\\c:\\'])
        eq(glob.glob(br'\\\\?\\c:\\', flags=self.DEFAULT_FLAGS), [b'\\\\?\\c:\\'])
        eq(glob.glob(r'\\\\*\\*\\', flags=self.DEFAULT_FLAGS), [])
        eq(glob.glob(br'\\\\*\\*\\', flags=self.DEFAULT_FLAGS), [])

    def check_escape(self, arg, expected, raw=False):
        """Verify escapes."""

        if raw:
            self.assertEqual(glob.raw_escape(arg), expected)
            self.assertEqual(glob.raw_escape(os.fsencode(arg)), os.fsencode(expected))
        else:
            self.assertEqual(glob.escape(arg), expected)
            self.assertEqual(glob.escape(os.fsencode(arg)), os.fsencode(expected))

    def test_escape(self):
        """Test path escapes."""

        check = self.check_escape
        check('abc', 'abc')
        check('[', r'\[')
        check('?', r'\?')
        check('*', r'\*')
        check('[[_/*?*/_]]', r'\[\[_/\*\?\*/_]]')
        check('/[[_/*?*/_]]/', r'/\[\[_/\*\?\*/_]]/')

    def test_raw_escape(self):
        """Test path escapes."""

        check = self.check_escape
        check('abc', 'abc', raw=True)
        check('[', r'\[', raw=True)
        check('?', r'\?', raw=True)
        check('*', r'\*', raw=True)
        check('[[_/*?*/_]]', r'\[\[_/\*\?\*/_]]', raw=True)
        check('/[[_/*?*/_]]/', r'/\[\[_/\*\?\*/_]]/', raw=True)
        check(r'\x3f', r'\?', raw=True)

    @unittest.skipUnless(sys.platform == "win32", "Win32 specific test")
    def test_escape_windows(self):
        """Test windows escapes."""
        check = self.check_escape
        check('a:\\?', r'a:\\\?')
        check('b:\\*', r'b:\\\*')
        check(r'\\\\?\\c:\\?', r'\\\\?\\c:\\\?')
        check(r'\\\\*\\*\\*', r'\\\\*\\*\\\*')
        check('//?/c:/?', r'//?/c:/\?')
        check('//*/*/*', r'//*/*/\*')

    def test_recursive_glob(self):
        """Test recurision."""

        eq = self.assertSequencesEqual_noorder
        full = [
            ('EF',), ('ZZZ',),
            ('a',), ('a', 'D'),
            ('a', 'bcd'),
            ('a', 'bcd', 'EF'),
            ('a', 'bcd', 'efg'),
            ('a', 'bcd', 'efg', 'ha'),
            ('aaa',), ('aaa', 'zzzF'),
            ('aab',), ('aab', 'F'),
        ]
        if can_symlink():
            full += [
                ('sym1',), ('sym2',),
                ('sym3',),
                ('sym3', 'EF'),
                ('sym3', 'efg'),
                ('sym3', 'efg', 'ha'),
            ]
        eq(self.glob('**', flags=self.DEFAULT_FLAGS), self.joins(('',), *full))
        eq(self.glob('**', '**', flags=self.DEFAULT_FLAGS), self.joins(('',), *full))
        eq(self.glob(os.curdir, '**'),
            self.joins((os.curdir, ''), *((os.curdir,) + i for i in full)))
        dirs = [('a', ''), ('a', 'bcd', ''), ('a', 'bcd', 'efg', ''),
                ('aaa', ''), ('aab', '')]
        if can_symlink():
            dirs += [('sym3', ''), ('sym3', 'efg', '')]
        eq(self.glob('**', '', flags=self.DEFAULT_FLAGS), self.joins(('',), *dirs))

        eq(self.glob('a', '**', flags=self.DEFAULT_FLAGS), self.joins(
            ('a', ''), ('a', 'D'), ('a', 'bcd'), ('a', 'bcd', 'EF'),
            ('a', 'bcd', 'efg'), ('a', 'bcd', 'efg', 'ha')))
        eq(self.glob('a**', flags=self.DEFAULT_FLAGS), self.joins(('a',), ('aaa',), ('aab',)))
        expect = [('a', 'bcd', 'EF'), ('EF',)]
        if can_symlink():
            expect += [('sym3', 'EF')]
        eq(self.glob('**', 'EF', flags=self.DEFAULT_FLAGS), self.joins(*expect))
        expect = [('a', 'bcd', 'EF'), ('aaa', 'zzzF'), ('aab', 'F'), ('EF',)]
        if can_symlink():
            expect += [('sym3', 'EF')]
        eq(self.glob('**', '*F', flags=self.DEFAULT_FLAGS), self.joins(*expect))
        eq(self.glob('**', '*F', '', flags=self.DEFAULT_FLAGS), [])
        eq(self.glob('**', 'bcd', '*', flags=self.DEFAULT_FLAGS), self.joins(
            ('a', 'bcd', 'EF'), ('a', 'bcd', 'efg')))
        eq(self.glob('a', '**', 'bcd', flags=self.DEFAULT_FLAGS), self.joins(('a', 'bcd')))

        with change_cwd(self.tempdir):
            join = os.path.join
            eq(glob.glob('**', flags=self.DEFAULT_FLAGS), [join(*i) for i in full])
            eq(glob.glob(self.globjoin('**', ''), flags=self.DEFAULT_FLAGS),
                [join(*i) for i in dirs])
            eq(glob.glob(self.globjoin('**', '*'), flags=self.DEFAULT_FLAGS),
                [join(*i) for i in full])
            eq(glob.glob(self.globjoin(os.curdir, '**'), flags=self.DEFAULT_FLAGS),
                [join(os.curdir, '')] + [join(os.curdir, *i) for i in full])
            eq(glob.glob(self.globjoin(os.curdir, '**', ''), flags=self.DEFAULT_FLAGS),
                [join(os.curdir, '')] + [join(os.curdir, *i) for i in dirs])
            eq(glob.glob(self.globjoin(os.curdir, '**', '*'), flags=self.DEFAULT_FLAGS),
                [join(os.curdir, *i) for i in full])
            eq(glob.glob(self.globjoin('**', 'zz*F'), flags=self.DEFAULT_FLAGS),
                [join('aaa', 'zzzF')])
            eq(glob.glob('**zz*F', flags=self.DEFAULT_FLAGS), [])
            expect = [join('a', 'bcd', 'EF'), 'EF']
            if can_symlink():
                expect += [join('sym3', 'EF')]
            eq(glob.glob(self.globjoin('**', 'EF'), flags=self.DEFAULT_FLAGS), expect)


class GlobCornerCaseTests(unittest.TestCase):
    """Some tests that need a very specific file set to test against for corner cases."""

    DEFAULT_FLAGS = glob.BRACE | glob.EXTGLOB | glob.GLOBSTAR

    def norm(self, *parts):
        """Normalizes file path (in relation to temp dir)."""

        return os.path.join(self.tempdir, *parts)

    def globjoin(self, *parts):
        """Joins glob path."""

        sep = os.fsencode(self.globsep) if isinstance(parts[0], bytes) else self.globsep
        return sep.join(list(parts))

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
                except Exception:
                    retry -= 1
        create_empty_file(filename)

    def setUp(self):
        """Setup."""

        if os.sep == '/':
            self.globsep = os.sep
        else:
            self.globsep = r'\\'
        self.tempdir = TESTFN + "_dir"
        self.mktemp('test[')
        self.mktemp('a', 'b')
        self.mktemp('a[', ']b')
        self.mktemp('@(a', 'b)')
        self.mktemp('@(a[', ']b)')
        self.can_symlink = can_symlink()

    def tearDown(self):
        """Cleanup."""

        retry = 3
        while retry:
            try:
                shutil.rmtree(self.tempdir)
                retry = 0
            except Exception:
                retry -= 1

    def assertSequencesEqual_noorder(self, l1, l2):
        """Verify lists match (unordered)."""

        l1 = list(l1)
        l2 = list(l2)
        self.assertEqual(set(l1), set(l2))
        self.assertEqual(sorted(l1), sorted(l2))

    def glob(self, *parts, **kwargs):
        """Perform a glob with validation."""

        if parts:
            if len(parts) == 1:
                pattern = parts[0]
            else:
                pattern = self.globjoin(*parts)
            p = self.globjoin(self.tempdir, pattern)
        else:
            p = self.tempdir
        res = glob.glob(p, **kwargs)
        self.assertCountEqual(glob.iglob(p, **kwargs), res)
        bres = [os.fsencode(x) for x in res]
        self.assertCountEqual(glob.glob(os.fsencode(p), **kwargs), bres)
        self.assertCountEqual(glob.iglob(os.fsencode(p), **kwargs), bres)
        return res

    def test_special_cases(self):
        """Test very specific, special cases."""

        eq = self.assertSequencesEqual_noorder
        eq(self.glob('a[/]b', flags=self.DEFAULT_FLAGS), [self.norm('a[', ']b')])
        eq(self.glob('@(a/b)', flags=self.DEFAULT_FLAGS), [])
        eq(self.glob('@(a[/]b)', flags=self.DEFAULT_FLAGS), [])
        eq(self.glob('test[', flags=self.DEFAULT_FLAGS), [self.norm('test[')])
        eq(self.glob(r'a\/b', flags=self.DEFAULT_FLAGS), [self.norm('a', 'b')] if not util.is_case_sensitive() else [])
        eq(
            self.glob(r'a[\/]b', flags=self.DEFAULT_FLAGS),
            [self.norm('a[', ']b')] if not util.is_case_sensitive() else []
        )

        if not util.is_case_sensitive():
            eq(self.glob('a[\\', flags=self.DEFAULT_FLAGS), [self.norm('a[', '')])
            eq(self.glob('@(a[\\', flags=self.DEFAULT_FLAGS), [self.norm('@(a[', '')])


@skip_unless_symlink
class SymlinkLoopGlobTests(unittest.TestCase):
    """Symlink loop test case."""

    DEFAULT_FLAGS = glob.BRACE | glob.EXTGLOB | glob.GLOBSTAR

    def globjoin(self, *parts):
        """Joins glob path."""

        sep = os.fsencode(self.globsep) if isinstance(parts[0], bytes) else self.globsep
        return sep.join(list(parts))

    def setUp(self):
        """Setup."""

        if os.sep == '/':
            self.globsep = os.sep
        else:
            self.globsep = r'\\'

    def test_selflink(self):
        """Test self links."""

        tempdir = TESTFN + "_dir"
        os.makedirs(tempdir)
        self.addCleanup(shutil.rmtree, tempdir)
        with change_cwd(tempdir):
            os.makedirs('dir')
            create_empty_file(os.path.join('dir', 'file'))
            os.symlink(os.curdir, os.path.join('dir', 'link'))

            results = glob.glob('**', flags=self.DEFAULT_FLAGS)
            self.assertEqual(len(results), len(set(results)))
            results = set(results)
            depth = 0
            while results:
                path = os.path.join(*(['dir'] + ['link'] * depth))
                self.assertIn(path, results)
                results.remove(path)
                if not results:
                    break
                path = os.path.join(path, 'file')
                self.assertIn(path, results)
                results.remove(path)
                depth += 1

            results = glob.glob(os.path.join('**', 'file'), flags=self.DEFAULT_FLAGS)
            self.assertEqual(len(results), len(set(results)))
            results = set(results)
            depth = 0
            while results:
                path = os.path.join(*(['dir'] + ['link'] * depth + ['file']))
                self.assertIn(path, results)
                results.remove(path)
                depth += 1

            results = glob.glob(self.globjoin('**', ''), flags=self.DEFAULT_FLAGS)
            self.assertEqual(len(results), len(set(results)))
            results = set(results)
            depth = 0
            while results:
                path = os.path.join(*(['dir'] + ['link'] * depth + ['']))
                self.assertIn(path, results)
                results.remove(path)
                depth += 1
