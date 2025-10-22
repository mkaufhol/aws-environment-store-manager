from typing import TypedDict


class AWSTag(TypedDict):
    Key: str
    Value: str


class Parameter(TypedDict):
    Name: str
    Type: str
    Value: str
    Version: int
    LastModifiedDate: str
    ARN: str
    DataType: str


class ParameterResponse(TypedDict):
    Parameter: Parameter
