# -*- coding: utf-8 -*-
"""初始化后台任务的压测与幂等回归（S7）。

**默认不跑。** 需要一个一次性的 PostgreSQL 实例，通过环境变量显式指定：

    ZAC_PERF_ALLOW=yes \
    ZAC_PERF_DSN='postgresql://postgres:pw@127.0.0.1:55432/ops' \
    python3 -m pytest tests/test_init_perf.py -q

两道门禁（见 `_perf_dsn`）：`ZAC_PERF_ALLOW` 必须显式为 yes（防"顺手带上 DSN 就跑"），
且 DSN 指向的库不得与 config.yaml 配置的库相同（防误打生产库）。

**不要并入默认全量跑**：本模块会重建 `app` 模块（要替换 DB_* 环境变量），且会真起
后台线程、真写库。单独执行即可。

安全约束（计划 Non-Goal）：
- 不得对生产库执行 —— 由 `_perf_dsn` 的双门禁挡住；
- `finally` 清理失败必须**显式报错**，不得静默通过。
"""
import os
import sys
import time
from urllib.parse import urlparse

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SEED_PREFIX = '10.99.'
TEMPLATE = '21001'
PERF_SYSTEM = '压测系统'
N_HOSTS = 2000
N_ITEMS = 5             # 模板内监控项数 → 期望 N_HOSTS × N_ITEMS 行
ROWS_PER_ASSET = 4      # 每个 webscenario_items 行的 4 个 URL 各产 1 条 review 记录
N_WEB_ASSETS = 8000     # 让重建耗时足够长，中止信号必然落在任务中途


# ---------------------------------------------------------------- 门禁

def _perf_dsn():
    """解析并校验 DSN。缺省/未放行一律 skip；DSN 非法则 fail。"""
    dsn = os.environ.get('ZAC_PERF_DSN', '').strip()
    if not dsn:
        pytest.skip('未设置 ZAC_PERF_DSN（压测需要一个一次性 PostgreSQL）')
    if os.environ.get('ZAC_PERF_ALLOW', '').strip().lower() != 'yes':
        pytest.skip('未显式设置 ZAC_PERF_ALLOW=yes（压测会真写库，需显式放行）')

    p = urlparse(dsn)
    if p.scheme not in ('postgres', 'postgresql') or not p.hostname:
        pytest.fail(f'ZAC_PERF_DSN 不是合法的 postgresql:// URL（scheme={p.scheme!r}）')

    return {
        'host': p.hostname, 'port': p.port or 5432,
        'dbname': (p.path or '/').lstrip('/'),
        'user': p.username, 'password': p.password or '',
    }


def _configured_db():
    """config.yaml 里配置的库（**排除** DB_* 环境变量）。

    必须排除：否则若操作者为了跑压测把 DB_* 导出到 shell，这里读到的就是压测库本身，
    门禁会把自己判成"生产库"而误报。
    """
    import config_loader
    keys = ('DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD')
    saved = {k: os.environ.pop(k, None) for k in keys}
    try:
        return config_loader.load_config().get('database', {}) or {}
    finally:
        for k, v in saved.items():
            if v is not None:
                os.environ[k] = v


def _assert_not_the_configured_db(target):
    """DSN 不得指向 config.yaml 里配置的那个库 —— 那可能是生产库。

    这里是 **fail 而非 skip**：操作者既然显式要求压测，就该被告知目标库选错了。
    """
    cfg = _configured_db()
    same = (str(cfg.get('host')) == str(target['host'])
            and str(cfg.get('port', 5432)) == str(target['port'])
            and str(cfg.get('name')) == str(target['dbname']))
    if same:
        pytest.fail(
            f"拒绝执行：ZAC_PERF_DSN 指向的库与 config.yaml 配置的库相同 "
            f"（{target['host']}:{target['port']}/{target['dbname']}）。"
            f"压测会 TRUNCATE 整表，必须用一次性实例。")
    if target['dbname'] in ('', 'postgres', 'template0', 'template1'):
        pytest.fail(f"拒绝执行：ZAC_PERF_DSN 指向系统库 {target['dbname']!r}")


