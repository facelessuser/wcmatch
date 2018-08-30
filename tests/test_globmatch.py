# -*- coding: utf-8 -*-
"""Tests for rumcore."""
import unittest
import mock
import wcmatch.glob as glob
import wcmatch._wcparse as _wcparse
import wcmatch.util as util


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
        """Get option vallue."""

        return self._options.get(key, default)


class TestGlobFilter(unittest.TestCase):
    """Test matchtes against `globfilter`.

    Each list entry in `cases` is run through the `globsplit` and then `globfilter`.
    Entries are run through `globsplit` ensure it does not add any unintended side effects.

    There are a couple special types that can be inserted in the case list that can alter
    the behavior of the cases that follow.

    * Strings: These will be printed and then the next case will be processed.
    * Options: This object takes keyword parameters that are used to alter the next tests options:
        * skip_split: If set to `True`, this will cause the next tests to be skipped when we are processing
            cases with `globsplit`.
    * GlobFiles: This object takes a list of file paths and will set them as the current file list to
        compare against.  If `append` is set to `True`, it will extend the test's filelist instead of
        replacing.

    Each test case entry (list) is an array of up to 4 parameters (2 minimum).

    * Pattern
    * Expected result (filenames matched by the pattern)
    * Flags
    * List of files that will temporarily override the current main filelist just for this specific case.

    The default flags are: NEGATE | GLOBSTAR | EXTGLOB | BRACE. If any of these flags are provided in
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
        [
            '**',
            [
                'a', 'b', 'c', 'd', 'abc',
                'abd', 'abe', 'bb', 'bcd',
                'ca', 'cb', 'dd', 'de',
                'bdir/', 'bdir/cfile'
            ]
        ],

        [r'\\.\\./*/', []],
        [r's/\\..*//', []],

        'legendary larry crashes bashes',
        ['/^root:/{s/^[^:]*:[^:]*:\\([^:]*\\).*$/\\1/', []],
        ['/^root:/{s/^[^:]*:[^:]*:\\([^:]*\\).*$/\u0001/', []],

        'character classes',
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

        'http://www.opensource.apple.com/source/bash/bash-23/bash/tests/glob-test',
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
        ['\\', ['\\'], 0, ['\\']],
        ['[\\\\]', (['\\'] if util.is_case_sensitive() else []), 0, ['\\']],
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
        ['{/*,*}', [], 0, ['/asdf/asdf/asdf']],
        ['{/?,*}', ['/a', 'bb'], 0, ['/a', '/b/b', '/a/b/c', 'bb']],

        'dots should not match unless requested',
        ['**', ['a/b'], 0, ['a/b', 'a/.d', '.a/.d']],

        # .. and . can only match patterns starting with .,
        # even when options.dot is set.
        GlobFiles(['a/./b', 'a/../b', 'a/c/b', 'a/.d/b']),
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
        # NOTE: We don't support these so they should work fine.
        ['[!a*', ['[!ab'], 0, ['[!ab', '[ab']],
        ['[#a*', ['[#ab'], 0, ['[#ab', '[ab']],

        # The following tests have `|` not included in things like +(...) etc.
        # We run these tests through normally and through glob.globsplit which splits
        # patterns on unenclosed `|`, so disable these few tests during split tests.
        Options(skip_split=True),
        # like: {a,b|c\\,d\\\|e} except it's unclosed, so it has to be escaped.
        # NOTE: I don't know what the original test was doing because it was matching
        # something crazy. Multimatch regex expanded to escapes to like a 50.
        # I think ours expands them proper, so the original test has been altered.
        [
            '+(a|*\\|c\\\\|d\\\\\\|e\\\\\\\\|f\\\\\\\\\\|g',
            (['+(a|b\\|c\\|d\\|e\\\\|f\\\\|g'] if util.is_case_sensitive() else []),
            0,
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
        # test extglob nested in extglob
        [
            '@(a@(c|d)|c@(b|,d))',
            ['ac', 'ad', 'cb', 'c,d']
        ],

        # NOTE: We don't currently support the base match option
        # [
        #   'a?b',
        #   ['x/y/acb', 'acb/'],
        #   {matchBase: True},
        #   ['x/y/acb', 'acb/', 'acb/d/e', 'x/y/acb/d']
        # ],
        ['#*', ['#a', '#b'], 0, ['#a', '#b', 'c#d']],

        # begin channelling Boole and deMorgan...
        # NOTE: We changed these to `-` since our negation dosn't use `!`.
        'negation tests',
        GlobFiles(['d', 'e', '!ab', '!abc', 'a!b', '\\!a']),

        # anything that is NOT a* matches.
        ['!a*', ['\\!a', 'd', 'e', '!ab', '!abc']],

        # anything that IS !a* matches.
        ['!a*', ['!ab', '!abc'], glob.N],

        # NOTE: We don't allow negating negation.
        # # anything that IS a* matches
        # ['!!a*', ['a!b']],

        # anything that is NOT !a* matches
        ['!\\!a*', ['a!b', 'd', 'e', '\\!a']],

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
        # last one is tricky! * matches foo, . matches ., and 'js.js' != 'js'
        # copy bash 4.3 behavior on this.
        ['*.!(js)', ['foo.bar', 'foo.', 'boo.js.boo', 'foo.js.js']],

        'https://github.com/isaacs/minimatch/issues/5',
        GlobFiles(
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
        ['[a-0][a-\u0100]', []],

        'Consecutive slashes.',
        GlobFiles(
            [
                'a/b/c', 'd/e/f', 'a/e/c'
            ]
        ),
        ['*//e///*', ['d/e/f', 'a/e/c']],
        [r'*//\e///*', ['d/e/f', 'a/e/c']],

        'Backslash trailing cases',
        GlobFiles(
            [
                'a/b/c/', 'd/e/f/', 'a/e/c/'
            ]
        ),
        ['**\\', [] if util.is_case_sensitive() else ['a/b/c/', 'd/e/f/', 'a/e/c/']],

        'Invalid extglob groups',
        GlobFiles(
            [
                '@([test', '@([test\\', '@(test\\', 'test['
            ]
        ),
        ['@([test', ['@([test'] if util.is_case_sensitive() else ['@([test', '@([test\\']],
        ['@([test\\', ['@([test\\']],
        ['@(test\\', ['@(test\\']],
        ['@(test[)', ['test[']],

        'Inverse dot tests',
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

        "Slash exclusion",
        GlobFiles(
            [
                'test/test', 'test\\/test'
            ]
        ),
        ['test/test', ['test/test'], glob.F],
        ['test\\/test', ['test\\/test'], glob.F],
        ['@(test/test)', [], glob.F],
        [r'@(test\/test)', [], glob.F],
        ['test[/]test', [], glob.F],
        [r'test[\/]test', [], glob.F]
    ]

    def setUp(self):
        """Setup the tests."""

        self.files = []
        # The tests we scraped were written with this assumed.
        self.flags = glob.NEGATE | glob.GLOBSTAR | glob.EXTGLOB | glob.BRACE
        self.skip_split = False

    def norm_files(self, files, flags):
        """Normalize files."""

        flags = glob._flag_transform(flags)
        unix = _wcparse.is_unix_style(flags)

        return [(util.norm_slash(x) if not unix else x) for x in files]

    def _filter(self, p, split=False):
        """Filter with glob pattern."""

        if isinstance(p, GlobFiles):
            if p.append:
                self.files.extend(p.filelist)
            else:
                self.files.clear()
                self.files.extend(p.filelist)
        elif isinstance(p, Options):
            self.skip_split = p.get('skip_split', False)
        elif isinstance(p, str):
            print(">>> ", p, '<<<\n')
        else:
            files = self.files if len(p) < 4 else p[3]
            flags = 0 if len(p) < 3 else p[2]
            flags = self.flags ^ flags
            pat = p[0] if isinstance(p[0], list) else [p[0]]
            if split and self.skip_split:
                return
            if split:
                new_pat = []
                for x in pat:
                    new_pat.extend(list(glob.globsplit(x, flags=flags)))
                pat = new_pat
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
            source = sorted(self.norm_files(p[1], flags))
            print("TEST: ", result, '<==>', source, '\n')
            self.assertEqual(result, source)

    def test_glob_filter(self):
        """Test wildcard parsing."""

        _wcparse._compile.cache_clear()

        for p in self.cases:
            self._filter(p)

    def test_glob_split_filter(self):
        """Test wildcard parsing by first splitting on `|`."""

        _wcparse._compile.cache_clear()

        for p in self.cases:
            self._filter(p, split=True)


class TestGlobMatch(unittest.TestCase):
    """
    Tests that are performed against globmatch.

    Each case entry is a list of 4 parameters.

    * Pattern
    * Filename
    * Expected result (boolean of whether pattern matched filename)
    * Flags

    The default flags are NEGATE | GLOBSTAR | EXTGLOB | BRACE. Any flags passed through via entry are XORed.
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
        ['?(*.json|!(*.js))', 'other.bar', True, glob.N]
    ]

    def setUp(self):
        """Setup default flag options."""

        # The tests we scraped were written with this assumed.
        self.flags = glob.NEGATE | glob.GLOBSTAR | glob.EXTGLOB | glob.BRACE

    def test_cases(self):
        """Test ignore cases."""

        for case in self.cases:
            pattern = case[0]
            filename = case[1]
            goal = case[2]
            flags = self.flags
            if len(case) > 3:
                flags ^= case[3]

            print("PATTERN: ", pattern)
            print("FILE: ", filename)
            print("GOAL: ", goal)
            print("FLAGS: ", bin(flags))

            self.assertTrue(glob.globmatch(filename, pattern, flags=flags) == goal)


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

    def test_windows_drives(self):
        """Test windows drives."""

        if util.is_case_sensitive():
            return

        self.assertTrue(
            glob.globmatch(
                '//?/c:/somepath/to/match/file.txt',
                '//?/c:/**/*.txt',
                flags=self.flags
            )
        )

        self.assertTrue(
            glob.globmatch(
                'c:/somepath/to/match/file.txt',
                'c:/**/*.txt',
                flags=self.flags
            )
        )

    @mock.patch('wcmatch.util.platform')
    @mock.patch('wcmatch.util.is_case_sensitive')
    def test_glob_parsing_win(self, mock__iscase_sensitive, mock_platform):
        """Test windows style glob parsing."""

        mock_platform.return_value = "windows"
        mock__iscase_sensitive.return_value = False
        _wcparse._compile.cache_clear()

        self.assertTrue(
            glob.globmatch(
                'some/name/with/named/file/test.py',
                '**/named/file/*.py',
                flags=self.flags
            )
        )
        self.assertTrue(
            glob.globmatch(
                'some/name/with/na[/]med/file/test.py',
                '**/na[/]med/file/*.py',
                flags=self.flags
            )
        )
        self.assertTrue(
            glob.globmatch(
                'some/name/with/na[/]med\\/file/test.py',
                '**/na[/]med\\/file/*.py',
                flags=self.flags
            )
        )
        self.assertTrue(
            glob.globmatch(
                'some/name/with/na[\\]med/file/test.py',
                r'**/na[\\]med/file/*.py',
                flags=self.flags | glob.R
            )
        )
        self.assertTrue(
            glob.globmatch(
                'some\\name\\with\\na[\\]med\\file\\test.py',
                r'**/na[\\]med/file/*.py',
                flags=self.flags | glob.R
            )
        )
        self.assertTrue(
            glob.globmatch(
                'some\\name\\with\\na[\\]med\\file*.py',
                r'**\\na[\\]med\\file\*.py',
                flags=self.flags | glob.R
            )
        )
        self.assertTrue(
            glob.globmatch(
                'some\\name\\with\\na[\\]med\\file\\test.py',
                r'**\\na[\\]m\ed\\file\\*.py',
                flags=self.flags | glob.R
            )
        )
        self.assertTrue(
            glob.globmatch(
                'some\\name\\with\\na[\\]med\\\\file\\test.py',
                r'**\\na[\\]m\ed\\/file\\*.py',
                flags=self.flags | glob.R
            )
        )
        self.assertTrue(
            glob.globmatch(
                'some\\name\\with\\na[\\\\]med\\\\file\\test.py',
                r'**\\na[\/]m\ed\/file\\*.py',
                flags=self.flags | glob.R
            )
        )

    @mock.patch('wcmatch.util.is_case_sensitive')
    def test_glob_translate(self, mock__iscase_sensitive):
        """Test glob transaltion."""

        mock__iscase_sensitive.return_value = True
        _wcparse._compile.cache_clear()

        if util.PY37:
            value = (
                [
                    '^(?s:(?:(?!(?:/|^)\\.).)*?(?:^|$|/)+(?![/.])[\x00-\x7f]/+stuff/+(?=.)'
                    '(?!(?:\\.{1,2})(?:$|/))(?:(?!\\.)[^/]*?)?[/]*?)$'
                ],
                []
            )
        elif util.PY36:
            value = (
                [
                    '^(?s:(?:(?!(?:\\/|^)\\.).)*?(?:^|$|\\/)+(?![\\/.])[\x00-\x7f]\\/+stuff\\/+(?=.)'
                    '(?!(?:\\.{1,2})(?:$|\\/))(?:(?!\\.)[^\\/]*?)?[\\/]*?)$'
                ],
                []
            )
        else:
            value = (
                [
                    '(?s)^(?:(?:(?!(?:\\/|^)\\.).)*?(?:^|$|\\/)+(?![\\/.])[\x00-\x7f]\\/+stuff\\/+(?=.)'
                    '(?!(?:\\.{1,2})(?:$|\\/))(?:(?!\\.)[^\\/]*?)?[\\/]*?)$'
                ],
                []
            )

        self.assertEqual(
            glob.translate('**/[[:ascii:]]/stuff/*', flags=self.flags),
            value
        )

    @mock.patch('wcmatch.util.is_case_sensitive')
    def test_glob_parsing_nix(self, mock__iscase_sensitive):
        """Test wildcard parsing."""

        mock__iscase_sensitive.return_value = True
        _wcparse._compile.cache_clear()

        self.assertTrue(
            glob.globmatch(
                'some/name/with/named/file/test.py',
                '**/named/file/*.py',
                flags=self.flags
            )
        )
        self.assertTrue(
            glob.globmatch(
                'some/name/with/na[/]med/file/test.py',
                '**/na[/]med/file/*.py',
                flags=self.flags
            )
        )
        self.assertTrue(
            glob.globmatch(
                'some/name/with/na[/]med\\/file/test.py',
                '**/na[/]med\\/file/*.py',
                flags=self.flags
            )
        )
        self.assertTrue(
            glob.globmatch(
                'some/name/with/na\\med/file/test.py',
                r'**/na[\\]med/file/*.py',
                flags=self.flags | glob.R
            )
        )
        self.assertTrue(
            glob.globmatch(
                'some/name/with/na[\\/]med\\/file/test.py',
                r'**/na[\/]med\/file/*.py',
                flags=self.flags | glob.R
            )
        )

    def test_glob_integrity(self):
        """Globmatch must match what glob globs."""

        # Number of slashes is inconsequential
        # Glob really looks at what is in between. Multiple slashes are the same as one separator.
        # UNC mounts are special cases and it matters there.
        self.assertTrue(
            all(
                [
                    glob.globmatch(
                        x, '**/../*.{md,py}', flags=self.flags
                    ) for x in glob.glob('**/../*.{md,py}', flags=self.flags)
                ]
            )
        )
        self.assertTrue(
            all(
                [
                    glob.globmatch(
                        x, './**/./../*.py', flags=self.flags
                    ) for x in glob.glob('./**/./../*.py', flags=self.flags)
                ]
            )
        )
        self.assertTrue(
            all(
                [
                    glob.globmatch(
                        x, './///**///./../*.py', flags=self.flags
                    ) for x in glob.glob('./**/.//////..////*.py', flags=self.flags)
                ]
            )
        )
