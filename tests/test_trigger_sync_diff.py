# -*- coding: utf-8 -*-
"""
触发器复核同步 Diff —— 匹配锚点与指纹对齐

修复两处缺陷（spec 已确认）：
1. 以 description（名称）为匹配 Key：名称是可编辑属性，改名后查不到原触发器
   → 误判 CREATE。改为按表达式解析出的 item key 集合锚定（复用
   _parse_trigger_item_keys，零 schema 变更）。
2. calculate_fingerprint 拿本地 3 字段 dict 直接比 output='extend' 的约 40 字段
   dict，永远不相等 → 存量触发器恒判 UPDATE，UNCHANGED 分支不可达。
   改为两侧都投影成同形三元组再比。

三条同步路径（/api/sync/preview、/api/sync/apply、/api/sync/execute）是同一份
逻辑的三份复制，全部覆盖 —— 前端批量同步确认按钮实际调用的是 execute。
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

def _row(rid, name, expression, priority=4, change_type=None):
    """triggers_review 复核行（只含路由实际取用的字段）"""
    return {'id': rid, 'host_ip': '10.0.0.1', 'name': name, 'expression': expression,
            'priority': priority, 'change_type': change_type}


def _ztrigger(tid, description, expression, priority=4):
    """output='extend' 形态 —— 字段数远多于本地载荷，专门用来复现指纹不对称"""
    return {'triggerid': str(tid), 'description': description, 'expression': expression,
            'priority': str(priority), 'status': '0', 'value': '0', 'state': '0',
            'error': '', 'lastchange': '0', 'comments': '', 'url': '', 'type': '0',
            'recovery_mode': '0', 'correlation_mode': '0', 'manual_close': '0',
            'opdata': '', 'flags': '0', 'templateid': '', 'hosts': [],
            'dependencies': [], 'tags': [{'tag': 'ManagedBy', 'value': 'PythonScript'}]}


class FakeZabbixApi:
    """pyzabbix 风格端点。item.get 恒返回"全部存在"，放行 execute 的依赖前置校验。"""

    class item:
        @staticmethod
        def get(**kwargs):
            keys = (kwargs.get('filter') or {}).get('key_') or []
            if isinstance(keys, str):
                keys = [keys]
            return [{'itemid': str(i), 'key_': k} for i, k in enumerate(keys)]


class FakeZabbixClient:
    """api 必须为真值（路由以 getattr(client, 'api', None) 判连接成功）。

    calculate_fingerprint 用**真实现** —— 本轮修的就是指纹不对称，
    拿假指纹自证等于没测。
    """

    api = FakeZabbixApi()
    calculate_fingerprint = zabbix_mac.ZabbixClient.calculate_fingerprint

    def __init__(self, *args, **kwargs):
        self.triggers = []
        self.create_calls = []
        self.update_calls = []
        self.delete_calls = []

    def get_host_id(self, host):
        return HOST_ID

    def get_managed_triggers(self, host_id):
        return list(self.triggers)

    def create_trigger(self, data):
        self.create_calls.append(dict(data))
        return '90001'

    def update_trigger(self, trigger_id, data):
        self.update_calls.append((trigger_id, dict(data)))
        return True

    def delete_trigger(self, trigger_id):
        self.delete_calls.append(trigger_id)
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
def post_sync(app, client, monkeypatch):
    """按路径驱动一次同步：注入假 ZabbixClient，复核行从 mock cursor 取出。

    返回 _post(path, rows, zabbix_triggers) -> (resp, fake_client)；
    path 另需 action_type 时通过 payload 扩展。
    """
    fake = FakeZabbixClient()
    monkeypatch.setattr(zabbix_mac, 'ZabbixClient', lambda *a, **kw: fake)
    cur = app.test_mock_cursor

    def _post(path, rows, zabbix_triggers, extra=None):
        cur.fetchall.return_value = rows
        fake.triggers = zabbix_triggers
        payload = {'ids': [r['id'] for r in rows], 'table': 'triggers_review',
                   'environment': ENV}
        if extra:
            payload.update(extra)
        resp = client.post(path, json=payload)
        return resp, fake

    return _post


# ---- 场景 1：名称与表达式同时修改 → UPDATE 而非 CREATE ----

class TestRenameBecomesUpdate:

    def test_renamed_and_retuned_previews_as_update(self, post_sync):
        """spec 场景 1：High CPU Usage / >5 → Extreme High CPU Usage / >8"""
        rows = [_row(1, 'Extreme High CPU Usage', '{10.0.0.1:cpu.load.avg(5)}>8')]
        zt = [_ztrigger(22901, 'High CPU Usage', '{10.0.0.1:cpu.load.avg(5)}>5')]
        resp, _ = post_sync('/api/sync/preview', rows, zt)

        assert resp.status_code == 200
        data = resp.get_json()
        actions = [c['action'] for c in data['changes']]
        assert 'CREATE' not in actions, f'改名被误判为新增：{data["changes"]}'
        assert actions == ['UPDATE']
        assert data['summary']['update_count'] == 1
        assert data['summary']['create_count'] == 0

    def test_threshold_only_change_previews_as_update(self, post_sync):
        """只改阈值（名称不动）也必须是 UPDATE —— 指纹要能察觉 expression 变化"""
        rows = [_row(1, 'High CPU Usage', '{10.0.0.1:cpu.load.avg(5)}>8')]
        zt = [_ztrigger(22901, 'High CPU Usage', '{10.0.0.1:cpu.load.avg(5)}>5')]
        resp, _ = post_sync('/api/sync/preview', rows, zt)

        data = resp.get_json()
        assert [c['action'] for c in data['changes']] == ['UPDATE']

    def test_apply_calls_update_not_create(self, post_sync):
        """spec 场景 2 前半（apply 路径）：下发必须走 trigger.update"""
        rows = [_row(1, 'Extreme High CPU Usage', '{10.0.0.1:cpu.load.avg(5)}>8')]
        zt = [_ztrigger(22901, 'High CPU Usage', '{10.0.0.1:cpu.load.avg(5)}>5')]
        resp, fake = post_sync('/api/sync/apply', rows, zt)

        assert resp.status_code == 200
        assert fake.create_calls == [], '改名被当成新增下发到 Zabbix'
        assert len(fake.update_calls) == 1
        tid, payload = fake.update_calls[0]
        assert tid == '22901'
        assert payload['description'] == 'Extreme High CPU Usage'
        assert payload['expression'] == '{10.0.0.1:cpu.load.avg(5)}>8'

    def test_execute_calls_update_not_create(self, post_sync):
        """execute 路径（前端批量同步确认按钮真正调用的那条）同样走 update"""
        rows = [_row(1, 'Extreme High CPU Usage', '{10.0.0.1:cpu.load.avg(5)}>8')]
        zt = [_ztrigger(22901, 'High CPU Usage', '{10.0.0.1:cpu.load.avg(5)}>5')]
        resp, fake = post_sync('/api/sync/execute', rows, zt,
                               extra={'action_type': 'trigger'})

        assert resp.status_code == 200
        assert fake.create_calls == []
        assert [tid for tid, _ in fake.update_calls] == ['22901']

    def test_repreview_after_update_is_unchanged(self, post_sync):
        """spec 场景 2 后半：同步后复跑预览应为 UNCHANGED（指纹不对称修复）"""
        new_name, new_expr = 'Extreme High CPU Usage', '{10.0.0.1:cpu.load.avg(5)}>8'
        rows = [_row(1, new_name, new_expr)]
        # Zabbix 侧已更新为复核后的值
        zt = [_ztrigger(22901, new_name, new_expr)]
        resp, _ = post_sync('/api/sync/preview', rows, zt)

        data = resp.get_json()
        assert data['changes'] == []
        assert data['summary']['unchanged_count'] == 1


# ---- 指纹不对称回归 ----

class TestFingerprintAlignment:

    def test_identical_trigger_is_unchanged_not_update(self, post_sync):
        """内容逐字一致的存量触发器必须 UNCHANGED —— 改造前恒判 UPDATE"""
        rows = [_row(1, 'High CPU Usage', '{10.0.0.1:cpu.load.avg(5)}>5')]
        zt = [_ztrigger(22901, 'High CPU Usage', '{10.0.0.1:cpu.load.avg(5)}>5')]
        resp, _ = post_sync('/api/sync/preview', rows, zt)

        data = resp.get_json()
        assert data['changes'] == [], \
            'UNCHANGED 分支不可达说明两侧指纹仍未对齐'
        assert data['summary']['unchanged_count'] == 1

    def test_priority_only_change_is_update(self, post_sync):
        """priority 字符串 '4' 与本地 int 4 归一后可比，改级报警级别要被察觉"""
        rows = [_row(1, 'High CPU Usage', '{10.0.0.1:cpu.load.avg(5)}>5', priority=3)]
        zt = [_ztrigger(22901, 'High CPU Usage', '{10.0.0.1:cpu.load.avg(5)}>5', priority=4)]
        resp, _ = post_sync('/api/sync/preview', rows, zt)

        assert [c['action'] for c in resp.get_json()['changes']] == ['UPDATE']


# ---- CREATE 边界与匹配器契约 ----

class TestMatcherContract:

    def test_genuinely_new_item_key_previews_as_create(self, post_sync):
        """被监控的 item key 在 Zabbix 侧不存在 → 才是真新增"""
        rows = [_row(1, 'Disk Full', '{10.0.0.1:vfs.fs.size[/,pfree].last()}<10')]
        zt = [_ztrigger(22901, 'High CPU Usage', '{10.0.0.1:cpu.load.avg(5)}>5')]
        resp, _ = post_sync('/api/sync/preview', rows, zt)

        data = resp.get_json()
        assert [c['action'] for c in data['changes']] == ['CREATE']

    def test_delete_uses_identity_not_name(self, post_sync):
        """改名 + 标记下线 → 仍要能找到原触发器删掉（改造前按名称查不到，静默漏删）"""
        rows = [_row(1, 'CPU 已改名', '{10.0.0.1:cpu.load.avg(5)}>5', change_type='delete')]
        zt = [_ztrigger(22901, 'High CPU Usage', '{10.0.0.1:cpu.load.avg(5)}>5')]
        resp, fake = post_sync('/api/sync/execute', rows, zt,
                               extra={'action_type': 'trigger'})

        assert resp.status_code == 200
        assert fake.delete_calls == ['22901']
        assert fake.create_calls == [] and fake.update_calls == []

    def test_duplicate_item_keys_matched_once_each(self):
        """同一主机上监控同一 item key 的两条触发器，各被消费一次，不重复匹配"""
        zt = [_ztrigger(1, '阈值5', '{h:cpu.load.avg(5)}>5'),
              _ztrigger(2, '阈值9', '{h:cpu.load.avg(5)}>9')]
        rows = [_row(1, '阈值7a', '{h:cpu.load.avg(5)}>7'),
                _row(2, '阈值7b', '{h:cpu.load.avg(5)}>7')]
        pairs = __import__('app')._match_trigger_rows(rows, zt)

        matched = sorted(p[1]['triggerid'] for p in pairs if p[1])
        assert matched == ['1', '2'], matched

    def test_row_without_parseable_key_falls_back_to_name(self, post_sync):
        """表达式解析不出 item key（如 {TRIGGER.VALUE}=1）→ 回落名称匹配"""
        rows = [_row(1, '服务停了', '{TRIGGER.VALUE}=1')]
        zt = [_ztrigger(30001, '服务停了', '{TRIGGER.VALUE}=1')]
        resp, _ = post_sync('/api/sync/preview', rows, zt)

        data = resp.get_json()
        assert data['summary']['unchanged_count'] == 1

    def test_fallback_miss_is_create_with_observable_hint(self, post_sync):
        """回落也匹配不上 → CREATE，且 details 说明按名称匹配（边界可观测）"""
        rows = [_row(1, '换了名字的定时器', '{TRIGGER.VALUE}=1')]
        zt = [_ztrigger(30001, '原本的名字', '{TRIGGER.VALUE}=1')]
        resp, _ = post_sync('/api/sync/preview', rows, zt)

        data = resp.get_json()
        assert [c['action'] for c in data['changes']] == ['CREATE']
        assert '已按名称匹配' in data['changes'][0]['details']

    def test_no_zabbix_triggers_on_host(self, post_sync):
        """主机上没有任何托管触发器 → 全部 CREATE，不异常"""
        rows = [_row(1, 'High CPU Usage', '{10.0.0.1:cpu.load.avg(5)}>5')]
        resp, fake = post_sync('/api/sync/preview', rows, [])

        data = resp.get_json()
        assert [c['action'] for c in data['changes']] == ['CREATE']
