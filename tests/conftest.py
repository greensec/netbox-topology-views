import os
import re
import subprocess
import sys
import time
from urllib.parse import urljoin

import pytest
import requests


@pytest.fixture(scope="session")
def netbox_server(tmp_path_factory):
    """Start a NetBox runserver and yield its base URL."""
    netbox_dir = os.environ.get("NETBOX_DIR", "netbox/netbox")
    base_url = os.environ.get("NETBOX_BASE_URL", "http://127.0.0.1:8000")
    env = os.environ.copy()
    env["DJANGO_SUPERUSER_PASSWORD"] = "admin"

    # Create a superuser for the tests
    subprocess.run(
        [sys.executable, "manage.py", "createsuperuser",
         "--no-input", "--username", "admin", "--email", "admin@example.com"],
        cwd=netbox_dir,
        env=env,
        check=True,
    )

    log_path = tmp_path_factory.mktemp("netbox") / "runserver.log"
    log_file = log_path.open("w+")
    proc = subprocess.Popen(
        [sys.executable, "manage.py", "runserver", "127.0.0.1:8000"],
        cwd=netbox_dir,
        env=env,
        stdout=log_file,
        stderr=subprocess.STDOUT,
    )

    # Wait for the server to become ready
    deadline = time.time() + 120
    while time.time() < deadline:
        try:
            resp = requests.get(urljoin(base_url, "/login/"), timeout=2)
            if resp.status_code < 500:
                break
        except Exception:
            pass
        if proc.poll() is not None:
            log_file.flush()
            log_file.seek(0)
            raise RuntimeError(
                f"NetBox runserver exited early (code {proc.returncode}):\n"
                f"{log_file.read()}"
            )
        time.sleep(1)
    else:
        proc.terminate()
        raise RuntimeError("NetBox runserver did not become ready in time")

    try:
        yield base_url
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except Exception:
            proc.kill()
        log_file.close()


@pytest.fixture
def console_errors(page):
    """Capture console error messages from the page."""
    errors = []

    def handler(msg):
        if msg.type == "error":
            errors.append(msg.text)

    page.on("console", handler)
    yield errors
    page.remove_listener("console", handler)


@pytest.fixture
def logged_in_page(page, netbox_server):
    """Log in to NetBox and return the page."""
    page.goto(urljoin(netbox_server, "/login/"))
    page.locator('input[name="username"]').fill("admin")
    page.locator('input[name="password"]').fill("admin")
    page.locator('button[type="submit"]').click()
    page.wait_for_url(re.compile(r"^(?!.*/login/).*$"), timeout=10000)
    return page
