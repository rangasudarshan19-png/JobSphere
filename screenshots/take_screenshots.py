"""
JobSphere — Automated Screenshot Capture
Uses Playwright to capture screenshots of all UI pages.
Requires: pip install playwright && python -m playwright install chromium
Backend must be running on http://127.0.0.1:8000
"""

import asyncio
import os
import http.server
import threading
import time
import json
import urllib.request

# ── Configuration ──
API_BASE = "http://127.0.0.1:8000"
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")
FRONTEND_PORT = 5500
FRONTEND_BASE = f"http://localhost:{FRONTEND_PORT}"
SCREENSHOT_DIR = os.path.dirname(os.path.abspath(__file__))

USER_EMAIL = "rangasudarshan19@gmail.com"
USER_PASSWORD = "Sudarshan@1"
ADMIN_EMAIL = "admin@jobtracker.com"
ADMIN_PASSWORD = "admin123"

VIEWPORT = {"width": 1440, "height": 900}

# (screenshot_name, html_file, needs_auth)
USER_PAGES = [
    ("01_landing_page",       "index.html",             False),
    ("02_login_page",         "login.html",             False),
    ("03_signup_page",        "signup.html",             False),
    ("04_dashboard",          "dashboard.html",          True),
    ("05_job_search",         "job-search.html",         True),
    ("06_job_tracker",        "job-tracker.html",        True),
    ("07_kanban_tracker",     "kanban-tracker.html",     True),
    ("08_ai_resume_builder",  "ai-resume-builder.html",  True),
    ("09_cover_letter",       "cover-letter.html",       True),
    ("10_interview_prep",     "interview-prep.html",     True),
    ("11_job_matching",       "job-matching.html",       True),
    ("12_analytics",          "analytics.html",          True),
    ("13_profile",            "profile.html",            True),
]

# (screenshot_name, html_file, tab_id)
ADMIN_PAGES = [
    ("admin_01_overview",       "admin.html", "overview"),
    ("admin_02_api_status",     "admin.html", "api-status"),
    ("admin_03_users",          "admin.html", "users"),
    ("admin_04_manage_users",   "admin.html", "manage-users"),
    ("admin_05_applications",   "admin.html", "applications"),
    ("admin_06_announcements",  "admin.html", "announcements"),
    ("admin_07_audit_logs",     "admin.html", "audit-logs"),
]


def start_frontend_server():
    """Start a simple HTTP server to serve the frontend files."""
    os.chdir(FRONTEND_DIR)
    handler = http.server.SimpleHTTPRequestHandler
    handler.log_message = lambda *args: None
    server = http.server.HTTPServer(("localhost", FRONTEND_PORT), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"  Frontend server started on {FRONTEND_BASE}")
    return server


def login_via_api(email, password):
    """Login via direct HTTP request and return (token, user_name)."""
    data = json.dumps({"email": email, "password": password}).encode("utf-8")
    req = urllib.request.Request(
        f"{API_BASE}/api/auth/login",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode())
            token = result.get("access_token")
            user_name = result.get("user_name", "")
            if token:
                print(f"    Logged in as {email}")
                return token, user_name
            print(f"    No token in response for {email}")
            return None, None
    except Exception as e:
        print(f"    Login FAILED for {email}: {e}")
        return None, None


