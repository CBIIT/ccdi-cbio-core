"""
Pytest hello world example tests.
"""
import pytest
from hello import hello, add


class TestHello:
    """Test cases for the hello function."""
    
    def test_hello_default(self):
        """Test hello with default parameter."""
        assert hello() == "Hello, World!"
    
    def test_hello_with_name(self):
        """Test hello with a custom name."""
        assert hello("Alice") == "Hello, Alice!"
    
    def test_hello_with_empty_string(self):
        """Test hello with an empty string."""
        assert hello("") == "Hello, !"


class TestAdd:
    """Test cases for the add function."""
    
    def test_add_positive_numbers(self):
        """Test adding two positive numbers."""
        assert add(2, 3) == 5
    
    def test_add_negative_numbers(self):
        """Test adding two negative numbers."""
        assert add(-1, -1) == -2
    
    def test_add_mixed_numbers(self):
        """Test adding positive and negative numbers."""
        assert add(10, -3) == 7
    
    def test_add_zero(self):
        """Test adding zero."""
        assert add(5, 0) == 5
        assert add(0, 5) == 5


def test_standalone_example():
    """A standalone test function example."""
    result = hello("pytest")
    assert "pytest" in result
    assert result.startswith("Hello")
