"""Custom types."""
from typing import TypeVar, Union, Tuple, Set, MutableSequence
import os

T = TypeVar('T')
WcPattern = Union[T, MutableSequence[T], Tuple[T], Set[T]]
WcPath = Union[T, 'os.PathLike[T]']
