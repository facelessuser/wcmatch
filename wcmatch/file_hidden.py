#!/usr/bin/python
"""File hidden."""
from __future__ import unicode_literals
import contextlib
import ctypes
from os.path import expanduser, basename
from . import util

_OSX_FOUNDATION_NOT_LOADED = 0
_OSX_USE_FOUNDATION = 1
_OSX_USE_CORE_FOUNDATION = 2
_OSX_FOUNDATION_METHOD = _OSX_FOUNDATION_NOT_LOADED


def platform_not_implemented(path):
    """Raise an exception that platform not implemented."""

    raise NotImplementedError


if util.platform() == "windows":
    def is_win_hidden(path):
        """Check if hidden for Windows."""

        f = basename(path)
        attrs = ctypes.windll.kernel32.GetFileAttributesW(path)
        return (attrs != -1 and bool(attrs & 2)) or (f.startswith('.') and f != "..")
else:
    is_win_hidden = platform_not_implemented


def is_nix_hidden(path):
    """Check if hidden for Linux."""

    f = basename(path)
    return f.startswith('.') and f != ".."


def _test(fn):
    """Test if osx hidden is working."""

    path = expanduser("~/Library")
    is_osx_hidden(path)
    # print "OSX Hidden Method: %d, Test Path: %s, Result: %s"  % (_OSX_FOUNDATION_METHOD, path, str(fn(path)))


if util.platform() == "osx" and _OSX_FOUNDATION_METHOD == _OSX_FOUNDATION_NOT_LOADED:
    # Fallback to use ctypes to call the ObjC library CoreFoundation for OSX is_hidden

    # http://stackoverflow.com/questions/284115/cross-platform-hidden-file-detection
    try:
        # Setup OSX access to CoreFoundatin for hidden file detection
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

        # This one is a static CFStringRef.
        kCFURLIsHiddenKey = ctypes.c_void_p.in_dll(cf, 'kCFURLIsHiddenKey')

        @contextlib.contextmanager
        def cfreleasing(objects):
            """Releasing Foundation objects."""

            try:
                yield
            finally:
                for obj in objects:
                    cf.CFRelease(obj)

        def is_osx_hidden(path):
            """OSX platform is_hidden."""

            # Convert file name to bytes
            if not isinstance(path, bytes):
                path = path.encode('UTF-8')

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

        _OSX_FOUNDATION_METHOD = _OSX_USE_CORE_FOUNDATION
        _test(is_osx_hidden)
    except Exception:
        is_osx_hidden = is_nix_hidden
        _OSX_FOUNDATION_METHOD = _OSX_FOUNDATION_NOT_LOADED


if util.platform() != "osx":
    is_osx_hidden = platform_not_implemented


def is_hidden(path):
    """Return if file is hidden based on platform rules."""

    platform = util.platform()
    if platform == "windows":
        return is_win_hidden(path)
    elif platform == "osx":
        if is_nix_hidden(path):
            return True
        elif _OSX_FOUNDATION_METHOD != _OSX_FOUNDATION_NOT_LOADED:
            return is_osx_hidden(path)
        return False
    else:
        return is_nix_hidden(path)


if __name__ == '__main__':
    import sys

    for arg in sys.argv[1:]:
        filename = expanduser(arg)
        print('{}: {}'.format(filename, is_hidden(filename)))
