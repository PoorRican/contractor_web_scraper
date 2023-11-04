from dataclasses import dataclass


@dataclass
class SearchResult:
    title: str
    description: str
    url: str


SearchResults = list[SearchResult]
""" A list of `SearchResult` objects. """
