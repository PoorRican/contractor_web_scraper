from typing import ClassVar, Generator, Any, NoReturn

from googlesearch import search, SearchResult
from langchain.prompts import PromptTemplate
from langchain.schema.runnable import Runnable
from langchain.chat_models import ChatOpenAI
from langchain.schema.output_parser import StrOutputParser

from models import Contractor


NUM_RESULTS: int = 15


LLM = ChatOpenAI(temperature=0, model_name='gpt-3.5-turbo')
MODEL_PARSER = LLM | StrOutputParser()


_name_extractor_prompt = PromptTemplate.from_template(
    """You will be given the title of a company webpage.
    
    Here is the webpage title: 
    {title}
    
    
    Extract and return only name of the company.
    """
)


_description_expand_prompt = PromptTemplate.from_template(
    """ You will be given the title, URL, and description of a search result. Please explain what this page is about in one sentence.
    Does this page directly represent construction company website?
    
    Here is the title: {title}
    Here is the URL: {url}
    Here is the description: {description}
    """
)


_is_contractor_prompt = PromptTemplate.from_template(
    """Given an explanation of a search result, determine if it represents a webpage for a construction contractor company website. Return 'contractor' if it is, and 'not contractor' if it's a different type of page that mentions 'contractor' but is not a contractor company website.
    You will encounter how-to / guide pages, government websites, association pages, union pages, registration pages, directory pages, and best of pages, which are not contractors.
    
    {explanation}
    """
)


class ContractorFinder:
    """ Find contractor websites by parsing description via LLM """

    contractors: list[Contractor] = []
    _name_extract_chain: ClassVar[Runnable] = _name_extractor_prompt | MODEL_PARSER
    _expand_chain: ClassVar[Runnable] = _description_expand_prompt | LLM
    _is_contractor_chain: ClassVar[Runnable] = {'explanation': _expand_chain} | _is_contractor_prompt | MODEL_PARSER

    @classmethod
    def _is_contractor_site(cls, result: SearchResult) -> bool:
        """ Detect if site is a company site based on search result description.

        Pass description to LangChain prompt.
        """
        title = result.title
        url = result.url
        description = result.description
        response = cls._is_contractor_chain.invoke({
            'title': title,
            'url': url,
            'description': description
        })
        if response == 'contractor':
            return True
        elif response == 'not contractor':
            return False
        else:
            raise ValueError("`_is_contractor_chain` returned ambiguous output")

    @classmethod
    def _extract_contractor_name(cls, title: str) -> str:
        """ Extract company name from page title using LLM """
        return cls._name_extract_chain.invoke({'title': title})

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
        return search(term, advanced=True, num_results=NUM_RESULTS, sleep_interval=1)

    def __call__(self, terms: list[str]) -> NoReturn:
        """ Perform searches for all terms then parse and save results """
        for term in terms:
            results = self._perform_search(term)
            self._parse_results(results)

    def _parse_results(self, results: Generator[SearchResult, Any, None]) -> NoReturn:
        for i in results:
            if self._is_contractor_site(i):
                self._save_contractor(i)
