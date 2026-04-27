#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import psycopg2
from psycopg2 import sql

def setup_zabbix_database():
    print("开始设置 Zabbix 数据库...")
    
    # 连接到默认的 postgres 数据库
    conn = None
    try:
        # 第一步：连接到 postgres 数据库创建用户和数据库
        print("1. 连接到默认数据库...")
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            database='postgres',
            user='fan',
            password=''
        )
        conn.autocommit = True
        cur = conn.cursor()
        
        # 检查用户是否已存在
        cur.execute("SELECT 1 FROM pg_roles WHERE rolname='zabbix'")
        if cur.fetchone():
            print("   ⚠️  用户 zabbix 已存在，跳过创建")
        else:
            print("2. 创建 zabbix 用户...")
            cur.execute("CREATE USER zabbix WITH PASSWORD 'zabbix'")
            print("   ✅ 用户创建成功")
        
        # 检查数据库是否已存在
        cur.execute("SELECT 1 FROM pg_database WHERE datname='zabbix'")
        if cur.fetchone():
            print("   ⚠️  数据库 zabbix 已存在，跳过创建")
        else:
            print("3. 创建 zabbix 数据库...")
            cur.execute("CREATE DATABASE zabbix OWNER zabbix")
            print("   ✅ 数据库创建成功")
        
        cur.close()
        conn.close()
        
        # 第二步：连接到 zabbix 数据库设置权限
        print("\n4. 连接到 zabbix 数据库...")
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            database='zabbix',
            user='fan',
            password=''
        )
        conn.autocommit = True
        cur = conn.cursor()
        
        print("5. 授予权限...")
        cur.execute("GRANT ALL PRIVILEGES ON SCHEMA public TO zabbix")
        cur.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO zabbix")
        cur.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO zabbix")
        print("   ✅ 权限设置成功")
        
        cur.close()
        conn.close()
        
        print("\n✅ Zabbix 数据库设置成功！")
        print("\n数据库信息:")
        print("  数据库名: zabbix")
        print("  用户名: zabbix")
        print("  密码: zabbix")
        print("  主机: localhost")
        print("  端口: 5432")
        
    except Exception as e:
        print(f"\n❌ 设置数据库失败: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    setup_zabbix_database()
