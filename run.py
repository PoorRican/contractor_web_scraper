""" Run `SearchParser` with `TERMS` """
import asyncio

from parsers import SearchParser
from ResultsHandler import ResultsHandler

# TODO: move this to an .env file
TERMS: list[str] = ["Pennsylvania residential contractor"]

if __name__ == '__main__':
    handler = ResultsHandler()
    finder = SearchParser(handler.handle_results)

    asyncio.run(finder(TERMS))

    print(f"Found {len(handler.contractors)} contractors")
    for contractor in handler.contractors.values():
        print(contractor.pretty(), end='\n\n')