def _schema():
    """业务表所在的 schema。app 的连接由 config_loader 带上 search_path，
    本模块自建的 psycopg2 连接必须自己带上同样的设置，否则所有表都"不存在"。"""
    return (_configured_db().get('schema') or 'zabbix_mac')


# ---------------------------------------------------------------- 造数 / 清理

def _rows(conn, sql, params=None):
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def _scalar(conn, sql, params=None):
    return _rows(conn, sql, params)[0][0]


def _reset_items_review(conn):
    """清空本轮的 items_review 行，让下一次初始化是一次**全量新增**。

    为什么需要：`_diff_and_merge` 只在真的有 insert/update/delete 时才 `_emit`
    进度（`_emit` 写在 `if inserts:` 等分支内部），所以"全 unchanged"的复跑
    整场不产生任何行级进度。测试若依赖上一次残留的状态，就会时而看得到进度、
    时而看不到 —— 每个用例自己把起点摆正。
    """
    with conn.cursor() as cur:
        cur.execute(f"DELETE FROM items_review WHERE host_ip LIKE '{SEED_PREFIX}%'")


def _purge(conn):
    """删除本轮造出的全部数据及遗留。"""
    with conn.cursor() as cur:
        cur.execute(f"DELETE FROM items_review WHERE host_ip LIKE '{SEED_PREFIX}%'")
        cur.execute(f"DELETE FROM webscenario_items_review WHERE system = '{PERF_SYSTEM}'")
        cur.execute(f"DELETE FROM webscenario_items WHERE system = '{PERF_SYSTEM}'")
        cur.execute(f"DELETE FROM items WHERE template_name = '{TEMPLATE}'")
        cur.execute(f"DELETE FROM hosts WHERE name LIKE '{SEED_PREFIX}%'")


def _seed(conn):
    """造数。先清残留（上一轮跑崩留下的），再插入。"""
    _purge(conn)
    with conn.cursor() as cur:
        # 1) 目标主机（items_review init 的 CROSS JOIN 右侧）
        cur.execute(f"""
            INSERT INTO hosts (name, description, system, subsystem, template_id, in_room)
            SELECT '{SEED_PREFIX}' || g, 'perf', '{PERF_SYSTEM}', '压测模块', '{TEMPLATE}', '压测机房'
            FROM generate_series(1, {N_HOSTS}) g
        """)
        # 2) 模板监控项（items_review.item_id 有外键，必须先有 items）
        cur.execute(f"""
            INSERT INTO items (item_key, name, type, value_type, delay, template_name)
            SELECT 'perf.key.' || g, '压测监控项 ' || g, 0, 3, '1m', '{TEMPLATE}'
            FROM generate_series(1, {N_ITEMS}) g
        """)
        # 3) web 场景源数据（每行产出 4 条 review 记录）
        cur.execute(f"""
            INSERT INTO webscenario_items
                (system, subsystem, nginx_clb, nginx, clb, pod,
                 webtest_api, webtest_nginx_api, in_room)
            SELECT '{PERF_SYSTEM}', 'perf_' || g,
                   'http://clb/' || g, 'http://nginx/' || g,
                   'http://clb-direct/' || g, 'http://pod/' || g,
                   'http://api/' || g, 'http://nginx-api/' || g, '压测机房'
            FROM generate_series(1, {N_WEB_ASSETS}) g
        """)


def _cleanup(conn):
    """`finally` 清理。**失败必须显式报错** —— 静默通过会把脏数据留给下一次运行，
    让"行数对不上"这类断言以最难排查的方式失败。"""
    try:
        conn.rollback()
    except Exception:
        pass
    try:
        _purge(conn)
    except Exception as exc:
        raise AssertionError(
            f'压测数据清理失败，压测库已被污染，请手工清理后再跑：{exc}') from exc

    # 验证清理确实生效 —— 上面那个 try 只证明"没抛异常"
    leftovers = {
        'items_review': _scalar(conn, f"SELECT count(*) FROM items_review WHERE host_ip LIKE '{SEED_PREFIX}%'"),
        'hosts': _scalar(conn, f"SELECT count(*) FROM hosts WHERE name LIKE '{SEED_PREFIX}%'"),
        'items': _scalar(conn, f"SELECT count(*) FROM items WHERE template_name = '{TEMPLATE}'"),
        'webscenario_items': _scalar(conn, f"SELECT count(*) FROM webscenario_items WHERE system = '{PERF_SYSTEM}'"),
        'webscenario_items_review': _scalar(conn, f"SELECT count(*) FROM webscenario_items_review WHERE system = '{PERF_SYSTEM}'"),
    }
    dirty = {k: v for k, v in leftovers.items() if v}
    if dirty:
        raise AssertionError(f'压测数据清理不完整，仍有残留：{dirty}')


