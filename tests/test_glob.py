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


class Options():
    """Test options."""

    def __init__(self, **kwargs):
        """Initialize."""

        self._options = kwargs

    def get(self, key, default=None):
        """Get option vallue."""

        return self._options.get(key, default)


class _TestGlob(unittest.TestCase):
    """
    Test glob.

    Each list entry in `cases` is run through the `glob`, then the pattern and results are converted
    to bytes and run trough `glob` again. Results are checked against the provided result list.

    There are a couple special types that can be inserted in the case list that can alter
    the behavior of the cases that follow.

    * Strings: These will be printed and then the next case will be processed.
    * Options: This object takes keyword parameters that are used to alter the next tests options:
        * absolute: When joining path parts, due not append to the tempdir.
        * skip: Skip tests when this is enabled.
        * cwd_temp: Switch the current working directory to the temp directory instead of having to prepend
            the temp direcotry to patterns and results.

    Each test case entry (list) is an array of up to 3 parameters (2 minimum).

    * Pattern: a list of path parts that are to be joined with the current OS separator.
    * Expected result (filenames matched by the pattern): a list of sublists where each sublist contains
        path parts that are to be joined with the current OS separator.
        Each path represents a full file path ot match.
    * Flags

    The default flags are: GLOBSTAR | EXTGLOB | BRACE. If any of these flags are provided in
    a test case, they will disable the default of the same name. All other flags will enable flags as expected.
    """

    DEFAULT_FLAGS = glob.BRACE | glob.EXTGLOB | glob.GLOBSTAR

    cases = []

    def norm(self, *parts):
        """Normalizes file path (in relation to temp dir)."""

        if len(parts) and isinstance(parts[0], bytes):
            return os.path.join(os.fsencode(self.tempdir), *[os.fsencode(x) for x in parts])
        else:
            return os.path.join(self.tempdir, *parts)

    def globjoin(self, *parts):
        """Joins glob path."""

        sep = os.fsencode(self.globsep) if len(parts) and isinstance(parts[0], bytes) else self.globsep
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

        self.absolute = False
        self.skip = False
        self.cwd_temp = False
        if os.sep == '/':
            self.globsep = os.sep
        else:
            self.globsep = r'\\'
        self.tempdir = TESTFN + "_dir"
        self.setup_fs()

    def setup_fs(self):
        """Setup filesystem."""

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

        is_bytes = len(parts) and isinstance(parts[0], bytes)
        if parts:
            if len(parts) == 1:
                p = parts[0]
            else:
                p = self.globjoin(*parts)
            if not self.absolute:
                p = self.globjoin(self.tempdir, p)
        else:
            p = os.fsencode(self.tempdir) if is_bytes else self.tempdir

        res = glob.glob(p, **kwargs)
        if res:
            self.assertEqual({type(r) for r in res}, {str})
        self.assertCountEqual(glob.iglob(p, **kwargs), res)

        bres = [os.fsencode(x) for x in res]
        self.assertCountEqual(glob.glob(os.fsencode(p), **kwargs), bres)
        self.assertCountEqual(glob.iglob(os.fsencode(p), **kwargs), bres)
        if bres:
            self.assertEqual({type(r) for r in bres}, {bytes})
        return res

    def nglob(self, *parts, **kwargs):
        """Perform a glob with validation."""

        is_bytes = len(parts) and isinstance(parts[0], bytes)
        if parts:
            if len(parts) == 1:
                p = parts[0]
            else:
                p = self.globjoin(*parts)
            if not self.absolute:
                p = self.globjoin(self.tempdir, p)
        else:
            p = os.fsencode(self.tempdir) if is_bytes else self.tempdir

        p = (b'!' if is_bytes else '!') + p
        if not self.absolute:
            p = [self.globjoin(self.tempdir, (b'**' if is_bytes else '**')), p]
        else:
            p = [b'**' if is_bytes else '**', p]
        res = glob.glob(p, **kwargs)
        if res:
            self.assertEqual({type(r) for r in res}, {str})
        self.assertCountEqual(glob.iglob(p, **kwargs), res)

        bres = [os.fsencode(x) for x in res]
        self.assertCountEqual(glob.glob([os.fsencode(x) for x in p], **kwargs), bres)
        self.assertCountEqual(glob.iglob([os.fsencode(x) for x in p], **kwargs), bres)
        if bres:
            self.assertEqual({type(r) for r in bres}, {bytes})
        return res

    def assertSequencesEqual_noorder(self, l1, l2):
        """Verify lists match (unordered)."""

        l1 = list(l1)
        l2 = list(l2)
        self.assertEqual(set(l1), set(l2))
        self.assertEqual(sorted(l1), sorted(l2))

    def test_glob_cases(self):
        """Test glob cases."""

        eq = self.assertSequencesEqual_noorder

        for case in self.cases:

            if isinstance(case, Options):
                absolute = case.get('absolute')
                if absolute is not None:
                    self.absolute = absolute
                skip = case.get('skip')
                if skip is not None:
                    self.skip = skip
                cwd_temp = case.get('cwd_temp')
                if cwd_temp is not None:
                    self.cwd_temp = cwd_temp
                continue
            if isinstance(case, str):
                print(case)
                continue

            if self.skip:
                continue

            pattern = case[0]
            if not self.absolute:
                results = [self.norm(*x) for x in case[1]] if case[1] is not None else None
            else:
                results = [os.path.join(*list(x)) for x in case[1]] if case[1] is not None else None
            flags = self.DEFAULT_FLAGS

            if len(case) > 2:
                flags ^= case[2]

            negative = flags & glob.N

            print("PATTERN: ", pattern)
            print("FLAGS: ", bin(flags))
            print("NEGATIVE: ", bin(negative))
            print("EXPECTED: ", results)

            if self.cwd_temp:
                with change_cwd(self.tempdir):
                    res = self.nglob(*pattern, flags=flags) if negative else self.glob(*pattern, flags=flags)
            else:
                res = self.nglob(*pattern, flags=flags) if negative else self.glob(*pattern, flags=flags)
            if results is not None:
                print("RESULTS: ", res)
                eq(res, results)
            print('\n')


