""" Run `ContractorFinder` with `TERMS` """
import asyncio

from ContractorFinder import ContractorFinder

# TODO: move this to an .env file
TERMS: list[str] = ["Pennsylvania residential contractor"]

if __name__ == '__main__':
    finder = ContractorFinder()

    asyncio.run(finder(TERMS))

    print(f"Found {len(finder.contractors)} contractors")
    for i in finder.contractors:
        print(i)
