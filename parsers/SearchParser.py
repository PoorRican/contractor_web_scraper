import asyncio
from typing import ClassVar, Generator, Any, NoReturn, Callable, Coroutine
from urllib.parse import urlparse

from googlesearch import search, SearchResult
from langchain.prompts import PromptTemplate
from langchain.schema.runnable import Runnable

from models import Contractor
from llm import LLM, MODEL_PARSER
from typedefs import SearchResults

NUM_RESULTS: int = 100


_name_extractor_prompt = PromptTemplate.from_template(
    """You will be given the title, description, and URL of a company website.
    
    Here is the website title: {title}
    Here is the website description: {description}
    Here is the website URL: {url}
    
    
    
    Infer and extract the name of the company. Only return the name of the company.
    """
)


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


class SearchParser:
    """ Perform search and filter contractor websites via LLM.

    This is a functor which accepts a list of search terms, then parses each search result. A `Contractor` object is
    created for each search result that is determined to be a contractor website. For each `Contract` object, the
    `ContractorHandler` is notified by passing a list of `Contractor` objects to the `on_parse` callback.
    """

    _name_extract_chain: ClassVar[Runnable] = _name_extractor_prompt | MODEL_PARSER
    """ Chain to extract company name from search result.
     
    This is used by `_extract_contractor()` to extract the company name from a search result.
    """
    _expand_chain: ClassVar[Runnable] = _description_expand_prompt | LLM
    _is_contractor_chain: ClassVar[Runnable] = {'explanation': _expand_chain} | _is_contractor_prompt | MODEL_PARSER
    """ Chain to determine if a search result is a contractor site.
    
    This is used by `_is_contractor_site()` to determine if a search result is a contractor site.
    """

    _on_parse: Callable[[[Contractor]], Coroutine[Any, Any, None]]
    """ Asynchronous callback for handling batches of `Contractor` objects. """

    def __init__(self, on_parse: Callable[[[Contractor]], Coroutine[Any, Any, None]]):
        self._on_parse = on_parse

    @classmethod
    async def _is_contractor_site(cls, result: SearchResult) -> bool:
        """ Detect if site is a company site based on search result.

        This uses the `_is_contractor_chain` to determine if the search result is a contractor site.

        Parameters:
            result: `SearchResult` object to check

        Returns:
            True if site is a contractor site, False otherwise
        """
        title = result.title
        url = result.url
        description = result.description
        response = await cls._is_contractor_chain.ainvoke({
            'title': title,
            'url': url,
            'description': description
        })
        response = response.strip()
        if response == 'contractor':
            return True
        elif response == 'not contractor':
            return False
        else:
            raise ValueError(f"`_is_contractor_chain` returned ambiguous output: '{response}'")

    @classmethod
    async def _extract_contractor(cls, result: SearchResult) -> Contractor:
        """ Extract company data from search result using LLM.

        This uses the `_name_extract_chain` to extract the company name from the search result.

        Parameters:
            result: `SearchResult` object to extract data from

        Returns:
            `Contractor` object containing extracted data
        """
        name = cls._name_extract_chain.ainvoke({
            'title': result.title,
            'description': result.description,
            'url': result.url
        })
        desc = result.description
        # remove path and params from URL
        url = urlparse(result.url)._replace(path='')._replace(params='').geturl()

        return Contractor(await name, desc, url)

    @staticmethod
    def _perform_search(term: str) -> SearchResults:
        """ Wrapper for `googlesearch.search`

        This uses `NUM_RESULTS` as the number of results to fetch.

        Parameters:
            term: search term to use

        Returns:
            Generator of `SearchResult` objects
        """
        return search(term, advanced=True, num_results=NUM_RESULTS, sleep_interval=1)

    async def __call__(self, terms: list[str]) -> NoReturn:
        """ Handles searches for each term in `terms`.

        Each batch of `Contractor` objects are handled individually by the `_on_parse()` callback.

        Parameters:
            terms: list of search terms
        """
        # TODO: this could be parallelized
        for term in terms:
            results = self._perform_search(term)
            print("Fetched search...processing results")
            await self._parse_results(results)

    async def _parse_results(self, results: SearchResults) -> NoReturn:
        """ Parse unfiltered results into `Contractor` objects

        This will filter out any search results that are not contractor sites. Then for each contractor site, the
        `_on_parse` callback is called with a list of `Contractor` objects.

        For each batch of `Contractor` objects that are parsed, the `_on_parse` callback is called.

        Parameters:
            results: generator of `SearchResult` objects to parse. This should be the output of `googlesearch.search()`.
        """
        results = [result for result in results]

        # parse all results into an array of booleans
        # any result that is a contractor site will be True
        contractor_sites = await asyncio.gather(*[self._is_contractor_site(result) for result in results])

        print("Extracting contractors...")
        # for each contractor site, extract the contractor data
        routines = []
        for result, _extract in zip(results, contractor_sites):
            if _extract:
                routines.append(self._extract_contractor(result))
        contractors = await asyncio.gather(*routines)

        await self._on_parse(contractors)
