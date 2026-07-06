#!/usr/bin/env python3
"""Apply pending database migrations (018-023)"""
import psycopg2, os, sys
sys.path.insert(0, '.')
from config_loader import load_config

cfg = load_config()
db = cfg['database']
conn = psycopg2.connect(host=db['host'], port=db['port'], database=db['name'], user=db['user'], password=db['password'])
cur = conn.cursor()

mig_dir = 'database_update'
files = sorted(f for f in os.listdir(mig_dir) if f.endswith('.sql') and not f.startswith('apply'))

applied = 0
for fname in files:
    ver = fname.split('_')[0]
    cur.execute("SELECT COUNT(*) FROM zabbix_mac.schema_migrations WHERE version = %s", (ver,))
    if cur.fetchone()[0] > 0:
        print(f'SKIP {fname}')
        continue
    with open(os.path.join(mig_dir, fname)) as f:
        cur.execute(f.read())
    desc = fname.replace('.sql', '').split('_', 1)[1] if '_' in fname else ''
    cur.execute("INSERT INTO zabbix_mac.schema_migrations (version, description) VALUES (%s, %s)", (ver, desc))
    conn.commit()
    applied += 1
    print(f'APPLIED {fname}')

print(f'Done: {applied} migrations applied')
cur.close()
conn.close()
