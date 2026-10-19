"""Check leading dots after extended groups that can match an empty string."""
import os

import pytest

from wcmatch import fnmatch, glob


@pytest.mark.parametrize('matcher', [fnmatch, glob])
@pytest.mark.parametrize('pattern', ['?(a)*', '*(a)?hidden', '@(a|)[.]hidden', '+(a|)*'])
@pytest.mark.parametrize('as_bytes', [False, True])
@pytest.mark.parametrize('capture', [False, True])
@pytest.mark.parametrize('dotmatch', [False, True])
def test_optional_group_wildcard_dotmatch(matcher, pattern, as_bytes, capture, dotmatch):
    """Wildcards still need `DOTMATCH` when an earlier group consumes no text."""

    flags = matcher.EXTMATCH | matcher.FORCEUNIX
    if capture:
        flags |= matcher.CAPTURE
    if dotmatch:
        flags |= matcher.DOTMATCH
    hidden, visible = '.hidden', 'a.hidden'
    if as_bytes:
        pattern, hidden, visible = pattern.encode(), hidden.encode(), visible.encode()
    match = matcher.fnmatch if matcher is fnmatch else matcher.globmatch

    assert match(hidden, pattern, flags=flags) is dotmatch
    assert match(visible, pattern, flags=flags)


@pytest.mark.parametrize('matcher', [fnmatch, glob])
@pytest.mark.parametrize('as_bytes', [False, True])
@pytest.mark.parametrize('capture', [False, True])
def test_optional_group_literal_dot(matcher, as_bytes, capture):
    """A literal dot after an empty group continues to match hidden names."""

    flags = matcher.EXTMATCH | matcher.FORCEUNIX
    if capture:
        flags |= matcher.CAPTURE
    pattern, hidden, visible = '?(a).hidden', '.hidden', 'a.hidden'
    if as_bytes:
        pattern, hidden, visible = pattern.encode(), hidden.encode(), visible.encode()
    match = matcher.fnmatch if matcher is fnmatch else matcher.globmatch

    assert match(hidden, pattern, flags=flags)
    assert match(visible, pattern, flags=flags)


@pytest.mark.parametrize('windows', [False, True])
@pytest.mark.parametrize('pattern', ['?(a)*', '*(a)?hidden', '@(a|)[.]hidden', '+(a|)*'])
def test_optional_group_after_separator(pattern, windows):
    """Dot restrictions also apply at the start of later path components."""

    flags = glob.EXTGLOB | (glob.FORCEWIN if windows else glob.FORCEUNIX)
    separator = '\\' if windows else '/'

    assert not glob.globmatch('root' + separator + '.hidden', 'root/' + pattern, flags=flags)
    assert glob.globmatch('root' + separator + 'a.hidden', 'root/' + pattern, flags=flags)


@pytest.mark.parametrize('as_bytes', [False, True])
@pytest.mark.parametrize('dotmatch', [False, True])
def test_optional_group_glob_directory(tmp_path, as_bytes, dotmatch):
    """Directory scans omit hidden entries unless `DOTMATCH` is requested."""

    for name in ['.hidden', 'a.hidden', 'visible']:
        (tmp_path / name).touch()
    flags = glob.EXTGLOB
    expected = ['a.hidden', 'visible']
    if dotmatch:
        flags |= glob.DOTMATCH
        expected.insert(0, '.hidden')
    pattern, root_dir = '?(a)*', str(tmp_path)
    if as_bytes:
        pattern, root_dir = pattern.encode(), os.fsencode(root_dir)
        expected = [name.encode() for name in expected]

    assert sorted(glob.glob(pattern, root_dir=root_dir, flags=flags)) == expected
