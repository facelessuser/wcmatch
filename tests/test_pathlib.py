"""Test `pathlib`."""
import pytest
import unittest
import os
from wcmatch import pathlib


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
    """Test match method."""

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
