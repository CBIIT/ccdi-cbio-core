"""
Simple hello world module for pytest example.
"""

def hello(name: str = "World") -> str:
    """
    Returns a greeting message.
    
    Args:
        name: The name to greet (default: "World")
    
    Returns:
        A greeting string
    """
    return f"Hello, {name}!"


def add(a: int, b: int) -> int:
    """
    Adds two numbers together.
    
    Args:
        a: First number
        b: Second number
    
    Returns:
        Sum of a and b
    """
    return a + b
