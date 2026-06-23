import pymysql
conn = pymysql.connect(host='127.0.0.1', port=3307, user='nutrigain', password='yennhi2602', database='food_recommender')
cur = conn.cursor()
cur.execute('SELECT food_id, name, id FROM foods LIMIT 20')
rows = cur.fetchall()
for r in rows:
    print(r)
cur.close()
conn.close()
