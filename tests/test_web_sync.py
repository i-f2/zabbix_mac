# -*- coding: utf-8 -*-
"""
Web 场景 / Web 触发器复核同步 —— 修复轮回归测试

覆盖 spec 修复的三类真机实证缺陷：
1. 托管识别：5.0 httptest 对象无 tags，按标签过滤恒得空集 → 每次同步
   重复 CREATE、下线永不命中。现按 (hostid, 场景名) 身份锚配对。
2. 载荷形态：url/status_codes/timeout 是 step 属性，平铺在场景级会被
   5.0 整单拒收。现统一 steps 形载荷。
3. 指纹不对称：本地 5 字段 vs extend 20+ 字段 + steps 永不相等。
   现两侧投影 _scenario_project 同形（name + steps[url,status_codes]）。
"""
import os
import sys
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import zabbix_mac

ENV = '测试环境'
HOST_ID = '10086'


# ---- 数据构造 ----

def _row(rid, name, url, status_code='200', change_type=None):
    """webscenario_items_review 复核行（只含路由实际取用的字段）"""
    return {'id': rid, 'host': '10.0.0.1', 'name': name, 'url': url,
            'status_code': status_code, 'change_type': change_type}


def _zscenario(sid, name, url, status_codes='200'):
    """output='extend' + selectSteps 形态 —— 字段数远多于本地载荷"""
    return {'httptestid': str(sid), 'name': name, 'hostid': HOST_ID,
            'delay': '1m', 'retries': '1', 'agent': '0', 'status': '0',
            'templateid': '0', 'variables': [], 'headers': [],
            'nextcheck': '0',
            'steps': [{'no': '1', 'name': url, 'url': url,
                       'status_codes': status_codes, 'timeout': '30',
                       'follow_redirects': '1'}]}


class FakeZabbixClient:
    """api 必须为真值（路由以 getattr(client, 'api', None) 判连接成功）。

    calculate_fingerprint 用**真实现** —— 本轮修的就是指纹不对称，
    拿假指纹自证等于没测。
    """

    api = True
    calculate_fingerprint = zabbix_mac.ZabbixClient.calculate_fingerprint

    def __init__(self, *args, **kwargs):
        self.scenarios = []
        self.create_calls = []
        self.update_calls = []
        self.delete_calls = []

    def get_host_id(self, host):
        return HOST_ID

    def get_managed_web_scenarios(self, host_id):
        return list(self.scenarios)

    def create_web_scenario(self, data):
        self.create_calls.append(dict(data))
        return '60001'

    def update_web_scenario(self, scenario_id, data):
        self.update_calls.append((scenario_id, dict(data)))
        return True

    def delete_web_scenario(self, scenario_id):
        self.delete_calls.append(scenario_id)
        return True


# ---- Fixtures ----

