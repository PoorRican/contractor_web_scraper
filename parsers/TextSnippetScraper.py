import warnings
from abc import abstractmethod, ABC
from copy import copy
from typing import Union, Callable, NoReturn

from bs4 import Tag, PageElement
from langchain.schema.runnable import Runnable
from openai import InvalidRequestError


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
    @property
    @abstractmethod
    def _chain(self) -> Runnable:
        """ Return a chain of LLM models to extract data from text snippets.

        This should be overridden by subclasses.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def _failure_text(self) -> str:
        """ Return a string to be returned by LLM when no data is found.

        ie: 'no address', 'no phone number', etc.

        This should be overridden by subclasses.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def _search_type(self) -> str:
        """ Return a string representing the type of data being scraped.

        ie: 'address', 'phone number', etc.

        This should be overridden by subclasses and is used for user feedback.
        """
        raise NotImplementedError

    @staticmethod
    def _strip_extra_data(content: Tag) -> Tag:
        """ Preprocess HTML content to remove all HTML attributes from tags.

        This is used to remove all superfluous data and significantly reduce the number of tokens in the content.
        """
        for tag in content.find_all(True):
            tag.attrs = {}
        return content

    async def _process(self, content: Union[Tag, PageElement]) -> Union[str, None]:
        """ Attempt to extract the text snippet from HTML content using `self._chain`.

        Parameters:
            content: HTML content to extract snippet from

        Returns:
            The extracted snippet, or None if no snippet was found.
        """
        try:
            result: str = await self._chain.ainvoke({'content': str(content)})
            if self._failure_text not in result.lower():
                return result
        except InvalidRequestError:
            print(f"InvalidRequestError while scraping {self._search_type}. String might be too many tokens...")
            # TODO: break down content into smaller pieces
        return None

    async def __call__(self, content: Tag, url: str, callback: Callable[[str], None]) -> NoReturn:
        """ Scrape snippet from HTML content """
        _content = self._strip_extra_data(copy(content))

        # attempt to find snippet in footer or header
        for i in ('footer', 'header'):
            section = _content.find(i)
            if section is not None:
                snippet = await self._process(section)
                if snippet is not None:
                    return callback(snippet)

        # begin to look at all small text snippets
        for i in ('p', 'span', 'a'):
            sections = _content.find_all(i)
            for section in sections:
                snippet = await self._process(section)
                if snippet is not None:
                    return callback(snippet)

        # as a last resort, look at first and last chunks
        chunk_size = 5000
        first, last = str(_content)[:chunk_size], str(_content)[-chunk_size:]
        for i in (first, last):
            snippet = await self._process(i)
            if snippet is not None:
                return callback(snippet)

        warnings.warn(f"Could not find {self._search_type} on site: {url}")
        return
