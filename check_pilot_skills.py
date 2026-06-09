from dotenv import load_dotenv
load_dotenv('.env.local')
import os, psycopg2
conn = psycopg2.connect(os.getenv('RAILWAY_DATABASE_URL'), sslmode='require')
cur = conn.cursor()
cur.execute("""
SELECT e.nombre, e.id, ms.skill_normalized, ms.tipo_skill
FROM especializaciones e
JOIN microcurriculos m ON m.specialization_id = e.id
JOIN microcurriculo_skills ms ON ms.microcurriculo_id = m.id
WHERE e.id IN (92, 94, 108)
ORDER BY e.id, ms.tipo_skill
""")
rows = cur.fetchall()
prog = None
for row in rows:
    if row[0] != prog:
        prog = row[0]
        print(f"\n{prog} (id={row[1]}):")
    print(f"  {row[2]} ({row[3]})")
print(f"\nTotal skills: {len(rows)}")
conn.close()
