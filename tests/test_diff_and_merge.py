# -*- coding: utf-8 -*-
"""
_diff_and_merge 批量写测试 — 验证 S0 重构后的写入行为

覆盖:
  1. UPDATE 折进 upsert：N 条变更只发 1 条 execute_values，而非 N 次 cur.execute
  2. 生成的 SQL 形状正确（ON CONFLICT ... DO UPDATE SET / sync_status='pending_confirm'）
  3. DELETE 合并为单条 `WHERE id = ANY(%s) AND sync_status = 'synced'`
  4. 返回值 result 字典与重构前的旧实现逐键相等
  5. 进度钩子与中止钩子
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

TABLE = 'items_review'
UNIQUE_KEYS = ['item_id', 'host_ip']
CONTENT_COLUMNS = ['name', 'key_']
ALL_COLS = ['item_id', 'host_ip', 'name', 'key_', 'system', 'subsystem', 'in_room']


@pytest.fixture(scope='module')
def app_module():
    """导入 app 模块（mock 掉 config_loader，避免依赖真实配置/数据库）"""
    with patch('config_loader.load_config', return_value=MOCK_CONFIG):
        if 'app' in sys.modules:
            del sys.modules['app']
        import app
        yield app


def _src(item_id, name, host='10.0.0.1'):
    return {'item_id': str(item_id), 'host_ip': host, 'name': name,
            'key_': 'k%s' % item_id, 'system': 'SYS', 'subsystem': 'SUB',
            'in_room': '机房A'}


def _existing(row_id, item_id, name, sync_status='synced', confirmed=False,
              host='10.0.0.1'):
    return {'id': row_id, 'item_id': str(item_id), 'host_ip': host,
            'name': name, 'key_': 'k%s' % item_id, 'system': 'SYS',
            'subsystem': 'SUB', 'in_room': '机房A',
            'sync_status': sync_status, 'confirmed': confirmed}


def _run(app_module, new_rows, existing_rows, **kwargs):
    cur = MagicMock()
    with patch('psycopg2.extras.execute_values') as mock_ev:
        result = app_module._diff_and_merge(
            cur, TABLE, UNIQUE_KEYS, CONTENT_COLUMNS,
            new_rows, existing_rows, ALL_COLS, **kwargs)
    return result, cur, mock_ev


# ---- 旧实现的返回口径（重构前的 diff 逻辑，原样保留作为对照） ----

def _legacy_result(new_rows, existing_rows):
    existing_by_key = {}
    for row in existing_rows:
        key = tuple(str(row.get(k, '')) for k in UNIQUE_KEYS)
        existing_by_key[key] = row

    new_keys = set()
    inserts = 0
    updates = 0
    unchanged_synced = 0
    unchanged_pending = 0

    for src in new_rows:
        key = tuple(str(src.get(k, '')) for k in UNIQUE_KEYS)
        new_keys.add(key)
        if key not in existing_by_key:
            inserts += 1
        else:
            existing = existing_by_key[key]
            changed = any(
                str(src.get(col, '')) != str(existing.get(col, ''))
                for col in CONTENT_COLUMNS
            )
            if changed:
                updates += 1
            elif existing.get('sync_status') == 'synced':
                unchanged_synced += 1
            else:
                unchanged_pending += 1

    deletions = 0
    for key, row in existing_by_key.items():
        if (key not in new_keys
                and row.get('sync_status') == 'synced'
                and not row.get('confirmed', False)):
            deletions += 1

    return {'new': inserts, 'update': updates, 'delete': deletions,
            'unchanged': unchanged_synced + unchanged_pending}


# ---- 夹具 ----

def _mixed_fixture():
    """1 新增 / 1 变更 / 2 不变 / 1 待删除 / 1 已确认（不删除）"""
    new_rows = [
        _src(1, 'A'),           # 全新
        _src(2, 'B2'),          # 内容变更（原 B1）
        _src(3, 'C'),           # 未变，synced
        _src(4, 'D'),           # 未变，待同步
    ]
    existing_rows = [
        _existing(101, 2, 'B1', 'synced'),
        _existing(102, 3, 'C', 'synced'),
        _existing(103, 4, 'D', 'pending_confirm'),
        _existing(104, 9, 'Z', 'synced'),               # 上游已无 → 删除
        _existing(105, 10, 'Y', 'synced', confirmed=True),  # 已确认 → 不删除
    ]
    return new_rows, existing_rows


# ---- 1 & 4. 返回值口径 ----

class TestResultEquivalence:
    """result 字典必须与重构前逐键相等"""

    def test_mixed_fixture_matches_legacy(self, app_module):
        new_rows, existing_rows = _mixed_fixture()
        expected = _legacy_result(new_rows, existing_rows)
        result, _cur, _ev = _run(app_module, new_rows, existing_rows)
        assert result == expected
        assert result == {'new': 1, 'update': 1, 'delete': 1, 'unchanged': 2}

    def test_empty_inputs(self, app_module):
        result, cur, mock_ev = _run(app_module, [], [])
        assert result == {'new': 0, 'update': 0, 'delete': 0, 'unchanged': 0}
        assert mock_ev.call_count == 0
        assert cur.execute.call_count == 0

    @pytest.mark.parametrize('n_changed,n_unchanged,n_deleted', [
        (0, 5, 0), (5, 0, 0), (0, 0, 5), (12, 7, 3), (200, 50, 9),
    ])
    def test_counts_match_legacy_across_shapes(self, app_module, n_changed,
                                               n_unchanged, n_deleted):
        new_rows, existing_rows = [], []
        row_id = 1000
        for i in range(n_changed):
            new_rows.append(_src(i, 'NEW%d' % i))
            existing_rows.append(_existing(row_id, i, 'OLD%d' % i, 'synced'))
            row_id += 1
        for i in range(n_changed, n_changed + n_unchanged):
            new_rows.append(_src(i, 'SAME%d' % i))
            existing_rows.append(_existing(row_id, i, 'SAME%d' % i, 'synced'))
            row_id += 1
        for i in range(100, 100 + n_deleted):
            existing_rows.append(_existing(row_id, i, 'GONE%d' % i, 'synced'))
            row_id += 1

        expected = _legacy_result(new_rows, existing_rows)
        result, _cur, _ev = _run(app_module, new_rows, existing_rows)
        assert result == expected


# ---- 2 & 3. SQL 形状 ----

class TestSqlShape:
    """写入语句形状：批量 upsert + 单条批量删除"""

    def test_updates_use_single_batched_upsert(self, app_module):
        """100 条变更 → 恰好 1 次 execute_values，0 次逐行 cur.execute"""
        n = 100
        new_rows = [_src(i, 'NEW%d' % i) for i in range(n)]
        existing_rows = [
            _existing(1000 + i, i, 'OLD%d' % i, 'synced') for i in range(n)
        ]

        result, cur, mock_ev = _run(app_module, new_rows, existing_rows)

        assert result['update'] == n
        assert mock_ev.call_count == 1, '变更应合并为单条批量 upsert'
        assert cur.execute.call_count == 0, '不应再有逐行 UPDATE'

        _cur_arg, sql, argslist = mock_ev.call_args[0]
        assert 'ON CONFLICT (item_id, host_ip) DO UPDATE SET' in sql
        assert "sync_status = 'pending_confirm'" in sql
        assert "change_type = 'update'" in sql
        assert 'updated_at = CURRENT_TIMESTAMP' in sql
        assert len(argslist) == n

    def test_update_upsert_sets_only_insert_cols_via_excluded(self, app_module):
        """EXCLUDED 只覆盖 all_insert_cols，不动 id / created_at / confirmed"""
        new_rows = [_src(1, 'CHANGED')]
        existing_rows = [_existing(1001, 1, 'ORIG', 'synced')]

        _result, _cur, mock_ev = _run(app_module, new_rows, existing_rows)
        sql = mock_ev.call_args[0][1]

        for col in ALL_COLS:
            assert 'EXCLUDED.%s' % col in sql
        for untouched in ('id', 'created_at', 'confirmed', 'status_verification'):
            assert '%s = EXCLUDED.%s' % (untouched, untouched) not in sql

    def test_insert_keeps_do_nothing(self, app_module):
        """INSERT 分支必须保持 DO NOTHING（筛选初始化依赖该边界行为）"""
        new_rows = [_src(1, 'A')]
        _result, _cur, mock_ev = _run(app_module, new_rows, [])

        sql = mock_ev.call_args[0][1]
        assert 'ON CONFLICT (item_id, host_ip) DO NOTHING' in sql
        assert 'DO UPDATE SET' not in sql

    def test_deletions_use_single_any_statement(self, app_module):
        """40 条删除 → 恰好 1 次 cur.execute，含 ANY(%s) 与 synced 守卫"""
        n = 40
        existing_rows = [
            _existing(2000 + i, i, 'GONE%d' % i, 'synced') for i in range(n)
        ]

        result, cur, mock_ev = _run(app_module, [], existing_rows)

        assert result['delete'] == n
        assert mock_ev.call_count == 0
        assert cur.execute.call_count == 1

        sql, params = cur.execute.call_args[0]
        assert 'WHERE id = ANY(%s)' in sql
        assert "AND sync_status = 'synced'" in sql
        assert "sync_status = 'pending_delete'" in sql
        assert "change_type = 'delete'" in sql
        assert params == ([2000 + i for i in range(n)],)

    def test_deletions_chunked_at_500(self, app_module):
        """超过 500 条删除必须分片，避免逼近 PostgreSQL 参数上限"""
        n = 1200
        existing_rows = [
            _existing(3000 + i, i, 'GONE%d' % i, 'synced') for i in range(n)
        ]

        result, cur, _ev = _run(app_module, [], existing_rows)

        assert result['delete'] == n
        assert cur.execute.call_count == 3  # 500 + 500 + 200
        sizes = [len(call.args[1][0]) for call in cur.execute.call_args_list]
        assert sizes == [500, 500, 200]

    def test_duplicate_update_keys_are_deduped(self, app_module):
        """同键重复行不得进入 upsert（否则 cannot affect row a second time）"""
        new_rows = [_src(1, 'X'), _src(1, 'Y')]   # 同一 (item_id, host_ip)
        existing_rows = [_existing(1001, 1, 'ORIG', 'synced')]

        _result, _cur, mock_ev = _run(app_module, new_rows, existing_rows)

        assert mock_ev.call_count == 1
        assert len(mock_ev.call_args[0][2]) == 1


# ---- 5. 进度与中止钩子 ----

class TestHooks:

    def test_progress_callback_reports_monotonic_done(self, app_module):
        events = []
        new_rows = [_src(i, 'NEW%d' % i) for i in range(250)]
        existing_rows = [
            _existing(1000 + i, i, 'OLD%d' % i, 'synced') for i in range(250)
        ]

        _run(app_module, new_rows, existing_rows,
             progress_cb=lambda phase, done, total: events.append((phase, done, total)))

        assert events, '应至少上报一次进度'
        dones = [e[1] for e in events]
        assert dones == sorted(dones), 'done 必须单调不减'
        assert all(e[2] == 250 for e in events), 'total 应恒等于待处理总数'
        assert events[-1][1] == 250, '末次进度应等于总数'
        assert {e[0] for e in events} == {'update'}

    def test_abort_callback_raises_job_aborted(self, app_module):
        new_rows = [_src(i, 'NEW%d' % i) for i in range(300)]
        existing_rows = [
            _existing(1000 + i, i, 'OLD%d' % i, 'synced') for i in range(300)
        ]

        with pytest.raises(app_module._JobAborted):
            _run(app_module, new_rows, existing_rows, abort_cb=lambda: True)

    def test_no_hooks_is_noop(self, app_module):
        """不传钩子时行为与旧调用点完全一致（4 个现有调用点都走这条路）"""
        new_rows, existing_rows = _mixed_fixture()
        result, _cur, _ev = _run(app_module, new_rows, existing_rows)
        assert result == _legacy_result(new_rows, existing_rows)


# ---- 辅助函数 ----

class TestHelpers:

    def test_chunked(self, app_module):
        assert list(app_module._chunked([1, 2, 3, 4, 5], 2)) == [[1, 2], [3, 4], [5]]
        assert list(app_module._chunked([], 2)) == []
        assert list(app_module._chunked([1, 2], 0)) == [[1, 2]]
        assert list(app_module._chunked([1, 2], -1)) == [[1, 2]]

    def test_dedupe_by_key_keeps_first(self, app_module):
        rows = [_src(1, 'first'), _src(1, 'second'), _src(2, 'other')]
        out = app_module._dedupe_by_key(rows, UNIQUE_KEYS)
        assert len(out) == 2
        assert out[0]['name'] == 'first'

    def test_dedupe_distinguishes_keys(self, app_module):
        rows = [_src(1, 'a', host='10.0.0.1'), _src(1, 'b', host='10.0.0.2')]
        assert len(app_module._dedupe_by_key(rows, UNIQUE_KEYS)) == 2

    def test_emit_swallows_callback_errors(self, app_module):
        """进度回调抛异常绝不能拖垮事务"""
        def boom(phase, done, total):
            raise RuntimeError('回调炸了')
        app_module._emit(boom, 'insert', 1, 10)  # 不应抛出

    def test_check_abort_noop_without_callback(self, app_module):
        app_module._check_abort(None)  # 不应抛出

    def test_check_abort_raises_when_true(self, app_module):
        with pytest.raises(app_module._JobAborted):
            app_module._check_abort(lambda: True)