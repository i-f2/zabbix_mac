# -*- coding: utf-8 -*-
"""
API 端点与杂项页面回归测试

覆盖: /api/review/item-triggers（参数校验/复核表查询）、/api/review/verify
（统一核验端点：参数/环境/空记录分支 + verified/not_found/异常计数语义）、
/api/search（q 校验、5 实体聚合、hosts detail=template_id —— 缺陷②回归钉）、
/search 与 /base-template/import 与 /discovery-rules 与 /filter-conditions
页面 GET、/webscenarios/seed 双分支、/items-review/sync 无效环境 400。
"""
import os
import sys
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MOCK_CONFIG = {
    'app': {'secret_key': 'test-secret-key-for-testing', 'host': '127.0.0.1',
            'port': 5050, 'debug': False, 'default_template_name': '21001'},
    'database': {'host': 'localhost', 'port': 5432, 'name': 'ops',
                 'user': 'postgres', 'password': '', 'client_encoding': 'utf8',
                 'schema': 'zabbix_mac'},
    'zabbix_environments': [
        {'key': 'testenv', 'name': '测试环境', 'url': 'http://localhost/api_jsonrpc.php',
         'username': 'Admin', 'password': 'zabbix'},
        {'key': 'nourl', 'name': '空URL环境', 'url': '',
         'username': 'Admin', 'password': ''},
    ],
    'sync': {'default_workers': 5, 'max_retry_attempts': 3, 'retry_delay': 2},
    'zabbix_room_mapping': {},
}


class _CountRow(dict):
    """双形态行：兼容 fetchone()[0] 与 fetchone()['count']。"""

    def __getitem__(self, k):
        if isinstance(k, int):
            return 0
        return dict.get(self, k, 0)


class FakeCursor:
    """按 SQL 中表名标记返回预置行（dict 行模拟 DictCursor）。"""

    def __init__(self, rows_by_table=None, fail_on=None):
        self.executes = []
        self._rows_by_table = rows_by_table or {}
        self._fail_on = fail_on
        self._sql = ''

    def execute(self, sql, params=None):
        self.executes.append((sql, params))
        self._sql = ' '.join(sql.split())
        if self._fail_on and self._fail_on in self._sql:
            raise RuntimeError('db down')

    def fetchall(self):
        for marker, rows in self._rows_by_table.items():
            if marker in self._sql:
                return rows
        return []

    def fetchone(self):
        return _CountRow({'count': 0})

    def calls(self, marker):
        return [c for c in self.executes if marker in c[0]]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class FakeConn:
    def __init__(self, cursor):
        self._cursor = cursor
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def cursor(self, cursor_factory=None):
        return self._cursor

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


@pytest.fixture(scope='module')
def app_module():
    with patch('config_loader.load_config', return_value=MOCK_CONFIG):
        if 'app' in sys.modules:
            del sys.modules['app']
        import app
        app.app.config['TESTING'] = True
        app.app.config['WTF_CSRF_ENABLED'] = False
        app.app.before_request_funcs[None] = []
        yield app


@pytest.fixture
def client(app_module):
    return app_module.app.test_client()


# ---- /api/review/item-triggers ----

class TestApiItemTriggers:
    def test_missing_params_400(self, client):
        resp = client.get('/api/review/item-triggers')
        assert resp.status_code == 400
        assert '缺少' in resp.get_json()['message']
        resp = client.get('/api/review/item-triggers?host_ip=1.1.1.1')
        assert resp.status_code == 400

    def test_success_dict_rows(self, app_module, client):
        rows = [{'id': 1, 'name': 't1', 'expression': 'e'}]
        conn = FakeConn(FakeCursor(rows_by_table={'FROM triggers_review': rows}))
        with patch.object(app_module, 'get_db_connection', return_value=conn):
            resp = client.get('/api/review/item-triggers?host_ip=1.1.1.1&template_name=21001')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True and data['triggers'] == rows
        q = conn._cursor.calls('SELECT * FROM triggers_review')[0]
        assert q[1] == ('1.1.1.1', '21001')
        assert conn.closed


# ---- /api/review/verify ----

def _verify_json(**kw):
    base = {'action_type': 'item', 'ids': [1], 'environment': '测试环境'}
    base.update(kw)
    return base


@pytest.fixture
def mock_zabbix():
    """mock 路由内 local import 的 ZabbixClient（按 type 返回不同结果）。"""
    with patch('zabbix_mac.ZabbixClient') as cls:
        inst = cls.return_value
        inst.api = MagicMock()
        yield cls, inst


