"""Equal compiled matchers share dictionary and set entries."""

import re

import pytest

from wcmatch import _wcmatch, fnmatch, glob


class DerivedRegexp(_wcmatch.WcRegexp):
    """A regular-expression matcher inheriting value equality."""


class PatternTuple(tuple):
    """A tuple subtype with the same element-wise equality."""


def assert_shared_key(original, equivalent):
    """Check equality through real dictionary and set operations."""

    assert original == equivalent
    assert equivalent == original
    assert {original: 'cached'}[equivalent] == 'cached'
    assert hash(original) == hash(equivalent)
    assert len({original, equivalent}) == 1


@pytest.mark.parametrize('binary', [False, True])
@pytest.mark.parametrize('variant', ['subclass', 'include-tuple', 'exclude-tuple'])
def test_regexp_hash_matches_equality(binary, variant):
    """Equal regexp values remain interchangeable across supported subtypes."""

    include = (re.compile(b'keep.*' if binary else 'keep.*'),)
    exclude = (re.compile(b'skip.*' if binary else 'skip.*'),)
    original = _wcmatch.WcRegexp(include, exclude)
    if variant == 'subclass':
        equivalent = DerivedRegexp(include, exclude)
    elif variant == 'include-tuple':
        equivalent = _wcmatch.WcRegexp(PatternTuple(include), exclude)
    else:
        equivalent = _wcmatch.WcRegexp(include, PatternTuple(exclude))

    assert_shared_key(original, equivalent)


@pytest.mark.parametrize('wrapper', [fnmatch.WcMatcher, glob.WcMatcher])
@pytest.mark.parametrize('regexp_class', [_wcmatch.WcRegexp, DerivedRegexp])
def test_wrapper_hash_matches_inherited_equality(wrapper, regexp_class):
    """Equal public matcher subclasses can retrieve existing cache entries."""

    class DerivedMatcher(wrapper):
        """A public matcher subtype inheriting the matching behavior."""

    patterns = (re.compile(r'keep.*'),)
    original = wrapper(_wcmatch.WcRegexp(patterns))
    equivalent = DerivedMatcher(regexp_class(patterns))
    assert original.match('keep.txt')
    assert equivalent.match('keep.txt')
    assert_shared_key(original, equivalent)
