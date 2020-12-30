"""
These test cases are taken straight from `cpython` to ensure our glob works as good as the builtin.

Matches close to the normal glob implementation, but there are a few consciously
made difference in implementation.

1. Our glob will often return things like `.` and `..` matching Bash's behavior.
2. We do not normalize out `.` and `..`, so the norm function below just joins.
3. We escape with backslashes not `[]`.
4. A Window's path separator will be two backslashes in a pattern due to escape logic, not one.
"""
import contextlib
from wcmatch import glob
from wcmatch import pathlib
from wcmatch import _wcparse
from wcmatch import util
import re
import types
import pytest
import os
import shutil
import sys
import unittest
import warnings

# Below is general helper stuff that Python uses in `unittests`.  As these
# not meant for users, and could change without notice, include them
# ourselves so we aren't surprised later.
TESTFN = '@test'

# Disambiguate `TESTFN` for parallel testing, while letting it remain a valid
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
    except OSError:
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
        """Get option value."""

        return self._options.get(key, default)


class _TestGlob:
    """
    Test glob.

    Each list entry in `cases` is run through the `glob`, then the pattern and results are converted
    to bytes and run trough `glob` again. Results are checked against the provided result list.

    There are a couple special types that can be inserted in the case list that can alter
    the behavior of the cases that follow.

    * `Strings`: These will be printed and then the next case will be processed.
    * `Options`: This object takes keyword parameters that are used to alter the next tests options:
        * `absolute`: When joining path parts, due not append to the temporary directory.
        * `skip`: Skip tests when this is enabled.
        * `cwd_temp`: Switch the current working directory to the temp directory instead of having to prepend
            the temp directory to patterns and results.

    Each test case entry (list) is an array of up to 3 parameters (2 minimum).

    * Pattern: a list of path parts that are to be joined with the current OS separator.
    * Expected result (file names matched by the pattern): a list of sub-lists where each sub-list contains
        path parts that are to be joined with the current OS separator.
        Each path represents a full file path to match.
    * Flags

    The default flags are: `GLOBSTAR` | `EXTGLOB` | `BRACE` | `FOLLOW`. If any of these flags are provided in
    a test case, they will disable the default of the same name. All other flags will enable flags as expected.
    """

    DEFAULT_FLAGS = glob.BRACE | glob.EXTGLOB | glob.GLOBSTAR | glob.FOLLOW

    cases = []

    @classmethod
    def norm(cls, *parts):
        """Normalizes file path (in relation to temp directory)."""

        return os.path.join(cls.tempdir, *parts)

    @classmethod
    def res_norm(cls, *parts, absolute=False, mark=False):
        """Normalize results adding a trailing slash if mark flag is enabled."""

        if not absolute:
            path = os.path.join(cls.tempdir, *parts)
        else:
            path = os.path.join(*parts)
        if mark and os.path.isdir(os.path.join(cls.tempdir, *parts)):
            path = os.path.join(path, b'' if isinstance(path, bytes) else '')
        return path

    @classmethod
    def globjoin(cls, *parts):
        """Joins glob path."""

        sep = cls.globsep
        return sep.join(list(parts))

    @classmethod
    def mktemp(cls, *parts):
        """Make temp directory."""

        filename = cls.norm(*parts)
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

    @classmethod
    def setup_class(cls):
        """Setup."""

        cls.default_negate = '**'
        cls.absolute = False
        cls.skip = False
        cls.cwd_temp = False
        cls.just_negative = False
        if os.sep == '/':
            cls.globsep = os.sep
        else:
            cls.globsep = r'\\'
        cls.tempdir = TESTFN + "_dir"
        cls.setup_fs()

    @classmethod
    def setup_fs(cls):
        """Setup file system."""

    @classmethod
    def teardown_class(cls):
        """Cleanup."""

        retry = 3
        while retry:
            try:
                shutil.rmtree(cls.tempdir)
                retry = 0
            except Exception:
                retry -= 1

    @staticmethod
    def assert_equal(a, b):
        """Assert equal."""

        assert a == b, "Comparison between objects yielded false."

    @staticmethod
    def assert_count_equal(a, b):
        """Assert count equal."""

        c1 = len(list(a)) if isinstance(a, types.GeneratorType) else len(a)
        c2 = len(list(b)) if isinstance(b, types.GeneratorType) else len(b)
        assert c1 == c2, "Length of %d does not equal %d" % (c1, c2)

    @classmethod
    def glob(cls, *parts, **kwargs):
        """Perform a glob with validation."""

        if parts:
            if len(parts) == 1:
                p = parts[0]
            else:
                p = cls.globjoin(*parts)
            if not cls.absolute:
                p = cls.globjoin(cls.tempdir, p)
        else:
            p = cls.tempdir

        res = glob.glob(p, **kwargs)
        print("RESULTS: ", res)
        if res:
            cls.assert_equal({type(r) for r in res}, {str})
        cls.assert_count_equal(glob.iglob(p, **kwargs), res)

        if 'root_dir' in kwargs and kwargs['root_dir'] is not None:
            kwargs['root_dir'] = os.fsencode(kwargs['root_dir'])

        bres = [os.fsencode(x) for x in res]
        cls.assert_count_equal(glob.glob(os.fsencode(p), **kwargs), bres)
        cls.assert_count_equal(glob.iglob(os.fsencode(p), **kwargs), bres)
        if bres:
            cls.assert_equal({type(r) for r in bres}, {bytes})
        return res

    @classmethod
    def nglob(cls, *parts, **kwargs):
        """Perform a glob with validation."""

        if parts:
            if len(parts) == 1:
                p = parts[0]
            else:
                p = cls.globjoin(*parts)
            if not cls.absolute:
                p = cls.globjoin(cls.tempdir, p)
        else:
            p = cls.tempdir

        p = '!' + p
        if not cls.just_negative:
            if not cls.absolute:
                p = [cls.globjoin(cls.tempdir, cls.default_negate), p]
            else:
                p = [cls.default_negate, p]
        else:
            p = [p]
        res = glob.glob(p, **kwargs)
        print("RESULTS: ", sorted(res))
        if res:
            cls.assert_equal({type(r) for r in res}, {str})
        cls.assert_count_equal(glob.iglob(p, **kwargs), res)

        if 'root_dir' in kwargs and kwargs['root_dir'] is not None:
            kwargs['root_dir'] = os.fsencode(kwargs['root_dir'])

        bres = [os.fsencode(x) for x in res]
        cls.assert_count_equal(glob.glob([os.fsencode(x) for x in p], **kwargs), bres)
        cls.assert_count_equal(glob.iglob([os.fsencode(x) for x in p], **kwargs), bres)
        if bres:
            cls.assert_equal({type(r) for r in bres}, {bytes})
        return res

    @classmethod
    def assertSequencesEqual_noorder(cls, l1, l2):
        """Verify lists match (unordered)."""

        l1 = list(l1)
        l2 = list(l2)
        cls.assert_equal(set(l1), set(l2))
        cls.assert_equal(sorted(l1), sorted(l2))

    @classmethod
    def eval_glob_cases(cls, case):
        """Evaluate glob cases."""

        eq = cls.assertSequencesEqual_noorder

        # for case in self.cases:

        if isinstance(case, Options):
            absolute = case.get('absolute')
            if absolute is not None:
                cls.absolute = absolute
            skip = case.get('skip')
            if skip is not None:
                cls.skip = skip
            cwd_temp = case.get('cwd_temp')
            if cwd_temp is not None:
                cls.cwd_temp = cwd_temp
            just_negative = case.get('just_negative')
            if just_negative is not None:
                cls.just_negative = just_negative
            default_negate = case.get('default_negate')
            if default_negate is not None:
                cls.default_negate = default_negate
            pytest.skip("Change Options")

        if cls.skip:
            pytest.skip("Skipped")

        pattern = case[0]

        flags = cls.DEFAULT_FLAGS
        if len(case) > 2:
            flags ^= case[2]
        negative = flags & glob.N

        results = [
            cls.res_norm(*x, absolute=cls.absolute, mark=flags & glob.MARK) for x in case[1]
        ] if case[1] is not None else None

        print("PATTERN: ", pattern)
        print("FLAGS: ", bin(flags))
        print("NEGATIVE: ", bin(negative))
        print("EXPECTED: ", sorted(results) if results is not None else results)

        if cls.cwd_temp:
            if negative:
                res = cls.nglob(*pattern, flags=flags, root_dir=cls.tempdir)
            else:
                res = cls.glob(*pattern, flags=flags, root_dir=cls.tempdir)
        else:
            res = cls.nglob(*pattern, flags=flags) if negative else cls.glob(*pattern, flags=flags)
        if results is not None:
            eq(res, results)
        print('\n')


