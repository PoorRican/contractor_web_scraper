""" Run `SearchParser` with `TERMS` """
import asyncio

from parsers import SearchParser
from ContractorHandler import ContractorHandler

# TODO: move this to an .env file
TERMS: list[str] = ["Pennsylvania residential contractor"]

if __name__ == '__main__':
    handler = ContractorHandler()
    finder = SearchParser(handler.handle_contractors)

    asyncio.run(finder(TERMS))

    print(f"Found {len(handler.contractors)} contractors")
