"""
Test inverse extended groups, `!(...)`, that sit inside other extended groups.

An inverse group that consumes some text is only valid if the rest of the pattern can match what is left, and if none
of the ways the rest could match would make the consumed text match one of the group's own patterns. The rest of the
pattern includes what follows the group inside its slot, and what follows the enclosing group.

Inside `+(...)` and `*(...)` groups, the rest only includes the remainder of the group's slot and whatever follows the
loop, it does not consider further iterations. Each iteration is judged as though it were the last one. This means
`+(!(foo))` does not match `foo`, just like `!(foo)`, even though `f` and `oo` each match `!(foo)`.

An inverse group inside the patterns of another inverse group follows the same rule, the text it can consume has to end
where the text consumed by the outer group ends. This is exact when what follows the outer group has a fixed length,
as only one place is left for it to end.

The reference model below implements the first rule directly with a simple backtracking matcher. It is used to check
that the regular expressions produced by the parser follow the rule.
"""
import itertools
import os
import random
import re

import pytest

from wcmatch import fnmatch, glob


def parse(pattern, i=0, stop=''):
    """Parse a pattern made of literals, `?`, `*`, and extended groups into a small tree."""

    nodes = []
    while i < len(pattern) and pattern[i] not in stop:
        c = pattern[i]
        if c in '?@*+!' and i + 1 < len(pattern) and pattern[i + 1] == '(':
            alts = []
            i += 2
            while True:
                alt, i = parse(pattern, i, '|)')
                alts.append(alt)
                i += 1
                if pattern[i - 1] == ')':
                    break
            nodes.append(('inv' if c == '!' else 'grp', c, alts))
        else:
            nodes.append(('lit', c) if c not in '*?' else (c,))
            i += 1
    return nodes, i


def model_match(nodes, name):
    """Match with the reference model."""

    end = len(name)

    def seq(items, pos, k, kl):
        """
        Match a sequence of nodes at `pos`, then call the continuation `k`.

        Inverse groups use `kl` to find the places where the rest of the pattern can match. It is the same as `k`,
        except in loops, where it skips any further iterations.
        """

        if not items:
            return k(pos)
        node, rest = items[0], items[1:]

        def cont(q):
            return seq(rest, q, k, kl)

        kind = node[0]
        if kind == 'lit':
            return pos < end and name[pos] == node[1] and cont(pos + 1)
        if kind == '?':
            return pos < end and cont(pos + 1)
        if kind == '*':
            return any(cont(e) for e in range(pos, end + 1))

        alts = node[2]

        def alts_match(start, k2, kl2):
            return any(seq(a, start, k2, kl2) for a in alts)

        if kind == 'grp':
            t = node[1]

            def here(q):
                """The rest after this group, up to the local end."""

                return cont(q) if kl is k else seq(rest, q, kl, kl)

            if t == '@':
                return alts_match(pos, cont, here)
            if t == '?':
                return cont(pos) or alts_match(pos, cont, here)

            def loop(start):
                def again(q):
                    return q > start and loop(q)

                return cont(start) or alts_match(start, again, here)

            if t == '*':
                return loop(pos)

            def first(q):
                return cont(q) or (q > pos and loop(q))

            return alts_match(pos, first, here)

        # Inverse group: none of the places where the rest can match may end a match of the group's patterns
        real_ends = [e for e in range(pos, end + 1) if cont(e)]
        local_ends = real_ends if kl is k else [e for e in range(pos, end + 1) if seq(rest, e, kl, kl)]

        def ends_at(e):
            return lambda q: q == e

        return bool(real_ends) and not any(alts_match(pos, ends_at(e), ends_at(e)) for e in local_ends)

    def top(q):
        return q == end

    return seq(nodes, 0, top, top)


