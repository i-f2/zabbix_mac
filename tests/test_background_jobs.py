# -*- coding: utf-8 -*-
"""
后台任务基础设施测试 (S1)

覆盖:
  1. 任务异常 → 事务回滚、锁释放、进度写入 success=False
  2. 任务中止 → 回滚、running=False、aborted=True
  3. 派发阶段异常 → 锁释放、异常照常抛出
  4. 锁移交：worker 释放；迟到释放（token 不符）为空操作
  5. 僵死锁回收：超 SYNC_JOB_HARD_TIMEOUT 后可被抢占
  6. _open_worker_connection 保留 search_path 并追加 statement_timeout
  7. 装饰器：成功 → 202 且后台执行；忙碌 → 409；校验失败 → 原样返回并释放锁
"""
import os
import re
import sys
import threading
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
    'sync': {'default_workers': 5, 'max_retry_attempts': 3, 'retry_delay': 2,
             'job_statement_timeout_seconds': 900,
             'job_hard_timeout_seconds': 1800},
    'zabbix_room_mapping': {},
}


@pytest.fixture(scope='module')
def app_module():
    with patch('config_loader.load_config', return_value=MOCK_CONFIG):
        if 'app' in sys.modules:
            del sys.modules['app']
        import app
        yield app


@pytest.fixture
def clean_state(app_module):
    """每个用例前后都把全局锁/进度恢复到空闲，避免相互污染"""
    def reset():
        app_module._sync_abort_event.clear()
        app_module._release_sync_lock(app_module._sync_held_token)
        app_module._sync_held_token = None
        app_module._sync_acquired_at = 0.0
        with app_module._sync_progress_lock:
            app_module._sync_progress.update({
                'running': False, 'success': None, 'aborted': False,
                'message': '', 'errors': [], 'job': '', 'unit': None,
                'phase': '', 'rows_done': 0, 'rows_total': 0, 'percent': None,
                'hosts_done': 0, 'hosts_total': 0, 'current_host': '',
                'updated_at': 0.0,
            })
    reset()
    yield
    reset()


def _fake_conn(commit_raises=False):
    """构造一个 psycopg2 连接替身，游标支持 with 语句"""
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    if commit_raises:
        conn.commit.side_effect = RuntimeError('commit 炸了')
    return conn, cur


def _run_job(app_module, job, token, conn):
    with patch.object(app_module, '_open_worker_connection', return_value=conn):
        app_module._run_background_job(job, token)


# ---- 1 & 2. 任务体的成功/失败/中止 ----

