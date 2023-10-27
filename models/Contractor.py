from typing import NoReturn


class Contractor(object):
    """ Abstraction for parsed contractor data """
    title: str
    description: str
    url: str
    services: list[str] = []

    def __init__(self, title: str, description: str, url: str):
        self.title = title
        self.description = description
        self.url = url

    def add_service(self, service: str) -> NoReturn:
        """ Add service to local list """
        if service not in self.services:
            self.services.append(service)
