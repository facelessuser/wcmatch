"""Types."""
from typing import Union, Any, Iterable, AnyStr
import pathlib
import os

Strings = Union[AnyStr]
StringList = list[Strings]
WildcardPatterns = Union[Strings, StringList]
PathLikes = os.PathLike
PathLikeList = list[PathLikes]
Paths = Union[str, bytes, PathLikes]
PathList = list[Paths]