class TestJobLifecycle:

    def test_success_commits_and_marks_success(self, app_module, clean_state):
        conn, _cur = _fake_conn()
        token = app_module._acquire_sync_lock()
        job = app_module._BackgroundJob('demo', lambda ctx, cur: '干完了', unit='条')

        _run_job(app_module, job, token, conn)

        conn.commit.assert_called_once()
        conn.rollback.assert_not_called()
        prog = app_module._sync_progress
        assert prog['running'] is False
        assert prog['success'] is True
        assert prog['message'] == '干完了'
        assert app_module._sync_held_token is None, '锁必须已释放'

    def test_exception_rolls_back_and_releases_lock(self, app_module, clean_state):
        """任务抛异常 → 回滚、锁释放、running=False、success=False"""
        conn, _cur = _fake_conn()
        token = app_module._acquire_sync_lock()

        def boom(ctx, cur):
            raise RuntimeError('上游查询失败')

        _run_job(app_module, app_module._BackgroundJob('demo', boom), token, conn)

        conn.rollback.assert_called()
        conn.commit.assert_not_called()
        prog = app_module._sync_progress
        assert prog['running'] is False
        assert prog['success'] is False
        assert '上游查询失败' in prog['message']
        assert prog['errors'] and '上游查询失败' in prog['errors'][-1]
        assert app_module._sync_held_token is None, '异常路径也必须释放锁'
        # 锁真的能再被拿到
        assert app_module._acquire_sync_lock() is not None

    def test_abort_rolls_back_without_touching_data(self, app_module, clean_state):
        """中止 → 回滚、aborted=True、消息承诺数据未变更"""
        conn, _cur = _fake_conn()
        token = app_module._acquire_sync_lock()

        def aborter(ctx, cur):
            ctx.report('insert', 10, 100)
            raise app_module._JobAborted()

        _run_job(app_module, app_module._BackgroundJob('demo', aborter, unit='条'), token, conn)

        conn.rollback.assert_called()
        conn.commit.assert_not_called()
        prog = app_module._sync_progress
        assert prog['running'] is False
        assert prog['aborted'] is True
        assert prog['success'] is False
        assert '数据未变更' in prog['message']
        assert app_module._sync_held_token is None

    def test_commit_failure_is_reported_and_lock_released(self, app_module, clean_state):
        conn, _cur = _fake_conn(commit_raises=True)
        token = app_module._acquire_sync_lock()

        _run_job(app_module, app_module._BackgroundJob('demo', lambda ctx, cur: None),
                 token, conn)

        assert app_module._sync_progress['success'] is False
        assert app_module._sync_progress['running'] is False
        assert app_module._sync_held_token is None

    def test_connection_is_always_closed(self, app_module, clean_state):
        conn, _cur = _fake_conn()
        token = app_module._acquire_sync_lock()
        _run_job(app_module, app_module._BackgroundJob('demo', lambda ctx, cur: None),
                 token, conn)
        conn.close.assert_called_once()

    def test_connection_closed_even_on_failure(self, app_module, clean_state):
        conn, _cur = _fake_conn()
        token = app_module._acquire_sync_lock()

        def boom(ctx, cur):
            raise RuntimeError('x')

        _run_job(app_module, app_module._BackgroundJob('demo', boom), token, conn)
        conn.close.assert_called_once()

    def test_open_worker_connection_failure_releases_lock(self, app_module, clean_state):
        """连不上库也必须释放锁，否则此后所有同步永久 409"""
        token = app_module._acquire_sync_lock()
        with patch.object(app_module, '_open_worker_connection',
                          side_effect=RuntimeError('连接被拒')):
            app_module._run_background_job(
                app_module._BackgroundJob('demo', lambda ctx, cur: None), token)

        assert app_module._sync_held_token is None
        assert app_module._sync_progress['success'] is False


# ---- 3. 进度上报 ----

class TestJobContext:

    def test_report_sets_rows_and_percent(self, app_module, clean_state):
        conn, _cur = _fake_conn()
        token = app_module._acquire_sync_lock()

        def body(ctx, cur):
            ctx.report('update', 450, 1000)
            assert app_module._sync_progress['percent'] == 45
            assert app_module._sync_progress['rows_done'] == 450
            assert app_module._sync_progress['rows_total'] == 1000
            assert app_module._sync_progress['unit'] == '条'
            assert app_module._sync_progress['phase'] == 'update'

        job = app_module._BackgroundJob('demo', body, unit='条')
        _run_job(app_module, job, token, conn)
        assert app_module._sync_progress['success'] is True

    def test_report_with_zero_total_gives_zero_percent(self, app_module, clean_state):
        conn, _cur = _fake_conn()
        token = app_module._acquire_sync_lock()

        def body(ctx, cur):
            ctx.report('insert', 0, 0)
            assert app_module._sync_progress['percent'] == 0

        _run_job(app_module, app_module._BackgroundJob('demo', body, unit='条'), token, conn)

    def test_report_phase_keeps_row_counts(self, app_module, clean_state):
        conn, _cur = _fake_conn()
        token = app_module._acquire_sync_lock()

        def body(ctx, cur):
            ctx.report('insert', 10, 10)
            ctx.report_phase('update', '正在合并变更...')
            assert app_module._sync_progress['phase'] == 'update'
            assert app_module._sync_progress['rows_done'] == 10

        _run_job(app_module, app_module._BackgroundJob('demo', body, unit='条'), token, conn)

    def test_report_hosts_feeds_host_branch(self, app_module, clean_state):
        """主机级进度不得污染 rows_*，前端才能走 host 分支"""
        conn, _cur = _fake_conn()
        token = app_module._acquire_sync_lock()

        def body(ctx, cur):
            ctx.report_hosts(3, 10, '10.0.0.3')
            p = app_module._sync_progress
            assert p['hosts_done'] == 3 and p['hosts_total'] == 10
            assert p['current_host'] == '10.0.0.3'
            assert p['rows_total'] == 0 and p['percent'] is None

        _run_job(app_module, app_module._BackgroundJob('demo', body), token, conn)

    def test_should_abort_reflects_abort_event(self, app_module, clean_state):
        conn, _cur = _fake_conn()
        token = app_module._acquire_sync_lock()
        seen = []

        def body(ctx, cur):
            seen.append(ctx.should_abort())
            app_module._sync_abort_event.set()
            seen.append(ctx.should_abort())

        _run_job(app_module, app_module._BackgroundJob('demo', body), token, conn)
        assert seen == [False, True]

    def test_finish_snaps_progress_to_100(self, app_module, clean_state):
        conn, _cur = _fake_conn()
        token = app_module._acquire_sync_lock()

        def body(ctx, cur):
            ctx.report('insert', 40, 100)

        _run_job(app_module, app_module._BackgroundJob('demo', body, unit='条'), token, conn)
        assert app_module._sync_progress['percent'] == 100
        assert app_module._sync_progress['rows_done'] == 100


