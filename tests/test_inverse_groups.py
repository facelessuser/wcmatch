"""
Test inverse extended groups, `!(...)`.

If the patterns in an inverse group can only match text up to some length, the group matches any other text, whatever
follows it. `!(a)*` matches `a`, as the group can match nothing and `*` can match `a`. This is the case when the
patterns are made of characters, `?`, `[...]`, and groups such as `@(...)` and `?(...)` of those. Inverse groups in the
patterns are fine too: an inverse group matches any text from some length on, so an inverse group around it can only
match shorter text. `!(!(a)|b)` matches `a` and nothing else, even when something follows it. Text that is matched from
some length on cannot be followed by other text in the same pattern though, `!(!(a)b)` is not known.

Patterns that can match text of any length, with `*`, `+(...)`, `*(...)`, or lengths that are not known, must be
translated with what follows them. If the patterns cannot match nothing, the group can match nothing whenever the rest
of the pattern matches, so `!(*.js)*` matches any name that does not start with a dot. Otherwise, an inverse group that
consumes some text is only valid if the rest of the pattern can match what is left, and if none of the ways the rest
could match would make the consumed text match one of the group's own patterns. The rest of the pattern includes what
follows the group inside its slot, and what follows the enclosing group.

Inside `+(...)` and `*(...)` groups, the rest only includes the remainder of the group's slot and whatever follows the
loop, it does not consider further iterations. Each iteration is judged as though it were the last one. This means
`+(!(a*b))` does not match `axb`, even though `ax` and `b` each match `!(a*b)`.

An inverse group inside the patterns of another inverse group follows the same rules, and its patterns are matched
against the text it consumes, which has to end where the text consumed by the outer group ends. This is exact when what
follows the outer group has a fixed length, as only one place is left for it to end. Such a group does not get to match
nothing just because the rest matches, as that could make the patterns of the outer group match nothing too.

The reference model below implements these rules directly with a simple backtracking matcher. It is used to check
that the regular expressions produced by the parser follow them.
"""
import itertools
import os
import random
import re

import pytest

from wcmatch import _wcparse, fnmatch, glob


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


def lengths(alts):
    """
    Get what lengths of text the patterns can match.

    This is 'empty' if the patterns only match empty text, 'bounded' if there is a longest text they can match, 'open'
    if they match any text from some length on, and `None` if it is not known.
    """

    kinds = [sequence_lengths(alt) for alt in alts]
    if None in kinds:
        return None
    if 'open' in kinds:
        return 'open'
    return 'bounded' if 'bounded' in kinds else 'empty'


def sequence_lengths(nodes):
    """Get what lengths of text a sequence of nodes can match."""

    result = 'empty'
    for node in nodes:
        kind = node_lengths(node)
        if kind is None:
            return None
        if result == 'empty':
            result = kind
        elif kind != 'empty':
            # Text matched from some length on, next to other text, has lengths we cannot list
            if result == 'open' or kind == 'open':
                return None
    return result


def node_lengths(node):
    """Get what lengths of text a node can match."""

    if node[0] in ('lit', '?'):
        return 'bounded'
    if node[0] == '*':
        return None
    kind = lengths(node[2] + ([[]] if node[0] == 'grp' and node[1] == '?' else []))
    if node[0] == 'inv':
        # What the patterns do not match
        return None if kind is None else 'bounded' if kind == 'open' else 'open'
    return kind if node[1] in '@?' else None


def matches_nothing(alts):
    """Check if patterns of known lengths can match nothing."""

    return any(all(node_matches_nothing(node) for node in alt) for alt in alts)


def node_matches_nothing(node):
    """Check if a node of known lengths can match nothing."""

    if node[0] in ('lit', '?'):
        return False
    if node[0] == '*':
        return True
    if node[0] == 'inv':
        return not matches_nothing(node[2])
    return node[1] in '?*' or matches_nothing(node[2])


def is_non_empty(node):
    """Check if a node always matches at least a character, as far as the parser can tell."""

    if node[0] in ('lit', '?'):
        return True
    if node[0] == '*':
        return False
    if node[0] == 'inv':
        # An inverse group of known lengths can only match nothing if its patterns do not
        return lengths(node[2]) is not None and matches_nothing(node[2])
    return node[1] in '@+' and not maybe_empty(node[2])


def maybe_empty(alts):
    """Check if the patterns may match nothing, which is when one has no piece that always matches a character."""

    return any(not any(is_non_empty(node) for node in alt) for alt in alts)


