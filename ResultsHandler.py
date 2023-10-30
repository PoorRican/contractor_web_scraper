import asyncio
from typing import NoReturn, ClassVar

from models import Contractor
from parsers import AddressScraper, EmailScraper, PhoneScraper, SiteCrawler


class ResultsHandler:
    """ Top-level observer which receives parsed `Contractor` objects.

    This class is responsible for saving the parsed data to the database,
    then subsequently scraping contractor sites asynchronously. Eventually, processing should occur in a separate
    thread.

    Attributes:
        contractors: dict of parsed `Contractor` objects
    """
    contractors: dict[str, Contractor] = dict()

    @staticmethod
    async def _scrape(contractor: Contractor) -> NoReturn:
        """ Asynchronously process a single contractor.

        This will fetch the contractor site, then scrape the address from the site.
        """

        crawler = SiteCrawler(contractor)
        await crawler()

    async def handle_results(self, contractors: [Contractor]) -> NoReturn:
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