def generate(rng, depth=0):
    """Generate a random pattern."""

    parts = []
    for _ in range(rng.choice([1, 2, 2, 3])):
        r = rng.random()
        if r < 0.28:
            parts.append(rng.choice('abc'))
        elif r < 0.38:
            parts.append('*')
        elif r < 0.44:
            parts.append('?')
        elif depth < 2:
            alts = [generate(rng, depth + 1) for _ in range(rng.choice([1, 1, 2, 2, 3]))]
            parts.append(rng.choice('?@*+!!!') + '(' + '|'.join(alts) + ')')
        else:
            parts.append(rng.choice('abc'))
    return ''.join(parts)


def inverse_placement(nodes, ancestors=()):
    """Find where the inverse groups are: in a loop, inside another inverse group, or neither."""

    found = set()
    for node in nodes:
        if node[0] in ('grp', 'inv'):
            kind = 'inv' if node[0] == 'inv' else node[1]
            if node[0] == 'inv':
                if 'inv' in ancestors:
                    found.add('in inverse')
                if any(a in '*+' for a in ancestors):
                    found.add('in loop')
            for alt in node[2]:
                found |= inverse_placement(alt, ancestors + (kind,))
    return found


NAMES = [''.join(p) for n in range(1, 5) for p in itertools.product('abc', repeat=n)]


def generate_patterns(seed, count, placement=frozenset()):
    """Generate patterns whose inverse groups are all in a loop, all in an inverse group, or all in neither."""

    rng = random.Random(seed)
    patterns = []
    seen = set()
    while len(patterns) < count:
        p = generate(rng)
        if '!(' in p and p not in seen and inverse_placement(parse(p)[0]) == placement:
            seen.add(p)
            patterns.append(p)
    return patterns


def generate_nested_patterns(seed, count):
    """Generate patterns with an inverse group inside another one, followed by text of a fixed length."""

    rng = random.Random(seed)
    patterns = []
    seen = set()
    while len(patterns) < count:
        inner = '|'.join(generate(rng, 1) for _ in range(rng.choice([1, 2, 2, 3])))
        pattern = rng.choice(['', 'a', 'b?', '?']) + '!(' + inner + ')' + rng.choice(['', 'a', 'b', 'ab', '?', 'c?'])
        if rng.random() < 0.3:
            pattern = '@(' + pattern + ')'
        if pattern not in seen and inverse_placement(parse(pattern)[0]) == {'in inverse'}:
            seen.add(pattern)
            patterns.append(pattern)
    return patterns


def fn_match(name, pattern, flags=0):
    """Match with `fnmatch`."""

    return fnmatch.fnmatch(name, pattern, flags=fnmatch.EXTMATCH | fnmatch.FORCEUNIX | flags)


def glob_match(name, pattern, flags=0):
    """Match with `globmatch`."""

    return glob.globmatch(name, pattern, flags=glob.EXTGLOB | glob.FORCEUNIX | flags)


MATCHERS = pytest.mark.parametrize('matcher', [fn_match, glob_match])

