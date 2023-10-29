from typing import ClassVar

from langchain.prompts import PromptTemplate
from langchain.schema.runnable import Runnable

from llm import LONG_MODEL_PARSER
from parsers.TextSnippetScraper import TextSnippetScraper


def _email_scraper_chain() -> Runnable:
    """ Create a chain of LLM models to extract a phone number from text snippets """
    _email_scraper_prompt = PromptTemplate.from_template(
        """You will be given the HTML content of a construction company website.

        Here is the content: ```{content}```

        What is the email address of the company contact? Return only the email address and nothing else.
        If there is more than one email address listed, return the first one, but nothing else.
        If there is no email address within the content, return 'no email address' and nothing else.
        """
    )

    _formatter_prompt = PromptTemplate.from_template(
        """You will be given text that should directly represent an email address.

        Here is the email address: {email}

        Is this a specific email address? If not, return the raw text 'no email address' but nothing else.
        Make sure the email address is formatted properly.
        Only return the email address itself.
        """
    )

    _email_extract_chain: Runnable = _email_scraper_prompt | LONG_MODEL_PARSER
    return {'email': _email_extract_chain} | _formatter_prompt | LONG_MODEL_PARSER


class EmailScraper(TextSnippetScraper):
    _chain: ClassVar[Runnable] = _email_scraper_chain()
    _failure_text: ClassVar[str] = 'no email address'
    _search_type: ClassVar[str] = 'email address'