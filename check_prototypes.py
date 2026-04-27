#!/usr/bin/env python3
import psycopg2
from psycopg2.extras import DictCursor

# 数据库连接参数
db_config = {
    'host': 'localhost',
    'port': 5433,
    'database': 'zabbix',
    'user': 'zabbix',
    'password': 'zabbix'
}

try:
    # 连接数据库
    conn = psycopg2.connect(**db_config)
    print("成功连接到数据库")
    
    # 检查自动发现规则
    print("\n=== 自动发现规则 ===")
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute("SELECT * FROM mac_discovery_rules")
        rules = cur.fetchall()
        print(f"找到 {len(rules)} 条自动发现规则")
        for rule in rules:
            print(f"规则ID: {rule['id']}, 名称: {rule['name']}, 键: {rule['key']}, 模板: {rule['template_name']}")
    
    # 检查监控项原型
    print("\n=== 监控项原型 ===")
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute("SELECT * FROM mac_item_prototypes")
        item_prototypes = cur.fetchall()
        print(f"找到 {len(item_prototypes)} 个监控项原型")
        for proto in item_prototypes:
            print(f"规则ID: {proto['discovery_rule_id']}, 名称: {proto['name']}, 键: {proto['key']}")
    
    # 检查触发器原型
    print("\n=== 触发器原型 ===")
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute("SELECT * FROM mac_trigger_prototypes")
        trigger_prototypes = cur.fetchall()
        print(f"找到 {len(trigger_prototypes)} 个触发器原型")
        for proto in trigger_prototypes:
            print(f"规则ID: {proto['discovery_rule_id']}, 描述: {proto['description']}")
    
    conn.close()
except Exception as e:
    print(f"数据库连接失败: {e}")
