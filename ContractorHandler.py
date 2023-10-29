import asyncio
from typing import NoReturn, ClassVar
import warnings

import aiohttp
from aiohttp_retry import RetryClient
from requests import Session, ConnectTimeout
from requests.adapters import HTTPAdapter, Retry
from requests.utils import default_headers
from bs4 import BeautifulSoup, Tag

from models import Contractor
from parsers.EmailScraper import EmailScraper
from parsers.AddressScraper import AddressScraper
from parsers.PhoneScraper import PhoneScraper


class ContractorHandler:
    """ Top-level observer which receives parsed `Contractor` objects.

    This class is responsible for saving the parsed data to the database,
    then subsequently scraping contractor sites asynchronously. Eventually, processing should occur in a separate
    thread.

    Attributes:
        _address_scraper: `AddressScraper` functor to scrape addresses from contractor sites
        contractors: dict of parsed `Contractor` objects
    """
    _address_scraper: ClassVar[AddressScraper] = AddressScraper()
    _phone_scraper: ClassVar[PhoneScraper] = PhoneScraper()
    _email_scraper: ClassVar[EmailScraper] = EmailScraper()
    contractors: dict[str, Contractor] = dict()

    @staticmethod
    async def _fetch_site(url: str) -> Tag:
        """ Asynchronously fetch HTML content from a URL then clean HTML content.

        All <script> and <media> elements are removed from the HTML content.

        There is an internal retry mechanism to handle HTTP errors.

        Parameters:
            url: URL of site to fetch

        Returns:
            `bs4.Tag` object containing the cleaned HTML `body` content
        """
        async with RetryClient() as client:
            # spoof user agent
            headers = default_headers()
            headers.update({'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, '
                                          'like Gecko) Chrome/118.0.0.0 Safari/537.36',
                            'Dnt': '1',
                            'Sec-Ch-Ua': '"Not=A?Brand";v = "99", "Chromium";v = "118"'
                            })
            async with client.get(url, headers=headers) as response:
                content = await response.text()

        soup = BeautifulSoup(content, 'html.parser')
        body = soup.find('body')

        # kill all unnecessary tags
        tags = ('script', 'img', 'style', 'svg', 'video', 'audio', 'picture', 'iframe', 'i', 'source', 'noscript',
                'link', 'meta', 'head', 'canvas', 'button', 'form', 'input', 'textarea', 'select', 'option',
                'label', 'fieldset', 'legend', 'datalist', 'optgroup', 'keygen', 'output', 'progress', 'meter',)
        for tag in tags:
            for node in body.find_all(tag):
                node.decompose()

        return body

    async def _scrape(self, contractor: Contractor) -> NoReturn:
        """ Asynchronously process a single contractor.

        This will fetch the contractor site, then scrape the address from the site.
        """
        try:
            content = await self._fetch_site(contractor.url)
        except ConnectTimeout:
            warnings.warn(f"Timed out while fetching site: {contractor.url}")
            return

        # TODO: all scraping should be awaited by gathering a list of coroutines
        await self._address_scraper(content, contractor.url, contractor.set_address)
        await self._phone_scraper(content, contractor.url, contractor.set_phone)
        await self._email_scraper(content, contractor.url, contractor.set_email)

        if contractor.address is not None:
            print(f"Found address: {contractor.title}: {contractor.address}")

        if contractor.phone is not None:
            print(f"Found phone number: {contractor.title}: {contractor.phone}")

        if contractor.email is not None:
            print(f"Found email: {contractor.title}: {contractor.email}")

    async def handle_contractors(self, contractors: [Contractor]) -> NoReturn:
        """ Handle contractors that are found by `SearchParser`.

        This will save the contractors to internal storage, then scrape the contractor sites asynchronously.

        Parameters:
            contractors: list of `Contractor` objects to handle
        """
        routines = []
        for contractor in contractors:
            if contractor.title not in self.contractors.keys():
                self.contractors[contractor.title] = contractor
                routines.append(self._scrape(contractor))
            else:
                print(f"Encountered duplicate entry '{contractor.title}'")

        await asyncio.gather(*routines)
