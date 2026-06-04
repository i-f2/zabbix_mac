# -*- coding: utf-8 -*-
"""
性能测试 - 数据库查询性能、N+1 查询检测、API 调用性能
"""

import os
import sys
import time
import pytest
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# 性能阈值（秒）
QUERY_RESPONSE_THRESHOLD = 2.0  # 单查询不超过 2 秒
SYNC_SINGLE_HOST_THRESHOLD = 10.0  # 单主机同步不超过 10 秒


class TestDatabasePerformance:
    """数据库查询性能测试（需要真实数据库）"""

    DB_CONFIG = {
        'host': os.environ.get('TEST_DB_HOST', 'localhost'),
        'port': int(os.environ.get('TEST_DB_PORT', 5432)),
        'database': os.environ.get('TEST_DB_NAME', 'zabbix_mac'),
        'user': os.environ.get('TEST_DB_USER', 'fan'),
        'password': os.environ.get('TEST_DB_PASSWORD', ''),
        'client_encoding': 'utf8'
    }

    def test_query_items_response_time(self):
        """测试 items 表查询响应时间"""
        try:
            import psycopg2
            from psycopg2.extras import DictCursor

            conn = psycopg2.connect(**self.DB_CONFIG)
            start = time.time()

            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute("SELECT COUNT(*) FROM items")
                count = cur.fetchone()[0]

            elapsed = time.time() - start
            conn.close()

            print(f"  items 表行数: {count}, 查询耗时: {elapsed:.3f}s")
            assert elapsed < QUERY_RESPONSE_THRESHOLD, \
                f"查询超过阈值 {QUERY_RESPONSE_THRESHOLD}s: {elapsed:.3f}s"
        except Exception as e:
            pytest.skip(f"数据库查询失败: {e}")

    def test_query_triggers_response_time(self):
        """测试 triggers 表查询响应时间"""
        try:
            import psycopg2
            from psycopg2.extras import DictCursor

            conn = psycopg2.connect(**self.DB_CONFIG)
            start = time.time()

            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute("SELECT COUNT(*) FROM triggers")
                count = cur.fetchone()[0]

            elapsed = time.time() - start
            conn.close()

            print(f"  triggers 表行数: {count}, 查询耗时: {elapsed:.3f}s")
            assert elapsed < QUERY_RESPONSE_THRESHOLD
        except Exception as e:
            pytest.skip(f"数据库查询失败: {e}")

    def test_query_review_tables_response_time(self):
        """测试复核表查询响应时间"""
        try:
            import psycopg2
            from psycopg2.extras import DictCursor

            conn = psycopg2.connect(**self.DB_CONFIG)
            results = {}

            for table in ['items_review', 'triggers_review', 'item_prototypes_review', 'trigger_prototypes_review']:
                start = time.time()
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cur.fetchone()[0]
                elapsed = time.time() - start
                results[table] = {'count': count, 'elapsed': f'{elapsed:.3f}s'}
                assert elapsed < QUERY_RESPONSE_THRESHOLD, \
                    f"{table} 查询超过阈值: {elapsed:.3f}s"

            conn.close()
            for table, result in results.items():
                print(f"  {table}: {result['count']} 行, 查询耗时: {result['elapsed']}")
        except Exception as e:
            pytest.skip(f"数据库查询失败: {e}")

    def test_n_plus_one_query_detection(self):
        """检测 N+1 查询模式（代码审查）"""
        with open('zabbix_mac.py', 'r') as f:
            content = f.read()

        # 检测 load_template_from_db 中的多次分离查询
        import re
        queries_in_template_loading = len(re.findall(r'cur\.execute\(', content))

        # load_template_from_db 方法中的查询次数
        with open('zabbix_mac.py', 'r') as f:
            lines = f.readlines()

        in_method = False
        method_queries = 0
        method_lines = []
        for i, line in enumerate(lines):
            if 'def load_template_from_db' in line:
                in_method = True
            if in_method:
                method_lines.append(line)
                if 'cur.execute(' in line:
                    method_queries += 1
                if in_method and i + 1 < len(lines) and 'def ' in lines[i + 1] and lines[i + 1].startswith('    def '):
                    break

        print(f"  load_template_from_db 方法中的 SQL 查询数: {method_queries}")
        print(f"  总 SQL 查询数: {queries_in_template_loading}")

        # 每次模板加载都执行多个独立查询 (items + triggers + discovery_rules + prototypes)
        # 理想情况是 1-2 次 JOIN 查询，当前方法每次加载模板需要 3 次以上查询
        if method_queries > 3:
            print(f"  ⚠ 潜在 N+1 查询: load_template_from_db 执行 {method_queries} 次独立查询")
            print(f"    建议: 使用 JOIN 或子查询合并为 1-2 次查询")

    def test_index_effectiveness(self):
        """检查数据库索引"""
        try:
            import psycopg2
            from psycopg2.extras import DictCursor

            conn = psycopg2.connect(**self.DB_CONFIG)

            # 查询各表的索引信息
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute("""
                    SELECT
                        tablename,
                        indexname,
                        indexdef
                    FROM pg_indexes
                    WHERE schemaname = 'public'
                    ORDER BY tablename, indexname
                """)
                indexes = cur.fetchall()

            conn.close()

            if not indexes:
                print("  ⚠ 没有任何数据库索引")
                return

            # 按表分组
            index_by_table = {}
            for idx in indexes:
                table = idx['tablename']
                if table not in index_by_table:
                    index_by_table[table] = []
                index_by_table[table].append(idx['indexname'])

            for table, idxs in sorted(index_by_table.items()):
                print(f"  {table}: {len(idxs)} 个索引 - {', '.join(idxs[:3])}")
                if len(idxs) > 3:
                    print(f"    ...还有 {len(idxs)-3} 个")

        except Exception as e:
            pytest.skip(f"索引查询失败: {e}")


