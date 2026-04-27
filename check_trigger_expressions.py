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

def main():
    """查询数据库中的触发器表达式"""
    try:
        conn = psycopg2.connect(**db_config)
        print("成功连接到数据库")
        
        # 查询触发器表达式
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("SELECT name, expression FROM mac_triggers LIMIT 10")
            triggers = cur.fetchall()
            print("\n触发器表达式:")
            for trigger in triggers:
                print(f"名称: {trigger['name']}")
                print(f"表达式: {trigger['expression']}")
                print("-")
        
        # 查询触发器原型表达式
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("SELECT description, expression FROM mac_trigger_prototypes LIMIT 10")
            prototypes = cur.fetchall()
            print("\n触发器原型表达式:")
            for proto in prototypes:
                print(f"描述: {proto['description']}")
                print(f"表达式: {proto['expression']}")
                print("-")
        
        conn.close()
    except Exception as e:
        print(f"发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
