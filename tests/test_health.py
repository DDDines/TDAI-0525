import asyncio
from Backend.main import health_check


def test_health_check():
    result = asyncio.run(health_check())
    assert result == {"status": "ok"}
