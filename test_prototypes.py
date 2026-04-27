#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试自动发现规则和原型数据
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
    
    # 检查自动发现规则
    print("\n=== 自动发现规则 ===")
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute("SELECT * FROM mac_discovery_rules")
        rules = cur.fetchall()
        print(f"发现 {len(rules)} 个自动发现规则:")
        for rule in rules:
            print(f"  - {rule['name']} (ID: {rule['id']}, Key: {rule['key']})")
    
    # 检查监控项原型
    print("\n=== 监控项原型 ===")
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute("SELECT * FROM mac_item_prototypes")
        prototypes = cur.fetchall()
        print(f"发现 {len(prototypes)} 个监控项原型:")
        for proto in prototypes[:5]:  # 只显示前 5 个
            print(f"  - {proto['name']} (Key: {proto['key']}, Rule ID: {proto['discovery_rule_id']})")
        if len(prototypes) > 5:
            print(f"  ... 还有 {len(prototypes) - 5} 个监控项原型")
    
    # 检查触发器原型
    print("\n=== 触发器原型 ===")
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute("SELECT * FROM mac_trigger_prototypes")
        prototypes = cur.fetchall()
        print(f"发现 {len(prototypes)} 个触发器原型:")
        for proto in prototypes:
            print(f"  - {proto['description']} (Rule ID: {proto['discovery_rule_id']})")
    
    conn.close()
    print("\n测试完成！")
except Exception as e:
    print(f"数据库连接失败: {e}")
