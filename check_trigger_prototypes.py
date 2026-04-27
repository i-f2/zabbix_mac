#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查触发器原型数据
"""

import psycopg2
from psycopg2.extras import DictCursor

# 数据库连接配置
DB_CONFIG = {
    'host': 'localhost',
    'port': 5433,
    'database': 'zabbix',
    'user': 'zabbix',
    'password': 'zabbix'
}

try:
    # 连接数据库
    conn = psycopg2.connect(**DB_CONFIG)
    print("成功连接到 PostgreSQL 数据库")
    
    # 检查触发器原型
    print("\n=== 触发器原型 ===")
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute("SELECT description, expression FROM mac_trigger_prototypes")
        prototypes = cur.fetchall()
        print(f"发现 {len(prototypes)} 个触发器原型:")
        for proto in prototypes:
            print(f"  - {proto['description']}")
            print(f"    表达式: {proto['expression']}")
    
    conn.close()
    print("\n检查完成！")
except Exception as e:
    print(f"数据库连接失败: {e}")
