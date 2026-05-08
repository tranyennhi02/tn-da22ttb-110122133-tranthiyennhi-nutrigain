import pymysql
import sys
ids = ['171662','173777','170142','167697']
conn = pymysql.connect(host='127.0.0.1', port=3307, user='nutrigain', password='yennhi2602', database='food_recommender')
cur = conn.cursor()
for fid in ids:
    cur.execute('SELECT id, food_id, name FROM foods WHERE food_id=%s LIMIT 1', (fid,))
    r = cur.fetchone()
    print(fid, '->', r)
cur.close(); conn.close()
