import re
import warnings
from copy import copy
from typing import ClassVar, Union, Callable, NoReturn

from bs4 import Tag, PageElement
from langchain.prompts import PromptTemplate
from langchain.schema.runnable import Runnable
from openai import InvalidRequestError

from llm import LONG_MODEL_PARSER
from models import Contractor

_address_scaper_prompt = PromptTemplate.from_template(
    """You will be given the HTML content of a construction company website.
    
    Here is the content: ```{content}```
    
    What is the mailing address of the company? Return only the address and nothing else.
    If there are two addresses, return the first one, but nothing else.
    If there is no mailing address within the content, return 'no address' and nothing else.
    """
)

_formatter_prompt = PromptTemplate.from_template(
    """You will be given text that should directly represent a mailing address.
    
    Here is the address: {address}
    
    Is this a specific mailing address? If not, return 'no address' and nothing else.
    Format the mailing address so that it is on one line, with commas separating each part of the address.
    """
)


class AddressScraper:
    _extract_chain: ClassVar[Runnable] = _address_scaper_prompt | LONG_MODEL_PARSER
    _chain: ClassVar[Runnable] = {'address': _extract_chain} | _formatter_prompt | LONG_MODEL_PARSER

    @staticmethod
    def _format_address(address: str) -> str:
        pattern = r'([A-Za-z0-9])\n'
        stripped = re.sub(pattern, r'\1, ', address)
        return stripped.replace(',\n', ', ').replace('.\n', ', ')

    @staticmethod
    def _strip_extra_data(content: Tag) -> Tag:
        for tag in content.find_all(True):
            # Remove all HTML attributes from the tag
            tag.attrs = {}
        return content

    async def _process(self, content: Union[Tag, PageElement]) -> Union[str, None]:
        """ Attempt to extract address from HTML content

        Parameters:
            content: HTML content to extract address from

        Returns:
            Address string if found, else None
        """
        try:
            result: str = await self._chain.ainvoke({'content': str(content)})
            if result.lower() != 'no address':
                return self._format_address(result)
                # replace newlines with commas using regex
        except InvalidRequestError:
            print(f"InvalidRequestError while scraping address. String might be too many tokens...")
            # TODO: break down content into smaller pieces
        return None

    async def __call__(self, content: Tag, url: str, callback: Callable[[str], None]) -> NoReturn:
        """ Scrape address from HTML content """
        _content = self._strip_extra_data(copy(content))

        # attempt to find address in footer or header
        for i in ('footer', 'header'):
            section = _content.find(i)
            if section is not None:
                address = await self._process(section)
                if address is not None:
                    return callback(address)

        # begin to look at all small text snippets
        for i in ('p', 'span', 'a'):
            sections = _content.find_all(i)
            for section in sections:
                address = await self._process(section)
                if address is not None:
                    return callback(address)

        # as a last resort, look at first and last chunks
        chunk_size = 5000
        first, last = str(_content)[:chunk_size], str(_content)[-chunk_size:]
        for i in (first, last):
            address = await self._process(i)
            if address is not None:
                return callback(address)

        warnings.warn(f"Could not find address on site: {url}")
        return
