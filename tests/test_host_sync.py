# -*- coding: utf-8 -*-
"""
主机资产同步测试 — /host/sync 多模板拆分

覆盖: template_id 逗号拆分解析、按 (name, template_id) 幂等 UPSERT、
模板减少时清理 stale 绑定、手动主机不受影响、无模板跳过。
"""
import os
import sys
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ---- Fixtures ----

@pytest.fixture(scope='module')
def mock_config():
    """全局 mock 配置"""
    return {
        'app': {'secret_key': 'test-secret-key-for-testing', 'host': '127.0.0.1',
                'port': 5050, 'debug': False, 'default_template_name': '21001'},
        'database': {'host': 'localhost', 'port': 5432, 'name': 'ops',
                     'user': 'postgres', 'password': '', 'client_encoding': 'utf8',
                     'schema': 'zabbix_mac'},
        'zabbix_environments': [
            {'key': 'test_env', 'name': '测试环境', 'url': 'http://localhost/api_jsonrpc.php',
             'username': 'Admin', 'password': 'zabbix'}
        ],
        'sync': {'default_workers': 5, 'max_retry_attempts': 3, 'retry_delay': 2},
        'zabbix_room_mapping': {},
    }


@pytest.fixture
def app(mock_config):
    """创建 mock Flask 应用 (CSRF 禁用)，get_db_connection 全 mock"""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_conn.cursor.return_value.__exit__.return_value = None

    # 1. 先以 mock 配置导入 app 模块（模块级 load_config 依赖 DB_CONFIG 初始化）
    with patch('config_loader.load_config', return_value=mock_config):
        if 'app' in sys.modules:
            del sys.modules['app']
        from app import app
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        # 清空 before_request handlers 以绕过 CSRF 验证
        app.before_request_funcs[None] = []

    # 2. 模块对象稳定后再 patch get_db_connection（此前 del+reimport 会使 patch 落在孤儿模块上）
    with patch('app.get_db_connection', return_value=mock_conn):
        app.test_mock_conn = mock_conn
        app.test_mock_cursor = mock_cursor
        yield app


@pytest.fixture
def client(app):
    """测试客户端"""
    return app.test_client()


def _sub_asset(ip, template_id, system='测试系统', subsystem='测试模块',
               hostname='测试主机', in_room='测试机房'):
    return {
        'system': system, 'subsystem': subsystem, 'hostname': hostname,
        'ip': ip, 'template_id': template_id, 'in_room': in_room,
    }


def _host(hid, name, template_id, system=None, subsystem=None, in_room=None, description=None):
    return {
        'id': hid, 'name': name, 'template_id': template_id,
        'system': system, 'subsystem': subsystem, 'in_room': in_room,
        'description': description,
    }


def _sql_calls(mock_cursor, kind):
    """按 SQL 前缀统计 execute 调用"""
    kinds = {'INSERT': 'INSERT INTO hosts', 'UPDATE': 'UPDATE hosts',
             'DELETE': 'DELETE FROM hosts'}
    prefix = kinds[kind]
    return [c for c in mock_cursor.execute.call_args_list
            if c.args and isinstance(c.args[0], str) and c.args[0].lstrip().startswith(prefix)]


def _run_sync(client, app, sub_assets, existing_hosts):
    """设置 mock 数据并执行 /host/sync"""
    app.test_mock_cursor.fetchall.side_effect = [sub_assets, existing_hosts]
    resp = client.post('/host/sync')
    return resp, app.test_mock_cursor


# ---- _parse_template_ids 纯单元测试 ----

class TestParseTemplateIds:
    """模板 ID 拆分解析"""

    def test_single(self):
        from app import _parse_template_ids
        assert _parse_template_ids('21001') == ['21001']

    def test_comma_separated_with_spaces(self):
        from app import _parse_template_ids
        assert _parse_template_ids('21001, 91001,60001') == ['21001', '91001', '60001']

    def test_empty(self):
        from app import _parse_template_ids
        assert _parse_template_ids('') == []

    def test_only_commas_and_spaces(self):
        from app import _parse_template_ids
        assert _parse_template_ids(' , , ') == []

    def test_dedup(self):
        from app import _parse_template_ids
        assert _parse_template_ids('21001,21001, 91001') == ['21001', '91001']

    def test_none(self):
        from app import _parse_template_ids
        assert _parse_template_ids(None) == []


