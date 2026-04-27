#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
执行 SQL 脚本创建 webscenario_items_review 表
"""

import psycopg2
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('create_webscenario_review_table')

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'zabbix_mac',
    'user': 'fan',
    'password': ''
}

def create_webscenario_review_table():
    """创建 webscenario_items_review 表"""
    try:
        # 连接数据库
        logger.info("连接数据库...")
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = True
        cursor = conn.cursor()
        
        # 创建表
        logger.info("创建 webscenario_items_review 表...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS webscenario_items_review (
                id SERIAL PRIMARY KEY,
                system VARCHAR(100) NOT NULL,
                subsystem VARCHAR(100) NOT NULL,
                host VARCHAR(255) NOT NULL DEFAULT 'Zabbix server',
                name VARCHAR(255) NOT NULL,
                url VARCHAR(255) NOT NULL,
                status_code VARCHAR(50) NOT NULL DEFAULT '200',
                modified BOOLEAN DEFAULT FALSE,
                confirmed BOOLEAN DEFAULT FALSE,
                status_verification VARCHAR(50) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 创建索引
        logger.info("创建索引...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_webscenario_items_review_system ON webscenario_items_review(system)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_webscenario_items_review_subsystem ON webscenario_items_review(subsystem)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_webscenario_items_review_host ON webscenario_items_review(host)")
        
        # 关闭连接
        cursor.close()
        conn.close()
        
        logger.info("webscenario_items_review 表创建完成！")
        return True
        
    except Exception as e:
        logger.error(f"创建 webscenario_items_review 表失败: {e}")
        return False

if __name__ == "__main__":
    create_webscenario_review_table()