def model_match(nodes, name):
    """Match with the reference model."""

    end = len(name)

    def seq(items, pos, k, kl, inv):
        """
        Match a sequence of nodes at `pos`, then call the continuation `k`.

        Inverse groups use `kl` to find the places where the rest of the pattern can match. It is the same as `k`,
        except in loops, where it skips any further iterations. `inv` is set inside inverse groups.
        """

        if not items:
            return k(pos)
        node, rest = items[0], items[1:]

        def cont(q):
            return seq(rest, q, k, kl, inv)

        kind = node[0]
        if kind == 'lit':
            return pos < end and name[pos] == node[1] and cont(pos + 1)
        if kind == '?':
            return pos < end and cont(pos + 1)
        if kind == '*':
            return any(cont(e) for e in range(pos, end + 1))

        alts = node[2]

        def alts_match(start, k2, kl2, inv2=inv):
            return any(seq(a, start, k2, kl2, inv2) for a in alts)

        if kind == 'grp':
            t = node[1]

            def here(q):
                """The rest after this group, up to the local end."""

                return cont(q) if kl is k else seq(rest, q, kl, kl, inv)

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

        def ends_at(e):
            return lambda q: q == e

        if lengths(alts) is not None:
            # Patterns of known lengths: the group can match any text that they do not match
            return any(cont(e) and not alts_match(pos, ends_at(e), ends_at(e), True) for e in range(pos, end + 1))

        if not inv and not maybe_empty(alts):
            # The patterns cannot match nothing, so the group can if the rest of the pattern matches
            if cont(pos) and (kl is k or seq(rest, pos, kl, kl, inv)):
                return True

        # Otherwise none of the places where the rest can match may end a match of the group's patterns
        real_ends = [e for e in range(pos, end + 1) if cont(e)]
        local_ends = real_ends if kl is k else [e for e in range(pos, end + 1) if seq(rest, e, kl, kl, inv)]
        return bool(real_ends) and not any(alts_match(pos, ends_at(e), ends_at(e), True) for e in local_ends)

    def top(q):
        return q == end

    return seq(nodes, 0, top, top, False)


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
    # Patterns that can only match text of a limited length: the group matches any other text, whatever follows it
    ('!(a)', ['b', 'ab', 'aa'], ['a']),
    ('!(a)b', ['xb', 'b', 'abb'], ['ab']),
    ('!(a)*', ['a', 'ab', 'b', 'xa'], []),
    ('!(foo)*.txt', ['foo.txt', 'foobar.txt', 'bar.txt'], ['foo.js']),
    ('!(foo).txt', ['x.txt', 'foox.txt'], ['foo.txt']),
    ('!(a|bc)*', ['a', 'bc', 'b', 'x'], []),
    ('!(a|)*', ['x', 'ab'], ['a']),
    ('!(?(a))*', ['b', 'aab'], ['a']),
    ('!(?(a))', ['aa', 'b'], ['a']),
    ('!(?(a)b)*', ['b', 'ab', 'x', 'abb'], []),
    ('!(@(a|bc)d)*', ['ad', 'bcd', 'x', 'bd'], []),
    ('!(a?)*', ['ab', 'a', 'x'], []),
    ('!()', ['a'], []),
    ('@(!(a)b)', ['b', 'xb', 'abb'], ['ab', 'a']),
    ('@(!(a)*)', ['a', 'ab', 'b', 'xa'], []),
    ('@(!(a)b|c)d', ['bd', 'xbd', 'cd'], ['abd', 'ab']),
    ('@(!(ab)?)c', ['xyc', 'ac', 'abc'], ['abxc']),
    ('@(x|!(a))b', ['b', 'xb', 'cb', 'aab'], ['ab']),
    ('?(!(a))b', ['b', 'cb'], ['ab']),
    ('@(!(a)*)c', ['abc', 'bc', 'xac', 'c'], ['ab']),
    ('@(!(a)b)@(!(c)d)', ['xbxd', 'bd'], ['abxd', 'bcd', 'xbcd']),
    ('@(!(a|b)+(c))d', ['cd', 'ccd', 'accd', 'bccd'], ['acd', 'ad']),
    # Brackets, escapes, and character classes are a character each
    ('!([ab])*', ['a', 'ab', 'b', 'c', 'x1'], []),
    ('!([ab])', ['ab', 'c', 'x1'], ['a', 'b']),
    (r'!(\*)', ['**', 'a', 'x1'], ['*']),
    (r'!(a\.b)', ['a.bc', 'a', '*'], ['a.b']),
    ('!(a.b)*', ['a', 'a.b', 'a.bc'], []),
    ('!([[:digit:]])', ['12', 'a', 'x1'], ['1']),
    ('!([[:digit:]])*', ['1', '12', 'a'], []),
    ('!(?)', ['ab', '12', 'x1', '**'], ['a', '1', '*']),
    # A bracket that is never closed is a character too
    ('!([)', ['a', 'ab', 'b['], ['[']),
    ('!(a[)', ['a', 'ab', '['], ['a[']),
    # Groups that are merged into their parent keep the same meaning
    ('@(a|@(!(b)c))d', ['xcd', 'ad', 'cd'], ['bcd']),
    ('@(@(!(a)b))', ['xb', 'b'], ['ab']),
    ('@(a|@(!(b)c|d))e', ['xce', 'de', 'ae', 'ce'], ['bce', 'e', 'bde']),
    ('?(a|@(!(b)c|d))e', ['xce', 'de', 'ae', 'e'], ['bce']),
    ('+(a|@(!(b)c|d))e', ['xce', 'de', 'ade', 'ae'], ['bce']),
    ('@(@(!(b)c|d)|a)e', ['xce', 'de', 'ae'], ['bce']),
    # Repeating names that match, matches
    ('+(!(foo))', ['foo', 'foobar', 'f'], []),
    ('*(!(foo))', ['foo', 'bar'], []),
    ('+(!(ba))', ['ba', 'a', 'bab'], []),
    ('*(!(ab)|x)', ['ab', 'aab', 'x'], []),
    ('+(!(foo)|x)', ['foo', 'xfoo', 'xx'], []),
    ('+(!(a))', ['ab', 'b', 'aa'], ['a']),
    ('*(!(a)|b)', ['ab', 'b'], ['a']),
    ('+(!(a)b)c', ['xbc', 'xbxbc', 'bc'], ['abc']),
    # Patterns that can match text of any length: the rest of the pattern is part of what makes the text match
    ('!(a*)b', ['b', 'cb'], ['ab', 'abb']),
    ('!(a*)*b', ['ab', 'abb', 'axb', 'b', 'cb'], ['a', 'ba', 'bc']),
    ('!(a*)b*', ['b', 'bx', 'cb', 'xb'], ['a', 'ab', 'abb', 'c', 'x']),
    ('!(a*|b*)c*', ['c', 'cb', 'cc'], ['a', 'b', 'ab', 'bc', 'x']),
    ('!(+(a)*)b*', ['b', 'ba', 'cb'], ['a', 'ab', 'c']),
    # Patterns that cannot match nothing leave the group free to match nothing, if the rest of the pattern matches
    ('!(*.js)*', ['x', 'a.js', 'a.json', 'a.js.js'], []),
    ('!(*a)*', ['bb', 'a', 'ba', 'xab'], []),
    ('!(a*)*', ['a', 'ab', 'b'], []),
    ('@(!(a*)*|x)', ['a', 'ab', 'x'], []),
    ('!(@(a*))*', ['a', 'ab', 'b'], []),
    ('!(@(a*)|b+(c))*', ['a', 'bc', 'b'], []),
    ('@(!(a*)b)', ['b', 'xb'], ['ab']),
    ('@(x|!(a*))b', ['b', 'xb'], ['ab', 'aab']),
    # Inside loops, each iteration is judged as though it were the last
    ('+(!(a*))', ['ba'], ['ab', 'a']),
    ('+(!(a*b))', ['ax', 'b', 'xaxb'], ['axb']),
    ('*(!(a*)|b)', ['ba', 'b'], ['ab']),
    ('+(!(a*)b)c', ['xbc', 'xbxbc'], ['abc']),
    ('+(!(a*)b)', ['b', 'bb', 'cb', 'xb'], ['ab', 'a', 'ba']),
    ('@(!(a*)b|x)*', ['b', 'x', 'xb', 'bx'], ['a', 'ab', 'c']),
    # Inverse groups inside inverse groups
    ('!(!(a))', ['a'], ['aa', 'b', 'ab']),
    ('!(!(a)|b)', ['a'], ['aa', 'ab', 'b', 'c']),
    ('!(a!(b))', ['ab', 'b', 'ba'], ['a', 'aa', 'aba', 'abb']),
    ('!(!(a)b)', ['ab', 'a', 'c'], ['b', 'xb', 'abb']),
    ('!(a!(b)c)', ['abc', 'xac', 'a'], ['ac', 'abac']),
    ('!(a!(b)c)d', ['abcd', 'ad', 'xacd'], ['acd']),
    ('!(x|!(a)b)c', ['abc', 'c', 'yc'], ['xc', 'bc', 'aabc']),
    ('@(a|!(b!(c)))d', ['bcd', 'ad', 'xd'], ['bd', 'bxd']),
    # An inverse group matches any text from some length on, so an inverse group around it can only match shorter text
    ('!(!(a)|b)*', ['a', 'ab', 'aa'], ['b', 'ba', 'x']),
    ('!(!(a)|b)c', ['ac'], ['c', 'bc', 'aac', 'xc']),
    ('!(!(a)*)', [], ['a', 'ab', 'b', 'c']),
    ('!(?(!(a)))', ['a'], ['b', 'aa', 'ab']),
    ('!(!(!(a)))', ['b', 'ab', 'aa'], ['a']),
    ('!(a|b!(c)*)', ['c', 'aa', 'ab', 'ca'], ['a', 'b', 'bc', 'bca']),
    # What an inverse group inside another one can match does not depend on what follows the outer group
    ('!(a!(b)*)', ['b', 'xa', 'ba'], ['a', 'ab', 'aab']),
    ('!(a!(b)*)c', ['bc', 'xac'], ['ac', 'abc']),
    ('!(!(a)c*)', ['ab', 'a', 'b', 'ac'], ['c', 'acc', 'bc', 'cc']),
    ('!(!(a)*b)', ['a', 'c', 'ba'], ['b', 'ab', 'cb']),
    # An inverse group next to a group that matches nothing is still an inverse group
    ('!(!(a)@())', ['a'], ['b', 'aa', 'ab']),
    ('!(!(a)?())', ['a'], ['b', 'aa', 'ab']),
    ('!(!(a)@()|b)*', ['a', 'aa', 'ab'], ['b', 'c', 'ba']),
    # If the patterns match every text, the group cannot match any, and if they match only nothing, it matches nothing
    ('!(!()|?(a))', [], ['a', 'b', 'ab']),
    ('!(!())', [], ['a', 'ab']),
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


