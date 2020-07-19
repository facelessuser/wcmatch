"""Test `pathlib`."""
import contextlib
import pytest
import unittest
import os
from wcmatch import pathlib, glob, _wcparse
import pathlib as pypathlib
import pickle
import warnings


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


class TestGlob(unittest.TestCase):
    """
    Test file globbing.

    NOTE: We are not testing the actual `glob` library, just the interface on the `pathlib` object and specifics
    introduced by the particular function.

    """

    def test_relative(self):
        """Test relative path."""

        abspath = os.path.abspath('.')
        p = pathlib.Path(abspath)
        with change_cwd(os.path.dirname(abspath)):
            results = list(p.glob('docs/**/*.md', flags=pathlib.GLOBSTAR))
        self.assertTrue(len(results))
        self.assertTrue(all([file.suffix == '.md' for file in results]))

    def test_relative_exclude(self):
        """Test relative path exclude."""

        abspath = os.path.abspath('.')
        p = pathlib.Path(abspath)
        with change_cwd(os.path.dirname(abspath)):
            results = list(p.glob('docs/**/*.md|!**/index.md', flags=pathlib.GLOBSTAR | pathlib.NEGATE | pathlib.SPLIT))
        self.assertTrue(len(results))
        self.assertTrue(all([file.name != 'index.md' for file in results]))

    def test_glob(self):
        """Test globbing function."""

        p = pathlib.Path('docs')
        results = list(p.glob('*.md'))
        self.assertTrue(not results)

        results = list(p.glob('**/*.md', flags=pathlib.GLOBSTAR))
        self.assertTrue(len(results))
        self.assertTrue(all([file.suffix == '.md' for file in results]))

    def test_rglob(self):
        """Test globbing function."""

        p = pathlib.Path('docs')
        results = list(p.rglob('*.md'))
        self.assertTrue(len(results))
        self.assertTrue(all([file.suffix == '.md' for file in results]))

        results = list(p.rglob('*.md'))
        self.assertTrue(len(results))
        self.assertTrue(all([file.suffix == '.md' for file in results]))

        results = list(p.rglob('markdown/*.md'))
        self.assertTrue(len(results))
        self.assertTrue(all([file.suffix == '.md' for file in results]))

    def test_integrity(self):
        """Test glob integrity, or better put, test the path structure comes out sane."""

        orig = [pathlib.Path(x) for x in glob.iglob('docs/**/*.md', flags=glob.GLOBSTAR)]
        results = list(pathlib.Path('docs').glob('**/*.md', flags=glob.GLOBSTAR))
        self.assertEqual(orig, results)

        orig = [pathlib.Path(x) for x in glob.iglob('**/*.md', flags=glob.GLOBSTAR)]
        results = list(pathlib.Path('').glob('**/*.md', flags=glob.GLOBSTAR))
        self.assertEqual(orig, results)


