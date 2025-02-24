# -*- coding: utf-8 -*-
"""Tests for `globmatch`."""
import unittest
import pytest
import copy
import re
import os
import sys
import wcmatch.glob as glob
import wcmatch._wcparse as _wcparse
import wcmatch.util as util
import shutil
import pathlib

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


class _TestGlobmatch(unittest.TestCase):
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
        self.default_flags = glob.G | glob.P

    def tearDown(self):
        """Cleanup."""

        retry = 3
        while retry:
            try:
                shutil.rmtree(self.tempdir)
                while os.path.exists(self.tempdir):
                    pass
                retry = 0
            except Exception:  # noqa: PERF203
                retry -= 1


class GlobFiles():
    """List of glob files."""

    def __init__(self, filelist, append=False):
        """File list object."""

        self.filelist = filelist
        self.append = append


class Options():
    """Test options."""

    def __init__(self, **kwargs):
        """Initialize."""

        self._options = kwargs

    def get(self, key, default=None):
        """Get option value."""

        return self._options.get(key, default)


class TestGlobFilter:
    """
    Test matches against `globfilter`.

    Each list entry in `cases` is run through the `globsplit` and then `globfilter`.
    Entries are run through `globsplit` ensure it does not add any unintended side effects.

    There are a couple special types that can be inserted in the case list that can alter
    the behavior of the cases that follow.

    * `Strings`: These will be printed and then the next case will be processed.
    * `Options`: This object takes keyword parameters that are used to alter the next tests options:
        * skip_split: If set to `True`, this will cause the next tests to be skipped when we are processing
            cases with `globsplit`.
    * `GlobFiles`: This object takes a list of file paths and will set them as the current file list to
        compare against.  If `append` is set to `True`, it will extend the test's file list instead of
        replacing.

    Each test case entry (list) is an array of up to 4 parameters (2 minimum).

    * Pattern
    * Expected result (filenames matched by the pattern)
    * Flags
    * List of files that will temporarily override the current main file list just for this specific case.

    The default flags are: `NEGATE` | `GLOBSTAR` | `EXTGLOB` | `BRACE`. If any of these flags are provided in
    a test case, they will disable the default of the same name. All other flags will enable flags as expected.

    """

    cases = [
        Options(skip_split=False),

        GlobFiles(
            [
                'a', 'b', 'c', 'd', 'abc',
                'abd', 'abe', 'bb', 'bcd',
                'ca', 'cb', 'dd', 'de',
                'bdir/', 'bdir/cfile'
            ]
        ),

        # http://www.bashcookbook.com/bashinfo/source/bash-1.14.7/tests/glob-test
        ['a*', ['a', 'abc', 'abd', 'abe']],

        ['X*', []],

        # Slightly different than `bash/sh/ksh`
        # \\* is not un-escaped to literal "*" in a failed match,
        # but it does make it get treated as a literal star
        ['\\*', []],
        ['\\**', []],
        ['\\*\\*', []],

        ['b*/', ['bdir/']],
        ['c*', ['c', 'ca', 'cb']],
        [
            '**',
            [
                'a', 'b', 'c', 'd', 'abc',
                'abd', 'abe', 'bb', 'bcd',
                'ca', 'cb', 'dd', 'de',
                'bdir/', 'bdir/cfile'
            ]
        ],

        [R'\\.\\./*/', []],
        [R's/\\..*//', []],

        # legendary Larry crashes bashes
        ['/^root:/{s/^[^:]*:[^:]*:\\([^:]*\\).*$/\\1/', []],
        ['/^root:/{s/^[^:]*:[^:]*:\\([^:]*\\).*$/\u0001/', []],

        # character classes
        ['[a-c]b*', ['abc', 'abd', 'abe', 'bb', 'cb']],
        ['[a-y]*[^c]', ['abd', 'abe', 'bb', 'bcd', 'bdir/', 'ca', 'cb', 'dd', 'de']],
        ['a*[^c]', ['abd', 'abe']],

        GlobFiles(['a-b', 'aXb'], append=True),
        ['a[X-]b', ['a-b', 'aXb']],
        GlobFiles(['.x', '.y'], append=True),
        ['[^a-c]*', ['d', 'dd', 'de']],
        GlobFiles(['a*b/', 'a*b/ooo'], append=True),
        ['a\\*b/*', ['a*b/ooo']],
        ['a\\*?/*', ['a*b/ooo']],
        ['*\\\\!*', [], 0, ['echo !7']],
        ['*\\!*', ['echo !7'], 0, ['echo !7']],
        ['*.\\*', ['r.*'], 0, ['r.*']],
        ['a[b]c', ['abc']],
        ['a[\\b]c', ['abc']],
        ['a?c', ['abc']],
        ['a\\*c', [], 0, ['abc']],
        ['', [''], 0, ['']],

        # http://www.opensource.apple.com/source/bash/bash-23/bash/tests/glob-test
        GlobFiles(['man/', 'man/man1/', 'man/man1/bash.1'], append=True),
        ['*/man*/bash.*', ['man/man1/bash.1']],
        ['man/man1/bash.1', ['man/man1/bash.1']],
        ['a***c', ['abc'], 0, ['abc']],
        ['a*****?c', ['abc'], 0, ['abc']],
        ['?*****??', ['abc'], 0, ['abc']],
        ['*****??', ['abc'], 0, ['abc']],
        ['?*****?c', ['abc'], 0, ['abc']],
        ['?***?****c', ['abc'], 0, ['abc']],
        ['?***?****?', ['abc'], 0, ['abc']],
        ['?***?****', ['abc'], 0, ['abc']],
        ['*******c', ['abc'], 0, ['abc']],
        ['*******?', ['abc'], 0, ['abc']],
        ['a*cd**?**??k', ['abcdecdhjk'], 0, ['abcdecdhjk']],
        ['a**?**cd**?**??k', ['abcdecdhjk'], 0, ['abcdecdhjk']],
        ['a**?**cd**?**??k***', ['abcdecdhjk'], 0, ['abcdecdhjk']],
        ['a**?**cd**?**??***k', ['abcdecdhjk'], 0, ['abcdecdhjk']],
        ['a**?**cd**?**??***k**', ['abcdecdhjk'], 0, ['abcdecdhjk']],
        ['a****c**?**??*****', ['abcdecdhjk'], 0, ['abcdecdhjk']],
        ['[-abc]', ['-'], 0, ['-']],
        ['[abc-]', ['-'], 0, ['-']],
        ['\\', [], 0, ['\\']],
        ['\\\\', ['\\'], 0, ['\\']],
        ['/', ['\\'], glob.W, ['\\']],
        ['/', ['/'], glob.U, ['/']],
        ['[\\\\]', (['\\'] if util.is_case_sensitive() else []), 0, ['\\']],
        ['[\\\\]', ['\\'], glob.U, ['\\']],
        ['[\\\\]', [], glob.W, ['\\']],
        ['[[]', ['['], 0, ['[']],
        ['[', ['['], 0, ['[']],
        ['[*', ['[abc'], 0, ['[abc']],

        # a right bracket shall lose its special meaning and\
        # represent itself in a bracket expression if it occurs\
        # first in the list.  -- POSIX.2 2.8.3.2
        ['[]]', [']'], 0, [']']],
        ['[]-]', [']'], 0, [']']],
        ['[a-\\z]', ['p'], 0, ['p']],
        ['??**********?****?', [], 0, ['abc']],
        ['??**********?****c', [], 0, ['abc']],
        ['?************c****?****', [], 0, ['abc']],
        ['*c*?**', [], 0, ['abc']],
        ['a*****c*?**', [], 0, ['abc']],
        ['a********???*******', [], 0, ['abc']],
        ['[]', [], 0, ['a']],
        ['[abc', [], 0, ['[']],

        # No case tests
        ['XYZ', ['xYz'], glob.I, ['xYz', 'ABC', 'IjK']],
        [
            'ab*',
            ['ABC'],
            glob.I,
            ['xYz', 'ABC', 'IjK']
        ],
        [
            '[ia]?[ck]',
            ['ABC', 'IjK'],
            glob.I,
            ['xYz', 'ABC', 'IjK']
        ],

        # [ pattern, [matches], MM opts, files, TAP opts]
        # one star/two star
        ['{/*,*}', [], 0, ['/asdf/asdf/asdf']],
        ['{/?,*}', ['/a', 'bb'], 0, ['/a', '/b/b', '/a/b/c', 'bb']],

        # dots should not match unless requested
        ['**', ['a/b'], 0, ['a/b', 'a/.d', '.a/.d']],

        # .. and . can only match patterns starting with .,
        # even when options.dot is set.
        GlobFiles(['a/./b', 'a/../b', 'a/c/b', 'a/.d/b']),
        ['a/*/b', ['a/c/b', 'a/.d/b'], glob.D],
        ['a/.*/b', ['a/./b', 'a/../b', 'a/.d/b'], glob.D],
        ['a/*/b', ['a/c/b'], 0],
        ['a/.*/b', ['a/./b', 'a/../b', 'a/.d/b'], 0],
        ['a/.*/b', ['a/.d/b'], glob.Z],
        # Escaped `.` will still be treated as a `.`
        [R'a/\.*/b', ['a/./b', 'a/../b', 'a/.d/b'], 0],
        [R'a/\.*/b', ['a/.d/b'], glob.Z],

        # this also tests that changing the options needs
        # to change the cache key, even if the pattern is
        # the same!
        [
            '**',
            ['a/b', 'a/.d', '.a/.d'],
            glob.D,
            ['.a/.d', 'a/.d', 'a/b']
        ],

        # paren sets cannot contain slashes
        ['*(a/b)', [], 0, ['a/b']],

        # brace sets trump all else.
        #
        # invalid glob pattern.  fails on bash4 and `bsdglob`.
        # however, in this implementation, it's easier just
        # to do the intuitive thing, and let brace-expansion
        # actually come before parsing any `extglob` patterns,
        # like the documentation seems to say.
        #
        # XXX: if anyone complains about this, either fix it
        # or tell them to grow up and stop complaining.
        #
        # `bash/bsdglob` says this:
        # , ["*(a|{b),c)}", ["*(a|{b),c)}"], {}, ["a", "ab", "ac", "ad"]]
        # but we do this instead:
        ['*(a|{b),c)}', ['a', 'ab', 'ac'], 0, ['a', 'ab', 'ac', 'ad']],

        # test partial parsing in the presence of comment/negation chars
        # NOTE: We don't support these so they should work fine.
        ['[!a*', ['[!ab'], 0, ['[!ab', '[ab']],
        ['[#a*', ['[#ab'], 0, ['[#ab', '[ab']],

        # The following tests have `|` not included in things like +(...) etc.
        # We run these tests through normally and through `glob.globsplit` which splits
        # patterns on unenclosed `|`, so disable these few tests during split tests.
        Options(skip_split=True),
        # like: {a,b|c\\,d\\\|e} except it's unclosed, so it has to be escaped.
        # NOTE: I don't know what the original test was doing because it was matching
        # something crazy. `Multimatch` regex expanded to escapes to like a 50.
        # I think ours expands them proper, so the original test has been altered.
        [
            '+(a|*\\|c\\\\|d\\\\\\|e\\\\\\\\|f\\\\\\\\\\|g',
            (['+(a|b\\|c\\|d\\|e\\\\|f\\\\|g'] if util.is_case_sensitive() else []),
            0,
            ['+(a|b\\|c\\|d\\|e\\\\|f\\\\|g', 'a', 'b\\c']
        ],
        [
            '+(a|*\\|c\\\\|d\\\\\\|e\\\\\\\\|f\\\\\\\\\\|g',
            ['+(a|b\\|c\\|d\\|e\\\\|f\\\\|g'],
            glob.U,
            ['+(a|b\\|c\\|d\\|e\\\\|f\\\\|g', 'a', 'b\\c']
        ],
        [
            '+(a|*\\|c\\\\|d\\\\\\|e\\\\\\\\|f\\\\\\\\\\|g',
            [],
            glob.W,
            ['+(a|b\\|c\\|d\\|e\\\\|f\\\\|g', 'a', 'b\\c']
        ],

        # crazy nested {,,} and *(||) tests.
        GlobFiles(
            [
                'a', 'b', 'c', 'd', 'ab', 'ac', 'ad', 'bc', 'cb', 'bc,d',
                'c,db', 'c,d', 'd)', '(b|c', '*(b|c', 'b|c', 'b|cc', 'cb|c',
                'x(a|b|c)', 'x(a|c)', '(a|b|c)', '(a|c)'
            ]
        ),
        ['*(a|{b,c})', ['a', 'b', 'c', 'ab', 'ac']],
        ['{a,*(b|c,d)}', ['a', '(b|c', '*(b|c', 'd)']],
        # a
        # *(b|c)
        # *(b|d)
        ['{a,*(b|{c,d})}', ['a', 'b', 'bc', 'cb', 'c', 'd']],
        ['*(a|{b|c,c})', ['a', 'b', 'c', 'ab', 'ac', 'bc', 'cb']],

        # test various flag settings.
        [
            '*(a|{b|c,c})',
            ['x(a|b|c)', 'x(a|c)', '(a|b|c)', '(a|c)'],
            glob.E
        ],

        Options(skip_split=False),
        # test `extglob` nested in `extglob`
        [
            '@(a@(c|d)|c@(b|,d))',
            ['ac', 'ad', 'cb', 'c,d']
        ],

        # Negation and extended glob together
        # `!` will be treated as an exclude pattern if it isn't followed by `(`.
        # `(` must be escaped to exclude a name that starts with `(`.
        # If `!(` doesn't start a valid extended glob pattern,
        # it will be treated as a literal, not an exclude pattern.
        Options(skip_split=True),
        [
            R'!\(a|c)',
            [
                '(a|b|c)', '(b|c', '*(b|c', 'a', 'ab', 'ac', 'ad', 'b', 'bc', 'bc,d', 'b|c', 'b|cc',
                'c', 'c,d', 'c,db', 'cb', 'cb|c', 'd', 'd)', 'x(a|b|c)', 'x(a|c)'
            ],
            glob.A
        ],
        [
            '!(a|c)',
            [
                '(a|b|c)', '(a|c)', '(b|c', '*(b|c', 'ab', 'ac', 'ad', 'b', 'bc', 'bc,d', 'b|c', 'b|cc',
                'c,d', 'c,db', 'cb', 'cb|c', 'd', 'd)', 'x(a|b|c)', 'x(a|c)'
            ],
            glob.A
        ],
        ['!!(a|c)', ['a', 'c'], glob.A],
        ['!(a|c*', [], glob.A],
        Options(skip_split=False),

        # Test `MATCHBASE`.
        [
            'a?b',
            ['x/y/acb', 'acb/'],
            glob.X,
            ['x/y/acb', 'acb/', 'acb/d/e', 'x/y/acb/d']
        ],

        # Test that `MATCHBASE` isn't enabled after `GLOBSTAR` patterns with slashes
        # If `MATCHBASE` was still enabled, the `.y` folder would be gobbled up.
        [
            '**/acb',
            ['acb/'],
            glob.X,
            ['x/.y/acb', 'acb/', 'acb/d/e', 'x/.y/acb/d']
        ],
        [
            '**/acb',
            ['x/.y/acb', 'acb/'],
            glob.X | glob.D,
            ['x/.y/acb', 'acb/', 'acb/d/e', 'x/.y/acb/d']
        ],

        ['#*', ['#a', '#b'], 0, ['#a', '#b', 'c#d']],

        # begin channelling Boole and deMorgan...
        # NOTE: We changed these to `-` since our negation doesn't use `!`.
        # negation tests
        GlobFiles(['d', 'e', '!ab', '!abc', 'a!b', '\\!a']),

        # anything that is NOT a* matches.
        ['**|!a*', ['\\!a', 'd', 'e', '!ab', '!abc'], glob.S],

        # anything that IS !a* matches.
        ['!a*', ['!ab', '!abc'], glob.N],

        # NOTE: We don't allow negating negation.
        # # anything that IS a* matches
        # ['!!a*', ['a!b']],

        # anything that is NOT !a* matches
        ['**|!\\!a*', ['a!b', 'd', 'e', '\\!a'], glob.S],

        # negation nestled within a pattern
        GlobFiles(
            [
                'foo.js',
                'foo.bar',
                'foo.js.js',
                'blar.js',
                'foo.',
                'boo.js.boo'
            ]
        ),
        # last one is tricky! * matches foo, . matches ., and `'js.js' != 'js'`
        # copy bash 4.3 behavior on this.
        ['*.!(js)', ['foo.bar', 'foo.', 'boo.js.boo', 'foo.js.js']],

        # https://github.com/isaacs/minimatch/issues/5
        GlobFiles(
            [
                'a/b/.x/c', 'a/b/.x/c/d', 'a/b/.x/c/d/e', 'a/b/.x', 'a/b/.x/',
                'a/.x/b', '.x', '.x/', '.x/a', '.x/a/b', 'a/.x/b/.x/c', '.x/.x',
                'test.x/a'
            ]
        ),
        [
            '**/.x/**',
            [
                '.x/', '.x/a', '.x/a/b', 'a/.x/b', 'a/b/.x/', 'a/b/.x/c',
                'a/b/.x/c/d', 'a/b/.x/c/d/e'
            ]
        ],

        [
            '**.x/*',
            [
                'test.x/a', '.x/a'
            ]
        ],

        [
            R'**\.x/*',
            [
                'test.x/a', '.x/a'
            ]
        ],

        # https://github.com/isaacs/minimatch/issues/59
        ['[z-a]', []],
        ['a/[2015-03-10T00:23:08.647Z]/z', []],
        ['[a-0][a-\u0100]', []],

        # Consecutive slashes.
        GlobFiles(
            [
                'a/b/c', 'd/e/f', 'a/e/c'
            ]
        ),
        ['*//e///*', ['d/e/f', 'a/e/c']],
        [R'*//\e///*', ['d/e/f', 'a/e/c']],

        # Backslash trailing cases
        GlobFiles(
            [
                'a/b/c/', 'd/e/f/', 'a/e/c/'
            ]
        ),
        ['**\\', ['a/b/c/', 'd/e/f/', 'a/e/c/']],
        ['**\\', ['a/b/c/', 'd/e/f/', 'a/e/c/'], glob.U],
        ['**\\', ['a/b/c/', 'd/e/f/', 'a/e/c/'], glob.W],
        [R'**\\', [] if util.is_case_sensitive() else ['a/b/c/', 'd/e/f/', 'a/e/c/']],
        [R'**\\', [], glob.U],
        [R'**\\', ['a/b/c/', 'd/e/f/', 'a/e/c/'], glob.W],

        # Invalid `extglob` groups
        GlobFiles(
            [
                '@([test', '@([test\\', '@(test\\', 'test['
            ]
        ),
        ['@([test', ['@([test'] if util.is_case_sensitive() else ['@([test', '@([test\\']],
        ['@([test', ['@([test'], glob.U],
        ['@([test', ['@([test', '@([test\\'], glob.W],
        ['@([test\\', ['@([test'] if util.is_case_sensitive() else ['@([test', '@([test\\']],
        ['@(test\\', [] if util.is_case_sensitive() else ['@(test\\']],
        ['@(test[)', ['test[']],

        # Dot tests
        GlobFiles(
            [
                '.', '..', '.abc', 'abc', '...', '..abc'
            ]
        ),

        # Basic dot tests
        ['[.]abc', []],
        [R'[\.]abc', []],
        ['.abc', ['.abc']],
        [R'\.abc', ['.abc']],
        ['[.]abc', ['.abc'], glob.D],
        [R'[\.]abc', ['.abc'], glob.D],

        ['.', ['.']],
        ['..', ['..']],
        ['.*', ['.', '..', '.abc', '...', '..abc']],
        [R'.\a*', ['.abc']],
        [R'\.', ['.']],
        [R'\..', ['..']],
        [R'\.\.', ['..']],
        ['..*', ['..', '...', '..abc']],
        [R'...', ['...']],
        [R'..\.', ['...']],

        ['.', ['.'], glob.Z],
        ['..', ['..'], glob.Z],
        ['.*', ['.abc', '...', '..abc'], glob.Z],
        [R'.\a*', ['.abc'], glob.Z],
        [R'\.', ['.'], glob.Z],
        [R'\..', ['..'], glob.Z],
        [R'\.\.', ['..'], glob.Z],
        ['..*', ['...', '..abc'], glob.Z],
        [R'...', ['...'], glob.Z],
        [R'..\.', ['...'], glob.Z],

        # Dot tests trailing slashes
        GlobFiles(
            [
                './', '../', '.abc/', 'abc/', '.../', '..abc/'
            ]
        ),
        ['./', ['./']],
        ['../', ['../']],
        ['..\\', ['../']],
        ['./', ['./'], glob.Z],
        ['../', ['../'], glob.Z],
        ['..\\', ['../'], glob.Z],
        [R'.\\', ['./'], glob.W | glob.Z],

        # Inverse dot tests
        GlobFiles(
            [
                '.', '..', '.abc', 'abc'
            ]
        ),

        # We enable glob.N by default, so staring with `!`
        # is a problem without glob.M
        ['!(test)', ['abc'], glob.M],
        ['!(test)', ['.abc', 'abc'], glob.D | glob.M],
        ['.!(test)', ['.', '..', '.abc'], glob.M],
        ['.!(test)', ['.', '..', '.abc'], glob.D | glob.M],
        ['!(.)', ['abc'], glob.M],
        [R'!(\.)', ['abc'], glob.M],
        [R'!(\x2e)', ['abc'], glob.M | glob.R],
        ['@(!(.))', ['abc'], glob.M],
        ['!(@(.))', ['abc'], glob.M],
        ['+(!(.))', ['abc'], glob.M],
        ['!(+(.))', ['abc'], glob.M],
        ['!(?)', ['abc'], glob.M],
        ['!(*)', [], glob.M],
        ['!([.])', ['abc'], glob.M],
        ['!(.)', ['..', '.abc', 'abc'], glob.M | glob.D],
        [R'!(\.)', ['..', '.abc', 'abc'], glob.M | glob.D],
        [R'!(\x2e)', ['..', '.abc', 'abc'], glob.M | glob.R | glob.D],
        ['@(!(.))', ['..', '.abc', 'abc'], glob.M | glob.D],
        ['!(@(.))', ['..', '.abc', 'abc'], glob.M | glob.D],
        ['+(!(.))', ['..', '.abc', 'abc'], glob.M | glob.D],
        ['+(!(.))', ['.abc', 'abc'], glob.M | glob.D | glob.Z],
        ['!(+(.))', ['.abc', 'abc'], glob.M | glob.D],
        ['!(?)', ['.abc', 'abc'], glob.M | glob.D],
        ['!(*)', [], glob.M | glob.D],
        ['!([.])', ['.abc', 'abc'], glob.M | glob.D],
        ['@(..|.)', ['.', '..']],
        ['@(..|.)', ['.', '..'], glob.Z],

        # More extended pattern dot related tests
        ['*(.)', ['.', '..']],
        [R'*(\.)', ['.', '..']],
        ['*([.])', []],
        ['*(?)', ['abc']],
        ['@(.?)', ['..']],
        ['@(?.)', []],
        ['*(.)', ['.', '..'], glob.D],
        [R'*(\.)', ['.', '..'], glob.D],
        ['*([.])', [], glob.D],
        ['*(?)', ['.abc', 'abc'], glob.D],
        ['@(.?)', ['..'], glob.D],
        ['@(?.)', [], glob.D],

        GlobFiles(['folder/abc', 'directory/abc', 'dir/abc']),
        # Test that inverse works properly mid path.
        ['!(folder)/*', ['directory/abc', 'dir/abc'], glob.M],
        ['!(folder)dir/abc', ['dir/abc'], glob.M],
        ['!(dir)/abc', ['directory/abc', 'folder/abc'], glob.M],

        # Slash exclusion
        GlobFiles(['test/test', 'test\\/test']),

        # Force Unix/Linux
        ['test/test', ['test/test'], glob.U],
        ['test\\/test', ['test/test'], glob.U],
        [R'test\\/test', ['test\\/test'], glob.U],
        ['@(test/test)', [], glob.U],
        [R'@(test\/test)', [], glob.U],
        ['test[/]test', [], glob.U],
        [R'test[\/]test', [], glob.U],

        # Force Windows
        ['test/test', ['test/test', 'test\\/test'], glob.W],
        ['test\\/test', ['test/test', 'test\\/test'], glob.W],
        ['@(test/test)', [], glob.W],
        [R'@(test\/test)', [], glob.W],
        ['test[/]test', [], glob.W],
        [R'test[\/]test', [], glob.W],

        # Case
        ['TEST/test', ['test/test', 'test\\/test'], glob.W],
        ['test\\/TEST', ['test/test', 'test\\/test'], glob.W],
        ['TEST/test', [], glob.W | glob.C],
        ['test\\/TEST', [], glob.W | glob.C],
        ['test/test', ['test/test', 'test\\/test'], glob.W | glob.C],
        ['test\\/test', ['test/test', 'test\\/test'], glob.W | glob.C],
        ['TEST/test', ['test/test'], glob.U | glob.I],
        ['test\\/TEST', ['test/test'], glob.U | glob.I],
        [R'test\\/TEST', ['test\\/test'], glob.U | glob.I],
        ['TEST/test', [], glob.U],
        ['test\\/TEST', [], glob.U],

        # Ensure we don't count slashes with `*`.
        GlobFiles(['test/test', 'test//']),

        ['test/*', ['test/test']],
        ['test/*', ['test/test'], glob.W],

        GlobFiles(['test\\test', 'test\\\\']),

        ['test/*', ['test\\test'], glob.W],

        GlobFiles(['c:/some/path', '//host/share/some/path']),

        # Test Windows drive and UNC host/share case sensitivity
        ['C:/**', ['c:/some/path'], glob.W],
        ['//HoSt/ShArE/**', ['//host/share/some/path'], glob.W],
        ['C:/SoMe/PaTh', ['c:/some/path'], glob.W],
        ['//HoSt/ShArE/SoMe/PaTh', ['//host/share/some/path'], glob.W],
        ['C:/**', ['c:/some/path'], glob.W | glob.C],
        ['//HoSt/ShArE/**', ['//host/share/some/path'], glob.W | glob.C],
        ['C:/SoMe/PaTh', [], glob.W | glob.C],
        ['//HoSt/ShArE/SoMe/PaTh', [], glob.W | glob.C],

        # Issue #24
        GlobFiles(
            ["goo.cfg", "foo.bar", "foo.bar.cfg", "foo.cfg.bar"]
        ),
        ['*.bar', ["foo.bar", "foo.cfg.bar"]],
        ['*|!*.bar', ["goo.cfg", "foo.bar.cfg"], glob.S],

        # Test `NODIR` option
        GlobFiles(
            [
                "test/..", "test/.", "test/...", "test/.file", "test/.file/",
                ".", "..", "...", '.../', "test/", "file", "/file"
            ]
        ),
        ['**/*', ['...', '.../', '/file', 'file', 'test/', 'test/...', 'test/.file', 'test/.file/'], glob.D],
        ['**/*', ['...', 'file', 'test/...', 'test/.file', "/file"], glob.O | glob.D],
        ['**/..', [], glob.O | glob.D],
        ['**/..', ['..', 'test/..'], glob.D],
        GlobFiles(
            [
                b"test/..", b"test/.", b"test/...", b"test/.file", b"test/.file/",
                b".", b"..", b"...", b'.../', b"test/", b"file", b"/file"
            ]
        ),
        [b'**/*', [b'...', b'file', b'test/...', b'test/.file', b"/file"], glob.O | glob.D],

        # Test Windows drives
        GlobFiles(
            [
                '//?/UNC/LOCALHOST/c$/temp', '//./UNC/LOCALHOST/c$/temp', '//?/GLOBAL/UNC/LOCALHOST/c$/temp',
                '//?/GLOBAL/global/UNC/LOCALHOST/c$/temp', '//?/C:/temp'
            ]
        ),

        ['//?/unc/localhost/c$/*', ['//?/UNC/LOCALHOST/c$/temp'], glob.W],
        ['//./unc/localhost/c$/*', ['//./UNC/LOCALHOST/c$/temp'], glob.W],
        ['//?/global/unc/localhost/c$/*', ['//?/GLOBAL/UNC/LOCALHOST/c$/temp'], glob.W],
        ['//?/global/global/unc/localhost/c$/*', ['//?/GLOBAL/global/UNC/LOCALHOST/c$/temp'], glob.W],
        ['//?/c:/*', ['//?/C:/temp'], glob.W],

        GlobFiles(
            [
                b'//?/UNC/LOCALHOST/c$/temp', b'//./UNC/LOCALHOST/c$/temp', b'//?/GLOBAL/UNC/LOCALHOST/c$/temp',
                b'//?/GLOBAL/global/UNC/LOCALHOST/c$/temp', b'//?/C:/temp'
            ]
        ),
        [b'//?/unc/localhost/c$/*', [b'//?/UNC/LOCALHOST/c$/temp'], glob.W],
        [b'//./unc/localhost/c$/*', [b'//./UNC/LOCALHOST/c$/temp'], glob.W],
        [b'//?/global/unc/localhost/c$/*', [b'//?/GLOBAL/UNC/LOCALHOST/c$/temp'], glob.W],
        [b'//?/global/global/unc/localhost/c$/*', [b'//?/GLOBAL/global/UNC/LOCALHOST/c$/temp'], glob.W],
        [b'//?/c:/*', [b'//?/C:/temp'], glob.W]
    ]

    @classmethod
    def setup_class(cls):
        """Setup the tests."""

        cls.files = []
        # The tests we scraped were written with this assumed.
        cls.flags = glob.NEGATE | glob.GLOBSTAR | glob.EXTGLOB | glob.BRACE
        cls.skip_split = False

    @staticmethod
    def norm_files(files, flags):
        """Normalize files."""

        flags = glob._flag_transform(flags)
        unix = _wcparse.is_unix_style(flags)

        return [(_wcparse.norm_slash(x, flags) if not unix else x) for x in files]

    @staticmethod
    def assert_equal(a, b):
        """Assert equal."""

        assert a == b, "Comparison between objects yielded False."

    @classmethod
    def _filter(cls, case, split=False):
        """Filter with glob pattern."""

        if isinstance(case, GlobFiles):
            if case.append:
                cls.files.extend(case.filelist)
            else:
                cls.files.clear()
                cls.files.extend(case.filelist)
            pytest.skip("Update file list")
        elif isinstance(case, Options):
            cls.skip_split = case.get('skip_split', False)
            pytest.skip("Change Options")

        files = cls.files if len(case) < 4 else case[3]
        flags = 0 if len(case) < 3 else case[2]

        print('Flags?')
        print(case)
        print(flags, cls.flags)
        flags = cls.flags ^ flags
        pat = case[0] if isinstance(case[0], list) else [case[0]]
        if split and cls.skip_split:
            return
        if split:
            flags |= glob.SPLIT
        print("PATTERN: ", case[0])
        print("FILES: ", files)
        print("FLAGS: ", bin(flags))
        result = sorted(
            glob.globfilter(
                files,
                pat,
                flags=flags
            )
        )
        source = sorted(case[1])
        print("TEST: ", result, '<==>', source, '\n')
        cls.assert_equal(result, source)

    @pytest.mark.parametrize("case", cases)
    def test_glob_filter(self, case):
        """Test wildcard parsing."""

        _wcparse._compile.cache_clear()

        self._filter(case)

    @pytest.mark.parametrize("case", cases)
    def test_glob_split_filter(self, case):
        """Test wildcard parsing by first splitting on `|`."""

        _wcparse._compile.cache_clear()

        self._filter(case, split=True)


