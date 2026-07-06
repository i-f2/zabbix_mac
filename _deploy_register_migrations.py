#!/usr/bin/env python3
"""Register already-applied migrations in tracking table"""
import psycopg2, sys, os

conn = psycopg2.connect(
    host='localhost',
    port=5432,
    database='ops',
    user='postgres',
    password='',
)
cur = conn.cursor()

migrations = [
    ('018', 'add_review_unique_constraints'),
    ('019', 'add_inroom_field'),
    ('020', 'add_inroom_to_review'),
    ('021', 'create_web_trigger_review'),
    ('022', 'add_inroom_to_remaining_review_tables'),
    ('023', 'add_diff_sync_fields'),
]

for ver, desc in migrations:
    cur.execute("SELECT COUNT(*) FROM zabbix_mac.schema_migrations WHERE version = %s", (ver,))
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO zabbix_mac.schema_migrations (version, description) VALUES (%s, %s)", (ver, desc))
        print(f'REGISTERED {ver} {desc}')
    else:
        print(f'ALREADY REGISTERED {ver} {desc}')

conn.commit()
cur.close()
conn.close()
print('Done')