@MATCHERS
@pytest.mark.parametrize('dotmatch', [False, True])
@pytest.mark.parametrize(
    ('pattern', 'hidden', 'visible'),
    [
        ('!(a)*', '.x', 'x'),
        ('!(.hid)*', '.hid', 'x'),
        ('@(!(a)b)', '.b', 'xb'),
    ]
)
def test_inverse_exact_dotmatch(matcher, dotmatch, pattern, hidden, visible):
    """Names that start with a dot still need `DOTMATCH` unless they are matched with a literal dot."""

    flags = fnmatch.DOTMATCH if dotmatch else 0

    assert matcher(visible, pattern, flags=flags)
    assert matcher(hidden, pattern, flags=flags) is dotmatch


@MATCHERS
def test_inverse_exact_dot_in_patterns(matcher):
    """A literal dot is matched by the patterns, but a hidden name still needs `DOTMATCH`."""

    assert not matcher('.hid', '!(.hid)')
    assert matcher('.a', '!(.hid)', flags=fnmatch.DOTMATCH)
    assert not matcher('.hid', '!(.hid)', flags=fnmatch.DOTMATCH)
    assert matcher('.b', '!(a)', flags=fnmatch.DOTMATCH)
    assert not matcher('.b', '!(a)')


DOT_NAMES = ['x', 'b', 'a.js', 'a.json', '.env', '.js', '.a.js', '.x.txt', 'b.txt', 'ab']
HIDDEN_FREE = ['x', 'b', 'a.js', 'a.json', 'b.txt', 'ab']

