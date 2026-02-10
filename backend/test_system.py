"""
Comprehensive system test for Ain News Monitor
Tests all critical paths before Render deployment
"""
import requests
import time
import json
import sys

BASE = "http://127.0.0.1:5555"
session = requests.Session()
PASS = 0
FAIL = 0
WARN = 0

def ok(msg):
    global PASS
    PASS += 1
    print(f"  ✅ {msg}")

def fail(msg):
    global FAIL
    FAIL += 1
    print(f"  ❌ {msg}")

def warn(msg):
    global WARN
    WARN += 1
    print(f"  ⚠️  {msg}")

def test(name, func):
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print(f"{'='*60}")
    try:
        func()
    except Exception as e:
        fail(f"Exception: {e}")

# ─── 1. Health Check ─────────────────────────────────────────
def test_health():
    r = session.get(f"{BASE}/")
    if r.status_code == 200:
        ok(f"Server responding (status {r.status_code})")
    else:
        fail(f"Server returned {r.status_code}")

# ─── 2. Auth: Unauthenticated access blocked ─────────────────
def test_auth_blocked():
    endpoints = [
        ("GET", "/api/keywords"),
        ("GET", "/api/articles"),
        ("GET", "/api/monitor/status"),
        ("POST", "/api/keywords"),
    ]
    for method, path in endpoints:
        r = getattr(requests, method.lower())(f"{BASE}{path}")
        if r.status_code == 401:
            ok(f"{method} {path} → 401 (auth required)")
        else:
            fail(f"{method} {path} → {r.status_code} (expected 401)")

# ─── 3. Login ─────────────────────────────────────────────────
def test_login():
    # Wrong password
    r = session.post(f"{BASE}/api/auth/login", json={
        "email": "elite@local", "password": "wrongpassword"
    })
    if r.status_code != 200 or not r.json().get("success", True):
        ok("Wrong password rejected")
    else:
        fail("Wrong password accepted!")
    
    # Correct login
    r = session.post(f"{BASE}/api/auth/login", json={
        "email": "elite@local", "password": "135813581234"
    })
    if r.status_code == 200:
        data = r.json()
        # Login may return {user: {...}} or {email, id, name, role} directly
        email = data.get('email') or data.get('user', {}).get('email', '')
        if email:
            ok(f"Login successful: {email}")
        else:
            fail(f"Login response unexpected: {data}")
    else:
        fail(f"Login failed: {r.status_code} - {r.text[:100]}")

# ─── 4. Get current keywords ─────────────────────────────────
def test_get_keywords():
    r = session.get(f"{BASE}/api/keywords")
    if r.status_code == 200:
        data = r.json()
        keywords = data.get("keywords", data) if isinstance(data, dict) else data
        ok(f"Keywords loaded: {len(keywords)} keywords")
        for kw in keywords:
            print(f"      ID:{kw.get('id')} text:'{kw.get('text_ar', kw.get('text'))}' enabled:{kw.get('enabled')}")
        return keywords
    else:
        fail(f"Get keywords failed: {r.status_code}")
        return []

# ─── 5. Delete all existing keywords (clean state) ───────────
def test_delete_all_keywords():
    r = session.get(f"{BASE}/api/keywords")
    if r.status_code != 200:
        fail("Cannot get keywords for cleanup")
        return
    
    data = r.json()
    keywords = data.get("keywords", data) if isinstance(data, dict) else data
    
    for kw in keywords:
        kw_id = kw.get("id")
        r = session.delete(f"{BASE}/api/keywords/{kw_id}")
        if r.status_code == 200:
            ok(f"Deleted keyword ID:{kw_id} '{kw.get('text_ar', '')}'")
        else:
            fail(f"Delete keyword {kw_id} failed: {r.status_code}")
    
    # Verify empty
    r = session.get(f"{BASE}/api/keywords")
    data = r.json()
    keywords = data.get("keywords", data) if isinstance(data, dict) else data
    if len(keywords) == 0:
        ok("All keywords deleted - clean state")
    else:
        fail(f"Still have {len(keywords)} keywords after deletion")

# ─── 6. Monitor status with no keywords ──────────────────────
def test_monitor_no_keywords():
    r = session.get(f"{BASE}/api/monitor/status")
    if r.status_code == 200:
        data = r.json()
        ok(f"Monitor status OK: running={data.get('running')}, executing={data.get('executing')}")
        if 'user_has_keywords' in data:
            ok(f"user_has_keywords={data['user_has_keywords']}, user_keyword_count={data.get('user_keyword_count')}")
        else:
            warn("Missing 'user_has_keywords' field in status response")
    else:
        fail(f"Monitor status failed: {r.status_code}")

# ─── 7. Add a keyword ────────────────────────────────────────
def test_add_keyword(text="السعودية"):
    r = session.post(f"{BASE}/api/keywords", json={"text_ar": text})
    if r.status_code == 200:
        data = r.json()
        if data.get("success"):
            ok(f"Added keyword '{text}' (ID: {data.get('id')})")
            return data.get("id")
        else:
            fail(f"Add keyword response: {data}")
    else:
        fail(f"Add keyword failed: {r.status_code} - {r.text[:200]}")
    return None