# ---------------------------------------------------------------- fixtures

@pytest.fixture(scope='module')
def perf_state():
    """连接压测库 + 造数，模块级只做一次；`finally` 强制清理。"""
    import psycopg2

    target = _perf_dsn()
    _assert_not_the_configured_db(target)
    if target['dbname'] in ('', 'postgres', 'template0', 'template1'):
        pytest.fail(f"拒绝执行：ZAC_PERF_DSN 指向系统库 {target['dbname']!r}")

    conn = psycopg2.connect(options=f'-c search_path={_schema()}', **target)
    conn.set_client_encoding('utf8')
    conn.autocommit = True
    try:
        _seed(conn)
        yield {'dsn': target, 'conn': conn}
    finally:
        try:
            _cleanup(conn)
        finally:
            conn.close()


@pytest.fixture(scope='module')
def perf_app(perf_state):
    """把 app 重新绑定到压测库上。

    必须在**导入 app 之前**写好 DB_* 环境变量（config_loader 在导入期读它们），
    并清掉 sys.modules 里可能已被其它测试模块导入过的 app。
    """
    keys = ('DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD')
    saved = {k: os.environ.get(k) for k in keys}
    dsn = perf_state['dsn']
    os.environ.update({
        'DB_HOST': dsn['host'], 'DB_PORT': str(dsn['port']), 'DB_NAME': dsn['dbname'],
        'DB_USER': dsn['user'], 'DB_PASSWORD': dsn['password'],
    })
    os.environ.setdefault('APP_SECRET_KEY', 'perf-test-secret-key')

    sys.modules.pop('app', None)
    import app as app_module
    app_module.app.config['TESTING'] = True
    app_module.app.before_request_funcs[None] = []   # 绕过 CSRF

    yield app_module

    for k, v in saved.items():                       # 还原，免得影响同进程后续模块
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    sys.modules.pop('app', None)


@pytest.fixture
def client(perf_app):
    return perf_app.app.test_client()


@pytest.fixture
def conn(perf_state):
    return perf_state['conn']


# ---------------------------------------------------------------- 工具

def _wait_settled(client, timeout=180):
    """轮询到任务结束，返回 (终态进度, 观察到的 percent 序列)。"""
    deadline = time.time() + timeout
    seen, last = [], None
    while time.time() < deadline:
        last = client.get('/review/sync-progress').get_json()
        if last.get('percent') is not None:
            seen.append(last['percent'])
        if not last.get('running'):
            return last, seen
        time.sleep(0.05)
    raise AssertionError(f'任务在 {timeout}s 内没结束，最后进度：{last}')


# ---------------------------------------------------------------- 用例

