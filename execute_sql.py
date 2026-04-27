#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import psycopg2

def execute_sql_file():
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
        
        # 1. 创建表 - 按顺序创建，注意依赖关系
        print("正在创建表...")
        
        # 创建 templates 表
        cur.execute("""
            CREATE TABLE IF NOT EXISTS templates (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL UNIQUE,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✓ templates 表创建成功")
        
        # 创建 items 表
        cur.execute("""
            CREATE TABLE IF NOT EXISTS items (
                id SERIAL PRIMARY KEY,
                item_key VARCHAR(255) NOT NULL UNIQUE,
                name VARCHAR(255) NOT NULL,
                type INTEGER NOT NULL,
                value_type INTEGER NOT NULL,
                delay VARCHAR(50) NOT NULL,
                description TEXT,
                units VARCHAR(50),
                multiplier INTEGER DEFAULT 0,
                delta INTEGER DEFAULT 0,
                history INTEGER DEFAULT 7,
                trends INTEGER DEFAULT 365,
                status INTEGER DEFAULT 0,
                template_name VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✓ items 表创建成功")
        
        # 创建 triggers 表
        cur.execute("""
            CREATE TABLE IF NOT EXISTS triggers (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                expression TEXT NOT NULL,
                priority INTEGER NOT NULL,
                description TEXT,
                status INTEGER DEFAULT 0,
                template_name VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✓ triggers 表创建成功")
        
        # 创建 discovery_rules 表
        cur.execute("""
            CREATE TABLE IF NOT EXISTS discovery_rules (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                key VARCHAR(255) NOT NULL,
                delay VARCHAR(50) NOT NULL,
                evaltype INTEGER DEFAULT 0,
                status INTEGER DEFAULT 0,
                template_name VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✓ discovery_rules 表创建成功")
        
        # 创建 filter_conditions 表
        cur.execute("""
            CREATE TABLE IF NOT EXISTS filter_conditions (
                id SERIAL PRIMARY KEY,
                discovery_rule_id INTEGER NOT NULL REFERENCES discovery_rules(id) ON DELETE CASCADE,
                macro VARCHAR(255) NOT NULL,
                value TEXT NOT NULL,
                operator VARCHAR(50) DEFAULT 'MATCHES_REGEX',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✓ filter_conditions 表创建成功")
        
        # 创建 item_prototypes 表
        cur.execute("""
            CREATE TABLE IF NOT EXISTS item_prototypes (
                id SERIAL PRIMARY KEY,
                discovery_rule_id INTEGER NOT NULL REFERENCES discovery_rules(id) ON DELETE CASCADE,
                name VARCHAR(255) NOT NULL,
                key VARCHAR(255) NOT NULL,
                value_type INTEGER NOT NULL,
                delay VARCHAR(50) NOT NULL,
                description TEXT,
                units VARCHAR(50),
                multiplier INTEGER DEFAULT 0,
                delta INTEGER DEFAULT 0,
                history INTEGER DEFAULT 7,
                trends INTEGER DEFAULT 365,
                status INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✓ item_prototypes 表创建成功")
        
        # 创建 trigger_prototypes 表
        cur.execute("""
            CREATE TABLE IF NOT EXISTS trigger_prototypes (
                id SERIAL PRIMARY KEY,
                discovery_rule_id INTEGER NOT NULL REFERENCES discovery_rules(id) ON DELETE CASCADE,
                description TEXT NOT NULL,
                expression TEXT NOT NULL,
                priority INTEGER NOT NULL,
                status INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✓ trigger_prototypes 表创建成功")
        
        # 创建索引
        print("\n正在创建索引...")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_items_item_key ON items(item_key)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_items_template ON items(template_name)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_triggers_template ON triggers(template_name)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_discovery_rules_template ON discovery_rules(template_name)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_filter_conditions_rule ON filter_conditions(discovery_rule_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_item_prototypes_rule ON item_prototypes(discovery_rule_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_trigger_prototypes_rule ON trigger_prototypes(discovery_rule_id)")
        print("✓ 索引创建成功")
        
        conn.commit()
        print("\n✅ 所有表创建成功！")
        
        # 验证表已创建
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        tables = cur.fetchall()
        print(f"\n数据库中的表: {[table[0] for table in tables]}")
        
        cur.close()
        
    except Exception as e:
        print(f"❌ 执行失败: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    execute_sql_file()
