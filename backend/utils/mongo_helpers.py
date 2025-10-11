"""Helper functions for MongoDB operations."""

from typing import Any, Dict, Optional
from bson import ObjectId


def clean_empty_values(value: Any) -> Any:
    """Clean empty strings and convert to None.
    
    MongoDB sometimes has empty strings where None would be more appropriate.
    This function converts empty strings to None for better Pydantic validation.
    
    Args:
        value: Value to clean.
        
    Returns:
        Cleaned value (None if empty string, original value otherwise).
    """
    if value == "":
        return None
    return value


def convert_objectid_to_str(document: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Convert MongoDB ObjectId fields to strings and clean empty values.
    
    This function recursively:
    1. Converts all ObjectId instances to strings
    2. Converts empty strings to None for better validation
    
    Args:
        document: MongoDB document dictionary.
        
    Returns:
        Document with ObjectId fields converted to strings and cleaned values.
        
    Example:
        >>> doc = {"_id": ObjectId("507f1f77bcf86cd799439011"), "name": "John", "age": ""}
        >>> convert_objectid_to_str(doc)
        {"_id": "507f1f77bcf86cd799439011", "name": "John", "age": None}
    """
    if document is None:
        return None
        
    converted = {}
    for key, value in document.items():
        if isinstance(value, ObjectId):
            converted[key] = str(value)
        elif isinstance(value, dict):
            converted[key] = convert_objectid_to_str(value)
        elif isinstance(value, list):
            converted[key] = [
                convert_objectid_to_str(item) if isinstance(item, dict) else
                str(item) if isinstance(item, ObjectId) else
                clean_empty_values(item)
                for item in value
            ]
        else:
            converted[key] = clean_empty_values(value)
    return converted

