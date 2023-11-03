from langchain.prompts import PromptTemplate
from langchain.output_parsers import CommaSeparatedListOutputParser

from llm import LONG_MODEL_PARSER, LONG_LLM
from utils import fetch_site


_parser = CommaSeparatedListOutputParser()


_link_extract_prompt = PromptTemplate.from_template(
    """You will be given several <a> tags from a company website.
    
    Here are the <a> tags: {links}
    
    Extract all important pages from the website, such as the 'About Us' page, the 'Contact Us' page, etc.
    Include any pages that showcase the company's work, such as a 'Projects' page.
    Additionally, include any pages that are important to the company, such as a 'Services' page.
    
    Each page should be on its own line and should include the full URL.
    Exclude any external links, such as links to social media.
    Exclude any media files, such as links to images or videos.
    If the link is a relative link, include the full URL with the domain: {url}
    """
)


_link_order_prompt = PromptTemplate.from_template(
    """You will be given a list of links from a company website.
    
    Here are the links: {links}
    
    Order the links from most important to least important.
    If possible the first few links should be 'about us' -> 'contact us' -> 'services' -> 'projects'.
    Then the remaining links should be ordered by importance.
    Include the full URL for each link.
   
    Exclude privacy policy and terms of service pages.
    """
)


_url_extract_prompt = PromptTemplate.from_template(
    """ You will be given a list of links from a company website.
    
    Here are the links: {links}
    
    Extract the URL for each link and return as a list.
    Include the full URL for each link and nothing but the full URL.
    
    {format_instructions}
    """, partial_variables={'format_instructions': _parser.get_format_instructions()}
)


class SiteMapExtractor:

    _extract_chain = _link_extract_prompt | LONG_MODEL_PARSER
    _order_chain = {'links': _extract_chain} | _link_order_prompt | LONG_MODEL_PARSER
    _chain = {'links': _order_chain} | _url_extract_prompt | LONG_LLM | _parser

    @classmethod
    async def extract(cls, url: str) -> list[str]:
        """ Extract all links from the page """
        content = await fetch_site(url)
        links = [link for link in content.find_all('a')]
        for i in links:
            href = i.attrs.get('href')
            i.attrs = {'href': href}
        extracted = await cls._chain.ainvoke({'links': links, 'url': url})
        return extracted

    @classmethod
    async def __call__(cls, url: str) -> list[str]:
        return await cls.extract(url)
