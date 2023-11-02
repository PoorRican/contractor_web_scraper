import os
from time import sleep

import requests

from typedefs import SearchResults, SearchResult

from dotenv import load_dotenv

load_dotenv()


def perform_search(query: str, chunk_size: int, offset: int = 0) -> SearchResults:
    """ Wrapper for `googlesearch.search`

    This uses `NUM_RESULTS` as the number of results to fetch.

    Parameters:
        query: search term to use
        chunk_size: number of results to fetch per search
        offset: offset to use for search

    Returns:
        Generator of `SearchResult` objects
    """
    endpoint = 'https://api.bing.microsoft.com/v7.0/search'
    subscription_key = os.environ['BING_SEARCH_V7_SUBSCRIPTION_KEY']

    headers = {'Ocp-Apim-Subscription-Key': subscription_key}
    mkt = 'en-US'
    params = {'q': query, 'mkt': mkt, 'responseFilters': 'webpages', 'count': chunk_size, 'offset': offset}
    response = requests.get(endpoint, headers=headers, params=params)
    response.raise_for_status()
    data = response.json()

    results = []
    for result in data['webPages']['value']:
        results.append(SearchResult(result['name'], result['snippet'], result['url']))
    return results