# What Bash matches without and with `dotglob`. A group that matches nothing is still at the start of a name.
DOT_CASES = [
    ('!(*.js)*', HIDDEN_FREE, DOT_NAMES),
    ('!(a*)*', HIDDEN_FREE, DOT_NAMES),
    ('!(*.js).*', ['a.js', 'a.json', 'b.txt'], ['a.js', 'a.json', '.env', '.js', '.a.js', '.x.txt', 'b.txt']),
    ('!(*.js)*.txt', ['b.txt'], ['.x.txt', 'b.txt']),
    ('!(a*)b*', ['b', 'b.txt'], ['b', 'b.txt']),
    ('@(!(*.js)*|x)', HIDDEN_FREE, DOT_NAMES),
    ('+(!(*.js)*)', HIDDEN_FREE, DOT_NAMES),
    ('*(!(*.js)*)', HIDDEN_FREE, DOT_NAMES),
    ('?(!(*.js)*)', HIDDEN_FREE, DOT_NAMES),
    ('@(a|!(*.js)*)', HIDDEN_FREE, DOT_NAMES),
    ('!(*.js)@(*)', HIDDEN_FREE, DOT_NAMES),
    ('@(!(a*)*)@(*)', HIDDEN_FREE, DOT_NAMES),
    ('!(a*)@(.js|*)', HIDDEN_FREE, DOT_NAMES),
]


@MATCHERS
@pytest.mark.parametrize(('pattern', 'default', 'dotmatch'), DOT_CASES)
def test_inverse_dot_handling(matcher, pattern, default, dotmatch):
    """A leading dot needs `DOTMATCH`, even if an inverse group matches nothing or is followed by a wildcard."""

    for wrap in ('{}', '@({})'):
        for flags, expected in ((0, default), (fnmatch.DOTMATCH, dotmatch)):
            names = [name for name in DOT_NAMES if matcher(name, wrap.format(pattern), flags=flags)]
            assert names == expected, (wrap.format(pattern), flags)


