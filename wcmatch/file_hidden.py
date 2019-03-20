#!/usr/bin/python
"""File hidden."""
from __future__ import unicode_literals
import contextlib
import ctypes
import os
from . import util

_OSX_FOUNDATION_NOT_LOADED = 0
_OSX_USE_FOUNDATION = 1
_OSX_USE_CORE_FOUNDATION = 2
_OSX_FOUNDATION_METHOD = _OSX_FOUNDATION_NOT_LOADED


def platform_not_implemented(path):  # pragma: no cover
    """Raise an exception that platform not implemented."""

    raise NotImplementedError


def is_nix_hidden(path):
    """Check if hidden for Linux."""

    f = os.path.basename(path)
    return f.startswith('.')


def is_nix_hidden_bytes(path):
    """Check if hidden for Linux."""

    f = os.path.basename(path)
    return f.startswith(b'.')


if util.platform() == "windows":
    def is_win_hidden(path):
        """Check if hidden for Windows."""

        f = os.path.basename(path)
        attrs = ctypes.windll.kernel32.GetFileAttributesW(path)
        return (attrs != -1 and bool(attrs & 2)) or f.startswith('.')

    def is_win_hidden_bytes(path):
        """Check if bytes hidden for Windows."""

        f = os.path.basename(path)
        attrs = ctypes.windll.kernel32.GetFileAttributesA(path)
        return (attrs != -1 and bool(attrs & 2)) or f.startswith(b'.')
else:
    is_win_hidden = platform_not_implemented
    is_win_hidden_bytes = platform_not_implemented


def _test(fn):  # pragma: no cover
    """Test if macOS hidden is working."""

    path = os.path.expanduser("~/Library")
    is_osx_hidden(path)


if util.platform() == "osx" and _OSX_FOUNDATION_METHOD == _OSX_FOUNDATION_NOT_LOADED:  # pragma: no cover
    # Fallback to use `ctypes` to call the `ObjC` library `CoreFoundation` for macOS `is_hidden`

    # http://stackoverflow.com/questions/284115/cross-platform-hidden-file-detection
    try:
        # Setup macOS access to `CoreFoundatin` for hidden file detection
        cf = ctypes.cdll.LoadLibrary('/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation')
        cf.CFShow.argtypes = [ctypes.c_void_p]
        cf.CFShow.restype = None
        cf.CFRelease.argtypes = [ctypes.c_void_p]
        cf.CFRelease.restype = None
        cf.CFURLCreateFromFileSystemRepresentation.argtypes = [
            ctypes.c_void_p,
            ctypes.c_char_p,
            ctypes.c_long,
            ctypes.c_int
        ]
        cf.CFURLCreateFromFileSystemRepresentation.restype = ctypes.c_void_p
        cf.CFURLCopyResourcePropertyForKey.argtypes = [
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p
        ]
        cf.CFURLCopyResourcePropertyForKey.restype = ctypes.c_int
        cf.CFBooleanGetValue.argtypes = [ctypes.c_void_p]
        cf.CFBooleanGetValue.restype = ctypes.c_int

        # This one is a static `CFStringRef`.
        kCFURLIsHiddenKey = ctypes.c_void_p.in_dll(cf, 'kCFURLIsHiddenKey')  # noqa: N816

        @contextlib.contextmanager
        def cfreleasing(objects):
            """Releasing Foundation objects."""

            try:
                yield
            finally:
                for obj in objects:
                    cf.CFRelease(obj)

        def is_osx_hidden_bytes(path):
            """Check if bytes hidden for macOS."""

            # Convert file name to bytes

            objects = []
            with cfreleasing(objects):
                url = cf.CFURLCreateFromFileSystemRepresentation(None, path, len(path), False)
                objects.append(url)
                val = ctypes.c_void_p(0)
                ret = cf.CFURLCopyResourcePropertyForKey(
                    url, kCFURLIsHiddenKey, ctypes.addressof(val), None
                )
                if ret:
                    result = cf.CFBooleanGetValue(val)
                    objects.append(val)
                    return True if result else False
                raise OSError('CFURLCopyResourcePropertyForKey failed')

        def is_osx_hidden(path):
            """Check if hidden for macOS."""

            return is_osx_hidden_bytes(os.fsencode(path))

        _OSX_FOUNDATION_METHOD = _OSX_USE_CORE_FOUNDATION
        _test(is_osx_hidden)
    except Exception:
        is_osx_hidden = is_nix_hidden
        _OSX_FOUNDATION_METHOD = _OSX_FOUNDATION_NOT_LOADED

else:
    is_osx_hidden = platform_not_implemented
    is_osx_hidden_bytes = platform_not_implemented


def is_hidden(path):
    """Return if file is hidden based on platform rules."""

    platform = util.platform()
    if platform == "windows":
        return is_win_hidden(path)
    elif platform == "osx":  # pragma: no cover
        if is_nix_hidden(path):
            return True
        elif _OSX_FOUNDATION_METHOD != _OSX_FOUNDATION_NOT_LOADED:
            return is_osx_hidden(path)
        return False
    else:
        return is_nix_hidden(path)


def is_hidden_bytes(path):
    """Return if file is hidden based on platform rules."""

    platform = util.platform()
    if platform == "windows":
        return is_win_hidden_bytes(path)
    elif platform == "osx":  # pragma: no cover
        if is_nix_hidden_bytes(path):
            return True
        elif _OSX_FOUNDATION_METHOD != _OSX_FOUNDATION_NOT_LOADED:
            return is_osx_hidden_bytes(path)
        return False
    else:
        return is_nix_hidden_bytes(path)


if __name__ == '__main__':  # pragma: no cover
    import sys

    for arg in sys.argv[1:]:
        filename = os.path.expanduser(arg)
        print('{}: {}'.format(filename, is_hidden(filename)))
