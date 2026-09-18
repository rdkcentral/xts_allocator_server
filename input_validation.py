"""
Input validation utilities for API endpoints.

Provides validation for common input patterns to prevent injection attacks
and ensure data integrity.
"""

import re
from typing import Any, Dict, Optional, List


class ValidationError(Exception):
    """Raised when input validation fails."""
    pass


def validate_email(email: str, required: bool = True) -> Optional[str]:
    """
    Validate email address format.
    
    Args:
        email: Email address to validate
        required: Whether email is required (default: True)
        
    Returns:
        Sanitized email or None if not required and empty
        
    Raises:
        ValidationError: If email format is invalid
    """
    if not email:
        if required:
            raise ValidationError("Email is required")
        return None
    
    # Normalize first: strip whitespace and lowercase
    email = email.strip().lower()
    
    if len(email) > 254:  # RFC 5321
        raise ValidationError("Email address too long (max 254 characters)")
    
    # Basic email regex (not perfect but catches common issues)
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        raise ValidationError(f"Invalid email format: {email}")
    
    return email


def validate_string(value: str, field_name: str, min_length: int = 1, 
                   max_length: int = 255, pattern: Optional[str] = None,
                   required: bool = True) -> Optional[str]:
    """
    Validate string input with length and pattern constraints.
    
    Args:
        value: String to validate
        field_name: Name of field (for error messages)
        min_length: Minimum length (default: 1)
        max_length: Maximum length (default: 255)
        pattern: Optional regex pattern to match
        required: Whether field is required
        
    Returns:
        Sanitized string or None if not required and empty
        
    Raises:
        ValidationError: If validation fails
    """
    if not value or (isinstance(value, str) and not value.strip()):
        if required:
            raise ValidationError(f"{field_name} is required")
        return None
    
    value = str(value).strip()
    
    if len(value) < min_length:
        raise ValidationError(
            f"{field_name} must be at least {min_length} characters"
        )
    
    if len(value) > max_length:
        raise ValidationError(
            f"{field_name} must be at most {max_length} characters (got {len(value)})"
        )
    
    if pattern and not re.match(pattern, value):
        raise ValidationError(
            f"{field_name} format is invalid"
        )
    
    return value


def validate_integer(value: Any, field_name: str, min_value: Optional[int] = None,
                    max_value: Optional[int] = None, required: bool = True) -> Optional[int]:
    """
    Validate integer input with range constraints.
    
    Args:
        value: Value to validate
        field_name: Name of field (for error messages)
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        required: Whether field is required
        
    Returns:
        Integer value or None if not required and empty
        
    Raises:
        ValidationError: If validation fails
    """
    if value is None or value == "":
        if required:
            raise ValidationError(f"{field_name} is required")
        return None
    
    # Reject floats explicitly (int(3.14) would succeed)
    if isinstance(value, float):
        raise ValidationError(f"{field_name} must be an integer")
    
    try:
        int_value = int(value)
    except (ValueError, TypeError):
        raise ValidationError(f"{field_name} must be an integer")
    
    if min_value is not None and int_value < min_value:
        raise ValidationError(
            f"{field_name} must be at least {min_value} (got {int_value})"
        )
    
    if max_value is not None and int_value > max_value:
        raise ValidationError(
            f"{field_name} must be at most {max_value} (got {int_value})"
        )
    
    return int_value


def validate_tags(tags: Any, max_tags: int = 20, max_length: int = 50) -> List[str]:
    """
    Validate and sanitize device tags.
    
    Args:
        tags: Tags as list or comma-separated string
        max_tags: Maximum number of tags allowed
        max_length: Maximum length per tag
        
    Returns:
        List of sanitized tags
        
    Raises:
        ValidationError: If validation fails
    """
    if not tags:
        return []
    
    # Convert to list if string
    if isinstance(tags, str):
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    elif isinstance(tags, list):
        tag_list = [str(t).strip() for t in tags if t]
    else:
        raise ValidationError("Tags must be a list or comma-separated string")
    
    if len(tag_list) > max_tags:
        raise ValidationError(f"Maximum {max_tags} tags allowed (got {len(tag_list)})")
    
    # Validate each tag
    sanitized_tags = []
    tag_pattern = r'^[a-zA-Z0-9_-]+$'
    
    for tag in tag_list:
        if len(tag) > max_length:
            raise ValidationError(f"Tag too long: '{tag}' (max {max_length} characters)")
        
        if not re.match(tag_pattern, tag):
            raise ValidationError(
                f"Tag contains invalid characters: '{tag}' "
                f"(use only letters, numbers, underscore, hyphen)"
            )
        
        sanitized_tags.append(tag.lower())
    
    # Remove duplicates while preserving order
    seen = set()
    unique_tags = []
    for tag in sanitized_tags:
        if tag not in seen:
            seen.add(tag)
            unique_tags.append(tag)
    
    return unique_tags


def validate_user_data(user_data: Dict[str, Any]) -> Dict[str, str]:
    """
    Validate user data from allocation request.
    
    Args:
        user_data: Dictionary with user information
        
    Returns:
        Dictionary with validated user data
        
    Raises:
        ValidationError: If validation fails
    """
    if not isinstance(user_data, dict):
        raise ValidationError("User data must be a dictionary")
    
    validated = {}
    
    # Email (required)
    if "email" not in user_data:
        raise ValidationError("User email is required")
    validated["email"] = validate_email(user_data["email"], required=True)
    
    # Username (optional, defaults to email prefix)
    username = user_data.get("username")
    if username:
        validated["username"] = validate_string(
            username, "username", min_length=1, max_length=50,
            pattern=r'^[a-zA-Z0-9._-]+$', required=False
        )
    else:
        # Default to email prefix
        validated["username"] = validated["email"].split("@")[0]
    
    # Name (optional)
    name = user_data.get("name")
    if name:
        validated["name"] = validate_string(
            name, "name", min_length=1, max_length=100, required=False
        )
    
    return validated


def sanitize_json_string(value: str, max_length: int = 10000) -> str:
    """
    Sanitize string for JSON storage (prevent extremely large inputs).
    
    Args:
        value: String to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized string
        
    Raises:
        ValidationError: If string exceeds max length
    """
    if not isinstance(value, str):
        value = str(value)
    
    if len(value) > max_length:
        raise ValidationError(
            f"String too long: {len(value)} characters (max {max_length})"
        )
    
    return value.strip()
