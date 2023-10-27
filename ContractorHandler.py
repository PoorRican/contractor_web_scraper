from typing import NoReturn

from models import Contractor


class ContractorHandler:
    """ Top-level observer which receives parsed `Contractor` objects.

    This class is responsible for saving the parsed data to the database,
    then subsequently scraping contractor sites in a separate thread.
    """
    contractors: dict[str, Contractor] = dict()

    def handle_contractors(self, contractors: [Contractor]) -> NoReturn:
        """ Handle contractors that are found by `ContractorFinder`. """
        for contractor in contractors:
            print(f"Handling contractor: {contractor}")
            if contractor.title not in self.contractors.keys():
                self.contractors[contractor.title] = contractor
            else:
                print(f"Encountered duplicate entry '{contractor.title}'")