class TestGlobMatch:
    """
    Tests that are performed against `globmatch`.

    Each case entry is a list of 4 parameters.

    * Pattern
    * File name
    * Expected result (boolean of whether pattern matched file name)
    * Flags

    The default flags are `NEGATE` | `GLOBSTAR` | `EXTGLOB` | `BRACE`. Any flags passed through via entry are XORed.
    So if any of the default flags are passed via an entry, they will be disabled. All other flags will
    enable the feature.

    """

    cases = [
        ['*.!(js|css)', 'bar.min.js', True, glob.N],
        ['!*.+(js|css)', 'bar.min.js', False, glob.N],
        ['*.+(js|css)', 'bar.min.js', True, glob.N],

        ['*.!(j)', 'a-integration-test.js', True, glob.N],
        ['!(*-integration-test.js)', 'a-integration-test.js', False, glob.N],
        ['*-!(integration-)test.js', 'a-integration-test.js', True, glob.N],
        ['*-!(integration)-test.js', 'a-integration-test.js', False, glob.N],
        ['*!(-integration)-test.js', 'a-integration-test.js', True, glob.N],
        ['*!(-integration-)test.js', 'a-integration-test.js', True, glob.N],
        ['*!(integration)-test.js', 'a-integration-test.js', True, glob.N],
        ['*!(integration-test).js', 'a-integration-test.js', True, glob.N],
        ['*-!(integration-test).js', 'a-integration-test.js', True, glob.N],
        ['*-!(integration-test.js)', 'a-integration-test.js', True, glob.N],
        ['*-!(integra)tion-test.js', 'a-integration-test.js', False, glob.N],
        ['*-integr!(ation)-test.js', 'a-integration-test.js', False, glob.N],
        ['*-integr!(ation-t)est.js', 'a-integration-test.js', False, glob.N],
        ['*-i!(ntegration-)test.js', 'a-integration-test.js', False, glob.N],
        ['*i!(ntegration-)test.js', 'a-integration-test.js', True, glob.N],
        ['*te!(gration-te)st.js', 'a-integration-test.js', True, glob.N],
        ['*-!(integration)?test.js', 'a-integration-test.js', False, glob.N],
        ['*?!(integration)?test.js', 'a-integration-test.js', True, glob.N],

        ['foo-integration-test.js', 'foo-integration-test.js', True, glob.N],
        ['!(*-integration-test.js)', 'foo-integration-test.js', False, glob.N],

        ['*.!(js).js', 'foo.jszzz.js', True, glob.N],

        ['*.!(js)', 'asd.jss', True, glob.N],

        ['*.!(js).!(xy)', 'asd.jss.xyz', True, glob.N],

        ['*.!(js).!(xy)', 'asd.jss.xy', False, glob.N],

        ['*.!(js).!(xy)', 'asd.js.xyz', False, glob.N],

        ['*.!(js).!(xy)', 'asd.js.xy', False, glob.N],

        ['*.!(js).!(xy)', 'asd.sjs.zxy', True, glob.N],

        ['*.!(js).!(xy)', 'asd..xyz', True, glob.N],

        ['*.!(js).!(xy)', 'asd..xy', False, glob.N],
        ['*.!(js|x).!(xy)', 'asd..xy', False, glob.N],

        ['*.!(js)', 'foo.js.js', True, glob.N],

        ['*(*.json|!(*.js))', 'testjson.json', True, glob.N],
        ['+(*.json|!(*.js))', 'testjson.json', True, glob.N],
        ['@(*.json|!(*.js))', 'testjson.json', True, glob.N],
        ['?(*.json|!(*.js))', 'testjson.json', True, glob.N],

        ['*(*.json|!(*.js))', 'foojs.js', False, glob.N],  # XXX bash 4.3 disagrees!
        ['+(*.json|!(*.js))', 'foojs.js', False, glob.N],  # XXX bash 4.3 disagrees!
        ['@(*.json|!(*.js))', 'foojs.js', False, glob.N],
        ['?(*.json|!(*.js))', 'foojs.js', False, glob.N],

        ['*(*.json|!(*.js))', 'other.bar', True, glob.N],
        ['+(*.json|!(*.js))', 'other.bar', True, glob.N],
        ['@(*.json|!(*.js))', 'other.bar', True, glob.N],
        ['?(*.json|!(*.js))', 'other.bar', True, glob.N],

        # Complex inverse cases
        ['!(not )@(this)', 'not this', False, glob.N],
        ['!(not )@(this)', 'but this', True, glob.N],
        ['!(not)!( this)', 'not this', True, glob.N],
        ['!(not @(this ))@(okay)', 'not this okay', False, glob.N],
        ['!(not @(this ))@(okay)', 'but this okay', True, glob.N],
        ['!(not !(this ))@(okay)', 'but this okay', True, glob.N],
        ['!(but !(that ))@(okay)', 'but this okay', False, glob.N],
        ['!(but !(this ))@(okay)', 'but this okay', True, glob.N],
        ['!(not)!( this)@( okay)', 'but this okay', True, glob.N],
        ['@(but!( that))@( okay)', "but this okay", True, glob.N],
        ['!(@(but!( that))@( okay))', "but this okay", False, glob.N],
    ]

    @classmethod
    def setup_class(cls):
        """Setup default flag options."""

        # The tests we scraped were written with this assumed.
        cls.flags = glob.NEGATE | glob.GLOBSTAR | glob.EXTGLOB | glob.BRACE

    @classmethod
    def evaluate(cls, case):
        """Evaluate case."""

        pattern = case[0]
        filename = case[1]
        goal = case[2]
        flags = cls.flags
        if len(case) > 3:
            flags ^= case[3]

        print("PATTERN: ", pattern)
        print("FILE: ", filename)
        print("GOAL: ", goal)
        print("FLAGS: ", bin(flags))

        assert glob.globmatch(filename, pattern, flags=flags) == goal, "Expression did not evaluate as %s" % goal

    @pytest.mark.parametrize("case", cases)
    def test_cases(self, case):
        """Test ignore cases."""

        self.evaluate(case)