@pytest.mark.parametrize(('pattern', 'default', 'dotmatch'), DOT_CASES)
def test_inverse_dot_handling_capture(pattern, default, dotmatch):
    """The capture flag does not change which names are hidden."""

    for flags, expected in ((0, default), (fnmatch.DOTMATCH, dotmatch)):
        regex = re.compile(fnmatch.translate(pattern, flags=fnmatch.EXTMATCH | fnmatch.CAPTURE | flags)[0][0])
        assert [name for name in DOT_NAMES if regex.match(name)] == expected, (pattern, flags)


@pytest.mark.parametrize('as_bytes', [False, True])
def test_inverse_dot_handling_bytes(as_bytes):
    """Bytes and strings hide the same names."""

    pattern = '!(*.js)*'
    names = DOT_NAMES
    expected = HIDDEN_FREE
    if as_bytes:
        pattern, names, expected = pattern.encode(), [n.encode() for n in names], [n.encode() for n in expected]

    flags = fnmatch.EXTMATCH | fnmatch.FORCEUNIX
    assert [n for n in names if fnmatch.fnmatch(n, pattern, flags=flags)] == expected


PATH_NAMES = ['.d', '.d/.env', '.d/x', '.env', 'a.js', 'd', 'd/.env', 'd/.env.txt', 'd/a.js', 'd/b.txt', 'd/x', 'x']
VISIBLE = ['d/a.js', 'd/b.txt', 'd/x']
EVERY_D = ['.d/.env', '.d/x', 'd/.env', 'd/.env.txt', 'd/a.js', 'd/b.txt', 'd/x']
RECURSIVE = ['a.js', 'd', 'd/a.js', 'd/b.txt', 'd/x', 'x']
EVERYWHERE = [
    '.d', '.d/.env', '.d/x', '.env', 'a.js', 'd', 'd/.env', 'd/.env.txt', 'd/a.js', 'd/b.txt', 'd/x', 'x'
]

# What Bash matches in this tree without and with `dotglob`, every segment follows the same rules
BASH_DOT_NAMES = ['.a', '.b', '..b', '.ab', '.bb', 'a', 'b', 'ab', 'a.b', 'xb']

# What Bash 5.3 expands these patterns to in a directory holding `BASH_DOT_NAMES`, without `dotglob`.
# A group that has an alternative that starts with a dot, directly or through a group that starts it, lets a `*` that
# ends its alternative, or any other part that can match nothing, match nothing so a dot after the group is the leading
# dot. A wildcard never matches the leading dot itself, and a `*` followed by more of its alternative cannot match
# nothing.
BASH_DOT_CASES = [
    ('@(*|.a).b', ['.b', 'a.b']),
    ('?(x)@(*|.a).b', ['.b', 'a.b']),
    ('+(*|.a).b', ['.b', 'a.b']),
    ('*(*|.a).b', ['.b', 'a.b']),
    ('@(*|@(.a|x)).b', ['.b', 'a.b']),
    ('@(*|x@(.a)).b', ['a.b']),
    ('@(|.a).b', ['.b']),
    ('@(*?(x)|.a).b', ['.b', 'a.b']),
    ('@(?(x)*|.a).b', ['.b', 'a.b']),
    ('@(*|.a)b', ['.ab', 'b', 'ab', 'a.b', 'xb']),
    ('@(*.|.a)b', ['.ab', 'a.b']),
    ('@(*.b|.a)', ['.a', 'a.b']),
    ('@(*|.a)*', ['.a', '.ab', 'a', 'b', 'ab', 'a.b', 'xb']),
    ('@(*|x).b', ['a.b']),
    ('@(*).b', ['a.b']),
    ('+(*).b', ['a.b']),
    ('?(*).b', ['.b', 'a.b']),
    ('*(*).b', ['.b', 'a.b']),
    ('?(x).b', ['.b']),
    ('*(*.a)', []),
    ('?(*.a)', []),
    ('*(*.b*(.a*|b))', ['a.b']),
    ('?(x)@(.b|*)b', ['.bb', 'b', 'ab', 'a.b', 'xb']),
    ('*(*)', ['a', 'b', 'ab', 'a.b', 'xb']),
    ('?(*)', ['a', 'b', 'ab', 'a.b', 'xb']),
    ('*(*a)', ['a']),
    ('@(.)b', ['.b']),
    ('?(.)b', ['.b', 'b']),
    ('@(a|.)b', ['.b', 'ab']),
    ('*(a|.)b', ['.b', '..b', '.ab', 'b', 'ab', 'a.b']),
    ('+(a|.)b', ['.b', '..b', '.ab', 'ab', 'a.b']),
    ('!(*|.a).b', []),
    ('@(*|!(.a)).b', ['.b', 'a.b']),
    ('@(!(x)|.a).b', ['a.b']),
]


