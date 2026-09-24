# -*- coding: utf-8 -*-
"""
复核页面「直接添加」路由回归测试（5 个 add 路由）

覆盖契约:
- /item-review/add: 主表 INSERT RETURNING id → 复核表 INSERT 双写，FK 传递，
  system/subsystem 空串→None，modified/confirmed=False + status_verification
  ='pending' 初始化，preprocessing JSON 容错三分支
- /trigger-review/add: 仅写复核表 + 主表 FK 引用（查无引用 400）
- /webscenario-review/add / /web-trigger-review/add: 单表插入 + pending 初始化
- /webscenario/add: GET 表单渲染 / POST 302 / DB 异常回落 200+flash
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
    'zabbix_environments': [],
    'sync': {'default_workers': 5, 'max_retry_attempts': 3, 'retry_delay': 2},
    'zabbix_room_mapping': {},
}


class FakeCursor:
    """RETURNING id → (42,)；SELECT id → 可配引用行；其余 execute 记录。"""

    def __init__(self, ref_row=(42,), fail_on=None):
        self.executes = []
        self._ref = ref_row
        self._fail_on = fail_on
        self._sql = ''

    def execute(self, sql, params=None):
        self.executes.append((sql, params))
        self._sql = ' '.join(sql.split())
        if self._fail_on and self._fail_on in self._sql:
            raise RuntimeError('db down')

    def fetchone(self):
        if 'RETURNING id' in self._sql:
            return (42,)
        return self._ref

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


@pytest.fixture
def app_mod():
    with patch('config_loader.load_config', return_value=MOCK_CONFIG):
        if 'app' in sys.modules:
            del sys.modules['app']
        import app
        app.app.config['TESTING'] = True
        app.app.config['WTF_CSRF_ENABLED'] = False
        app.app.before_request_funcs[None] = []
        yield app


@pytest.fixture
def client(app_mod):
    return app_mod.app.test_client()


ITEM_FORM = {'item_key': 'k1', 'name': 'n1', 'type': '0', 'value_type': '0',
             'delay': '30s', 'template_name': '21001', 'host_ip': '10.0.0.1',
             'system': 'SysA', 'subsystem': ''}


class TestAddItemFromReview:
    def test_double_insert_with_fk(self, app_mod, client):
        cur = FakeCursor()
        conn = FakeConn(cur)
        with patch.object(app_mod, 'get_db_connection', return_value=conn):
            resp = client.post('/item-review/add', data=ITEM_FORM)
        assert resp.status_code == 200 and resp.get_json()['success'] is True
        main = cur.calls('INSERT INTO items (')
        review = cur.calls('INSERT INTO items_review (')
        assert len(main) == 1 and len(review) == 1
        # 复核表行以主表 RETURNING id 作 FK
        assert review[0][1][0] == 42
        # 状态初始化: modified=False, confirmed=False, status_verification='pending'
        assert review[0][1][-3:] == (False, False, 'pending')
        # system 透传 / subsystem 空串→None
        assert review[0][1][17] == 'SysA' and review[0][1][18] is None
        assert conn.committed and not conn.rolled_back and conn.closed

    @pytest.mark.parametrize('raw,expect', [
        ('[{"type": "5"}]', [{'type': '5'}]),   # 合法 JSON → 解析对象
        ('not json', None),                     # 非法 → None
        ('   ', None),                          # 空白 → None
        (None, None),                           # 缺省 → None
    ])
    def test_preprocessing_branches(self, app_mod, client, raw, expect):
        cur = FakeCursor()
        conn = FakeConn(cur)
        form = dict(ITEM_FORM)
        if raw is not None:
            form['preprocessing'] = raw
        with patch.object(app_mod, 'get_db_connection', return_value=conn):
            resp = client.post('/item-review/add', data=form)
        assert resp.status_code == 200, resp.get_json()
        review = cur.calls('INSERT INTO items_review (')
        assert review[0][1][16] == expect  # preprocessing 位列 16

    def test_missing_required_field_500_rollback(self, app_mod, client):
        cur = FakeCursor()
        conn = FakeConn(cur)
        form = dict(ITEM_FORM)
        del form['item_key']
        with patch.object(app_mod, 'get_db_connection', return_value=conn):
            resp = client.post('/item-review/add', data=form)
        assert resp.status_code == 500
        assert '添加失败' in resp.get_json()['message']
        assert conn.rolled_back and not conn.committed

    def test_db_error_500(self, app_mod, client):
        conn = FakeConn(FakeCursor(fail_on='INSERT INTO items_review'))
        with patch.object(app_mod, 'get_db_connection', return_value=conn):
            resp = client.post('/item-review/add', data=ITEM_FORM)
        assert resp.status_code == 500
        assert conn.rolled_back and conn.closed


TRIG_FORM = {'name': 't1', 'expression': '{host:k.last()}>1', 'priority': '3',
             'template_name': '21001', 'host_ip': '10.0.0.1'}


class TestAddTriggerFromReview:
    def test_success_refs_main_fk(self, app_mod, client):
        cur = FakeCursor(ref_row=(7,))
        conn = FakeConn(cur)
        with patch.object(app_mod, 'get_db_connection', return_value=conn):
            resp = client.post('/trigger-review/add', data=TRIG_FORM)
        assert resp.status_code == 200 and resp.get_json()['success'] is True
        assert len(cur.calls('SELECT id FROM triggers')) == 1
        ins = cur.calls('INSERT INTO triggers_review (')
        assert len(ins) == 1 and ins[0][1][0] == 7  # trigger_id FK
        assert ins[0][1][-3:] == (False, False, 'pending')
        assert cur.calls('INSERT INTO triggers (') == []  # 主表不写
        assert conn.committed

    def test_no_reference_400(self, app_mod, client):
        cur = FakeCursor(ref_row=None)
        conn = FakeConn(cur)
        with patch.object(app_mod, 'get_db_connection', return_value=conn):
            resp = client.post('/trigger-review/add', data=TRIG_FORM)
        assert resp.status_code == 400
        assert '无已有触发器' in resp.get_json()['message']
        assert cur.calls('INSERT INTO triggers_review') == []


WS_FORM = {'name': '[1.1.1.1] Web scenario [x] failed', 'host': 'Zabbix server',
           'url': 'http://1.1.1.1:80/api', 'status_code': '200',
           'system': 'S', 'subsystem': 'B'}


class TestAddWebscenarioReview:
    def test_success(self, app_mod, client):
        cur = FakeCursor()
        conn = FakeConn(cur)
        with patch.object(app_mod, 'get_db_connection', return_value=conn):
            resp = client.post('/webscenario-review/add', data=WS_FORM)
        assert resp.status_code == 200 and resp.get_json()['success'] is True
        ins = cur.calls('INSERT INTO webscenario_items_review')
        assert len(ins) == 1
        assert ins[0][1] == ('[1.1.1.1] Web scenario [x] failed', 'Zabbix server',
                             'http://1.1.1.1:80/api', '200', 'S', 'B')
        assert conn.committed

    def test_db_error_500_rollback(self, app_mod, client):
        conn = FakeConn(FakeCursor(fail_on='INSERT INTO webscenario_items_review'))
        with patch.object(app_mod, 'get_db_connection', return_value=conn):
            resp = client.post('/webscenario-review/add', data=WS_FORM)
        assert resp.status_code == 500 and conn.rolled_back

    def test_missing_required_fails_before_conn(self, app_mod, client):
        """name 等必填字段在开连接之前读取 —— 缺失即 BadRequestKeyError 被
        Flask 折算为 400，且 get_db_connection 根本不被调用，无连接泄漏。"""
        mock_get = MagicMock()
        with patch.object(app_mod, 'get_db_connection', mock_get):
            resp = client.post('/webscenario-review/add', data={'host': 'h'})
        assert resp.status_code == 400
        mock_get.assert_not_called()


WT_FORM = {'host': 'Zabbix server', 'web_scenario_name': 'ws1',
           'trigger_name': 't1', 'expression': '{h:web.test.fail[ws1].count(#3,0,ne)}>2'}


class TestAddWebTriggerReview:
    def test_success_defaults(self, app_mod, client):
        cur = FakeCursor()
        conn = FakeConn(cur)
        with patch.object(app_mod, 'get_db_connection', return_value=conn):
            resp = client.post('/web-trigger-review/add', data=WT_FORM)
        assert resp.status_code == 200 and resp.get_json()['success'] is True
        ins = cur.calls('INSERT INTO web_trigger_review')
        assert len(ins) == 1
        params = ins[0][1]
        assert params[0:4] == (WT_FORM['host'], 'ws1', 't1', WT_FORM['expression'])
        assert params[4] == 3 and params[5] == 0  # priority/status 缺省默认
        assert conn.committed

    def test_bad_priority_500_rollback(self, app_mod, client):
        conn = FakeConn(FakeCursor())
        form = dict(WT_FORM, priority='abc')
        with patch.object(app_mod, 'get_db_connection', return_value=conn):
            resp = client.post('/web-trigger-review/add', data=form)
        assert resp.status_code == 500 and conn.rolled_back


class TestAddWebscenarioMain:
    def test_get_renders_form(self, app_mod, client):
        """GET 在路由顶部即开连接但无查询，close 后直接渲染表单。"""
        conn = FakeConn(FakeCursor())
        with patch.object(app_mod, 'get_db_connection', return_value=conn):
            resp = client.get('/webscenario/add')
        assert resp.status_code == 200
        html = resp.data.decode('utf-8')
        assert 'nginx_clb' in html and 'webtest_nginx_api' in html
        assert conn.closed

    def test_post_success_redirects(self, app_mod, client):
        cur = FakeCursor()
        conn = FakeConn(cur)
        form = {'system': 'S', 'subsystem': 'B', 'nginx_clb': '1.1.1.1:80',
                'webtest_api': '/api/x', 'webtest_nginx_api': '/nginx/api/x',
                'in_room': '机房A'}
        with patch.object(app_mod, 'get_db_connection', return_value=conn):
            resp = client.post('/webscenario/add', data=form)
        assert resp.status_code == 302
        assert '/webscenarios' in resp.headers['Location']
        ins = cur.calls('INSERT INTO webscenario_items (')
        assert len(ins) == 1
        # 空端点列 → None 落库
        assert ins[0][1][2] == '1.1.1.1:80' and ins[0][1][3] is None
        assert conn.committed

    def test_post_db_error_falls_back_to_form(self, app_mod, client):
        """POST 写库异常 → rollback + flash + 回落渲染表单（200），非 500。"""
        conn = FakeConn(FakeCursor(fail_on='INSERT INTO webscenario_items'))
        form = {'system': 'S', 'webtest_api': '/a', 'webtest_nginx_api': '/b'}
        with patch.object(app_mod, 'get_db_connection', return_value=conn):
            resp = client.post('/webscenario/add', data=form)
        assert resp.status_code == 200
        assert conn.rolled_back