class TestGlobMatchSpecial(unittest.TestCase):
    """Test special cases that cannot easily be covered in earlier tests."""

    def setUp(self):
        """Setup default flag options."""

        self.flags = glob.NEGATE | glob.GLOBSTAR | glob.EXTGLOB | glob.BRACE

    def test_unfinished_ext(self):
        """Test unfinished ext."""

        flags = self.flags
        flags ^= glob.NEGATE

        for x in ['!', '?', '+', '*', '@']:
            self.assertTrue(glob.globmatch(x + '(a|B', x + '(a|B', flags=flags))
            self.assertFalse(glob.globmatch(x + '(a|B', 'B', flags=flags))

    def test_empty_pattern_lists(self):
        """Test empty pattern lists."""

        self.assertFalse(glob.globmatch('test', []))
        self.assertEqual(glob.globfilter(['test'], []), [])

    def test_windows_drives(self):
        """Test windows drives."""

        flags = self.flags
        flags |= glob.FORCEWIN

        self.assertTrue(
            glob.globmatch(
                '//?/c:/somepath/to/match/file.txt',
                '//?/c:/**/*.txt',
                flags=flags
            )
        )

        self.assertTrue(
            glob.globmatch(
                'c:/somepath/to/match/file.txt',
                'c:/**/*.txt',
                flags=flags
            )
        )

    def test_glob_parsing_win(self):
        """Test windows style glob parsing."""

        flags = self.flags
        flags |= glob.FORCEWIN

        _wcparse._compile.cache_clear()

        self.assertTrue(
            glob.globmatch(
                'some/name/with/named/file/test.py',
                '**/named/file/*.py',
                flags=flags
            )
        )
        self.assertTrue(
            glob.globmatch(
                'some/name/with/na[/]med/file/test.py',
                '**/na[/]med/file/*.py',
                flags=flags
            )
        )
        self.assertTrue(
            glob.globmatch(
                'some/name/with/na[/]med\\/file/test.py',
                '**/na[/]med\\/file/*.py',
                flags=flags
            )
        )
        self.assertTrue(
            glob.globmatch(
                'some/name/with/na[\\]med/file/test.py',
                R'**/na[\\]med/file/*.py',
                flags=flags | glob.R
            )
        )
        self.assertTrue(
            glob.globmatch(
                'some\\name\\with\\na[\\]med\\file\\test.py',
                R'**/na[\\]med/file/*.py',
                flags=flags | glob.R
            )
        )
        self.assertTrue(
            glob.globmatch(
                'some\\name\\with\\na[\\]med\\file*.py',
                R'**\\na[\\]med\\file\*.py',
                flags=flags | glob.R
            )
        )
        self.assertTrue(
            glob.globmatch(
                'some\\name\\with\\na[\\]med\\file\\test.py',
                R'**\\na[\\]m\ed\\file\\*.py',
                flags=flags | glob.R
            )
        )
        self.assertTrue(
            glob.globmatch(
                'some\\name\\with\\na[\\]med\\\\file\\test.py',
                R'**\\na[\\]m\ed\\/file\\*.py',
                flags=flags | glob.R
            )
        )
        self.assertTrue(
            glob.globmatch(
                'some\\name\\with\\na[\\\\]med\\\\file\\test.py',
                R'**\\na[\/]m\ed\/file\\*.py',
                flags=flags | glob.R
            )
        )

    def test_glob_translate_no_dir(self):
        """Test that an additional pattern is injected in translate."""

        pos, neg = glob.translate('**', flags=glob.G)
        self.assertEqual(1, len(pos))
        self.assertEqual(0, len(neg))

        pos, neg = glob.translate('**', flags=glob.G | glob.O)
        self.assertEqual(1, len(pos))
        self.assertEqual(1, len(neg))

        pos, neg = glob.translate(b'**', flags=glob.G)
        self.assertEqual(1, len(pos))
        self.assertEqual(0, len(neg))

        pos, neg = glob.translate(b'**', flags=glob.G | glob.O)
        self.assertEqual(1, len(pos))
        self.assertEqual(1, len(neg))

    def test_capture_groups(self):
        """Test capture groups."""

        gpat = glob.translate("test/@(this)/+(many)/?(meh)*(!)/!(not this)@(.md)", flags=glob.E)
        pat = re.compile(gpat[0][0])
        match = pat.match(os.path.normpath('test/this/manymanymany/meh!!!!!/okay.md'))
        self.assertEqual(('this', 'manymanymany', 'meh', '!!!!!', 'okay', '.md'), match.groups())

    def test_nested_capture_groups(self):
        """Test nested capture groups."""

        gpat = glob.translate("@(file)@(+([[:digit:]]))@(.*)", flags=glob.E)
        pat = re.compile(gpat[0][0])
        match = pat.match('file33.test.txt')
        self.assertEqual(('file', '33', '33', '.test.txt'), match.groups())

    def test_list_groups(self):
        """Test capture groups with lists."""

        gpat = glob.translate("+(f|i|l|e)+([[:digit:]])@(.*)", flags=glob.E)
        pat = re.compile(gpat[0][0])
        match = pat.match('file33.test.txt')
        self.assertEqual(('file', '33', '.test.txt'), match.groups())

    def test_glob_translate(self):
        """Test glob translation."""

        flags = self.flags
        flags |= glob.FORCEUNIX

        value = (
            [
                '^(?s:(?:(?!(?:[/]|^)\\.).)*?(?:^|$|[/])+' +
                ('(?!(?:\\.{1,2})(?:$|[/]))(?![/.])[\x00-\x7f][/]+stuff[/]+(?=[^/])') +
                '(?!(?:\\.{1,2})(?:$|[/]))(?:(?!\\.)[^/]*?)?[/]*?)$'
            ],
            []
        )

        self.assertEqual(
            glob.translate('**/[[:ascii:]]/stuff/*', flags=flags),
            value
        )

    def test_glob_parsing_nix(self):
        """Test wildcard parsing."""

        flags = self.flags
        flags |= glob.FORCEUNIX

        self.assertTrue(
            glob.globmatch(
                'some/name/with/named/file/test.py',
                '**/named/file/*.py',
                flags=flags
            )
        )
        self.assertTrue(
            glob.globmatch(
                'some/name/with/na[/]med/file/test.py',
                '**/na[/]med/file/*.py',
                flags=flags
            )
        )
        self.assertTrue(
            glob.globmatch(
                'some/name/with/na[/]med\\/file/test.py',
                '**/na[/]med\\\\/file/*.py',
                flags=flags
            )
        )
        self.assertTrue(
            glob.globmatch(
                'some/name/with/na\\med/file/test.py',
                R'**/na[\\]med/file/*.py',
                flags=flags | glob.R
            )
        )
        self.assertTrue(
            glob.globmatch(
                'some/name/with/na[\\/]med\\/file/test.py',
                R'**/na[\\/]med\\/file/*.py',
                flags=flags | glob.R
            )
        )

    def test_glob_translate_real_has_no_positive_default(self):
        """Test that `REALPATH` translations provide a default positive pattern."""

        pos, neg = glob.translate('!this', flags=self.flags)
        self.assertTrue(len(pos) == 0)
        self.assertTrue(len(neg) == 1)

        pos, neg = glob.translate('!this', flags=self.flags | glob.REALPATH)
        self.assertTrue(len(pos) == 0)
        self.assertTrue(len(neg) == 1)

    def test_glob_match_real(self):
        """Test real `globmatch` vs regular `globmatch`."""

        # When there is no context from the file system,
        # `globmatch` can't determine folder with no trailing slash.
        self.assertFalse(glob.globmatch('docs/src', '**/src/**', flags=self.flags))
        self.assertTrue(glob.globmatch('docs/src/', '**/src/**', flags=self.flags))
        self.assertTrue(glob.globmatch('docs/src', '**/src/**', flags=self.flags | glob.REALPATH))
        self.assertTrue(glob.globmatch('docs/src/', '**/src/**', flags=self.flags | glob.REALPATH))

        # Missing files will only match in `globmatch` without context from file system.
        self.assertTrue(glob.globmatch('bad/src/', '**/src/**', flags=self.flags))
        self.assertFalse(glob.globmatch('bad/src/', '**/src/**', flags=self.flags | glob.REALPATH))

    def test_glob_match_real_bytes(self):
        """Test real `globmatch` vs regular `globmatch` with bytes strings."""

        # When there is no context from the file system,
        # `globmatch` can't determine folder with no trailing slash.
        self.assertFalse(glob.globmatch(b'docs/src', b'**/src/**', flags=self.flags))
        self.assertTrue(glob.globmatch(b'docs/src/', b'**/src/**', flags=self.flags))
        self.assertTrue(glob.globmatch(b'docs/src', b'**/src/**', flags=self.flags | glob.REALPATH))
        self.assertTrue(glob.globmatch(b'docs/src/', b'**/src/**', flags=self.flags | glob.REALPATH))

        # Missing files will only match in `globmatch` without context from file system.
        self.assertTrue(glob.globmatch(b'bad/src/', b'**/src/**', flags=self.flags))
        self.assertFalse(glob.globmatch(b'bad/src/', b'**/src/**', flags=self.flags | glob.REALPATH))

    def test_glob_match_real_outside_curdir(self):
        """Test that real `globmatch` will not allow match outside current directory unless using an absolute path."""

        # Let's find something predictable for this cross platform test.
        user_dir = os.path.expanduser('~')
        if user_dir != '~':
            glob_user = glob.escape(user_dir)
            self.assertFalse(glob.globmatch(user_dir, '**', flags=self.flags | glob.REALPATH))
            self.assertTrue(glob.globmatch(user_dir, glob_user + '/**', flags=self.flags | glob.REALPATH))

    def test_glob_integrity_bytes(self):
        """Test glob integrity to exercises the bytes portion of the code."""

        self.assertTrue(
            all(
                glob.globmatch(
                        x, b'!**/*.md', flags=self.flags | glob.SPLIT
                    ) for x in glob.glob(b'!**/*.md', flags=self.flags | glob.SPLIT)
            )
        )

    def test_glob_integrity(self):
        """`globmatch` must match what glob globs."""

        # Number of slashes is inconsequential
        # Glob really looks at what is in between. Multiple slashes are the same as one separator.
        # UNC mounts are special cases and it matters there.
        self.assertTrue(
            all(
                glob.globmatch(
                        x, '**/../*.{md,py}', flags=self.flags
                    ) for x in glob.glob('**/../*.{md,py}', flags=self.flags)
            )
        )
        self.assertTrue(
            all(
                glob.globmatch(
                        x, './**/./../*.py', flags=self.flags
                    ) for x in glob.glob('./**/./../*.py', flags=self.flags)
            )
        )
        self.assertTrue(
            all(
                glob.globmatch(
                        x, './///**///./../*.py', flags=self.flags
                    ) for x in glob.glob('./**/.//////..////*.py', flags=self.flags)
            )
        )
        self.assertTrue(
            all(
                glob.globmatch(
                        x, '**/docs/**', flags=self.flags
                    ) for x in glob.glob('**/docs/**', flags=self.flags)
            )
        )
        self.assertTrue(
            all(
                glob.globmatch(
                        x, '**/docs/**|!**/*.md', flags=self.flags | glob.SPLIT
                    ) for x in glob.glob('**/docs/**|!**/*.md', flags=self.flags | glob.SPLIT)
            )
        )

        self.assertTrue(
            all(
                glob.globmatch(
                        x, '!**/*.md', flags=self.flags | glob.SPLIT
                    ) for x in glob.glob('!**/*.md', flags=self.flags | glob.SPLIT)
            )
        )
        self.assertFalse(
            all(
                glob.globmatch(
                        x, '**/docs/**|!**/*.md', flags=self.flags | glob.SPLIT
                    ) for x in glob.glob('**/docs/**', flags=self.flags | glob.SPLIT)
            )
        )

    def test_glob_integrity_marked(self):
        """`globmatch` must match what glob globs with marked directories."""

        # Number of slashes is inconsequential
        # Glob really looks at what is in between. Multiple slashes are the same as one separator.
        # UNC mounts are special cases and it matters there.
        self.assertTrue(
            all(
                glob.globmatch(
                        x, '**/docs/**', flags=self.flags | glob.MARK
                    ) for x in glob.glob('**/docs/**', flags=self.flags | glob.MARK)
            )
        )
        self.assertTrue(
            all(
                glob.globmatch(
                        x, '**/docs/**|!**/*.md', flags=self.flags | glob.SPLIT | glob.MARK
                    ) for x in glob.glob('**/docs/**|!**/*.md', flags=self.flags | glob.SPLIT | glob.MARK)
            )
        )

        self.assertTrue(
            all(
                glob.globmatch(
                        x, '!**/*.md', flags=self.flags | glob.SPLIT | glob.MARK
                    ) for x in glob.glob('!**/*.md', flags=self.flags | glob.SPLIT | glob.MARK)
            )
        )
        self.assertFalse(
            all(
                glob.globmatch(
                        x, '**/docs/**|!**/*.md', flags=self.flags | glob.SPLIT | glob.MARK
                    ) for x in glob.glob('**/docs/**', flags=self.flags | glob.SPLIT | glob.MARK)
            )
        )

    def test_glob_integrity_real(self):
        """`globmatch` must match what glob globs against the real file system."""

        # Number of slashes is inconsequential
        # Glob really looks at what is in between. Multiple slashes are the same as one separator.
        # UNC mounts are special cases and it matters there.
        self.assertTrue(
            all(
                glob.globmatch(
                        x, '**/../*.{md,py}', flags=self.flags | glob.REALPATH
                    ) for x in glob.glob('**/../*.{md,py}', flags=self.flags)
            )
        )
        self.assertTrue(
            all(
                glob.globmatch(
                        x, './**/./../*.py', flags=self.flags | glob.REALPATH
                    ) for x in glob.glob('./**/./../*.py', flags=self.flags)
            )
        )
        self.assertTrue(
            all(
                glob.globmatch(
                        x, './///**///./../*.py', flags=self.flags | glob.REALPATH
                    ) for x in glob.glob('./**/.//////..////*.py', flags=self.flags)
            )
        )
        self.assertTrue(
            all(
                glob.globmatch(
                        x, '**/docs/**', flags=self.flags | glob.REALPATH
                    ) for x in glob.glob('**/docs/**', flags=self.flags)
            )
        )
        self.assertTrue(
            all(
                glob.globmatch(
                        x, '**/docs/**|!**/*.md', flags=self.flags | glob.SPLIT | glob.REALPATH
                    ) for x in glob.glob('**/docs/**|!**/*.md', flags=self.flags | glob.SPLIT)
            )
        )
        self.assertTrue(
            all(
                glob.globmatch(
                        x, '!**/*.md', flags=self.flags | glob.SPLIT | glob.REALPATH
                    ) for x in glob.glob('!**/*.md', flags=self.flags | glob.SPLIT)
            )
        )
        self.assertFalse(
            all(
                glob.globmatch(
                        x, '**/docs/**|!**/*.md', flags=self.flags | glob.SPLIT | glob.REALPATH
                    ) for x in glob.glob('**/docs/**', flags=self.flags | glob.SPLIT)
            )
        )

    def test_glob_integrity_real_marked(self):
        """`globmatch` must match what glob globs against the real file system and marked directories."""

        # Number of slashes is inconsequential
        # Glob really looks at what is in between. Multiple slashes are the same as one separator.
        # UNC mounts are special cases and it matters there.
        self.assertTrue(
            all(
                glob.globmatch(
                        x, '**/docs/**', flags=self.flags | glob.REALPATH | glob.MARK
                    ) for x in glob.glob('**/docs/**', flags=self.flags | glob.MARK)
            )
        )
        self.assertTrue(
            all(
                glob.globmatch(
                        x, '**/docs/**|!**/*.md', flags=self.flags | glob.SPLIT | glob.REALPATH | glob.MARK
                    ) for x in glob.glob('**/docs/**|!**/*.md', flags=self.flags | glob.SPLIT | glob.MARK)
            )
        )
        self.assertTrue(
            all(
                glob.globmatch(
                        x, '!**/*.md', flags=self.flags | glob.SPLIT | glob.REALPATH | glob.MARK
                    ) for x in glob.glob('!**/*.md', flags=self.flags | glob.SPLIT | glob.MARK)
            )
        )
        self.assertFalse(
            all(
                glob.globmatch(
                        x, '**/docs/**|!**/*.md', flags=self.flags | glob.SPLIT | glob.REALPATH | glob.MARK
                    ) for x in glob.glob('**/docs/**', flags=self.flags | glob.SPLIT | glob.MARK)
            )
        )

    @unittest.skipUnless(sys.platform.startswith('win'), "Windows specific test")
    def test_glob_match_real_ignore_forceunix(self):
        """Ignore `FORCEUNIX` when using `globmatch` real."""

        self.assertTrue(glob.globmatch('docs/', '**/DOCS/**', flags=self.flags | glob.REALPATH | glob.FORCEUNIX))

    @unittest.skipUnless(not sys.platform.startswith('win'), "Non Windows test")
    def test_glob_match_real_ignore_forcewin(self):
        """Ignore `FORCEWIN` when using `globmatch` real."""

        self.assertFalse(glob.globmatch('docs/', '**/DOCS/**', flags=self.flags | glob.REALPATH | glob.FORCEWIN))
        self.assertTrue(
            glob.globmatch('docs/', '**/DOCS/**', flags=self.flags | glob.REALPATH | glob.FORCEWIN | glob.I)
        )

    def test_glob_match_ignore_forcewin_forceunix(self):
        """Ignore `FORCEUNIX` and `FORCEWIN` when both are used."""

        if sys.platform.startswith('win'):
            self.assertTrue(glob.globmatch('docs/', '**/DOCS/**', flags=self.flags | glob.FORCEWIN | glob.FORCEUNIX))
        else:
            self.assertFalse(glob.globmatch('docs/', '**/DOCS/**', flags=self.flags | glob.FORCEWIN | glob.FORCEUNIX))
            self.assertTrue(glob.globmatch('docs/', '**/docs/**', flags=self.flags | glob.FORCEWIN | glob.FORCEUNIX))

    def test_root_dir(self):
        """Test root directory with `globmatch`."""

        self.assertFalse(glob.globmatch('markdown', 'markdown', flags=glob.REALPATH))
        self.assertTrue(glob.globmatch('markdown', 'markdown', flags=glob.REALPATH, root_dir='docs/src'))

    def test_match_root_dir_pathlib(self):
        """Test root directory with `globmatch` using `pathlib`."""

        from wcmatch import pathlib

        self.assertFalse(glob.globmatch(pathlib.Path('markdown'), 'markdown', flags=glob.REALPATH))
        self.assertTrue(
            glob.globmatch(pathlib.Path('markdown'), 'markdown', flags=glob.REALPATH, root_dir=pathlib.Path('docs/src'))
        )

    def test_match_pathlib_str_bytes(self):
        """Test that mismatch type of `pathlib` and `bytes` asserts."""

        from wcmatch import pathlib

        with self.assertRaises(TypeError):
            glob.globmatch(pathlib.Path('markdown'), b'markdown')

    def test_match_str_bytes(self):
        """Test that mismatch type of `str` and `bytes` asserts."""

        with self.assertRaises(TypeError):
            glob.globmatch('markdown', b'markdown')

    def test_match_bytes_pathlib_str_realpath(self):
        """Test that mismatch type of `pathlib` and bytes asserts."""

        from wcmatch import pathlib

        with self.assertRaises(TypeError):
            glob.globmatch(
                pathlib.Path('markdown'),
                b'markdown', flags=glob.REALPATH
            )

    def test_match_bytes_root_dir_pathlib_realpath(self):
        """Test that mismatch type of root directory `pathlib` and `bytes` asserts."""

        from wcmatch import pathlib

        with self.assertRaises(TypeError):
            glob.globmatch(
                b'markdown',
                b'markdown',
                flags=glob.REALPATH,
                root_dir=pathlib.Path('.')
            )

    def test_match_bytes_root_dir_str_realpath(self):
        """Test that mismatch type of root directory `pathlib` and `bytes` asserts."""

        with self.assertRaises(TypeError):
            glob.globmatch(
                b'markdown',
                b'markdown',
                flags=glob.REALPATH,
                root_dir='.'
            )

    def test_match_str_root_dir_bytes_realpath(self):
        """Test that mismatch type of root directory of `bytes` and `str` asserts."""

        with self.assertRaises(TypeError):
            glob.globmatch(
                'markdown',
                'markdown',
                flags=glob.REALPATH,
                root_dir=b'.'
            )

    def test_filter_root_dir_pathlib(self):
        """Test root directory with `globfilter`."""

        from wcmatch import pathlib

        results = glob.globfilter(
            [pathlib.Path('markdown')],
            'markdown',
            flags=glob.REALPATH,
            root_dir=pathlib.Path('docs/src')
        )

        self.assertTrue(all(isinstance(result, pathlib.Path) for result in results))

    def test_filter_root_dir_pathlib_bytes(self):
        """Test root directory with `globfilter`."""

        from wcmatch import pathlib

        with self.assertRaises(TypeError):
            glob.globfilter(
                [pathlib.Path('markdown')],
                b'markdown',
                flags=glob.REALPATH,
                root_dir=pathlib.Path('docs/src')
            )


