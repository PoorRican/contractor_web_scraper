""" Run `ContractorFinder` with `TERMS` """
import asyncio

from ContractorFinder import ContractorFinder

# TODO: move this to an .env file
TERMS: list[str] = ["Pennsylvania residential contractor"]

if __name__ == '__main__':
    finder = ContractorFinder()

    asyncio.run(finder(TERMS))
    print(finder.contractors)