class Testglob(_TestGlob):
    """
    Test glob.

    See `_TestGlob` class for more information in regards to test case format.
    """

    cases = [
        # Test literal.
        [('a',), [('a',)]],
        [('a', 'D'), [('a', 'D')]],
        [('aab',), [('aab',)]],
        [('zymurgy',), []],
        Options(absolute=True),
        [['*'], None],
        [[os.curdir, '*'], None],
        Options(absolute=False),

        # Glob one directory
        [('a*',), [('a',), ('aab',), ('aaa',)]],
        [('*a',), [('a',), ('aaa',)]],
        [('.*',), [('.',), ('..',), ('.aa',), ('.bb',)], glob.SCANDOTDIR],
        [('.*',), [('.aa',), ('.bb',)]],
        [('?aa',), [('aaa',)]],
        [('aa?',), [('aaa',), ('aab',)]],
        [('aa[ab]',), [('aaa',), ('aab',)]],
        [('*q',), []],
        [('.',), [('.',)]],
        [('?',), [('a',)]],
        [('[.a]',), [('a',)]],
        [('*.',), []],

        # Glob with braces
        [('{a*,a*}',), [('a',), ('aab',), ('aaa',)]],

        # Glob with braces and "unique" turned off
        [('{a*,a*}',), [('a',), ('aab',), ('aaa',), ('a',), ('aab',), ('aaa',)], glob.Q],

        # Test recursive glob logic with no symlink following.
        [
            ('**', '*'),
            [
                ('aab',), ('aab', 'F'), ('a',), ('a', 'bcd'), ('a', 'bcd', 'EF'), ('a', 'bcd', 'efg'),
                ('a', 'bcd', 'efg', 'ha'), ('a', 'D'), ('aaa',), ('aaa', 'zzzF'), ('EF',), ('ZZZ',)
            ] if not can_symlink() else [
                ('aab',), ('aab', 'F'), ('a',), ('a', 'bcd'), ('a', 'bcd', 'EF'), ('a', 'bcd', 'efg'),
                ('a', 'bcd', 'efg', 'ha'), ('a', 'D'), ('aaa',), ('aaa', 'zzzF'), ('EF',), ('ZZZ',),
                ('sym1',), ('sym2',), ('sym3',)
            ],
            glob.L
        ],

        [
            ('**',),
            [
                ('',), ('aab',), ('aab', 'F'), ('a',), ('a', 'bcd'), ('a', 'bcd', 'EF'), ('a', 'bcd', 'efg'),
                ('a', 'bcd', 'efg', 'ha'), ('a', 'D'), ('aaa',), ('aaa', 'zzzF'), ('EF',), ('ZZZ',)
            ] if not can_symlink() else [
                ('',), ('aab',), ('aab', 'F'), ('a',), ('a', 'bcd'), ('a', 'bcd', 'EF'), ('a', 'bcd', 'efg'),
                ('a', 'bcd', 'efg', 'ha'), ('a', 'D'), ('aaa',), ('aaa', 'zzzF'), ('EF',), ('ZZZ',),
                ('sym1',), ('sym2',)
            ],
            glob.L
        ],

        Options(default_negate='**'),
        # Glob inverse
        [
            ('a*', '**'),
            [
                ('EF',), ('ZZZ',), ('',)
            ] if not can_symlink() else [
                ('EF',), ('ZZZ',), ('',), ('sym1',), ('sym3',), ('sym2',),
                ('sym3', 'efg'), ('sym3', 'efg', 'ha'), ('sym3', 'EF')
            ],
            glob.N
        ],

        Options(default_negate='sym3/EF'),
        [
            ('**', 'EF'),
            [
            ] if not can_symlink() else [
            ],
            glob.N | glob.L
        ],

        [
            ('**', 'EF'),
            [
            ] if not can_symlink() else [
            ],
            glob.N
        ],

        Options(default_negate='**'),

        # Disable symlinks
        [
            ('a*', '**'),
            [
                ('EF',), ('ZZZ',), ('',)
            ] if not can_symlink() else [
                ('EF',), ('ZZZ',), ('',), ('sym1',), ('sym2',)
            ],
            glob.N | glob.L
        ],

        Options(cwd_temp=True, absolute=True),
        # Test base matching
        [
            ('*',),
            [
                ('EF',), ('ZZZ',), ('a',), ('a', 'D'), ('a', 'bcd'), ('a', 'bcd', 'EF'),
                ('a', 'bcd', 'efg'), ('a', 'bcd', 'efg', 'ha'), ('aaa',), ('aaa', 'zzzF'), ('aab',),
                ('aab', 'F')
            ] if not can_symlink() else [
                ('EF',), ('ZZZ',), ('a',), ('a', 'D'), ('a', 'bcd'), ('a', 'bcd', 'EF'),
                ('a', 'bcd', 'efg'), ('a', 'bcd', 'efg', 'ha'), ('aaa',), ('aaa', 'zzzF'), ('aab',),
                ('aab', 'F'), ('sym1',), ('sym2',), ('sym3',)
            ],
            glob.L | glob.X
        ],

        # Test that base matching does not occur with a path pattern
        [
            ('aab', '*'),
            [('aab', 'F')],
            glob.L | glob.X
        ],
        Options(cwd_temp=False, absolute=False),

        [
            ('**',),
            [
                ('a', 'bcd', 'EF',), ('a', 'bcd', 'efg', 'ha',), ('a', 'D',),
                ('aaa', 'zzzF',), ('aab', 'F',), ('EF',), ('ZZZ',)
            ] if not can_symlink() else [
                ('a', 'bcd', 'EF',), ('a', 'bcd', 'efg', 'ha',), ('a', 'D',),
                ('aaa', 'zzzF',), ('aab', 'F',), ('EF',), ('sym1',), ('sym2',), ('ZZZ',)
            ],
            glob.L | glob.O
        ],

        # Test nested glob directory
        [
            ('a', 'bcd', 'E*'),
            [('a', 'bcd', 'EF')] if util.is_case_sensitive() else [('a', 'bcd', 'EF'), ('a', 'bcd', 'efg')]
        ],
        [('a', 'bcd', '*g'), [('a', 'bcd', 'efg')]],

        # Test case sensitive and insensitive
        [
            ('a', 'bcd', 'E*'),
            [('a', 'bcd', 'EF')],
            glob.C
        ],
        [
            ('a', 'bcd', 'E*'),
            [('a', 'bcd', 'EF'), ('a', 'bcd', 'efg')],
            glob.I
        ],

        # Test glob directory names.
        [('*', 'D'), [('a', 'D')]],
        [('*', '*a'), []],
        [('a', '*', '*', '*a'), [('a', 'bcd', 'efg', 'ha')]],
        [('?a?', '*F'), [('aaa', 'zzzF'), ('aab', 'F')]],

        # Test glob magic in drive name.
        Options(absolute=True, skip=sys.platform != "win32"),
        [('*:',), []],
        [('?:',), []],
        [(r'\\\\?\\c:\\',), [('\\\\?\\c:\\',)]],
        [(r'\\\\*\\*\\',), []],
        Options(absolute=False, skip=False),

        Options(skip=not can_symlink()),
        # Test broken symlinks
        [('sym*',), [('sym1',), ('sym2',), ('sym3',)]],
        [('sym1',), [('sym1',)]],
        [('sym2',), [('sym2',)]],

        # Test glob symlinks.,
        [('sym3',), [('sym3',)]],
        [('sym3', '*'), [('sym3', 'EF'), ('sym3', 'efg')]],
        [('sym3', ''), [('sym3', '')]],
        [('*', '*F'), [('aaa', 'zzzF'), ('aab', 'F'), ('sym3', 'EF')]],
        Options(skip=False),

        # Test only directories
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

        # Test `extglob`.
        [('@(a|aa*(a|b))',), [('aab',), ('aaa',), ('a',)]],

        # Test sequences.
        [('[a]',), [('a',)]],
        [('[!b]',), [('a',)]],
        [('[^b]',), [('a',)]],
        [(r'@([\a]|\aaa)',), [('a',), ('aaa',)]],

        Options(absolute=True),
        # Test empty.
        [('',), []],
        Options(absolute=False),

        # Patterns ending with a slash shouldn't match non-directories.
        [('Z*Z', ''), []],
        [('ZZZ', ''), []],
        [('aa*', ''), [('aaa', ''), ('aab', '')]],

        # Test recursion.
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
            # Directories
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
                ('.', 'aaa', ''), ('.', 'aab', '')
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
        Options(just_negative=True, default_negate='**'),
        [
            ('a*', '**'),
            [
            ] if not can_symlink() else [
            ],
            glob.N
        ],
        Options(just_negative=False, cwd_temp=False, absolute=False),

        # Test the file directly -- without magic.
        [[], [[]]]
    ]

    @classmethod
    def setup_fs(cls):
        """Setup file system."""

        cls.mktemp('a', 'D')
        cls.mktemp('aab', 'F')
        cls.mktemp('.aa', 'G')
        cls.mktemp('.bb', 'H')
        cls.mktemp('aaa', 'zzzF')
        cls.mktemp('ZZZ')
        cls.mktemp('EF')
        cls.mktemp('a', 'bcd', 'EF')
        cls.mktemp('a', 'bcd', 'efg', 'ha')
        cls.can_symlink = can_symlink()
        if cls.can_symlink:
            os.symlink(cls.norm('broken'), cls.norm('sym1'))
            os.symlink('broken', cls.norm('sym2'))
            os.symlink(os.path.join('a', 'bcd'), cls.norm('sym3'))

    @pytest.mark.parametrize("case", cases)
    def test_glob_cases(self, case):
        """Test glob cases."""

        self.eval_glob_cases(case)

    def test_negateall(self):
        """Negate applied to all files."""

        for file in glob.glob('!**/', flags=glob.N | glob.NEGATEALL | glob.G, root_dir=self.tempdir):
            self.assert_equal(os.path.isdir(file), False)

    def test_negateall_bytes(self):
        """Negate applied to all files."""

        for file in glob.glob(b'!**/', flags=glob.N | glob.NEGATEALL | glob.G, root_dir=os.fsencode(self.tempdir)):
            self.assert_equal(os.path.isdir(file), False)