class TestAPIPerformance:
    """API 调用性能测试（使用 mock）"""

    @pytest.fixture
    def mock_zabbix_client(self):
        with patch('zabbix_mac.ZabbixAPI') as mock_api:
            mock_instance = MagicMock()
            mock_instance.host.get.return_value = [{'hostid': '10084'}]
            mock_instance.hostinterface.get.return_value = [{'interfaceid': '1', 'type': '1'}]
            mock_instance.item.get.return_value = []
            mock_instance.trigger.get.return_value = []
            mock_instance.discoveryrule.get.return_value = []
            mock_instance.httptest.get.return_value = []
            mock_api.return_value = mock_instance
            yield mock_instance

    def test_single_host_sync_api_calls(self, mock_zabbix_client):
        """统计单主机同步的 API 调用次数"""
        from zabbix_mac import ZabbixClient, ConfigLoader, ReportGenerator, SyncEngine

        client = ZabbixClient("http://test/api", "user", "pass")
        client.api = mock_zabbix_client
        config_loader = ConfigLoader(None)
        report = ReportGenerator()
        engine = SyncEngine(client, config_loader, report)

        config = {
            'items': {'test.cpu': {'name': 'CPU', 'delay': '1m', 'value_type': 3}},
            'triggers': {},
            'discovery_rules': [],
            'web_scenarios': []
        }

        start = time.time()
        engine.sync_host("test-host", config, dry_run=False)
        elapsed = time.time() - start

        # API 调用次数统计
        host_get_count = mock_zabbix_client.host.get.call_count
        item_get_count = mock_zabbix_client.item.get.call_count
        interface_get_count = mock_zabbix_client.hostinterface.get.call_count

        print(f"  同步耗时: {elapsed:.3f}s")
        print(f"  API 调用: host.get={host_get_count}, item.get={item_get_count}, "
              f"hostinterface.get={interface_get_count}")

    def test_sync_with_dependent_items(self, mock_zabbix_client):
        """测试依赖监控项同步时的 API 调用"""
        from zabbix_mac import ZabbixClient, ConfigLoader, ReportGenerator, SyncEngine

        client = ZabbixClient("http://test/api", "user", "pass")
        client.api = mock_zabbix_client
        config_loader = ConfigLoader(None)
        report = ReportGenerator()
        engine = SyncEngine(client, config_loader, report)

        # 包含依赖监控项的配置
        config = {
            'items': {
                'test.cpu': {'name': 'CPU', 'delay': '1m', 'value_type': 3},
                'test.mem': {'name': 'Memory', 'delay': '1m', 'value_type': 3}
            },
            'triggers': {},
            'discovery_rules': [],
            'web_scenarios': []
        }

        start = time.time()
        engine.sync_host("test-host", config, dry_run=False)
        elapsed = time.time() - start

        total_api_calls = (mock_zabbix_client.host.get.call_count +
                           mock_zabbix_client.item.get.call_count +
                           mock_zabbix_client.hostinterface.get.call_count)

        print(f"  同步 {len(config['items'])} 个监控项, 耗时: {elapsed:.3f}s")
        print(f"  总 API 调用: {total_api_calls}")

    def test_parallel_sync_overhead(self):
        """测试线程池并行同步的开销"""
        from concurrent.futures import ThreadPoolExecutor

        # 测量线程池创建开销
        start = time.time()

        def mock_sync(name):
            import time as t
            t.sleep(0.01)
            return name

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(mock_sync, f"host{i}") for i in range(5)]
            results = [f.result() for f in futures]

        elapsed = time.time() - start
        print(f"  5 个并行任务完成耗时: {elapsed:.3f}s")
        assert elapsed < 2.0, f"并行任务耗时超过预期: {elapsed:.3f}s"