@skip_unless_symlink
class TestGlobmatchSymlink(_TestGlobmatch):
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

        self.default_flags = glob.G | glob.P | glob.B

    def test_globmatch_symlink(self):
        """Test `globmatch` with symlinks."""

        self.assertFalse(glob.globmatch(self.tempdir + '/sym1/a.txt', '**/*.txt}', flags=self.default_flags))
        self.assertTrue(glob.globmatch(self.tempdir + '/a.txt', '**/*.txt', flags=self.default_flags))
        self.assertTrue(glob.globmatch(self.tempdir + '/sym1/', '**', flags=self.default_flags))

    def test_globmatch_follow_symlink(self):
        """Test `globmatch` with symlinks that we follow."""

        self.assertTrue(glob.globmatch(self.tempdir + '/sym1/a.txt', '**/*.txt', flags=self.default_flags | glob.L))
        self.assertTrue(glob.globmatch(self.tempdir + '/a.txt', '**/*.txt', flags=self.default_flags | glob.L))
        self.assertTrue(glob.globmatch(self.tempdir + '/sym1/', '**', flags=self.default_flags))

    def test_globmatch_trigger_symlink_cache(self):
        """Use a pattern that exercises the symlink cache."""

        self.assertFalse(glob.globmatch(self.tempdir + '/sym1/a.txt', '**/{*.txt,*.t*}', flags=self.default_flags))

    def test_globmatch_globstarlong(self):
        """Test `***`."""

        flags = glob.GL | glob.P
        self.assertTrue(glob.globmatch(self.tempdir + '/sym1/a.txt', '***/*.txt', flags=flags))
        self.assertFalse(glob.globmatch(self.tempdir + '/sym1/a.txt', '**/*.txt', flags=flags))

    def test_globmatch_globstarlong_follow(self):
        """Test `***` with `FOLLOW`."""

        flags = glob.GL | glob.P | glob.L
        self.assertTrue(glob.globmatch(self.tempdir + '/sym1/a.txt', '***/*.txt', flags=flags))
        self.assertFalse(glob.globmatch(self.tempdir + '/sym1/a.txt', '**/*.txt', flags=flags))

    def test_globmatch_globstarlong_matchbase(self):
        """Test `***` with `MATCHBASE`."""

        flags = glob.GL | glob.P | glob.X
        self.assertFalse(glob.globmatch(self.tempdir + '/sym1/a.txt', '*.txt', flags=flags))

    def test_globmatch_globstarlong_matchbase_follow(self):
        """Test `***` with `MATCHBASE`."""

        flags = glob.GL | glob.P | glob.X | glob.L
        self.assertTrue(glob.globmatch(self.tempdir + '/sym1/a.txt', '*.txt', flags=flags))


