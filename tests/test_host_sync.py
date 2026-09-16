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


def _expected_message(processed, created, updated, deleted, skipped):
    """改造前响应体的 message 逐字格式（统计口径未变，只是不再走 HTTP 返回）。"""
    return (f'资产同步完成：处理 {processed} 台资产，新增 {created}，'
            f'更新 {updated}，清理 {deleted}，跳过 {skipped}')


def _sql_calls(mock_cursor, kind):
    """按 SQL 前缀统计 cur.execute 调用（DELETE 与两条 SELECT 走这里）"""
    kinds = {'INSERT': 'INSERT INTO hosts', 'UPDATE': 'UPDATE hosts',
             'DELETE': 'DELETE FROM hosts', 'SELECT_SUB_ASSETS': 'SELECT system, subsystem',
             'SELECT_HOSTS': 'SELECT id, name, template_id'}
    prefix = kinds[kind]
    return [c for c in mock_cursor.execute.call_args_list
            if c.args and isinstance(c.args[0], str) and c.args[0].lstrip().startswith(prefix)]


def _bulk_calls(ev_calls, kind):
    """挑出 execute_values 调用（批量写走这里，逐行 cur.execute 已消除）。

    两条路径的 SQL **都以 `INSERT INTO hosts` 开头**（更新走 upsert 而非
    `UPDATE ... FROM`），只能靠冲突分支区分：新增是 DO NOTHING，更新是 DO UPDATE。
    """
    tail = 'DO NOTHING' if kind == 'INSERT' else 'DO UPDATE SET'
    return [(sql, rows) for sql, rows in ev_calls
            if sql.lstrip().startswith('INSERT INTO hosts') and tail in sql]


@pytest.fixture
def run_sync(app, client, monkeypatch):
    """驱动一次**真实的**后台任务路径：路由 → 装饰器 → 任务体 → runner。

    用 inline 派发 + mock worker 连接，不启线程、不连数据库。任务体经由
    execute_values 批量写库，故在此替换 execute_values 并记录 (sql, 行列表)。

    比"直接调用任务体"更硬：HTTP 契约（202）、锁的获取与释放、事务边界、
    进度终态都被覆盖到。
    """
    import psycopg2.extras
    import app as app_module

    monkeypatch.setattr(app_module, '_open_worker_connection',
                        lambda *a, **kw: app.test_mock_conn)
    monkeypatch.setattr(app_module, '_background_jobs_inline', True)

    ev_calls = []

    def fake_execute_values(cur, sql, argslist, **kwargs):
        ev_calls.append((sql, list(argslist)))

    monkeypatch.setattr(psycopg2.extras, 'execute_values', fake_execute_values)

    def _run(sub_assets, existing_hosts):
        app.test_mock_cursor.fetchall.side_effect = [sub_assets, existing_hosts]
        resp = client.post('/host/sync')
        return _Result(resp, app.test_mock_cursor, ev_calls, app_module._sync_progress)

    return _run


