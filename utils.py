import os
from typing import NoReturn
from urllib.parse import urlparse

from aiohttp_retry import RetryClient
import requests
from dotenv import load_dotenv

from requests.utils import default_headers
from bs4 import BeautifulSoup, Tag

from models import Contractor
from typedefs import SearchResult, SearchResults

load_dotenv()


async def fetch_site(url: str) -> Tag:
    """ Asynchronously fetch HTML content from a URL then clean HTML content.

    All <script> and <media> elements are removed from the HTML content.

    There is an internal retry mechanism to handle HTTP errors.

    Parameters:
        url: URL of site to fetch

    Returns:
        `bs4.Tag` object containing the cleaned HTML `body` content
    """
    async with RetryClient() as client:
        # spoof user agent
        headers = default_headers()
        headers.update({'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, '
                                      'like Gecko) Chrome/118.0.0.0 Safari/537.36',
                        'Dnt': '1',
                        'Sec-Ch-Ua': '"Not=A?Brand";v = "99", "Chromium";v = "118"'
                        })
        async with client.get(url, headers=headers) as response:
            content = await response.text()

    soup = BeautifulSoup(content, 'html.parser')
    body = soup.find('body')

    # kill all unnecessary tags
    tags = ('script', 'img', 'style', 'svg', 'video', 'audio', 'picture', 'iframe', 'i', 'source', 'noscript',
            'link', 'meta', 'head', 'canvas', 'button', 'form', 'input', 'textarea', 'select', 'option',
            'label', 'fieldset', 'legend', 'datalist', 'optgroup', 'keygen', 'output', 'progress', 'meter',)
    for tag in tags:
        for node in body.find_all(tag):
            node.decompose()

    return body


def strip_html_attrs(content: Tag) -> Tag:
    """ Preprocess HTML content by removing all HTML attributes from tags.

    This is used to remove all superfluous data and significantly reduce the number of tokens in the content.

    Parameters:
        content: HTML content to preprocess

    Returns:
        `bs4.Tag` object containing the cleaned HTML content
    """
    for tag in content.find_all(True):
        tag.attrs = {}
    return content


def export_contractors(contractors: dict[str, Contractor]) -> NoReturn:
    with open('results.txt', 'w') as f:
        for contractor in contractors.values():
            pretty = contractor.pretty()
            f.write(pretty)
            f.write('\n\n')


def strip_url(url: str) -> str:
    """ Strip URL of all query parameters and path.

    Parameters:
        url: URL to strip

    Returns:
        URL with all query parameters and path removed
    """
    return urlparse(url)._replace(path='')._replace(params='').geturl()


def _perform_search(query: str, offset: int = 0) -> SearchResults:
    """ Wrapper for `googlesearch.search`

    This uses `NUM_RESULTS` as the number of results to fetch.

    Parameters:
        query: search term to use

    Returns:
        Generator of `SearchResult` objects
    """
    endpoint = 'https://api.bing.microsoft.com/v7.0/search'
    subscription_key = os.environ['BING_SEARCH_V7_SUBSCRIPTION_KEY']

    headers = {'Ocp-Apim-Subscription-Key': subscription_key}
    mkt = 'en-US'
    params = {'q': query, 'mkt': mkt, 'responseFilters': 'webpages', 'count': 25, 'offset': offset}
    response = requests.get(endpoint, headers=headers, params=params)
    response.raise_for_status()
    data = response.json()

    results = []
    for result in data['webPages']['value']:
        results.append(SearchResult(result['name'], result['snippet'], result['url']))
    return results


def perform_search(query: str, num_results: int = 100) -> SearchResults:
    assert num_results % 25 == 0, "num_results must be a multiple of 25"

    print(f"\nFetching search for '{query}'")

    results = []
    for offset in range(0, num_results, 25):
        results.extend(_perform_search(query, offset))
    return results
