"""Helper functions for MongoDB operations."""

from typing import Any, Dict, Optional
from bson import ObjectId, Binary


def clean_empty_values(value: Any) -> Any:
    """Clean empty strings and invalid data, convert to None.
    
    MongoDB sometimes has empty strings or corrupted data where None would be 
    more appropriate. This function:
    - Converts empty strings to None
    - Converts invalid integers/floats to None
    - Converts standalone integers to strings (e.g., title as int)
    
    Args:
        value: Value to clean.
        
    Returns:
        Cleaned value (None if empty/invalid, original value otherwise).
    """
    if value == "":
        return None
    
    # Handle corrupted integer strings (e.g., '1995è')
    if isinstance(value, str):
        # Try to extract valid integer if string looks like it should be an int
        try:
            # Check if it starts with digits
            import re
            match = re.match(r'^(\d+)', value)
            if match and len(match.group(1)) == len(value):
                # It's a valid integer string, keep it
                return value
            elif match and len(match.group(1)) > 0:
                # It has digits at start but garbage after, extract the int
                return int(match.group(1))
        except (ValueError, AttributeError):
            pass
    
    return value


def convert_objectid_to_str(document: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Convert MongoDB ObjectId fields to strings and clean empty/corrupted values.
    
    This function recursively:
    1. Converts all ObjectId instances to strings
    2. Converts empty strings to None for better validation
    3. Handles corrupted data (e.g., title as int, year as string with garbage)
    
    Args:
        document: MongoDB document dictionary.
        
    Returns:
        Document with ObjectId fields converted to strings and cleaned values.
        
    Example:
        >>> doc = {"_id": ObjectId("507f1f77bcf86cd799439011"), "title": 28, "year": "1995è"}
        >>> convert_objectid_to_str(doc)
        {"_id": "507f1f77bcf86cd799439011", "title": "28", "year": 1995}
    """
    if document is None:
        return None
        
    converted = {}
    for key, value in document.items():
        if isinstance(value, ObjectId):
            converted[key] = str(value)
        elif isinstance(value, Binary):
            # Skip binary embedding data or mark as has_embedding
            # Store metadata instead of the raw binary
            if key in ['plot_embedding', 'plot_embedding_voyage_3_large']:
                converted[f'{key}_available'] = True
                # Skip the actual binary data for now
                continue
            else:
                converted[key] = None
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
            # Special handling for known string fields that might be ints
            if key in ['title', 'plot', 'fullplot'] and isinstance(value, int):
                # Convert to string if it's supposed to be a string field
                converted[key] = str(value)
            else:
                converted[key] = clean_empty_values(value)
    return converted

