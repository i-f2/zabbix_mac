# -*- coding: utf-8 -*-
"""
Web 场景复核初始化多端点展开测试

覆盖: _split_endpoints / _compose_web_url 纯函数、_build_webscenario_rows
逐端点展开（命名 `_ip_port` + URL 组合 + 机房 IP 注入）、source_sql 的
api 配对（nginx 系配 webtest_nginx_api、clb/pod 配 webtest_api）、
Web 触发器派生对展开后场景名的继承（派生逻辑零改动，契约钉住）。
"""
import os
import re
import sys
import pytest
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
        yield app


ROOM_MAPPING = {'压测机房': '10.0.0.1'}


def _row(endpoints, api_path='/api/test', name='Sys_Sub_clb', room='压测机房'):
    return {'system': 'Sys', 'subsystem': 'Sub', 'host': 'Zabbix server',
            'name': name, 'endpoints': endpoints, 'api_path': api_path,
            'status_code': '200', 'in_room': room}


class TestSplitEndpoints:
    def test_single_value(self, app_module):
        assert app_module._split_endpoints('192.168.1.1:8080') == ['192.168.1.1:8080']

    def test_multi_comma(self, app_module):
        assert app_module._split_endpoints('192.168.1.1:8080,192.168.1.2:8080') == [
            '192.168.1.1:8080', '192.168.1.2:8080']

    def test_whitespace_and_empty_items(self, app_module):
        assert app_module._split_endpoints(' a:1 , , b:2 ,') == ['a:1', 'b:2']

    def test_fullwidth_comma(self, app_module):
        assert app_module._split_endpoints('a:1，b:2') == ['a:1', 'b:2']

    def test_empty_and_none(self, app_module):
        assert app_module._split_endpoints('') == []
        assert app_module._split_endpoints(None) == []
        assert app_module._split_endpoints(' , , ') == []


class TestComposeWebUrl:
    def test_plain_composition(self, app_module):
        assert app_module._compose_web_url('192.168.1.1:8080', '/api/test') == \
            'http://192.168.1.1:8080/api/test'

    def test_empty_api(self, app_module):
        assert app_module._compose_web_url('192.168.1.1:8080', '') == 'http://192.168.1.1:8080'
        assert app_module._compose_web_url('192.168.1.1:8080', None) == 'http://192.168.1.1:8080'

    def test_schemed_endpoint_no_double_prefix(self, app_module):
        assert app_module._compose_web_url('http://1.2.3.4:80', '/x') == 'http://1.2.3.4:80/x'
        assert app_module._compose_web_url('https://1.2.3.4', '/x') == 'https://1.2.3.4/x'

    def test_api_slash_normalized(self, app_module):
        assert app_module._compose_web_url('1.2.3.4:80', 'api/x') == 'http://1.2.3.4:80/api/x'

    def test_empty_endpoint(self, app_module):
        assert app_module._compose_web_url('', '/api') == ''
        assert app_module._compose_web_url(None, '/api') == ''


class TestBuildWebscenarioRows:
    def test_multi_endpoint_expansion(self, app_module):
        rows = [_row('1.1.1.1:8080,1.1.1.2:8080', '/nginx/api/test', name='Sys_Sub_clb')]
        out = app_module._build_webscenario_rows(rows, ROOM_MAPPING)
        assert len(out) == 2
        # 名称 `_ip_port` 后缀区分端点，机房 IP 注入包裹不变
        assert [r[3] for r in out] == [
            '[10.0.0.1] Web scenario [Sys_Sub_clb_1.1.1.1_8080] failed',
            '[10.0.0.1] Web scenario [Sys_Sub_clb_1.1.1.2_8080] failed',
        ]
        # URL = http://{ip:port}{api_path}，逐端点独立
        assert [r[4] for r in out] == [
            'http://1.1.1.1:8080/nginx/api/test',
            'http://1.1.1.2:8080/nginx/api/test',
        ]
        # 其余列原样透传
        assert all(r[0] == 'Sys' and r[1] == 'Sub' and r[2] == 'Zabbix server'
                   and r[5] == '200' and r[6] == '压测机房' for r in out)

    def test_single_value_uniform_composition(self, app_module):
        """单值也走同一套组合逻辑（统一加 scheme + api 路径）。"""
        out = app_module._build_webscenario_rows(
            [_row('1.1.1.1:8080', '/api/test')], ROOM_MAPPING)
        assert len(out) == 1
        assert out[0][3] == '[10.0.0.1] Web scenario [Sys_Sub_clb_1.1.1.1_8080] failed'
        assert out[0][4] == 'http://1.1.1.1:8080/api/test'

    def test_room_fallback_unknown(self, app_module):
        out = app_module._build_webscenario_rows([_row('1.1.1.1:80', room='无映射机房')], {})
        assert out[0][3].startswith('[Unknown] Web scenario')

    def test_blank_endpoints_yields_no_rows(self, app_module):
        assert app_module._build_webscenario_rows([_row('')], ROOM_MAPPING) == []
        assert app_module._build_webscenario_rows([_row(None)], ROOM_MAPPING) == []

    def test_column_contract_unchanged(self, app_module):
        """插入列契约保持 7 列 —— _rebuild_init_job 的 columns 不变。"""
        assert app_module._WEBSCENARIOS_INIT_SPEC['columns'] == [
            'system', 'subsystem', 'host', 'name', 'url', 'status_code', 'in_room']


