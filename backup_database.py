#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库备份脚本

功能：
1. 备份Zabbix相关的数据库表
2. 支持修改数据
3. 遇到问题时进行修复
"""

import psycopg2
import json
import os
import time
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('backup_database')

# 自定义JSON编码器，处理datetime类型
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'port': 5433,
    'database': 'zabbix',
    'user': 'zabbix',
    'password': 'zabbix'
}

# 要备份的表
TABLES_TO_BACKUP = [
    'mac_templates',
    'mac_items',
    'mac_triggers',
    'mac_trigger_dependencies',
    'mac_discovery_rules',
    'mac_filter_conditions',
    'mac_item_prototypes',
    'mac_trigger_prototypes'
]

def connect_db():
    """连接数据库"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        logger.info("成功连接到数据库")
        return conn
    except Exception as e:
        logger.error(f"连接数据库失败: {e}")
        raise

def backup_table(conn, table_name):
    """备份单个表"""
    try:
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        
        # 构造备份数据
        backup_data = {
            'table': table_name,
            'columns': columns,
            'rows': rows
        }
        
        # 创建备份目录
        backup_dir = 'database_backup'
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        # 生成备份文件名
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        backup_file = os.path.join(backup_dir, f'{table_name}_{timestamp}.json')
        
        # 写入备份文件
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=2, cls=DateTimeEncoder)
        
        logger.info(f"成功备份表 {table_name} 到 {backup_file}")
        return backup_file
    except Exception as e:
        logger.error(f"备份表 {table_name} 失败: {e}")
        raise

def modify_data(conn):
    """修改数据示例"""
    try:
        cursor = conn.cursor()
        
        # 示例：更新mac_templates表中的描述
        cursor.execute("""
            UPDATE mac_templates 
            SET description = 'Updated template description' 
            WHERE name = 'Template OS Linux by Zabbix agent'
        """)
        
        conn.commit()
        logger.info("成功修改数据")
    except Exception as e:
        logger.error(f"修改数据失败: {e}")
        conn.rollback()
        raise

def check_and_fix_tables(conn):
    """检查并修复表结构"""
    try:
        cursor = conn.cursor()
        
        # 检查是否存在mac_items_total视图
        cursor.execute("""
            SELECT EXISTS(
                SELECT 1 
                FROM information_schema.views 
                WHERE table_name = 'mac_items_total'
            )
        """)
        view_exists = cursor.fetchone()[0]
        
        # 如果视图存在，先删除
        if view_exists:
            logger.info("删除mac_items_total视图")
            cursor.execute("DROP VIEW IF EXISTS mac_items_total")
        
        # 检查mac_items表的history和trends字段类型
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'mac_items' 
            AND column_name IN ('history', 'trends')
        """)
        
        columns = cursor.fetchall()
        for column_name, data_type in columns:
            if data_type != 'character varying':
                logger.info(f"修复表 mac_items 字段 {column_name} 的类型")
                cursor.execute(f"""
                    ALTER TABLE mac_items 
                    ALTER COLUMN {column_name} TYPE VARCHAR(32)
                """)
        
        # 检查mac_item_prototypes表的history和trends字段类型
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'mac_item_prototypes' 
            AND column_name IN ('history', 'trends')
        """)
        
        columns = cursor.fetchall()
        for column_name, data_type in columns:
            if data_type != 'character varying':
                logger.info(f"修复表 mac_item_prototypes 字段 {column_name} 的类型")
                cursor.execute(f"""
                    ALTER TABLE mac_item_prototypes 
                    ALTER COLUMN {column_name} TYPE VARCHAR(32)
                """)
        
        # 重新创建mac_items_total视图
        if view_exists:
            logger.info("重新创建mac_items_total视图")
            cursor.execute("""
                CREATE VIEW mac_items_total AS
                SELECT COUNT(*) as total_items
                FROM mac_items
            """)
        
        conn.commit()
        logger.info("表结构检查和修复完成")
    except Exception as e:
        logger.error(f"检查和修复表结构失败: {e}")
        conn.rollback()
        raise

def main():
    """主函数"""
    conn = None
    try:
        # 连接数据库
        conn = connect_db()
        
        # 检查并修复表结构
        check_and_fix_tables(conn)
        
        # 备份所有表
        for table in TABLES_TO_BACKUP:
            backup_table(conn, table)
        
        # 修改数据
        modify_data(conn)
        
        logger.info("数据库备份和修改操作完成")
    except Exception as e:
        logger.error(f"执行过程中发生错误: {e}")
    finally:
        if conn:
            conn.close()
            logger.info("数据库连接已关闭")

if __name__ == "__main__":
    main()
