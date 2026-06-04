# -*- coding: utf-8 -*-
"""
SyncEngine 测试 - 同步引擎测试
"""

import os
import sys
import pytest
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from zabbix_mac import SyncEngine, ZabbixClient, ConfigLoader, ReportGenerator


class TestSyncEngineInit:
    """SyncEngine 初始化测试"""

    @pytest.fixture
    def engine(self):
        client = ZabbixClient("", "", "", dry_run=True)
        config_loader = ConfigLoader({'host': 'localhost', 'database': 'test'})
        report = ReportGenerator()
        return SyncEngine(client, config_loader, report)

    def test_init(self, engine):
        """初始化同步引擎"""
        assert engine.zabbix_client is not None
        assert engine.config_loader is not None
        assert engine.report_generator is not None


class TestSyncEngineSync:
    """同步功能测试"""

    @pytest.fixture
    def mock_engine(self):
        """创建 mock 同步引擎"""
        client = MagicMock()
        config_loader = MagicMock()
        report = MagicMock()

        client.dry_run = True
        client.get_host_id.return_value = "10084"
        client.get_host_interface_id.return_value = "1"
        client.get_managed_items.return_value = []
        client.get_managed_triggers.return_value = []
        client.get_managed_discovery_rules.return_value = []
        client.get_managed_web_scenarios.return_value = []

        return SyncEngine(client, config_loader, report)

    def test_sync_host_dry_run(self, mock_engine):
        """dry-run 模式下同步主机"""
        config = {
            'items': {},
            'triggers': {},
            'discovery_rules': [],
            'web_scenarios': []
        }
        mock_engine.config_loader.build_host_config.return_value = config
        mock_engine.zabbix_client.get_host_id.return_value = "10084"

        mock_engine.sync_host("test-host", {}, dry_run=True)
        assert mock_engine.zabbix_client.get_host_id.call_count >= 1

    def test_sync_host_no_config(self, mock_engine):
        """主机无配置：get_host_id 先被调用，然后因配置不存在返回"""
        mock_engine.config_loader.build_host_config.return_value = {}

        # sync_host 首先调用 get_host_id，然后 build_host_config
        # 如果 get_host_id 返回 None 则提前返回
        mock_engine.zabbix_client.get_host_id.return_value = None
        mock_engine.sync_host("non-existent", {}, dry_run=True)
        mock_engine.report_generator.log_change.assert_not_called()

    def test_sync_host_not_found(self, mock_engine):
        """主机不存在时跳过"""
        mock_engine.zabbix_client.get_host_id.return_value = None
        mock_engine.sync_host("non-existent", {}, dry_run=True)
        mock_engine.report_generator.log_change.assert_not_called()

    def test_sync_all_hosts_empty(self, mock_engine):
        """同步空配置"""
        mock_engine.sync_all_hosts({}, dry_run=True)
        mock_engine.zabbix_client.get_host_id.assert_not_called()


class TestSyncEngineItems:
    """监控项同步测试"""

    @pytest.fixture
    def engine(self):
        client = ZabbixClient("", "", "", dry_run=True)
        config_loader = ConfigLoader({'host': 'localhost', 'database': 'test'})
        report = ReportGenerator()
        return SyncEngine(client, config_loader, report)

    def test_sync_items_empty(self, engine):
        """同步空监控列表"""
        engine._sync_items("10084", {}, dry_run=True)

    def test_sync_triggers_empty(self, engine):
        """同步空触发器（同步方法需要 dict 参数）"""
        engine._sync_triggers("10084", "test-host", {}, dry_run=True)

    def test_sync_triggers_with_targets(self, engine):
        """同步目标触发器"""
        target_triggers = {
            'High CPU': {'expression': '{test:system.cpu.load.last()}>5', 'priority': 3}
        }
        engine._sync_triggers("10084", "test-host", target_triggers, dry_run=True)

    def test_sync_discovery_rules_empty(self, engine):
        """同步空发现规则"""
        engine._sync_discovery_rules("10084", "test-host", [], dry_run=True)

    def test_sync_web_scenarios_empty(self, engine):
        """同步空 web 场景"""
        engine._sync_web_scenarios("10084", "test-host", [], dry_run=True)


class TestSyncEngineValidation:
    """同步验证测试"""

    def test_validate_sync_no_dry_run(self):
        """验证同步（_validate_sync 无 dry_run 参数）"""
        client = ZabbixClient("", "", "", dry_run=True)
        config_loader = ConfigLoader({'host': 'localhost', 'database': 'test'})
        report = ReportGenerator()
        engine = SyncEngine(client, config_loader, report)

        with patch.object(engine.zabbix_client, 'api', create=True) as mock_api:
            mock_api.item.get.return_value = []
            mock_api.trigger.get.return_value = []
            result = engine._validate_sync("10084", "test-host", {}, {})
            assert result is None  # 不返回值，只生成日志
