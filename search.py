import os
from datetime import datetime
from time import sleep
from typing import Union, ClassVar

import requests

from typedefs import SearchResults, SearchResult

from dotenv import load_dotenv

load_dotenv()


class Search(object):
    _rpm: ClassVar[int] = 3
    """ Number of requests per minute to limit the Bing Search API to. """
    _last_run: ClassVar[Union[None, datetime]] = None

    @classmethod
    def _limit_rate(cls) -> None:
        """ Limit the rate of requests to the Bing Search API.

        If the last call is less than 60 seconds / `_rpm` ago, sleep for the remaining time.
        """
        if cls._last_run is None:
            cls._last_run = datetime.now()
            return
        delta = datetime.now() - cls._last_run
        t = 60 / cls._rpm
        if delta.seconds < t:
            print(f"Rate limit hit. Sleeping for {t - delta.seconds} seconds...")
            sleep(t - delta.seconds)
        cls._last_run = datetime.now()

    @classmethod
    def __call__(cls, query: str, chunk_size: int, offset: int = 0) -> SearchResults:
        """ Wrapper for `googlesearch.search`

        This uses `NUM_RESULTS` as the number of results to fetch.

        Parameters:
            query: search term to use
            chunk_size: number of results to fetch per search
            offset: offset to use for search

        Returns:
            Generator of `SearchResult` objects
        """
        cls._limit_rate()

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