# ---- 4. 锁移交与 token 语义 ----

class TestLockHandoff:

    def test_second_acquire_fails_while_held(self, app_module, clean_state):
        assert app_module._acquire_sync_lock() is not None
        assert app_module._acquire_sync_lock() is None

    def test_release_with_wrong_token_is_noop(self, app_module, clean_state):
        """僵死锁被回收并由新任务接管后，原 worker 的迟到释放不得误伤"""
        stale = app_module._acquire_sync_lock()
        assert app_module._try_reclaim_stale_lock() is False, '未超时不应回收'
        # 强制回收（模拟超时）
        app_module._sync_acquired_at = 0.0
        with app_module._sync_progress_lock:
            app_module._sync_progress['updated_at'] = 0.0
        with patch.object(app_module, 'SYNC_JOB_HARD_TIMEOUT', -1):
            assert app_module._try_reclaim_stale_lock() is True

        fresh = app_module._acquire_sync_lock()
        assert fresh is not None and fresh != stale

        app_module._release_sync_lock(stale)          # 迟到释放
        assert app_module._sync_held_token == fresh, '迟到释放不得释放新任务的锁'
        assert app_module._acquire_sync_lock() is None, '锁应仍被新任务持有'

    def test_release_none_token_is_noop(self, app_module, clean_state):
        token = app_module._acquire_sync_lock()
        app_module._release_sync_lock(None)
        assert app_module._sync_held_token == token

    def test_release_twice_is_safe(self, app_module, clean_state):
        token = app_module._acquire_sync_lock()
        app_module._release_sync_lock(token)
        app_module._release_sync_lock(token)          # 不应抛 RuntimeError
        assert app_module._acquire_sync_lock() is not None

    def test_tokens_are_monotonic(self, app_module, clean_state):
        a = app_module._acquire_sync_lock()
        app_module._release_sync_lock(a)
        b = app_module._acquire_sync_lock()
        assert b > a

    def test_lock_released_from_worker_thread(self, app_module, clean_state):
        """真实线程下完成一次完整移交"""
        conn, _cur = _fake_conn()
        token = app_module._acquire_sync_lock()
        done = threading.Event()

        def body(ctx, cur):
            done.set()

        with patch.object(app_module, '_open_worker_connection', return_value=conn):
            t = threading.Thread(target=app_module._run_background_job,
                                 args=(app_module._BackgroundJob('demo', body), token))
            t.start()
            t.join(timeout=5)

        assert done.is_set()
        assert app_module._sync_held_token is None
        assert app_module._acquire_sync_lock() is not None


# ---- 5. 僵死锁回收 ----