@pytest.mark.parametrize(('pattern', 'expected'), BASH_DOT_CASES)
def test_dot_in_groups_follows_bash(pattern, expected):
    """A dot at the start of an alternative lets wildcards in the group match nothing before the dot."""

    assert [n for n in BASH_DOT_NAMES if fn_match(n, pattern)] == expected, pattern
    assert [n for n in BASH_DOT_NAMES if glob_match(n, pattern)] == expected, pattern


PATH_CASES = [
    ('!(*.js)*', ['a.js', 'd', 'x'], ['.d', '.env', 'a.js', 'd', 'x']),
    ('d/!(*.js)*', VISIBLE, ['d/.env', 'd/.env.txt', 'd/a.js', 'd/b.txt', 'd/x']),
    ('!(*.js)*/x', ['d/x'], ['.d/x', 'd/x']),
    ('!(*.js)/*', VISIBLE, EVERY_D),
    ('*/!(*.js)*', VISIBLE, EVERY_D),
    ('!(*.js)*/!(*.js)*', VISIBLE, EVERY_D),
    ('d/!(*.js)*.txt', ['d/b.txt'], ['d/.env.txt', 'd/b.txt']),
    ('d/!(a*)*', VISIBLE, ['d/.env', 'd/.env.txt', 'd/a.js', 'd/b.txt', 'd/x']),
    ('.d/!(*.js)*', ['.d/x'], ['.d/.env', '.d/x']),
    ('**/!(*.js)*', RECURSIVE, EVERYWHERE),
    ('**/!(a*)*', RECURSIVE, EVERYWHERE),
    ('**/d/!(*.js)*', VISIBLE, ['d/.env', 'd/.env.txt', 'd/a.js', 'd/b.txt', 'd/x']),
    ('@(!(*.js)*)/x', ['d/x'], ['.d/x', 'd/x']),
    ('+(!(*.js)*)/*', VISIBLE, EVERY_D),
    ('!(*.js)@(*)/x', ['d/x'], ['.d/x', 'd/x']),
]


@pytest.mark.parametrize(('pattern', 'default', 'dotglob'), PATH_CASES)
def test_inverse_dot_handling_paths(pattern, default, dotglob):
    """Every segment of a path hides names that start with a dot, including a segment that matches nothing."""

    flags = glob.EXTGLOB | glob.GLOBSTAR | glob.FORCEUNIX
    assert [p for p in PATH_NAMES if glob.globmatch(p, pattern, flags=flags)] == default, pattern
    assert [p for p in PATH_NAMES if glob.globmatch(p, pattern, flags=flags | glob.DOTGLOB)] == dotglob, pattern


@pytest.mark.parametrize(('pattern', 'default', 'dotglob'), PATH_CASES)
def test_inverse_dot_handling_file_system(tmp_path, pattern, default, dotglob):
    """Walking the file system hides the same names as matching paths."""

    for name in ('x', 'a.js', '.env', 'd/x', 'd/.env', 'd/a.js', 'd/.env.txt', 'd/b.txt', '.d/x', '.d/.env'):
        path = tmp_path / name
        path.parent.mkdir(exist_ok=True)
        path.touch()

    def scan(flags):
        # Windows reports paths with backslashes
        return sorted(p.replace('\\', '/') for p in glob.glob(pattern, flags=flags, root_dir=tmp_path))

    flags = glob.EXTGLOB | glob.GLOBSTAR
    assert scan(flags) == default, pattern
    assert scan(flags | glob.DOTGLOB) == dotglob, pattern


DOT_ALPHABET = [''.join(p) for n in range(1, 4) for p in itertools.product('ab.', repeat=n) if set(p) != {'.'}]


