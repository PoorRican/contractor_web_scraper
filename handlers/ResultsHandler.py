import asyncio
from csv import DictReader, DictWriter
from os.path import exists
from typing import NoReturn

from log import logger
from typedefs import Contractor
from .SiteCrawler import SiteCrawler


FILENAME = 'contractors.csv'


class ResultsHandler:
    """ Top-level observer which receives parsed `Contractor` objects.

    This class is for handling parsed `Contractor` objects. It is responsible for saving the contractors to local
    storage, reading/writing the CSV file, and scraping the contractor sites.

    Parsing of the contractor sites is done asynchronously. Ideally, processing should be done in parallel.

    Attributes:
        contractors: dict of parsed `Contractor` objects
    """
    contractors: dict[str, Contractor] = dict()

    def __init__(self):
        self.load()

    @staticmethod
    async def _scrape(contractor: Contractor) -> NoReturn:
        """ Asynchronously process a single contractor by using the `SiteCrawler` functor.

        Parameters:
            contractor: `Contractor` object to process
        """

        crawler = SiteCrawler(contractor)
        await crawler()

    async def handle_results(self, contractors: [Contractor]) -> NoReturn:
        """ Handle contractors that are found by `SearchHandler`.

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
                logger.debug(f"Encountered duplicate entry '{contractor.title}'")

        await asyncio.gather(*routines)
        self.save()

    def load(self) -> NoReturn:
        if exists(FILENAME):
            self._read()
            logger.info(f"Read {len(self.contractors)} objects from local storage!")
        else:
            logger.info(f"Local storage '{FILENAME}' does not exist. Starting database from scratch!")

    def save(self) -> NoReturn:
        self._write()
        logger.info(f"Saved {len(self.contractors)} objects to local storage!")

    def _read(self):
        """ load parsed contractors from local CSV file """
        with open(FILENAME, 'r') as f:
            reader = DictReader(f, fieldnames=Contractor.fields())
            _ = reader.__next__()       # throw out the header row
            for row in reader:
                contractor = Contractor.construct(**row)
                self.contractors[contractor.title] = contractor

    def _write(self):
        """ write parsed contractors to local CSV file """
        with open(FILENAME, 'w') as f:
            writer = DictWriter(f, fieldnames=Contractor.fields())
            writer.writeheader()
            for contractor in self.contractors.values():
                writer.writerow(contractor.dict())
