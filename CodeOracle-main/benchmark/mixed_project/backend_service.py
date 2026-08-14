"""
Backend service handling user operations.
"""
from auth_helper import generate_session_token, verify_session_token


class BackendService:
    def __init__(self, service_name: str = "AuthAPI"):
        self.service_name = service_name
        self.active_sessions = {}

    def login(self, user_id: str, role: str = "user") -> str:
        token = generate_session_token(user_id, role)
        self.active_sessions[user_id] = token
        return token

    def is_authenticated(self, token: str) -> bool:
        return verify_session_token(token)