@unittest.skipUnless(os.path.expanduser('~') != '~', "Requires expand user functionality")
class TestTilde(unittest.TestCase):
    """Test tilde cases."""

    def test_tilde_globmatch(self):
        """Test tilde in `globmatch` environment."""

        files = os.listdir(os.path.expanduser('~'))
        gfiles = glob.globfilter(
            glob.glob('~/*', flags=glob.T | glob.D),
            '~/*', flags=glob.T | glob.D | glob.P
        )

        self.assertEqual(len(files), len(gfiles))

    def test_tilde_globmatch_no_realpath(self):
        """Test tilde in `globmatch` environment but with real path disabled."""

        files = os.listdir(os.path.expanduser('~'))
        gfiles = glob.globfilter(
            glob.glob('~/*', flags=glob.T | glob.D),
            '~/*', flags=glob.T | glob.D
        )

        self.assertNotEqual(len(files), len(gfiles))

    def test_tilde_globmatch_no_tilde(self):
        """Test tilde in `globmatch` environment but with tilde disabled."""

        files = os.listdir(os.path.expanduser('~'))
        gfiles = glob.globfilter(
            glob.glob('~/*', flags=glob.T | glob.D),
            '~/*', flags=glob.D | glob.P
        )

        self.assertNotEqual(len(files), len(gfiles))