@pytest.mark.parametrize('seed', [20, 21])
def test_inverse_dot_handling_model(seed):
    """
    Only a leading dot is special when the patterns have no dot, so names are matched like the model, less hidden names.

    With `DOTMATCH` the dot is like any other character. This includes the capture flag and names in a directory.
    """

    patterns = list(generate_patterns(seed, 40)) + list(generate_patterns(seed, 40, frozenset({'in loop'})))
    patterns += list(generate_nested_patterns(seed, 40))

    bad = []
    for pattern in patterns:
        nodes = parse(pattern)[0]
        plain = re.compile(fnmatch.translate(pattern, flags=fnmatch.EXTMATCH | fnmatch.CAPTURE)[0][0])
        dotted = re.compile(
            fnmatch.translate(pattern, flags=fnmatch.EXTMATCH | fnmatch.CAPTURE | fnmatch.DOTMATCH)[0][0]
        )
        for name in DOT_ALPHABET:
            matches = model_match(nodes, name)
            expected = matches and not name.startswith('.')
            results = (
                fn_match(name, pattern) is expected,
                glob_match('x/' + name, 'x/' + pattern) is expected,
                bool(plain.match(name)) is expected,
                fn_match(name, pattern, flags=fnmatch.DOTMATCH) is matches,
                glob_match('x/' + name, 'x/' + pattern, flags=fnmatch.DOTMATCH) is matches,
                bool(dotted.match(name)) is matches,
            )
            if not all(results):
                bad.append((pattern, name, results))
                break
    assert not bad, bad[:5]


@pytest.mark.parametrize('seed', [30, 31])
def test_inverse_never_matches_hidden_names(seed):
    """Patterns without a dot never match a name that starts with one, without `DOTMATCH`."""

    rng = random.Random(seed)
    count = 0
    while count < 150:
        pattern = generate(rng)
        if '!(' not in pattern:
            continue
        count += 1
        for name in ('.a', '.ab', '.abc', '.b', '.'):
            assert not fn_match(name, pattern), (pattern, name)
            assert not glob_match(name, pattern), (pattern, name)
            assert not glob_match('x/' + name, 'x/' + pattern), (pattern, name)


@MATCHERS
def test_inverse_exact_many_optional_parts_in_alternatives(matcher):
    """Alternatives that can each be tracked, but are too long to track together, still work."""

    first = ''.join('?({})'.format(c) for c in 'abcdefghi')
    second = ''.join('?({})'.format(c) for c in 'mnopqrstu')
    flags = fnmatch.EXTMATCH
    alone = fnmatch.translate('!(' + first + ')', flags=flags)[0][0]
    pattern = '!(' + first + '|' + second + ')'
    together = fnmatch.translate(pattern, flags=flags)[0][0]

    # Each is tracked by length, but the lengths of both together take too much room
    assert len(alone) > 3000
    assert len(together) < 1000
    assert not matcher('', pattern)
    assert not matcher('a', pattern)
    assert not matcher('abcdefghi', pattern)
    assert not matcher('mnu', pattern)
    assert matcher('ca', pattern)
    assert matcher('x', pattern)
    assert matcher('abcdefghij', pattern)


START = r'^(?s:(?!(?:(?<=[/])|(?<=^))(?:\.{1,2})(?:$|[/]))'

# The lengths of text that groups match are only kept for inverse groups, other groups translate the same without them
UNTRACKED = [
    ('@(foo|bar)*.txt', r'(?!(?<=^)\.)(?:foo|bar)(?!(?<=^)\.).*?\.txt', r'(?!(?<=^)\.)(foo|bar)(?!(?<=^)\.).*?\.txt'),
    ('?(a)b', r'(?:(?!(?<=^)\.)(?:a))?b', r'((?:(?!(?<=^)\.)(?:a))?)b'),
    ('+(a|b)c', r'(?!(?<=^)\.)(?:a|b)+c', r'((?!(?<=^)\.)(?:a|b)+)c'),
    ('*(x|y)z', r'(?:(?!(?<=^)\.)(?:x|y))*z', r'((?:(?!(?<=^)\.)(?:x|y))*)z'),
    ('@(a|?(b))*', r'(?!(?<=^)\.)(?:a|b|)(?!(?<=^)\.).*?', r'(?!(?<=^)\.)(a|((?:b)?))(?!(?<=^)\.).*?'),
    ('+(?(a)b)', r'(?!(?<=^)\.)(?:(?:a)?b)+', r'((?!(?<=^)\.)(?:((?:a)?)b)+)'),
    ('@(a|@(b|c))d', r'(?!(?<=^)\.)(?:a|b|c)d', r'(?!(?<=^)\.)(a|(b|c))d'),
]


@pytest.mark.parametrize(('pattern', 'regex', 'capture_regex'), UNTRACKED)
def test_groups_without_inverse_groups_translate_the_same(pattern, regex, capture_regex):
    """Groups that are not in an inverse group do not change because lengths are tracked for inverse groups."""

    flags = fnmatch.EXTMATCH | fnmatch.FORCEUNIX
    assert fnmatch.translate(pattern, flags=flags)[0][0] == START + regex + ')$'
    assert fnmatch.translate(pattern, flags=flags | fnmatch.CAPTURE)[0][0] == START + capture_regex + ')$'


