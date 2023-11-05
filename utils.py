from typing import NoReturn
from urllib.parse import urlparse

from aiohttp_retry import RetryClient

from requests.utils import default_headers
from bs4 import BeautifulSoup, Tag

from typedefs import Contractor


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

    if body is None:
        raise ValueError(f"Retrieved HTML did not contain a body")

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
