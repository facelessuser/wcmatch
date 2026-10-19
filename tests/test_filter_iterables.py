"""Filename filtering accepts iterables without a truth value."""
import pytest
from wcmatch import fnmatch, glob


class NoTruthIterable:
    """Model collections such as NumPy arrays without importing NumPy."""

    def __init__(self, names):
        """Store the filenames to iterate over."""

        self.names = names

    def __iter__(self):
        """Iterate over filenames without testing the collection's truth value."""

        return iter(self.names)

    def __bool__(self):
        """Reject truth testing, as array collections do."""

        raise ValueError('The truth value of this collection is ambiguous')


@pytest.mark.parametrize('module', [fnmatch, glob], ids=['fnmatch', 'glob'])
@pytest.mark.parametrize('precompiled', [False, True], ids=['direct', 'compiled'])
@pytest.mark.parametrize('names, expected', [
    ([], []),
    (['keep.txt', 'skip.txt', 'readme.md'], ['keep.txt'])
], ids=['empty', 'nonempty'])
def test_filter_iterable_without_truth_value(module, precompiled, names, expected):
    """Filter names and exclusions using iteration alone."""

    values = NoTruthIterable(names)
    if precompiled:
        actual = module.compile('*.txt', exclude='skip.txt').filter(values)
    elif module is fnmatch:
        actual = fnmatch.filter(values, '*.txt', exclude='skip.txt')
    else:
        actual = glob.globfilter(values, '*.txt', exclude='skip.txt')
    assert actual == expected
