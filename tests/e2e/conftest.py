"""E2E harness: a real uvicorn server on a throw-away database, driven by installed Chrome."""
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture(scope="session")
def server(tmp_path_factory):
    port = _free_port()
    db_file = tmp_path_factory.mktemp("e2e") / "e2e.db"
    env = {**os.environ, "FOODDASH_DATABASE_URL": f"sqlite:///{db_file}"}
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app", "--port", str(port), "--log-level", "warning"],
        cwd=ROOT, env=env,
    )
    base_url = f"http://127.0.0.1:{port}"
    for _ in range(100):
        try:
            if httpx.get(f"{base_url}/api/health", timeout=1).status_code == 200:
                break
        except httpx.HTTPError:
            time.sleep(0.1)
    else:
        process.terminate()
        pytest.fail("server did not start")
    yield base_url
    process.terminate()
    process.wait(timeout=10)


@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as p:
        try:
            instance = p.chromium.launch(channel="chrome", headless=True)
        except Exception as exc:  # pragma: no cover - environment dependent
            pytest.skip(f"Google Chrome is not available for Playwright: {exc}")
        yield instance
        instance.close()


@pytest.fixture()
def page(browser, server):
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    context.set_default_timeout(8000)
    page = context.new_page()
    page.base_url = server
    page.goto(server)
    yield page
    context.close()


@pytest.fixture()
def api_url(server):
    return server