class TestStaleLockReclaim:

    def test_reclaim_when_acquired_at_is_stale(self, app_module, clean_state):
        app_module._acquire_sync_lock()
        with patch.object(app_module, 'SYNC_JOB_HARD_TIMEOUT', -1):
            assert app_module._try_reclaim_stale_lock() is True
        assert app_module._sync_held_token is None

    def test_fresh_heartbeat_prevents_reclaim(self, app_module, clean_state):
        """长任务持续刷新 updated_at，不应被误回收"""
        app_module._acquire_sync_lock()
        app_module._sync_acquired_at = 0.0                 # 拿锁时刻很旧
        with app_module._sync_progress_lock:
            app_module._sync_progress['updated_at'] = __import__('time').monotonic()
        assert app_module._try_reclaim_stale_lock() is False, '有心跳就不算僵死'

    def test_reclaim_on_free_lock_returns_false(self, app_module, clean_state):
        assert app_module._sync_held_token is None
        assert app_module._try_reclaim_stale_lock() is False


# ---- 4b. 同步锁装饰器（12 条既有路由共用） ----

class TestSyncLockDecorator:
    """_with_sync_lock 由直接 acquire/release 改为 token 移交后的回归"""

    def test_releases_on_success(self, app_module, clean_state):
        @app_module._with_sync_lock
        def f():
            return 'ok'

        with app_module.app.test_request_context('/x', method='POST'):
            assert f() == 'ok'
        assert app_module._sync_held_token is None
        assert app_module._acquire_sync_lock() is not None

    def test_returns_409_when_held(self, app_module, clean_state):
        held = app_module._acquire_sync_lock()
        try:
            @app_module._with_sync_lock
            def f():
                raise AssertionError('锁被占用时路由体不得执行')

            with app_module.app.test_request_context('/x', method='POST'):
                resp, status = f()
            assert status == 409
            assert resp.get_json()['message'] == '另一个同步/初始化操作正在进行，请稍后再试'
        finally:
            app_module._release_sync_lock(held)

    def test_releases_on_exception(self, app_module, clean_state):
        @app_module._with_sync_lock
        def f():
            raise ValueError('boom')

        with app_module.app.test_request_context('/x', method='POST'):
            with pytest.raises(ValueError):
                f()
        assert app_module._sync_held_token is None
        assert app_module._acquire_sync_lock() is not None

    def test_repeated_calls_do_not_leak_lock(self, app_module, clean_state):
        @app_module._with_sync_lock
        def f():
            return 'ok'

        with app_module.app.test_request_context('/x', method='POST'):
            for _ in range(5):
                assert f() == 'ok'
        assert app_module._sync_held_token is None


# ---- 6. worker 连接构造 ----

class TestWorkerConnection:

    def test_search_path_preserved_and_timeout_appended(self, app_module):
        """覆盖 options 会让所有查询报 relation does not exist —— 必须追加"""
        captured = {}

        def fake_connect(**kwargs):
            captured.update(kwargs)
            return MagicMock()

        with patch('psycopg2.connect', side_effect=fake_connect):
            app_module._open_worker_connection()

        opts = captured['options']
        assert '-c search_path=zabbix_mac' in opts, 'search_path 必须原样保留'
        assert f'-c statement_timeout={app_module.SYNC_JOB_STATEMENT_TIMEOUT_MS}' in opts
        assert captured['database'] == 'ops'
        assert captured['user'] == 'postgres'

    def test_default_statement_timeout_is_15min(self, app_module):
        assert app_module.SYNC_JOB_STATEMENT_TIMEOUT_MS == 900 * 1000

    def test_db_config_itself_is_not_mutated(self, app_module):
        """_open_worker_connection 不得就地改动全局 DB_CONFIG"""
        before = app_module.DB_CONFIG['options']
        with patch('psycopg2.connect', return_value=MagicMock()):
            app_module._open_worker_connection()
        assert app_module.DB_CONFIG['options'] == before
        assert 'statement_timeout' not in app_module.DB_CONFIG['options']


# ---- 7. 装饰器 ----

