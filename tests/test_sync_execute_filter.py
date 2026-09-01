# -*- coding: utf-8 -*-
"""
/api/sync/execute LLD Filter 绑定回归测试

背景：监控项原型 / 触发器原型同步时，若 discovery_rules 配置未附带
filter_conditions（_conditions），ensure_discovery_rule 创建 LLD 规则时
filter 为空 → Zabbix 自动发现规则过滤器未绑定任何条目。

修复前 api_sync_execute 的两个原型分支用裸 SELECT 加载 dr 配置，
不带 _conditions；修复后改为 _load_dr_configs_with_filters。
本测试驱动真实路由，断言 ensure_discovery_rule 收到的 dr_cfg 携带 _conditions。
"""
import os
import sys
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_TEST_CONFIG = {
    'app': {'secret_key': 'k', 'host': '127.0.0.1', 'port': 5050, 'debug': False,
            'default_template_name': '21001'},
    'database': {'host': 'localhost', 'port': 5432, 'name': 'ops',
                 'user': 'postgres', 'password': '', 'client_encoding': 'utf8',
                 'schema': 'zabbix_mac'},
    'zabbix_environments': [],
    'sync': {'default_workers': 5, 'max_retry_attempts': 3, 'retry_delay': 2},
    'zabbix_room_mapping': {},
}

_TEST_ENV = {'test': {'url': 'http://t/api', 'username': 'u', 'password': 'p'}}


@pytest.fixture(scope='module')
def app_module():
    """在 mock 配置下导入 app 模块（CSRF 禁用），返回模块对象本身。

    返回模块而非 flask app，便于按模块全局打 patch——路由函数在导入时
    绑定到该模块的全局命名空间，patch app_module.get_db_connection 等
    才能命中路由实际查找的符号。
    """
    with patch('config_loader.load_config', return_value=_TEST_CONFIG):
        if 'app' in sys.modules:
            del sys.modules['app']
        import app as app_module
        app_module.app.config['TESTING'] = True
        app_module.app.config['WTF_CSRF_ENABLED'] = False
        app_module.app.before_request_funcs[None] = []
        yield app_module


class _RouteCursor:
    """可编程路由游标：fetchall 按注入队列依次弹出。"""

    def __init__(self, fetchall_queue=None):
        self._queue = list(fetchall_queue) if fetchall_queue else []
        self.executes = []

    def execute(self, sql, params=None):
        self.executes.append((sql, params))

    def fetchall(self):
        return self._queue.pop(0) if self._queue else []

    def fetchone(self):
        return None

    def executemany(self, sql, seq):
        self.executes.append((sql, seq))

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class _RouteConn:
    """路由主连接：cursor() 依次返回注入的游标。"""

    def __init__(self, cursors):
        self._cursors = list(cursors)

    def cursor(self, cursor_factory=None):
        return self._cursors.pop(0)

    def commit(self):
        pass

    def rollback(self):
        raise AssertionError('成功路径不应触发 rollback')

    def close(self):
        pass


def _run_sync_execute(app_module, action_type, host_rows, dr_rows, cond_rows,
                      is_trigger=False):
    """POST /api/sync/execute，返回 (response, mock_client)。"""
    conn = _RouteConn([
        _RouteCursor([host_rows]),          # SELECT * FROM <table>
        _RouteCursor([dr_rows, cond_rows]),  # _load_dr_configs_with_filters
    ])
    uconn = MagicMock()  # 同步后更新 sync_status 的连接

    mock_client = MagicMock()
    mock_client.api = MagicMock()
    mock_client.get_host_id.return_value = '10084'
    mock_client.get_host_interface_id.return_value = '1'
    mock_client.ensure_discovery_rule.return_value = '777'
    if is_trigger:
        mock_client.get_trigger_prototypes.return_value = []
        mock_client.create_trigger_prototype.return_value = '999'
    else:
        mock_client.get_item_prototypes.return_value = []
        mock_client.create_item_prototype.return_value = '888'

    with patch.object(app_module, 'get_db_connection',
                      side_effect=[conn, uconn]), \
         patch.object(app_module, 'ZABBIX_ENVIRONMENTS', _TEST_ENV), \
         patch('zabbix_mac.ZabbixClient', return_value=mock_client):
        resp = app_module.app.test_client().post(
            '/api/sync/execute',
            json={'action_type': action_type, 'ids': [1], 'environment': 'test'})
    return resp, mock_client


