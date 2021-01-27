"""Types."""
import sys
import typing
import os

PY39 = (3, 7) <= sys.version_info


Strings = typing.Union[typing.AnyStr]
StringList = typing.List[Strings]
WildcardPatterns = typing.Union[Strings, StringList]
PathLikes = os.PathLike
PathLikeList = typing.List[PathLikes]
Paths = typing.Union[str, bytes, PathLikes]
PathList = typing.List[Paths]
