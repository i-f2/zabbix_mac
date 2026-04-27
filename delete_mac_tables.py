#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import psycopg2

# 数据库连接参数
db_config = {
    'host': 'localhost',
    'port': 5432,
    'database': 'zabbix_mac',
    'user': 'fan',
    'password': ''
}

try:
    # 连接到数据库
    conn = psycopg2.connect(**db_config)
    conn.autocommit = True
    cursor = conn.cursor()
    
    # 查找所有以 'mac' 开头的表
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_name LIKE 'mac%' 
        AND table_schema = 'public'
    """)
    
    tables = cursor.fetchall()
    
    if not tables:
        print("没有找到以 'mac' 开头的表")
    else:
        print(f"找到 {len(tables)} 个以 'mac' 开头的表:")
        for table in tables:
            table_name = table[0]
            print(f"- {table_name}")
            
            # 删除表
            try:
                cursor.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE")
                print(f"  ✓ 已删除表 {table_name}")
            except Exception as e:
                print(f"  ✗ 删除表 {table_name} 失败: {e}")
    
    # 关闭连接
    cursor.close()
    conn.close()
    print("\n操作完成")
    
except Exception as e:
    print(f"连接数据库失败: {e}")
