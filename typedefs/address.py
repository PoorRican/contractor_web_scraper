from typing import Annotated

from langchain.pydantic_v1 import BaseModel, Field, validator, ValidationError


class Address(BaseModel):
    street: Annotated[str, Field(description="Street or mailing address for business", min_length=1)]
    city: Annotated[str, Field(description="City", min_length=1)]
    state: Annotated[str, Field(description="State", min_length=1)]
    zip: Annotated[str, Field(description="Zip code", min_length=1)]

    @staticmethod
    def _parsing_fail(v: str) -> bool:
        return 'no address' in v.lower()

    @validator('street')
    @classmethod
    def is_street(cls, v) -> str:
        if cls._parsing_fail(v):
            raise ValidationError("Invalid street")
        return v

    @validator('city')
    @classmethod
    def is_city(cls, v) -> str:
        if cls._parsing_fail(v):
            raise ValidationError("Invalid city")
        return v

    @validator('state')
    @classmethod
    def is_state(cls, v) -> str:
        if cls._parsing_fail(v):
            raise ValidationError("Invalid state")
        return v

    @validator('zip')
    @classmethod
    def is_zip(cls, v) -> str:
        if cls._parsing_fail(v):
            raise ValidationError("Invalid zip")
        return v