class TestApiReviewVerify:
    def test_param_validation_400(self, client):
        resp = client.post('/api/review/verify', json={})
        assert resp.status_code == 400
        resp = client.post('/api/review/verify',
                           json=_verify_json(ids=[]))
        assert resp.status_code == 400
        resp = client.post('/api/review/verify',
                           json=_verify_json(environment='不存在'))
        assert resp.status_code == 400
        assert '参数无效' in resp.get_json()['message']

    def test_bad_action_type_400(self, client):
        resp = client.post('/api/review/verify',
                           json=_verify_json(action_type='bogus'))
        assert resp.status_code == 400
        assert '无效的 action_type' in resp.get_json()['message']

    def test_env_without_url_500(self, client):
        resp = client.post('/api/review/verify',
                           json=_verify_json(environment='空URL环境'))
        assert resp.status_code == 500
        assert '未配置 URL' in resp.get_json()['message']

    def test_empty_table_404(self, app_module, client, mock_zabbix):
        conn = FakeConn(FakeCursor())
        with patch.object(app_module, 'get_db_connection', return_value=conn):
            resp = client.post('/api/review/verify', json=_verify_json())
        assert resp.status_code == 404
        assert '未找到匹配的记录' in resp.get_json()['message']
        assert conn.closed

    def test_verified_flow(self, app_module, client, mock_zabbix):
        cls, zb = mock_zabbix
        zb.get_host_id.return_value = '100'
        zb.api.item.get.return_value = [{'itemid': '1'}]
        rows = [{'id': 1, 'host_ip': 'h1', 'item_key': 'k1'}]
        conn = FakeConn(FakeCursor(rows_by_table={'FROM items_review': rows}))
        with patch.object(app_module, 'get_db_connection', return_value=conn):
            resp = client.post('/api/review/verify', json=_verify_json())
        data = resp.get_json()
        assert resp.status_code == 200
        assert data['success'] is True and data['status'] == 'success'
        assert data['verified'] == 1 and data['not_found'] == 0
        upd = conn._cursor.calls('UPDATE items_review SET status_verification')
        assert len(upd) == 1 and upd[0][1] == ('verified', 1)
        assert conn.committed

    def test_not_found_and_no_host_flows(self, app_module, client, mock_zabbix):
        cls, zb = mock_zabbix
        zb.get_host_id.return_value = '100'
        zb.api.item.get.return_value = []          # 远端查无
        rows = [
            {'id': 1, 'host_ip': 'h1', 'item_key': 'k1'},
            {'id': 2, 'host_ip': 'h2', 'item_key': ''},   # 键为空 → 直接 not_found
        ]
        conn = FakeConn(FakeCursor(rows_by_table={'FROM items_review': rows}))
        with patch.object(app_module, 'get_db_connection', return_value=conn):
            resp = client.post('/api/review/verify',
                               json=_verify_json(ids=[1, 2]))
        data = resp.get_json()
        assert data['status'] == 'warning'
        assert data['verified'] == 0 and data['not_found'] == 2
        assert data['failed_ids'] == [1, 2]
        assert '未找到' in data['message']

    def test_missing_host_not_queried(self, app_module, client, mock_zabbix):
        cls, zb = mock_zabbix
        zb.get_host_id.return_value = None         # 主机名解析失败
        rows = [{'id': 1, 'host_ip': 'h1', 'item_key': 'k1'}]
        conn = FakeConn(FakeCursor(rows_by_table={'FROM items_review': rows}))
        with patch.object(app_module, 'get_db_connection', return_value=conn):
            resp = client.post('/api/review/verify', json=_verify_json())
        data = resp.get_json()
        assert data['not_found'] == 1
        zb.api.item.get.assert_not_called()

    def test_zabbix_api_exception_collected(self, app_module, client, mock_zabbix):
        from zabbix_mac import ZabbixAPIException
        cls, zb = mock_zabbix
        zb.get_host_id.return_value = '100'
        zb.api.item.get.side_effect = ZabbixAPIException('boom')
        rows = [{'id': 1, 'host_ip': 'h1', 'item_key': 'k1'}]
        conn = FakeConn(FakeCursor(rows_by_table={'FROM items_review': rows}))
        with patch.object(app_module, 'get_db_connection', return_value=conn):
            resp = client.post('/api/review/verify', json=_verify_json())
        data = resp.get_json()
        assert data['success'] is True
        assert data['verified'] == 0 and data['not_found'] == 0
        assert data['errors'] and 'boom' in data['errors'][0]

    def test_httptest_search_uses_name_field(self, app_module, client, mock_zabbix):
        cls, zb = mock_zabbix
        zb.get_host_id.return_value = '100'
        zb.api.httptest.get.return_value = [{'httptestid': '1'}]
        rows = [{'id': 1, 'host': 'H', 'name': 'ws1'}]
        conn = FakeConn(FakeCursor(rows_by_table={'FROM webscenario_items_review': rows}))
        with patch.object(app_module, 'get_db_connection', return_value=conn):
            resp = client.post('/api/review/verify',
                               json=_verify_json(action_type='webscenario'))
        assert resp.get_json()['verified'] == 1
        kw = zb.api.httptest.get.call_args.kwargs
        assert kw['search'] == {'name': 'ws1'}


