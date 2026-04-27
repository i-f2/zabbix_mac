#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
执行 SQL 脚本创建 webscenario_items 表
"""

import psycopg2
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('create_webscenario_table')

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'zabbix_mac',
    'user': 'fan',
    'password': ''
}

def create_webscenario_table():
    """创建 webscenario_items 表"""
    try:
        # 连接数据库
        logger.info("连接数据库...")
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = True
        cursor = conn.cursor()
        
        # 创建表
        logger.info("创建 webscenario_items 表...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS webscenario_items (
                id SERIAL PRIMARY KEY,
                system VARCHAR(100) NOT NULL,
                subsystem VARCHAR(100) NOT NULL,
                nginx_clb VARCHAR(255),
                nginx VARCHAR(255),
                clb VARCHAR(255),
                pod VARCHAR(255),
                webtest_api VARCHAR(255) NOT NULL,
                webtest_nginx_api VARCHAR(255) NOT NULL,
                in_room VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 创建索引
        logger.info("创建索引...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_webscenario_items_system ON webscenario_items(system)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_webscenario_items_subsystem ON webscenario_items(subsystem)")
        
        # 插入示例数据
        logger.info("插入示例数据...")
        cursor.execute("""
            INSERT INTO webscenario_items (
                system, subsystem, nginx_clb, nginx, clb, pod, 
                webtest_api, webtest_nginx_api, in_room
            ) VALUES
            ('Test System', 'Test Subsystem', '192.168.1.1:8080', '192.168.1.2:8080', '192.168.1.3:8080', '192.168.1.4:8080',
             '/api/test', '/nginx/api/test', 'Room A'),
            ('Another System', 'Another Subsystem', '192.168.2.1:8080', '192.168.2.2:8080', '192.168.2.3:8080', '192.168.2.4:8080',
             '/api/another', '/nginx/api/another', 'Room B')
            ON CONFLICT DO NOTHING
        """)
        
        # 关闭连接
        cursor.close()
        conn.close()
        
        logger.info("webscenario_items 表创建完成！")
        return True
        
    except Exception as e:
        logger.error(f"创建 webscenario_items 表失败: {e}")
        return False

if __name__ == "__main__":
    create_webscenario_table()