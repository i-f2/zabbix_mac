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
    
    # 检查监控项原型的delay字段
    print("\n=== 监控项原型的delay字段 ===")
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute("SELECT id, name, key, delay FROM mac_item_prototypes")
        item_prototypes = cur.fetchall()
        for proto in item_prototypes:
            print(f"ID: {proto['id']}, 名称: {proto['name']}, 键: {proto['key']}, delay: {proto['delay']}")
    
    # 检查触发器原型
    print("\n=== 触发器原型 ===")
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute("SELECT id, description, expression, priority FROM mac_trigger_prototypes")
        trigger_prototypes = cur.fetchall()
        for proto in trigger_prototypes:
            print(f"ID: {proto['id']}, 描述: {proto['description']}, 表达式: {proto['expression']}, 优先级: {proto['priority']}")
    
    conn.close()
except Exception as e:
    print(f"数据库连接失败: {e}")
