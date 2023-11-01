import asyncio
import warnings
from asyncio import sleep
from typing import ClassVar, Any, NoReturn, Callable, Coroutine

from googlesearch import search, SearchResult
from langchain.prompts import PromptTemplate
from langchain.schema.runnable import Runnable
from requests import ReadTimeout, HTTPError

from models import Contractor
from llm import MODEL_PARSER
from parsers.ResultChecker import ResultChecker
from typedefs import SearchResults
from utils import strip_url

NUM_RESULTS: int = 100


_name_extractor_prompt = PromptTemplate.from_template(
    """You will be given the title, description, and URL of a company website.
    
    Here is the website title: {title}
    Here is the website description: {description}
    Here is the website URL: {url}
    
    
    
    Infer and extract the name of the company. Only return the name of the company.
    """
)


class SearchParser:
    """ Perform search and filter contractor websites via LLM.

    This is a functor which accepts a list of search terms, then parses each search result. A `Contractor` object is
    created for each search result that is determined to be a contractor website. For each `Contract` object, the
    `ResultsHandler` is notified by passing a list of `Contractor` objects to the `on_parse` callback.
    """

    _name_extract_chain: ClassVar[Runnable] = _name_extractor_prompt | MODEL_PARSER
    """ Chain to extract company name from search result.
     
    This is used by `_extract_contractor()` to extract the company name from a search result.
    """

    _is_contractor_site: ClassVar[ResultChecker] = ResultChecker()

    _on_parse: Callable[[[Contractor]], Coroutine[Any, Any, None]]
    """ Asynchronous callback for handling batches of `Contractor` objects. """

    def __init__(self, on_parse: Callable[[[Contractor]], Coroutine[Any, Any, None]]):
        self._on_parse = on_parse

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
        url = strip_url(result.url)

        return Contractor(await name, desc, url)

    @staticmethod
    async def _perform_search(term: str) -> SearchResults:
        """ Wrapper for `googlesearch.search`

        This uses `NUM_RESULTS` as the number of results to fetch.

        Parameters:
            term: search term to use

        Returns:
            Generator of `SearchResult` objects
        """
        print(f"\nFetching search for '{term}'")
        max_retries = 10
        retries = 0
        while retries < max_retries:
            try:
                results = search(term, advanced=True, num_results=NUM_RESULTS, sleep_interval=1)
                return [result for result in results]
            except (ReadTimeout, HTTPError) as e:
                retries += 1
                time = pow(retries, 3)
                warnings.warn(f"Retrying search for '{term}' after {time}s. Error: {e}")
                await sleep(time)
        raise ReadTimeout('Retried 5 times')

    async def __call__(self, terms: list[str]) -> NoReturn:
        """ Handles searches for each term in `terms`.

        Each batch of `Contractor` objects are handled individually by the `_on_parse()` callback.

        Parameters:
            terms: list of search terms
        """
        # TODO: this could be parallelized
        for term in terms:
            results = await self._perform_search(term)
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
        # parse all results into an array of booleans
        # any result that is a contractor site will be True
        contractor_sites = await asyncio.gather(*[self._is_contractor_site(result) for result in results])

        # for each contractor site, extract the contractor data
        routines = []
        for result, _extract in zip(results, contractor_sites):
            if _extract:
                routines.append(self._extract_contractor(result))
        contractors = await asyncio.gather(*routines)
        print(f"Extracted {len(contractors)} contractors from {len(results)}")

        await self._on_parse(contractors)