class TestIsMagic(unittest.TestCase):
    """Test "is magic" logic."""

    def test_default(self):
        """Test default magic."""

        self.assertTrue(glob.is_magic("test*"))
        self.assertTrue(glob.is_magic("test["))
        self.assertTrue(glob.is_magic("test]"))
        self.assertTrue(glob.is_magic("test?"))
        self.assertTrue(glob.is_magic("test\\"))

        self.assertFalse(glob.is_magic("test~!()-/|{}"))

    def test_extmatch(self):
        """Test extended match magic."""

        self.assertTrue(glob.is_magic("test*", flags=glob.EXTGLOB))
        self.assertTrue(glob.is_magic("test[", flags=glob.EXTGLOB))
        self.assertTrue(glob.is_magic("test]", flags=glob.EXTGLOB))
        self.assertTrue(glob.is_magic("test?", flags=glob.EXTGLOB))
        self.assertTrue(glob.is_magic("test\\", flags=glob.EXTGLOB))
        self.assertTrue(glob.is_magic("test(", flags=glob.EXTGLOB))
        self.assertTrue(glob.is_magic("test)", flags=glob.EXTGLOB))

        self.assertFalse(glob.is_magic("test~!-/|{}", flags=glob.EXTGLOB))

    def test_negate(self):
        """Test negate magic."""

        self.assertTrue(glob.is_magic("test*", flags=glob.NEGATE))
        self.assertTrue(glob.is_magic("test[", flags=glob.NEGATE))
        self.assertTrue(glob.is_magic("test]", flags=glob.NEGATE))
        self.assertTrue(glob.is_magic("test?", flags=glob.NEGATE))
        self.assertTrue(glob.is_magic("test\\", flags=glob.NEGATE))
        self.assertTrue(glob.is_magic("test!", flags=glob.NEGATE))

        self.assertFalse(glob.is_magic("test~()-/|{}", flags=glob.NEGATE))

    def test_minusnegate(self):
        """Test minus negate magic."""

        self.assertTrue(glob.is_magic("test*", flags=glob.NEGATE | glob.MINUSNEGATE))
        self.assertTrue(glob.is_magic("test[", flags=glob.NEGATE | glob.MINUSNEGATE))
        self.assertTrue(glob.is_magic("test]", flags=glob.NEGATE | glob.MINUSNEGATE))
        self.assertTrue(glob.is_magic("test?", flags=glob.NEGATE | glob.MINUSNEGATE))
        self.assertTrue(glob.is_magic("test\\", flags=glob.NEGATE | glob.MINUSNEGATE))
        self.assertTrue(glob.is_magic("test-", flags=glob.NEGATE | glob.MINUSNEGATE))

        self.assertFalse(glob.is_magic("test~()!/|{}", flags=glob.NEGATE | glob.MINUSNEGATE))

    def test_brace(self):
        """Test brace magic."""

        self.assertTrue(glob.is_magic("test*", flags=glob.BRACE))
        self.assertTrue(glob.is_magic("test[", flags=glob.BRACE))
        self.assertTrue(glob.is_magic("test]", flags=glob.BRACE))
        self.assertTrue(glob.is_magic("test?", flags=glob.BRACE))
        self.assertTrue(glob.is_magic("test\\", flags=glob.BRACE))
        self.assertTrue(glob.is_magic("test{", flags=glob.BRACE))
        self.assertTrue(glob.is_magic("test}", flags=glob.BRACE))

        self.assertFalse(glob.is_magic("test~!-/|", flags=glob.BRACE))

    def test_split(self):
        """Test split magic."""

        self.assertTrue(glob.is_magic("test*", flags=glob.SPLIT))
        self.assertTrue(glob.is_magic("test[", flags=glob.SPLIT))
        self.assertTrue(glob.is_magic("test]", flags=glob.SPLIT))
        self.assertTrue(glob.is_magic("test?", flags=glob.SPLIT))
        self.assertTrue(glob.is_magic("test\\", flags=glob.SPLIT))
        self.assertTrue(glob.is_magic("test|", flags=glob.SPLIT))

        self.assertFalse(glob.is_magic("test~()-!/", flags=glob.SPLIT))

    def test_tilde(self):
        """Test tilde magic."""

        self.assertTrue(glob.is_magic("test*", flags=glob.GLOBTILDE))
        self.assertTrue(glob.is_magic("test[", flags=glob.GLOBTILDE))
        self.assertTrue(glob.is_magic("test]", flags=glob.GLOBTILDE))
        self.assertTrue(glob.is_magic("test?", flags=glob.GLOBTILDE))
        self.assertTrue(glob.is_magic("test\\", flags=glob.GLOBTILDE))
        self.assertTrue(glob.is_magic("test~", flags=glob.GLOBTILDE))

        self.assertFalse(glob.is_magic("test|()-!/", flags=glob.GLOBTILDE))

    def test_all(self):
        """Test tilde magic."""

        flags = (
            glob.EXTGLOB |
            glob.NEGATE |
            glob.BRACE |
            glob.SPLIT |
            glob.GLOBTILDE
        )

        self.assertTrue(glob.is_magic("test*", flags=flags))
        self.assertTrue(glob.is_magic("test[", flags=flags))
        self.assertTrue(glob.is_magic("test]", flags=flags))
        self.assertTrue(glob.is_magic("test?", flags=flags))
        self.assertTrue(glob.is_magic(r"te\\st", flags=flags))
        self.assertTrue(glob.is_magic(r"te\st", flags=flags))
        self.assertTrue(glob.is_magic("test!", flags=flags))
        self.assertTrue(glob.is_magic("test|", flags=flags))
        self.assertTrue(glob.is_magic("test(", flags=flags))
        self.assertTrue(glob.is_magic("test)", flags=flags))
        self.assertTrue(glob.is_magic("test{", flags=flags))
        self.assertTrue(glob.is_magic("test}", flags=flags))
        self.assertTrue(glob.is_magic("test~", flags=flags))
        self.assertTrue(glob.is_magic("test-", flags=flags | glob.MINUSNEGATE))

        self.assertFalse(glob.is_magic("test-", flags=flags))
        self.assertFalse(glob.is_magic("test!", flags=flags | glob.MINUSNEGATE))

    def test_all_bytes(self):
        """Test tilde magic."""

        flags = (
            glob.EXTGLOB |
            glob.NEGATE |
            glob.BRACE |
            glob.SPLIT |
            glob.GLOBTILDE
        )

        self.assertTrue(glob.is_magic(b"test*", flags=flags))
        self.assertTrue(glob.is_magic(b"test[", flags=flags))
        self.assertTrue(glob.is_magic(b"test]", flags=flags))
        self.assertTrue(glob.is_magic(b"test?", flags=flags))
        self.assertTrue(glob.is_magic(rb"te\\st", flags=flags))
        self.assertTrue(glob.is_magic(rb"te\st", flags=flags))
        self.assertTrue(glob.is_magic(b"test!", flags=flags))
        self.assertTrue(glob.is_magic(b"test|", flags=flags))
        self.assertTrue(glob.is_magic(b"test(", flags=flags))
        self.assertTrue(glob.is_magic(b"test)", flags=flags))
        self.assertTrue(glob.is_magic(b"test{", flags=flags))
        self.assertTrue(glob.is_magic(b"test}", flags=flags))
        self.assertTrue(glob.is_magic(b"test~", flags=flags))
        self.assertTrue(glob.is_magic(b"test-", flags=flags | glob.MINUSNEGATE))

        self.assertFalse(glob.is_magic(b"test-", flags=flags))
        self.assertFalse(glob.is_magic(b"test!", flags=flags | glob.MINUSNEGATE))

    def test_win_path(self):
        """Test windows path."""

        flags = (
            glob.EXTGLOB |
            glob.NEGATE |
            glob.FORCEWIN |
            glob.GLOBTILDE
        )

        self.assertFalse(glob.is_magic('//?/UNC/server/*[]!|(){}~-/', flags=flags))
        self.assertFalse(glob.is_magic('//?/UNC/server/*[]!|()~-/', flags=flags | glob.BRACE))
        self.assertFalse(glob.is_magic('//?/UNC/server/*[]!(){}~-/', flags=flags | glob.SPLIT))

        self.assertTrue(glob.is_magic('//?/UNC/server/*[]!|(){}|~-/', flags=flags | glob.BRACE))
        self.assertTrue(glob.is_magic('//?/UNC/server/*[]!(){}|~-/', flags=flags | glob.SPLIT))
        self.assertTrue(glob.is_magic(R'\\\\server\\mount\\', flags=flags))