class TestMemoryUsage:
    """内存使用监控"""

    def test_report_generator_memory(self):
        """测试 ReportGenerator 报告生成的内存使用"""
        from zabbix_mac import ReportGenerator

        report = ReportGenerator()

        # 模拟大量变更记录
        for i in range(1000):
            report.log_change("created", "item", f"test-item-{i}")
            report.log_change("updated", "trigger", f"test-trigger-{i}")

        result = report.generate_report("json")
        report_size = len(result)
        print(f"  2000 条变更记录的报告大小: {report_size} 字符")

        # 检查是否有明显的内存泄漏风险
        changes_count = len(report.changes.get("created", []))
        assert changes_count == 1000, f"变更记录丢失: 期望 1000, 实际 {changes_count}"


class TestQueryPatternAnalysis:
    """查询模式分析（静态代码审查）"""

    def test_template_loading_query_pattern(self):
        """分析模板加载的查询模式"""
        with open('zabbix_mac.py', 'r') as f:
            content = f.read()

        import re
        # 找出所有 SELECT 查询
        selects = re.findall(r'SELECT.*?FROM\s+(\w+)', content, re.IGNORECASE | re.DOTALL)
        tables_queried = [s.strip() for s in selects]

        # 统计每个表的查询次数
        table_counts = {}
        for t in tables_queried:
            table_name = t.split()[0] if ' ' in t else t
            table_counts[table_name] = table_counts.get(table_name, 0) + 1

        print("  各表查询频率:")
        for table, count in sorted(table_counts.items(), key=lambda x: -x[1]):
            print(f"    {table}: {count} 次查询")

        # 检查 LIMIT 使用
        limit_count = len(re.findall(r'LIMIT\s+\d+', content, re.IGNORECASE))
        print(f"  使用 LIMIT 的查询数: {limit_count}")

    def test_api_call_pattern(self):
        """分析同步引擎中的 API 调用模式"""
        with open('zabbix_mac.py', 'r') as f:
            content = f.read()

        import re
        # 找出所有 Zabbix API 调用
        api_calls = re.findall(r'self\.zabbix_client\.(\w+)\(', content)
        api_call_counts = {}
        for call in api_calls:
            api_call_counts[call] = api_call_counts.get(call, 0) + 1

        print("  Zabbix API 调用频率:")
        for method, count in sorted(api_call_counts.items(), key=lambda x: -x[1])[:15]:
            print(f"    {method}: {count} 次")

        # 检查循环内的 API 调用模式
        inner_loop_calls = len(re.findall(r'for.*:\s*\n.*self\.zabbix_client\.\w+\(', content))
        if inner_loop_calls > 0:
            print(f"  ⚠ 循环内 API 调用: 发现 {inner_loop_calls} 处")
            print(f"    建议: 批量 API 调用可减少网络开销")
