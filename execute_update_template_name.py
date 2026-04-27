#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
执行 SQL 脚本更新 template_name 字段值
"""

import psycopg2
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('update_template_name')

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'zabbix_mac',
    'user': 'fan',
    'password': ''
}

def update_template_name():
    """更新 template_name 字段值"""
    try:
        # 连接数据库
        logger.info("连接数据库...")
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = True
        cursor = conn.cursor()
        
        # 1. 更新 items 表
        logger.info("更新 items 表...")
        cursor.execute("""
            UPDATE items SET template_name = '21001' WHERE template_name = 'Template OS Linux by Zabbix agent - Standardized'
        """)
        logger.info(f"更新了 {cursor.rowcount} 条记录")
        
        # 2. 更新 triggers 表
        logger.info("更新 triggers 表...")
        cursor.execute("""
            UPDATE triggers SET template_name = '21001' WHERE template_name = 'Template OS Linux by Zabbix agent - Standardized'
        """)
        logger.info(f"更新了 {cursor.rowcount} 条记录")
        
        # 3. 更新 discovery_rules 表
        logger.info("更新 discovery_rules 表...")
        cursor.execute("""
            UPDATE discovery_rules SET template_name = '21001' WHERE template_name = 'Template OS Linux by Zabbix agent - Standardized'
        """)
        logger.info(f"更新了 {cursor.rowcount} 条记录")
        
        # 4. 更新 templates 表
        logger.info("更新 templates 表...")
        cursor.execute("""
            UPDATE templates SET name = '21001' WHERE name = 'Template OS Linux by Zabbix agent - Standardized'
        """)
        logger.info(f"更新了 {cursor.rowcount} 条记录")
        
        # 关闭连接
        cursor.close()
        conn.close()
        
        logger.info("更新完成！")
        return True
        
    except Exception as e:
        logger.error(f"更新失败: {e}")
        return False

if __name__ == "__main__":
    update_template_name()