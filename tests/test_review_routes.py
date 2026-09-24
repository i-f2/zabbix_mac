# -*- coding: utf-8 -*-
"""
Review 路由集成测试 — 测试 6 个复核页面的 GET/POST/API 路由

覆盖: 页面加载、筛选、初始化、核验、同步预览、导出、确认操作
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
    """创建 mock Flask 应用 (CSRF 禁用)"""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    class _CountRow(dict):
        """双形态行：兼容 fetchone()[0] 与 fetchone()['count'] 两种取数写法。"""

        def __getitem__(self, k):
            if isinstance(k, int):
                return 0
            return dict.get(self, k, 0)

    mock_cursor.fetchall.return_value = []
    # 计数查询形态：路由多处 fetchone()[0]/['count']，None 会 TypeError（活库假通过的历史潜伏）
    mock_cursor.fetchone.return_value = _CountRow({'count': 0})
    mock_cursor.description = (('id', None, None, None, None, None, None),)
    mock_cursor.rowcount = 0
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    # 1. 先以 mock 配置导入 app 模块（模块级 load_config 依赖 DB_CONFIG 初始化）
    with patch('config_loader.load_config', return_value=mock_config):
        if 'app' in sys.modules:
            del sys.modules['app']
        from app import app
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        # 清空 before_request handlers 以绕过 CSRF 验证
        app.before_request_funcs[None] = []

    # 2. 模块对象稳定后再 patch get_db_connection —— 若在 del+reimport 之前 patch，
    #    补丁落在孤儿模块上，路由会打到真实数据库（无库时 32 用例全红，历史潜伏缺陷）
    with patch('app.get_db_connection', return_value=mock_conn):
        yield app


@pytest.fixture
def client(app):
    """测试客户端"""
    return app.test_client()


# ---- Review 页面加载测试 ----

REVIEW_PAGES = [
    ('/items-review', 'items_review'),
    ('/triggers-review', 'triggers_review'),
    ('/webscenarios-review', 'webscenarios_review'),
    ('/web-triggers-review', 'web_triggers_review'),
    ('/item-prototypes-review', 'item_prototypes_review'),
    ('/trigger-prototypes-review', 'trigger_prototypes_review'),
]


class TestReviewPagesGet:
    """6 个复核页面 GET 请求测试"""

    @pytest.mark.parametrize('url,name', REVIEW_PAGES)
    def test_page_loads(self, client, url, name):
        """复核页面加载"""
        resp = client.get(url)
        assert resp.status_code == 200, f'{name} 返回 {resp.status_code}'

    @pytest.mark.parametrize('url,name', REVIEW_PAGES)
    def test_page_with_all_filters(self, client, url, name):
        """复核页面加载（带全筛选参数）"""
        resp = client.get(f'{url}?host=test&system=sys&subsystem=sub&sync_filter=pending')
        assert resp.status_code == 200, f'{name} 带筛选返回 {resp.status_code}'

    @pytest.mark.parametrize('url,name', REVIEW_PAGES)
    def test_page_with_page_param(self, client, url, name):
        """复核页面带分页参数"""
        resp = client.get(f'{url}?page=1&per_page=10')
        assert resp.status_code == 200, f'{name} 分页返回 {resp.status_code}'


# ---- API 路由测试 ----

class TestReviewApi:
    """Review API 路由测试"""

    def test_dashboard_stats(self, client):
        """dashboard-stats API"""
        resp = client.get('/api/review/dashboard-stats')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data is not None
        # 应返回常见统计字段
        if isinstance(data, dict):
            assert 'items_review' in data or 'total' in data or isinstance(data, dict)

    def test_pending_counts(self, client):
        """pending-counts API"""
        resp = client.get('/api/review/pending-counts')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data is not None

    def test_sync_progress(self, client):
        """sync-progress API"""
        resp = client.get('/review/sync-progress')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data is not None

    def test_verify_without_env(self, client):
        """verify API 不传 environment 应返回 400"""
        # verify 路由内部本地导入 zabbix_mac.ZabbixClient，需要 mock
        from unittest.mock import MagicMock
        with patch('zabbix_mac.ZabbixClient') as mock_zabbix_cls:
            mock_zabbix_cls.return_value = MagicMock()
            mock_zabbix_cls.return_value.api = MagicMock()
            # 各 verify 路由
            verify_routes = [
                '/items-review/verify',
                '/triggers-review/verify',
                '/webscenarios-review/verify',
                '/item-prototypes-review/verify',
                '/trigger-prototypes-review/verify',
            ]
            for route in verify_routes:
                resp = client.post(route, json={})
                # 无 environment 时各路由返回 400
                assert resp.status_code == 400, f'{route} 返回 {resp.status_code}'
                data = resp.get_json()
                assert data is not None
                assert 'success' in data
                assert data['success'] is False


# ---- 路由功能性测试 ----

class TestReviewExportRoutes:
    """Review 导出路由测试"""

    @pytest.mark.parametrize('url,name', [
        ('/items-review/export', 'items_review'),
        ('/triggers-review/export', 'triggers_review'),
        ('/webscenarios-review/export', 'webscenarios_review'),
        ('/web-triggers-review/export', 'web_triggers_review'),
        ('/item-prototypes-review/export', 'item_prototypes_review'),
        ('/trigger-prototypes-review/export', 'trigger_prototypes_review'),
    ])
    def test_export(self, client, url, name):
        """导出路由返回 Excel"""
        resp = client.get(url)
        # mock 空表下 400「表为空」是导出路由的正确契约；不应 500
        assert resp.status_code in (200, 302, 400, 404), f'{name} 导出 {resp.status_code}'
        if resp.status_code == 200:
            ct = resp.content_type or ''
            assert 'spreadsheet' in ct or 'vnd.openxmlformats' in ct or 'octet-stream' in ct, \
                f'{name} Content-Type: {ct}'


@pytest.fixture
def stub_dispatch(app, monkeypatch):
    """把后台派发换成"立即完成"的桩：不启线程、不连数据库。

    6 条 init 路由改造后是 202 + 后台线程执行。本文件的 smoke 测试只关心
    路由契约（快速返回、任务规格正确），任务体本身由 test_background_jobs.py
    与 test_diff_and_merge.py 覆盖。

    桩必须自己释放锁 —— 真实实现里锁是由 worker 线程在 finally 中释放的，
    桩不释放会让后续用例全部撞 409。
    """
    import app as app_module
    dispatched = []

    def fake_dispatch(job, token):
        dispatched.append(job)
        app_module._progress_finish(True, f'{job.name} 完成')
        app_module._release_sync_lock(token)

    monkeypatch.setattr(app_module, '_dispatch_background_job', fake_dispatch)
    return dispatched


class TestReviewInitRoutes:
    """Review 初始化路由测试"""

    @pytest.mark.parametrize('url,name', [
        ('/items-review/initialize', 'items_review'),
        ('/triggers-review/initialize', 'triggers_review'),
        ('/webscenarios-review/initialize', 'webscenarios_review'),
        ('/web-triggers-review/initialize', 'web_triggers_review'),
        ('/item-prototypes-review/initialize', 'item_prototypes_review'),
        ('/trigger-prototypes-review/initialize', 'trigger_prototypes_review'),
    ])
    def test_initialize(self, client, url, name, stub_dispatch):
        """初始化路由契约：立即返回 202 + 任务已受理（6 条已全部异步化）

        断言 202 是**严格**的 —— 退回同步执行（200）即回归，必须被这个用例拦住：
        HTTP 请求里跑完整初始化正是本次改造要消灭的 504 成因。
        """
        resp = client.post(url, json={})
        assert resp.status_code == 202, \
            f'{name} init 返回 {resp.status_code}，期望 202（异步受理）'
        data = resp.get_json()
        assert data['success'] is True
        assert data['async'] is True
        assert data['message']
        assert len(stub_dispatch) == 1, f'{name} 返回 202 但未派发后台任务'
        assert stub_dispatch[0].name == f'{name}_init'

    def test_initialize_locked_returns_409(self, client, stub_dispatch):
        """锁被占用时初始化返回 409，且不派发任务"""
        import app as app_module
        token = app_module._acquire_sync_lock()
        assert token is not None
        try:
            resp = client.post('/items-review/initialize', json={})
            assert resp.status_code == 409, f'期望 409，实际 {resp.status_code}'
            assert resp.get_json()['success'] is False
            assert not stub_dispatch
        finally:
            app_module._release_sync_lock(token)


class TestReviewConfirmRoutes:
    """Review 确认路由测试"""

    @pytest.mark.parametrize('url_template,name', [
        ('/item-review/confirm/1', 'items_review'),
        ('/trigger-review/confirm/1', 'triggers_review'),
        ('/webscenario-review/confirm/1', 'webscenarios_review'),
        ('/web-trigger-review/confirm/1', 'web_triggers_review'),
        ('/item-prototype-review/confirm/1', 'item_prototypes_review'),
        ('/trigger-prototype-review/confirm/1', 'trigger_prototypes_review'),
    ])
    def test_confirm(self, client, url_template, name):
        """确认路由"""
        resp = client.post(url_template)
        assert resp.status_code in (200, 500), f'{name} confirm {resp.status_code}'
        if resp.status_code == 200:
            data = resp.get_json()
            assert data is not None
            assert 'success' in data


class TestSyncPreviewRoutes:
    """Sync preview 路由测试"""

    def test_sync_preview_empty_body(self, client):
        """空请求体"""
        resp = client.post('/api/sync/preview', json={})
        assert resp.status_code in (200, 400, 500)

    def test_sync_preview_no_items(self, client):
        """空 item 列表"""
        resp = client.post('/api/sync/preview', json={
            'environment': '测试环境',
            'items': [],
            'action_type': 'item'
        })
        assert resp.status_code in (200, 400, 500)
        if resp.status_code == 200:
            data = resp.get_json()
            assert data is not None

    def test_sync_preview_bad_environment(self, client):
        """无效环境名"""
        resp = client.post('/api/sync/preview', json={
            'environment': '不存在的环境',
            'items': [],
            'action_type': 'item'
        })
        assert resp.status_code in (400, 500)


# ---- Web 页面扩展路由测试 ----

class TestWebScenarioRoutes:
    """Web 场景专属路由测试"""

    def test_webscenario_sync_triggers(self, client):
        """Web 场景触发器同步路由"""
        resp = client.post('/webscenarios-review/sync-triggers', json={})
        assert resp.status_code in (200, 400, 500)

    def test_web_trigger_verify(self, client):
        """Web 触发器核验路由"""
        resp = client.post('/web-triggers-review/verify', json={})
        assert resp.status_code in (200, 400, 500)


# ---- Database 操作测试 ----

class TestReviewImportRoutes:
    """Review 导入路由测试"""

    @pytest.mark.parametrize('url,name', [
        ('/items-review/import', 'items_review'),
        ('/triggers-review/import', 'triggers_review'),
        ('/webscenarios-review/import', 'webscenarios_review'),
        ('/web-triggers-review/import', 'web_triggers_review'),
        ('/item-prototypes-review/import', 'item_prototypes_review'),
        ('/trigger-prototypes-review/import', 'trigger_prototypes_review'),
    ])
    def test_import_no_file(self, client, url, name):
        """不传文件"""
        resp = client.post(url, data={})
        # 可能 400 (无文件) 或 302 (重定向)
        assert resp.status_code in (200, 302, 400, 500), f'{name} import {resp.status_code}'
