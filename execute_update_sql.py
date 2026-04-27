#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import psycopg2
import sys

def execute_sql_file(file_path):
    conn = None
    try:
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            database='zabbix_mac',
            user='fan',
            password=''
        )
        
        cur = conn.cursor()
        
        print(f"正在执行SQL文件: {file_path}")
        
        # 读取并执行SQL文件
        with open(file_path, 'r') as f:
            sql_script = f.read()
        
        # 执行SQL脚本
        cur.execute(sql_script)
        
        conn.commit()
        print("✅ SQL执行成功！")
        
        cur.close()
        
    except Exception as e:
        print(f"❌ 执行失败: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python execute_update_sql.py <sql_file_path>")
        sys.exit(1)
    
    sql_file_path = sys.argv[1]
    execute_sql_file(sql_file_path)