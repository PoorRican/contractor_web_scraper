import asyncio
import warnings
from enum import Enum
from typing import NoReturn

from aiohttp import ClientTimeout

from models import Contractor
from parsers import AddressScraper, PhoneScraper, EmailScraper
from parsers.TextSnippetScraper import TextSnippetScraper
from typedefs import ContractorCallback
from utils import fetch_site


class _FieldType(Enum):
    """ An enum representing a field type to be scraped.

    This enum is used to determine which scraper and callback to use for a given field. Additionally, it is used to
    determine which fields are have not been scraped for a given `Contractor` object.
    """
    address = 'address'
    email = 'email'
    phone = 'phone'

    def get_scraper(self) -> TextSnippetScraper:
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
        """ Return the corresponding callback for this field type """
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
    _contractor: Contractor

    _pages: set[str] = set()
    """ A set of URLs to be scraped """

    _fields: set[_FieldType] = default_fields()
    """ A set of fields that are lacking by the `Contractor` object """

    def __init__(self, contractor: Contractor):
        """ Initialize the `SiteCrawler` object.

        A list of pages to be scraped is initialized with the contractor's URL.
        """
        self._contractor = contractor

        # TODO: populate pages from contractor site (home -> about -> contact -> services -> projects -> ...)
        self._pages.add(contractor.url)

    async def __call__(self) -> NoReturn:
        """ Scrape all pages for data.

        As each page is scraped, it is removed from the list of pages to be scraped.
        """
        while self._fields and self._pages:
            page = self._pages.pop()
            await self._scrape_page(page)

    async def _scrape_page(self, url: str) -> NoReturn:
        """ Scrape a single page for data.

        This will fetch the page, then scrape the page for data. If any data is found, the corresponding callback will
        be called and the field is removed from the list of fields to be scraped.
        """
        try:
            content = await fetch_site(url)
        except ClientTimeout:
            warnings.warn(f"Timed out while fetching site: {url}")
            return

        # create a list of scraper coroutines and callbacks
        scrapers = [field.get_scraper() for field in self._fields]
        callbacks = [field.get_callback(self._contractor) for field in self._fields]
        coroutines = [scrapers[i](content, url, callbacks[i]) for i in range(len(scrapers))]

        # run all scrapers concurrently
        results = await asyncio.gather(*coroutines)

        # remove fields that were found
        _removal = set()
        for result, field in zip(results, self._fields):
            if result:
                _removal.add(field)
        for field in _removal:
            self._fields.remove(field)
