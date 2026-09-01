# -*- coding: utf-8 -*-
"""
LLD 发现规则 Filter 绑定测试

覆盖: build_discovery_rule_filter 运算符映射、ensure_discovery_rule 打包 filter、
app._load_dr_filters / _load_dr_configs_with_filters 附加 filter_conditions。
"""
import os
import sys
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zabbix_mac import (ZabbixClient, build_discovery_rule_filter,
                        _normalize_rule_filter)


# ---- build_discovery_rule_filter 纯单元测试 ----

class TestBuildDiscoveryRuleFilter:
    """运算符映射 + filter 结构"""

    def test_empty_conditions(self):
        f = build_discovery_rule_filter(1, [])
        assert f == {'evaltype': 1, 'conditions': []}

    def test_none_evaltype_defaults_zero(self):
        f = build_discovery_rule_filter(None, [])
        assert f['evaltype'] == 0

    def test_equals_wraps_value_op8(self):
        f = build_discovery_rule_filter(1, [
            {'macro': '{#FSTYPE}', 'value': 'ext4', 'operator': 'EQUALS'}])
        assert f['conditions'] == [
            {'macro': '{#FSTYPE}', 'value': '^ext4$', 'operator': 8}]

    def test_not_equal_wraps_value_op9(self):
        f = build_discovery_rule_filter(1, [
            {'macro': '{#FSTYPE}', 'value': 'tmpfs', 'operator': 'NOT_EQUAL'}])
        assert f['conditions'] == [
            {'macro': '{#FSTYPE}', 'value': '^tmpfs$', 'operator': 9}]

    def test_regex_ops_no_wrap(self):
        f = build_discovery_rule_filter(1, [
            {'macro': '{#FSNAME}', 'value': '^/etc', 'operator': 'MATCHES_REGEX'},
            {'macro': '{#FSNAME}', 'value': '/proc', 'operator': 'NOT_MATCHES_REGEX'},
        ])
        assert f['conditions'] == [
            {'macro': '{#FSNAME}', 'value': '^/etc', 'operator': 8},
            {'macro': '{#FSNAME}', 'value': '/proc', 'operator': 9},
        ]

    def test_contains_ops(self):
        f = build_discovery_rule_filter(1, [
            {'macro': '{#MAC}', 'value': 'x', 'operator': 'CONTAINS'},
            {'macro': '{#MAC}', 'value': 'y', 'operator': 'NOT_CONTAINS'},
        ])
        assert [c['operator'] for c in f['conditions']] == [8, 9]

    def test_unknown_operator_defaults_op8(self):
        f = build_discovery_rule_filter(1, [
            {'macro': '{#MAC}', 'value': 'v', 'operator': 'WEIRD'}])
        assert f['conditions'][0]['operator'] == 8

    def test_evaltype_passthrough(self):
        f = build_discovery_rule_filter(2, [])
        assert f['evaltype'] == 2


# ---- _normalize_rule_filter 归一化比较 ----

class TestNormalizeRuleFilter:
    """Zabbix filter 与本地 filter 的可比性（自愈判断的基础）"""

    def test_none_for_missing_filter(self):
        assert _normalize_rule_filter(None) is None
        assert _normalize_rule_filter({}) is None

    def test_zabbix_string_fields_match_local_ints(self):
        # Zabbix 返回：evaltype/operator 为字符串，附带 formulaid
        zbx = {'evaltype': '1', 'conditions': [
            {'macro': '{#FSTYPE}', 'value': '^ext4$', 'operator': '8', 'formulaid': 'A'},
        ]}
        local = {'evaltype': 1, 'conditions': [
            {'macro': '{#FSTYPE}', 'value': '^ext4$', 'operator': 8},
        ]}
        assert _normalize_rule_filter(zbx) == _normalize_rule_filter(local)

    def test_condition_order_ignored(self):
        a = {'evaltype': 0, 'conditions': [
            {'macro': '{#A}', 'value': 'x', 'operator': 8},
            {'macro': '{#B}', 'value': 'y', 'operator': 9},
        ]}
        b = {'evaltype': 0, 'conditions': [
            {'macro': '{#B}', 'value': 'y', 'operator': 9},
            {'macro': '{#A}', 'value': 'x', 'operator': 8},
        ]}
        assert _normalize_rule_filter(a) == _normalize_rule_filter(b)

    def test_value_diff_detected(self):
        a = {'evaltype': 0, 'conditions': [{'macro': '{#A}', 'value': '^ext4$', 'operator': 8}]}
        b = {'evaltype': 0, 'conditions': [{'macro': '{#A}', 'value': '^xfs$', 'operator': 8}]}
        assert _normalize_rule_filter(a) != _normalize_rule_filter(b)


