"""
E2E Verification Script - Tests both User and Admin flows
Verifies all critical endpoints after the fixes applied in this session.
"""
import requests
import json
import sys

BASE = "http://127.0.0.1:8000/api"
PASS_COUNT = 0
FAIL_COUNT = 0

def test(name, condition, detail=""):
    global PASS_COUNT, FAIL_COUNT
    if condition:
        PASS_COUNT += 1
        print(f"  [PASS] {name}")
    else:
        FAIL_COUNT += 1
        print(f"  [FAIL] {name} - {detail}")

def get_token(email, password):
    r = requests.post(f"{BASE}/auth/login", json={"email": email, "password": password})
    if r.status_code == 200:
        return r.json().get("access_token")
    return None

def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}

print("=" * 60)
print("E2E VERIFICATION - User + Admin Flows")
print("=" * 60)

# ============ USER AUTHENTICATION FLOW ============
print("\n--- 1. User Authentication ---")

# Login with valid credentials
r = requests.post(f"{BASE}/auth/login", json={"email": "rangasudarshan19@gmail.com", "password": "Sudarshan@1"})
test("User login", r.status_code == 200, f"Status: {r.status_code}")
user_token = r.json().get("access_token") if r.status_code == 200 else None

# Login with invalid credentials
r = requests.post(f"{BASE}/auth/login", json={"email": "fake@test.com", "password": "wrong"})
test("Invalid login rejected", r.status_code == 401, f"Status: {r.status_code}")

# Get current user
if user_token:
    r = requests.get(f"{BASE}/auth/me", headers=auth_headers(user_token))
    test("Get current user", r.status_code == 200, f"Status: {r.status_code}")
    test("Has email field", "email" in r.json(), f"Keys: {list(r.json().keys())}")

# No token access
r = requests.get(f"{BASE}/auth/me")
test("Unauthorized without token", r.status_code in [401, 403], f"Status: {r.status_code}")

# ============ USER APPLICATION FLOW ============
print("\n--- 2. Application CRUD ---")

if user_token:
    headers = auth_headers(user_token)
    
    # Create application
    app_data = {
        "job_title": "E2E Test Engineer",
        "company_name": "TestCorp",
        "status": "applied",
        "job_url": "https://testcorp.com/jobs/1",
        "location": "Remote",
        "job_type": "Full-time",
        "salary_range": "$100k-$120k",
        "notes": "E2E test application"
    }
    r = requests.post(f"{BASE}/applications/", json=app_data, headers=headers)
    test("Create application", r.status_code in [200, 201], f"Status: {r.status_code}, Body: {r.text[:200]}")
    app_id = r.json().get("id") if r.status_code in [200, 201] else None
    
    # List applications
    r = requests.get(f"{BASE}/applications/", headers=headers)
    test("List applications", r.status_code == 200, f"Status: {r.status_code}")
    test("Applications is list", isinstance(r.json(), list), f"Type: {type(r.json())}")
    
    # Update application
    if app_id:
        r = requests.put(f"{BASE}/applications/{app_id}", json={"status": "interview_scheduled"}, headers=headers)
        test("Update application", r.status_code == 200, f"Status: {r.status_code}")
    
    # Delete application (cleanup)
    if app_id:
        r = requests.delete(f"{BASE}/applications/{app_id}", headers=headers)
        test("Delete application", r.status_code in [200, 204], f"Status: {r.status_code}")

# ============ ADMIN AUTHENTICATION ============
print("\n--- 3. Admin Authentication ---")

r = requests.post(f"{BASE}/auth/login", json={"email": "admin@jobtracker.com", "password": "admin123"})
test("Admin login", r.status_code == 200, f"Status: {r.status_code}")
admin_token = r.json().get("access_token") if r.status_code == 200 else None

if admin_token:
    r = requests.get(f"{BASE}/auth/me", headers=auth_headers(admin_token))
    test("Admin is_admin flag", r.json().get("is_admin") == True, f"is_admin: {r.json().get('is_admin')}")

# ============ ADMIN DASHBOARD ============
print("\n--- 4. Admin Dashboard ---")

