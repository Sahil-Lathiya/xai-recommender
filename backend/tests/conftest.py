import asyncio
import pytest


@pytest.fixture(scope="session")
def event_loop():
    """Single event loop for the entire test session.

    Prevents 'Event loop is closed' errors when SQLAlchemy's asyncpg
    connection pool retains connections between module-scoped fixtures.
    """
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()