# ─── 8. Add duplicate keyword ────────────────────────────────
def test_add_duplicate_keyword(text="السعودية"):
    r = session.post(f"{BASE}/api/keywords", json={"text_ar": text})
    if r.status_code != 200 or not r.json().get("success", True):
        ok(f"Duplicate keyword '{text}' correctly rejected")
    else:
        data = r.json()
        if data.get("error") or not data.get("success"):
            ok(f"Duplicate keyword rejected: {data.get('error', 'rejected')}")
        else:
            warn(f"Duplicate keyword was accepted (may be by design): {data}")

# ─── 9. Articles endpoint ────────────────────────────────────
def test_articles():
    r = session.get(f"{BASE}/api/articles")
    if r.status_code == 200:
        data = r.json()
        if isinstance(data, list):
            ok(f"Articles endpoint OK: {len(data)} articles")
        else:
            articles = data.get("articles", [])
            total = data.get("total", len(articles))
            ok(f"Articles endpoint OK: {total} articles")
    else:
        fail(f"Articles failed: {r.status_code}")
    
    # Stats
    r = session.get(f"{BASE}/api/articles/stats")
    if r.status_code == 200:
        ok(f"Article stats OK: {r.json()}")
    else:
        fail(f"Article stats failed: {r.status_code}")
    
    # Countries
    r = session.get(f"{BASE}/api/articles/countries")
    if r.status_code == 200:
        ok(f"Article countries OK")
    else:
        fail(f"Article countries failed: {r.status_code}")

# ─── 10. Toggle keyword ──────────────────────────────────────
def test_toggle_keyword(kw_id):
    if not kw_id:
        warn("No keyword ID to toggle")
        return
    
    r = session.post(f"{BASE}/api/keywords/{kw_id}/toggle")
    if r.status_code == 200:
        ok(f"Toggle keyword {kw_id} OK")
    else:
        fail(f"Toggle keyword {kw_id} failed: {r.status_code} - {r.text[:100]}")

# ─── 11. Sources and Countries (admin) ───────────────────────
def test_sources_countries():
    r = session.get(f"{BASE}/api/sources")
    if r.status_code == 200:
        data = r.json()
        sources = data.get("sources", data) if isinstance(data, dict) else data
        ok(f"Sources: {len(sources)} loaded")
    else:
        fail(f"Sources failed: {r.status_code}")
    
    r = session.get(f"{BASE}/api/countries")
    if r.status_code == 200:
        data = r.json()
        countries = data.get("countries", data) if isinstance(data, dict) else data
        ok(f"Countries: {len(countries)} loaded")
    else:
        fail(f"Countries failed: {r.status_code}")
    
    r = session.get(f"{BASE}/api/sources/countries")
    if r.status_code == 200:
        ok("Sources/countries endpoint OK")
    else:
        fail(f"Sources/countries failed: {r.status_code}")

# ─── 12. Top Headlines ───────────────────────────────────────
def test_top_headlines():
    r = session.get(f"{BASE}/api/headlines/top?country=السعودية")
    if r.status_code == 200:
        ok("Top headlines endpoint OK")
    else:
        fail(f"Top headlines failed: {r.status_code}")

# ─── 13. External Headlines ──────────────────────────────────
def test_external_headlines():
    r = session.get(f"{BASE}/api/external-headlines?country=sa")
    if r.status_code == 200:
        ok(f"External headlines OK")
    else:
        warn(f"External headlines returned {r.status_code} (may need API key)")

# ─── 14. Cleanup status ──────────────────────────────────────
def test_cleanup_status():
    r = session.get(f"{BASE}/api/system/cleanup-status")
    if r.status_code == 200:
        data = r.json()
        ok(f"Cleanup status OK: days_remaining={data.get('days_remaining')}")
    else:
        fail(f"Cleanup status failed: {r.status_code}")

# ─── 15. Monitor start/stop ──────────────────────────────────
def test_monitor_controls():
    # Status first
    r = session.get(f"{BASE}/api/monitor/status")
    status = r.json()
    was_running = status.get("running", False)
    
    # Stop
    r = session.post(f"{BASE}/api/monitor/stop")
    if r.status_code == 200:
        data = r.json()
        ok(f"Monitor stop: {data.get('message', data)}")
    else:
        fail(f"Monitor stop failed: {r.status_code}")
    
    time.sleep(1)
    
    # Start
    r = session.post(f"{BASE}/api/monitor/start")
    if r.status_code == 200:
        data = r.json()
        ok(f"Monitor start: {data.get('message', data)}")
    else:
        fail(f"Monitor start failed: {r.status_code}")
    
    # Verify running
    time.sleep(1)
    r = session.get(f"{BASE}/api/monitor/status")
    if r.status_code == 200:
        data = r.json()
        if data.get("running"):
            ok("Monitor confirmed running after start")
        else:
            warn("Monitor not showing as running after start")

