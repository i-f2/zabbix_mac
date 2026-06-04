# -*- coding: utf-8 -*-
"""
ZabbixClient 测试 - 核心 API 客户端封装测试
"""

import os
import sys
import pytest
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from zabbix_mac import ZabbixClient, MAX_RETRY_ATTEMPTS


class TestZabbixClientInit:
    """ZabbixClient 初始化测试"""

    def test_init_dry_run(self):
        """dry_run 模式下不连接 API"""
        client = ZabbixClient("http://test/api", "user", "pass", dry_run=True)
        assert client.dry_run is True
        assert client.api is None

    def test_init_no_credentials(self):
        """无凭据时不连接"""
        client = ZabbixClient("", "", "")
        assert client.api is None

    def test_init_with_credentials(self):
        """有凭据时尝试连接（mock）"""
        with patch('zabbix_mac.ZabbixAPI') as mock_api:
            mock_instance = Mock()
            mock_api.return_value = mock_instance
            client = ZabbixClient("http://test/api", "user", "pass")
            mock_api.assert_called_once_with("http://test/api")
            mock_instance.login.assert_called_once_with("user", "pass")


class TestZabbixClientGetHost:
    """获取主机 ID 测试"""

    def test_get_host_id_dry_run(self):
        """dry_run 模式下返回模拟 ID"""
        client = ZabbixClient("", "", "", dry_run=True)
        host_id = client.get_host_id("test-host")
        assert host_id == "12345"

    def test_get_host_id_success(self):
        """成功获取主机 ID"""
        with patch('zabbix_mac.ZabbixAPI') as mock_api:
            mock_instance = MagicMock()
            mock_instance.host.get.return_value = [{'hostid': '10084'}]
            mock_api.return_value = mock_instance
            client = ZabbixClient("http://test/api", "user", "pass")
            client.api = mock_instance
            host_id = client.get_host_id("test-host")
            assert host_id == "10084"
            mock_instance.host.get.assert_called_once()

    def test_get_host_id_not_found(self):
        """主机不存在时返回 None"""
        with patch('zabbix_mac.ZabbixAPI') as mock_api:
            mock_instance = MagicMock()
            mock_instance.host.get.return_value = []
            mock_api.return_value = mock_instance
            client = ZabbixClient("http://test/api", "user", "pass")
            client.api = mock_instance
            host_id = client.get_host_id("non-existent-host")
            assert host_id is None

    def test_get_host_id_exception_then_retry(self):
        """API 异常后重试"""
        with patch('zabbix_mac.ZabbixAPI') as mock_api:
            mock_instance = MagicMock()
            mock_instance.host.get.side_effect = [
                Exception("API Error"),
                [{'hostid': '10084'}]
            ]
            mock_api.return_value = mock_instance
            client = ZabbixClient("http://test/api", "user", "pass")
            client.api = mock_instance
            host_id = client.get_host_id("test-host")
            assert host_id == "10084"
            assert mock_instance.host.get.call_count == 2

    def test_get_host_id_all_retries_fail(self):
        """所有重试都失败时返回 None"""
        with patch('zabbix_mac.ZabbixAPI') as mock_api:
            mock_instance = MagicMock()
            mock_instance.host.get.side_effect = Exception("Persistent API Error")
            mock_api.return_value = mock_instance
            client = ZabbixClient("http://test/api", "user", "pass")
            client.api = mock_instance
            host_id = client.get_host_id("test-host")
            assert host_id is None
            assert mock_instance.host.get.call_count == MAX_RETRY_ATTEMPTS


