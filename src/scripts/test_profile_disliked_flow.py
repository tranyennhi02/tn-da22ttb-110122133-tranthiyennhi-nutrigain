import json
import urllib.request
import urllib.parse
import sys

BASE = "http://localhost:8000"
EMAIL = "nhi96942@gmail.com"
PASSWORD = "password123"

def req(method, path, token=None, data=None):
    url = BASE + path
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if data is not None:
        body = json.dumps(data).encode('utf-8')
        headers["Content-Type"] = "application/json"
    else:
        body = None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.getcode(), json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        try:
            payload = e.read().decode('utf-8')
            return e.code, json.loads(payload)
        except Exception:
            return e.code, {"error": str(e)}
    except Exception as e:
        return None, {"error": str(e)}


def main():
    print("1) Reset password & clear profile via debug-db-reset")
    code, res = req("POST", f"/api/v1/debug-db-reset?email={urllib.parse.quote(EMAIL)}")
    print(code, res)

    print("2) Login")
    code, res = req("POST", "/api/v1/auth/login", data={"email": EMAIL, "password": PASSWORD})
    print(code, res)
    if code != 200 or "access_token" not in res:
        print("Login failed, aborting")
        sys.exit(1)
    token = res["access_token"]

    print("3) GET /api/v1/users/me (before)")
    code, me = req("GET", "/api/v1/users/me", token=token)
    print(code, json.dumps(me, indent=2, ensure_ascii=False))

    profile = me.get("profile") or {}

    payload = {
        "weight_kg": 38,
        "height_cm": 167,
        "target_weight_kg": 56,
        "favorite_foods": [],
        "disliked_foods": [],
        "disliked_food_groups": profile.get("disliked_food_groups", []),
        "age": profile.get("age"),
        "sex": profile.get("sex"),
        "gender": profile.get("gender"),
        "activity_level": profile.get("activity_level", "moderate"),
        "surplus_kcal": profile.get("surplus_kcal"),
        "weight_gain_speed": profile.get("weight_gain_speed"),
        "diet_type": profile.get("diet_type"),
        "budget_level": profile.get("budget_level"),
        "items_per_meal": profile.get("items_per_meal"),
    }

    # Remove keys with None to avoid changing unintended fields
    payload = {k: v for k, v in payload.items() if v is not None}

    print("4) PUT /api/v1/users/me/profile with payload:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    code, res = req("PUT", "/api/v1/users/me/profile", token=token, data=payload)
    print(code, json.dumps(res, indent=2, ensure_ascii=False))

    print("5) GET /api/v1/users/me (immediately after PUT)")
    code, me2 = req("GET", "/api/v1/users/me", token=token)
    print(code, json.dumps(me2, indent=2, ensure_ascii=False))

    print("6) Re-login to simulate reload/login")
    code, res = req("POST", "/api/v1/auth/login", data={"email": EMAIL, "password": PASSWORD})
    print(code, res)
    if code != 200 or "access_token" not in res:
        print("Re-login failed")
        sys.exit(1)
    token2 = res["access_token"]

    print("7) GET /api/v1/users/me (after re-login)")
    code, me3 = req("GET", "/api/v1/users/me", token=token2)
    print(code, json.dumps(me3, indent=2, ensure_ascii=False))

    print("8) GET /api/v1/weight-logs/summary (to produce weight summary logs)")
    code, summary = req("GET", "/api/v1/weight-logs/summary", token=token2)
    print(code, json.dumps(summary, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    main()
