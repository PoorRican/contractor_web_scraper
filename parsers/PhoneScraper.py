from typing import ClassVar

from langchain.prompts import PromptTemplate
from langchain.schema.runnable import Runnable

from llm import LONG_MODEL_PARSER
from parsers.TextSnippetScraper import TextSnippetScraper


def _phone_scraper_chain() -> Runnable:
    """ Create a chain of LLM models to extract a phone number from text snippets """
    _phone_scaper_prompt = PromptTemplate.from_template(
        """You will be given the HTML content of a construction company website.

        Here is the content: ```{content}```

        What is the phone number of the company? Return only the phone number and nothing else.
        If there are two phone numbers, return the first one, but nothing else.
        If there is no phone number within the content, return 'no phone number' and nothing else.
        """
    )

    _formatter_prompt = PromptTemplate.from_template(
        """You will be given text that should directly represent a phone number.

        Here is the phone number: {phone_number}

        Is this a specific phone number? If not, return 'no phone number' and nothing else.
        Format the phone number as `(###) ###-####`.
        """
    )

    _phone_extract_chain: Runnable = _phone_scaper_prompt | LONG_MODEL_PARSER
    return {'phone_number': _phone_extract_chain} | _formatter_prompt | LONG_MODEL_PARSER


class PhoneScraper(TextSnippetScraper):
    _chain: ClassVar[Runnable] = _phone_scraper_chain()
    _failure_text: ClassVar[str] = 'no phone number'
    _search_type: ClassVar[str] = 'phone number'