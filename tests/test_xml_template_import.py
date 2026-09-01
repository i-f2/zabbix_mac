# -*- coding: utf-8 -*-
"""
Zabbix 模板 XML 导入测试

覆盖: xml_template_parser 解析（6 组件 + 类型映射）、app._upsert 幂等分支、
parse-preview / execute-import 两个 API 路由。
"""
import io
import os
import re
import sys
import pytest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from xml_template_parser import (parse_template_xml, _duration_to_days,
                                 ITEM_TYPE_MAP, VALUE_TYPE_MAP, PRIORITY_MAP)

SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<zabbix_export>
    <version>5.0</version>
    <templates>
        <template>
            <template>21001</template>
            <name>21001</name>
            <description>Standard Linux monitoring template</description>
            <groups><group><name>Templates</name></group></groups>
            <items>
                <item>
                    <name>CPU utilization</name>
                    <type>ZABBIX_PASSIVE</type>
                    <key>system.cpu.util[,iowait]</key>
                    <delay>30s</delay>
                    <history>7d</history>
                    <trends>365d</trends>
                    <value_type>FLOAT</value_type>
                    <units>%</units>
                    <description>CPU iowait</description>
                    <preprocessing>
                        <step><type>MULTIPLIER</type><params>0.1</params></step>
                    </preprocessing>
                </item>
                <item>
                    <name>Free disk space on /</name>
                    <type>DEPENDENT</type>
                    <key>vfs.fs.size[/,free]</key>
                    <delay>1m</delay>
                    <history>7d</history>
                    <trends>365d</trends>
                    <value_type>UNSIGNED</value_type>
                    <units>B</units>
                    <master_item><key>vfs.fs.discovery</key></master_item>
                </item>
            </items>
            <triggers>
                <trigger>
                    <expression>last(/21001/system.cpu.util[,iowait])&gt;90</expression>
                    <name>High CPU iowait</name>
                    <priority>HIGH</priority>
                    <description>CPU iowait high</description>
                    <status>ENABLED</status>
                </trigger>
            </triggers>
            <discovery_rules>
                <discovery_rule>
                    <name>Filesystem discovery</name>
                    <type>ZABBIX_PASSIVE</type>
                    <key>vfs.fs.discovery</key>
                    <delay>1h</delay>
                    <filter>
                        <evaltype>AND_OR</evaltype>
                        <conditions>
                            <condition>
                                <macro>{#FSTYPE}</macro>
                                <value>^(ext4|xfs)$</value>
                                <operator>MATCHES_REGEX</operator>
                                <formulaid>A</formulaid>
                            </condition>
                            <condition>
                                <macro>{#FSNAME}</macro>
                                <value>^(/dev|/sys)</value>
                                <operator>NOT_MATCHES_REGEX</operator>
                                <formulaid>B</formulaid>
                            </condition>
                        </conditions>
                    </filter>
                    <item_prototypes>
                        <item_prototype>
                            <name>Used space on $1</name>
                            <type>ZABBIX_PASSIVE</type>
                            <key>vfs.fs.size[{#FSNAME},used]</key>
                            <delay>1m</delay>
                            <history>7d</history>
                            <trends>365d</trends>
                            <value_type>UNSIGNED</value_type>
                            <units>B</units>
                        </item_prototype>
                    </item_prototypes>
                    <trigger_prototypes>
                        <trigger_prototype>
                            <expression>last(/21001/vfs.fs.size[{#FSNAME},pfree])&lt;10</expression>
                            <name>Disk free less than 10%</name>
                            <priority>WARNING</priority>
                            <status>ENABLED</status>
                        </trigger_prototype>
                    </trigger_prototypes>
                </discovery_rule>
            </discovery_rules>
        </template>
    </templates>
</zabbix_export>
"""


# ---- Parser 单元测试 ----

class TestParseTemplateXml:
    def test_parse_basics(self):
        templates = parse_template_xml(SAMPLE_XML)
        assert len(templates) == 1
        tpl = templates[0]
        assert tpl['name'] == '21001'
        assert tpl['description'] == 'Standard Linux monitoring template'
        assert len(tpl['items']) == 2
        assert len(tpl['triggers']) == 1
        assert len(tpl['discovery_rules']) == 1

    def test_parse_items(self):
        tpl = parse_template_xml(SAMPLE_XML)[0]
        it1 = tpl['items'][0]
        assert it1['item_key'] == 'system.cpu.util[,iowait]'
        assert it1['type'] == ITEM_TYPE_MAP['ZABBIX_PASSIVE'] == 0
        assert it1['value_type'] == VALUE_TYPE_MAP['FLOAT'] == 0
        assert it1['delay'] == '30s'
        assert it1['history'] == 7
        assert it1['trends'] == 365
        assert it1['units'] == '%'
        assert it1['template_name'] == '21001'
        assert it1['preprocessing'] == '[{"type": "5", "params": "0.1", "error_handler": "0", "error_handler_params": ""}]'

        it2 = tpl['items'][1]
        assert it2['type'] == ITEM_TYPE_MAP['DEPENDENT'] == 18
        assert it2['value_type'] == VALUE_TYPE_MAP['UNSIGNED'] == 3
        assert it2['master_item'] == 'vfs.fs.discovery'
        assert 'preprocessing' not in it2

    def test_parse_triggers(self):
        tpl = parse_template_xml(SAMPLE_XML)[0]
        trig = tpl['triggers'][0]
        assert trig['name'] == 'High CPU iowait'
        assert trig['priority'] == PRIORITY_MAP['HIGH'] == 4
        assert trig['status'] == 0
        assert trig['template_name'] == '21001'
        assert 'last(/21001/system.cpu.util[,iowait])>90' in trig['expression']

    def test_parse_discovery_rule(self):
        tpl = parse_template_xml(SAMPLE_XML)[0]
        dr = tpl['discovery_rules'][0]
        assert dr['rule']['name'] == 'Filesystem discovery'
        assert dr['rule']['key'] == 'vfs.fs.discovery'
        assert dr['rule']['delay'] == '1h'
        assert dr['rule']['evaltype'] == 0  # AND_OR
        assert dr['rule']['template_name'] == '21001'
        assert len(dr['conditions']) == 2
        assert dr['conditions'][0] == {'macro': '{#FSTYPE}', 'value': '^(ext4|xfs)$',
                                       'operator': 'MATCHES_REGEX'}
        assert dr['conditions'][1]['operator'] == 'NOT_MATCHES_REGEX'
        assert len(dr['item_prototypes']) == 1
        ip = dr['item_prototypes'][0]
        assert ip['key'] == 'vfs.fs.size[{#FSNAME},used]'
        assert ip['value_type'] == 3
        assert len(dr['trigger_prototypes']) == 1
        tp = dr['trigger_prototypes'][0]
        assert tp['description'] == 'Disk free less than 10%'  # live 表用 description 存名称
        assert tp['priority'] == 2  # WARNING

    def test_invalid_xml(self):
        with pytest.raises(ValueError):
            parse_template_xml('<not-xml>')

    def test_wrong_root(self):
        with pytest.raises(ValueError):
            parse_template_xml('<zabbix_export><templates><template><name>t</name></template></templates></zabbix_export>'
                               .replace('zabbix_export', 'other_export'))

    def test_no_templates(self):
        with pytest.raises(ValueError):
            parse_template_xml('<zabbix_export><templates></templates></zabbix_export>')

    def test_missing_template_name(self):
        with pytest.raises(ValueError):
            parse_template_xml('<zabbix_export><templates><template><items/></template></templates></zabbix_export>')

    def test_template_id_defaults_to_xml_name(self):
        """未传 template_id → 模板标识取 XML <template>/<name>（向后兼容）。"""
        tpl = parse_template_xml(SAMPLE_XML)[0]
        assert tpl['template_id'] == '21001'

    def test_template_id_forces_binding(self):
        """用户输入的 template_id 强制覆盖 XML 模板名，绑定到所有记录。"""
        templates = parse_template_xml(SAMPLE_XML, template_id='91001')
        tpl = templates[0]
        assert tpl['template_id'] == '91001'
        assert tpl['name'] == '91001'
        for item in tpl['items']:
            assert item['template_name'] == '91001'
        for trig in tpl['triggers']:
            assert trig['template_name'] == '91001'
        for dr in tpl['discovery_rules']:
            assert dr['rule']['template_name'] == '91001'
            assert dr['conditions']  # 过滤器嵌套在发现规则下
            assert dr['item_prototypes']
            assert dr['trigger_prototypes']

    def test_root_and_item_nested_sections(self):
        """Zabbix 5.0 导出把简单触发器内嵌在 <item>/<triggers> 下、引用关联模板条目的
        触发器放在根级 <triggers>、触发器原型内嵌在 <item_prototype>/<trigger_prototypes>
        下——这些都应被归集到所属模板，且同样绑定用户 template_id。"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<zabbix_export><version>5.0</version>
<templates><template><template>T1</template><name>T1</name><items>
<item><name>cpu</name><key>system.cpu.util</key><type>ZABBIX_PASSIVE</type><delay>1m</delay>
<triggers><trigger><expression>{last()}&gt;90</expression><name>CPU high</name><priority>WARNING</priority></trigger></triggers>
</item></items></template></templates>
<triggers>
<trigger><expression>{T1:system.cpu.util.last()}&gt;95</expression><name>CPU very high</name><priority>HIGH</priority></trigger>
</triggers>
<discovery_rules><discovery_rule><name>DR</name><key>vfs.fs.discovery</key><delay>1h</delay>
<item_prototypes><item_prototype><name>ip</name><key>vfs.fs.size[{$1}]</key><value_type>UNSIGNED</value_type>
<trigger_prototypes><trigger_prototype><expression>last(/T1/vfs.fs.size[{$1}])&lt;10</expression><name>low</name><priority>AVERAGE</priority></trigger_prototype></trigger_prototypes>
</item_prototype></item_prototypes>
</discovery_rule></discovery_rules>
</zabbix_export>
"""
        tpl = parse_template_xml(xml, template_id='91001')[0]
        assert len(tpl['items']) == 1
        assert len(tpl['triggers']) == 2  # item 内嵌 + 根级
        assert all(t['template_name'] == '91001' for t in tpl['triggers'])
        assert len(tpl['discovery_rules']) == 1
        dr = tpl['discovery_rules'][0]
        assert len(dr['trigger_prototypes']) == 1  # item_prototype 内嵌
        assert dr['rule']['template_name'] == '91001'


class TestDurationToDays:
    def test_days(self):
        assert _duration_to_days('7d') == 7
        assert _duration_to_days('365d') == 365

    def test_other_units(self):
        assert _duration_to_days('1w') == 7
        assert _duration_to_days('1M') == 30  # 月
        assert _duration_to_days('1y') == 365
        assert _duration_to_days('12h') == 1  # 四舍五入

    def test_empty(self):
        assert _duration_to_days('') is None
        assert _duration_to_days(None) is None
        assert _duration_to_days('abc') is None


# ---- _upsert 幂等分支测试 ----

class FakeCursor:
    """可编程假游标：SELECT 返回注入队列，INSERT...RETURNING 自增 id。"""

    def __init__(self, fetch_queue=None):
        self.executes = []
        self.next_id = 1
        self._fetch_queue = list(fetch_queue) if fetch_queue else []
        self._sql = ''

    def execute(self, sql, params=None):
        self.executes.append((sql, params))
        self._sql = sql

    def fetchone(self):
        if 'RETURNING id' in self._sql:
            row = {'id': self.next_id}
            self.next_id += 1
            return row
        if self._fetch_queue:
            return self._fetch_queue.pop(0)
        return None

    def fetchall(self):
        return []

    def calls(self, marker):
        return [c for c in self.executes if c[0] and marker in c[0]]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class FakeConn:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self, cursor_factory=None):
        return self._cursor

    def commit(self):
        pass

    def rollback(self):
        raise AssertionError('成功路径不应触发 rollback')

    def close(self):
        pass


_TEST_CONFIG = {
    'app': {'secret_key': 'k', 'host': '127.0.0.1', 'port': 5050, 'debug': False,
            'default_template_name': '21001'},
    'database': {'host': 'localhost', 'port': 5432, 'name': 'ops',
                 'user': 'postgres', 'password': '', 'client_encoding': 'utf8',
                 'schema': 'zabbix_mac'},
    'zabbix_environments': [],
    'sync': {'default_workers': 5, 'max_retry_attempts': 3, 'retry_delay': 2},
    'zabbix_room_mapping': {},
}


@pytest.fixture(scope='module')
def app():
    """mock 配置导入 app 模块（CSRF 禁用），暴露 _upsert/_values_equal"""
    with patch('config_loader.load_config', return_value=_TEST_CONFIG):
        if 'app' in sys.modules:
            del sys.modules['app']
        from app import app, _upsert, _values_equal
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.before_request_funcs[None] = []
        app._upsert = _upsert
        app._values_equal = _values_equal
        yield app


@pytest.fixture
def client(app):
    return app.test_client()


class TestUpsert:
    def test_upsert_created(self, app):
        cur = FakeCursor()  # SELECT → None（空库）
        st, rid = app._upsert(cur, 'items', ['template_name', 'item_key'],
                              {'template_name': 'T', 'item_key': 'k', 'name': 'n'})
        assert st == 'created'
        assert rid == 1
        assert len(cur.calls('INSERT INTO zabbix_mac.items')) == 1

    def test_upsert_skipped(self, app):
        existing = {'id': 1, 'template_name': 'T', 'item_key': 'k', 'name': 'n'}
        cur = FakeCursor([existing])
        st, rid = app._upsert(cur, 'items', ['template_name', 'item_key'],
                              {'template_name': 'T', 'item_key': 'k', 'name': 'n'})
        assert st == 'skipped'
        assert rid == 1
        assert cur.calls('UPDATE zabbix_mac.items') == []
        assert cur.calls('INSERT INTO zabbix_mac.items') == []

    def test_upsert_updated(self, app):
        existing = {'id': 1, 'template_name': 'T', 'item_key': 'k', 'name': 'old'}
        cur = FakeCursor([existing])
        st, _ = app._upsert(cur, 'items', ['template_name', 'item_key'],
                            {'template_name': 'T', 'item_key': 'k', 'name': 'new'})
        assert st == 'updated'
        updates = cur.calls('UPDATE zabbix_mac.items')
        assert len(updates) == 1
        assert updates[0][1][0] == 'new'  # 第一个 SET 参数是 name

    def test_upsert_skip_on_cross_template_clash(self, app):
        """同 item_key 已被其他模板占用 → 跳过（不静默改绑，避免覆盖既有配置）"""
        # 第一次 SELECT(主键) → None；第二次 SELECT(adopt_key=item_key) → 命中冲突行
        cur = FakeCursor([None, {'id': 9, 'item_key': 'k'}])
        st, rid = app._upsert(cur, 'items', ['template_name', 'item_key'],
                              {'template_name': 'B', 'item_key': 'k', 'name': 'n'},
                              adopt_key='item_key')
        assert st == 'skipped'
        assert rid == 9
        assert cur.calls('UPDATE zabbix_mac.items') == []
        assert cur.calls('INSERT INTO zabbix_mac.items') == []

    def test_values_equal(self, app):
        eq = app._values_equal
        assert eq("[{'type': '5', 'params': '0.1'}]", '[{"type": "5", "params": "0.1"}]')
        assert not eq("[{'type': '5'}]", '[{"type": "6"}]')
        assert eq(7, 7)
        assert not eq(7, 8)
        assert eq(None, None)
        assert not eq(None, '')


# ---- API 路由测试 ----

def _post_xml(client, url, template_id=None):
    data = {'file': (io.BytesIO(SAMPLE_XML.encode('utf-8')), 'template.xml')}
    if template_id:
        data['template_id'] = template_id
    return client.post(url, data=data, content_type='multipart/form-data')


class TestParsePreview:
    def _preview(self, client, template_id=None):
        cursor = FakeCursor()
        conn = FakeConn(cursor)
        with patch('app.get_db_connection', return_value=conn):
            resp = _post_xml(client, '/api/base-template/parse-preview', template_id=template_id)
        return resp, cursor

    def test_counts(self, client):
        resp, cursor = self._preview(client)
        data = resp.get_json()
        assert resp.status_code == 200
        assert data['success'] is True
        tc = data['total_counts']
        assert tc == {'templates': 1, 'items': 2, 'triggers': 1, 'discovery_rules': 1,
                      'filter_conditions': 2, 'item_prototypes': 1, 'trigger_prototypes': 1}
        assert data['templates'][0]['name'] == '21001'
        assert data['already_imported'] is False

    def test_template_id_field(self, client):
        """表单携带 template_id → 响应回显且模板名被强制绑定。"""
        resp, cursor = self._preview(client, template_id='91001')
        data = resp.get_json()
        assert resp.status_code == 200
        assert data['success'] is True
        assert data['template_id'] == '91001'
        assert data['templates'][0]['template_id'] == '91001'
        assert data['templates'][0]['name'] == '91001'
        assert data['already_imported'] is False

    def test_preview_warns_when_already_imported(self, client):
        """templates 注册表已有同名模板 → already_imported=True（前端据此弹窗提示并禁用导入）"""
        cursor = FakeCursor([{'id': 1}])
        conn = FakeConn(cursor)
        with patch('app.get_db_connection', return_value=conn):
            resp = _post_xml(client, '/api/base-template/parse-preview', template_id='21001')
        data = resp.get_json()
        assert resp.status_code == 200
        assert data['success'] is True
        assert data['already_imported'] is True

    def test_invalid_xml(self, client):
        data = {'file': (io.BytesIO(b'<broken'), 'bad.xml')}
        resp = client.post('/api/base-template/parse-preview', data=data,
                           content_type='multipart/form-data')
        assert resp.status_code == 400
        assert resp.get_json()['success'] is False

    def test_missing_file(self, client):
        resp = client.post('/api/base-template/parse-preview',
                           data={}, content_type='multipart/form-data')
        assert resp.status_code == 400


class TestExecuteImport:
    def test_created_all(self, client, app):
        cursor = FakeCursor()
        conn = FakeConn(cursor)
        with patch('app.get_db_connection', return_value=conn):
            resp = _post_xml(client, '/api/base-template/execute-import')
        data = resp.get_json()
        assert resp.status_code == 200
        assert data['success'] is True
        r = data['results']
        assert r['templates']['created'] == 1
        assert r['items']['created'] == 2
        assert r['triggers']['created'] == 1
        assert r['discovery_rules']['created'] == 1
        assert r['filter_conditions']['created'] == 2
        assert r['item_prototypes']['created'] == 1
        assert r['trigger_prototypes']['created'] == 1
        # SQL 级验证
        assert len(cursor.calls('INSERT INTO zabbix_mac.templates')) == 1
        assert len(cursor.calls('INSERT INTO zabbix_mac.items')) == 2
        assert len(cursor.calls('INSERT INTO zabbix_mac.discovery_rules')) == 1
        assert len(cursor.calls('INSERT INTO zabbix_mac.filter_conditions')) == 2
        assert len(cursor.calls('INSERT INTO zabbix_mac.item_prototypes')) == 1
        assert len(cursor.calls('INSERT INTO zabbix_mac.trigger_prototypes')) == 1

    def test_template_id_binding(self, client, app):
        """execute-import 携带 template_id → 写入记录的 template_name = 用户输入值。"""
        cursor = FakeCursor()
        conn = FakeConn(cursor)
        with patch('app.get_db_connection', return_value=conn):
            resp = _post_xml(client, '/api/base-template/execute-import', template_id='91001')
        data = resp.get_json()
        assert resp.status_code == 200
        assert data['success'] is True
        # 模板注册表：name 列写入用户 template_id
        tpl_inserts = cursor.calls('INSERT INTO zabbix_mac.templates')
        assert len(tpl_inserts) == 1
        assert any(v == '91001' for v in tpl_inserts[0][1])
        # 6 张基础表：items/triggers/discovery_rules 的 template_name 均被强制绑定
        for marker in ['INSERT INTO zabbix_mac.items',
                       'INSERT INTO zabbix_mac.triggers',
                       'INSERT INTO zabbix_mac.discovery_rules']:
            for _, params in cursor.calls(marker):
                assert any(v == '91001' for v in params)

    def test_rejects_when_template_already_imported(self, client, app):
        """新规：模板ID已导入过 → 弹窗提示并拒绝导入（409，不写库）。"""
        cursor = FakeCursor([{'id': 1}])  # templates 注册表已有该模板
        conn = FakeConn(cursor)
        with patch('app.get_db_connection', return_value=conn):
            resp = _post_xml(client, '/api/base-template/execute-import', template_id='21001')
        data = resp.get_json()
        assert resp.status_code == 409
        assert data['success'] is False
        assert '21001' in data['message']
        assert '拒绝' in data['message']
        # 未发生任何写入
        assert cursor.calls('INSERT INTO zabbix_mac.templates') == []
        assert cursor.calls('INSERT INTO zabbix_mac.items') == []
        assert cursor.calls('INSERT INTO zabbix_mac.triggers') == []

    def test_rejects_when_parent_table_has_records(self, client, app):
        """templates 注册表无记录但 items 已有该 template_name → 同样拒绝（任一父表命中即拒）。"""
        # 第一次 fetchone：templates 注册表 → None；第二次：items → 命中
        cursor = FakeCursor([None, {'id': 7}])
        conn = FakeConn(cursor)
        with patch('app.get_db_connection', return_value=conn):
            resp = _post_xml(client, '/api/base-template/execute-import', template_id='21001')
        data = resp.get_json()
        assert resp.status_code == 409
        assert data['success'] is False
        assert '拒绝' in data['message']
