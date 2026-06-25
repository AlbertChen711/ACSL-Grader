"""Quick integration test for the refactored ACSL grader."""
import urllib.request
import urllib.parse
import http.cookiejar
import sys
import time
import subprocess
import os

# Start the Flask app
proc = subprocess.Popen([sys.executable, "app.py"], cwd=os.path.dirname(__file__))
time.sleep(3)

BASE = "http://127.0.0.1:5000"
jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

def get(path):
    return opener.open(f"{BASE}{path}")

def post(path, data):
    return opener.open(f"{BASE}{path}", data=urllib.parse.urlencode(data).encode())

try:
    # 1. Home page
    r = get("/")
    assert r.status == 200, f"Home failed: {r.status}"
    print(f"PASS Home: {r.status}")

    # 2. Signup
    r = post("/signup", {"email": "a@b.com", "password": "x", "confirm": "x"})
    assert r.status == 200 or r.url.endswith("/login"), f"Signup failed: {r.status} {r.url}"
    print(f"PASS Signup: {r.status}")

    # 3. Login
    r = post("/login", {"email": "a@b.com", "password": "x"})
    assert r.status == 200 or r.url.endswith("/"), f"Login failed: {r.status}"
    print(f"PASS Login: {r.status}")

    # 4. Home page shows years
    r = get("/")
    content = r.read().decode()
    assert "2025-2026" in content, "Year 2025-2026 not on home page"
    assert "2024-2025" in content, "Year 2024-2025 not on home page"
    print(f"PASS Home years: found 2024-2025, 2025-2026")

    # 5. Season page
    r = get("/2025-2026")
    content = r.read().decode()
    assert "2025-2026" in content, "Season year not in page"
    assert "Junior" in content, "Division Junior not in page"
    assert "contest1" in content or "Contest 1" in content, "Contest link not in page"
    print(f"PASS Season 2025-2026")

    # 6. Contest page
    r = get("/2025-2026/junior/contest1")
    content = r.read().decode()
    assert "Creature Capture" in content, "Problem name not found"
    assert "2025-2026" in content, "Year not in breadcrumb"
    assert "junior" in content or "Junior" in content, "Division not in page"
    assert "Contest1" in content, "Contest not in page"
    print(f"PASS Contest 2025-2026/junior/contest1: Creature Capture")

    # 7. 2024-2025 season
    r = get("/2024-2025")
    content = r.read().decode()
    assert "2024-2025" in content, "2024-2025 season year not in page"
    assert "contest1" in content, "contest1 not in 2024-2025 season"
    print(f"PASS Season 2024-2025")

    # 8. 2024-2025 contest
    r = get("/2024-2025/junior/contest1")
    content = r.read().decode()
    assert "Rings" in content, "Problem name 'Rings' not found"
    assert "2024-2025" in content, "Year not found in 2024-2025 contest page"
    print(f"PASS Contest 2024-2025/junior/contest1: Rings")

    # 9. 404 for nonexistent contest
    try:
        r = get("/2024-2025/junior/nonexistent")
        content = r.read().decode()
        assert "not found" in content.lower(), "404 page should contain 'not found'"
        print(f"PASS 404: nonexistent contest shows error page")
    except urllib.error.HTTPError as e:
        assert e.code == 404, f"Expected 404, got {e.code}"
        print(f"PASS 404: HTTP {e.code}")

    print("\n=== ALL TESTS PASSED ===")

finally:
    proc.terminate()
    proc.wait()