# ─── 16. Keyword limit test ──────────────────────────────────
def test_keyword_limit():
    # Try adding up to MAX_KEYWORDS (5) + 1
    added_ids = []
    keywords_to_try = ["مصر", "الأردن", "قطر", "الكويت"]
    
    for text in keywords_to_try:
        r = session.post(f"{BASE}/api/keywords", json={"text_ar": text})
        if r.status_code == 200:
            data = r.json()
            if data.get("success"):
                added_ids.append(data.get("id"))
                ok(f"Added '{text}' ({len(added_ids)}/5)")
            else:
                ok(f"Keyword '{text}' rejected at limit: {data.get('error', '')[:80]}")
                break
        else:
            if r.status_code == 400 or r.status_code == 429:
                ok(f"Keyword limit enforced at {len(added_ids)} keywords")
            else:
                fail(f"Unexpected response: {r.status_code} - {r.text[:100]}")
            break
    
    # Try one more (should be rejected if limit is 5)
    if len(added_ids) >= 5:
        r = session.post(f"{BASE}/api/keywords", json={"text_ar": "عراق"})
        if r.status_code == 200 and r.json().get("success"):
            fail("6th keyword accepted! Limit not enforced")
            # Cleanup the extra one
            extra_id = r.json().get("id")
            if extra_id:
                session.delete(f"{BASE}/api/keywords/{extra_id}")
        else:
            ok("6th keyword correctly rejected (limit=5)")
    
    # Cleanup - delete added keywords
    for kw_id in added_ids:
        session.delete(f"{BASE}/api/keywords/{kw_id}")
    ok(f"Cleaned up {len(added_ids)} test keywords")

# ─── 17. User profile ────────────────────────────────────────
def test_user_profile():
    r = session.get(f"{BASE}/api/auth/me")
    if r.status_code == 200:
        data = r.json()
        ok(f"User profile OK: {data.get('email', 'unknown')}")
    else:
        fail(f"User profile failed: {r.status_code}")

# ─── 18. Export endpoint ──────────────────────────────────────
def test_exports():
    r = session.get(f"{BASE}/api/exports")
    if r.status_code == 200:
        ok("Exports list OK")
    else:
        fail(f"Exports failed: {r.status_code}")

# ─── 19. Check for any Python import issues ──────────────────
def test_imports():
    """Test that all backend modules can be imported without errors"""
    import importlib
    modules = [
        "models", "config", "global_scheduler", "scheduler",
        "keyword_expansion", "translation_service", "rss_service",
        "async_monitor_wrapper", "async_rss_fetcher",
    ]
    for mod in modules:
        try:
            importlib.import_module(mod)
            ok(f"Import {mod} OK")
        except Exception as e:
            fail(f"Import {mod} FAILED: {e}")

# ─── RUN ALL TESTS ───────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "🧪" * 30)
    print("AIN NEWS MONITOR - COMPREHENSIVE SYSTEM TEST")
    print("🧪" * 30)
    
    test("1. Server Health", test_health)
    test("2. Auth Blocked (unauthenticated)", test_auth_blocked)
    test("3. Login", test_login)
    test("4. Get Keywords (current)", test_get_keywords)
    test("5. Delete All Keywords (clean state)", test_delete_all_keywords)
    test("6. Monitor Status (no keywords)", test_monitor_no_keywords)
    
    # Add a keyword and test
    print(f"\n{'='*60}")
    print(f"TEST: 7. Add Keyword")
    print(f"{'='*60}")
    kw_id = test_add_keyword("السعودية")
    
    test("8. Add Duplicate Keyword", lambda: test_add_duplicate_keyword("السعودية"))
    test("9. Articles Endpoint", test_articles)
    test("10. Toggle Keyword", lambda: test_toggle_keyword(kw_id))
    # Toggle back
    if kw_id:
        session.post(f"{BASE}/api/keywords/{kw_id}/toggle")
    
    test("11. Sources & Countries", test_sources_countries)
    test("12. Top Headlines", test_top_headlines)
    test("13. External Headlines", test_external_headlines)
    test("14. Cleanup Status", test_cleanup_status)
    test("15. Monitor Controls (stop/start)", test_monitor_controls)
    test("16. Keyword Limit (max 5)", test_keyword_limit)
    test("17. User Profile", test_user_profile)
    test("18. Exports", test_exports)
    test("19. Python Imports", test_imports)
    
    # Final cleanup - delete the test keyword
    if kw_id:
        session.delete(f"{BASE}/api/keywords/{kw_id}")
        print(f"\n  🧹 Cleaned up test keyword ID:{kw_id}")
    
    # ─── SUMMARY ──────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"TEST SUMMARY")
    print(f"{'='*60}")
    print(f"  ✅ PASSED: {PASS}")
    print(f"  ❌ FAILED: {FAIL}")
    print(f"  ⚠️  WARNINGS: {WARN}")
    total = PASS + FAIL
    if FAIL == 0:
        print(f"\n  🎉 ALL {total} TESTS PASSED!")
    else:
        print(f"\n  ⚠️  {FAIL} FAILURES - FIX BEFORE DEPLOY")
    print(f"{'='*60}\n")
    
    sys.exit(1 if FAIL > 0 else 0)