class TestPathlibGlobmatch:
    """
    Tests that are performed against `globmatch`.

    Each case entry is a list of 4 parameters.

    * Pattern
    * File name
    * Expected result (boolean of whether pattern matched file name)
    * Flags
    * Force Windows or Unix (string with `windows` or `unix`)

    The default flags are `NEGATE` | `EXTGLOB` | `BRACE`. Any flags passed through via entry are XORed.
    So if any of the default flags are passed via an entry, they will be disabled. All other flags will
    enable the feature.

    NOTE: We are not testing the actual `globmatch` library, just the interface on the `pathlib` object.

    """

    cases = [
        ['some/*/*/match', 'some/path/to/match', True, pathlib.G],
        ['some/**/match', 'some/path/to/match', False],
        ['some/**/match', 'some/path/to/match', True, pathlib.G],

        # `pathlib` doesn't keep trailing slash, so we can't tell it's a directory
        ['some/**/match/', 'some/path/to/match/', False, pathlib.G],
        ['.', '.', True],
        ['.', '', True],

        # `PurePath`
        ['some/*/*/match', 'some/path/to/match', True, pathlib.G, "pure"],
        ['some/**/match', 'some/path/to/match', False, 0, "pure"],
        ['some/**/match', 'some/path/to/match', True, pathlib.G, "pure"],
        ['some/**/match/', 'some/path/to/match/', False, pathlib.G, "pure"],
        ['.', '.', True, 0, "pure"],
        ['.', '', True, 0, "pure"],

        # Force a specific platform with a specific `PurePath`.
        ['//?/C:/**/file.log', r'\\?\C:\Path\path\file.log', True, pathlib.G, "windows"],
        ['/usr/*/bin', '/usr/local/bin', True, pathlib.G, "unix"]
    ]

    @classmethod
    def setup_class(cls):
        """Setup default flag options."""

        # The tests we scraped were written with this assumed.
        cls.flags = pathlib.NEGATE | pathlib.EXTGLOB | pathlib.BRACE

    @classmethod
    def evaluate(cls, case):
        """Evaluate case."""

        pattern = case[0]
        name = case[1]
        goal = case[2]
        flags = cls.flags
        path = None
        platform = "auto"
        if len(case) > 3:
            flags ^= case[3]
        if len(case) > 4:
            if case[4] == "windows":
                path = pathlib.PureWindowsPath(name)
                platform = case[4]
            elif case[4] == "unix":
                path = pathlib.PurePosixPath(name)
                platform = case[4]
            elif case[4] == "pure":
                path = pathlib.PurePath(name)
        if path is None:
            path = pathlib.Path(name)

        print('PATH: ', str(path))
        print("PATTERN: ", pattern)
        print("FILE: ", name)
        print("GOAL: ", goal)
        print("FLAGS: ", bin(flags))
        print("Platform: ", platform)

        cls.run(path, pattern, flags, goal)

    @classmethod
    def run(cls, path, pattern, flags, goal):
        """Run the command."""

        assert path.globmatch(pattern, flags=flags) == goal, "Expression did not evaluate as %s" % goal

    @pytest.mark.parametrize("case", cases)
    def test_cases(self, case):
        """Test ignore cases."""

        self.evaluate(case)


class TestPathlibMatch(TestPathlibGlobmatch):
    """
    Test match method.

    NOTE: We are not testing the actual `globmatch` library, just the interface on the `pathlib` object and the
    additional behavior that match injects (recursive logic).

    """

    cases = [
        ['match', 'some/path/to/match', True],
        ['to/match', 'some/path/to/match', True],
        ['path/to/match', 'some/path/to/match', True],
        ['some/**/match', 'some/path/to/match', False],
        ['some/**/match', 'some/path/to/match', True, pathlib.G]
    ]

    @classmethod
    def run(cls, path, pattern, flags, goal):
        """Run the command."""

        assert path.match(pattern, flags=flags) == goal, "Expression did not evaluate as %s" % goal


class TestRealpath(unittest.TestCase):
    """Test real path of pure paths."""

    def test_real_directory(self):
        """Test real directory."""

        p = pathlib.PurePath('wcmatch')
        self.assertTrue(p.globmatch('*/', flags=pathlib.REALPATH))
        self.assertTrue(p.globmatch('*', flags=pathlib.REALPATH))

    def test_real_file(self):
        """Test real file."""

        p = pathlib.PurePath('setup.py')
        self.assertFalse(p.globmatch('*/', flags=pathlib.REALPATH))
        self.assertTrue(p.globmatch('*', flags=pathlib.REALPATH))


