"""
Authentication and token helper for backend services.
"""

def generate_session_token(user_id: str, role: str = "user") -> str:
    """Generates a pseudo session token."""
    if not user_id:
        raise ValueError("user_id cannot be empty")
    return f"tok_{role}_{user_id}_secret"

def verify_session_token(token: str) -> bool:
    """Validates session token format."""
    if not token or not token.startswith("tok_"):
        return False
    parts = token.split("_")
    return len(parts) >= 4
