# -*- coding: utf-8 -*-
"""
pytest 配置和 fixtures
"""

import os
import sys
import pytest
from unittest.mock import Mock, patch

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 测试环境配置
TEST_DB_CONFIG = {
    'host': os.environ.get('TEST_DB_HOST', 'localhost'),
    'port': int(os.environ.get('TEST_DB_PORT', 5432)),
    'database': os.environ.get('TEST_DB_NAME', 'zabbix_mac'),
    'user': os.environ.get('TEST_DB_USER', 'fan'),
    'password': os.environ.get('TEST_DB_PASSWORD', ''),
    'client_encoding': 'utf8'
}

TEST_ZABBIX_CONFIG = {
    'url': os.environ.get('TEST_ZABBIX_URL', 'http://localhost/api_jsonrpc.php'),
    'username': os.environ.get('TEST_ZABBIX_USERNAME', 'Admin'),
    'password': os.environ.get('TEST_ZABBIX_PASSWORD', 'zabbix'),
}


@pytest.fixture
def db_config():
    """数据库配置 fixture"""
    return TEST_DB_CONFIG


@pytest.fixture
def zabbix_config():
    """Zabbix 配置 fixture"""
    return TEST_ZABBIX_CONFIG


@pytest.fixture
def mock_zabbix_api():
    """模拟 Zabbix API"""
    with patch('pyzabbix.ZabbixAPI') as mock_api:
        client = Mock()
        client.login.return_value = True
        mock_api.return_value = client
        yield client


@pytest.fixture
def mock_db_connection():
    """模拟数据库连接"""
    with patch('psycopg2.connect') as mock_conn:
        mock_cursor = Mock()
        mock_conn.return_value.cursor.return_value = mock_cursor
        yield mock_conn


@pytest.fixture
def sample_host():
    """示例主机数据"""
    return {
        'hostid': '10084',
        'host': 'test-host',
        'name': 'Test Host',
        'interfaces': [
            {
                'interfaceid': '1',
                'ip': '192.168.1.100',
                'port': '10050'
            }
        ]
    }


@pytest.fixture
def sample_item():
    """示例监控项数据"""
    return {
        'itemid': '23296',
        'name': 'CPU Load',
        'key_': 'system.cpu.load',
        'delay': '1m',
        'type': '0',
        'value_type': '0',
        'description': 'CPU load average',
        'status': '0',
        'tags': [{'tag': 'ManagedBy', 'value': 'PythonScript'}]
    }


@pytest.fixture
def sample_trigger():
    """示例触发器数据"""
    return {
        'triggerid': '13508',
        'name': 'High CPU Load',
        'expression': '{test-host:system.cpu.load.last()}>5',
        'priority': '3',
        'status': '0',
        'description': 'CPU load is high',
        'tags': [{'tag': 'ManagedBy', 'value': 'PythonScript'}]
    }


@pytest.fixture
def sample_discovery_rule():
    """示例自动发现规则数据"""
    return {
        'itemid': '23000',
        'name': 'Filesystem Discovery',
        'key_': 'vfs.fs.discovery',
        'delay': '1h',
        'type': '0',
        'status': '0'
    }