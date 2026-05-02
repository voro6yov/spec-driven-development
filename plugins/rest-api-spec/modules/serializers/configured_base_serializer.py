from pydantic import BaseModel, ConfigDict

from .json_utils import to_camel

__all__ = ["ConfiguredResponseSerializer", "ConfiguredRequestSerializer"]


class ConfiguredRequestSerializer(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        serialize_by_alias=True,
        validate_by_name=True,
        validate_by_alias=True,
        use_enum_values=True,
        str_strip_whitespace=True,
    )


class ConfiguredResponseSerializer(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
        validate_by_alias=True,
        serialize_by_alias=True,
        use_enum_values=True,
    )
