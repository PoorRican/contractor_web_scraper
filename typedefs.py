from typing import Union, NoReturn, Callable, Any, Generator

from bs4 import PageElement, Tag
from googlesearch import SearchResult


LLMInput = Union[Tag, PageElement, str]
""" A type alias for the input to LLM. """

ContractorCallback = Callable[[str], NoReturn]
""" A callback function to set a `Contractor` attribute. """

SearchResults = Generator[SearchResult, Any, None]
""" A generator of `SearchResult` objects. """
