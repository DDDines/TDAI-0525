"""Shared rate limiter instance for the application."""
from slowapi import Limiter
from slowapi.util import get_remote_address


def build_limiter() -> Limiter:
    """Create the shared SlowAPI limiter used by HTTP routes."""
    return Limiter(key_func=get_remote_address)


limiter = build_limiter()
