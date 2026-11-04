"""Consecutive `globstar` patterns retain the symlink traversal allowed by either member."""
from wcmatch import glob
import os
import pytest

@pytest.mark.parametrize('as_bytes', [False, True])
@pytest.mark.parametrize('pattern', ['**/***/f', '***/**/f', '**/***/**/f', '***/**/***/f', '**/***/', '***/**/'])
@pytest.mark.parametrize('use_fd', [False, True])
def test_mixed_consecutive_globstars(tmp_path, pattern, as_bytes, use_fd):
    """Either ordering permits a triple star to consume a symlink directory."""
    target = tmp_path / 'target'
    target.mkdir()
    (target / 'f').touch()
    try:
        (tmp_path / 'link').symlink_to(target, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip('Symlinks are unavailable')
    if use_fd and not glob.SUPPORT_DIR_FD:
        pytest.skip('dir_fd is unavailable')
    root = '.' if use_fd else str(tmp_path)
    filename = os.path.join('link', 'nested', '') if pattern.endswith('/') else os.path.join('link', 'f')
    (target / 'nested').mkdir()
    if as_bytes:
        pattern, root, filename = map(os.fsencode, (pattern, root, filename))
    fd = os.open(tmp_path, os.O_RDONLY) if use_fd else None
    try:
        assert filename in glob.glob(pattern, root_dir=root, dir_fd=fd, flags=glob.GLOBSTARLONG)
        assert glob.globmatch(filename, pattern, root_dir=root, dir_fd=fd, flags=glob.REALPATH | glob.GLOBSTARLONG)
    finally:
        if fd is not None:
            os.close(fd)


@pytest.mark.parametrize('pattern', ['**/f', '**/**/f', '**/**/**/f'])
def test_double_globstars_do_not_follow_symlinks(tmp_path, pattern):
    """Collapsing double stars alone must not enable traversal."""
    target = tmp_path / 'target'
    target.mkdir()
    (target / 'f').touch()
    try:
        (tmp_path / 'link').symlink_to(target, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip('Symlinks are unavailable')
    flags = glob.GLOBSTARLONG
    assert os.path.join('target', 'f') in glob.glob(pattern, root_dir=tmp_path, flags=flags)
    assert os.path.join('link', 'f') not in glob.glob(pattern, root_dir=tmp_path, flags=flags)
    assert glob.globmatch('target/f', pattern, root_dir=tmp_path, flags=flags | glob.REALPATH)
    assert not glob.globmatch('link/f', pattern, root_dir=tmp_path, flags=flags | glob.REALPATH)
