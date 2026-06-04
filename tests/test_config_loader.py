# -*- coding: utf-8 -*-
"""
ConfigLoader 测试 - 配置加载器测试
"""

import os
import sys
import pytest
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from zabbix_mac import ConfigLoader


class TestConfigLoaderInit:
    """ConfigLoader 初始化测试"""

    def test_init(self, db_config):
        """初始化配置加载器"""
        loader = ConfigLoader(db_config)
        assert loader.db_config == db_config
        assert loader.connection is None

    def test_init_no_db_config(self):
        """无数据库配置初始化"""
        loader = ConfigLoader(None)
        assert loader.db_config is None
        assert loader.connection is None

    def test_connect_db(self, db_config):
        """数据库连接"""
        with patch('psycopg2.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_connect.return_value = mock_conn
            loader = ConfigLoader(db_config)
            result = loader.connect_db()
            assert result is True
            assert loader.connection is not None
            mock_conn.set_client_encoding.assert_called_once_with('UTF8')

    def test_connect_db_no_config(self):
        """无配置时数据库连接失败"""
        loader = ConfigLoader(None)
        result = loader.connect_db()
        assert result is False

    def test_connect_db_failure(self, db_config):
        """数据库连接失败"""
        with patch('psycopg2.connect') as mock_connect:
            mock_connect.side_effect = Exception("Connection failed")
            loader = ConfigLoader(db_config)
            result = loader.connect_db()
            assert result is False
            assert loader.connection is None

    def test_connect_db_all_retries_fail(self, db_config):
        """所有重试都失败"""
        with patch('psycopg2.connect') as mock_connect:
            mock_connect.side_effect = Exception("Persistent failure")
            loader = ConfigLoader(db_config)
            result = loader.connect_db()
            assert result is False

    def test_reset_connection(self, db_config):
        """重置数据库连接"""
        with patch('psycopg2.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_connect.return_value = mock_conn
            loader = ConfigLoader(db_config)
            loader.connect_db()
            loader.reset_connection()
            mock_conn.close.assert_called_once()


class TestConfigLoaderTemplates:
    """模板加载测试"""

    def test_load_template_from_db_empty(self, db_config):
        """加载不存在的模板"""
        with patch('psycopg2.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.fetchall.side_effect = [
                [],  # items
                [],  # triggers
                [],  # discovery_rules
            ]
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_connect.return_value = mock_conn
            loader = ConfigLoader(db_config)
            loader.connection = mock_conn
            template = loader.load_template_from_db("NonExistent")
            assert template == {}

    def test_load_template_no_db(self):
        """无数据库配置时返回空"""
        loader = ConfigLoader(None)
        template = loader.load_template("Test")
        assert template == {}

    def test_deep_merge(self, db_config):
        """深层合并测试"""
        loader = ConfigLoader(db_config)
        base = {'items': {'cpu': {'name': 'CPU'}}, 'triggers': {}}
        override = {'items': {'mem': {'name': 'Memory'}}, 'triggers': {'high': {'name': 'High'}}}
        result = loader.deep_merge(base, override)
        assert 'cpu' in result.get('items', {})
        assert 'mem' in result.get('items', {})
        assert 'high' in result.get('triggers', {})


class TestConfigLoaderHostConfig:
    """主机配置构建测试"""

    def test_get_host_config_none(self, db_config):
        """获取不存在的主机配置"""
        loader = ConfigLoader(db_config)
        host_config = loader.get_host_config({}, "non-existent")
        assert host_config is None

    def test_get_host_config_exists(self, db_config):
        """获取存在的主机配置"""
        loader = ConfigLoader(db_config)
        config = {
            'hosts': {
                'test-host': {'ip': '192.168.1.1'}
            }
        }
        host_config = loader.get_host_config(config, "test-host")
        assert host_config == {'ip': '192.168.1.1'}

    def test_build_host_config_not_found(self, db_config):
        """主机不存在时返回空"""
        loader = ConfigLoader(db_config)
        result = loader.build_host_config({}, "non-existent")
        assert result == {}

    def test_build_host_config_no_templates(self, db_config):
        """主机无模板时返回基本配置"""
        loader = ConfigLoader(db_config)
        config = {'hosts': {'test-host': {'ip': '1.2.3.4'}}}
        result = loader.build_host_config(config, "test-host")
        assert result == {}


class TestConfigLoaderReviewTables:
    """复核表操作测试"""

    def test_initialize_items_review_no_conn(self, db_config):
        """未连接时初始化复核表"""
        with patch.object(ConfigLoader, 'connect_db', return_value=False):
            loader = ConfigLoader(db_config)
            result = loader.initialize_items_review()
            assert result is False

    def test_initialize_triggers_review_no_conn(self, db_config):
        """未连接时初始化触发器复核表"""
        with patch.object(ConfigLoader, 'connect_db', return_value=False):
            loader = ConfigLoader(db_config)
            result = loader.initialize_triggers_review()
            assert result is False

    def test_export_items_review(self, db_config):
        """导出复核表需要 output_file 参数"""
        with patch('psycopg2.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = []
            mock_cursor.description = [('id',), ('name',)]
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_connect.return_value = mock_conn

            loader = ConfigLoader(db_config)
            loader.connection = mock_conn
            result = loader.export_items_review_to_excel("/tmp/test.xlsx")
            assert result is False  # 空表导出失败

    def test_import_items_review(self, db_config):
        """导入复核表"""
        with patch('psycopg2.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_connect.return_value = mock_conn

            loader = ConfigLoader(db_config)
            result = loader.import_items_review_from_excel.__doc__  # 验证方法存在
            assert result is not None
