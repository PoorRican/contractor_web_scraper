import re
from copy import copy
from typing import ClassVar, Union

from bs4 import Tag, PageElement
from langchain.prompts import PromptTemplate
from langchain.schema.runnable import Runnable
from openai import InvalidRequestError

from llm import LONG_MODEL_PARSER

_address_scaper_prompt = PromptTemplate.from_template(
    """You will be given the HTML content of a construction company website.
    
    Here is the content: {content}
    
    What is the mailing address of the company? Return only the address and nothing else.
    If there is no mailing address within the content, return 'no address' and nothing else.
    """
)


class AddressScraper:
    _chain: ClassVar[Runnable] = _address_scaper_prompt | LONG_MODEL_PARSER

    @staticmethod
    def _format_address(address: str) -> str:
        pattern = r'([A-Za-z0-9])\n'
        stripped = re.sub(pattern, r'\1, ', address)
        return stripped.replace(',\n', ', ')

    async def _process(self, content: Union[Tag, PageElement]) -> Union[str, None]:
        """ Attempt to extract address from HTML content

        Parameters:
            content: HTML content to extract address from

        Returns:
            Address string if found, else None
        """
        try:
            result: str = await self._chain.ainvoke({'content': str(content)})
            if result != 'no address':
                return self._format_address(result)
                # replace newlines with commas using regex
        except InvalidRequestError:
            print(f"InvalidRequestError while scraping address. String might be too many tokens...")
            # TODO: break down content into smaller pieces
        return None

    async def __call__(self, content: Tag) -> str:
        """ Scrape address from HTML content """

        # attempt to find address in footer or header
        for i in ('footer', 'header'):
            section = content.find(i)
            if section is not None:
                address = await self._process(section)
                if address is not None:
                    return address

        # begin to chunk the rest of the content into smaller pieces
        _content: Tag = copy(content)
        for i in ('footer', 'header'):
            for tag in _content.find_all(i):
                tag.decompose()
        for section in _content.children:
            address = await self._process(section)
            if address is not None:
                return address
