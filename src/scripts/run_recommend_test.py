import json, time, urllib.request, urllib.error
base='http://localhost:8000'
email=f'test_{int(time.time())}@example.com'
password='Password123!'
register_payload={'email':email,'password':password,'full_name':'Test User'}
req=urllib.request.Request(base+'/api/v1/auth/register',data=json.dumps(register_payload).encode(),headers={'Content-Type':'application/json'})
with urllib.request.urlopen(req) as resp:
    token=json.loads(resp.read())['access_token']
    print('token', token[:20])
recommend_payload={'weight':37,'height':167,'activity':'moderate','age':22,'sex':'female','goal_type':'gain','gain_speed':'moderate','items_per_meal':4}
req2=urllib.request.Request(base+'/api/v1/recommendations',data=json.dumps(recommend_payload).encode(),headers={'Content-Type':'application/json','Authorization':f'Bearer {token}'})
try:
    with urllib.request.urlopen(req2) as r:
        b=r.read().decode()
        print('OK', b[:400])
except urllib.error.HTTPError as e:
    print('HTTP', e.code, e.read().decode())
except Exception as e:
    print('ERR', e)
