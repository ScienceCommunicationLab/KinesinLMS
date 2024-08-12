import pytest
from django.core.cache import cache


@pytest.fixture(scope="function", autouse=True)
def clear_caches() -> None:
    """
    Called before each test function.
    """
    # Clear all the caches, specifically the course nav cache.
    cache.clear()
