""" Run `SearchParser` with `TERMS` """
import asyncio

from parsers import SearchParser
from ResultsHandler import ResultsHandler
from utils import export_contractors

if __name__ == '__main__':

    with open('terms.txt', 'r') as f:
        TERMS: list[str] = f.read().split('\n')

    handler = ResultsHandler()
    finder = SearchParser(handler.handle_results)

    asyncio.run(finder(TERMS))

    print(f"Found {len(handler.contractors)} contractors")

    export_contractors(handler.contractors)
