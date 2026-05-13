import sys
import pytest
from prometheus_client import REGISTRY


@pytest.fixture(autouse=True)
def _isolate_module_reloads(request):
    """
    Isolate module reloads in test_root_path.py to avoid Prometheus registry pollution.

    When test_root_path.py does importlib.reload(backend.main), it tries to register
    the same Prometheus metrics again. This fixture removes duplicate collectors for
    tests that do module reloads, allowing the same gauges to be registered multiple times.
    """
    # For tests that do module reloads, pre-unregister the inprogress gauge
    # so it can be re-registered without error
    if "test_root_path" in request.node.nodeid:
        # Find and temporarily remove the http_requests_inprogress gauge
        # so the reload can re-register it
        to_unregister = []
        for collector in list(REGISTRY._collector_to_names.keys()):
            try:
                names = REGISTRY._collector_to_names.get(collector, set())
                if "http_requests_inprogress" in names:
                    to_unregister.append(collector)
            except Exception:
                pass

        for collector in to_unregister:
            try:
                REGISTRY.unregister(collector)
            except Exception:
                pass

    yield
