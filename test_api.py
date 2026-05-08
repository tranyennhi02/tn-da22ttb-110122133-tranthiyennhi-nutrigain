import urllib.request
import json

url = "http://localhost:8000/api/v1/recommendations"
data = {
  "weight": 36,
  "height": 167,
  "activity": "moderate",
  "age": 22,
  "sex": "female",
  "goal_type": "gain",
  "gain_speed": "moderate",
  "items_per_meal": 4
}
req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers={"Content-Type": "application/json"})
try:
    with urllib.request.urlopen(req) as response:
        print("Status:", response.status)
        print("Response:", response.read().decode("utf-8")[:500])
except urllib.error.HTTPError as e:
    print("HTTPError:", e.code)
    print("Response:", e.read().decode("utf-8"))
except Exception as e:
    print("Error:", e)