class TestGlobMarked(Testglob):
    """Test glob marked."""

    DEFAULT_FLAGS = glob.BRACE | glob.EXTGLOB | glob.GLOBSTAR | glob.FOLLOW | glob.MARK


class TestPathlibNorm(unittest.TestCase):
    """Test normalization cases."""

    def test_norm(self):
        """Test normalization."""

        self.assertEqual(glob.Glob('.')._pathlib_norm('/./test'), '/test')
        self.assertEqual(glob.Glob('.')._pathlib_norm('/.'), '/')
        self.assertEqual(glob.Glob('.')._pathlib_norm('test/.'), 'test')
        self.assertEqual(glob.Glob('.')._pathlib_norm('test/./'), 'test')
        self.assertEqual(glob.Glob('.')._pathlib_norm('./.'), '')
        self.assertEqual(glob.Glob('.')._pathlib_norm('.'), '')
        self.assertEqual(glob.Glob('.')._pathlib_norm('test/./.test/'), 'test/.test')
        self.assertEqual(glob.Glob('.')._pathlib_norm('/.test/'), '/.test')
        self.assertEqual(glob.Glob('.')._pathlib_norm('/../../././.'), '/../..')
        self.assertEqual(glob.Glob('.')._pathlib_norm('./././././'), '')
        self.assertEqual(glob.Glob('.')._pathlib_norm('././../../'), '../..')
        self.assertEqual(glob.Glob('.')._pathlib_norm('/././../../'), '/../..')
        self.assertEqual(glob.Glob('.')._pathlib_norm('/'), '/')
        self.assertEqual(glob.Glob('.')._pathlib_norm('/.'), '/')
        self.assertEqual(glob.Glob('.')._pathlib_norm('./'), '')
        self.assertEqual(glob.Glob('.')._pathlib_norm('./test'), 'test')

    @unittest.skipUnless(sys.platform.startswith('win'), "Windows specific test")
    def test_norm_windows(self):
        """Test normalization on Windows."""

        self.assertEqual(glob.Glob('.')._pathlib_norm('\\.\\test'), '\\test')
        self.assertEqual(glob.Glob('.')._pathlib_norm('\\.'), '\\')
        self.assertEqual(glob.Glob('.')._pathlib_norm('test\\.'), 'test')
        self.assertEqual(glob.Glob('.')._pathlib_norm('test\\.\\'), 'test')
        self.assertEqual(glob.Glob('.')._pathlib_norm('.\\.'), '')
        self.assertEqual(glob.Glob('.')._pathlib_norm('.'), '')
        self.assertEqual(glob.Glob('.')._pathlib_norm('test\\.\\.test\\'), 'test\\.test')
        self.assertEqual(glob.Glob('.')._pathlib_norm('\\.test\\'), '\\.test')
        self.assertEqual(glob.Glob('.')._pathlib_norm('\\..\\..\\.\\.\\.'), '\\..\\..')
        self.assertEqual(glob.Glob('.')._pathlib_norm('.\\.\\.\\.\\.\\'), '')
        self.assertEqual(glob.Glob('.')._pathlib_norm('.\\.\\..\\..\\'), '..\\..')
        self.assertEqual(glob.Glob('.')._pathlib_norm('\\.\\.\\..\\..\\'), '\\..\\..')
        self.assertEqual(glob.Glob('.')._pathlib_norm('\\'), '\\')
        self.assertEqual(glob.Glob('.')._pathlib_norm('\\.'), '\\')
        self.assertEqual(glob.Glob('.')._pathlib_norm('.\\'), '')
        self.assertEqual(glob.Glob('.')._pathlib_norm('.\\test'), 'test')