@pytest.mark.parametrize(
    ('pattern', 'tracked'),
    [
        ('@(foo|bar)*.txt', 0),
        ('+(a|b)c?(d)', 0),
        ('?(a)@(b|?(c))+(?(d)e)', 0),
        ('!(a)', 1),
        ('@(!(a)bc)', 1),
        ('!(a?(b))', 2),
        ('!(a)@(b|c)!(d)', 2),
    ]
)
def test_lengths_are_only_tracked_in_inverse_groups(monkeypatch, pattern, tracked):
    """Only inverse groups, and the pieces they are made of, have their lengths worked out."""

    sized = []
    groups = []
    original_sized = _wcparse.Sized
    original_lengths = _wcparse.WcParse._group_lengths

    def spy_sized(value):
        sized.append(value)
        return original_sized(value)

    def spy_lengths(extended):
        groups.append(extended)
        return original_lengths(extended)

    monkeypatch.setattr(_wcparse, 'Sized', spy_sized)
    monkeypatch.setattr(_wcparse.WcParse, '_group_lengths', staticmethod(spy_lengths))
    _wcparse.WcParse(pattern, _wcparse.EXTMATCH).parse()

    # Each inverse group works out its lengths, and nothing outside of one does
    assert len(groups) == tracked
    assert (not sized) is (pattern.count('!(') == 0)
    if pattern == '@(!(a)bc)':
        assert sized == ['a']


def test_inverse_exact_many_optional_parts():
    """Patterns that are too long to track the lengths of still work, and do not grow without bound."""

    letters = 'abcdefghij'
    pattern = '!(' + ''.join('?({})'.format(c) for c in letters) + ')'
    regex = fnmatch.translate(pattern, flags=fnmatch.EXTMATCH)[0][0]

    assert len(regex) < 1000
    assert fn_match('ca', pattern)
    assert fn_match('x', pattern)
    assert fn_match(letters + 'k', pattern)
    assert not fn_match('ac', pattern)
    assert not fn_match(letters, pattern)


@MATCHERS
def test_inverse_exact_group_too_large(matcher):
    """Patterns whose lengths can be tracked, but not the lengths of the group around them, still work."""

    pattern = '!(?(aa)?(b)?(c)?(d)?(e)?(f)?(gg)?(hh)?(i))'
    regex = fnmatch.translate(pattern, flags=fnmatch.EXTMATCH)[0][0]

    assert len(regex) < 1000
    assert matcher('a', pattern)
    assert matcher('ba', pattern)
    assert matcher('x', pattern)
    assert not matcher('', pattern)
    assert not matcher('aab', pattern)
    assert not matcher('aabcdefgghhi', pattern)


@pytest.mark.parametrize(
    ('pattern', 'name', 'groups'),
    [
        ('a!(b)c', 'axyc', ('xy',)),
        ('a!(b)c', 'ac', ('',)),
        ('!(a)*', 'ab', ('',)),
        ('x!(?(a))y', 'xaby', ('ab', None)),
        ('@(!(a|b)+(c))d', 'xccd', ('xcc', 'x', 'cc')),
        ('!(a|bc)@(d)', 'xyd', ('xy', 'd')),
        ('+(!(a)b)', 'xbyb', ('xbyb', 'y')),
        ('!(!(a)|b)*', 'abc', ('a', None)),
        ('!(?(!(a)))', 'a', ('a', None, None)),
        ('@(!(!(a)))b', 'ab', ('a', 'a', None)),
    ]
)
def test_inverse_exact_capture(pattern, name, groups):
    """Extended groups are capturing groups in the order of the pattern, and an inverse group captures its text."""

    regex = re.compile(fnmatch.translate(pattern, flags=fnmatch.EXTMATCH | fnmatch.CAPTURE)[0][0])

    assert regex.match(name).groups() == groups


@pytest.mark.parametrize('seed', [16, 17])
def test_inverse_exact_capture_groups_in_order(seed):
    """Random patterns get one capturing group for each extended group, whether or not the lengths are tracked."""

    rng = random.Random(seed)
    count = 0
    while count < 150:
        pattern = generate(rng)
        if '!(' not in pattern:
            continue
        count += 1
        groups = sum(1 for i in range(len(pattern) - 1) if pattern[i] in '@?*+!' and pattern[i + 1] == '(')
        regex = fnmatch.translate(pattern, flags=fnmatch.EXTMATCH | fnmatch.CAPTURE)[0][0]
        assert re.compile(regex).groups == groups, pattern


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
        ('!(a)*/x', ['a/x', 'ab/x', 'b/x'], ['a/b/x', 'a/y']),
        ('!(a)/x', ['b/x', 'ab/x'], ['a/x']),
        ('!(a)/@(!(b)*)', ['b/a', 'x/b', 'x/y'], ['a/b']),
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
