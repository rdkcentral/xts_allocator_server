"""Tests for input validation utilities."""

import pytest
from input_validation import (
    ValidationError,
    validate_email,
    validate_string,
    validate_integer,
    validate_tags,
    validate_user_data,
    sanitize_json_string
)


class TestEmailValidation:
    """Test email validation."""
    
    def test_valid_email(self):
        """Test valid email formats."""
        assert validate_email("user@example.com") == "user@example.com"
        assert validate_email("test.user+tag@example.co.uk") == "test.user+tag@example.co.uk"
        assert validate_email("  USER@EXAMPLE.COM  ") == "user@example.com"  # Lowercase and trim
    
    def test_invalid_email_format(self):
        """Test invalid email formats."""
        with pytest.raises(ValidationError, match="Invalid email format"):
            validate_email("notanemail")
        
        with pytest.raises(ValidationError, match="Invalid email format"):
            validate_email("@example.com")
        
        with pytest.raises(ValidationError, match="Invalid email format"):
            validate_email("user@")
    
    def test_email_too_long(self):
        """Test email length limit."""
        long_email = "a" * 250 + "@example.com"
        with pytest.raises(ValidationError, match="Email address too long"):
            validate_email(long_email)
    
    def test_email_required(self):
        """Test required email validation."""
        with pytest.raises(ValidationError, match="Email is required"):
            validate_email("")
        
        with pytest.raises(ValidationError, match="Email is required"):
            validate_email(None)
    
    def test_email_optional(self):
        """Test optional email validation."""
        assert validate_email("", required=False) is None
        assert validate_email(None, required=False) is None


class TestStringValidation:
    """Test string validation."""
    
    def test_valid_string(self):
        """Test valid string input."""
        assert validate_string("test", "field") == "test"
        assert validate_string("  test  ", "field") == "test"  # Trimmed
    
    def test_string_length_limits(self):
        """Test string length constraints."""
        # Too short
        with pytest.raises(ValidationError, match="must be at least"):
            validate_string("ab", "field", min_length=3)
        
        # Too long
        with pytest.raises(ValidationError, match="must be at most"):
            validate_string("a" * 100, "field", max_length=50)
    
    def test_string_pattern(self):
        """Test string pattern matching."""
        # Valid pattern
        assert validate_string("user123", "username", pattern=r'^[a-z0-9]+$') == "user123"
        
        # Invalid pattern
        with pytest.raises(ValidationError, match="format is invalid"):
            validate_string("user@123", "username", pattern=r'^[a-z0-9]+$')
    
    def test_string_required(self):
        """Test required string validation."""
        with pytest.raises(ValidationError, match="is required"):
            validate_string("", "field", required=True)
    
    def test_string_optional(self):
        """Test optional string validation."""
        assert validate_string("", "field", required=False) is None
        assert validate_string(None, "field", required=False) is None


class TestIntegerValidation:
    """Test integer validation."""
    
    def test_valid_integer(self):
        """Test valid integer input."""
        assert validate_integer(42, "field") == 42
        assert validate_integer("42", "field") == 42
    
    def test_invalid_integer(self):
        """Test invalid integer input."""
        with pytest.raises(ValidationError, match="must be an integer"):
            validate_integer("not a number", "field")
        
        with pytest.raises(ValidationError, match="must be an integer"):
            validate_integer(3.14, "field")
    
    def test_integer_range(self):
        """Test integer range constraints."""
        # Valid range
        assert validate_integer(5, "field", min_value=1, max_value=10) == 5
        
        # Below min
        with pytest.raises(ValidationError, match="must be at least"):
            validate_integer(0, "field", min_value=1)
        
        # Above max
        with pytest.raises(ValidationError, match="must be at most"):
            validate_integer(100, "field", max_value=50)
    
    def test_integer_optional(self):
        """Test optional integer validation."""
        assert validate_integer(None, "field", required=False) is None
        assert validate_integer("", "field", required=False) is None


class TestTagsValidation:
    """Test tags validation."""
    
    def test_valid_tags_list(self):
        """Test valid tags as list."""
        tags = validate_tags(["4k", "hdr", "uk"])
        assert tags == ["4k", "hdr", "uk"]
    
    def test_valid_tags_string(self):
        """Test valid tags as comma-separated string."""
        tags = validate_tags("4k, hdr, uk")
        assert tags == ["4k", "hdr", "uk"]
    
    def test_tags_lowercase(self):
        """Test tags are converted to lowercase."""
        tags = validate_tags("4K, HDR, UK")
        assert tags == ["4k", "hdr", "uk"]
    
    def test_tags_deduplicated(self):
        """Test duplicate tags are removed."""
        tags = validate_tags(["4k", "hdr", "4k", "uk"])
        assert tags == ["4k", "hdr", "uk"]
    
    def test_tags_max_count(self):
        """Test maximum tag count."""
        with pytest.raises(ValidationError, match="Maximum.*tags allowed"):
            validate_tags([f"tag{i}" for i in range(25)], max_tags=20)
    
    def test_tag_max_length(self):
        """Test maximum tag length."""
        with pytest.raises(ValidationError, match="Tag too long"):
            validate_tags(["a" * 100], max_length=50)
    
    def test_tag_invalid_characters(self):
        """Test tags with invalid characters."""
        with pytest.raises(ValidationError, match="invalid characters"):
            validate_tags(["valid-tag", "invalid tag with spaces"])
    
    def test_empty_tags(self):
        """Test empty tags."""
        assert validate_tags([]) == []
        assert validate_tags("") == []
        assert validate_tags(None) == []


class TestUserDataValidation:
    """Test user data validation."""
    
    def test_valid_user_data(self):
        """Test valid user data."""
        user_data = {
            "email": "user@example.com",
            "username": "testuser",
            "name": "Test User"
        }
        validated = validate_user_data(user_data)
        assert validated["email"] == "user@example.com"
        assert validated["username"] == "testuser"
        assert validated["name"] == "Test User"
    
    def test_user_data_email_required(self):
        """Test email is required."""
        with pytest.raises(ValidationError, match="email is required"):
            validate_user_data({"username": "test"})
    
    def test_user_data_username_defaults(self):
        """Test username defaults to email prefix."""
        validated = validate_user_data({"email": "user@example.com"})
        assert validated["username"] == "user"
    
    def test_user_data_invalid_username(self):
        """Test invalid username characters."""
        with pytest.raises(ValidationError):
            validate_user_data({
                "email": "user@example.com",
                "username": "invalid username!"
            })
    
    def test_user_data_not_dict(self):
        """Test non-dict user data."""
        with pytest.raises(ValidationError, match="must be a dictionary"):
            validate_user_data("not a dict")


class TestJSONStringSanitization:
    """Test JSON string sanitization."""
    
    def test_sanitize_normal_string(self):
        """Test normal string sanitization."""
        assert sanitize_json_string("test") == "test"
        assert sanitize_json_string("  test  ") == "test"
    
    def test_sanitize_long_string(self):
        """Test extremely long string is rejected."""
        with pytest.raises(ValidationError, match="String too long"):
            sanitize_json_string("a" * 20000, max_length=10000)
    
    def test_sanitize_non_string(self):
        """Test non-string is converted."""
        assert sanitize_json_string(123) == "123"
        assert sanitize_json_string(True) == "True"
