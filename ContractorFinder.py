import asyncio
from typing import ClassVar, Generator, Any, NoReturn, Coroutine

from googlesearch import search, SearchResult
from langchain.prompts import PromptTemplate
from langchain.schema.runnable import Runnable
from langchain.chat_models import ChatOpenAI
from langchain.schema.output_parser import StrOutputParser
from langchain.callbacks import StdOutCallbackHandler

from models import Contractor


NUM_RESULTS: int = 100


LLM = ChatOpenAI(temperature=0, model_name='gpt-3.5-turbo', callbacks=[StdOutCallbackHandler()])
MODEL_PARSER = LLM | StrOutputParser()


_name_extractor_prompt = PromptTemplate.from_template(
    """You will be given the title and description of a company website.
    
    Here is the website title: {title}
    Here is the website description: {description}
    
    
    Extract and return only name of the company.
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
    and 'not contractor' if it's a different type of page that mentions 'contractor' but is not a contractor company website.
    
    {explanation}
    """
)


class ContractorFinder:
    """ Find contractor websites via LLM """

    contractors: list[Contractor] = []
    _name_extract_chain: ClassVar[Runnable] = _name_extractor_prompt | MODEL_PARSER
    _expand_chain: ClassVar[Runnable] = _description_expand_prompt | LLM
    _is_contractor_chain: ClassVar[Runnable] = {'explanation': _expand_chain} | _is_contractor_prompt | MODEL_PARSER

    @classmethod
    async def _is_contractor_site(cls, result: SearchResult) -> bool:
        """ Detect if site is a company site based on search result description.

        Pass description to LangChain prompt.
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
        """ Extract company data from search result using LLM """
        name = cls._name_extract_chain.ainvoke({'title': result.title, 'description': result.description})
        desc = result.description
        url = result.url

        return Contractor(await name, desc, url)

    @staticmethod
    def _perform_search(term: str) -> Generator[SearchResult, Any, None]:
        """ Wrapper for `googlesearch.search` """
        return search(term, advanced=True, num_results=NUM_RESULTS, sleep_interval=1)

    async def __call__(self, terms: list[str]) -> NoReturn:
        """ Perform searches for all terms then parse and save results """
        # TODO: this could be parallelized
        for term in terms:
            results = self._perform_search(term)
            print("Fetched search...processing results")
            await self._parse_results(results)

    async def _parse_results(self, results: Generator[SearchResult, Any, None]) -> NoReturn:
        """ Parse unfiltered results into `Contractor` objects """
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

        self.contractors.extend(contractors)