class TestZabbixClientItems:
    """监控项操作测试"""

    def test_get_managed_items(self):
        """获取受管理监控项（Zabbix 5.0 无标签过滤，返回全部）"""
        with patch('zabbix_mac.ZabbixAPI') as mock_api:
            mock_instance = MagicMock()
            mock_instance.item.get.return_value = [
                {'itemid': '1', 'name': 'item1', 'key_': 'item1'},
                {'itemid': '2', 'name': 'item2', 'key_': 'item2'}
            ]
            mock_api.return_value = mock_instance
            client = ZabbixClient("http://test/api", "user", "pass")
            client.api = mock_instance
            items = client.get_managed_items("10084")
            assert len(items) == 2

    def test_create_item(self):
        """创建监控项"""
        with patch('zabbix_mac.ZabbixAPI') as mock_api:
            mock_instance = MagicMock()
            mock_instance.item.create.return_value = {'itemids': ['30000']}
            mock_api.return_value = mock_instance
            client = ZabbixClient("http://test/api", "user", "pass")
            client.api = mock_instance
            item_id = client.create_item({'name': 'test', 'key_': 'test.key'})
            assert item_id == '30000'

    def test_create_item_failure(self):
        """创建监控项失败"""
        with patch('zabbix_mac.ZabbixAPI') as mock_api:
            mock_instance = MagicMock()
            mock_instance.item.create.side_effect = Exception("Create failed")
            mock_api.return_value = mock_instance
            client = ZabbixClient("http://test/api", "user", "pass")
            client.api = mock_instance
            item_id = client.create_item({'name': 'test'})
            assert item_id is None

    def test_update_item(self):
        """更新监控项"""
        with patch('zabbix_mac.ZabbixAPI') as mock_api:
            mock_instance = MagicMock()
            mock_instance.item.update.return_value = {'itemids': ['30000']}
            mock_api.return_value = mock_instance
            client = ZabbixClient("http://test/api", "user", "pass")
            client.api = mock_instance
            result = client.update_item("30000", {'name': 'updated'})
            assert result is True

    def test_delete_item(self):
        """删除监控项"""
        with patch('zabbix_mac.ZabbixAPI') as mock_api:
            mock_instance = MagicMock()
            mock_instance.item.delete.return_value = {'itemids': ['30000']}
            mock_api.return_value = mock_instance
            client = ZabbixClient("http://test/api", "user", "pass")
            client.api = mock_instance
            result = client.delete_item("30000")
            assert result is True

    def test_create_item_dry_run(self):
        """dry_run 模式下返回模拟 ID"""
        client = ZabbixClient("http://test/api", "user", "pass", dry_run=True)
        item_id = client.create_item({'name': 'test', 'key_': 'test.key'})
        assert item_id == "98765"


class TestZabbixClientTriggers:
    """触发器操作测试"""

    def test_get_managed_triggers(self):
        """获取受管理触发器"""
        with patch('zabbix_mac.ZabbixAPI') as mock_api:
            mock_instance = MagicMock()
            mock_instance.trigger.get.return_value = [
                {'triggerid': '1', 'name': 'trigger1', 'tags': [{'tag': 'ManagedBy', 'value': 'PythonScript'}]},
                {'triggerid': '2', 'name': 'trigger2', 'tags': []}
            ]
            mock_api.return_value = mock_instance
            client = ZabbixClient("http://test/api", "user", "pass")
            client.api = mock_instance
            triggers = client.get_managed_triggers("10084")
            assert len(triggers) == 1
            assert triggers[0]['triggerid'] == '1'

    def test_create_trigger(self):
        """创建触发器"""
        with patch('zabbix_mac.ZabbixAPI') as mock_api:
            mock_instance = MagicMock()
            mock_instance.trigger.create.return_value = {'triggerids': ['20000']}
            mock_api.return_value = mock_instance
            client = ZabbixClient("http://test/api", "user", "pass")
            client.api = mock_instance
            trigger_id = client.create_trigger({'description': 'test trigger'})
            assert trigger_id == '20000'

    def test_update_trigger(self):
        """更新触发器"""
        with patch('zabbix_mac.ZabbixAPI') as mock_api:
            mock_instance = MagicMock()
            client = ZabbixClient("http://test/api", "user", "pass")
            client.api = mock_instance
            result = client.update_trigger("20000", {'description': 'updated'})
            assert result is True
            client.api.trigger.update.assert_called_once()


class TestZabbixClientFingerprint:
    """指纹计算测试"""

    def test_calculate_fingerprint(self):
        """计算对象指纹"""
        client = ZabbixClient("", "", "", dry_run=True)
        obj = {'name': 'test', 'key_': 'test.key', 'delay': '60'}
        fp = client.calculate_fingerprint(obj)
        assert fp is not None
        assert isinstance(fp, str)
        assert len(fp) == 32  # MD5 hex digest length

    def test_fingerprint_excludes_itemid(self):
        """指纹计算排除 itemid"""
        client = ZabbixClient("", "", "", dry_run=True)
        obj1 = {'name': 'test', 'key_': 'test.key'}
        obj2 = {'name': 'test', 'key_': 'test.key', 'itemid': '12345'}
        fp1 = client.calculate_fingerprint(obj1)
        fp2 = client.calculate_fingerprint(obj2)
        assert fp1 == fp2

    def test_fingerprint_differs_on_value_change(self):
        """不同值得出不同指纹"""
        client = ZabbixClient("", "", "", dry_run=True)
        fp1 = client.calculate_fingerprint({'name': 'test', 'delay': '60'})
        fp2 = client.calculate_fingerprint({'name': 'test', 'delay': '120'})
        assert fp1 != fp2


