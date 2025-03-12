import re
from typing import Annotated

from fastapi import Form, HTTPException
from nearai.shared.client_config import IDENTIFIER_PATTERN
from pydantic import AfterValidator, BaseModel


def valid_identifier(identifier: str) -> str:
    result = IDENTIFIER_PATTERN.match(identifier)
    if result is None:
        raise HTTPException(
            status_code=400, detail=f"Invalid identifier: {repr(identifier)}. Should match {IDENTIFIER_PATTERN.pattern}"
        )
    return result[0]


class EntryLocation(BaseModel):
    namespace: Annotated[str, AfterValidator(valid_identifier)]
    name: Annotated[str, AfterValidator(valid_identifier)]
    version: Annotated[str, AfterValidator(valid_identifier)]

    @staticmethod
    def from_str(entry: str) -> "EntryLocation":
        """Creates a location from a string `entry` in the format namespace/name/version."""
        pattern = re.compile("^(?P<namespace>[^/]+)/(?P<name>[^/]+)/(?P<version>[^/]+)$")
        match = pattern.match(entry)

        if match is None:
            raise ValueError(f"Invalid entry format: {entry}. Should have the format <namespace>/<name>/<version>")

        return EntryLocation(
            namespace=match.group("namespace"),
            name=match.group("name"),
            version=match.group("version"),
        )

    def to_str(self) -> str:
        """Returns the location as a string in the format namespace/name/version."""
        return f"{self.namespace}/{self.name}/{self.version}"

    @classmethod
    def as_form(cls, namespace: str = Form(...), name: str = Form(...), version: str = Form(...)):
        """Creates a location from form data."""
        return cls(namespace=namespace, name=name, version=version)