class _Result:
    """一次同步的可观测产物：HTTP 响应、cursor、批量写调用、进度终态。"""

    def __init__(self, resp, cursor, ev_calls, progress):
        self.resp = resp
        self.cursor = cursor
        self.ev_calls = ev_calls
        self.progress = progress

    @property
    def message(self):
        """任务终态文案，等价于改造前响应体的 message 字段。"""
        return self.progress['message']


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

    def test_split_multi_template_creates_three_hosts(self, run_sync):
        """'21001, 91001, 60001' 应拆成 3 条 hosts 记录（单次批量 INSERT）"""
        r = run_sync([_sub_asset('10.0.0.1', '21001, 91001, 60001')], [])

        assert r.resp.status_code == 202
        assert r.progress['success'] is True
        assert r.message == _expected_message(1, 3, 0, 0, 0)

        inserts = _bulk_calls(r.ev_calls, 'INSERT')
        assert len(inserts) == 1, '3 条新增必须合成 1 次 execute_values'
        sql, rows = inserts[0]
        assert sql.lstrip().startswith('INSERT INTO hosts')
        assert 'ON CONFLICT (name, template_id) DO NOTHING' in sql
        assert len(rows) == 3
        # (name, system, subsystem, template_id, description, in_room)
        assert sorted(row[3] for row in rows) == ['21001', '60001', '91001']
        assert all(row[0] == '10.0.0.1' for row in rows)

    def test_idempotent_no_duplicates(self, run_sync):
        """重复执行不产生重复记录（既有绑定已存在 → 0 新增 0 更新）"""
        sub_assets = [_sub_asset('10.0.0.1', '21001', system='S', subsystem='M', in_room='R')]
        existing = [_host(1, '10.0.0.1', '21001', system='S', subsystem='M',
                          in_room='R', description='测试主机')]
        r = run_sync(sub_assets, existing)

        assert r.message == _expected_message(1, 0, 0, 0, 0)
        assert r.ev_calls == []
        assert _sql_calls(r.cursor, 'DELETE') == []

    def test_update_changed_fields(self, run_sync):
        """同 (name, template_id) 但字段有变更 → 折进 upsert 的 DO UPDATE 分支"""
        sub_assets = [_sub_asset('10.0.0.1', '21001', system='新系统', in_room='新机房')]
        existing = [_host(1, '10.0.0.1', '21001', system='旧系统',
                          in_room='旧机房', description='测试主机')]
        r = run_sync(sub_assets, existing)

        assert r.message == _expected_message(1, 0, 1, 0, 0)
        updates = _bulk_calls(r.ev_calls, 'UPDATE')
        assert len(updates) == 1
        sql, rows = updates[0]
        assert 'ON CONFLICT (name, template_id) DO UPDATE SET' in sql
        # 只改这 4 个可变字段 + updated_at；id / created_at / name / template_id 原地保留
        for col in ('system', 'subsystem', 'description', 'in_room'):
            assert f'{col} = EXCLUDED.{col}' in sql
        assert 'updated_at = CURRENT_TIMESTAMP' in sql
        assert "id = EXCLUDED" not in sql and 'created_at' not in sql
        assert len(rows) == 1
        assert rows[0][1] == '新系统'   # system
        assert rows[0][5] == '新机房'   # in_room

    def test_update_does_not_touch_identity_columns(self, run_sync):
        """更新路径不得改写 id —— 改造前是按 WHERE id=%s 原地更新"""
        sub_assets = [_sub_asset('10.0.0.1', '21001', system='新系统')]
        existing = [_host(1, '10.0.0.1', '21001', system='旧系统', description='测试主机')]
        r = run_sync(sub_assets, existing)

        _, rows = _bulk_calls(r.ev_calls, 'UPDATE')[0]
        # upsert 按 (name, template_id) 命中，未提供 id，故 id 不可能被覆盖
        assert rows[0][0] == '10.0.0.1'
        assert 1 not in rows[0]

    def test_cleanup_stale_binding(self, run_sync):
        """源模板从 '21001,91001' 变为 '21001' → 删除 (ip, 91001) 旧绑定"""
        sub_assets = [_sub_asset('10.0.0.1', '21001')]
        existing = [
            # 与源字段完全一致 → 不产生更新，让断言只聚焦清理
            _host(1, '10.0.0.1', '21001', system='测试系统', subsystem='测试模块',
                  in_room='测试机房', description='测试主机'),
            _host(2, '10.0.0.1', '91001'),
        ]
        r = run_sync(sub_assets, existing)

        assert r.message == _expected_message(1, 0, 0, 1, 0)
        deletes = _sql_calls(r.cursor, 'DELETE')
        assert len(deletes) == 1
        assert deletes[0].args[0] == 'DELETE FROM hosts WHERE id = ANY(%s)'
        assert deletes[0].args[1] == ([2],)

    def test_preserves_manual_hosts(self, run_sync):
        """不在源资产中的手动主机不受影响"""
        sub_assets = [_sub_asset('10.0.0.1', '21001')]
        existing = [_host(1, 'manual-host', '99999')]  # 手动主机，不在 sub_assets
        r = run_sync(sub_assets, existing)

        assert r.message == _expected_message(1, 1, 0, 0, 0)
        assert _sql_calls(r.cursor, 'DELETE') == []

    def test_skip_when_no_valid_template(self, run_sync):
        """无有效 template_id → 跳过并记录日志，不产生记录"""
        sub_assets = [_sub_asset('10.0.0.1', ''), _sub_asset('10.0.0.2', ' , , ')]
        r = run_sync(sub_assets, [])

        assert r.message == _expected_message(2, 0, 0, 0, 2)
        assert r.ev_calls == []

    def test_deletes_are_chunked(self, run_sync):
        """清理超过一个分片时切成多次 DELETE，而非逐行一条"""
        sub_assets = [_sub_asset('10.0.0.1', '21001')]
        existing = [_host(1, '10.0.0.1', '21001', system='测试系统', subsystem='测试模块',
                          in_room='测试机房', description='测试主机')] + \
                   [_host(i, '10.0.0.1', f'9{i:04d}') for i in range(2, 1205)]
        r = run_sync(sub_assets, existing)

        deletes = _sql_calls(r.cursor, 'DELETE')
        assert [len(c.args[1][0]) for c in deletes] == [500, 500, 203]
        assert r.message == _expected_message(1, 0, 0, 1203, 0)

    def test_inserts_are_chunked(self, run_sync):
        """新增超过一个分片时切成多次 execute_values（不是 1200 次往返）"""
        sub_assets = [_sub_asset(f'10.0.{i // 250}.{i % 250}', '21001')
                      for i in range(1200)]
        r = run_sync(sub_assets, [])

        inserts = _bulk_calls(r.ev_calls, 'INSERT')
        assert [len(rows) for _, rows in inserts] == [500, 500, 200]
        assert r.message == _expected_message(1200, 1200, 0, 0, 0)


