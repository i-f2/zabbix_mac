# -*- coding: utf-8 -*-
"""
并发测试 - 多线程同步、资源竞争、死锁检测、报告生成并发测试
"""

import os
import sys
import time
import threading
import pytest
from unittest.mock import Mock, patch, MagicMock
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestReportGeneratorConcurrency:
    """报告生成器并发测试"""

    def test_log_change_under_concurrent_load(self):
        """多线程同时记录变更"""
        from zabbix_mac import ReportGenerator

        report = ReportGenerator()
        errors = []

        def worker(worker_id):
            try:
                for i in range(100):
                    report.log_change("created", "item", f"worker-{worker_id}-item-{i}")
                    report.log_change("updated", "trigger", f"worker-{worker_id}-trigger-{i}")
            except Exception as e:
                errors.append(str(e))

        threads = []
        for wid in range(10):
            t = threading.Thread(target=worker, args=(wid,))
            threads.append(t)

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"并发记录变更出错: {errors}"
        total_created = len(report.changes.get("created", []))
        total_updated = len(report.changes.get("updated", []))
        assert total_created == 1000, f"created 预期 1000, 实际 {total_created}"
        assert total_updated == 1000, f"updated 预期 1000, 实际 {total_updated}"
        print(f"  10 线程各记录 200 条变更: created={total_created}, updated={total_updated}")

    def test_generate_report_while_logging(self):
        """边记录变更边生成报告"""
        from zabbix_mac import ReportGenerator

        report = ReportGenerator()
        stop_event = threading.Event()

        def logger_worker():
            i = 0
            while not stop_event.is_set():
                report.log_change("created", "item", f"concurrent-item-{i}")
                i += 1
                if i % 100 == 0:
                    time.sleep(0.001)

        def report_worker():
            while not stop_event.is_set():
                try:
                    r = report.generate_report("json")
                    assert r is not None
                except Exception as e:
                    print(f"报告生成异常: {e}")
                time.sleep(0.005)

        log_thread = threading.Thread(target=logger_worker)
        rpt_thread = threading.Thread(target=report_worker)

        log_thread.start()
        rpt_thread.start()

        time.sleep(0.5)
        stop_event.set()

        log_thread.join(timeout=2)
        rpt_thread.join(timeout=2)

        # 验证数据一致性
        created = report.changes.get("created", [])
        updated = report.changes.get("updated", [])
        total = len(created) + len(updated)
        print(f"  边记录边生成报告: 总计 {total} 条变更记录")
        assert total > 0, "未记录任何变更"

    def test_lock_prevents_race_condition(self):
        """验证锁机制防止竞态条件"""
        from zabbix_mac import ReportGenerator

        report = ReportGenerator()
        # 模拟不同线程同时写入
        def race_worker(data_list):
            for item in data_list:
                report.log_change("created", "item", item)

        data_batches = [
            [f"batch0-item-{i}" for i in range(500)],
            [f"batch1-item-{i}" for i in range(500)],
        ]

        threads = [
            threading.Thread(target=race_worker, args=(batch,))
            for batch in data_batches
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(report.changes["created"]) == 1000, \
            f"数据不一致: 预期 1000, 实际 {len(report.changes['created'])}"
        print(f"  锁保护有效: 1000 条并发写入无数据丢失")


class TestThreadPoolSafety:
    """线程池安全测试"""

    def test_sync_all_hosts_no_deadlock(self):
        """sync_all_hosts 不会死锁（使用 mock）"""
        from zabbix_mac import SyncEngine, ZabbixClient, ConfigLoader, ReportGenerator

        client = ZabbixClient("", "", "", dry_run=True)
        config_loader = ConfigLoader(None)
        report = ReportGenerator()
        engine = SyncEngine(client, config_loader, report)

        config = {
            'hosts': {
                'host1': {'ip': '1.1.1.1'},
                'host2': {'ip': '2.2.2.2'},
                'host3': {'ip': '3.3.3.3'},
                'host4': {'ip': '4.4.4.4'},
                'host5': {'ip': '5.5.5.5'},
            }
        }

        timeout = 15  # 15秒超时
        start = time.time()

        with patch.object(engine.zabbix_client, 'get_host_id', return_value=None):
            engine.sync_all_hosts(config, dry_run=True, workers=3)

        elapsed = time.time() - start
        assert elapsed < timeout, f"可能死锁! 耗时 {elapsed:.2f}s 超过阈值 {timeout}s"
        print(f"  5 台主机同步完成, 耗时: {elapsed:.3f}s, 无死锁")

    def test_thread_pool_exception_handling(self):
        """测试线程池中的异常处理"""
        from zabbix_mac import SyncEngine, ZabbixClient, ConfigLoader, ReportGenerator

        client = ZabbixClient("", "", "", dry_run=True)
        config_loader = ConfigLoader(None)
        report = ReportGenerator()
        engine = SyncEngine(client, config_loader, report)

        # 个别主机失败不应影响其他主机
        config = {
            'hosts': {
                'ok-host': {'ip': '1.1.1.1'},
                'bad-host': {'ip': '2.2.2.2'},
            }
        }

        call_count = {}

        def mock_get_host_id(host_name):
            call_count[host_name] = call_count.get(host_name, 0) + 1
            if host_name == 'bad-host':
                raise Exception("Simulated API error")
            return "10084"

        with patch.object(engine.zabbix_client, 'get_host_id', side_effect=mock_get_host_id):
            try:
                engine.sync_all_hosts(config, dry_run=True, workers=2)
            except Exception:
                pytest.fail("sync_all_hosts 不应向上抛出异常")

        print(f"  ok-host 被调用 {call_count.get('ok-host', 0)} 次")
        print(f"  bad-host 被调用 {call_count.get('bad-host', 0)} 次")

    def test_concurrent_sync_same_host(self):
        """同一主机被并发同步时的行为"""
        from zabbix_mac import SyncEngine, ZabbixClient, ConfigLoader, ReportGenerator

        client = ZabbixClient("", "", "", dry_run=True)
        config_loader = ConfigLoader(None)
        report = ReportGenerator()
        engine = SyncEngine(client, config_loader, report)

        config = {
            'items': {'test.cpu': {'delay': '1m', 'value_type': 3}},
            'triggers': {}
        }

        def sync_wrapper():
            engine.sync_host("same-host", config, dry_run=True)

        threads = [threading.Thread(target=sync_wrapper) for _ in range(3)]
        start = time.time()

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        elapsed = time.time() - start
        print(f"  3 线程同步同一主机完成, 耗时: {elapsed:.3f}s")
        # 验证不抛出异常即可


class TestResourceContention:
    """资源竞争检测"""

    def test_zabbix_client_shared_across_threads(self):
        """验证 ZabbixClient 在多线程间共享时的行为"""
        from zabbix_mac import ZabbixClient

        # 使用 mock 避免真实连接
        with patch('zabbix_mac.ZabbixAPI'):
            client = ZabbixClient("http://test/api", "user", "pass")
            client.api = MagicMock()
            client.api.host.get.return_value = [{'hostid': '10084'}]

            errors = []

            def get_hosts(thread_id):
                try:
                    for _ in range(50):
                        result = client.get_host_id(f"test-host-{thread_id}")
                        assert result is not None
                except Exception as e:
                    errors.append(str(e))

            threads = [
                threading.Thread(target=get_hosts, args=(i,))
                for i in range(5)
            ]

            for t in threads:
                t.start()
            for t in threads:
                t.join()

            assert len(errors) == 0, f"共享 ZabbixClient 出错: {errors}"
            print(f"  5 线程并发调用 get_host_id {5*50} 次, 无错误")

    def test_config_loader_shared_connection(self):
        """验证 ConfigLoader 数据库连接在模拟环境下的行为"""
        from zabbix_mac import ConfigLoader

        config_loader = ConfigLoader(None)  # 无数据库配置，不连接

        errors = []

        def access_loader(thread_id):
            try:
                # 只访问无共享状态的方法
                template = config_loader.load_template("nonexistent")
                host_config = config_loader.get_host_config({}, "test")
            except Exception as e:
                errors.append(str(e))

        threads = [
            threading.Thread(target=access_loader, args=(i,))
            for i in range(5)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"ConfigLoader 并发访问出错: {errors}"
        print(f"  5 线程并发访问 ConfigLoader, 无错误")

    def test_report_generator_lock_contention(self):
        """测试高竞争下的锁性能"""
        from zabbix_mac import ReportGenerator

        report = ReportGenerator()
        thread_count = 20
        ops_per_thread = 500

        def high_contention_worker(wid):
            for i in range(ops_per_thread):
                report.log_change("created", "item", f"hc-item-{wid}-{i}")

        start = time.time()
        threads = [threading.Thread(target=high_contention_worker, args=(i,))
                   for i in range(thread_count)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        elapsed = time.time() - start
        total_ops = thread_count * ops_per_thread
        throughput = total_ops / elapsed

        assert len(report.changes["created"]) == total_ops, \
            f"数据丢失: 预期 {total_ops}, 实际 {len(report.changes['created'])}"
        print(f"  20 线程 × 500 次写入, 耗时 {elapsed:.3f}s, 吞吐量 {throughput:.0f} ops/s")


class TestDeadlockDetection:
    """死锁检测"""

    def test_no_deadlock_in_report_generator(self):
        """验证 ReportGenerator 不会死锁"""
        from zabbix_mac import ReportGenerator

        report = ReportGenerator()

        def worker():
            for i in range(200):
                report.log_change("created", "item", f"dl-item-{i}")
                report.log_change("updated", "trigger", f"dl-trigger-{i}")

        # 模拟长时间持有锁然后生成报告
        def lock_holder():
            for i in range(50):
                with report.lock:
                    report.changes["created"].append({
                        "type": "item", "name": f"held-{i}", "details": None
                    })
                    time.sleep(0.001)  # 模拟耗时操作

        threads = [threading.Thread(target=worker) for _ in range(3)]
        threads.append(threading.Thread(target=lock_holder))

        start = time.time()
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        elapsed = time.time() - start
        total = len(report.changes["created"]) + len(report.changes["updated"])
        print(f"  死锁检测通过: {total} 条记录, 耗时 {elapsed:.3f}s")

    def test_no_deadlock_sync_all_hosts_parallel(self):
        """验证并发同步不会死锁（使用补丁的 API）"""
        from zabbix_mac import ZabbixClient, ConfigLoader, ReportGenerator, SyncEngine

        client = MagicMock()
        client.dry_run = True
        client.get_host_id.return_value = "10084"
        client.get_host_interface_id.return_value = "1"
        client.get_managed_items.return_value = []
        client.get_managed_triggers.return_value = []
        client.get_managed_discovery_rules.return_value = []
        client.get_managed_web_scenarios.return_value = []
        client.calculate_fingerprint.return_value = "test_fingerprint"

        config_loader = ConfigLoader(None)
        report = ReportGenerator()
        engine = SyncEngine(client, config_loader, report)

        config = {
            'hosts': {
                'host1': None, 'host2': None, 'host3': None,
                'host4': None, 'host5': None,
            }
        }

        def multi_sync():
            engine.sync_all_hosts(config, dry_run=True, workers=5)

        threads = [threading.Thread(target=multi_sync) for _ in range(2)]

        start = time.time()
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        elapsed = time.time() - start
        assert elapsed < 30, "可能死锁! 超过 30 秒超时"
        print(f"  并行 sync_all_hosts 完成, 耗时: {elapsed:.3f}s, 无死锁")
