from typing import ClassVar

from langchain.prompts import PromptTemplate
from langchain.schema.runnable import Runnable

from llm import LONG_MODEL_PARSER
from parsers.TextSnippetScraper import TextSnippetScraper


def _address_scraper_chain() -> Runnable:
    """ Create a chain of LLM models to extract addresses from text snippets """
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

    _address_extract_chain: Runnable = _address_scaper_prompt | LONG_MODEL_PARSER
    return {'address': _address_extract_chain} | _formatter_prompt | LONG_MODEL_PARSER


class AddressScraper(TextSnippetScraper[str]):
    _chain: ClassVar[Runnable] = _address_scraper_chain()
    _failure_text: ClassVar[str] = 'no address'
    _search_type: ClassVar[str] = 'address'
