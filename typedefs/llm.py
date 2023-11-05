from typing import Union

from bs4 import Tag, PageElement

LLMInput = Union[Tag, PageElement, str]
""" A type alias for the input to LLM. """
