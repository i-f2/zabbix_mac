#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import psycopg2

def check_postgres_config():
    print("检查 PostgreSQL 配置...")
    
    try:
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            database='postgres',
            user='fan',
            password=''
        )
        cur = conn.cursor()
        
        # 检查监听地址
        print("\n1. 检查监听地址:")
        cur.execute("SHOW listen_addresses")
        listen_addr = cur.fetchone()[0]
        print(f"   listen_addresses = {listen_addr}")
        
        # 检查端口
        print("\n2. 检查端口:")
        cur.execute("SHOW port")
        port = cur.fetchone()[0]
        print(f"   port = {port}")
        
        # 检查数据目录
        print("\n3. 检查数据目录:")
        cur.execute("SHOW data_directory")
        data_dir = cur.fetchone()[0]
        print(f"   data_directory = {data_dir}")
        
        # 检查配置文件
        print("\n4. 检查配置文件:")
        cur.execute("SHOW config_file")
        config_file = cur.fetchone()[0]
        print(f"   config_file = {config_file}")
        
        # 检查 hba_file
        print("\n5. 检查 HBA 文件:")
        cur.execute("SHOW hba_file")
        hba_file = cur.fetchone()[0]
        print(f"   hba_file = {hba_file}")
        
        cur.close()
        conn.close()
        
        print("\n✅ 配置检查完成！")
        
        # 给出建议
        if listen_addr != '*':
            print(f"\n⚠️  建议: 将 listen_addresses 改为 '*' 以允许 Docker 容器连接")
            print(f"   配置文件: {config_file}")
        
    except Exception as e:
        print(f"\n❌ 检查失败: {e}")

if __name__ == "__main__":
    check_postgres_config()
