""" Run `SearchHandler` with `TERMS` """
import asyncio
from dotenv import load_dotenv

from handlers import SearchHandler
from ResultsHandler import ResultsHandler
from utils import export_contractors

if __name__ == '__main__':
    load_dotenv()  # load environment variables from .env.

    with open('terms.txt', 'r') as f:
        TERMS: list[str] = f.read().split('\n')

    handler = ResultsHandler()
    finder = SearchHandler(handler.handle_results)

    asyncio.run(finder(TERMS))

    print(f"Found {len(handler.contractors)} contractors")

    export_contractors(handler.contractors)
