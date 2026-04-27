#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试数据库连接
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
    
    # 测试查询
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute("SELECT * FROM mac_templates LIMIT 1")
        result = cur.fetchone()
        print(f"查询结果: {result}")
    
    conn.close()
    print("数据库连接测试成功")
except Exception as e:
    print(f"数据库连接失败: {e}")