class TestApiSyncExecuteFilterBinding:
    """回归：原型同步时 ensure_discovery_rule 必须收到带 _conditions 的配置。"""

    def test_item_prototype_sync_binds_conditions(self, app_module):
        host_rows = [{'id': 1, 'host_ip': '192.168.1.10', 'discovery_rule_id': 7,
                      'name': 'Used space', 'key': 'vfs.fs.size[{#FSNAME},used]',
                      'type': 0, 'value_type': 3, 'delay': '1m', 'status': 0,
                      'change_type': 'new'}]
        dr_rows = [{'id': 7, 'name': 'FS', 'key': 'vfs.fs.discovery',
                    'delay': '1h', 'evaltype': 1, 'status': 0}]
        cond_rows = [{'discovery_rule_id': 7, 'macro': '{#FSTYPE}',
                      'value': 'ext4', 'operator': 'EQUALS'}]

        resp, client = _run_sync_execute(
            app_module, 'itemprototype', host_rows, dr_rows, cond_rows)

        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert data['created'] == 1

        args = client.ensure_discovery_rule.call_args.args
        assert args[0] == '10084'           # host_id
        assert args[1] == 'vfs.fs.discovery'  # dr key
        dr_cfg = args[2]
        # 修复点：dr_cfg 必须携带 _conditions，否则 filter 为空无法绑定
        assert dr_cfg['_conditions'] == cond_rows

    def test_trigger_prototype_sync_binds_conditions(self, app_module):
        host_rows = [{'id': 1, 'host_ip': '192.168.1.10', 'discovery_rule_id': 7,
                      'description': 'Disk low',
                      'expression': 'last(/21001/vfs.fs.size[{#FSNAME},pfree])<10',
                      'priority': 2, 'status': 0, 'change_type': 'new'}]
        dr_rows = [{'id': 7, 'name': 'FS', 'key': 'vfs.fs.discovery',
                    'delay': '1h', 'evaltype': 1, 'status': 0}]
        cond_rows = [{'discovery_rule_id': 7, 'macro': '{#FSTYPE}',
                      'value': 'ext4', 'operator': 'EQUALS'}]

        resp, client = _run_sync_execute(
            app_module, 'triggerprototype', host_rows, dr_rows, cond_rows,
            is_trigger=True)

        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert data['created'] == 1

        args = client.ensure_discovery_rule.call_args.args
        assert args[1] == 'vfs.fs.discovery'
        assert args[2]['_conditions'] == cond_rows

    def test_no_dr_id_skips_filter_loader(self, app_module):
        """无 discovery_rule_id 的行不进 loader，同步正常降级（不抛错）。"""
        host_rows = [{'id': 2, 'host_ip': '192.168.1.11',
                      'name': 'Solo', 'key': 'solo.key',
                      'type': 0, 'value_type': 3, 'delay': '1m', 'status': 0,
                      'change_type': 'new'}]

        conn = _RouteConn([
            _RouteCursor([host_rows]),  # SELECT * FROM <table>
        ])
        uconn = MagicMock()
        mock_client = MagicMock()
        mock_client.api = MagicMock()
        mock_client.get_host_id.return_value = '10084'
        mock_client.get_host_interface_id.return_value = '1'
        mock_client.get_item_prototypes.return_value = []

        with patch.object(app_module, 'get_db_connection',
                          side_effect=[conn, uconn]), \
             patch.object(app_module, 'ZABBIX_ENVIRONMENTS', _TEST_ENV), \
             patch('zabbix_mac.ZabbixClient', return_value=mock_client):
            resp = app_module.app.test_client().post(
                '/api/sync/execute',
                json={'action_type': 'itemprototype', 'ids': [2],
                      'environment': 'test'})

        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert any('未找到 discovery_rule_id' in e for e in data['errors'])
        # 无 dr_id 时不触发 ensure_discovery_rule
        mock_client.ensure_discovery_rule.assert_not_called()
