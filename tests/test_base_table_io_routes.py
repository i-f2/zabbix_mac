# -*- coding: utf-8 -*-
"""
基础表/复核表 Excel 导出-导入路由回归测试

覆盖: 13 个导出路由（BytesIO 流式形态 9 个 + DictCursor 临时文件形态 4 个，
含空表分支与异常 500 分支）、13 个导入路由（未选文件/空文件名 400、
DELETE+INSERT 契约、NaN→None、类 JSON 字符串列转义、非法列名 500+回滚）、
_sanitize_import_columns 与「导出↔导入」往返幂等 —— 导出文件（SELECT *）
必含 id 主键列，导入侧必须静默剔除方可往返可用。
"""
import io
import os
import sys
import pytest
import pandas as pd
from unittest.mock import patch

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


class FakeCursor:
    """可编程假游标：SELECT 行可配（tuple 或 dict），记录 execute/executemany。"""

    def __init__(self, rows=None, cols=None, rowcount=0, fail=False):
        self._rows = rows or []
        self.description = tuple((c,) + (None,) * 6 for c in (cols or []))
        self.rowcount = rowcount
        self._fail = fail
        self.executes = []
        self.executemany_calls = []

    def execute(self, sql, params=None):
        self.executes.append((sql, params))
        if self._fail:
            raise RuntimeError('boom')

    def fetchall(self):
        return self._rows

    def executemany(self, sql, seq):
        self.executemany_calls.append((sql, [tuple(v) for v in seq]))

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


def _xlsx(cols, rows):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as w:
        pd.DataFrame(rows, columns=cols).to_excel(w, index=False)
    buf.seek(0)
    return buf


def _post_file(client, url, file_tuple):
    return client.post(url, data={'file': file_tuple},
                       content_type='multipart/form-data')


# 13 组 (导入 URL, 表名) —— 与 app._ALLOWED_IMPORT_COLUMNS 键一一对应
IO_TABLES = [
    ('/items', 'items'),
    ('/triggers', 'triggers'),
    ('/item-prototypes', 'item_prototypes'),
    ('/trigger-prototypes', 'trigger_prototypes'),
    ('/discovery-rules', 'discovery_rules'),
    ('/filter-conditions', 'filter_conditions'),
    ('/webscenarios', 'webscenario_items'),
    ('/items-review', 'items_review'),
    ('/triggers-review', 'triggers_review'),
    ('/item-prototypes-review', 'item_prototypes_review'),
    ('/trigger-prototypes-review', 'trigger_prototypes_review'),
    ('/webscenarios-review', 'webscenario_items_review'),
    ('/web-triggers-review', 'web_trigger_review'),
]

# 9 个 BytesIO 流式导出（空表仍 200）：7 主表 + webscenarios-review + web-triggers-review
STREAM_EXPORTS = [u + '/export' for u, t in IO_TABLES
                  if u not in ('/items-review', '/triggers-review',
                               '/item-prototypes-review', '/trigger-prototypes-review')]
# 4 个 DictCursor 临时文件导出（空表 400）
DICT_EXPORTS = ['/items-review/export', '/triggers-review/export',
                '/item-prototypes-review/export', '/trigger-prototypes-review/export']


class TestStreamExports:
    @pytest.mark.parametrize('url', STREAM_EXPORTS)
    def test_export_ok(self, app_module, client, url):
        cur = FakeCursor(rows=[(1, 'a')], cols=['id', 'name'])
        conn = FakeConn(cur)
        with patch.object(app_module, 'get_db_connection', return_value=conn):
            resp = client.get(url)
        assert resp.status_code == 200
        assert 'spreadsheet' in (resp.content_type or '')
        assert 'attachment' in resp.headers.get('Content-Disposition', '')
        assert len(resp.data) > 0
        assert conn.closed

    def test_empty_rows_still_200(self, app_module, client):
        conn = FakeConn(FakeCursor(rows=[], cols=['id']))
        with patch.object(app_module, 'get_db_connection', return_value=conn):
            resp = client.get('/items/export')
        assert resp.status_code == 200

    def test_db_error_returns_500_json(self, app_module, client):
        conn = FakeConn(FakeCursor(fail=True))
        with patch.object(app_module, 'get_db_connection', return_value=conn):
            resp = client.get('/items/export')
        assert resp.status_code == 500
        data = resp.get_json()
        assert data['success'] is False and '导出失败' in data['message']


class TestDictCursorExports:
    @pytest.mark.parametrize('url', DICT_EXPORTS)
    def test_export_ok(self, app_module, client, url):
        cur = FakeCursor(rows=[{'id': 1, 'name': 'x', 'expression': 'e'}])
        conn = FakeConn(cur)
        with patch.object(app_module, 'get_db_connection', return_value=conn):
            resp = client.get(url)
        assert resp.status_code == 200
        assert 'spreadsheet' in (resp.content_type or '')

    @pytest.mark.parametrize('url', DICT_EXPORTS)
    def test_empty_returns_400(self, app_module, client, url):
        conn = FakeConn(FakeCursor(rows=[]))
        with patch.object(app_module, 'get_db_connection', return_value=conn):
            resp = client.get(url)
        assert resp.status_code == 400
        assert resp.get_json()['success'] is False