@pytest.fixture(scope='module')
def mock_config():
    """全局 mock 配置（与 test_host_sync 同构；环境按 get_zabbix_environments 以 name 为键）"""
    return {
        'app': {'secret_key': 'test-secret-key-for-testing', 'host': '127.0.0.1',
                'port': 5050, 'debug': False, 'default_template_name': '21001'},
        'database': {'host': 'localhost', 'port': 5432, 'name': 'ops',
                     'user': 'postgres', 'password': '', 'client_encoding': 'utf8',
                     'schema': 'zabbix_mac'},
        'zabbix_environments': [
            {'key': 'test_env', 'name': ENV, 'url': 'http://localhost/api_jsonrpc.php',
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

    with patch('config_loader.load_config', return_value=mock_config):
        if 'app' in sys.modules:
            del sys.modules['app']
        from app import app
        app.config['TESTING'] = True
        app.before_request_funcs[None] = []

    with patch('app.get_db_connection', return_value=mock_conn):
        app.test_mock_conn = mock_conn
        app.test_mock_cursor = mock_cursor
        yield app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def fake_zabbix(monkeypatch):
    fake = FakeZabbixClient()
    monkeypatch.setattr(zabbix_mac, 'ZabbixClient', lambda *a, **kw: fake)
    return fake


# ---- 场景域：预览 ----

class TestScenarioPreview:

    def test_identical_scenario_is_unchanged_not_update(self, app, client, fake_zabbix):
        """内容逐字一致的存量场景必须 UNCHANGED —— 指纹投影对齐后可达
        （修复前：extend 形态 vs 本地载荷永不相等；更早前连 url 都比错对象）"""
        fake_zabbix.scenarios = [_zscenario(1, '[Unknown] Web scenario [Sys_Sub_clb] failed',
                                           '192.168.1.1:8080')]
        app.test_mock_cursor.fetchall.return_value = [
            _row(1, '[Unknown] Web scenario [Sys_Sub_clb] failed', '192.168.1.1:8080')]

        resp = client.post('/api/sync/preview', json={
            'ids': [1], 'table': 'webscenario_items_review', 'environment': ENV})

        data = resp.get_json()
        assert data['changes'] == [], data['changes']
        assert data['summary']['unchanged_count'] == 1

    def test_url_change_previews_as_update(self, app, client, fake_zabbix):
        """URL 变更 → UPDATE（修旧实现 comparing 幽灵字段 url 恒空串）"""
        fake_zabbix.scenarios = [_zscenario(1, '场景A', '192.168.1.1:8080')]
        app.test_mock_cursor.fetchall.return_value = [
            _row(1, '场景A', '192.168.1.9:8080')]

        resp = client.post('/api/sync/preview', json={
            'ids': [1], 'table': 'webscenario_items_review', 'environment': ENV})

        data = resp.get_json()
        assert [c['action'] for c in data['changes']] == ['UPDATE']

    def test_status_code_change_previews_as_update(self, app, client, fake_zabbix):
        """状态码阈值变更 → UPDATE（steps 投影可比）"""
        fake_zabbix.scenarios = [_zscenario(1, '场景A', '192.168.1.1:8080',
                                            status_codes='200')]
        app.test_mock_cursor.fetchall.return_value = [
            _row(1, '场景A', '192.168.1.1:8080', status_code='200,201')]

        resp = client.post('/api/sync/preview', json={
            'ids': [1], 'table': 'webscenario_items_review', 'environment': ENV})

        data = resp.get_json()
        assert [c['action'] for c in data['changes']] == ['UPDATE']

    def test_missing_scenario_previews_as_create(self, app, client, fake_zabbix):
        fake_zabbix.scenarios = []
        app.test_mock_cursor.fetchall.return_value = [_row(1, '场景B', '192.168.2.1:8080')]

        resp = client.post('/api/sync/preview', json={
            'ids': [1], 'table': 'webscenario_items_review', 'environment': ENV})

        data = resp.get_json()
        assert [c['action'] for c in data['changes']] == ['CREATE']


# ---- 场景域：下发 ----

class TestScenarioExecute:

    def test_create_uses_steps_form_payload(self, app, client, fake_zabbix):
        """创建载荷必须是 steps 形 —— url/status_codes 平铺在场景级会被
        Zabbix 5.0 以 unexpected parameter 整单拒收（真机实证）"""
        app.test_mock_cursor.fetchall.return_value = [_row(1, '场景C', '192.168.3.1:8080')]
        resp = client.post('/api/sync/execute', json={
            'ids': [1], 'action_type': 'webscenario', 'environment': ENV})

        assert resp.status_code == 200
        data = resp.get_json()
        assert data['created'] == 1
        payload = fake_zabbix.create_calls[0]
        assert 'url' not in payload and 'status_codes' not in payload \
               and 'timeout' not in payload
        assert len(payload['steps']) == 1
        step = payload['steps'][0]
        assert step['url'] == '192.168.3.1:8080'
        assert step['status_codes'] == '200'
        assert 'timeout' in step and 'no' in step
        assert 'tags' not in payload

    def test_rerun_after_create_is_idempotent(self, app, client, fake_zabbix):
        """重跑收敛：第二轮 Zabbix 侧已有同名场景（等集）→ created=0 / updated=0。
        修复前 get_managed 恒空 → 每次同步都重复 CREATE 一份"""
        row = _row(1, '场景D', '192.168.4.1:8080')
        app.test_mock_cursor.fetchall.return_value = [row]

        # 第一轮：创建
        resp1 = client.post('/api/sync/execute', json={
            'ids': [1], 'action_type': 'webscenario', 'environment': ENV})
        assert resp1.get_json()['created'] == 1

        # 第二轮：Zabbix 侧出现了与载荷投影等价的场景
        fake_zabbix.scenarios = [_zscenario(9, '场景D', '192.168.4.1:8080')]
        resp2 = client.post('/api/sync/execute', json={
            'ids': [1], 'action_type': 'webscenario', 'environment': ENV})
        data = resp2.get_json()
        assert data['created'] == 0, '重跑不得重复创建'
        assert data['updated'] == 0, '等集时不得触发 UPDATE'
        assert len(fake_zabbix.create_calls) == 1, '第二轮不得再发 httptest.create'

    def test_update_flow_calls_update_not_create(self, app, client, fake_zabbix):
        """已存在但内容有差异 → httptest.update（载荷无 tags）"""
        fake_zabbix.scenarios = [_zscenario(5, '场景E', '192.168.5.1:8080')]
        app.test_mock_cursor.fetchall.return_value = [
            _row(1, '场景E', '192.168.5.9:8080')]

        resp = client.post('/api/sync/execute', json={
            'ids': [1], 'action_type': 'webscenario', 'environment': ENV})

        data = resp.get_json()
        assert data['updated'] == 1 and data['created'] == 0
        sid, payload = fake_zabbix.update_calls[0]
        assert sid == '5'
        assert 'tags' not in payload, '5.0 httptest.update 拒收 tags'
        assert 'hostid' in payload  # client 层发送前剥离，此处验证任务体仍带

    def test_delete_uses_matched_httptestid(self, app, client, fake_zabbix):
        """下线按身份锚命中 → httptest.delete（修复前 get_managed 恒空，
        删除分支永不触发）"""
        fake_zabbix.scenarios = [_zscenario(7, '场景F', '192.168.6.1:8080')]
        app.test_mock_cursor.fetchall.return_value = [
            _row(1, '场景F', '192.168.6.1:8080', change_type='delete')]

        resp = client.post('/api/sync/execute', json={
            'ids': [1], 'action_type': 'webscenario', 'environment': ENV})

        data = resp.get_json()
        assert data['deleted'] == 1
        assert fake_zabbix.delete_calls == ['7']
        assert fake_zabbix.create_calls == [] and fake_zabbix.update_calls == []

    def test_apply_no_longer_refuses(self, app, client, fake_zabbix):
        """apply 路径此前直接拒绝（'请使用全局监控同步'），预览弹窗的
        确认动作无处落地 —— 现与 execute 共用任务体，可正常下发"""
        fake_zabbix.scenarios = []
        app.test_mock_cursor.fetchall.return_value = [_row(1, '场景G', '192.168.7.1:8080')]

        resp = client.post('/api/sync/apply', json={
            'ids': [1], 'table': 'webscenario_items_review', 'environment': ENV})

        data = resp.get_json()
        assert resp.status_code == 200 and data['success'] is True
        assert data['created'] == 1
        assert not any('请使用全局' in e for e in data.get('errors', []))