class TestExceptions(unittest.TestCase):
    """Test exceptions."""

    def test_bad_path(self):
        """Test bad path."""

        with self.assertRaises(NotImplementedError):
            obj = pathlib.PosixPath if os.name == 'nt' else pathlib.WindowsPath
            obj('name')

    def test_bad_realpath(self):
        """Test bad real path."""

        with self.assertRaises(ValueError):
            obj = pathlib.PurePosixPath if os.name == 'nt' else pathlib.PureWindowsPath
            p = obj('wcmatch')
            p.globmatch('*', flags=pathlib.REALPATH)

    def test_absolute_glob(self):
        """Test absolute patterns in `pathlib` glob."""

        with self.assertRaises(ValueError):
            p = pathlib.Path('wcmatch')
            list(p.glob('/*'))

    def test_inverse_absolute_glob(self):
        """Test inverse absolute patterns in `pathlib` glob."""

        with self.assertRaises(ValueError):
            p = pathlib.Path('wcmatch')
            list(p.glob('!/*', flags=pathlib.NEGATE))


class TestComparisons(unittest.TestCase):
    """Test comparison."""

    def test_instance(self):
        """Test instance."""

        p1 = pathlib.Path('wcmatch')
        p2 = pypathlib.Path('wcmatch')

        self.assertTrue(isinstance(p1, pathlib.Path))
        self.assertTrue(isinstance(p1, pypathlib.Path))
        self.assertFalse(isinstance(p2, pathlib.Path))
        self.assertTrue(isinstance(p2, pypathlib.Path))

    def test_equal(self):
        """Test equivalence."""

        p1 = pathlib.Path('wcmatch')
        p2 = pypathlib.Path('wcmatch')
        p3 = pathlib.Path('docs')

        self.assertTrue(p1 == p2)
        self.assertFalse(p1 == p3)
        self.assertFalse(p3 == p2)

    def test_pure_equal(self):
        """Test equivalence."""

        p1 = pathlib.PureWindowsPath('wcmatch')
        p2 = pathlib.PurePosixPath('wcmatch')

        p3 = pypathlib.PureWindowsPath('wcmatch')
        p4 = pypathlib.PurePosixPath('wcmatch')

        self.assertTrue(p1 != p2)
        self.assertTrue(p3 != p4)

        self.assertTrue(p1 == p3)
        self.assertTrue(p2 == p4)

    def test_flavour_equal(self):
        """Test that the same flavours equal each other, regardless of path type."""

        p1 = pathlib.PurePath('wcmatch')
        p2 = pathlib.Path('wcmatch')

        p3 = pypathlib.PurePath('wcmatch')
        p4 = pypathlib.Path('wcmatch')

        self.assertTrue(p1 == p2)
        self.assertTrue(p3 == p4)
        self.assertTrue(p1 == p3)
        self.assertTrue(p2 == p4)
        self.assertTrue(p1 == p4)
        self.assertTrue(p2 == p3)

    def test_pickle(self):
        """Test pickling."""

        p1 = pathlib.PurePath('wcmatch')
        p2 = pathlib.Path('wcmatch')

        p3 = pickle.loads(pickle.dumps(p1))
        p4 = pickle.loads(pickle.dumps(p2))

        self.assertTrue(type(p1) == type(p3))
        self.assertTrue(type(p2) == type(p4))
        self.assertTrue(type(p1) != type(p2))
        self.assertTrue(type(p3) != type(p4))


class TestExpansionLimit(unittest.TestCase):
    """Test expansion limits."""

    def test_limit_globmatch(self):
        """Test expansion limit of `globmatch`."""

        with self.assertRaises(_wcparse.PatternLimitException):
            pathlib.PurePath('name').globmatch('{1..11}', flags=pathlib.BRACE, limit=10)

    def test_limit_match(self):
        """Test expansion limit of `match`."""

        with self.assertRaises(_wcparse.PatternLimitException):
            pathlib.PurePath('name').match('{1..11}', flags=pathlib.BRACE, limit=10)

    def test_limit_glob(self):
        """Test expansion limit of `glob`."""

        with self.assertRaises(_wcparse.PatternLimitException):
            list(pathlib.Path('.').glob('{1..11}', flags=pathlib.BRACE, limit=10))

    def test_limit_rglob(self):
        """Test expansion limit of `rglob`."""

        with self.assertRaises(_wcparse.PatternLimitException):
            list(pathlib.Path('.').rglob('{1..11}', flags=pathlib.BRACE, limit=10))