# ---- ensure_discovery_rule 打包 filter ----

class TestEnsureDiscoveryRuleFilter:
    """LLD 自动补齐时 filter 是否打包进 discoveryrule.create"""

    def _client(self, get_result):
        with patch('zabbix_mac.ZabbixAPI') as mock_api:
            mock_instance = MagicMock()
            mock_instance.discoveryrule.get.return_value = get_result
            mock_instance.discoveryrule.create.return_value = {'ruleids': ['777']}
            mock_api.return_value = mock_instance
            client = ZabbixClient('http://t/api', 'u', 'p')
            client.api = mock_instance
            return client, mock_instance

    def test_creates_rule_with_filter(self):
        client, api = self._client([])
        rule_config = {
            'name': 'FS Discovery', 'key': 'vfs.fs.discovery', 'delay': '1h',
            'evaltype': 1, 'status': 0,
            '_conditions': [
                {'macro': '{#FSTYPE}', 'value': 'ext4', 'operator': 'EQUALS'},
                {'macro': '{#FSNAME}', 'value': '^/etc', 'operator': 'MATCHES_REGEX'},
            ],
        }
        rid = client.ensure_discovery_rule('10084', 'vfs.fs.discovery', rule_config, 'iface1')
        assert rid == '777'
        data = api.discoveryrule.create.call_args.args[0]
        assert data['hostid'] == '10084'
        assert data['key_'] == 'vfs.fs.discovery'
        assert data['filter'] == {
            'evaltype': 1,
            'conditions': [
                {'macro': '{#FSTYPE}', 'value': '^ext4$', 'operator': 8},
                {'macro': '{#FSNAME}', 'value': '^/etc', 'operator': 8},
            ],
        }

    def test_no_conditions_no_filter_key(self):
        client, api = self._client([])
        rule_config = {'name': 'Plain', 'key': 'vfs.fs.discovery',
                       'delay': '1h', 'evaltype': 0}
        client.ensure_discovery_rule('10084', 'vfs.fs.discovery', rule_config, None)
        data = api.discoveryrule.create.call_args.args[0]
        assert 'filter' not in data

    def test_rule_exists_no_create(self):
        client, api = self._client([{'itemid': '5', 'key_': 'vfs.fs.discovery'}])
        rid = client.ensure_discovery_rule('10084', 'vfs.fs.discovery',
                                           {'name': 'X', 'key': 'vfs.fs.discovery'})
        assert rid == '5'
        api.discoveryrule.create.assert_not_called()


# ---- ensure_discovery_rule 自愈（已存在规则 filter 缺失/不一致补写）----