# Pattern, names that match, names that do not match.
CASES = [
    # The rest of the slot is part of what follows the inverse group
    ('@(!(a)b)', ['b', 'xb', 'abb'], ['ab', 'a']),
    ('@(!(a)*)', ['b', 'xa'], ['ab', 'a']),
    ('@(!(a)b|c)d', ['bd', 'xbd', 'cd'], ['abd', 'ab']),
    ('@(!(ab)?)c', ['xyc', 'ac', 'abc'], ['abxc']),
    # What follows the enclosing group is part of what follows the inverse group
    ('@(x|!(a))b', ['b', 'xb', 'cb', 'aab'], ['ab']),
    ('?(!(a))b', ['b', 'cb'], ['ab']),
    ('@(!(a)*)c', ['bc', 'xac', 'c'], ['abc']),
    ('@(!(a)b)@(!(c)d)', ['xbxd', 'bd'], ['abxd', 'bcd', 'xbcd']),
    # Groups that are merged into their parent keep the same meaning
    ('@(a|@(!(b)c))d', ['xcd', 'ad', 'cd'], ['bcd']),
    ('@(@(!(a)b))', ['xb', 'b'], ['ab']),
    ('@(a|@(!(b)c|d))e', ['xce', 'de', 'ae', 'ce'], ['bce', 'e', 'bde']),
    ('?(a|@(!(b)c|d))e', ['xce', 'de', 'ae', 'e'], ['bce']),
    ('+(a|@(!(b)c|d))e', ['xce', 'de', 'ade', 'ae'], ['bce']),
    ('@(@(!(b)c|d)|a)e', ['xce', 'de', 'ae'], ['bce']),
    # Inverse groups inside inverse groups
    ('!(!(a))', ['a'], ['aa', 'b', 'ab']),
    ('!(!(a)|b)', ['a'], ['aa', 'ab', 'b', 'c']),
    ('!(a!(b))', ['ab', 'b', 'ba'], ['a', 'aa', 'aba', 'abb']),
    ('!(!(a)b)', ['ab', 'a', 'c'], ['b', 'xb', 'abb']),
    ('!(a!(b)c)', ['abc', 'xac', 'a'], ['ac', 'abac']),
    ('!(a!(b)c)d', ['abcd', 'ad', 'xacd'], ['acd']),
    ('!(x|!(a)b)c', ['abc', 'c', 'yc'], ['xc', 'bc', 'aabc']),
    ('@(a|!(b!(c)))d', ['bcd', 'ad', 'xd'], ['bd', 'bxd']),
    # Each iteration is judged as though it were the last, so repeating names that match does not always match
    ('+(!(foo))', ['foobar', 'bar', 'f', 'fo', 'oo'], ['foo']),
    ('*(!(foo))', ['bar', 'fo'], ['foo']),
    ('+(!(ba))', ['a', 'b', 'bab', 'baa'], ['ba']),
    ('*(!(ab)|x)', ['aab', 'xab', 'x', 'b'], ['ab']),
    ('+(!(foo)|x)', ['xfoo', 'foox', 'xx'], ['foo']),
    # Inside loops, the rest is the remainder of the slot and what follows the loop
    ('+(!(a))', ['ab', 'b', 'aa'], ['a']),
    ('*(!(a)|b)', ['ab', 'b'], ['a']),
    ('+(!(a)b)c', ['xbc', 'xbxbc', 'bc'], ['abc']),
]


@MATCHERS
@pytest.mark.parametrize(('pattern', 'matches', 'excludes'), CASES)
def test_inverse_in_group(matcher, pattern, matches, excludes):
    """Test inverse groups inside groups."""

    for name in matches:
        assert matcher(name, pattern), (pattern, name)
    for name in excludes:
        assert not matcher(name, pattern), (pattern, name)


@MATCHERS
@pytest.mark.parametrize(('pattern', 'matches', 'excludes'), CASES)
def test_inverse_in_group_wrapped(matcher, pattern, matches, excludes):
    """A pattern keeps its meaning when it is wrapped in a group."""

    for name in matches:
        assert matcher(name, '@(' + pattern + ')'), (pattern, name)
    for name in excludes:
        assert not matcher(name, '@(' + pattern + ')'), (pattern, name)


@pytest.mark.parametrize('function', [fnmatch.translate, glob.translate])
@pytest.mark.parametrize(('pattern', 'matches', 'excludes'), CASES)
def test_inverse_in_group_capture(function, pattern, matches, excludes):
    """The capture flag only adds capturing groups, it does not change what matches."""

    flag = fnmatch.EXTMATCH if function is fnmatch.translate else glob.EXTGLOB
    flags = flag | (fnmatch.CAPTURE if function is fnmatch.translate else glob.CAPTURE)
    regex = re.compile(function(pattern, flags=flags)[0][0])

    for name in matches:
        assert regex.match(name), (pattern, name)
    for name in excludes:
        assert not regex.match(name), (pattern, name)


