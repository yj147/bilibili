"""Request/Response schemas for Config endpoints."""
from pydantic import BaseModel
from typing import Any


class ConfigValue(BaseModel):
    value: Any