class TestInitPerf:
    """2000 台主机下，初始化接口的响应时间、进度与数据一致性"""

    def test_init_returns_202_within_500ms(self, client, conn):
        """① 接口在 500ms 内返回 202 —— HTTP 请求里不再跑初始化"""
        _reset_items_review(conn)
        t0 = time.monotonic()
        resp = client.post('/items-review/initialize', json={})
        elapsed = time.monotonic() - t0

        assert resp.status_code == 202, f'期望 202（异步受理），实际 {resp.status_code}'
        body = resp.get_json()
        assert body['success'] is True and body['async'] is True
        assert elapsed < 0.5, (
            f'接口耗时 {elapsed * 1000:.0f}ms ≥ 500ms —— 又退回同步执行了？'
            f'（这正是本次改造要消灭的 504 成因）')

        # 仅供参考的对照数据：请求耗时应远小于任务本身的耗时。
        # 二者若同量级，说明工作其实还是跑在请求线程里。
        _wait_settled(client)
        job_elapsed = time.monotonic() - t0
        print(f'\n[perf] {N_HOSTS} 台主机 × {N_ITEMS} 监控项 = {N_HOSTS * N_ITEMS} 行：'
              f'接口 {elapsed * 1000:.1f}ms（<500ms 硬断言）／ 任务全量 {job_elapsed:.2f}s')

    def test_progress_climbs_to_100(self, client, conn):
        """② 进度从 0% 单调增长到 100%，最终 success"""
        _reset_items_review(conn)
        client.post('/items-review/initialize', json={})
        final, seen = _wait_settled(client)

        assert seen, '整个任务期间没有观察到任何行级进度（rows_total 始终为 0）'
        assert seen == sorted(seen), f'进度出现回退：{seen}'
        assert final['percent'] == 100, f"终态 percent={final['percent']}"
        assert final['success'] is True, final.get('message')
        assert final['unit'] == '条'
        assert final['rows_total'] == N_HOSTS * N_ITEMS

    def test_row_count_matches_expected(self, client, conn):
        """③ 落库行数与期望完全一致"""
        _reset_items_review(conn)
        client.post('/items-review/initialize', json={})
        _wait_settled(client)

        got = _scalar(conn, f"SELECT count(*) FROM items_review WHERE host_ip LIKE '{SEED_PREFIX}%'")
        assert got == N_HOSTS * N_ITEMS, f'期望 {N_HOSTS * N_ITEMS} 行，实际 {got}'

    def test_second_init_is_idempotent(self, client, conn):
        """④ 幂等复跑：行数不增，且全部落在 unchanged"""
        _reset_items_review(conn)
        client.post('/items-review/initialize', json={})
        _wait_settled(client)
        before = _scalar(conn, f"SELECT count(*) FROM items_review WHERE host_ip LIKE '{SEED_PREFIX}%'")

        client.post('/items-review/initialize', json={})
        final, _ = _wait_settled(client)

        after = _scalar(conn, f"SELECT count(*) FROM items_review WHERE host_ip LIKE '{SEED_PREFIX}%'")
        assert after == before, f'二次初始化产生了重复行：{before} → {after}'
        assert '新增 0 条' in final['message'], final['message']
        assert '删除 0 条' in final['message'], final['message']

    def test_abort_leaves_data_unchanged(self, client, conn):
        """⑤ 中止：TRUNCATE + INSERT 整体回滚，行数与序列均回到原值

        webscenarios 的初始化是"清表重建"，事务性回滚在这里才真正被考验 ——
        任务体若中途 commit，表会被留在残缺状态。
        """
        # 先跑完一轮，得到稳定的基线
        client.post('/webscenarios-review/initialize', json={})
        final, _ = _wait_settled(client)
        assert final['success'] is True, final.get('message')
        baseline = _scalar(conn, "SELECT count(*) FROM webscenario_items_review")
        seq_before = _scalar(conn, "SELECT last_value FROM webscenario_items_review_id_seq")
        assert baseline == N_WEB_ASSETS * ROWS_PER_ASSET, f'基线行数异常：{baseline}'

        # 再跑一轮，并在任务运行期间持续发中止信号
        resp = client.post('/webscenarios-review/initialize', json={})
        assert resp.status_code == 202
        final, aborted_seen = None, False
        deadline = time.time() + 180
        while time.time() < deadline:
            client.post('/review/sync-abort')
            final = client.get('/review/sync-progress').get_json()
            if not final.get('running'):
                aborted_seen = final.get('aborted') is True
                break
            time.sleep(0.02)

        assert final and final.get('running') is False, f'中止后任务仍在运行：{final}'
        assert aborted_seen, (
            f'任务在收到中止信号前就跑完了（源数据 {N_WEB_ASSETS} 行的窗口太窄）——'
            f'本次未覆盖中止路径，请调大 N_WEB_ASSETS 后重跑。终态：{final}')

        after = _scalar(conn, "SELECT count(*) FROM webscenario_items_review")
        seq_after = _scalar(conn, "SELECT last_value FROM webscenario_items_review_id_seq")
        assert after == baseline, f'中止后行数被改动：{baseline} → {after}（TRUNCATE 未回滚）'
        assert seq_after == seq_before, f'中止后序列被推进：{seq_before} → {seq_after}'