@pytest.mark.parametrize('as_bytes', [False, True])
@pytest.mark.parametrize(('pattern', 'matches', 'excludes'), CASES)
def test_inverse_in_group_bytes(pattern, matches, excludes, as_bytes):
    """Bytes and strings behave the same."""

    flags = fnmatch.EXTMATCH | fnmatch.FORCEUNIX
    if as_bytes:
        pattern, matches, excludes = pattern.encode(), [n.encode() for n in matches], [n.encode() for n in excludes]

    for name in matches:
        assert fnmatch.fnmatch(name, pattern, flags=flags), (pattern, name)
    for name in excludes:
        assert not fnmatch.fnmatch(name, pattern, flags=flags), (pattern, name)


@pytest.mark.parametrize('seed', [1, 2, 3])
def test_inverse_in_group_model(seed):
    """Check random patterns against the reference model."""

    bad = []
    for pattern in generate_patterns(seed, 120):
        nodes = parse(pattern)[0]
        for name in NAMES:
            if model_match(nodes, name) != fn_match(name, pattern):
                bad.append((pattern, name))
                break
    assert not bad, bad[:5]


@pytest.mark.parametrize('seed', [12, 13])
def test_inverse_in_loop_model(seed):
    """Check random inverse groups inside loops against the reference model."""

    bad = []
    for pattern in generate_patterns(seed, 40, frozenset({'in loop'})):
        nodes = parse(pattern)[0]
        for name in NAMES:
            if model_match(nodes, name) != fn_match(name, pattern):
                bad.append((pattern, name))
                break
    assert not bad, bad[:5]


@pytest.mark.parametrize('seed', [14, 15])
def test_inverse_in_loop_properties(seed):
    """
    Loops keep the properties that do not depend on how iterations are judged.

    A name that matches the loop's patterns on its own still matches when it is repeated once, and `+(...)` and
    `?(...)` can only match what `*(...)` does.
    """

    bad = []
    for pattern in generate_patterns(seed, 60):
        names = [n for n in NAMES if len(n) <= 3]
        single = {n for n in names if fn_match(n, pattern)}
        plus = {n for n in NAMES if fn_match(n, '+(' + pattern + ')')}
        star = {n for n in NAMES if fn_match(n, '*(' + pattern + ')')}
        optional = {n for n in NAMES if fn_match(n, '?(' + pattern + ')')}
        if not (single <= plus and single <= star and single <= optional and plus <= star and optional <= star):
            bad.append(pattern)
    assert not bad, bad[:5]


@pytest.mark.parametrize('seed', [10, 11])
def test_inverse_nested_model(seed):
    """Check random inverse groups inside inverse groups against the reference model."""

    bad = []
    for pattern in generate_nested_patterns(seed, 100):
        nodes = parse(pattern)[0]
        for name in NAMES:
            if model_match(nodes, name) != fn_match(name, pattern):
                bad.append((pattern, name))
                break
    assert not bad, bad[:5]


@pytest.mark.parametrize('seed', [4, 5])
def test_inverse_in_group_wrapped_random(seed):
    """Wrapping random patterns in a group, including ones with loops, does not change what they match."""

    rng = random.Random(seed)
    bad = []
    count = 0
    while count < 100:
        pattern = generate(rng)
        if '!(' not in pattern:
            continue
        count += 1
        for name in NAMES:
            if fn_match(name, pattern) != fn_match(name, '@(' + pattern + ')'):
                bad.append((pattern, name))
                break
    assert not bad, bad[:5]


@pytest.mark.parametrize('seed', [6, 7])
def test_inverse_in_group_capture_random(seed):
    """The capture flag does not change what random patterns match, including nested groups and loops."""

    rng = random.Random(seed)
    bad = []
    count = 0
    while count < 100:
        pattern = generate(rng)
        if '!(' not in pattern:
            continue
        count += 1
        regex = re.compile(fnmatch.translate(pattern, flags=fnmatch.EXTMATCH | fnmatch.CAPTURE)[0][0])
        for name in NAMES:
            if bool(regex.match(name)) != fn_match(name, pattern):
                bad.append((pattern, name))
                break
    assert not bad, bad[:5]