if admin_token:
    headers = auth_headers(admin_token)
    
    r = requests.get(f"{BASE}/admin/dashboard", headers=headers)
    test("Admin dashboard", r.status_code == 200, f"Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        test("Has total_users", "total_users" in data, f"Keys: {list(data.keys())}")
        test("Has total_applications", "total_applications" in data)

# ============ ADMIN USER MANAGEMENT ============
print("\n--- 5. Admin User Management ---")

if admin_token:
    headers = auth_headers(admin_token)
    
    r = requests.get(f"{BASE}/admin/users", headers=headers)
    test("List all users", r.status_code == 200, f"Status: {r.status_code}")
    if r.status_code == 200:
        users = r.json()
        test("Users is list", isinstance(users, list))
        test("Users have email", all("email" in u for u in users[:3]))

# ============ ADMIN ANALYTICS (Fixed endpoints) ============
print("\n--- 6. Admin Analytics (Fixed) ---")

if admin_token:
    headers = auth_headers(admin_token)
    
    # User analytics with valid period
    r = requests.get(f"{BASE}/admin/analytics/users?period=30d", headers=headers)
    test("User analytics (30d)", r.status_code == 200, f"Status: {r.status_code}")
    
    # User analytics with invalid period (should return 400 now, not crash)
    r = requests.get(f"{BASE}/admin/analytics/users?period=1m", headers=headers)
    test("Invalid period returns 400", r.status_code == 400, f"Status: {r.status_code}")
    
    # Application analytics
    r = requests.get(f"{BASE}/admin/analytics/applications?period=7d", headers=headers)
    test("Application analytics", r.status_code == 200, f"Status: {r.status_code}")
    
    # Company analytics (fixed: was using Application.company_name)
    r = requests.get(f"{BASE}/admin/analytics/companies", headers=headers)
    test("Company analytics", r.status_code == 200, f"Status: {r.status_code}")
    
    # Export analytics
    r = requests.get(f"{BASE}/admin/analytics/export?format=json", headers=headers)
    test("Export analytics (JSON)", r.status_code == 200, f"Status: {r.status_code}")

# ============ ADMIN STATS (Backward compat) ============
print("\n--- 7. Admin Stats ---")

if admin_token:
    headers = auth_headers(admin_token)
    
    r = requests.get(f"{BASE}/admin/stats", headers=headers)
    test("System stats", r.status_code == 200, f"Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        test("Has status_breakdown", "application_status_breakdown" in data)

# ============ ADMIN AUDIT LOGS ============
print("\n--- 8. Admin Audit & Security ---")

if admin_token:
    headers = auth_headers(admin_token)
    
    r = requests.get(f"{BASE}/admin/audit-logs", headers=headers)
    test("Audit logs", r.status_code == 200, f"Status: {r.status_code}")
    
    r = requests.get(f"{BASE}/admin/settings", headers=headers)
    test("System settings", r.status_code == 200, f"Status: {r.status_code}")

# ============ ADMIN ANNOUNCEMENTS ============
print("\n--- 9. Admin Announcements ---")

if admin_token:
    headers = auth_headers(admin_token)
    
    # Create announcement
    ann_data = {"title": "E2E Test Announcement", "content": "This is a test announcement from E2E verification."}
    r = requests.post(f"{BASE}/admin/announcements", json=ann_data, headers=headers)
    test("Create announcement", r.status_code == 200, f"Status: {r.status_code}")
    ann_id = r.json().get("announcement_id") if r.status_code == 200 else None
    
    # List announcements
    r = requests.get(f"{BASE}/admin/announcements", headers=headers)
    test("List announcements", r.status_code == 200, f"Status: {r.status_code}")
    
    # Delete announcement (cleanup)
    if ann_id:
        r = requests.delete(f"{BASE}/admin/announcements/{ann_id}", headers=headers)
        test("Delete announcement", r.status_code == 200, f"Status: {r.status_code}")

# ============ NON-ADMIN ACCESS BLOCKED ============
print("\n--- 10. Non-admin Access Blocked ---")

if user_token:
    headers = auth_headers(user_token)
    
    r = requests.get(f"{BASE}/admin/dashboard", headers=headers)
    test("Dashboard blocked for user", r.status_code == 403, f"Status: {r.status_code}")
    
    r = requests.get(f"{BASE}/admin/users", headers=headers)
    test("Users blocked for user", r.status_code == 403, f"Status: {r.status_code}")

# ============ SUMMARY ============
print("\n" + "=" * 60)
print(f"RESULTS: {PASS_COUNT} passed, {FAIL_COUNT} failed (out of {PASS_COUNT + FAIL_COUNT})")
print("=" * 60)

sys.exit(0 if FAIL_COUNT == 0 else 1)