class TestHidden(_TestGlob):
    """Test hidden specific cases."""

    cases = [
        [('**', '.*'), [('a', '.'), ('a', '..'), ('.aa',), ('.bb',), ('.',), ('..',)], glob.SCANDOTDIR],
        [('*', '.*'), [('a', '.'), ('a', '..')], glob.SCANDOTDIR],
        [('.*',), [('.aa',), ('.bb',), ('.',), ('..',)], glob.SCANDOTDIR],
        [
            ('**', '.*'),
            [
                ('a', '.'), ('a', '..'), ('.aa',), ('.aa', '.'), ('.aa', '..'),
                ('.bb',), ('.bb', '.'), ('.bb', '..'), ('.',), ('..',)
            ],
            glob.D | glob.SCANDOTDIR
        ],
        [
            ('**', '.*|**', '.', '.aa', '.'),
            [
                ('a', '.'), ('a', '..'), ('.aa',), ('.aa', '.'), ('.aa', '..'),
                ('.bb',), ('.bb', '.'), ('.bb', '..'), ('.',), ('..',), ('.', '.aa', '.')
            ],
            glob.D | glob.S | glob.SCANDOTDIR
        ],

        # Test `pathlib` mode. `pathlib` normalizes out `.` directories, so when evaluating unique values,
        # normalize paths with `.`.

        # Prevent matching `.aa` and `.aa/.` (same with `.bb`)
        [('**', '.*'), [('.aa',), ('.bb',)]],
        [('**', '.*'), [('.aa',), ('.bb',)], glob.Z],
        [('**', '.*'), [('.aa',), ('.bb',)], glob.SCANDOTDIR | glob.Z],

        [
            ('**', '.*'),
            [
                ('.aa',), ('.bb',)
            ],
            glob.D
        ],
        # Prevent matching `.aa/.` and `./.aa/.` as they are all the same as `.aa`
        [
            ('**', '.*|**', '.', '.aa', '.'),
            [
                ('.aa',), ('.bb',), ('.', '.aa', '.')
            ],
            glob.D | glob.S
        ],
        # Unique logic is disabled, so we can match `.aa` from one pattern and `./.aa/.` from another pattern.
        # Duplicates are still restricted from a single pattern, so `.aa/.` is not found in the first pattern as
        # `.aa` was already found, but unique results across multi-patterns is not enforced.
        [
            ('**', '.*|**', '.', '.aa', '.'),
            [
                ('.aa',), ('.bb',), ('.', '.aa', '.')
            ],
            glob.D | glob.S | glob.Q
        ],
        # Enable `pathlib` mode to ensure unique across multiple `pathlib` patterns.
        [
            ('**', '.*|**', '.', '.aa', '.'),
            [
                ('.aa',), ('.bb',)
            ],
            glob.D | glob.S | glob._PATHLIB
        ],
        # `NOUNIQUE` disables `pathlib` mode unique filtering.
        [
            ('**', '.*|**', '.', '.aa', '.'),
            [
                ('.aa',), ('.bb',), ('.', '.aa', '.')
            ],
            glob.D | glob.S | glob.Q | glob._PATHLIB
        ],
        # `pathlib` should still filter out duplicates if `.` and trailing slashes are normalized and
        # a single patter is used.
        [
            ('**', '.*'),
            [
                ('.', ), ('..', ), ('.aa',), ('.bb',), ('.bb', '..'),
                ('a', '.'), ('a', '..'), ('.aa', '..')
            ],
            glob.D | glob.S | glob.SCANDOTDIR | glob._PATHLIB
        ],

        Options(default_negate='**/./.*/*'),

        # `SCANDOTDIR` does not change our patterns (the negate pattern for instance),
        # just what is returned when scanning a folder with a wildcard.
        [
            ('**', '.*', '.aa', '*'),
            [
                ('.', '.bb', 'H')
            ],
            glob.D | glob.S | glob.N
        ],

        # Should we allow this? Or should `NODOTDIR` not apply to `NEGATE` patterns.
        [
            ('**', '.*', '.aa', '*'),
            [
                ('.', '.bb', 'H'), ('.', '.aa', 'G')
            ],
            glob.D | glob.S | glob.N | glob.Z
        ],

        Options(default_negate='**')
    ]

    @classmethod
    def setup_fs(cls):
        """Setup file system."""

        cls.mktemp('a', 'D')
        cls.mktemp('a', 'a')
        cls.mktemp('.aa', 'G')
        cls.mktemp('.bb', 'H')

    @pytest.mark.parametrize("case", cases)
    def test_glob_cases(self, case):
        """Test glob cases."""

        self.eval_glob_cases(case)


