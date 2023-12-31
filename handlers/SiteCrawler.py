import asyncio
from enum import Enum
from typing import NoReturn, Union, ClassVar

from log import logger
from typedefs import Contractor
from parsers import AddressScraper, PhoneScraper, EmailScraper
from parsers.SiteMapExtrator import SiteMapExtractor
from typedefs import ContractorCallback
from utils import fetch_site


class _FieldType(Enum):
    """ An enum representing a field type to be scraped.

    This enum is used to determine which scraper and callback to use for a given field. Additionally, it is used to
    determine which fields have not been scraped for a given `Contractor` object.
    """
    address = 'address'
    email = 'email'
    phone = 'phone'

    def get_scraper(self) -> Union[AddressScraper, EmailScraper, PhoneScraper]:
        """ Return the corresponding scraper type for this field type """
        if self == self.address:
            return AddressScraper()
        elif self == self.email:
            return EmailScraper()
        elif self == self.phone:
            return PhoneScraper()
        else:
            raise ValueError(f"Unknown field type: {self}")

    def get_callback(self, contractor: Contractor) -> ContractorCallback:
        """ Return the corresponding callback for this field type

        These callbacks are used by `TextSnippetScraper` to update the `Contractor` object with the scraped data.
        """
        if self == self.address:
            return contractor.set_address
        elif self == self.email:
            return contractor.set_email
        elif self == self.phone:
            return contractor.set_phone
        else:
            raise ValueError(f"Unknown field type: {self}")


def default_fields() -> set[_FieldType]:
    return {_FieldType.address, _FieldType.email, _FieldType.phone}


class SiteCrawler:
    """ A facade for scraping as much data as possible from a contractor website.

    A list of pages which need to be scraped, and fields which have not been found yet, are maintained internally. Each
    page is scraped individually, and callbacks are used to update the `Contractor` object. Whenever a field is found,
    it is removed from the list of fields to be scraped. Whenever a page is scraped, it is removed from the list of
    pages to be scraped.
    """
    _map_extractor: ClassVar[SiteMapExtractor] = SiteMapExtractor()
    _contractor: Contractor

    _pages: set[str]
    """ A set of URLs to be scraped.
    
    As pages are scraped, they are removed from this set.
    """

    _fields: set[_FieldType]
    """ A set of fields that are lacking by the `Contractor` object.
    
    As data is found, they are removed from this set.
    """

    def __init__(self, contractor: Contractor):
        """ Initialize the `SiteCrawler` object.

        A list of pages to be scraped is initialized with the contractor's URL.
        """
        self._pages = set()
        self._fields = default_fields()
        self._contractor = contractor

        self._pages.add(contractor.url)

    async def _add_sitemap(self):
        """ Add the sitemap to the list of pages to be scraped """
        try:
            sitemap = await self._map_extractor(self._contractor.url)

            for i in ('about', 'contact'):
                attr = getattr(sitemap, i)
                if attr:
                    self._pages.add(str(attr))
        except ValueError as e:
            logger.error(f"Error while extracting site map from {self._contractor.url}: {e}")

    async def __call__(self) -> NoReturn:
        """ Scrape all pages for data.

        As each page is scraped, it is removed from the list of pages to be scraped.
        """
        await self._add_sitemap()

        # scrape pages until all fields are found or all pages are scraped
        logger.info(f"Scraping {self._contractor.url}")
        while self._fields and self._pages:
            page = self._pages.pop()
            await self._scrape_page(page)

    async def _scrape_page(self, url: str) -> NoReturn:
        """ Scrape a single page for data.

        This will fetch the page, then scrape the page for data. If any data is found, the corresponding callback field
        is removed from the list of fields to be scraped.
        """
        try:
            content = await fetch_site(url)
        except ValueError as e:
            logger.error(f"Error while fetching site: {url}. Error: {e}")
            return

        # create a list of scraper coroutines and callbacks
        scrapers = [field.get_scraper() for field in self._fields]
        callbacks = [field.get_callback(self._contractor) for field in self._fields]
        coroutines = [scraper(content, url, callback) for scraper, callback in zip(scrapers, callbacks)]

        # run all scrapers concurrently
        results = await asyncio.gather(*coroutines)

        # remove fields that were found
        _removal = set()
        for result, field in zip(results, self._fields):
            if result:
                _removal.add(field)
        for field in _removal:
            self._fields.remove(field)