class TestEnsureDiscoveryRuleSelfHeal:
    """回归：旧版本创建 LLD 规则时 filter 为空 → 重新同步时补写 filter"""

    CONDITIONS = [
        {'macro': '{#FSTYPE}', 'value': 'ext4', 'operator': 'EQUALS'},
    ]

    def _cfg(self, **extra):
        cfg = {'name': 'FS Discovery', 'key': 'vfs.fs.discovery',
               'delay': '1h', 'evaltype': 1, 'status': 0,
               '_conditions': list(self.CONDITIONS)}
        cfg.update(extra)
        return cfg

    def _client(self, get_result):
        with patch('zabbix_mac.ZabbixAPI') as mock_api:
            mock_instance = MagicMock()
            mock_instance.discoveryrule.get.return_value = get_result
            mock_instance.discoveryrule.create.return_value = {'ruleids': ['777']}
            mock_api.return_value = mock_instance
            client = ZabbixClient('http://t/api', 'u', 'p')
            client.api = mock_instance
            return client, mock_instance

    def test_existing_rule_missing_filter_self_heals(self):
        # Zabbix 返回的规则没有 filter 字段（旧 bug 现场）
        client, api = self._client([{'itemid': '5', 'key_': 'vfs.fs.discovery'}])
        rid = client.ensure_discovery_rule('10084', 'vfs.fs.discovery', self._cfg(), None)
        assert rid == '5'
        api.discoveryrule.update.assert_called_once()
        update_data = api.discoveryrule.update.call_args.args[0]
        # 回归：Zabbix 5.0 discoveryrule.update 必须用 itemid（误用 ruleid 报 -32500）
        assert update_data['itemid'] == '5'
        assert 'ruleid' not in update_data
        assert update_data['filter'] == {
            'evaltype': 1,
            'conditions': [{'macro': '{#FSTYPE}', 'value': '^ext4$', 'operator': 8}],
        }
        api.discoveryrule.create.assert_not_called()

    def test_existing_rule_empty_filter_self_heals(self):
        client, api = self._client([{'itemid': '5', 'key_': 'vfs.fs.discovery',
                                     'filter': {}}])
        rid = client.ensure_discovery_rule('10084', 'vfs.fs.discovery', self._cfg(), None)
        assert rid == '5'
        api.discoveryrule.update.assert_called_once()

    def test_existing_rule_matching_filter_no_update(self):
        # Zabbix 返回的 filter 与本地配置一致（含 formulaid、字符串码）→ 不更新
        client, api = self._client([{'itemid': '5', 'key_': 'vfs.fs.discovery',
                                     'filter': {'evaltype': '1', 'conditions': [
                                         {'macro': '{#FSTYPE}', 'value': '^ext4$',
                                          'operator': '8', 'formulaid': 'A'}]}}])
        rid = client.ensure_discovery_rule('10084', 'vfs.fs.discovery', self._cfg(), None)
        assert rid == '5'
        api.discoveryrule.update.assert_not_called()

    def test_get_uses_select_filter(self):
        """回归：filter 是嵌套对象，必须 selectFilter 获取（放 output 会被忽略）。"""
        client, api = self._client([{'itemid': '5', 'key_': 'vfs.fs.discovery',
                                     'filter': {'evaltype': '1', 'conditions': [
                                         {'macro': '{#FSTYPE}', 'value': '^ext4$',
                                          'operator': '8', 'formulaid': 'A'}]}}])
        client.ensure_discovery_rule('10084', 'vfs.fs.discovery', self._cfg(), None)
        kwargs = api.discoveryrule.get.call_args.kwargs
        assert kwargs.get('selectFilter') == 'extend'
        assert 'filter' not in kwargs.get('output', [])

    def test_existing_rule_different_filter_updates(self):
        client, api = self._client([{'itemid': '5', 'key_': 'vfs.fs.discovery',
                                     'filter': {'evaltype': '1', 'conditions': [
                                         {'macro': '{#FSTYPE}', 'value': '^xfs$',
                                          'operator': '8', 'formulaid': 'A'}]}}])
        rid = client.ensure_discovery_rule('10084', 'vfs.fs.discovery', self._cfg(), None)
        assert rid == '5'
        api.discoveryrule.update.assert_called_once()

    def test_no_local_conditions_does_not_touch_remote(self):
        # 本地无过滤条件 → 即使远程规则 filter 缺失也不补写（不擅自改远程）
        client, api = self._client([{'itemid': '5', 'key_': 'vfs.fs.discovery'}])
        cfg = {'name': 'Plain', 'key': 'vfs.fs.discovery', 'delay': '1h', 'evaltype': 0}
        rid = client.ensure_discovery_rule('10084', 'vfs.fs.discovery', cfg, None)
        assert rid == '5'
        api.discoveryrule.update.assert_not_called()
        api.discoveryrule.create.assert_not_called()


# ---- app 侧 dr 配置加载（附加 filter_conditions）----

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


def _get_app_helpers():
    with patch('config_loader.load_config', return_value=_TEST_CONFIG):
        if 'app' in sys.modules:
            del sys.modules['app']
        from app import _load_dr_filters, _load_dr_configs_with_filters
        return _load_dr_filters, _load_dr_configs_with_filters


