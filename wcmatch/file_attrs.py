#!/usr/bin/python
"""File attributes."""
from __future__ import unicode_literals
import contextlib
import ctypes
import os
from . import util

_OSX_FOUNDATION_NOT_LOADED = 0
_OSX_USE_FOUNDATION = 1
_OSX_USE_CORE_FOUNDATION = 2
_OSX_FOUNDATION_METHOD = _OSX_FOUNDATION_NOT_LOADED

FILE_ATTRIBUTE_HIDDEN = 0x2
FILE_ATTRIBUTE_REPARSE_POINT = 0x400


def platform_not_implemented(path, **kwargs):  # pragma: no cover
    """Raise an exception that platform not implemented."""

    raise NotImplementedError


def has_nix_file_attributes(path, hidden=False, symlink=False):
    """Check if hidden or symlink for Linux."""

    f = os.path.basename(path)
    return (hidden and f.startswith('.')) or (symlink and os.path.islink(path))


def has_nix_file_attributes_bytes(path, hidden=False, symlink=False):
    """Check if hidden or symlink for Linux."""

    f = os.path.basename(path)
    return (hidden and f.startswith(b'.')) or (symlink and os.path.islink(path))


if util.platform() == "windows":
    def has_win_file_attributes(path, hidden=False, symlink=False):
        """Check if hidden or symlink for Windows."""

        f = os.path.basename(path)
        attrs = ctypes.windll.kernel32.GetFileAttributesW(path)
        return (
            (hidden and ((attrs != -1 and bool(attrs & FILE_ATTRIBUTE_HIDDEN)) or f.startswith('.'))) or
            (symlink and (attrs != -1 and bool(attrs & FILE_ATTRIBUTE_REPARSE_POINT)))
        )

    def has_win_file_attributes_bytes(path, hidden=False, symlink=False):
        """Check if bytes hidden or symlink for Windows."""

        f = os.path.basename(path)
        attrs = ctypes.windll.kernel32.GetFileAttributesA(path)
        return (
            (hidden and ((attrs != -1 and bool(attrs & FILE_ATTRIBUTE_HIDDEN)) or f.startswith(b'.'))) or
            (symlink and (attrs != -1 and bool(attrs & FILE_ATTRIBUTE_REPARSE_POINT)))
        )
else:
    has_win_file_attributes = platform_not_implemented
    has_win_file_attributes_bytes = platform_not_implemented


def _test():  # pragma: no cover
    """Test if macOS hidden or symlink is working."""

    path = os.path.expanduser("~/Library")
    has_macos_file_attributes_bytes(path)


if util.platform() == "osx" and _OSX_FOUNDATION_METHOD == _OSX_FOUNDATION_NOT_LOADED:  # pragma: no cover
    # Fallback to use `ctypes` to call the `ObjC` library `CoreFoundation` for macOS `has_file_attributes`

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
        kCFURLIsSymbolicLinkKey = ctypes.c_void_p.in_dll(cf, 'kCFURLIsSymbolicLinkKey')  # noqa: N816

        @contextlib.contextmanager
        def cfreleasing(objects):
            """Releasing Foundation objects."""

            try:
                yield
            finally:
                for obj in objects:
                    cf.CFRelease(obj)

        def macos_file_query(path, hidden=False, symlink=False):
            """Check if bytes hidden or symlink for macOS."""

            # Convert file name to bytes

            match = False
            objects = []
            with cfreleasing(objects):
                url = cf.CFURLCreateFromFileSystemRepresentation(None, path, len(path), False)
                objects.append(url)
                if hidden:
                    val = ctypes.c_void_p(0)
                    ret = cf.CFURLCopyResourcePropertyForKey(
                        url, kCFURLIsHiddenKey, ctypes.addressof(val), None
                    )
                    if ret:
                        result = cf.CFBooleanGetValue(val) if hidden else False
                        objects.append(val)
                        if result:
                            match = True
                    else:
                        raise OSError('CFURLCopyResourcePropertyForKey failed')
                if not match and symlink:
                    val2 = ctypes.c_void_p(0)
                    ret = cf.CFURLCopyResourcePropertyForKey(
                        url, kCFURLIsSymbolicLinkKey, ctypes.addressof(val2), None
                    )
                    if ret:
                        result = cf.CFBooleanGetValue(val) if symlink else False
                        objects.append(val2)
                        if result:
                            match = True
                    else:
                        raise OSError('CFURLCopyResourcePropertyForKey failed')
            return match

        def has_macos_file_attributes_bytes(path, hidden=False, symlink=False):
            """Check if bytes hidden or symlink for macOS."""

            return (
                (hidden and os.path.basename(path).startswith(b'.')) or
                macos_file_query(path, hidden, symlink)
            )

        def has_macos_file_attributes(path, hidden=False, symlink=False):
            """Check if hidden or symlink for macOS."""

            return (
                (hidden and os.path.basename(path).startswith('.')) or
                macos_file_query(os.fsencode(path), hidden, symlink)
            )

        _OSX_FOUNDATION_METHOD = _OSX_USE_CORE_FOUNDATION
        _test()
    except Exception:
        has_macos_file_attributes_bytes = has_nix_file_attributes_bytes
        _OSX_FOUNDATION_METHOD = _OSX_FOUNDATION_NOT_LOADED

else:
    has_macos_file_attributes = platform_not_implemented
    has_macos_file_attributes_bytes = platform_not_implemented


def has_file_attributes(path, hidden=False, symlink=False):
    """Return if file is hidden or symlink based on platform rules."""

    platform = util.platform()
    if platform == "windows":
        return has_win_file_attributes(path, hidden, symlink)
    elif platform == "osx" and _OSX_FOUNDATION_METHOD != _OSX_FOUNDATION_NOT_LOADED:  # pragma: no cover
        return has_macos_file_attributes(path, hidden, symlink)
    else:
        return has_nix_file_attributes(path, hidden, symlink)


def has_file_attributes_bytes(path, hidden=False, symlink=False):
    """Return if file is hidden or symlink based on platform rules."""

    platform = util.platform()
    if platform == "windows":
        return has_win_file_attributes_bytes(path, hidden, symlink)
    elif platform == "osx" and _OSX_FOUNDATION_METHOD != _OSX_FOUNDATION_NOT_LOADED:  # pragma: no cover
        return has_macos_file_attributes_bytes(path, hidden, symlink)
    else:
        return has_nix_file_attributes_bytes(path, hidden, symlink)


if __name__ == '__main__':  # pragma: no cover
    import sys

    for arg in sys.argv[1:]:
        filename = os.path.expanduser(arg)
        print('{}: {}'.format(filename, has_file_attributes(filename, True, True)))
