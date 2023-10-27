from typing import ClassVar, Generator, Any, NoReturn

from googlesearch import search, SearchResult

from models import Contractor


class ContractorFinder:
    """ Find contractor websites by parsing description via LLM """

    contractors: list[Contractor] = []
    _terms: ClassVar[list[str]] = ["Pennsylvania residential contractor"]

    @staticmethod
    def _is_contractor_site(result: SearchResult) -> bool:
        """ Detect if site is a company site based on search result description.

        Pass description to LangChain prompt.
        """
        description = result.description
        raise NotImplementedError

    @staticmethod
    def _extract_contractor_name(title: str) -> str:
        """ Extract company name from page title using LLM """
        raise NotImplementedError
    
    def _save_contractor(self, result: SearchResult) -> NoReturn:
        """ Generate and save `Contractor` object based on `SearchResult` """
        name = self._extract_contractor_name(result.title)
        desc = result.description
        url = result.url

        company = Contractor(name, desc, url)
        if company not in self.contractors:
            self.contractors.append(company)

    @staticmethod
    def _perform_search(term: str) -> Generator[SearchResult, Any, None]:
        """ Wrapper for `googlesearch.search` """
        return search(term, advanced=True, num_results=1000, sleep_interval=1)

    @classmethod
    def _run_searches(cls) -> NoReturn:
        """ Perform searches for all terms then parse and save results """
        for term in cls._terms:
            results = cls._perform_search(term)

    def _parse_results(self, results: Generator[SearchResult, Any, None]) -> NoReturn:
        for i in results:
            if self._is_contractor_site(i):
                self._save_contractor(i)