def _mock_cursor(side_effect):
    cur = MagicMock()
    cur.fetchall.side_effect = side_effect
    return cur


def _dict_row(data, index):
    """构造真实的 psycopg2 DictRow（list 子类，无法新增未声明键）。

    用于回归测试：DictRow 上设置 '_conditions' 会抛 KeyError，
    与生产环境 DictCursor.fetchall() 返回的 DictRow 行为一致。
    """
    from psycopg2.extras import DictRow
    row = DictRow.__new__(DictRow)
    row._index = index
    row.extend([data[k] for k in index])
    return row


class TestAppDrLoaders:
    """app._load_dr_filters / _load_dr_configs_with_filters"""

    def test_load_dr_filters(self):
        _load_dr_filters, _ = _get_app_helpers()
        cur = _mock_cursor([[{'discovery_rule_id': 7,
                              'macro': '{#FSTYPE}', 'value': 'ext4',
                              'operator': 'EQUALS'}]])
        result = _load_dr_filters(cur, [7])
        assert result == {7: [{'discovery_rule_id': 7, 'macro': '{#FSTYPE}',
                               'value': 'ext4', 'operator': 'EQUALS'}]}

    def test_load_dr_filters_empty_ids(self):
        _load_dr_filters, _ = _get_app_helpers()
        cur = _mock_cursor([])
        assert _load_dr_filters(cur, []) == {}
        cur.execute.assert_not_called()

    def test_load_dr_configs_with_filters(self):
        _, _load_dr_configs_with_filters = _get_app_helpers()
        dr_rows = [{'id': 7, 'name': 'FS', 'key': 'vfs.fs.discovery',
                    'delay': '1h', 'evaltype': 1, 'status': 0}]
        cond_rows = [{'discovery_rule_id': 7, 'macro': '{#FSTYPE}',
                      'value': 'ext4', 'operator': 'EQUALS'}]
        cur = _mock_cursor([dr_rows, cond_rows])
        result = _load_dr_configs_with_filters(cur, [7])
        assert 7 in result
        assert result[7]['_conditions'] == cond_rows
        assert result[7]['key'] == 'vfs.fs.discovery'

    def test_load_dr_configs_empty_ids(self):
        _, _load_dr_configs_with_filters = _get_app_helpers()
        cur = _mock_cursor([])
        assert _load_dr_configs_with_filters(cur, []) == {}
        cur.execute.assert_not_called()

    def test_load_dr_configs_with_filters_dictrow(self):
        """回归：DictCursor 返回 DictRow，设置 '_conditions' 必须不抛 KeyError。

        修复前 `dr_configs[rid]['_conditions'] = conds` 在 DictRow 上直接
        KeyError('_conditions')，导致 /api/sync/preview 报"预览失败"。
        """
        _, _load_dr_configs_with_filters = _get_app_helpers()
        dr_row = _dict_row(
            {'id': 7, 'name': 'FS', 'key': 'vfs.fs.discovery',
             'delay': '1h', 'evaltype': 1, 'status': 0},
            {'id': 0, 'name': 1, 'key': 2, 'delay': 3, 'evaltype': 4, 'status': 5})
        cond_row = _dict_row(
            {'discovery_rule_id': 7, 'macro': '{#FSTYPE}',
             'value': 'ext4', 'operator': 'EQUALS'},
            {'discovery_rule_id': 0, 'macro': 1, 'value': 2, 'operator': 3})
        cur = _mock_cursor([[dr_row], [cond_row]])
        result = _load_dr_configs_with_filters(cur, [7])
        assert 7 in result
        # _conditions 内的元素本身也是 DictRow（可按下标读字段），断言字段值而非 dict 相等
        conds = result[7]['_conditions']
        assert len(conds) == 1
        assert conds[0]['discovery_rule_id'] == 7
        assert conds[0]['macro'] == '{#FSTYPE}'
        assert conds[0]['value'] == 'ext4'
        assert conds[0]['operator'] == 'EQUALS'
        assert result[7]['key'] == 'vfs.fs.discovery'