class Testglob(_TestGlob):
    """
    Test glob.

    See `_TestGlob` class for more information in regards to test case format.
    """

    cases = [
        "Test literal.",
        [('a',), [('a',)]],
        [('a', 'D'), [('a', 'D')]],
        [('aab',), [('aab',)]],
        [('zymurgy',), []],
        Options(absolute=True),
        [['*'], None],
        [[os.curdir, '*'], None],
        Options(absolute=False),

        "Glob one directory",
        [('a*',), [('a',), ('aab',), ('aaa',)]],
        [('*a',), [('a',), ('aaa',)]],
        [('.*',), [('.',), ('..',), ('.aa',), ('.bb',)]],
        [('?aa',), [('aaa',)]],
        [('aa?',), [('aaa',), ('aab',)]],
        [('aa[ab]',), [('aaa',), ('aab',)]],
        [('*q',), []],

        "Glob inverse",
        [
            ('a*',),
            [
                ('EF',), ('ZZZ',), ('',)
            ] if not can_symlink() else [
                ('EF',), ('ZZZ',), ('',), ('sym1',), ('sym3',), ('sym2',),
                ('sym3', 'efg'), ('sym3', 'efg', 'ha'), ('sym3', 'EF')
            ],
            glob.N
        ],

        "Test nested glob directory",
        [
            ('a', 'bcd', 'E*'),
            [('a', 'bcd', 'EF')] if util.is_case_sensitive() else [('a', 'bcd', 'EF'), ('a', 'bcd', 'efg')]
        ],
        [('a', 'bcd', '*g'), [('a', 'bcd', 'efg')]],

        "Test glob directory names.",
        [('*', 'D'), [('a', 'D')]],
        [('*', '*a'), []],
        [('a', '*', '*', '*a'), [('a', 'bcd', 'efg', 'ha')]],
        [('?a?', '*F'), [('aaa', 'zzzF'), ('aab', 'F')]],

        "Test glob magic in drive name.",
        Options(absolute=True, skip=sys.platform != "win32"),
        [('*:',), []],
        [('?:',), []],
        [(r'\\\\?\\c:\\',), [('\\\\?\\c:\\',)]],
        [(r'\\\\*\\*\\',), []],
        Options(absolute=False, skip=False),

        Options(skip=not can_symlink()),
        "Test broken symlinks",
        [('sym*',), [('sym1',), ('sym2',), ('sym3',)]],
        [('sym1',), [('sym1',)]],
        [('sym2',), [('sym2',)]],

        "Test glob symlinks.",
        [('sym3',), [('sym3',)]],
        [('sym3', '*'), [('sym3', 'EF'), ('sym3', 'efg')]],
        [('sym3', ''), [('sym3', '')]],
        [('*', '*F'), [('aaa', 'zzzF'), ('aab', 'F'), ('sym3', 'EF')]],
        Options(skip=False),

        "Test only directories",
        [
            ('*', ''),
            [
                ('aab', ''), ('aaa', ''), ('a', '')
            ] if not can_symlink() else [
                ('aab', ''), ('aaa', ''), ('a', ''), ('sym3', '')
            ]
        ],
        Options(skip=util.is_case_sensitive()),
        [
            ('*\\',),
            [
                ('aab', ''), ('aaa', ''), ('a', '')
            ] if not can_symlink() else [
                ('aab', ''), ('aaa', ''), ('a', ''), ('sym3', '')
            ]
        ],
        Options(skip=False),

        "Test extglob.",
        [('@(a|aa*(a|b))',), [('aab',), ('aaa',), ('a',)]],

        "Test sequences.",
        [('[a]',), [('a',)]],
        [('[!b]',), [('a',)]],
        [('[^b]',), [('a',)]],
        [(r'@([\a]|\aaa)',), [('a',), ('aaa',)]],

        Options(absolute=True),
        "Test empty.",
        [('',), []],
        Options(absolute=False),

        "Patterns ending with a slash shouldn't match non-dirs.",
        [('Z*Z', ''), []],
        [('ZZZ', ''), []],
        [('aa*', ''), [('aaa', ''), ('aab', '')]],

        "Test recurision.",
        [
            ('**',),
            [
                ('',),
                ('EF',), ('ZZZ',),
                ('a',), ('a', 'D'),
                ('a', 'bcd'),
                ('a', 'bcd', 'EF'),
                ('a', 'bcd', 'efg'),
                ('a', 'bcd', 'efg', 'ha'),
                ('aaa',), ('aaa', 'zzzF'),
                ('aab',), ('aab', 'F')
            ] if not can_symlink() else [
                ('',),
                ('EF',), ('ZZZ',),
                ('a',), ('a', 'D'),
                ('a', 'bcd'),
                ('a', 'bcd', 'EF'),
                ('a', 'bcd', 'efg'),
                ('a', 'bcd', 'efg', 'ha'),
                ('aaa',), ('aaa', 'zzzF'),
                ('aab',), ('aab', 'F'),
                ('sym1',), ('sym2',),
                ('sym3',),
                ('sym3', 'EF'),
                ('sym3', 'efg'),
                ('sym3', 'efg', 'ha')
            ]
        ],
        [
            ('**', '**'),
            [
                ('',),
                ('EF',), ('ZZZ',),
                ('a',), ('a', 'D'),
                ('a', 'bcd'),
                ('a', 'bcd', 'EF'),
                ('a', 'bcd', 'efg'),
                ('a', 'bcd', 'efg', 'ha'),
                ('aaa',), ('aaa', 'zzzF'),
                ('aab',), ('aab', 'F'),
            ] if not can_symlink() else [
                ('',),
                ('EF',), ('ZZZ',),
                ('a',), ('a', 'D'),
                ('a', 'bcd'),
                ('a', 'bcd', 'EF'),
                ('a', 'bcd', 'efg'),
                ('a', 'bcd', 'efg', 'ha'),
                ('aaa',), ('aaa', 'zzzF'),
                ('aab',), ('aab', 'F'),
                ('sym1',), ('sym2',),
                ('sym3',),
                ('sym3', 'EF'),
                ('sym3', 'efg'),
                ('sym3', 'efg', 'ha')
            ]
        ],
        [
            ('.', '**'),
            [
                ('.', ''),
                ('.', 'EF'), ('.', 'ZZZ'),
                ('.', 'a'), ('.', 'a', 'D'),
                ('.', 'a', 'bcd'),
                ('.', 'a', 'bcd', 'EF'),
                ('.', 'a', 'bcd', 'efg'),
                ('.', 'a', 'bcd', 'efg', 'ha'),
                ('.', 'aaa'), ('.', 'aaa', 'zzzF'),
                ('.', 'aab'), ('.', 'aab', 'F'),
            ] if not can_symlink() else [
                ('.', ''),
                ('.', 'EF'), ('.', 'ZZZ'),
                ('.', 'a'), ('.', 'a', 'D'),
                ('.', 'a', 'bcd'),
                ('.', 'a', 'bcd', 'EF'),
                ('.', 'a', 'bcd', 'efg'),
                ('.', 'a', 'bcd', 'efg', 'ha'),
                ('.', 'aaa'), ('.', 'aaa', 'zzzF'),
                ('.', 'aab'), ('.', 'aab', 'F'),
                ('.', 'sym1'), ('.', 'sym2'),
                ('.', 'sym3'),
                ('.', 'sym3', 'EF'),
                ('.', 'sym3', 'efg'),
                ('.', 'sym3', 'efg', 'ha')
            ]
        ],
        [
            ('**', ''),
            # Dirs
            [
                ('',),
                ('a', ''), ('a', 'bcd', ''), ('a', 'bcd', 'efg', ''),
                ('aaa', ''), ('aab', '')
            ] if not can_symlink() else [
                ('',),
                ('a', ''), ('a', 'bcd', ''), ('a', 'bcd', 'efg', ''),
                ('aaa', ''), ('aab', ''),
                ('sym3', ''), ('sym3', 'efg', '')
            ]
        ],
        [
            ('a', '**'),
            [('a', ''), ('a', 'D'), ('a', 'bcd'), ('a', 'bcd', 'EF'), ('a', 'bcd', 'efg'), ('a', 'bcd', 'efg', 'ha')]
        ],
        [('a**',), [('a',), ('aaa',), ('aab',)]],
        [
            ('**', 'EF'),
            [('a', 'bcd', 'EF'), ('EF',)] if not can_symlink() else [('a', 'bcd', 'EF'), ('EF',), ('sym3', 'EF')]
        ],
        [
            ('**', '*F'),
            [
                ('a', 'bcd', 'EF'), ('aaa', 'zzzF'), ('aab', 'F'), ('EF',)
            ] if not can_symlink() else [
                ('a', 'bcd', 'EF'), ('aaa', 'zzzF'), ('aab', 'F'), ('EF',), ('sym3', 'EF')
            ]
        ],
        [('**', '*F', ''), []],
        [('**', 'bcd', '*'), [('a', 'bcd', 'EF'), ('a', 'bcd', 'efg')]],
        [('a', '**', 'bcd'), [('a', 'bcd')]],
        Options(cwd_temp=True, absolute=True),
        [
            ('**',),
            [
                ('EF',), ('ZZZ',),
                ('a',), ('a', 'D'),
                ('a', 'bcd'),
                ('a', 'bcd', 'EF'),
                ('a', 'bcd', 'efg'),
                ('a', 'bcd', 'efg', 'ha'),
                ('aaa',), ('aaa', 'zzzF'),
                ('aab',), ('aab', 'F')
            ] if not can_symlink() else [
                ('EF',), ('ZZZ',),
                ('a',), ('a', 'D'),
                ('a', 'bcd'),
                ('a', 'bcd', 'EF'),
                ('a', 'bcd', 'efg'),
                ('a', 'bcd', 'efg', 'ha'),
                ('aaa',), ('aaa', 'zzzF'),
                ('aab',), ('aab', 'F'),
                ('sym1',), ('sym2',),
                ('sym3',),
                ('sym3', 'EF'),
                ('sym3', 'efg'),
                ('sym3', 'efg', 'ha')
            ]
        ],
        [
            ('**', '*'),
            [
                ('EF',), ('ZZZ',),
                ('a',), ('a', 'D'),
                ('a', 'bcd'),
                ('a', 'bcd', 'EF'),
                ('a', 'bcd', 'efg'),
                ('a', 'bcd', 'efg', 'ha'),
                ('aaa',), ('aaa', 'zzzF'),
                ('aab',), ('aab', 'F')
            ] if not can_symlink() else [
                ('EF',), ('ZZZ',),
                ('a',), ('a', 'D'),
                ('a', 'bcd'),
                ('a', 'bcd', 'EF'),
                ('a', 'bcd', 'efg'),
                ('a', 'bcd', 'efg', 'ha'),
                ('aaa',), ('aaa', 'zzzF'),
                ('aab',), ('aab', 'F'),
                ('sym1',), ('sym2',),
                ('sym3',),
                ('sym3', 'EF'),
                ('sym3', 'efg'),
                ('sym3', 'efg', 'ha')
            ]
        ],
        [
            (os.curdir, '**'),
            [
                ('.', ''),
                ('.', 'EF'), ('.', 'ZZZ'),
                ('.', 'a',), ('.', 'a', 'D'),
                ('.', 'a', 'bcd'),
                ('.', 'a', 'bcd', 'EF'),
                ('.', 'a', 'bcd', 'efg'),
                ('.', 'a', 'bcd', 'efg', 'ha'),
                ('.', 'aaa'), ('.', 'aaa', 'zzzF'),
                ('.', 'aab'), ('.', 'aab', 'F')
            ] if not can_symlink() else [
                ('.', ''),
                ('.', 'EF',), ('.', 'ZZZ'),
                ('.', 'a',), ('.', 'a', 'D'),
                ('.', 'a', 'bcd'),
                ('.', 'a', 'bcd', 'EF'),
                ('.', 'a', 'bcd', 'efg'),
                ('.', 'a', 'bcd', 'efg', 'ha'),
                ('.', 'aaa'), ('.', 'aaa', 'zzzF'),
                ('.', 'aab'), ('.', 'aab', 'F'),
                ('.', 'sym1'), ('.', 'sym2'),
                ('.', 'sym3'),
                ('.', 'sym3', 'EF'),
                ('.', 'sym3', 'efg'),
                ('.', 'sym3', 'efg', 'ha')
            ]
        ],
        [
            (os.curdir, '**', '*'),
            [
                ('.', 'EF'), ('.', 'ZZZ'),
                ('.', 'a',), ('.', 'a', 'D'),
                ('.', 'a', 'bcd'),
                ('.', 'a', 'bcd', 'EF'),
                ('.', 'a', 'bcd', 'efg'),
                ('.', 'a', 'bcd', 'efg', 'ha'),
                ('.', 'aaa'), ('.', 'aaa', 'zzzF'),
                ('.', 'aab'), ('.', 'aab', 'F')
            ] if not can_symlink() else [
                ('.', 'EF',), ('.', 'ZZZ'),
                ('.', 'a',), ('.', 'a', 'D'),
                ('.', 'a', 'bcd'),
                ('.', 'a', 'bcd', 'EF'),
                ('.', 'a', 'bcd', 'efg'),
                ('.', 'a', 'bcd', 'efg', 'ha'),
                ('.', 'aaa'), ('.', 'aaa', 'zzzF'),
                ('.', 'aab'), ('.', 'aab', 'F'),
                ('.', 'sym1'), ('.', 'sym2'),
                ('.', 'sym3'),
                ('.', 'sym3', 'EF'),
                ('.', 'sym3', 'efg'),
                ('.', 'sym3', 'efg', 'ha')
            ]
        ],
        [
            ('**', ''),
            [
                ('a', ''), ('a', 'bcd', ''), ('a', 'bcd', 'efg', ''),
                ('aaa', ''), ('aab', '')
            ] if not can_symlink() else [
                ('a', ''), ('a', 'bcd', ''), ('a', 'bcd', 'efg', ''),
                ('aaa', ''), ('aab', ''),
                ('sym3', ''), ('sym3', 'efg', '')
            ]
        ],
        [
            (os.curdir, '**', ''),
            [
                ('.', ''),
                ('.', 'a', ''), ('.', 'a', 'bcd', ''), ('.', 'a', 'bcd', 'efg', ''),
                ('aaa', ''), ('.', 'aab', '')
            ] if not can_symlink() else [
                ('.', ''),
                ('.', 'a', ''), ('.', 'a', 'bcd', ''), ('.', 'a', 'bcd', 'efg', ''),
                ('.', 'aaa', ''), ('.', 'aab', ''),
                ('.', 'sym3', ''), ('.', 'sym3', 'efg', '')
            ]
        ],
        [('**', 'zz*F'), [('aaa', 'zzzF')]],
        [('**zz*F',), []],
        [
            ('**', 'EF'),
            [('a', 'bcd', 'EF'), ('EF',)] if not can_symlink() else [('a', 'bcd', 'EF'), ('EF',), ('sym3', 'EF')]
        ],
        [
            ('a*',),
            [
                ('EF',), ('ZZZ',)
            ] if not can_symlink() else [
                ('EF',), ('ZZZ',),
                ('sym1',), ('sym3',), ('sym2',), ('sym3', 'efg'), ('sym3', 'efg', 'ha'), ('sym3', 'EF')
            ],
            glob.N
        ],
        Options(cwd_temp=False, absolute=False),

        "Test the file directly -- without magic.",
        [[], [[]]]
    ]

    def setup_fs(self):
        """Setup filesystem."""

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


class TestGlobCornerCase(_TestGlob):
    """
    Some tests that need a very specific file set to test against for corner cases.

    See _TestGlob class for more information in regards to test case format.
    """

    cases = [
        "Test very specific, special cases.",
        [('a[/]b',), [('a[', ']b',)]],
        [('@(a/b)',), []],
        [('@(a[/]b)',), []],
        [('test[',), [('test[',)]],
        [(r'a\/b',), [('a', 'b')] if not util.is_case_sensitive() else []],
        [(r'a[\/]b',), [('a[', ']b')] if not util.is_case_sensitive() else []],

        Options(skip=util.is_case_sensitive()),
        [('a[\\',), [('a[', '')]],
        [('@(a[\\',), [('@(a[', '')]],
        Options(skip=False)
    ]

    def setup_fs(self):
        """Setup filesystem."""

        self.mktemp('test[')
        self.mktemp('a', 'b')
        self.mktemp('a[', ']b')
        self.mktemp('@(a', 'b)')
        self.mktemp('@(a[', ']b)')
        self.can_symlink = can_symlink()


class TestGlobEscapes(unittest.TestCase):
    """Test escaping."""

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