class TestBackgroundSyncLockDecorator:

    @staticmethod
    def _call(app_module, body, name='demo'):
        """直接调用被装饰的包装函数并归一化返回值。

        不注册真实路由：Flask 在首个请求后禁止 _check_setup_finished 之外的
        setup 调用，注册路由会污染整个 module 级 app fixture。
        """
        @app_module._with_background_sync_lock(name)
        def route():
            return body()

        with app_module.app.test_request_context('/__test_job', method='POST'):
            result = route()
        if isinstance(result, tuple):
            return result[0], result[1]
        return result, result.status_code

    def test_success_returns_202_and_runs_inline(self, app_module, clean_state):
        conn, _cur = _fake_conn()
        ran = []

        def body():
            return app_module._BackgroundJob(
                'demo', lambda ctx, cur: ran.append(1) or '完成', unit='条')

        with patch.object(app_module, '_background_jobs_inline', True), \
             patch.object(app_module, '_open_worker_connection', return_value=conn):
            resp, status = self._call(app_module, body)

        assert status == 202
        payload = resp.get_json()
        assert payload['async'] is True
        assert '后台启动' in payload['message']
        assert ran == [1], 'inline 模式下任务体应已执行'
        assert app_module._sync_progress['success'] is True
        assert app_module._sync_progress['job'] == 'demo'

    def test_busy_returns_409(self, app_module, clean_state):
        held = app_module._acquire_sync_lock()
        try:
            resp, status = self._call(
                app_module,
                lambda: app_module._BackgroundJob('demo', lambda c, k: None))
            assert status == 409
            assert '请稍后再试' in resp.get_json()['message']
        finally:
            app_module._release_sync_lock(held)

    def test_busy_does_not_run_job_body(self, app_module, clean_state):
        held = app_module._acquire_sync_lock()
        called = []
        try:
            self._call(app_module, lambda: called.append(1))   # 路由体不应被调用
            assert called == []
        finally:
            app_module._release_sync_lock(held)

    def test_validation_failure_passes_through_and_releases_lock(self, app_module, clean_state):
        """路由体校验失败返回 400 → 原样返回且立即释放锁"""
        def body():
            return app_module.jsonify({'success': False, 'message': '无效的环境'}), 400

        resp, status = self._call(app_module, body)

        assert status == 400
        assert resp.get_json()['message'] == '无效的环境'
        assert app_module._sync_held_token is None, '校验失败必须释放锁'
        assert app_module._acquire_sync_lock() is not None

    def test_route_exception_releases_lock_and_propagates(self, app_module, clean_state):
        def body():
            raise ValueError('路由体炸了')

        with pytest.raises(ValueError):
            self._call(app_module, body)
        assert app_module._sync_held_token is None

    def test_abort_event_cleared_before_dispatch(self, app_module, clean_state):
        """上一轮残留的中止信号不得毒化新任务"""
        app_module._sync_abort_event.set()
        seen = []

        def body():
            seen.append(app_module._sync_abort_event.is_set())
            return app_module._BackgroundJob('demo', lambda ctx, cur: None)

        with patch.object(app_module, '_background_jobs_inline', True), \
             patch.object(app_module, '_open_worker_connection',
                          return_value=_fake_conn()[0]):
            self._call(app_module, body)

        assert seen == [False], '派发前必须已清除中止信号'

    def test_progress_reset_before_dispatch(self, app_module, clean_state):
        """派发前进度必须已重置且 running=True，否则并发请求会误判锁僵死"""
        with app_module._sync_progress_lock:
            app_module._sync_progress['updated_at'] = 0.0
            app_module._sync_progress['rows_total'] = 999
        seen = {}

        def body():
            with app_module._sync_progress_lock:
                seen.update(app_module._sync_progress)
            return app_module._BackgroundJob('demo', lambda ctx, cur: None)

        with patch.object(app_module, '_background_jobs_inline', True), \
             patch.object(app_module, '_open_worker_connection',
                          return_value=_fake_conn()[0]):
            self._call(app_module, body)

        assert seen['running'] is True
        assert seen['rows_total'] == 0, '陈旧进度必须已清零'
        assert seen['updated_at'] > 0, '心跳必须已刷新，否则会被误判为僵死锁'

    def test_real_route_still_returns_409_when_locked(self, app_module, clean_state):
        """_with_sync_lock 改用 token 后，既有 12 条路由的 409 行为必须逐字不变"""
        held = app_module._acquire_sync_lock()
        try:
            with app_module.app.test_request_context('/review/sync-all', method='POST'):
                resp, status = app_module.sync_all_to_zabbix()
            assert status == 409
            assert '另一个同步/初始化操作正在进行，请稍后再试' in resp.get_json()['message']
        finally:
            app_module._release_sync_lock(held)

    def test_non_inline_dispatch_returns_immediately(self, app_module, clean_state):
        """真实线程模式：HTTP 立即返回 202，任务体在后台跑"""
        conn, _cur = _fake_conn()
        release = threading.Event()
        started = threading.Event()

        def body():
            def work(ctx, cur):
                started.set()
                release.wait(timeout=5)
                return '后台完成'
            return app_module._BackgroundJob('demo', work, unit='条')

        with patch.object(app_module, '_open_worker_connection', return_value=conn):
            resp, status = self._call(app_module, body)
            assert status == 202, 'HTTP 必须立即返回，不等任务跑完'
            assert started.wait(timeout=5), '任务应已在后台线程启动'
            assert app_module._sync_progress['running'] is True, '此刻仍在运行中'
            release.set()

        deadline = __import__('time').time() + 5
        while app_module._sync_progress['running'] and __import__('time').time() < deadline:
            __import__('time').sleep(0.01)
        assert app_module._sync_progress['success'] is True
        assert app_module._sync_progress['message'] == '后台完成'
        assert app_module._sync_held_token is None


