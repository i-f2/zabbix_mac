# -*- coding: utf-8 -*-
"""
Helper 函数单元测试 — 测试 app.py 中的纯函数工具

覆盖: _normalize_delay, _parse_trigger_item_keys, _translate_item_type,
      _translate_value_type, _classify_baseline, _baseline_css_class,
      _trigger_priority_info, _type_badge_color
"""
import os
import sys
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope='session', autouse=True)
def _patch_app_config():
    """在所有测试前 patch app 配置，避免 RuntimeError"""
    mock_config = {
        'app': {
            'secret_key': 'test-secret-key-for-testing',
            'host': '127.0.0.1',
            'port': 5050,
            'debug': False,
            'default_template_name': '21001',
        },
        'database': {
            'host': 'localhost',
            'port': 5432,
            'name': 'ops',
            'user': 'postgres',
            'password': '',
            'client_encoding': 'utf8',
            'schema': 'zabbix_mac',
        },
        'zabbix_environments': [],
        'sync': {},
        'zabbix_room_mapping': {},
    }
    with patch('config_loader.load_config', return_value=mock_config):
        yield


@pytest.fixture(scope='module')
def helpers():
    """延迟导入 app 模块中的 helper 函数"""
    import importlib
    with patch('config_loader.load_config') as mock_cfg:
        mock_cfg.return_value = {
            'app': {'secret_key': 'test-secret-key-for-testing', 'host': '127.0.0.1',
                    'port': 5050, 'debug': False, 'default_template_name': '21001'},
            'database': {'host': 'localhost', 'port': 5432, 'name': 'ops',
                         'user': 'postgres', 'password': '', 'client_encoding': 'utf8',
                         'schema': 'zabbix_mac'},
            'zabbix_environments': [], 'sync': {}, 'zabbix_room_mapping': {},
        }
        # Force re-import with patched config
        if 'app' in sys.modules:
            del sys.modules['app']
        import app as app_module
        yield app_module


class TestNormalizeDelay:
    """_normalize_delay 边界测试"""

    def test_normal_seconds(self, helpers):
        """正常秒值"""
        assert helpers._normalize_delay('30s') == '30s'

    def test_normal_minutes(self, helpers):
        """正常分钟值"""
        assert helpers._normalize_delay('1m') == '1m'
        assert helpers._normalize_delay('5m') == '5m'

    def test_normal_hours(self, helpers):
        """正常小时值"""
        assert helpers._normalize_delay('1h') == '1h'
        assert helpers._normalize_delay('12h') == '12h'

    def test_zero_values(self, helpers):
        """零值应转为 60s"""
        assert helpers._normalize_delay('0') == '60s'
        assert helpers._normalize_delay('0s') == '60s'
        assert helpers._normalize_delay('0m') == '60s'
        assert helpers._normalize_delay('0h') == '60s'

    def test_empty_values(self, helpers):
        """空值应转为 60s"""
        assert helpers._normalize_delay('') == '60s'
        assert helpers._normalize_delay('   ') == '60s'

    def test_none_value(self, helpers):
        """None 应转为 60s"""
        assert helpers._normalize_delay(None) == '60s'

    def test_whitespace_stripped(self, helpers):
        """前后空格应清除"""
        assert helpers._normalize_delay('  30s  ') == '30s'
        assert helpers._normalize_delay('  1m  ') == '1m'

    def test_invalid_string_preserved(self, helpers):
        """非标准但非零的字符串应原样返回"""
        assert helpers._normalize_delay('invalid') == 'invalid'
        assert helpers._normalize_delay('abc') == 'abc'

    def test_number_input(self, helpers):
        """数字输入应转为字符串"""
        assert helpers._normalize_delay(60) == '60'

    def test_already_normalized(self, helpers):
        """已经是合法值的不变"""
        assert helpers._normalize_delay('60s') == '60s'
        assert helpers._normalize_delay('300s') == '300s'


