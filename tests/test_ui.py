from urllib.parse import urljoin


import pytest


@pytest.fixture
def base_url(netbox_server):
    return netbox_server


def test_login(page, base_url, console_errors):
    """NetBox login page loads and authentication works."""
    page.goto(urljoin(base_url, "/login/"))
    page.locator('input[name="username"]').fill("admin")
    page.locator('input[name="password"]').fill("admin")
    page.locator('button[type="submit"]').click()
    page.wait_for_url(lambda url: not url.endswith("/login/"), timeout=10000)
    assert page.url != urljoin(base_url, "/login/")
    assert not console_errors, f"Console errors: {console_errors}"


def test_topology_page_loads(logged_in_page, base_url, console_errors):
    """The topology page renders without console errors."""
    logged_in_page.goto(urljoin(base_url, "/plugins/netbox_topology_views/topology/"))
    logged_in_page.wait_for_selector("#visgraph", state="visible", timeout=15000)
    assert not console_errors, f"Console errors: {console_errors}"


def test_images_page_loads(logged_in_page, base_url, console_errors):
    """The images page returns 200 and no console errors.

    This page exercises image_static_url() and get_image_url(), so it is the
    main regression test for the SuspiciousFileOperation that occurred with
    DEBUG=True and django-debug-toolbar.
    """
    response = logged_in_page.goto(urljoin(base_url, "/plugins/netbox_topology_views/images/"))
    assert response is not None and response.status == 200
    logged_in_page.wait_for_selector("form#images", state="visible", timeout=15000)
    assert not console_errors, f"Console errors: {console_errors}"


def test_dark_mode_does_not_break_topology(logged_in_page, base_url, console_errors):
    """Switching to dark mode while the topology page is open does not raise errors."""
    logged_in_page.goto(urljoin(base_url, "/plugins/netbox_topology_views/topology/"))
    logged_in_page.wait_for_selector("#visgraph", state="visible", timeout=15000)

    # Simulate the NetBox color-mode change on the page
    logged_in_page.evaluate("""() => {
        document.documentElement.setAttribute('data-bs-theme', 'dark');
        window.dispatchEvent(new CustomEvent('netbox.colorModeChanged', {
            detail: { netboxColorMode: 'dark' }
        }));
    }""")

    # Give any async handlers a moment to run
    logged_in_page.wait_for_timeout(500)

    # The graph code is wrapped in a bundle IIFE, so we cannot read the options
    # object directly. The next best thing is to ensure no JS errors were raised.
    assert not console_errors, f"Console errors: {console_errors}"
