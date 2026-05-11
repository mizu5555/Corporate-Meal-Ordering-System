import importlib
import os

from fastapi.testclient import TestClient


def _build_app(root_path: str = ""):
    if root_path:
        os.environ["ROOT_PATH"] = root_path
    else:
        os.environ.pop("ROOT_PATH", None)
    import backend.main as main
    importlib.reload(main)
    return main.app


def test_root_path_empty_by_default():
    app = _build_app("")
    assert app.root_path == ""


def test_root_path_picked_up_from_env():
    app = _build_app("/meal")
    assert app.root_path == "/meal"
    os.environ.pop("ROOT_PATH", None)


def test_openapi_reflects_root_path():
    app = _build_app("/meal-staging")
    client = TestClient(app)
    spec = client.get("/openapi.json").json()
    assert spec.get("servers") == [{"url": "/meal-staging"}]
    os.environ.pop("ROOT_PATH", None)