class TestDiffInitSpecs:
    """6 条 diff init 路由现在共用 _diff_init_job + 表驱动 spec（S2/S4）。

    这里只钉住"路由接线"部分：spec 与路由一一对应、快照发生在请求线程、
    以及两个原型路由对筛选参数的**刻意忽略**。SQL / 列定义与改造前的逐字
    等价由独立的比对脚本核对，不在单测里重复。
    """

    SPECS = [
        ('_ITEMS_INIT_SPEC', 'items_review', 'items_review_init', True),
        ('_TRIGGERS_INIT_SPEC', 'triggers_review', 'triggers_review_init', True),
        ('_ITEM_PROTOTYPES_INIT_SPEC', 'item_prototypes_review',
         'item_prototypes_review_init', False),
        ('_TRIGGER_PROTOTYPES_INIT_SPEC', 'trigger_prototypes_review',
         'trigger_prototypes_review_init', False),
    ]

    @pytest.mark.parametrize('attr,table,job_name,accepts_filters',
                             [(a, t, j, f) for a, t, j, f in SPECS])
    def test_spec_matches_route(self, app_module, attr, table, job_name, accepts_filters):
        spec = getattr(app_module, attr)
        assert spec['job_name'] == job_name
        assert spec['table'] == table
        assert spec['unique_keys'][-1] == 'host_ip', '唯一键末位约定为主机列'
        assert set(spec['content_columns']) <= set(spec['all_insert_cols']), \
            '内容列必须是插入列的子集，否则 EXCLUDED 引用会落空'
        assert spec['upstream_sql']('1=1').count('CROSS JOIN hosts h') == 1
        assert spec.get('accepts_filters', True) is accepts_filters

    def test_all_six_specs_have_distinct_tables(self, app_module):
        tables = [getattr(app_module, a)['table'] for a, *_ in self.SPECS]
        assert len(tables) == len(set(tables))

    def test_request_thread_snapshots_filters(self, app_module):
        """筛选条件必须在请求线程快照进 job，worker 里不得再读 request"""
        with app_module.app.test_request_context('/__t', method='POST'):
            job = app_module._diff_init_job(
                app_module._ITEMS_INIT_SPEC, {'system': ' 核心 ', 'subsystem': '账务'})
        assert job.name == 'items_review_init'
        assert job.unit == '条'
        # 快照结果落在闭包里，通过任务体实际使用的 where 反映出来
        captured = {}

        def fake_merge(cur, table, unique_keys, content_columns,
                       new_rows, existing_rows, all_insert_cols,
                       progress_cb=None, abort_cb=None):
            captured['table'] = table
            return {'new': 0, 'update': 0, 'delete': 0, 'unchanged': 0}

        cur = MagicMock()
        cur.fetchall.return_value = []
        # items spec 带 banner，会额外跑一次 COUNT(*) —— 得让 fetchone 可比较
        cur.fetchone.return_value = {'cnt': 0}
        with patch.object(app_module, '_diff_and_merge', side_effect=fake_merge):
            job.run(MagicMock(), cur)
        assert captured['table'] == 'items_review'
        # 带筛选 → 上游 SQL 里出现 h.system / h.subsystem 两个占位
        upstream_calls = [c for c in cur.execute.call_args_list
                          if 'CROSS JOIN hosts h' in str(c.args[0])]
        assert len(upstream_calls) == 1
        assert upstream_calls[0].args[1] == ['21001', '核心', '账务']

    def test_prototype_specs_ignore_filters(self, app_module):
        """两个原型路由改造前完全忽略 system/subsystem，改造后必须照旧 ——
        否则一个带参数的 POST 会悄悄把筛选应用上去，与改造前行为不一致。"""
        with app_module.app.test_request_context('/__t', method='POST'):
            job = app_module._diff_init_job(
                app_module._ITEM_PROTOTYPES_INIT_SPEC, {'system': '核心', 'subsystem': '账务'})
        cur = MagicMock()
        cur.fetchall.return_value = []
        with patch.object(app_module, '_diff_and_merge',
                          return_value={'new': 0, 'update': 0, 'delete': 0, 'unchanged': 0}):
            job.run(MagicMock(), cur)
        upstream_calls = [c for c in cur.execute.call_args_list
                          if 'CROSS JOIN hosts h' in str(c.args[0])]
        assert len(upstream_calls) == 1
        assert upstream_calls[0].args[1] == ['21001'], '筛选参数不得被应用'
        # 注意：SELECT 列表里本来就有 h.system 这一输出列，只能看 WHERE 部分
        where_part = str(upstream_calls[0].args[0]).split('WHERE', 1)[1]
        assert 'h.system = %s' not in where_part
        assert 'h.subsystem = %s' not in where_part

    @pytest.mark.parametrize('attr,table,job_name,accepts_filters',
                             [(a, t, j, f) for a, t, j, f in SPECS])
    def test_route_is_wired_to_background_decorator(
            self, app_module, attr, table, job_name, accepts_filters):
        """路由必须真的挂上后台装饰器 —— 只查 spec 字典是自说自话。

        端点是按函数名注册的，且 spec 的 job_name 与实际装饰器参数必须一致，
        否则进度里的 job 字段会对不上（前端按 job 判断任务类型）。
        """
        expected_endpoint = f'initialize_{table}'
        matched = [ep for ep, view in app_module.app.view_functions.items()
                   if getattr(view, '__background_job_name__', None) == job_name]
        assert matched == [expected_endpoint], \
            f'挂上后台装饰器 {job_name} 的端点为 {matched}，期望 {[expected_endpoint]}'


