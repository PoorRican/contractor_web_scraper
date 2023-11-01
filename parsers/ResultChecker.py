from operator import itemgetter
from typing import ClassVar

from googlesearch import SearchResult, search
from langchain.prompts import PromptTemplate
from langchain.schema.runnable import Runnable, RunnableParallel

from llm import LLM, MODEL_PARSER
from utils import strip_url

_description_expand_prompt = PromptTemplate.from_template(
    """ You will be given the title, URL, and description of a search result.

    Here is the title: {title}
    Here is the URL: {url}
    Here is the description: {description}


    Please explain what this page is about in one sentence.
    Does this page directly represent construction company website?

    """
)

_is_contractor_prompt = PromptTemplate.from_template(
    """Given an explanation of a search result,
    determine if it directly represents a webpage for a construction contractor company website.
    Return 'contractor' if it is,
    and 'not contractor' if it does not directly represent a contractor company website.

    {explanation}
    """
)


_comparator_prompt = PromptTemplate.from_template(
    """You will given a company title and a URL and have understanding to see the nuances between URL and company name.
    The URL may or may not directly represent the company.
    You are to compare the the url to the company name and determine if they are the same.
    
    If the URL contains words that or concepts that are not in the company name, then the URL does not directly
    represent the company. However, there might be acronyms or abbreviations in the URL that are not in the company
    name. 

    Here is the company title: {title}
    Here is the url: {url}
    
    Does the URL directly belong to the company? Respond tersely in one sentence."""
)

_comparator_simplification_prompt = PromptTemplate.from_template(
    """You will be given a statement describing if a URL belongs to a 
    
    Here is the statement: {statement}
    
    If the URL does not belong to the company, return a terse statement "not similar".
    If the URL belongs to the company, return a terse statement "same"."""
)

_comparator_preprocess_chain = _comparator_prompt | MODEL_PARSER
_comparator_chain = {'statement': _comparator_preprocess_chain} | _comparator_simplification_prompt | MODEL_PARSER

_expand_chain = _description_expand_prompt | MODEL_PARSER
_is_contractor_chain = {'explanation': _expand_chain} | _is_contractor_prompt | MODEL_PARSER


class ResultChecker:
    """ Functor which checks if a `SearchResult` is a valid company by comparing the `title` and `url`.

    If the `url` seems to be valid for the given company, then `True` is given. Otherwise, `False` is returned.
    This is meant to be used by `SearchParser` to ignore sites which feature valid companies such as local newspapers
    and instead favor actual company websites.
    """
    """ Chain to determine if a search result is a contractor site.

    This is used by `_is_contractor_site()` to determine if a search result is a contractor site.
    """

    _chain = RunnableParallel(alignment=_comparator_chain, is_contractor=_is_contractor_chain)

    @staticmethod
    def _is_contractor(response: str) -> bool:
        """ Detect if site is a company site based on search result.

        This is parse the result from `_is_contractor_chain`.

        Parameters:
            response: LLM response from `_is_contractor_chain`

        Returns:
            True if site is a contractor site, False otherwise
        """
        if 'not contractor' in response.lower():
            return False
        elif 'contractor' in response.lower():
            return True
        else:
            raise ValueError(f"`_is_contractor_chain` returned ambiguous output: '{response}'")

    @staticmethod
    def _is_contractor_site(response: str) -> bool:
        """ Detect if search result is a company site by comparing the `title` and `url`.

        This is to parse the result from `_comparator_chain`

        Parameters:
            response: LLM response from `_comparator_chain`

        Returns:
            True if site is a contractor site, False otherwise
        """
        lower = response.lower()
        if 'not similar' in lower:
            return False
        elif 'same' in lower:
            return True
        else:
            raise ValueError(f"`_comparator_chain` returned ambiguous output: '{response}'")

    @classmethod
    async def __call__(cls, result: SearchResult) -> bool:
        title = result.title
        description = result.description
        url = strip_url(result.url)

        response = await cls._chain.ainvoke({
            'title': title,
            'description': description,
            'url': url,
        })
        alignment = response['alignment']
        is_contractor = response['is_contractor']

        return cls._is_contractor(is_contractor) and cls._is_contractor_site(alignment)
