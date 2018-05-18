# -*- coding: utf-8 -*-
"""Tests for rumcore."""
import unittest
import pytest
import os
import mock
import wcmatch.glob as glob
import wcmatch._wcparse as _wcparse
import wcmatch.fnmatch as fnmatch
import wcmatch.wcmatch as wcmatch
from wcmatch import util


class TestGlob(unittest.TestCase):
    """Test globbing."""

    FILES = [
        'a', 'b', 'c', 'd', 'abc',
        'abd', 'abe', 'bb', 'bcd',
        'ca', 'cb', 'dd', 'de',
        'bdir/', 'bdir/cfile'
    ]

    # Initial tests gathered from https://github.com/isaacs/minimatch/blob/master/test/patterns
    # One was altered as it appeared to frankly be wrong. Others omitted as we do not support
    # the functionality currently, or have no interest to support it moving forward.
    file_filter = [
        'http://www.bashcookbook.com/bashinfo/source/bash-1.14.7/tests/glob-test',
        ['a*', ['a', 'abc', 'abd', 'abe']],

        ['X*', []],

        # isaacs: Slightly different than bash/sh/ksh
        # \\* is not un-escaped to literal "*" in a failed match,
        # but it does make it get treated as a literal star
        ['\\*', []],
        ['\\**', []],
        ['\\*\\*', []],

        ['b*/', ['bdir/']],
        ['c*', ['c', 'ca', 'cb']],
        ['**', FILES[:]],

        [r'\\.\\./*/', []],
        [r's/\\..*//', []],

        'legendary larry crashes bashes',
        ['/^root:/{s/^[^:]*:[^:]*:\\([^:]*\\).*$/\\1/', []],
        ['/^root:/{s/^[^:]*:[^:]*:\\([^:]*\\).*$/\u0001/', []],

        'character classes',
        ['[a-c]b*', ['abc', 'abd', 'abe', 'bb', 'cb']],
        ['[a-y]*[^c]', ['abd', 'abe', 'bb', 'bcd', 'bdir/', 'ca', 'cb', 'dd', 'de']],
        ['a*[^c]', ['abd', 'abe']],
        lambda files: files.extend(['a-b', 'aXb']),
        ['a[X-]b', ['a-b', 'aXb']],
        lambda files: files.extend(['.x', '.y']),
        ['[^a-c]*', ['d', 'dd', 'de']],
        lambda files: files.extend(['a*b/', 'a*b/ooo']),
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

        'http://www.opensource.apple.com/source/bash/bash-23/bash/tests/glob-test',
        lambda files: files.extend(['man/', 'man/man1/', 'man/man1/bash.1']),
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
        ['\\', ['\\'], 0, ['\\']],
        ['[\\\\]', ['\\'], 0, ['\\']],
        ['[[]', ['['], 0, ['[']],
        ['[', ['['], 0, ['[']],
        ['[*', ['[abc'], 0, ['[abc']],

        'a right bracket shall lose its special meaning and\n'
        'represent itself in a bracket expression if it occurs\n'
        'first in the list.  -- POSIX.2 2.8.3.2',
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

        'nocase tests',
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
        'onestar/twostar',
        [['/*', '*'], [], 0, ['/asdf/asdf/asdf']],
        [['/?', '*'], ['/a', 'bb'], 0, ['/a', '/b/b', '/a/b/c', 'bb']],

        'dots should not match unless requested',
        ['**', ['a/b'], 0, ['a/b', 'a/.d', '.a/.d']],

        # .. and . can only match patterns starting with .,
        # even when options.dot is set.
        lambda files: files.clear(),
        lambda files: files.extend(['a/./b', 'a/../b', 'a/c/b', 'a/.d/b']),
        ['a/*/b', ['a/c/b', 'a/.d/b'], glob.D],
        ['a/.*/b', ['a/./b', 'a/../b', 'a/.d/b'], glob.D],
        ['a/*/b', ['a/c/b'], 0],
        ['a/.*/b', ['a/./b', 'a/../b', 'a/.d/b'], 0],

        # this also tests that changing the options needs
        # to change the cache key, even if the pattern is
        # the same!
        [
            '**',
            ['a/b', 'a/.d', '.a/.d'],
            glob.D,
            ['.a/.d', 'a/.d', 'a/b']
        ],

        'paren sets cannot contain slashes',
        ['*(a/b)', [], 0, ['a/b']],

        # brace sets trump all else.
        #
        # invalid glob pattern.  fails on bash4 and bsdglob.
        # however, in this implementation, it's easier just
        # to do the intuitive thing, and let brace-expansion
        # actually come before parsing any extglob patterns,
        # like the documentation seems to say.
        #
        # XXX: if anyone complains about this, either fix it
        # or tell them to grow up and stop complaining.
        #
        # bash/bsdglob says this:
        # , ["*(a|{b),c)}", ["*(a|{b),c)}"], {}, ["a", "ab", "ac", "ad"]]
        # but we do this instead:
        ['*(a|{b),c)}', ['a', 'ab', 'ac'], 0, ['a', 'ab', 'ac', 'ad']],

        # test partial parsing in the presence of comment/negation chars
        ['[!a*', ['[!ab'], 0, ['[!ab', '[ab']],
        ['[#a*', ['[#ab'], 0, ['[#ab', '[ab']],

        # like: {a,b|c\\,d\\\|e} except it's unclosed, so it has to be escaped.
        # NOTE: I don't know what teh original test was doing because it was matching
        # something crazy. Multimatch regex expanded to escapes to like a 50.
        # I think ours expands them proper, so the original test has been altered.
        [
            '+(a|*\\|c\\\\|d\\\\\\|e\\\\\\\\|f\\\\\\\\\\|g',
            ['+(a|b\\|c\\|d\\|e\\\\|f\\\\|g'],
            0,
            ['+(a|b\\|c\\|d\\|e\\\\|f\\\\|g', 'a', 'b\\c']
        ],

        # crazy nested {,,} and *(||) tests.
        lambda files: files.clear(),
        lambda files: files.extend(
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
        # [
        #   'a?b',
        #   ['x/y/acb', 'acb/'],
        #   {matchBase: True},
        #   ['x/y/acb', 'acb/', 'acb/d/e', 'x/y/acb/d']
        # ],
        ['#*', ['#a', '#b'], 0, ['#a', '#b', 'c#d']],

        # begin channelling Boole and deMorgan...
        'negation tests',
        lambda files: files.clear(),
        lambda files: files.extend(['d', 'e', '!ab', '!abc', 'a!b', '\\!a']),

        # anything that is NOT a* matches.
        ['!a*', ['\\!a', 'd', 'e', '!ab', '!abc']],

        # anything that IS !a* matches.
        ['!a*', ['!ab', '!abc'], glob.N],

        # # anything that IS a* matches
        # ['!!a*', ['a!b']],

        # anything that is NOT !a* matches
        ['!\\!a*', ['a!b', 'd', 'e', '\\!a']],

        # negation nestled within a pattern
        lambda files: files.clear(),
        lambda files: files.extend(
            [
                'foo.js',
                'foo.bar',
                'foo.js.js',
                'blar.js',
                'foo.',
                'boo.js.boo'
            ]
        ),
        # last one is tricky! * matches foo, . matches ., and 'js.js' != 'js'
        # copy bash 4.3 behavior on this.
        ['*.!(js)', ['foo.bar', 'foo.', 'boo.js.boo', 'foo.js.js']],

        'https://github.com/isaacs/minimatch/issues/5',
        lambda files: files.clear(),
        lambda files: files.extend(
            [
                'a/b/.x/c', 'a/b/.x/c/d', 'a/b/.x/c/d/e', 'a/b/.x', 'a/b/.x/',
                'a/.x/b', '.x', '.x/', '.x/a', '.x/a/b', 'a/.x/b/.x/c', '.x/.x'
            ]
        ),
        [
            '**/.x/**',
            [
                '.x/', '.x/a', '.x/a/b', 'a/.x/b', 'a/b/.x/', 'a/b/.x/c',
                'a/b/.x/c/d', 'a/b/.x/c/d/e'
            ]
        ],

        'https://github.com/isaacs/minimatch/issues/59',
        ['[z-a]', []],
        ['a/[2015-03-10T00:23:08.647Z]/z', []],
        ['[a-0][a-\u0100]', []]
    ]

    matches = {
        'bar.min.js': {
            '*.!(js|css)': True,
            '!*.+(js|css)': False,
            '*.+(js|css)': True
        },

        'a-integration-test.js': {
            '*.!(j)': True,
            '!(*-integration-test.js)': False,
            '*-!(integration-)test.js': True,
            '*-!(integration)-test.js': False,
            '*!(-integration)-test.js': True,
            '*!(-integration-)test.js': True,
            '*!(integration)-test.js': True,
            '*!(integration-test).js': True,
            '*-!(integration-test).js': True,
            '*-!(integration-test.js)': True,
            '*-!(integra)tion-test.js': False,
            '*-integr!(ation)-test.js': False,
            '*-integr!(ation-t)est.js': False,
            '*-i!(ntegration-)test.js': False,
            '*i!(ntegration-)test.js': True,
            '*te!(gration-te)st.js': True,
            '*-!(integration)?test.js': False,
            '*?!(integration)?test.js': True
        },

        'foo-integration-test.js': {
            'foo-integration-test.js': True,
            '!(*-integration-test.js)': False
        },

        'foo.jszzz.js': {
            '*.!(js).js': True
        },

        'asd.jss': {
            '*.!(js)': True
        },

        'asd.jss.xyz': {
            '*.!(js).!(xy)': True
        },

        'asd.jss.xy': {
            '*.!(js).!(xy)': False
        },

        'asd.js.xyz': {
            '*.!(js).!(xy)': False
        },

        'asd.js.xy': {
            '*.!(js).!(xy)': False
        },

        'asd.sjs.zxy': {
            '*.!(js).!(xy)': True
        },

        'asd..xyz': {
            '*.!(js).!(xy)': True
        },

        'asd..xy': {
            '*.!(js).!(xy)': False,
            '*.!(js|x).!(xy)': False
        },

        'foo.js.js': {
            '*.!(js)': True
        },

        'testjson.json': {
            '*(*.json|!(*.js))': True,
            '+(*.json|!(*.js))': True,
            '@(*.json|!(*.js))': True,
            '?(*.json|!(*.js))': True
        },

        'foojs.js': {
            '*(*.json|!(*.js))': False,  # XXX bash 4.3 disagrees!
            '+(*.json|!(*.js))': False,  # XXX bash 4.3 disagrees!
            '@(*.json|!(*.js))': False,
            '?(*.json|!(*.js))': False
        },

        'other.bar': {
            '*(*.json|!(*.js))': True,
            '+(*.json|!(*.js))': True,
            '@(*.json|!(*.js))': True,
            '?(*.json|!(*.js))': True
        }

    }

    def setUp(self):
        """Setup the tests."""
        self.files = self.FILES[:]
        # The tests we scraped were written with this assumed.
        self.flags = glob.NEGATE

    def _filter(self, p):
        """Filter with glob pattern."""

        if callable(p):
            p(self.files)
        elif isinstance(p, str):
            print(">>> ", p, '<<<\n')
        else:
            files = self.files if len(p) < 4 else p[3]
            flags = 0 if len(p) < 3 else p[2]
            flags = self.flags ^ flags
            pat = p[0] if isinstance(p[0], list) else [p[0]]
            print("PATTERN: ", p[0])
            print("FILES: ", files)
            print("FLAGS: ", bin(flags)[2:])
            result = sorted(
                glob.globfilter(
                    files,
                    pat,
                    flags=flags
                )
            )
            source = sorted(p[1])
            print("TEST: ", result, '<==>', source, '\n')
            self.assertEqual(result, source)

    @mock.patch('wcmatch.util.platform')
    @mock.patch('wcmatch.util.is_case_sensitive')
    def test_glob_filter(self, mock__iscase_sensitive, mock_platform):
        """Test wildcard parsing."""

        mock_platform.return_value = "linux"
        mock__iscase_sensitive.return_value = True
        _wcparse._compile.cache_clear()

        for p in self.file_filter:
            self._filter(p)

    def test_ignore_cases(self):
        """Test ignore cases."""

        for filename, tests in self.matches.items():
            for pattern, goal in tests.items():
                print("PATTERN: ", pattern)
                print("FILE: ", filename)
                print("GOAL: ", goal)

                self.assertTrue(glob.globmatch(filename, pattern) == goal)

    def test_unfinished_ext(self):
        """Test unfinished ext."""

        for x in ['!', '?', '+', '*', '@']:
            self.assertTrue(glob.globmatch(x + '(a|B', x + '(a|B'))
            self.assertFalse(glob.globmatch(x + '(a|B', 'B'))

    @mock.patch('wcmatch.util.platform')
    @mock.patch('wcmatch.util.is_case_sensitive')
    def test_glob_parsing_windows(self, mock__iscase_sensitive, mock_platform):
        """Test wildcard parsing."""

        mock_platform.return_value = "windows"
        mock__iscase_sensitive.return_value = False
        _wcparse._compile.cache_clear()

        self.assertTrue(
            glob.globmatch(
                'some/name/with/named/file/test.py',
                '**/named/file/*.py'
            )
        )
        self.assertTrue(
            glob.globmatch(
                'some/name/with/na[/]med/file/test.py',
                '**/na[/]med/file/*.py'
            )
        )
        self.assertTrue(
            glob.globmatch(
                'some/name/with/na[/]med\\/file/test.py',
                '**/na[/]med\\/file/*.py'
            )
        )
        self.assertTrue(
            glob.globmatch(
                'some/name/with/na[\\]med/file/test.py',
                r'**/na[\\]med/file/*.py', flags=fnmatch.R
            )
        )
        self.assertTrue(
            glob.globmatch(
                'some\\name\\with\\na[\\]med\\file\\test.py',
                r'**/na[\\]med/file/*.py',
                flags=fnmatch.R
            )
        )
        self.assertTrue(
            glob.globmatch(
                'some\\name\\with\\na[\\]med\\file*.py',
                r'**\\na[\\]med\\file\*.py',
                flags=fnmatch.R
            )
        )
        self.assertTrue(
            glob.globmatch(
                'some\\name\\with\\na[\\]med\\file\\test.py',
                r'**\\na[\\]m\ed\\file\\*.py',
                flags=fnmatch.R
            )
        )
        self.assertTrue(
            glob.globmatch(
                'some\\name\\with\\na[\\]med\\\\file\\test.py',
                r'**\\na[\\]m\ed\\/file\\*.py',
                flags=fnmatch.R
            )
        )
        self.assertTrue(
            glob.globmatch(
                'some\\name\\with\\na[\\\\]med\\\\file\\test.py',
                r'**\\na[\/]m\ed\/file\\*.py',
                flags=fnmatch.R
            )
        )

    @mock.patch('wcmatch.util.platform')
    @mock.patch('wcmatch.util.is_case_sensitive')
    def test_glob_parsing_nix(self, mock__iscase_sensitive, mock_platform):
        """Test wildcard parsing."""

        mock_platform.return_value = "linux"
        mock__iscase_sensitive.return_value = True
        _wcparse._compile.cache_clear()

        self.assertTrue(
            glob.globmatch(
                'some/name/with/named/file/test.py',
                '**/named/file/*.py'
            )
        )
        self.assertTrue(
            glob.globmatch(
                'some/name/with/na[/]med/file/test.py',
                '**/na[/]med/file/*.py'
            )
        )
        self.assertTrue(
            glob.globmatch(
                'some/name/with/na[/]med\\/file/test.py',
                '**/na[/]med\\/file/*.py'
            )
        )
        self.assertTrue(
            glob.globmatch(
                'some/name/with/na\\med/file/test.py',
                r'**/na[\\]med/file/*.py',
                flags=glob.R
            )
        )
        self.assertTrue(
            glob.globmatch(
                'some/name/with/na[\\/]med\\/file/test.py',
                r'**/na[\/]med\/file/*.py',
                flags=glob.R
            )
        )

    def test_glob_integrity(self):
        """Globmatch must match what glob globs."""

        # Number of slashes is inconsequential
        # Glob really looks at what is in between. Multiple slashes are the same as one separator.
        # UNC mounts are special cases and it matters there.
        self.assertTrue(all([glob.globmatch(x, '**/../*.{md,py}') for x in glob.glob('**/../*.{md,py}')]))
        self.assertTrue(all([glob.globmatch(x, './**/./../*.py') for x in glob.glob('./**/./../*.py')]))
        self.assertTrue(all([glob.globmatch(x, './///**///./../*.py') for x in glob.glob('./**/.//////..////*.py')]))


class TestWildcard(unittest.TestCase):
    """Test wildcard pattern parsing."""

    @mock.patch('wcmatch.util.is_case_sensitive')
    def test_wildcard_parsing(self, mock__iscase_sensitive):
        """Test wildcard parsing."""

        mock__iscase_sensitive.return_value = True

        _wcparse._compile.cache_clear()

        p1, p2 = fnmatch.translate(
            fnmatch.fnsplit('*test[a-z]?|*test2[a-z]?|!test[!a-z]|!test[!-|a-z]'), flags=fnmatch.N
        )
        if util.PY36:
            self.assertEqual(p1, r'^(?s:(?=.).*?test[a-z].|(?=.).*?test2[a-z].)$')
            self.assertEqual(p2, r'^(?s:test[^a-z]|test[^\-\|a-z])$')
        else:
            self.assertEqual(p1, r'(?ms)^(?:(?=.).*?test[a-z].|(?=.).*?test2[a-z].)$')
            self.assertEqual(p2, r'(?ms)^(?:test[^a-z]|test[^\-\|a-z])$')

        p1, p2 = fnmatch.translate(
            fnmatch.fnsplit('*test[a-z]?|*test2[a-z]?|-test[!a-z]|-test[!-|a-z]'), flags=fnmatch.M | fnmatch.N
        )
        if util.PY36:
            self.assertEqual(p1, r'^(?s:(?=.).*?test[a-z].|(?=.).*?test2[a-z].)$')
            self.assertEqual(p2, r'^(?s:test[^a-z]|test[^\-\|a-z])$')
        else:
            self.assertEqual(p1, r'(?ms)^(?:(?=.).*?test[a-z].|(?=.).*?test2[a-z].)$')
            self.assertEqual(p2, r'(?ms)^(?:test[^a-z]|test[^\-\|a-z])$')

        p1, p2 = fnmatch.translate(fnmatch.fnsplit('test[]][!][][]', flags=fnmatch.F), flags=fnmatch.F)
        if util.PY36:
            self.assertEqual(p1, r'^(?s:test[\]][^\][]\[\])$')
            self.assertEqual(p2, None)
        else:
            self.assertEqual(p1, r'(?ms)^(?:test[\]][^\][]\[\])$')
            self.assertEqual(p2, None)

        p1, p2 = fnmatch.translate(fnmatch.fnsplit('test[!]'))
        if util.PY36:
            self.assertEqual(p1, r'^(?s:test\[\!\])$')
            self.assertEqual(p2, None)
        else:
            self.assertEqual(p1, r'(?ms)^(?:test\[\!\])$')
            self.assertEqual(p2, None)

        p1, p2 = fnmatch.translate(fnmatch.fnsplit('|test|'))
        if util.PY36:
            self.assertEqual(p1, r'^(?s:|test|)$')
            self.assertEqual(p2, None)
        else:
            self.assertEqual(p1, r'(?ms)^(?:|test|)$')
            self.assertEqual(p2, None)

        p1, p2 = fnmatch.translate(fnmatch.fnsplit('!|!test|!'), flags=fnmatch.N)
        if util.PY36:
            self.assertEqual(p1, r'^(?s:.*?)$')
            self.assertEqual(p2, r'^(?s:|test|)$')
        else:
            self.assertEqual(p1, r'(?ms)^(?:.*?)$')
            self.assertEqual(p2, r'(?ms)^(?:|test|)$')

        p1, p2 = fnmatch.translate(fnmatch.fnsplit('-|-test|-'), flags=fnmatch.M | fnmatch.N)
        if util.PY36:
            self.assertEqual(p1, r'^(?s:.*?)$')
            self.assertEqual(p2, r'^(?s:|test|)$')
        else:
            self.assertEqual(p1, r'(?ms)^(?:.*?)$')
            self.assertEqual(p2, r'(?ms)^(?:|test|)$')

        p1, p2 = fnmatch.translate(fnmatch.fnsplit('test[^chars]'))
        if util.PY36:
            self.assertEqual(p1, r'^(?s:test[^chars])$')
            self.assertEqual(p2, None)
        else:
            self.assertEqual(p1, r'(?ms)^(?:test[^chars])$')
            self.assertEqual(p2, None)

        p1 = fnmatch.translate(fnmatch.fnsplit(r'test[^\\-\\&]'))[0]
        if util.PY36:
            self.assertEqual(p1, r'^(?s:test[^\\-\\\&])$')
        else:
            self.assertEqual(p1, r'(?ms)^(?:test[^\\-\\\&])$')

        # BROKEN
        p1 = fnmatch.translate(fnmatch.fnsplit(r'\\*\\?\\|\\[\\]'))[0]
        if util.PY36:
            self.assertEqual(p1, r'^(?s:\\.*?\\.\\|\\[\\])$')
        else:
            self.assertEqual(p1, r'(?ms)^(?:\\.*?\\.\\|\\[\\])$')

        p1 = fnmatch.translate(fnmatch.fnsplit(r'\\u0300', flags=fnmatch.R), flags=fnmatch.R)[0]
        if util.PY36:
            self.assertEqual(p1, r'^(?s:\\u0300)$')
        else:
            self.assertEqual(p1, r'(?ms)^(?:\\u0300)$')

        self.assertEqual(
            fnmatch.filter(['testm', 'test\\3', 'testa'], fnmatch.fnsplit(r'te\st[ma]')),
            ['testm', 'testa']
        )

        self.assertTrue(fnmatch.fnmatch('test\test', r'test\test', flags=fnmatch.R))
        self.assertTrue(fnmatch.fnmatch('testtest', r'test\test'))
        self.assertTrue(fnmatch.fnmatch('test\\test', r'test\\test', flags=fnmatch.R))
        self.assertTrue(fnmatch.fnmatch('test\\test', r'test\\test'))
        self.assertTrue(fnmatch.fnmatch('test\\m', r'test\\m'))
        self.assertTrue(fnmatch.fnmatch('test\\b', r'test\\[a-z]'))
        self.assertTrue(fnmatch.fnmatch('test\\b', r'test\\[a-z]', flags=fnmatch.R))
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

        _wcparse._compile.cache_clear()

        p1, p2 = fnmatch.translate(
            fnmatch.fnsplit(b'*test[a-z]?|*test2[a-z]?|!test[!a-z]|!test[!-|a-z]'), flags=fnmatch.N
        )
        if util.PY36:
            self.assertEqual(p1, br'^(?s:(?=.).*?test[a-z].|(?=.).*?test2[a-z].)$')
            self.assertEqual(p2, br'^(?s:test[^a-z]|test[^\-\|a-z])$')
        else:
            self.assertEqual(p1, br'(?ms)^(?:(?=.).*?test[a-z].|(?=.).*?test2[a-z].)$')
            self.assertEqual(p2, br'(?ms)^(?:test[^a-z]|test[^\-\|a-z])$')

        p1, p2 = fnmatch.translate(
            fnmatch.fnsplit(b'*test[a-z]?|*test2[a-z]?|-test[!a-z]|-test[!-|a-z]'),
            flags=fnmatch.M | fnmatch.N
        )
        if util.PY36:
            self.assertEqual(p1, br'^(?s:(?=.).*?test[a-z].|(?=.).*?test2[a-z].)$')
            self.assertEqual(p2, br'^(?s:test[^a-z]|test[^\-\|a-z])$')
        else:
            self.assertEqual(p1, br'(?ms)^(?:(?=.).*?test[a-z].|(?=.).*?test2[a-z].)$')
            self.assertEqual(p2, br'(?ms)^(?:test[^a-z]|test[^\-\|a-z])$')

        p1, p2 = fnmatch.translate(fnmatch.fnsplit(b'test[]][!][][]'))
        if util.PY36:
            self.assertEqual(p1, br'^(?s:test[\]][^\][]\[\])$')
            self.assertEqual(p2, None)
        else:
            self.assertEqual(p1, br'(?ms)^(?:test[\]][^\][]\[\])$')
            self.assertEqual(p2, None)

        p1, p2 = fnmatch.translate(fnmatch.fnsplit(b'test[!]'))
        if util.PY36:
            self.assertEqual(p1, br'^(?s:test\[\!\])$')
            self.assertEqual(p2, None)
        else:
            self.assertEqual(p1, br'(?ms)^(?:test\[\!\])$')
            self.assertEqual(p2, None)

        p1, p2 = fnmatch.translate(fnmatch.fnsplit(b'|test|'))
        if util.PY36:
            self.assertEqual(p1, br'^(?s:|test|)$')
            self.assertEqual(p2, None)
        else:
            self.assertEqual(p1, br'(?ms)^(?:|test|)$')
            self.assertEqual(p2, None)

        p1, p2 = fnmatch.translate(fnmatch.fnsplit(b'!|!test|!'), flags=fnmatch.N)
        if util.PY36:
            self.assertEqual(p1, br'^(?s:.*?)$')
            self.assertEqual(p2, br'^(?s:|test|)$')
        else:
            self.assertEqual(p1, br'(?ms)^(?:.*?)$')
            self.assertEqual(p2, br'(?ms)^(?:|test|)$')

        p1, p2 = fnmatch.translate(fnmatch.fnsplit(b'-|-test|-'), flags=fnmatch.M | fnmatch.N)
        if util.PY36:
            self.assertEqual(p1, br'^(?s:.*?)$')
            self.assertEqual(p2, br'^(?s:|test|)$')
        else:
            self.assertEqual(p1, br'(?ms)^(?:.*?)$')
            self.assertEqual(p2, br'(?ms)^(?:|test|)$')

        p1, p2 = fnmatch.translate(fnmatch.fnsplit(b'test[^chars]'))
        if util.PY36:
            self.assertEqual(p1, br'^(?s:test[^chars])$')
            self.assertEqual(p2, None)
        else:
            self.assertEqual(p1, br'(?ms)^(?:test[^chars])$')
            self.assertEqual(p2, None)

        p1 = fnmatch.translate(fnmatch.fnsplit(br'test[^\\-\\&]'))[0]
        if util.PY36:
            self.assertEqual(p1, br'^(?s:test[^\\-\\\&])$')
        else:
            self.assertEqual(p1, br'(?ms)^(?:test[^\\-\\\&])$')

        # BROKEN
        p1 = fnmatch.translate(fnmatch.fnsplit(br'\\*\\?\\|\\[\\]'))[0]
        if util.PY36:
            self.assertEqual(p1, br'^(?s:\\.*?\\.\\|\\[\\])$')
        else:
            self.assertEqual(p1, br'(?ms)^(?:\\.*?\\.\\|\\[\\])$')

        p1 = fnmatch.translate(fnmatch.fnsplit(br'\\u0300'), flags=fnmatch.R)[0]
        if util.PY36:
            self.assertEqual(p1, br'^(?s:\\u0300)$')
        else:
            self.assertEqual(p1, br'(?ms)^(?:\\u0300)$')

        self.assertEqual(
            fnmatch.filter([b'testm', b'test\\3', b'testa'], fnmatch.fnsplit(br'te\st[ma]')),
            [b'testm', b'testa']
        )

        self.assertTrue(fnmatch.fnmatch(b'test\test', br'test\test', flags=fnmatch.R))
        self.assertTrue(fnmatch.fnmatch(b'testtest', br'test\test'))
        self.assertTrue(fnmatch.fnmatch(b'test\\test', br'test\\test', flags=fnmatch.R))
        self.assertTrue(fnmatch.fnmatch(b'test\\test', br'test\\test'))
        self.assertTrue(fnmatch.fnmatch(b'test\\m', br'test\\m'))
        self.assertTrue(fnmatch.fnmatch(b'test\\b', br'test\\[a-z]'))
        self.assertTrue(fnmatch.fnmatch(b'test\\b', br'test\\[a-z]', flags=fnmatch.R))
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

        _wcparse._compile.cache_clear()

        p1, p2 = fnmatch.translate(r'test\x70\u0070\U00000070\160\N{LATIN SMALL LETTER P}', flags=fnmatch.R)
        if util.PY36:
            self.assertEqual(p1, r'^(?s:testppppp)$')
            self.assertEqual(p2, None)
        else:
            self.assertEqual(p1, r'(?ms)^(?:testppppp)$')
            self.assertEqual(p2, None)

        p1, p2 = fnmatch.translate(r'test[\x70][\u0070][\U00000070][\160][\N{LATIN SMALL LETTER P}]', flags=fnmatch.R)
        if util.PY36:
            self.assertEqual(p1, r'^(?s:test[p][p][p][p][p])$')
            self.assertEqual(p2, None)
        else:
            self.assertEqual(p1, r'(?ms)^(?:test[p][p][p][p][p])$')
            self.assertEqual(p2, None)

        p1, p2 = fnmatch.translate(r'test\t\m', flags=fnmatch.R)
        if util.PY36:
            self.assertEqual(p1, r'^(?s:test\	m)$')
            self.assertEqual(p2, None)
        else:
            self.assertEqual(p1, r'(?ms)^(?:test\	m)$')
            self.assertEqual(p2, None)

        p1, p2 = fnmatch.translate(r'test[\\]test', flags=fnmatch.R)
        if util.PY36:
            self.assertEqual(p1, r'^(?s:test[\\]test)$')
            self.assertEqual(p2, None)
        else:
            self.assertEqual(p1, r'(?ms)^(?:test[\\]test)$')
            self.assertEqual(p2, None)

        p1, p2 = fnmatch.translate('test[\\')
        if util.PY36:
            self.assertEqual(p1, r'^(?s:test\[\\)$')
            self.assertEqual(p2, None)
        else:
            self.assertEqual(p1, r'(?ms)^(?:test\[\\)$')
            self.assertEqual(p2, None)

        p1, p2 = fnmatch.translate(r'test\44test', flags=fnmatch.R)
        if util.PY36:
            self.assertEqual(p1, r'^(?s:test\$test)$')
            self.assertEqual(p2, None)
        else:
            self.assertEqual(p1, r'(?ms)^(?:test\$test)$')
            self.assertEqual(p2, None)

        p1, p2 = fnmatch.translate(r'test\44', flags=fnmatch.R)
        if util.PY36:
            self.assertEqual(p1, r'^(?s:test\$)$')
            self.assertEqual(p2, None)
        else:
            self.assertEqual(p1, r'(?ms)^(?:test\$)$')
            self.assertEqual(p2, None)

        p1, p2 = fnmatch.translate(r'test\400', flags=fnmatch.R)
        if util.PY36:
            self.assertEqual(p1, r'^(?s:test\Ā)$')
            self.assertEqual(p2, None)
        else:
            self.assertEqual(p1, r'(?ms)^(?:test\Ā)$')
            self.assertEqual(p2, None)

        with pytest.raises(SyntaxError):
            fnmatch.translate(r'test\N', flags=fnmatch.R)

        with pytest.raises(SyntaxError):
            fnmatch.translate(r'test\Nx', flags=fnmatch.R)

        with pytest.raises(SyntaxError):
            fnmatch.translate(r'test\N{', flags=fnmatch.R)


class TestDirWalker(unittest.TestCase):
    """Test the _DirWalker class."""

    def setUp(self):
        """Setup the tests."""

        self.default_flags = wcmatch.R | wcmatch.I | wcmatch.M
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

        walker = wcmatch.WcMatch(
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

        walker = wcmatch.WcMatch(
            'tests/dir_walker',
            '*.*|-*.file', None,
            False, False, self.default_flags
        )

        self.crawl_files(walker)

        self.assertEqual(self.skipped, 2)
        self.assertEqual(len(self.files), 2)

    def test_recursive(self):
        """Test non-recursive search."""

        walker = wcmatch.WcMatch(
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

        walker = wcmatch.WcMatch(
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

        walker = wcmatch.WcMatch(
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

        walker = wcmatch.WcMatch(
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

        walker = wcmatch.WcMatch(
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

        walker = wcmatch.WcMatch(
            'tests/dir_walker',
            '*.txt*', None,
            True, True, self.default_flags
        )

        walker.kill()
        records = 0
        for f in walker.imatch():
            records += 1

        self.assertTrue(records == 1 or walker.get_skipped() == 1)
