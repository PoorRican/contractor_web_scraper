from typing import ClassVar, Any, Coroutine

from bs4 import Tag
from langchain.prompts import PromptTemplate
from langchain.schema.runnable import Runnable

from llm import LONG_MODEL_PARSER

_address_scaper_prompt = PromptTemplate.from_template(
    """You will be given the HTML content of a construction company website.
    
    Here is the content: {content}
    
    What is the mailing address of the company? Return only the address.
    If there is no mailing address on the page, return 'no address'.
    """
)


class AddressScraper:
    _chain: ClassVar[Runnable] = _address_scaper_prompt | LONG_MODEL_PARSER

    async def __call__(self, content: Tag) -> str:
        """ Scrape address from HTML content """
        # TODO: begin to chunk the content into smaller pieces

        section = content.find('footer')
        result = await self._chain.ainvoke({'content': section})
        if result != 'no address':
            return result

        section = content.find('header')
        result = await self._chain.ainvoke({'content': section})
        if result != 'no address':
            return result
