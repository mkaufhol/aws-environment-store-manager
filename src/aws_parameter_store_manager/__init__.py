"""AWS Parameter Store Manager - A Python library to manage AWS Parameter Store."""

from .manager import ParameterStoreManager
from .exceptions import ParameterNotFoundError, ParameterAlreadyExists

__version__ = "0.1.0"

__all__ = [
    "ParameterStoreManager",
    "ParameterNotFoundError",
    "ParameterAlreadyExists",
]
