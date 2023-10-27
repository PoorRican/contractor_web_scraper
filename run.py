""" Run `ContractorFinder` with `TERMS` """
import asyncio

from ContractorFinder import ContractorFinder
from ContractorHandler import ContractorHandler

# TODO: move this to an .env file
TERMS: list[str] = ["Pennsylvania residential contractor"]

if __name__ == '__main__':
    handler = ContractorHandler()
    finder = ContractorFinder(handler.handle_contractors)

    asyncio.run(finder(TERMS))

    print(f"Found {len(handler.contractors)} contractors")
