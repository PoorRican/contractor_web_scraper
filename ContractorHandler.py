import asyncio
from typing import NoReturn, ClassVar
import warnings

from aiohttp import ClientTimeout

from models import Contractor
from parsers.EmailScraper import EmailScraper
from parsers.AddressScraper import AddressScraper
from parsers.PhoneScraper import PhoneScraper
from utils import fetch_site


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

    async def _scrape(self, contractor: Contractor) -> NoReturn:
        """ Asynchronously process a single contractor.

        This will fetch the contractor site, then scrape the address from the site.
        """
        try:
            content = await fetch_site(contractor.url)
        except ClientTimeout:
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