class TestExpansionLimit(unittest.TestCase):
    """Test expansion limits."""

    def test_limit_globmatch(self):
        """Test expansion limit of `globmatch`."""

        with self.assertRaises(_wcparse.PatternLimitException):
            glob.globmatch('name', '{1..11}', flags=glob.BRACE, limit=10)

    def test_limit_filter(self):
        """Test expansion limit of `globfilter`."""

        with self.assertRaises(_wcparse.PatternLimitException):
            glob.globfilter(['name'], '{1..11}', flags=glob.BRACE, limit=10)

    def test_limit_translate(self):
        """Test expansion limit of `translate`."""

        with self.assertRaises(_wcparse.PatternLimitException):
            glob.translate('{1..11}', flags=glob.BRACE, limit=10)


class TestExcludes(unittest.TestCase):
    """Test expansion limits."""

    def test_translate_exclude(self):
        """Test exclusion in translation."""

        results = glob.translate('*/somepath', exclude='test/somepath')
        self.assertTrue(len(results[0]) == 1 and len(results[1]) == 1)
        results = glob.translate(b'*/somepath', exclude=b'test/somepath')
        self.assertTrue(len(results[0]) == 1 and len(results[1]) == 1)

    def test_translate_exclude_mix(self):
        """
        Test translate exclude mix.

        If both are given, flags are ignored.
        """

        results = glob.translate(['*/somepath', '!test/somepath'], exclude=b'test/somepath', flags=glob.N | glob.A)
        self.assertTrue(len(results[0]) == 2 and len(results[1]) == 1)

    def test_exclude(self):
        """Test exclude parameter."""

        self.assertTrue(glob.globmatch('path/name', '*/*', exclude='*/test'))
        self.assertTrue(glob.globmatch(b'path/name', b'*/*', exclude=b'*/test'))
        self.assertFalse(glob.globmatch('path/test', '*/*', exclude='*/test'))
        self.assertFalse(glob.globmatch(b'path/test', b'*/*', exclude=b'*/test'))

    def test_exclude_mix(self):
        """
        Test exclusion flags mixed with exclusion parameter.

        If both are given, flags are ignored.
        """

        self.assertTrue(glob.globmatch('path/name', '*/*', exclude='*/test', flags=glob.N | glob.A))
        self.assertTrue(glob.globmatch(b'path/name', b'*/*', exclude=b'*/test', flags=glob.N | glob.A))
        self.assertFalse(glob.globmatch('path/test', '*/*', exclude='*/test', flags=glob.N | glob.A))
        self.assertFalse(glob.globmatch(b'path/test', b'*/*', exclude=b'*/test', flags=glob.N | glob.A))

        self.assertTrue(glob.globmatch('path/name', ['*/*', '!path/name'], exclude='*/test', flags=glob.N | glob.A))
        self.assertFalse(glob.globmatch('path/test', ['*/*', '!path/name'], exclude='*/test', flags=glob.N | glob.A))
        self.assertTrue(glob.globmatch('!path/name', ['*/*', '!path/name'], exclude='*/test', flags=glob.N | glob.A))

    def test_filter(self):
        """Test exclusion with filter."""

        self.assertEqual(glob.globfilter(['path/name', 'path/test'], '*/*', exclude='path/test'), ['path/name'])