class _Recorder:
    """记录 SQL 调用顺序的假 cursor，供重建式任务体断言。"""

    def __init__(self, rows):
        self.rows = rows
        self.calls = []          # [(sql, params), ...]
        self.insert_batches = []  # execute_values 的批次长度

    def execute(self, sql, params=None):
        self.calls.append((sql, params))

    def fetchall(self):
        return self.rows

    def sqls(self):
        return [c[0] for c in self.calls]

    def index_of(self, needle):
        for i, sql in enumerate(self.sqls()):
            if needle in sql:
                return i
        return -1


class TestRebuildInitJob:
    """两条重建式 init（webscenarios / web-triggers）的任务体。

    重点钉住 S5 修掉的既有缺陷与中止语义：
      - TRUNCATE 必须发生在源数据 SELECT **之后**（原实现反了，整表在慢查询期间
        持 ACCESS EXCLUSIVE 锁）
      - 中止检查必须先于 TRUNCATE（此时中止不动任何数据）
    """

    def _rows(self, n):
        return [{'host': 'Zabbix server', 'web_scenario_name': f's{i}',
                 'system': 'A', 'subsystem': 'B', 'in_room': 'SZSE'} for i in range(n)]

    def _run(self, app_module, rows, abort_after=None, patch_execute_values=True):
        """跑 _job_body_rebuild，返回 (recorder, 结果文案或 'ABORTED')。

        abort_after=N 表示"第 N 条 SQL 发出后开始返回中止信号"，用来把中止
        精确钉在 TRUNCATE 前后。
        """
        spec = dict(app_module._WEB_TRIGGERS_INIT_SPEC)
        spec['system'] = spec['subsystem'] = ''
        spec['room_mapping'] = {'SZSE': '10.0.0.1'}
        cur = _Recorder(rows)
        ctx = MagicMock()
        ctx.should_abort.side_effect = (
            (lambda: len(cur.calls) >= abort_after) if abort_after is not None
            else (lambda: False))
        try:
            if patch_execute_values:
                with patch('psycopg2.extras.execute_values'):
                    return cur, app_module._job_body_rebuild(spec, ctx, cur)
            return cur, app_module._job_body_rebuild(spec, ctx, cur)
        except app_module._JobAborted:
            return cur, 'ABORTED'

    def test_truncate_happens_after_source_select(self, app_module):
        """先读后清 —— 这是 S5 修掉的锁窗口缺陷，顺序反了必须被拦住"""
        cur, msg = self._run(app_module, self._rows(3))
        i_select = cur.index_of('FROM webscenario_items_review')
        i_trunc = cur.index_of('TRUNCATE')
        assert i_select != -1 and i_trunc != -1, f'缺少语句: {cur.sqls()}'
        assert i_select < i_trunc, '源数据 SELECT 必须早于 TRUNCATE'
        assert '插入 3 条记录' in msg

    def test_truncate_is_inside_same_transaction(self, app_module):
        """任务体不得自己 commit —— 否则 TRUNCATE 的回滚语义失效"""
        cur, _ = self._run(app_module, self._rows(2))
        assert not any('COMMIT' in s.upper() for s in cur.sqls())

    def test_abort_before_truncate_touches_no_data(self, app_module):
        """中止应发生在 TRUNCATE 之前：数据零变更"""
        cur, outcome = self._run(app_module, self._rows(3), abort_after=1)
        assert outcome == 'ABORTED'
        assert 'TRUNCATE' not in ' '.join(cur.sqls()), '中止路径不得清表'

    def test_empty_source_still_truncates(self, app_module):
        """源表无数据时仍要清空复核表 —— 改造前的可见行为"""
        cur, msg = self._run(app_module, [])
        assert 'TRUNCATE' in ' '.join(cur.sqls())
        assert '表已清空' in msg
        assert 'INSERT' not in ' '.join(cur.sqls())

    def test_insert_is_chunked(self, app_module):
        """1200 行 → 500/500/200 三批，而不是 1200 次往返"""
        spec = dict(app_module._WEB_TRIGGERS_INIT_SPEC)
        spec['system'] = spec['subsystem'] = ''
        spec['room_mapping'] = {}
        cur = _Recorder(self._rows(1200))
        ctx = MagicMock()
        ctx.should_abort.return_value = False
        with patch('psycopg2.extras.execute_values') as ev:
            app_module._job_body_rebuild(spec, ctx, cur)
        sizes = [len(c.args[2]) for c in ev.call_args_list]
        assert sizes == [500, 500, 200], f'分片长度 {sizes}'

    def test_progress_is_reported(self, app_module):
        """行级进度要一路报到 total，前端才能推进进度条"""
        spec = dict(app_module._WEB_TRIGGERS_INIT_SPEC)
        spec['system'] = spec['subsystem'] = ''
        spec['room_mapping'] = {}
        cur = _Recorder(self._rows(1200))
        ctx = MagicMock()
        ctx.should_abort.return_value = False
        with patch('psycopg2.extras.execute_values'):
            app_module._job_body_rebuild(spec, ctx, cur)
        reported = ctx.report.call_args_list
        assert reported, '未上报任何行级进度'
        assert reported[-1].args == ('insert', 1200, 1200)

    def test_rebuild_routes_are_background(self, app_module):
        for attr, job_name in (('_WEBSCENARIOS_INIT_SPEC', 'webscenarios_review_init'),
                               ('_WEB_TRIGGERS_INIT_SPEC', 'web_triggers_review_init')):
            spec = getattr(app_module, attr)
            assert spec['job_name'] == job_name
            matched = [ep for ep, view in app_module.app.view_functions.items()
                       if getattr(view, '__background_job_name__', None) == job_name]
            assert len(matched) == 1, f'{job_name} 的端点为 {matched}'