@pytest.mark.parametrize('flags', [0, fnmatch.CAPTURE])
@pytest.mark.parametrize('seed', [8, 9])
def test_inverse_in_group_leaves_no_placeholders(seed, flags):
    """Placeholders used while building a regular expression never end up in the result."""

    rng = random.Random(seed)
    patterns = [p for p in (generate(rng) for _ in range(400)) if '!(' in p][:100]
    for pattern in patterns:
        for variant in (pattern, '@(' + pattern + ')', '+(' + pattern + '|b)c', 'x/' + pattern, pattern + '/y'):
            for translate, flag in ((fnmatch.translate, fnmatch.EXTMATCH), (glob.translate, glob.EXTGLOB)):
                capture = (fnmatch.CAPTURE if translate is fnmatch.translate else glob.CAPTURE) if flags else 0
                for regex in translate(variant, flags=flag | capture)[0]:
                    assert '(?#tail' not in regex, variant
                    re.compile(regex)


@pytest.mark.parametrize('literal', ['\x001\x00', '\\(\\?#tail0\\)', '\x00\\(\\?#tail1\\)\x00'])
def test_inverse_in_group_placeholder_lookalikes(literal):
    """Text in a pattern that looks like a placeholder is just text."""

    pattern = '@(' + literal + '|!(a)b)'
    name = literal.replace('\\', '')

    assert fn_match(name, pattern)
    assert fn_match('xb', pattern)
    assert not fn_match('ab', pattern)


@MATCHERS
@pytest.mark.parametrize('windows', [False, True])
@pytest.mark.parametrize(
    ('pattern', 'matches', 'excludes'),
    [
        ('@(!(a)b)/x', ['xb/x', 'b/x'], ['ab/x']),
        ('x/@(!(a)b)', ['x/xb', 'x/b'], ['x/ab']),
        ('@(x|!(a))/b', ['x/b', 'c/b'], ['a/b']),
        ('@(!(a)b)/@(!(c)d)', ['xb/xd', 'b/d'], ['ab/xd', 'xb/cd']),
    ]
)
def test_inverse_in_group_path_segments(matcher, windows, pattern, matches, excludes):
    """The text that follows an inverse group only counts up to the end of its path segment."""

    flags = glob.FORCEWIN if windows else glob.FORCEUNIX
    sep = '\\' if windows else '/'

    for name in matches:
        assert glob.globmatch(name.replace('/', sep), pattern, flags=glob.EXTGLOB | flags), (pattern, name)
    for name in excludes:
        assert not glob.globmatch(name.replace('/', sep), pattern, flags=glob.EXTGLOB | flags), (pattern, name)


@pytest.mark.parametrize('as_bytes', [False, True])
@pytest.mark.parametrize(
    ('pattern', 'files', 'expected'),
    [
        ('@(!(a)b)', ['ab', 'b', 'xb', 'abb', 'c'], ['abb', 'b', 'xb']),
        ('@(x|!(a))b', ['ab', 'b', 'xb', 'cb', 'c'], ['b', 'cb', 'xb']),
        ('+(!(a)b)c', ['abc', 'bc', 'xbc', 'xbxbc', 'c'], ['bc', 'xbc', 'xbxbc']),
    ]
)
def test_inverse_in_group_glob(tmp_path, as_bytes, pattern, files, expected):
    """A directory scan finds the same names that matching does."""

    for name in files:
        (tmp_path / name).touch()
    root_dir = str(tmp_path)
    if as_bytes:
        pattern, root_dir = pattern.encode(), os.fsencode(root_dir)
        expected = [e.encode() for e in expected]

    assert sorted(glob.glob(pattern, root_dir=root_dir, flags=glob.EXTGLOB)) == expected
