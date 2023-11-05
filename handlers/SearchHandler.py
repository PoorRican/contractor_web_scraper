import asyncio
from typing import ClassVar, Any, NoReturn, Callable, Coroutine

from langchain.prompts import PromptTemplate
from langchain.schema.runnable import Runnable

from typedefs import Contractor
from llm import MODEL_PARSER
from log import logger
from parsers.ResultChecker import ResultChecker
from typedefs import SearchResult, SearchResults
from utils import strip_url
from search import Search

NUM_RESULTS: int = 1000


def load_blacklist() -> list[str]:
    """ Load the blacklist from a file.

    Returns:
        list of strings containing the blacklist
    """
    with open('blacklist.txt', 'r') as f:
        return [line.strip() for line in f.readlines()]


_name_extractor_prompt = PromptTemplate.from_template(
    """You will be given the title, description, and URL of a company website.
    
    Here is the website title: {title}
    Here is the website description: {description}
    Here is the website URL: {url}
    
    
    
    Infer and extract the name of the company. Only return the name of the company.
    """
)


class SearchHandler:
    """ Perform search and filter contractor websites via LLM.

    This is a functor which accepts a list of search terms, then parses each search result. A `Contractor` object is
    created for each search result that is determined to be a contractor website. For each `Contractor` object, the
    `ResultsHandler` is notified by passing a list of `Contractor` objects to the `on_parse` callback.

    The `ResultChecker` functor is used to determine if a search result is a contractor website.
    """
    _blacklist: ClassVar[list[str]] = load_blacklist()
    """ A list of strings that are used to filter out search results.
    
    Most of the items in this list are URLs that are not contractor websites such as BBB, Yelp, etc.
    However, there are snippets (such as ".gov") that are also in this list.
    """

    _name_extract_chain: ClassVar[Runnable] = _name_extractor_prompt | MODEL_PARSER
    """ Chain to extract company name from search result.
     
    This is used by `_extract_contractor()` to extract the company name from a search result.
    """

    _is_contractor_site: ClassVar[ResultChecker] = ResultChecker()

    _on_parse: Callable[[[Contractor]], Coroutine[Any, Any, None]]
    """ Asynchronous callback for handling batches of `Contractor` objects. """

    search: ClassVar[Search] = Search()

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
        params = {
            'title': await name,
            'description': desc,
            'url': url
        }

        return Contractor(**params)

    async def __call__(self, terms: list[str]) -> NoReturn:
        """ Handles searches for each term in `terms`.

        Each batch of `Contractor` objects are handled by the `_parse_results()`.

        Chunking of search results is necessary to avoid hitting Bing Search API rate limits.

        Parameters:
            terms: list of search terms
        """
        _chunk_size = 50
        for term in terms:
            logger.info(f"Searching for '{term}'")
            _runs = NUM_RESULTS // _chunk_size
            run = 1
            for offset in range(0, NUM_RESULTS, _chunk_size):
                results = self.search(term, _chunk_size, offset)
                logger.info(f"Fetched search (run {run}/{_runs})...processing results")
                run += 1
                await self._parse_results(results)

    async def _parse_results(self, results: SearchResults) -> NoReturn:
        """ Parse unfiltered results into `Contractor` objects

        First, `SearchResult` URLs which contain a blacklisted snippet (ie: "yelp.com", ".gov", etc.) are filtered out.
        Then an LLM chain filters out any search results that are not contractor sites. For each contractor site, the
        results are given to `ResultsHandler.handle_results()` via the `_on_parse` callback.

        Parameters:
            results: generator of `SearchResult` objects to parse. This should be the output of `googlesearch.search()`.
        """

        # remove any results that contain a blacklisted string
        results = [result for result in results if not any([blacklist in result.url for blacklist in self._blacklist])]

        # parse all results into an array of booleans
        # any result that is a contractor site will be True
        contractor_sites = await asyncio.gather(*[self._is_contractor_site(result) for result in results])

        contractor_count = 0
        for i in contractor_sites:
            if i:
                contractor_count += 1

        logger.info(f"Filtered {contractor_count} contractors from {len(results)} results...extracting contractors")
        # for each contractor site, extract the contractor data
        routines = []
        for result, _extract in zip(results, contractor_sites):
            if _extract:
                routines.append(self._extract_contractor(result))
        contractors = await asyncio.gather(*routines)
        logger.info(f"Extracted {len(contractors)} contractors")

        await self._on_parse(contractors)
