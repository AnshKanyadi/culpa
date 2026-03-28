"""JSON serialization helpers for Culpa models."""

import json
from datetime import datetime
from typing import Any
from enum import Enum


class CulpaJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles datetime, enums, and other special types."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, Enum):
            return obj.value
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        if hasattr(obj, "dict"):
            return obj.dict()
        return super().default(obj)


def serialize(obj: Any) -> str:
    """Serialize an object to a JSON string."""
    return json.dumps(obj, cls=CulpaJSONEncoder)


def deserialize(data: str) -> Any:
    """Deserialize a JSON string to a Python object."""
    return json.loads(data)


def to_dict(obj: Any) -> dict:
    """Convert an object to a dictionary."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict"):
        return obj.dict()
    return json.loads(serialize(obj))