class TestZabbixClientDiscovery:
    """自动发现规则测试"""

    def test_get_managed_discovery_rules(self):
        """获取受管理自动发现规则"""
        with patch('zabbix_mac.ZabbixAPI') as mock_api:
            mock_instance = MagicMock()
            mock_instance.discoveryrule.get.return_value = [
                {'itemid': '1', 'name': 'rule1', 'tags': [{'tag': 'ManagedBy', 'value': 'PythonScript'}]}
            ]
            mock_api.return_value = mock_instance
            client = ZabbixClient("http://test/api", "user", "pass")
            client.api = mock_instance
            rules = client.get_managed_discovery_rules("10084")
            assert len(rules) == 1

    def test_create_discovery_rule(self):
        """创建自动发现规则"""
        with patch('zabbix_mac.ZabbixAPI') as mock_api:
            mock_instance = MagicMock()
            mock_instance.discoveryrule.create.return_value = {'itemids': ['40000']}
            mock_api.return_value = mock_instance
            client = ZabbixClient("http://test/api", "user", "pass")
            client.api = mock_instance
            rule_id = client.create_discovery_rule({'name': 'test rule'})
            assert rule_id == '40000'

    def test_get_item_prototypes(self):
        """获取监控项原型"""
        with patch('zabbix_mac.ZabbixAPI') as mock_api:
            mock_instance = MagicMock()
            mock_instance.itemprototype.get.return_value = [
                {'itemid': '1', 'name': 'prototype1'}
            ]
            mock_api.return_value = mock_instance
            client = ZabbixClient("http://test/api", "user", "pass")
            client.api = mock_instance
            prototypes = client.get_item_prototypes("40000")
            assert len(prototypes) == 1
            mock_instance.itemprototype.get.assert_called_once()

    def test_get_trigger_prototypes(self):
        """获取触发器原型"""
        with patch('zabbix_mac.ZabbixAPI') as mock_api:
            mock_instance = MagicMock()
            mock_instance.triggerprototype.get.return_value = [
                {'triggerid': '1', 'description': 'proto1'}
            ]
            mock_api.return_value = mock_instance
            client = ZabbixClient("http://test/api", "user", "pass")
            client.api = mock_instance
            prototypes = client.get_trigger_prototypes("40000")
            assert len(prototypes) == 1
            mock_instance.triggerprototype.get.assert_called_once()


class TestZabbixClientWebScenarios:
    """Web 场景测试"""

    def test_get_managed_web_scenarios(self):
        """获取受管理 web 场景"""
        with patch('zabbix_mac.ZabbixAPI') as mock_api:
            mock_instance = MagicMock()
            mock_instance.httptest.get.return_value = [
                {'httptestid': '1', 'name': 'web1', 'tags': [{'tag': 'ManagedBy', 'value': 'PythonScript'}]}
            ]
            mock_api.return_value = mock_instance
            client = ZabbixClient("http://test/api", "user", "pass")
            client.api = mock_instance
            scenarios = client.get_managed_web_scenarios("10084")
            assert len(scenarios) == 1

    def test_create_web_scenario(self):
        """创建 web 场景"""
        with patch('zabbix_mac.ZabbixAPI') as mock_api:
            mock_instance = MagicMock()
            mock_instance.httptest.create.return_value = {'httptestids': ['50000']}
            mock_api.return_value = mock_instance
            client = ZabbixClient("http://test/api", "user", "pass")
            client.api = mock_instance
            scenario_id = client.create_web_scenario({'name': 'web_test'})
            assert scenario_id == '50000'

    def test_update_web_scenario(self):
        """更新 web 场景"""
        with patch('zabbix_mac.ZabbixAPI') as mock_api:
            mock_instance = MagicMock()
            client = ZabbixClient("http://test/api", "user", "pass")
            client.api = mock_instance
            result = client.update_web_scenario("50000", {'name': 'updated'})
            assert result is True
            client.api.httptest.update.assert_called_once()

    def test_delete_web_scenario(self):
        """删除 web 场景"""
        with patch('zabbix_mac.ZabbixAPI') as mock_api:
            mock_instance = MagicMock()
            client = ZabbixClient("http://test/api", "user", "pass")
            client.api = mock_instance
            result = client.delete_web_scenario("50000")
            assert result is True
            client.api.httptest.delete.assert_called_once()
