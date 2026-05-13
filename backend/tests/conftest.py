from collections.abc import Generator

import pytest
from prometheus_client import REGISTRY


def _unregister_inprogress() -> None:
    """Remove the http_requests_inprogress collector so it can be re-registered."""
    for collector in list(REGISTRY._collector_to_names):
        names = REGISTRY._collector_to_names.get(collector, set())
        if "http_requests_inprogress" in names:
            REGISTRY.unregister(collector)


@pytest.fixture(autouse=True)
def _isolate_prometheus_registry() -> Generator[None, None, None]:
    """Prevent registry pollution from importlib.reload(backend.main) in test_root_path."""
    _unregister_inprogress()
    yield
    _unregister_inprogress()