class TestSourceSqlApiPairing:
    """api 配对在 source_sql 分支固定：nginx 系（nginx_clb/nginx）配
    webtest_nginx_api，clb/pod 配 webtest_api。"""

    def test_nginx_branches_use_nginx_api(self, app_module):
        sql = app_module._WEBSCENARIOS_INIT_SPEC['source_sql']('')
        assert "nginx_clb as endpoints, webtest_nginx_api as api_path" in sql
        assert "nginx as endpoints, webtest_nginx_api as api_path" in sql

    def test_clb_pod_branches_use_plain_api(self, app_module):
        sql = app_module._WEBSCENARIOS_INIT_SPEC['source_sql']('')
        assert "clb as endpoints, webtest_api as api_path" in sql
        assert "pod as endpoints, webtest_api as api_path" in sql


class TestBoundedScenarioName:
    """场景名收口：包裹后硬性 ≤63（Zabbix httptest.name 64 硬限），
    超预算截断 + 8 位 md5 尾缀 —— 确定性、抗碰撞，短名逐字节不变。"""

    def test_short_name_unchanged_byte_for_byte(self, app_module):
        assert app_module._wrap_scenario_name('Sys_Sub_clb_1.1.1.1_8080', '10.0.0.1') == \
            '[10.0.0.1] Web scenario [Sys_Sub_clb_1.1.1.1_8080] failed'

    def test_overlong_name_bounded_to_63(self, app_module):
        long_inner = '超长系统名_超长子系统名_clb' * 10 + '_1.1.1.1_8080'
        name = app_module._wrap_scenario_name(long_inner, '10.0.0.1')
        assert len(name) <= 63
        assert name.startswith('[10.0.0.1] Web scenario [')
        assert name.endswith('] failed')
        # inner 被截断，且尾缀为 '_' + 8 位十六进制哈希
        inner = name[len('[10.0.0.1] Web scenario ['):-len('] failed')]
        assert len(inner) < len(long_inner)
        assert re.search(r'_[0-9a-f]{8}$', inner)

    def test_deterministic_same_input_same_name(self, app_module):
        long_inner = 'L' * 100
        assert app_module._wrap_scenario_name(long_inner, '10.0.0.1') == \
            app_module._wrap_scenario_name(long_inner, '10.0.0.1')

    def test_distinct_long_endpoints_distinct_names(self, app_module):
        """碰撞金丝雀：同基名不同端点，截断区相同仍须靠哈希尾缀区分。"""
        base = 'Sys_' + '很长的子系统名称' * 20
        n1 = app_module._wrap_scenario_name(base + '_1.1.1.1_8080', '10.0.0.1')
        n2 = app_module._wrap_scenario_name(base + '_1.1.1.2_8080', '10.0.0.1')
        assert len(n1) <= 63 and len(n2) <= 63
        assert n1 != n2

    def test_build_rows_all_bounded_and_urls_intact(self, app_module):
        rows = [_row('1.1.1.1:8080,1.1.1.2:8080', '/api/test',
                     name='Sys_' + '超长子系统名' * 15 + '_clb')]
        out = app_module._build_webscenario_rows(rows, ROOM_MAPPING)
        assert len(out) == 2
        assert all(len(r[3]) <= 63 for r in out)
        assert out[0][3] != out[1][3]
        # URL 组合不受名称收口影响
        assert [r[4] for r in out] == [
            'http://1.1.1.1:8080/api/test',
            'http://1.1.1.2:8080/api/test',
        ]


class TestWebTriggerDerivation:
    def test_trigger_follows_expanded_scenario_name(self, app_module):
        """触发器初始化从已确认场景行派生 —— 场景按端点展开后，每端点自动
        一条触发器，名称与 expression 均引用展开后的场景名（派生逻辑零改动）。"""
        scenario_name = '[10.0.0.1] Web scenario [Sys_Sub_clb_1.1.1.1_8080] failed'
        rows = [{'host': 'Zabbix server', 'web_scenario_name': scenario_name,
                 'system': 'Sys', 'subsystem': 'Sub', 'in_room': '压测机房'}]
        out = app_module._build_web_trigger_rows(rows, ROOM_MAPPING)
        assert len(out) == 1
        trig = out[0]
        assert trig[1] == scenario_name
        assert scenario_name in trig[3]  # expression 引用展开后场景名
        assert 'web.test.fail[' in trig[3]
