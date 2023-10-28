import asyncio
from typing import NoReturn, ClassVar

from requests import get, Session
from requests.adapters import HTTPAdapter, Retry
from bs4 import BeautifulSoup, Tag

from models import Contractor
from parsers.AddressScraper import AddressScraper


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

        print(f"Fetching site: {url}")

        s = Session()
        retries = Retry(total=5, backoff_factor=1, status_forcelist=[502, 503, 504])
        s.mount('https://', HTTPAdapter(max_retries=retries))
        content = s.get(url).text

        soup = BeautifulSoup(content, 'html.parser')
        body = soup.find('body')

        # kill all script and media elements
        tags = ('script', 'img')
        for tag in tags:
            for node in body.find_all(tag):
                node.decompose()

        print(f"Fetched site: {url}")

        return body

    async def _scrape(self, contractor: Contractor) -> NoReturn:
        """ Asynchronously process a single contractor.

        This will fetch the contractor site, then scrape the address from the site.
        """
        print(f"Processing contractor: {contractor}")
        content = await self._fetch_site(contractor.url)

        # TODO: all scraping should be awaited by gathering a list of coroutines
        address = await self._address_scraper(content)
        print(f"Found address: {address}")
        # contractor.address = address

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