class TestSyncHostsContract:
    """路由与后台任务的契约"""

    def test_returns_202_immediately(self, run_sync):
        """路由必须立即以 202 受理，而不是同步跑完后返回 200"""
        r = run_sync([], [])
        assert r.resp.status_code == 202
        body = r.resp.get_json()
        assert body['success'] is True
        assert body['async'] is True
        assert body['message']

    def test_route_is_background_wrapped(self, app):
        """路由必须挂上后台装饰器 —— 否则又退回同步执行（本改造要消灭的 504 成因）"""
        import app as app_module
        view = app.view_functions['sync_hosts']
        assert getattr(view, '__background_job_name__', None) == 'host_sync'

    def test_lock_contention_returns_409(self, client, app):
        """改造前该路由无锁，可与初始化并发；现在并发触发必须 409"""
        import app as app_module
        token = app_module._acquire_sync_lock()
        assert token is not None
        try:
            resp = client.post('/host/sync')
            assert resp.status_code == 409
            assert resp.get_json()['success'] is False
        finally:
            app_module._release_sync_lock(token)

    def test_progress_reports_rows(self, run_sync):
        """进度按"台"上报，前端行分支据此渲染 1,200 / 5,000 (24%)"""
        sub_assets = [_sub_asset(f'10.0.0.{i}', '21001') for i in range(1, 6)]
        r = run_sync(sub_assets, [])

        assert r.progress['unit'] == '台'
        assert r.progress['rows_total'] == 5
        assert r.progress['rows_done'] == 5
        assert r.progress['percent'] == 100

    def test_hosts_page_wires_the_poller(self, client, app):
        """hosts.html 必须同时引入进度弹窗与 review_common.js

        少任一个，syncHosts() 会静默走回退分支（无进度、无停止按钮）——
        功能上"没坏"，但本次改造的收益全部丢失，且不会有人注意到。
        """
        cur = app.test_mock_cursor
        cur.fetchall.return_value = []
        cur.fetchone.return_value = {'count': 0}   # 分页组件要求 total 可比较

        html = client.get('/hosts').get_data(as_text=True)
        assert 'syncProgressModal' in html, 'hosts.html 缺少进度弹窗'
        assert 'js/review_common.js' in html, 'hosts.html 未加载 review_common.js'

    def test_failure_is_reported_not_raised(self, run_sync, app):
        """任务体抛异常 → running=False / success=False，且锁被释放"""
        import app as app_module
        app.test_mock_cursor.fetchall.side_effect = RuntimeError('boom')
        resp = app.test_client().post('/host/sync')

        assert resp.status_code == 202
        assert app_module._sync_progress['running'] is False
        assert app_module._sync_progress['success'] is False
        # 锁必须已释放，否则后续所有同步都撞 409
        token = app_module._acquire_sync_lock()
        assert token is not None
        app_module._release_sync_lock(token)
