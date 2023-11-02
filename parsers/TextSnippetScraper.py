import asyncio
from abc import ABC
from copy import copy
from typing import Union, Generator, ClassVar

from bs4 import Tag
from langchain.schema.runnable import Runnable
from openai import InvalidRequestError

from models import Contractor
from typedefs import LLMInput
from utils import strip_html_attrs


class TextSnippetScraper(ABC):
    """ A template functor class for scraping text snippets from HTML content.

    This class is designed for extracting small text snippets from HTML content. It begins by looking at the header and
    footer of the HTML content, then looks at all small text snippets (<p>, <span>, <a>). Finally, it then chunks takes
    large chunks of text from the beginning and end of the HTML content.

    Subclasses should override the following properties:
        _chain: a chain of LLM models to extract data from text snippets
        _failure_text: a string to be returned by LLM when no data is found
        _search_type: a string representing the type of data being scraped. Used for user feedback.
    """

    _chunk_size: ClassVar[int] = 100

    _chain: ClassVar[Runnable]
    _failure_text: ClassVar[str]
    _search_type: ClassVar[str]

    @classmethod
    async def _process(cls, content: LLMInput) -> Union[str, None]:
        """ Attempt to extract the text snippet from HTML content using `self._chain`.

        Parameters:
            content: HTML content to extract snippet from

        Returns:
            The extracted snippet, or None if no snippet was found.
        """
        try:
            result: str = await cls._chain.ainvoke({'content': str(content)})
            if cls._failure_text not in result.lower():
                return result
        except InvalidRequestError:
            print(f"InvalidRequestError while scraping {cls._search_type}. String might be too many tokens...")
            # TODO: break down content into smaller pieces
        return None

    @classmethod
    def _snippet_chunks(cls, content: Tag) -> Generator[list[Tag], None, None]:
        """ Iterate over all small text snippets in the HTML content and yield them in chunks.

        Parameters:
            content: HTML content to iterate over

        Yields:
            A list of small text snippets in chunks according to `TextSnippetScraper._chunk_size`
        """
        chunks = []
        for i in ('p', 'span', 'a', 'strong', 'li', 'b', 'u', 'font'):
            sections = content.find_all(i)
            for section in sections:
                chunks.append(section)
                if len(chunks) >= cls._chunk_size:
                    yield chunks
                    chunks = []

    @classmethod
    async def _process_chunks(cls, chunks: list[Tag], contractor: Contractor, callback: str) -> bool:
        """ Simultaneously process a list of chunks and call the callback function if a snippet is found.

        Parameters:
            chunks: list of chunks to process
            callback: callback function to execute if snippet is found

        Returns:
            True if snippet was found, False otherwise
        """
        coroutines = await asyncio.gather(*[cls._process(chunk) for chunk in chunks])
        for result in coroutines:
            if result is not None:
                cls._run_callback(contractor, callback, result)
                return True
        return False

    @staticmethod
    def _run_callback(contractor: Contractor, callback_name: str, snippet: str) -> None:
        """ Run a callback function on a `Contractor` object.

        Parameters:
            contractor: `Contractor` object to update
            callback_name: name of callback function
            snippet: snippet to pass to callback function
        """
        getattr(contractor, callback_name)(snippet)

    async def __call__(self, content: Tag, url: str, contractor: Contractor, callback: str) -> bool:
        """ Scrape snippet from HTML content.

        This will attempt to scrape a snippet from the HTML content. If a snippet is found, it will be passed to the
        callback function. If no snippet is found, a warning will be raised.

        Parameters:
            content: HTML content to scrape snippet from
            url: URL of the HTML content. This is used in the warning message.
            contractor: `Contractor` object to update
            callback: callback name

        Returns:
            True if snippet was found, False otherwise
        """
        _content = strip_html_attrs(copy(content))

        # attempt to find snippet in footer or header
        for i in ('footer', 'header'):
            section = _content.find(i)
            if section is not None:
                snippet = await self._process(section)
                if snippet is not None:
                    self._run_callback(contractor, callback, snippet)
                    return True

        # begin to look at all small text snippets
        for chunk in self._snippet_chunks(_content):
            if await self._process_chunks(chunk, contractor, callback):
                return True

        # as a last resort, look at first and last chunks
        chunk_size = 5000
        first, last = str(_content)[:chunk_size], str(_content)[-chunk_size:]
        for i in (first, last):
            snippet = await self._process(i)
            if snippet is not None:
                self._run_callback(contractor, callback, snippet)
                return True

        return False