def get_user_info(token):
    """Check is_admin via /api/auth/me."""
    req = urllib.request.Request(
        f"{API_BASE}/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return {}


async def inject_session(page, token, email, user_name="", is_admin=False):
    """Inject auth data into sessionStorage on the current origin."""
    await page.evaluate(
        """([token, email, userName, isAdmin]) => {
            sessionStorage.clear();
            sessionStorage.setItem('access_token', token);
            sessionStorage.setItem('userEmail', email);
            if (userName) sessionStorage.setItem('userName', userName);
            if (isAdmin) sessionStorage.setItem('isAdmin', 'true');
        }""",
        [token, email, user_name, is_admin],
    )


async def wait_for_page_ready(page, timeout_ms=6000):
    """Wait for loading indicators to disappear."""
    try:
        await page.wait_for_function(
            """() => {
                // Check loading overlay
                const overlay = document.getElementById('loadingOverlay');
                if (overlay && overlay.style.display !== 'none' && overlay.style.opacity !== '0') return false;
                // Check spinners
                const spinners = document.querySelectorAll('.spinner, .loading-spinner');
                for (const s of spinners) {
                    if (s.offsetParent !== null) return false;
                }
                return true;
            }""",
            timeout=timeout_ms,
        )
    except:
        pass


async def capture(page, name, wait_extra=500):
    """Take a viewport screenshot."""
    filepath = os.path.join(SCREENSHOT_DIR, f"{name}.png")
    await page.wait_for_timeout(wait_extra)
    await page.screenshot(path=filepath, full_page=False)
    print(f"    Captured: {name}.png")


async def main():
    from playwright.async_api import async_playwright

    print("=" * 55)
    print("  JobSphere — Screenshot Capture")
    print("=" * 55)

    # 1. Start frontend server
    print("\n[1/5] Starting frontend server...")
    server = start_frontend_server()
    time.sleep(1)

    # 2. Verify backend
    print("\n[2/5] Checking backend server...")
    try:
        urllib.request.urlopen(f"{API_BASE}/docs", timeout=5)
        print("  Backend is online")
    except Exception:
        print("  WARNING: Backend may not be running!")

    # 3. Authenticate via API
    print("\n[3/5] Authenticating...")
    user_token, user_name = login_via_api(USER_EMAIL, USER_PASSWORD)
    admin_token, admin_name = login_via_api(ADMIN_EMAIL, ADMIN_PASSWORD)

    admin_is_admin = False
    if admin_token:
        info = get_user_info(admin_token)
        admin_is_admin = info.get("is_admin", False)
        if admin_is_admin:
            print("    Admin role confirmed")

    ok = 0
    fail = 0

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # ──────────────── USER PAGES ────────────────
        print("\n[4/5] Capturing USER pages...")

        for name, filename, needs_auth in USER_PAGES:
            ctx = await browser.new_context(viewport=VIEWPORT)
            page = await ctx.new_page()

            try:
                # First, load a page on the same origin so sessionStorage is available
                await page.goto(f"{FRONTEND_BASE}/index.html", wait_until="domcontentloaded", timeout=10000)
                await page.wait_for_timeout(200)

                if needs_auth and user_token:
                    # Inject auth BEFORE navigating to the target page
                    await inject_session(page, user_token, USER_EMAIL, user_name, False)
                elif not needs_auth:
                    # Clear session so login/signup pages don't auto-redirect
                    await page.evaluate("sessionStorage.clear()")

                if needs_auth and not user_token:
                    print(f"    SKIPPED: {name} (no token)")
                    fail += 1
                    await ctx.close()
                    continue

                # Navigate to the real page
                await page.goto(f"{FRONTEND_BASE}/{filename}", wait_until="domcontentloaded", timeout=15000)
                await page.wait_for_timeout(2000)
                await wait_for_page_ready(page)

                # Verify we didn't get redirected to login
                if needs_auth and "login.html" in page.url:
                    print(f"    FAILED: {name} — redirected to login")
                    fail += 1
                    await ctx.close()
                    continue

                await capture(page, name, wait_extra=1000)
                ok += 1
            except Exception as e:
                print(f"    FAILED: {name} — {e}")
                fail += 1

            await ctx.close()

        # ──────────────── ADMIN PAGES ────────────────
        print("\n[5/5] Capturing ADMIN pages...")

        if not admin_token:
            print("    Admin login failed — skipping")
            fail += len(ADMIN_PAGES)
        else:
            ctx = await browser.new_context(viewport=VIEWPORT)
            page = await ctx.new_page()

            # Establish origin and inject admin auth
            await page.goto(f"{FRONTEND_BASE}/index.html", wait_until="domcontentloaded", timeout=10000)
            await page.wait_for_timeout(200)
            await inject_session(page, admin_token, ADMIN_EMAIL, admin_name, admin_is_admin)

            # Navigate to admin panel
            await page.goto(f"{FRONTEND_BASE}/admin.html", wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_timeout(4000)

            if "login.html" in page.url:
                print("    Redirected to login — admin auth failed")
                fail += len(ADMIN_PAGES)
            else:
                for sname, _, tab_id in ADMIN_PAGES:
                    try:
                        # Switch to the tab
                        await page.evaluate(
                            """(tabId) => {
                                // Deactivate all
                                document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
                                document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
                                // Activate target tab
                                const tab = document.getElementById(tabId);
                                if (tab) tab.classList.add('active');
                                // Highlight matching nav item
                                const map = {
                                    'overview': 'Overview', 'api-status': 'API Status',
                                    'users': 'All Users', 'manage-users': 'Manage Users',
                                    'applications': 'Applications', 'announcements': 'Announcements',
                                    'audit-logs': 'Audit Logs'
                                };
                                const label = map[tabId] || '';
                                document.querySelectorAll('.nav-item').forEach(n => {
                                    if (n.textContent.trim().includes(label)) n.classList.add('active');
                                });
                            }""",
                            tab_id,
                        )

                        # Trigger data loading
                        if tab_id == "users":
                            await page.evaluate("loadAllUsers()")
                        elif tab_id == "audit-logs":
                            await page.evaluate("loadAuditLogs()")
                        elif tab_id == "api-status":
                            await page.evaluate("checkAllApis()")
                        elif tab_id == "applications":
                            await page.evaluate("loadApplicationsList()")

                        await page.wait_for_timeout(3000)
                        await capture(page, sname, wait_extra=500)
                        ok += 1
                    except Exception as e:
                        print(f"    FAILED: {sname} — {e}")
                        fail += 1

            await ctx.close()

        await browser.close()

    server.shutdown()

    print("\n" + "=" * 55)
    print(f"  Results: {ok} captured, {fail} failed")
    print(f"  Saved to: {SCREENSHOT_DIR}")
    print("=" * 55)


if __name__ == "__main__":
    asyncio.run(main())