class TestCWD(_TestGlob):
    """Test files in the current working directory."""

    @classmethod
    def setup_fs(cls):
        """Setup file system."""

        cls.mktemp('a', 'D')
        cls.mktemp('aab', 'F')
        cls.mktemp('.aa', 'G')
        cls.mktemp('.bb', 'H')
        cls.mktemp('aaa', 'zzzF')
        cls.mktemp('ZZZ')
        cls.mktemp('EF')
        cls.mktemp('a', 'bcd', 'EF')
        cls.mktemp('a', 'bcd', 'efg', 'ha')
        cls.can_symlink = can_symlink()
        if cls.can_symlink:
            os.symlink(cls.norm('broken'), cls.norm('sym1'))
            os.symlink('broken', cls.norm('sym2'))
            os.symlink(os.path.join('a', 'bcd'), cls.norm('sym3'))

    def test_dots_cwd(self):
        """Test capture of dot files with recursive glob."""

        with change_cwd(self.tempdir):
            self.assert_equal(sorted(glob.glob(['**/.*', '!**/.', '!**/..'], flags=glob.G | glob.N)), ['.aa', '.bb'])

    def test_cwd(self):
        """Test root level glob on current working directory."""

        with change_cwd(self.tempdir):
            self.assert_equal(glob.glob('EF'), ['EF'])

    def test_cwd_root_dir(self):
        """Test root level glob when we switch directory via `root_dir`."""

        self.assert_equal(glob.glob('EF', root_dir=self.tempdir), ['EF'])

    def test_cwd_root_dir_pathlike(self):
        """Test root level glob when we switch directory via `root_dir` with a path-like object."""

        self.assert_equal(glob.glob('EF', root_dir=pathlib.Path(self.tempdir)), ['EF'])

    def test_cwd_root_dir_pathlike_bytes(self):
        """Test root level glob when we switch directory via `root_dir` with a path-like object."""

        self.assert_equal(glob.glob(b'EF', root_dir=pathlib.Path(self.tempdir)), [b'EF'])