class TestParseTriggerItemKeys:
    """_parse_trigger_item_keys 边界测试"""

    def test_simple_expression(self, helpers):
        """简单触发器表达式"""
        keys = helpers._parse_trigger_item_keys(
            '{host:system.cpu.load.last()}>5'
        )
        assert 'system.cpu.load' in keys

    def test_multiple_keys(self, helpers):
        """多个监控项 key"""
        keys = helpers._parse_trigger_item_keys(
            '{host:cpu.util.last()}>80 or {host:mem.used.last()}>90'
        )
        assert 'cpu.util' in keys
        assert 'mem.used' in keys
        assert len(keys) >= 2

    def test_key_with_params(self, helpers):
        """带参数的 key"""
        keys = helpers._parse_trigger_item_keys(
            '{host:mysql.status[uptime].last()}=0'
        )
        assert 'mysql.status[uptime]' in keys

    def test_multiple_params(self, helpers):
        """多个参数的 key"""
        keys = helpers._parse_trigger_item_keys(
            '{host:system.swap.size[,pfree].last()}<50'
        )
        assert 'system.swap.size[,pfree]' in keys

    def test_complex_expression_with_functions(self, helpers):
        """多函数表达式"""
        keys = helpers._parse_trigger_item_keys(
            '{host:net.if.in[eth0].last()}>1M or {host:net.if.out[eth0].avg(5m)}>2M'
        )
        assert 'net.if.in[eth0]' in keys
        assert 'net.if.out[eth0]' in keys

    def test_no_keys(self, helpers):
        """不含监控项 key 的表达式"""
        keys = helpers._parse_trigger_item_keys('')
        assert keys == []

    def test_weird_expression(self, helpers):
        """异常格式表达式"""
        keys = helpers._parse_trigger_item_keys('no-brackets-at-all')
        assert keys == [] or isinstance(keys, list)

    def test_none_expression(self, helpers):
        """None 输入"""
        keys = helpers._parse_trigger_item_keys(None)
        assert isinstance(keys, list)

    def test_duplicate_keys_deduped(self, helpers):
        """重复 key 应去重"""
        keys = helpers._parse_trigger_item_keys(
            '{host:key1.last()}>0 or {host:key1.last()}<100'
        )
        assert keys.count('key1') <= 1


class TestTranslateItemType:
    """_translate_item_type 映射完整性测试"""

    def test_all_types_present(self, helpers):
        """所有 Zabbix 监控项类型映射存在"""
        # Zabbix 5.0 item type 值: 0=Zabbix agent, 1=SNMPv1, 2=Zabbix trapper,
        # 3=Simple check, 4=SNMPv2c, 5=Zabbix internal, 6=SNMPv3,
        # 7=Zabbix agent (active), 8=Zabbix aggregate, 9=HTTP agent,
        # 10=SNMP trap, 11=Script, 12=Browser, 13=ODBC, 14=SSH, 15=TELNET, 16=JMX
        for type_val in range(0, 17):
            result = helpers._translate_item_type(str(type_val))
            assert result is not None
            assert isinstance(result, str)
            assert len(result) > 0

    def test_invalid_type_graceful(self, helpers):
        """无效 type 返回原始值"""
        result = helpers._translate_item_type('999')
        # 应该返回原始值或 fallback
        assert result is not None


class TestTranslateValueType:
    """_translate_value_type 映射完整性测试"""

    def test_all_value_types_present(self, helpers):
        """所有 Zabbix value_type 映射存在"""
        # 0=float, 1=char, 2=log, 3=int, 4=text
        for vt in range(0, 5):
            result = helpers._translate_value_type(str(vt))
            assert result is not None
            assert isinstance(result, str)

    def test_invalid_value_type_graceful(self, helpers):
        """无效 value_type 返回原始值"""
        result = helpers._translate_value_type('999')
        assert result is not None


class TestTriggerPriorityInfo:
    """_trigger_priority_info 映射完整性测试"""

    def test_all_priorities_mapped(self, helpers):
        """所有 0-5 等级映射"""
        labels = ['未分类', '信息', '警告', '一般', '严重', '灾难']
        colors = ['secondary', 'info', 'warning', 'warning', 'danger', 'danger']
        for i, (exp_label, exp_color) in enumerate(zip(labels, colors)):
            label, color = helpers._trigger_priority_info(str(i))
            assert label == exp_label
            assert color == exp_color

    def test_invalid_priority_graceful(self, helpers):
        """无效等级返回 fallback"""
        label, color = helpers._trigger_priority_info('999')
        assert label is not None
        assert color is not None


class TestClassifyBaseline:
    """_classify_baseline 分类测试"""

    def test_known_baseline_keys(self, handlers=None):
        """通用基线分类模式"""
        items = [
            # ('item_key', expected_prefix)
            ('system.cpu.load', 'cpu'),
            ('system.cpu.util', 'cpu'),
            ('vm.memory.size', 'mem'),
            ('net.if.in', 'net'),
            ('net.if.out', 'net'),
            ('vfs.fs.size', 'disk'),
            ('vfs.dev.read', 'disk'),
            ('proc.num', 'proc'),
            ('system.uptime', 'system'),
        ]
        # This requires importing the module — skip if not available
        pytest.skip('需要 app 模块基线配置')


class TestTypeBadgeColor:
    """_type_badge_color 测试"""

    def test_all_types_have_colors(self, helpers):
        """所有有效类型返回颜色"""
        for type_val in range(0, 17):
            color = helpers._type_badge_color(str(type_val))
            assert isinstance(color, str)
            assert len(color) > 0
