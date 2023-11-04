from langchain.prompts import PromptTemplate
from langchain.pydantic_v1 import BaseModel, Field, field_validator, ValidationError, HttpUrl
from typing import NoReturn, ClassVar, Callable, Annotated

from typedefs.validity import ValidityParser, Validity
from llm import LLM


class BaseContractor(BaseModel):
    title: Annotated[str, Field(description='Title of the contractor')]
    description: Annotated[str, Field(description='Description of the contractor')]
    URL: Annotated[HttpUrl, Field(description='URL of the contractor homepage')]
    # TODO: add industry field

    @classmethod
    @field_validator('description')
    def is_contractor(cls, v) -> str:
        prompt = PromptTemplate.from_template(
            """Does this description describe an actual construction contractor website? {description}
            
            {format_instructions}
            """,
            partial_variables={'format_instructions': ValidityParser.get_format_instructions()},
            output_parser=ValidityParser
        )
        chain = prompt | LLM | ValidityParser
        response: Validity = chain.invoke(v)
        if response.valid:
            raise ValidationError(f"Invalid URL: {v}")
        return v


class Contractor(object):
    """ Abstraction for parsed contractor data """
    fields: ClassVar[list[str]] = ('title', 'description', 'url', 'phone', 'email', 'address')

    title: str
    description: str
    url: str
    services: list[str] = []
    """ A list of services that the contractor provides """
    address: str = None
    """ A string representing the physical address of the contractor.
    
    If multiple addresses are found, only the first one is used.
    """
    location: str = None
    """ A string which represents what locations are served by the contractor """
    projects: list[str] = []
    """ A list of projects that the contractor has completed.
    
    Eventually, this should be a list of `Project` objects.
    """
    phone: str = None
    """ A string representing the phone number of the contractor.
    
    If multiple phone numbers are found, only the first one is used.
    This cannot be guaranteed to align with the `address` field.
    """
    email: str = None
    """ A string representing the email address of the contractor. """

    def __init__(self, title: str, description: str, url: str):
        self.title = title
        self.description = description
        self.url = url

    @staticmethod
    def from_row(
            title: str,
            description: str,
            url: str,
            phone: str,
            email: str,
            address: str
    ) -> 'Contractor':
        """ Factory to create a `Contractor` object from a CSV row """
        obj = Contractor(title, description, url)
        obj.email = email
        obj.phone = phone
        obj.address = address
        return obj

    def to_row(self) -> dict:
        return {
            'title': self.title,
            'description': self.description,
            'url': self.url,
            'phone': self.phone,
            'email': self.email,
            'address': self.address
        }

    def add_service(self, service: str) -> NoReturn:
        """ Add service to local list """
        if service not in self.services:
            self.services.append(service)

    def set_address(self, address: str) -> NoReturn:
        """ Update address string

        This is to be used as a callback from future scraper classes.
        """
        # TODO: eventually, this should accept a list of addresses
        self.address = address

    def set_location(self, location: str) -> NoReturn:
        """ Update location string

        This is to be used as a callback from future scraper classes.
        """
        self.location = location

    def add_project(self, project: str) -> NoReturn:
        """ Add project to local list

        This is to be used as a callback from future scraper classes.
        """
        if project not in self.projects:
            self.projects.append(project)

    def set_phone(self, phone: str) -> NoReturn:
        """ Update phone string

        This is to be used as a callback from future scraper classes.
        """
        self.phone = phone

    def set_email(self, email: str) -> NoReturn:
        """ Update email string

        This is to be used as a callback from future scraper classes.
        """
        self.email = email

    def __repr__(self) -> str:
        return f"<Contractor: {self.title}; url: {self.url}; description: {self.description}>"

    def pretty(self):
        msg = f"Contractor: {self.title}\n"
        msg += f"URL: {self.url}\n"
        msg += f"Description: {self.description}\n"

        if self.phone:
            msg += f"Phone: {self.phone}\n"
        if self.email:
            msg += f"Email: {self.email}\n"
        if self.address:
            msg += f"Address: {self.address}\n"

        if self.services:
            msg += f"Services: {self.services}\n"
        if self.location:
            msg += f"Location: {self.location}\n"
        if self.projects:
            msg += f"Projects: {self.projects}\n"

        return msg


ContractorCallback = Callable[[str], NoReturn]
""" A callback function to set a `Contractor` attribute. """