class TestImportParamValidation:
    @pytest.mark.parametrize('url,table', IO_TABLES)
    def test_missing_file_and_blank_name(self, client, url, table):
        resp = client.post(url + '/import')
        assert resp.status_code == 400
        assert '未选择文件' in resp.get_json()['message']
        resp = _post_file(client, url + '/import', (io.BytesIO(b''), ''))
        assert resp.status_code == 400
        assert '文件名为空' in resp.get_json()['message']


class TestImportSuccess:
    @pytest.mark.parametrize('url,table', IO_TABLES)
    def test_delete_then_insert_contract(self, app_module, client, url, table):
        cols = sorted(app_module._ALLOWED_IMPORT_COLUMNS[table])
        rows = [['v'] * len(cols) for _ in range(2)]
        conn = FakeConn(FakeCursor(rowcount=7))
        with patch.object(app_module, 'get_db_connection', return_value=conn):
            resp = _post_file(client, url + '/import', (_xlsx(cols, rows), 'd.xlsx'))
        assert resp.status_code == 200, resp.get_json()
        data = resp.get_json()
        assert data['success'] is True
        assert '删除 7 条，导入 2 条' in data['message']
        assert conn.committed and not conn.rolled_back and conn.closed
        cur = conn._cursor
        assert len(cur.calls('DELETE FROM ' + table)) == 1
        ins = cur.executemany_calls
        assert len(ins) == 1 and ins[0][0].startswith('INSERT INTO ' + table + ' (')
        assert len(ins[0][1]) == 2

    def test_nan_becomes_none(self, app_module, client):
        cols = ['item_key', 'name', 'template_name']
        rows = [['k1', None, 'T']]
        conn = FakeConn(FakeCursor())
        with patch.object(app_module, 'get_db_connection', return_value=conn):
            resp = _post_file(client, '/items/import', (_xlsx(cols, rows), 'd.xlsx'))
        assert resp.status_code == 200
        params = conn._cursor.executemany_calls[0][1]
        assert params[0][1] is None  # name 列 NaN → None

    def test_python_literal_string_jsonified(self, app_module, client):
        cols = ['item_key', 'description']
        rows = [['k1', "[{'type': '5', 'params': '0.1'}]"]]
        conn = FakeConn(FakeCursor())
        with patch.object(app_module, 'get_db_connection', return_value=conn):
            resp = _post_file(client, '/items/import', (_xlsx(cols, rows), 'd.xlsx'))
        assert resp.status_code == 200
        val = conn._cursor.executemany_calls[0][1][0][1]
        assert val == '[{"type": "5", "params": "0.1"}]'  # ast.literal_eval → json.dumps


class TestImportRejections:
    @pytest.mark.parametrize('url,table', IO_TABLES)
    def test_illegal_column_500_rollback_no_insert(self, app_module, client, url, table):
        cols = ['definitely_not_a_column']
        conn = FakeConn(FakeCursor())
        with patch.object(app_module, 'get_db_connection', return_value=conn):
            resp = _post_file(client, url + '/import', (_xlsx(cols, [['x']]), 'd.xlsx'))
        assert resp.status_code == 500
        assert '非法列名' in resp.get_json()['message']
        assert conn.rolled_back and not conn.committed
        assert conn._cursor.executemany_calls == []


class TestIdRoundTrip:
    """导出（SELECT *，必含 id）→ 导入 往返：id 主键列须被静默剔除，
    由序列重新生成。此前 _sanitize_import_columns 直接对 id 报「非法列名」，
    导出文件原样回导必然 500 —— 往返断裂缺陷的回归钉。"""

    @pytest.mark.parametrize('url,table', IO_TABLES)
    def test_export_file_with_id_imports_ok(self, app_module, client, url, table):
        cols = ['id'] + sorted(app_module._ALLOWED_IMPORT_COLUMNS[table])
        rows = [[i + 1] + ['v'] * (len(cols) - 1) for i in range(2)]
        conn = FakeConn(FakeCursor(rowcount=2))
        with patch.object(app_module, 'get_db_connection', return_value=conn):
            resp = _post_file(client, url + '/import', (_xlsx(cols, rows), 'd.xlsx'))
        assert resp.status_code == 200, resp.get_json()
        col_list = conn._cursor.executemany_calls[0][0].split('(', 1)[1].split(')')[0]
        inserted_cols = [c.strip() for c in col_list.split(',')]
        assert 'id' not in inserted_cols
        assert not conn.rolled_back

    def test_sanitize_strips_id_keeps_others(self, app_module):
        out = app_module._sanitize_import_columns(
            'items', ['id', 'item_key', 'name'])
        assert out == ['item_key', 'name']

    def test_sanitize_id_only_rejected(self, app_module):
        with pytest.raises(ValueError) as e:
            app_module._sanitize_import_columns('items', ['id'])
        assert '无有效导入列' in str(e.value)

    def test_sanitize_still_rejects_unknown(self, app_module):
        with pytest.raises(ValueError) as e:
            app_module._sanitize_import_columns('items', ['id', 'evil; DROP'])
        assert '非法列名' in str(e.value)