# ---- /host/sync 路由测试 ----

class TestSyncHosts:
    """同步路由行为"""

    def test_split_multi_template_creates_three_hosts(self, client, app):
        """'21001, 91001, 60001' 应拆成 3 条 hosts 记录"""
        sub_assets = [_sub_asset('10.0.0.1', '21001, 91001, 60001')]
        resp, cursor = _run_sync(client, app, sub_assets, [])

        data = resp.get_json()
        assert resp.status_code == 200
        assert data['success'] is True
        assert data['code'] == 200
        assert data['data']['processed_sub_assets'] == 1
        assert data['data']['created_hosts_count'] == 3
        assert data['data']['skipped_count'] == 0

        inserts = _sql_calls(cursor, 'INSERT')
        assert len(inserts) == 3
        params = [c.args[1] for c in inserts]
        tpls = sorted(p[3] for p in params)  # (name, system, subsystem, template_id, description, in_room)
        assert tpls == ['21001', '60001', '91001']
        # 每条记录的 name 都是同一个 ip
        assert all(p[0] == '10.0.0.1' for p in params)

    def test_idempotent_no_duplicates(self, client, app):
        """重复执行不产生重复记录（既有绑定已存在 → 0 新增 0 更新）"""
        sub_assets = [_sub_asset('10.0.0.1', '21001', system='S', subsystem='M', in_room='R')]
        existing = [_host(1, '10.0.0.1', '21001', system='S', subsystem='M', in_room='R', description='测试主机')]
        resp, cursor = _run_sync(client, app, sub_assets, existing)

        data = resp.get_json()
        assert data['data']['created_hosts_count'] == 0
        assert data['data']['updated_hosts_count'] == 0
        assert data['data']['deleted_count'] == 0
        assert _sql_calls(cursor, 'INSERT') == []
        assert _sql_calls(cursor, 'UPDATE') == []
        assert _sql_calls(cursor, 'DELETE') == []

    def test_update_changed_fields(self, client, app):
        """同 (name, template_id) 但字段有变更 → UPDATE"""
        sub_assets = [_sub_asset('10.0.0.1', '21001', system='新系统', in_room='新机房')]
        existing = [_host(1, '10.0.0.1', '21001', system='旧系统', in_room='旧机房', description='测试主机')]
        resp, cursor = _run_sync(client, app, sub_assets, existing)

        data = resp.get_json()
        assert data['data']['updated_hosts_count'] == 1
        updates = _sql_calls(cursor, 'UPDATE')
        assert len(updates) == 1
        assert updates[0].args[1][0] == '新系统'  # system
        assert updates[0].args[1][2] == '新机房'  # in_room

    def test_cleanup_stale_binding(self, client, app):
        """源模板从 '21001,91001' 变为 '21001' → 删除 (ip, 91001) 旧绑定"""
        sub_assets = [_sub_asset('10.0.0.1', '21001')]
        existing = [
            _host(1, '10.0.0.1', '21001'),
            _host(2, '10.0.0.1', '91001'),
        ]
        resp, cursor = _run_sync(client, app, sub_assets, existing)

        data = resp.get_json()
        assert data['data']['deleted_count'] == 1
        deletes = _sql_calls(cursor, 'DELETE')
        assert len(deletes) == 1
        assert deletes[0].args[1] == (2,)

    def test_preserves_manual_hosts(self, client, app):
        """不在源资产中的手动主机不受影响"""
        sub_assets = [_sub_asset('10.0.0.1', '21001')]
        existing = [_host(1, 'manual-host', '99999')]  # 手动主机，不在 sub_assets
        resp, cursor = _run_sync(client, app, sub_assets, existing)

        data = resp.get_json()
        assert data['data']['deleted_count'] == 0
        assert _sql_calls(cursor, 'DELETE') == []

    def test_skip_when_no_valid_template(self, client, app):
        """无有效 template_id → 跳过并记录日志，不产生记录"""
        sub_assets = [_sub_asset('10.0.0.1', ''), _sub_asset('10.0.0.2', ' , , ')]
        resp, cursor = _run_sync(client, app, sub_assets, [])

        data = resp.get_json()
        assert data['data']['skipped_count'] == 2
        assert data['data']['created_hosts_count'] == 0
        assert _sql_calls(cursor, 'INSERT') == []
