"""Types."""
from typing import Union, AnyStr
import os

Strings = Union[AnyStr]
StringList = list[Strings]
WildcardPatterns = Union[Strings, StringList]
PathLikes = os.PathLike
PathLikeList = list[PathLikes]
Paths = Union[str, bytes, PathLikes]
PathList = list[Paths]
