# coding: utf-8

"""
    FastAPI

    No description provided (generated by Openapi Generator https://github.com/openapitools/openapi-generator)

    The version of the OpenAPI document: 0.1.0
    Generated by OpenAPI Generator (https://openapi-generator.tech)

    Do not edit the class manually.
"""  # noqa: E501


from __future__ import annotations
from inspect import getfullargspec
import json
import pprint
import re  # noqa: F401
from pydantic import BaseModel, ConfigDict, Field, StrictStr, ValidationError, field_validator
from typing import Optional
from nearai.openapi_client.models.chat_completions_request import ChatCompletionsRequest
from nearai.openapi_client.models.completions_request import CompletionsRequest
from nearai.openapi_client.models.embeddings_request import EmbeddingsRequest
from nearai.openapi_client.models.image_generation_request import ImageGenerationRequest
from typing import Union, Any, List, Set, TYPE_CHECKING, Optional, Dict
from typing_extensions import Literal, Self
from pydantic import Field

REQUEST_ANY_OF_SCHEMAS = ["ChatCompletionsRequest", "CompletionsRequest", "EmbeddingsRequest", "ImageGenerationRequest"]

class Request(BaseModel):
    """
    Request
    """

    # data type: ChatCompletionsRequest
    anyof_schema_1_validator: Optional[ChatCompletionsRequest] = None
    # data type: CompletionsRequest
    anyof_schema_2_validator: Optional[CompletionsRequest] = None
    # data type: EmbeddingsRequest
    anyof_schema_3_validator: Optional[EmbeddingsRequest] = None
    # data type: ImageGenerationRequest
    anyof_schema_4_validator: Optional[ImageGenerationRequest] = None
    if TYPE_CHECKING:
        actual_instance: Optional[Union[ChatCompletionsRequest, CompletionsRequest, EmbeddingsRequest, ImageGenerationRequest]] = None
    else:
        actual_instance: Any = None
    any_of_schemas: Set[str] = { "ChatCompletionsRequest", "CompletionsRequest", "EmbeddingsRequest", "ImageGenerationRequest" }

    model_config = {
        "validate_assignment": True,
        "protected_namespaces": (),
    }

    def __init__(self, *args, **kwargs) -> None:
        if args:
            if len(args) > 1:
                raise ValueError("If a position argument is used, only 1 is allowed to set `actual_instance`")
            if kwargs:
                raise ValueError("If a position argument is used, keyword arguments cannot be used.")
            super().__init__(actual_instance=args[0])
        else:
            super().__init__(**kwargs)

    @field_validator('actual_instance')
    def actual_instance_must_validate_anyof(cls, v):
        instance = Request.model_construct()
        error_messages = []
        # validate data type: ChatCompletionsRequest
        if not isinstance(v, ChatCompletionsRequest):
            error_messages.append(f"Error! Input type `{type(v)}` is not `ChatCompletionsRequest`")
        else:
            return v

        # validate data type: CompletionsRequest
        if not isinstance(v, CompletionsRequest):
            error_messages.append(f"Error! Input type `{type(v)}` is not `CompletionsRequest`")
        else:
            return v

        # validate data type: EmbeddingsRequest
        if not isinstance(v, EmbeddingsRequest):
            error_messages.append(f"Error! Input type `{type(v)}` is not `EmbeddingsRequest`")
        else:
            return v

        # validate data type: ImageGenerationRequest
        if not isinstance(v, ImageGenerationRequest):
            error_messages.append(f"Error! Input type `{type(v)}` is not `ImageGenerationRequest`")
        else:
            return v

        if error_messages:
            # no match
            raise ValueError("No match found when setting the actual_instance in Request with anyOf schemas: ChatCompletionsRequest, CompletionsRequest, EmbeddingsRequest, ImageGenerationRequest. Details: " + ", ".join(error_messages))
        else:
            return v

    @classmethod
    def from_dict(cls, obj: Dict[str, Any]) -> Self:
        return cls.from_json(json.dumps(obj))

    @classmethod
    def from_json(cls, json_str: str) -> Self:
        """Returns the object represented by the json string"""
        instance = cls.model_construct()
        error_messages = []
        # anyof_schema_1_validator: Optional[ChatCompletionsRequest] = None
        try:
            instance.actual_instance = ChatCompletionsRequest.from_json(json_str)
            return instance
        except (ValidationError, ValueError) as e:
             error_messages.append(str(e))
        # anyof_schema_2_validator: Optional[CompletionsRequest] = None
        try:
            instance.actual_instance = CompletionsRequest.from_json(json_str)
            return instance
        except (ValidationError, ValueError) as e:
             error_messages.append(str(e))
        # anyof_schema_3_validator: Optional[EmbeddingsRequest] = None
        try:
            instance.actual_instance = EmbeddingsRequest.from_json(json_str)
            return instance
        except (ValidationError, ValueError) as e:
             error_messages.append(str(e))
        # anyof_schema_4_validator: Optional[ImageGenerationRequest] = None
        try:
            instance.actual_instance = ImageGenerationRequest.from_json(json_str)
            return instance
        except (ValidationError, ValueError) as e:
             error_messages.append(str(e))

        if error_messages:
            # no match
            raise ValueError("No match found when deserializing the JSON string into Request with anyOf schemas: ChatCompletionsRequest, CompletionsRequest, EmbeddingsRequest, ImageGenerationRequest. Details: " + ", ".join(error_messages))
        else:
            return instance

    def to_json(self) -> str:
        """Returns the JSON representation of the actual instance"""
        if self.actual_instance is None:
            return "null"

        if hasattr(self.actual_instance, "to_json") and callable(self.actual_instance.to_json):
            return self.actual_instance.to_json()
        else:
            return json.dumps(self.actual_instance)

    def to_dict(self) -> Optional[Union[Dict[str, Any], ChatCompletionsRequest, CompletionsRequest, EmbeddingsRequest, ImageGenerationRequest]]:
        """Returns the dict representation of the actual instance"""
        if self.actual_instance is None:
            return None

        if hasattr(self.actual_instance, "to_dict") and callable(self.actual_instance.to_dict):
            return self.actual_instance.to_dict()
        else:
            return self.actual_instance

    def to_str(self) -> str:
        """Returns the string representation of the actual instance"""
        return pprint.pformat(self.model_dump())


