"""Test independent filesystem prefixes for multiple globstars."""
import os
import pytest
from wcmatch import glob


@pytest.mark.parametrize('as_bytes', [False, True])
@pytest.mark.parametrize('pattern', ['**/literal/**/file.txt', '**/literal/**/leaf/**/file.txt'])
@pytest.mark.parametrize('link', ['outer/literal/link', 'outer/link'])
def test_globstar_symlink_prefix(tmp_path, monkeypatch, as_bytes, pattern, link):
    """Only symlinks on the actual matched path should prevent traversal."""

    filename = 'outer/literal/link/leaf/final/file.txt'
    file = tmp_path / filename
    file.parent.mkdir(parents=True)
    file.write_text('')
    root = str(tmp_path)
    link_path = os.path.normpath(str(tmp_path / link))
    if as_bytes:
        filename = os.fsencode(filename)
        pattern = os.fsencode(pattern)
        root = os.fsencode(root)
        link_path = os.fsencode(link_path)

    monkeypatch.setattr('wcmatch._wcmatch.os.path.islink', lambda path: os.path.normpath(path) == link_path)
    flags = glob.GLOBSTAR | glob.REALPATH
    assert glob.globmatch(filename, pattern, root_dir=root, flags=flags) == (link == 'outer/link')
    assert glob.globmatch(filename, pattern, root_dir=root, flags=flags | glob.FOLLOW)
