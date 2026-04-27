#!/usr/bin/env python3
import psycopg2

# 数据库连接参数
db_config = {
    'host': 'localhost',
    'port': 5433,
    'database': 'zabbix',
    'user': 'zabbix',
    'password': 'zabbix'
}

def main():
    """执行数据库更新脚本"""
    try:
        conn = psycopg2.connect(**db_config)
        print("成功连接到数据库")
        
        # 读取SQL文件
        with open('update_database_schema.sql', 'r') as f:
            sql = f.read()
        
        # 执行SQL
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
        print("数据库架构更新成功！")
        
        conn.close()
    except Exception as e:
        print(f"发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