class TestGlobCornerCase(_TestGlob):
    """
    Some tests that need a very specific file set to test against for corner cases.

    See `_TestGlob` class for more information in regards to test case format.
    """

    cases = [
        # Test very specific, special cases.
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

    @classmethod
    def setup_fs(cls):
        """Setup file system."""

        cls.mktemp('test[')
        cls.mktemp('a', 'b')
        cls.mktemp('a[', ']b')
        cls.mktemp('@(a', 'b)')
        cls.mktemp('@(a[', ']b)')
        cls.can_symlink = can_symlink()

    @pytest.mark.parametrize("case", cases)
    def test_glob_cases(self, case):
        """Test glob cases."""

        self.eval_glob_cases(case)


class TestGlobCornerCaseMarked(Testglob):
    """Test glob marked."""

    DEFAULT_FLAGS = glob.BRACE | glob.EXTGLOB | glob.GLOBSTAR | glob.FOLLOW | glob.MARK


class TestGlobEscapes(unittest.TestCase):
    """Test escaping."""

    def check_escape(self, arg, expected, raw=False, unix=None, raw_chars=True):
        """Verify escapes."""

        flags = 0
        if unix is False:
            flags = glob.FORCEWIN
        elif unix is True:
            flags = glob.FORCEUNIX

        if raw:
            self.assertEqual(glob.raw_escape(arg, unix=unix, raw_chars=raw_chars), expected)
            self.assertEqual(glob.raw_escape(os.fsencode(arg), unix=unix, raw_chars=raw_chars), os.fsencode(expected))
            file = (util.norm_pattern(arg, False, True) if raw_chars else arg).replace('\\\\', '\\')
            self.assertTrue(
                glob.globmatch(
                    file,
                    glob.raw_escape(arg, unix=unix, raw_chars=raw_chars),
                    flags=flags
                )
            )
        else:
            self.assertEqual(glob.escape(arg, unix=unix), expected)
            self.assertEqual(glob.escape(os.fsencode(arg), unix=unix), os.fsencode(expected))
            self.assertTrue(
                glob.globmatch(
                    arg,
                    glob.escape(arg, unix=unix),
                    flags=flags
                )
            )

    def test_escape(self):
        """Test path escapes."""

        check = self.check_escape
        check('abc', 'abc')
        check('[', r'\[')
        check('?', r'\?')
        check('*', r'\*')
        check('[[_/*?*/_]]', r'\[\[_/\*\?\*/_\]\]')
        check('/[[_/*?*/_]]/', r'/\[\[_/\*\?\*/_\]\]/')

    def test_raw_escape(self):
        """Test path escapes."""

        check = self.check_escape
        check(r'abc', 'abc', raw=True)
        check(r'[', r'\[', raw=True)
        check(r'?', r'\?', raw=True)
        check(r'*', r'\*', raw=True)
        check(r'[[_/*?*/_]]', r'\[\[_/\*\?\*/_\]\]', raw=True)
        check(r'/[[_/*?*/_]]/', r'/\[\[_/\*\?\*/_\]\]/', raw=True)
        check(r'\x3f', r'\?', raw=True)
        check(r'\\\\[^what]\\name\\temp', r'\\\\[^what]\\name\\temp', raw=True, unix=False)
        check('//[^what]/name/temp', r'//[^what]/name/temp', raw=True, unix=False)

    def test_raw_escape_no_raw_chars(self):
        """Test path escapes with no raw character translations."""

        check = self.check_escape
        check(r'abc', 'abc', raw=True, raw_chars=False)
        check(r'[', r'\[', raw=True, raw_chars=False)
        check(r'?', r'\?', raw=True, raw_chars=False)
        check(r'*', r'\*', raw=True, raw_chars=False)
        check(r'[[_/*?*/_]]', r'\[\[_/\*\?\*/_\]\]', raw=True, raw_chars=False)
        check(r'/[[_/*?*/_]]/', r'/\[\[_/\*\?\*/_\]\]/', raw=True, raw_chars=False)
        check(r'\x3f', r'\\x3f', raw=True, raw_chars=False)
        check(r'\\\\[^what]\\name\\temp', r'\\\\[^what]\\name\\temp', raw=True, raw_chars=False, unix=False)
        check('//[^what]/name/temp', r'//[^what]/name/temp', raw=True, raw_chars=False, unix=False)

    @unittest.skipUnless(sys.platform.startswith('win'), "Windows specific test")
    def test_escape_windows(self):
        """Test windows escapes."""

        check = self.check_escape
        check('a:\\?', r'a:\\\?')
        check('b:\\*', r'b:\\\*')
        check('\\\\?\\c:\\?', r'\\\\?\\c:\\\?')
        check('\\\\*\\*\\*', r'\\\\*\\*\\\*')
        check('//?/c:/?', r'//?/c:/\?')
        check('//*/*/*', r'//*/*/\*')
        check('//[^what]/name/temp', r'//[^what]/name/temp')

    def test_escape_forced_windows(self):
        """Test forced windows escapes."""

        check = self.check_escape
        check('a:\\?', r'a:\\\?', unix=False)
        check('b:\\*', r'b:\\\*', unix=False)
        check('\\\\?\\c:\\?', r'\\\\?\\c:\\\?', unix=False)
        check('\\\\*\\*\\*', r'\\\\*\\*\\\*', unix=False)
        check('//?/c:/?', r'//?/c:/\?', unix=False)
        check('//*/*/*', r'//*/*/\*', unix=False)
        check(
            '//./Volume{b75e2c83-0000-0000-0000-602f00000000}/temp',
            r'//./Volume\{b75e2c83-0000-0000-0000-602f00000000\}/temp',
            unix=False
        )
        check('//[^what]/name/temp', r'//[^what]/name/temp', unix=False)

    def test_escape_forced_unix(self):
        """Test forced windows Unix."""

        check = self.check_escape
        check('a:\\?', r'a:\\\?', unix=True)
        check('b:\\*', r'b:\\\*', unix=True)
        check('\\\\?\\c:\\?', r'\\\\\?\\c:\\\?', unix=True)
        check('\\\\*\\*\\*', r'\\\\\*\\\*\\\*', unix=True)
        check('//?/c:/?', r'//\?/c:/\?', unix=True)
        check('//*/*/*', r'//\*/\*/\*', unix=True)
        check('//[^what]/name/temp', r'//\[\^what\]/name/temp', unix=True)


@unittest.skipUnless(sys.platform.startswith('win'), "Windows specific test")
class TestWindowsDriveCase(unittest.TestCase):
    """Test Windows drive case."""

    RE_DRIVE = re.compile(r'((?:\\|/){2}[^\\/]+(?:\\|/){1}[^\\/]+|[a-z]:)((?:\\|/){1}|$)', re.I)

    def test_drive_insensitive(self):
        """Test drive case insensitivity."""

        cwd = os.getcwd()
        filepath = os.path.join(cwd, 'README.md')
        self.assertEqual([filepath], glob.glob(filepath.replace('\\', '\\\\')))
        self.assertEqual(
            [self.RE_DRIVE.sub(lambda m: m.group(0).upper(), filepath)],
            glob.glob(filepath.replace('\\', '\\\\').upper())
        )
        self.assertEqual(
            [self.RE_DRIVE.sub(lambda m: m.group(0).lower(), filepath)],
            glob.glob(filepath.replace('\\', '\\\\').lower())
        )

    def test_drive_sensitive(self):
        """Test drive case sensitivity (they'll be insensitive regardless of case flag)."""

        cwd = os.getcwd()
        filepath = os.path.join(cwd, 'README.md')
        self.assertEqual([filepath], glob.glob(filepath.replace('\\', '\\\\'), flags=glob.C))
        self.assertEqual(
            [self.RE_DRIVE.sub(lambda m: m.group(0).upper(), filepath)],
            glob.glob(self.RE_DRIVE.sub(lambda m: m.group(0).upper(), filepath).replace('\\', '\\\\'), flags=glob.C)
        )
        self.assertEqual(
            [self.RE_DRIVE.sub(lambda m: m.group(0).lower(), filepath)],
            glob.glob(self.RE_DRIVE.sub(lambda m: m.group(0).lower(), filepath).replace('\\', '\\\\'), flags=glob.C)
        )


@skip_unless_symlink
class TestSymlinkLoopGlob(unittest.TestCase):
    """Symlink loop test case."""

    DEFAULT_FLAGS = glob.BRACE | glob.EXTGLOB | glob.GLOBSTAR | glob.FOLLOW

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


class TestGlobPaths(unittest.TestCase):
    """Test `glob` paths."""

    def test_root(self):
        """Test that `glob` translates the root properly."""

        # On Windows, this should translate to the current drive.
        # On Linux/Unix, this should translate to the root.
        # Basically, we should not return an empty set.
        self.assertTrue(len(glob.glob('/*')) > 0)

    def test_start(self):
        """Test that starting directory/files are handled properly."""

        self.assertEqual(
            sorted(['docs', 'wcmatch', 'readme.md']),
            sorted([each.lower() for each in glob.glob(['BAD', 'docs', 'WCMATCH', 'readme.MD'], flags=glob.I)])
        )


@unittest.skipUnless(os.path.expanduser('~') != '~', "Requires expand user functionality")
class TestTilde(unittest.TestCase):
    """Test tilde cases."""

    def test_tilde(self):
        """Test tilde."""

        files = os.listdir(os.path.expanduser('~'))
        self.assertEqual(len(glob.glob('~/*', flags=glob.T | glob.D)), len(files))

    def test_tilde_bytes(self):
        """Test tilde in bytes."""

        files = os.listdir(os.path.expanduser(b'~'))
        self.assertEqual(len(glob.glob(b'~/*', flags=glob.T | glob.D)), len(files))

    def test_tilde_user(self):
        """Test tilde user cases."""

        user = os.path.basename(os.path.expanduser('~'))

        files = os.listdir(os.path.expanduser('~{}'.format(user)))
        self.assertEqual(len(glob.glob('~{}/*'.format(user), flags=glob.T | glob.D)), len(files))

    def test_tilde_disabled(self):
        """Test when tilde is disabled."""

        self.assertEqual(len(glob.glob('~/*', flags=glob.D)), 0)


class TestExpansionLimit(unittest.TestCase):
    """Test expansion limits."""

    def test_limit_glob(self):
        """Test expansion limit of `glob`."""

        with self.assertRaises(_wcparse.PatternLimitException):
            glob.glob('{1..11}', flags=glob.BRACE, limit=10)

    def test_limit_iglob(self):
        """Test expansion limit of `iglob`."""

        with self.assertRaises(_wcparse.PatternLimitException):
            list(glob.iglob('{1..11}', flags=glob.BRACE, limit=10))
