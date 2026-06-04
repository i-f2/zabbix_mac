# -*- coding: utf-8 -*-
"""
环境检查测试 - 验证数据库和 Zabbix API 连接
"""

import os
import sys
import pytest
import psycopg2
from psycopg2.extras import DictCursor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入项目配置
try:
    import zabbix_mac
    import app
except ImportError:
    pass


class TestEnvironmentCheck:
    """环境检查测试"""

    def test_postgres_connection(self):
        """测试 PostgreSQL 数据库连接"""
        db_config = {
            'host': os.environ.get('TEST_DB_HOST', 'localhost'),
            'port': int(os.environ.get('TEST_DB_PORT', 5432)),
            'database': os.environ.get('TEST_DB_NAME', 'zabbix_mac'),
            'user': os.environ.get('TEST_DB_USER', 'fan'),
            'password': os.environ.get('TEST_DB_PASSWORD', ''),
            'client_encoding': 'utf8'
        }

        try:
            conn = psycopg2.connect(**db_config)
            conn.set_client_encoding('utf8')
            assert conn is not None
            conn.close()
            print("✓ PostgreSQL 连接成功")
        except psycopg2.OperationalError as e:
            pytest.skip(f"PostgreSQL 连接失败: {e}")

    def test_database_tables_exist(self):
        """检查数据库表是否存在"""
        db_config = {
            'host': os.environ.get('TEST_DB_HOST', 'localhost'),
            'port': int(os.environ.get('TEST_DB_PORT', 5432)),
            'database': os.environ.get('TEST_DB_NAME', 'zabbix_mac'),
            'user': os.environ.get('TEST_DB_USER', 'fan'),
            'password': os.environ.get('TEST_DB_PASSWORD', ''),
            'client_encoding': 'utf8'
        }

        required_tables = [
            'items',
            'triggers',
            'discovery_rules',
            'filter_conditions',
            'item_prototypes',
            'trigger_prototypes',
            'hosts'
        ]

        try:
            conn = psycopg2.connect(**db_config)
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_type = 'BASE TABLE'
                """)
                existing_tables = {row['table_name'] for row in cur.fetchall()}

                missing_tables = set(required_tables) - existing_tables
                if missing_tables:
                    pytest.skip(f"缺少表: {missing_tables}")

                print(f"✓ 所有必需表存在: {', '.join(required_tables)}")
            conn.close()
        except psycopg2.OperationalError as e:
            pytest.skip(f"数据库连接失败: {e}")

    def test_review_tables_exist(self):
        """检查复核表是否存在"""
        db_config = {
            'host': os.environ.get('TEST_DB_HOST', 'localhost'),
            'port': int(os.environ.get('TEST_DB_PORT', 5432)),
            'database': os.environ.get('TEST_DB_NAME', 'zabbix_mac'),
            'user': os.environ.get('TEST_DB_USER', 'fan'),
            'password': os.environ.get('TEST_DB_PASSWORD', ''),
            'client_encoding': 'utf8'
        }

        required_review_tables = [
            'items_review',
            'triggers_review',
            'item_prototypes_review',
            'trigger_prototypes_review'
        ]

        try:
            conn = psycopg2.connect(**db_config)
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_type = 'BASE TABLE'
                """)
                existing_tables = {row['table_name'] for row in cur.fetchall()}

                missing_tables = set(required_review_tables) - existing_tables
                if missing_tables:
                    print(f"⚠ 缺少复核表: {missing_tables}")
                else:
                    print(f"✓ 所有复核表存在: {', '.join(required_review_tables)}")
            conn.close()
        except psycopg2.OperationalError as e:
            pytest.skip(f"数据库连接失败: {e}")

    def test_zabbix_api_connection(self):
        """测试 Zabbix API 连接（需要真实 Zabbix 环境）"""
        url = os.environ.get('TEST_ZABBIX_URL')
        username = os.environ.get('TEST_ZABBIX_USERNAME')
        password = os.environ.get('TEST_ZABBIX_PASSWORD')

        if not all([url, username, password]):
            pytest.skip("未设置 Zabbix 环境变量")

        try:
            from pyzabbix import ZabbixAPI

            api = ZabbixAPI(url)
            api.login(username, password)
            version = api.api_version()
            assert version is not None
            print(f"✓ Zabbix API 连接成功，版本: {version}")
            api.logout()
        except Exception as e:
            pytest.skip(f"Zabbix API 连接失败: {e}")

    def test_project_files_exist(self):
        """检查核心项目文件是否存在"""
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        required_files = [
            'zabbix_mac.py',
            'app.py',
            'CODE_WIKI.md',
            'docker-compose.yml'
        ]

        missing_files = []
        for file in required_files:
            file_path = os.path.join(base_path, file)
            if not os.path.exists(file_path):
                missing_files.append(file)

        if missing_files:
            pytest.fail(f"缺少文件: {missing_files}")

        print(f"✓ 所有核心文件存在: {', '.join(required_files)}")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])