class TestPrecompile(unittest.TestCase):
    """Test precompiled match objects."""

    def test_precompiled_match(self):
        """Test precompiled matching."""

        m = glob.compile('**/file', flags=glob.GLOBSTAR)
        self.assertTrue(m.match('some/path/file'))

    def test_precompiled_filter(self):
        """Test precompiled filtering."""

        pattern = '**/file'
        m = glob.compile(pattern, flags=glob.GLOBSTAR)
        self.assertEqual(
            m.filter(['test/file', 'file', 'nope']),
            glob.globfilter(['test/file', 'file', 'nope'], pattern, flags=glob.GLOBSTAR)
        )

    def test_precompiled_match_pathlib(self):
        """Test precompiled matching."""

        m = glob.compile('**/file', flags=glob.GLOBSTAR)
        self.assertTrue(m.match(pathlib.PurePath('some/path/file')))

    def test_precompiled_filter_pathlib(self):
        """Test precompiled filtering."""

        pattern = '**/file'
        m = glob.compile(pattern, flags=glob.GLOBSTAR)
        paths = [pathlib.PurePath('test/file'), pathlib.PurePath('file'), pathlib.PurePath('nope')]
        self.assertEqual(
            m.filter(paths),
            glob.globfilter(paths, pattern, flags=glob.GLOBSTAR)
        )

    def test_hash(self):
        """Test hashing."""

        m1 = glob.compile('test', flags=glob.C)
        m2 = glob.compile('test', flags=glob.C)
        m3 = glob.compile('test', flags=glob.I)
        m4 = glob.compile(b'test', flags=glob.C)

        self.assertTrue(m1 == m2)
        self.assertTrue(m1 != m3)
        self.assertTrue(m1 != m4)

        m5 = copy.copy(m1)
        self.assertTrue(m1 == m5)
        self.assertTrue(m5 in {m1})