# ---- /api/search（含缺陷② 回归钉）----

class TestApiSearch:
    def test_short_query_empty_results(self, client):
        assert client.get('/api/search').get_json()['results'] == []
        assert client.get('/api/search?q=a').get_json()['results'] == []

    def test_five_entity_aggregation(self, app_module, client):
        rows_by_table = {
            'FROM items': [{'id': 1, 'name': 'i', 'item_key': 'k', 'template_name': 'T'}],
            'FROM triggers': [{'id': 2, 'name': 't', 'expression': '{h:k.last()}',
                               'template_name': 'T'}],
            'FROM hosts': [{'id': 3, 'name': 'h', 'template_id': '21001'}],
            'FROM templates': [{'id': 4, 'name': 'tpl'}],
            'FROM discovery_rules': [{'id': 5, 'name': 'dr', 'key': 'dsk',
                                      'template_name': 'T'}],
        }
        conn = FakeConn(FakeCursor(rows_by_table=rows_by_table))
        with patch.object(app_module, 'get_db_connection', return_value=conn):
            resp = client.get('/api/search?q=cpu')
        data = resp.get_json()
        assert data['query'] == 'cpu'
        kinds = [r['type'] for r in data['results']]
        assert kinds == ['item', 'trigger', 'host', 'template', 'discovery_rule']
        labels = {r['type']: r['type_label'] for r in data['results']}
        assert labels['item'] == '监控项' and labels['discovery_rule'] == '自动发现规则'
        assert any('/item/edit/1' in r['url'] for r in data['results'])

    def test_hosts_detail_is_template_id(self, app_module, client):
        """缺陷② 回归钉：hosts 分支 SELECT 仅取 template_id（024 迁移后规范列），
        detail 必须读 template_id —— 此前误读 template_name 恒为空串。"""
        conn = FakeConn(FakeCursor(rows_by_table={
            'FROM hosts': [{'id': 3, 'name': 'h1', 'template_id': '21001,91001'}]}))
        with patch.object(app_module, 'get_db_connection', return_value=conn):
            data = client.get('/api/search?q=h1').get_json()
        host_result = [r for r in data['results'] if r['type'] == 'host'][0]
        assert host_result['detail'] == '21001,91001'


# ---- 杂项页面 GET ----

class TestMiscPages:
    def test_search_page_no_db(self, client):
        resp = client.get('/search?q=cpu')
        assert resp.status_code == 200

    def test_base_template_import_page_no_db(self, client):
        resp = client.get('/base-template/import')
        assert resp.status_code == 200
        assert 'xml' in resp.data.decode('utf-8').lower()

    @pytest.mark.parametrize('url', ['/discovery-rules', '/filter-conditions'])
    def test_list_pages(self, app_module, client, url):
        mock_conn = MagicMock()
        cur = MagicMock()
        cur.fetchall.return_value = []
        cur.fetchone.return_value = _CountRow({'count': 0})
        cur.description = (('id', None, None, None, None, None, None),)
        cur.rowcount = 0
        mock_conn.cursor.return_value.__enter__.return_value = cur
        with patch.object(app_module, 'get_db_connection', return_value=mock_conn):
            resp = client.get(url)
        assert resp.status_code == 200


# ---- /webscenarios/seed ----

class TestWebscenarioSeed:
    def test_success(self, app_module, client):
        conn = FakeConn(FakeCursor())
        with patch.object(app_module, 'get_db_connection', return_value=conn):
            resp = client.post('/webscenarios/seed')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True and '已插入 2 条' in data['message']
        assert len(conn._cursor.calls('INSERT INTO webscenario_items')) == 1
        assert conn.committed and conn.closed

    def test_db_error_500_rollback(self, app_module, client):
        conn = FakeConn(FakeCursor(fail_on='INSERT INTO webscenario_items'))
        with patch.object(app_module, 'get_db_connection', return_value=conn):
            resp = client.post('/webscenarios/seed')
        assert resp.status_code == 500
        assert conn.rolled_back and not conn.committed and conn.closed


# ---- /items-review/sync 参数校验分支 ----

class TestItemsReviewSyncValidation:
    def test_invalid_environment_400_no_conn(self, app_module, client):
        mock_get = MagicMock()
        with patch.object(app_module, 'get_db_connection', mock_get):
            resp = client.post('/items-review/sync',
                               json={'environment': '不存在的环境', 'ids': [1]})
        assert resp.status_code == 400
        assert '无效的环境' in resp.get_json()['message']
        mock_get.assert_not_called()

    def test_env_url_missing_500_no_conn(self, app_module, client):
        mock_get = MagicMock()
        with patch.object(app_module, 'get_db_connection', mock_get):
            resp = client.post('/items-review/sync',
                               json={'environment': '空URL环境', 'ids': [1]})
        assert resp.status_code == 500
        assert '未配置 Zabbix URL' in resp.get_json()['message']
        mock_get.assert_not_called()
