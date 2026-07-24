#!/usr/bin/env python3
"""
Zabbix MaC — 本地 Zabbix 5.0 集成测试脚本
===========================================
全面测试：连通性、资产同步、监控项/触发器/Web场景下发
⚠️ 铁律：本脚本只做测试诊断，不修改任何业务代码
"""

import sys
import os
import time
import json
import traceback
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

RESULTS: List[Dict[str, Any]] = []  # {case_id, module, severity, status, description, error, fix_suggestion}

def record(case_id: str, module: str, severity: str, status: str,
           description: str, error: str = "", fix_suggestion: str = ""):
    RESULTS.append(dict(case_id=case_id, module=module, severity=severity,
                        status=status, description=description,
                        error=error, fix_suggestion=fix_suggestion))
    icon = "✅" if status == "PASS" else ("⚠️" if status == "WARN" else "❌")
    print(f"  {icon} {case_id} [{status}] {description}")
    if error:
        print(f"     Error: {error[:200]}")

def header(title: str):
    print(f"\n{'='*70}\n  {title}\n{'='*70}")

# ---------------------------------------------------------------------------
# Test 1: Basic Connectivity & Config
# ---------------------------------------------------------------------------

def test_1_1_config_loading():
    """用例 1.1: 验证 config.yaml 中 local 环境配置加载"""
    header("Test 1.1: Config Loading — local environment")

    try:
        from config_loader import load_config, get_zabbix_environments

        # Load with ENV=local
        os.environ['ENV'] = 'local'
        config = load_config()
        envs = get_zabbix_environments(config)

        local_env = envs.get('本地Docker沙箱')
        if not local_env:
            record("TC-1.1", "Config", "High", "FAIL",
                   "local 环境未加载",
                   "get_zabbix_environments() 返回: " + json.dumps(envs, ensure_ascii=False),
                   "检查 config_local.yaml 是否存在，确认 zabbix_environments 列表包含 key=local")
            return

        assert local_env['url'] == 'http://localhost:8080/api_jsonrpc.php', \
            f"URL mismatch: {local_env['url']}"
        assert local_env['username'] == 'Admin', f"User mismatch: {local_env['username']}"
        assert local_env['password'] == 'zabbix', "Password mismatch"

        record("TC-1.1", "Config", "Low", "PASS",
               f"local 环境加载成功: url={local_env['url']}, user={local_env['username']}")

        # Also test without ENV=local (using config.yaml.example)
        os.environ.pop('ENV', None)
        config2 = load_config('config.yaml.example')
        envs2 = get_zabbix_environments(config2)
        names = list(envs2.keys())
        assert '本地Docker沙箱' in names, f"config.yaml.example 缺少本地环境: {names}"
        assert '深交所证联网' in names, f"config.yaml.example 缺少深交所证联网: {names}"
        print(f"     config.yaml.example 环境列表: {names}")

        record("TC-1.1b", "Config", "Low", "PASS",
               f"config.yaml.example 包含 {len(names)} 个环境: {names}")

    except Exception as e:
        record("TC-1.1", "Config", "High", "FAIL",
               "配置加载异常", str(e) + "\n" + traceback.format_exc()[:300],
               "检查 config.yaml / config_local.yaml 文件是否存在且格式正确")


def test_1_2_zabbix_api_connectivity():
    """用例 1.2: Zabbix API 登录/登出 + pyzabbix 兼容性"""
    header("Test 1.2: Zabbix API Connectivity — Zabbix 5.0 login/logout")

    try:
        from zabbix_mac import ZabbixAPI, ZabbixClient, ZabbixAPIException

        # Test 1: Low-level API
        api = ZabbixAPI('http://localhost:8080/api_jsonrpc.php')
        ver = api.api_version()
        print(f"     Zabbix version via apiinfo.version: {ver}")
        assert ver.startswith('5.0'), f"Expected Zabbix 5.0.x, got {ver}"
        record("TC-1.2a", "Zabbix API", "Low", "PASS",
               f"Zabbix API version: {ver}")

        # Test 2: Login
        login_result = api.user.login(user='Admin', password='zabbix')
        assert login_result and len(login_result) > 0, "Login returned empty token"
        print(f"     Login successful, token: {login_result[:8]}...")
        record("TC-1.2b", "Zabbix API", "Low", "PASS",
               "user.login 成功获取 auth token")

        # Test 3: Logout (may fail if session already ended)
        try:
            logout_result = api.user.logout()
            record("TC-1.2c", "Zabbix API", "Low", "PASS",
                   "user.logout 成功")
        except Exception as logout_err:
            # Known pyzabbix quirk: logout can fail after api_version() call
            record("TC-1.2c", "Zabbix API", "Low", "WARN",
                   f"user.logout 失败 (pyzabbix 已知问题): {str(logout_err)[:100]}",
                   str(logout_err),
                   "不影响正常功能，logout 失败时 session 会自动过期")

        # Test 4: ZabbixClient wrapper
        client = ZabbixClient(
            url='http://localhost:8080/api_jsonrpc.php',
            username='Admin',
            password='zabbix',
            dry_run=False
        )
        # Test get_host_id with the built-in "Zabbix server" host
        host_id = client.get_host_id('Zabbix server')
        if host_id:
            print(f"     Host 'Zabbix server' ID: {host_id}")
            record("TC-1.2d", "Zabbix API", "Low", "PASS",
                   f"ZabbixClient.get_host_id('Zabbix server') = {host_id}")
        else:
            record("TC-1.2d", "Zabbix API", "Medium", "WARN",
                   "ZabbixClient.get_host_id('Zabbix server') 返回 None",
                   "get_host_id 查询 'Zabbix server' 返回空",
                   "检查 ZabbixClient._connect() 和 get_host_id() 的 host.get filter 逻辑")

        # Test 5: Get host interface
        if host_id:
            iface_id = client.get_host_interface_id(host_id)
            if iface_id:
                print(f"     Host interface ID: {iface_id}")
                record("TC-1.2e", "Zabbix API", "Low", "PASS",
                       f"ZabbixClient.get_host_interface_id({host_id}) = {iface_id}")
            else:
                record("TC-1.2e", "Zabbix API", "Medium", "WARN",
                       "get_host_interface_id 返回 None (Zabbix server 无 agent 接口，正常)",
                       "Zabbix server 主机没有配置 Zabbix agent 接口",
                       "无需修复 — 无 agent 接口的主机无法下发监控项")

    except Exception as e:
        record("TC-1.2", "Zabbix API", "High", "FAIL",
               "Zabbix API 连接失败", str(e) + "\n" + traceback.format_exc()[:300],
               "确认 Docker 容器 zbx50-web 在运行: docker ps | grep zbx50")

# ---------------------------------------------------------------------------
# Test 2: Asset (Host) Sync
# ---------------------------------------------------------------------------

def test_2_host_sync():
    """用例 2.1 & 2.2: 主机资产同步"""
    header("Test 2: Host Asset Sync")

    try:
        from config_loader import load_config, get_db_config, get_zabbix_environments
        import psycopg2
        from psycopg2.extras import DictCursor

        os.environ['ENV'] = 'local'
        config = load_config()
        db_cfg = get_db_config(config)
        envs = get_zabbix_environments(config)
        local_env = envs.get('本地Docker沙箱')

        # Connect to local DB
        conn = psycopg2.connect(**db_cfg)
        cur = conn.cursor(cursor_factory=DictCursor)

        # Check hosts table
        cur.execute("SELECT COUNT(*) as cnt FROM hosts")
        host_count = cur.fetchone()['cnt']
        print(f"     hosts 表记录数: {host_count}")

        # Check host data quality
        cur.execute("""
            SELECT name, description, template_name, system, subsystem
            FROM hosts LIMIT 5
        """)
        sample_hosts = cur.fetchall()
        for h in sample_hosts:
            print(f"     Host: {h['name']} ({h.get('description','')}) "
                  f"template={h['template_name']} system={h['system']}")

        if host_count > 0:
            record("TC-2.1", "Asset Sync", "Low", "PASS",
                   f"hosts 表包含 {host_count} 条记录，字段完整")
        else:
            record("TC-2.1", "Asset Sync", "Medium", "WARN",
                   "hosts 表无记录（可能尚未执行同步）",
                   "",
                   "执行 /host/sync 或手动插入主机数据")

        # Test Zabbix host existence
        from zabbix_mac import ZabbixClient
        client = ZabbixClient(
            url=local_env['url'],
            username=local_env['username'],
            password=local_env['password'],
            dry_run=False
        )

        zabbix_hosts = client.api.host.get(output=["hostid", "host", "name"])
        print(f"     Zabbix 5.0 中主机数: {len(zabbix_hosts)}")
        for zh in zabbix_hosts[:5]:
            print(f"     Zabbix Host: {zh['host']} (ID: {zh['hostid']})")

        record("TC-2.2", "Asset Sync", "Low", "PASS",
               f"Zabbix API host.get 返回 {len(zabbix_hosts)} 台主机")

        cur.close()
        conn.close()

    except Exception as e:
        record("TC-2", "Asset Sync", "High", "FAIL",
               "主机资产同步测试异常", str(e) + "\n" + traceback.format_exc()[:300],
               "检查数据库连接和 Zabbix API 连通性")

# ---------------------------------------------------------------------------
# Test 3: Items Review Sync
# ---------------------------------------------------------------------------

def test_3_items_sync():
    """用例 3.1-3.3: 监控项复核与下发"""
    header("Test 3: Items Review Sync")

    try:
        from config_loader import load_config, get_db_config, get_zabbix_environments
        from zabbix_mac import ZabbixClient, ZabbixAPIException
        import psycopg2
        from psycopg2.extras import DictCursor

        os.environ['ENV'] = 'local'
        config = load_config()
        db_cfg = get_db_config(config)
        envs = get_zabbix_environments(config)
        local_env = envs.get('本地Docker沙箱')

        conn = psycopg2.connect(**db_cfg)
        cur = conn.cursor(cursor_factory=DictCursor)

        # 3.1: Check items_review data
        cur.execute("SELECT COUNT(*) as cnt FROM items_review")
        review_count = cur.fetchone()['cnt']
        print(f"     items_review 记录数: {review_count}")

        cur.execute("""
            SELECT id, host_ip, item_key, name, type, change_type, confirmed
            FROM items_review LIMIT 5
        """)
        sample_items = cur.fetchall()
        for it in sample_items:
            print(f"     Item: {it['item_key']} ({it['name']}) "
                  f"host={it['host_ip']} type={it['type']} "
                  f"change={it['change_type']} confirmed={it['confirmed']}")

        if review_count > 0:
            record("TC-3.1a", "Items Sync", "Low", "PASS",
                   f"items_review 包含 {review_count} 条记录")
        else:
            record("TC-3.1a", "Items Sync", "Medium", "WARN",
                   "items_review 无记录，跳过下发测试",
                   "",
                   "先执行 /items-review/initialize 初始化复核表")

        # 3.2: Test Zabbix 5.0 item.create compatibility (tags vs applications)
        client = ZabbixClient(
            url=local_env['url'],
            username=local_env['username'],
            password=local_env['password'],
            dry_run=False
        )

        # Get a host with interface to test item creation
        test_host_id = None
        test_iface_id = None
        zabbix_hosts = client.api.host.get(
            output=["hostid", "host"],
            selectInterfaces=["interfaceid", "ip", "type"]
        )
        for h in zabbix_hosts:
            if h.get('interfaces') and len(h['interfaces']) > 0:
                test_host_id = h['hostid']
                test_iface_id = h['interfaces'][0]['interfaceid']
                print(f"     测试主机: {h['host']} (hostid={test_host_id}, ifaceid={test_iface_id})")
                break

        if test_host_id and test_iface_id:
            # Test 3.2a: Create a simple item (no tags) — should succeed on Zabbix 5.0
            test_key = f"test.integration.check[{int(time.time())}]"
            test_item_data = {
                "hostid": test_host_id,
                "interfaceid": test_iface_id,
                "name": f"[INTEGRATION TEST] System Check {int(time.time())}",
                "key_": test_key,
                "type": 7,  # Zabbix trapper
                "value_type": 3,  # Numeric (unsigned)
                "delay": "30s",
            }

            try:
                item_id = client.create_item(test_item_data)
                if item_id:
                    print(f"     Created test item: {test_key} (ID: {item_id})")
                    record("TC-3.2a", "Items Sync", "Low", "PASS",
                           f"Zabbix 5.0 item.create 成功 (无 tags): {test_key}")

                    # Cleanup
                    client.delete_item(item_id)
                    print(f"     Cleaned up test item {item_id}")
                else:
                    record("TC-3.2a", "Items Sync", "High", "FAIL",
                           "item.create 返回 None（无 item_id）",
                           "create_item 返回了 None",
                           "检查 ZabbixClient.create_item() 的返回值处理")

            except ZabbixAPIException as e:
                record("TC-3.2a", "Items Sync", "High", "FAIL",
                       "Zabbix 5.0 item.create 失败",
                       str(e),
                       "检查 API 参数是否兼容 Zabbix 5.0，确认不存在 tags/applications 字段冲突")

            # Test 3.2b: Try creating item WITH applications (Zabbix 5.0 specific)
            try:
                test_item_with_app = {
                    "hostid": test_host_id,
                    "interfaceid": test_iface_id,
                    "name": f"[INTEGRATION TEST] With App {int(time.time())}",
                    "key_": f"test.with.app[{int(time.time())}]",
                    "type": 7,
                    "value_type": 3,
                    "delay": "30s",
                    "applications": ["Integration Test App"],  # Zabbix 5.0 使用 applications 数组
                }
                item_id2 = client.create_item(test_item_with_app)
                if item_id2:
                    print(f"     Created item with applications: {item_id2}")
                    record("TC-3.2b", "Items Sync", "Low", "PASS",
                           "Zabbix 5.0 item.create 支持 applications 参数")
                    client.delete_item(item_id2)
                else:
                    record("TC-3.2b", "Items Sync", "Medium", "WARN",
                           "applications 参数可能导致创建失败",
                           "create_item 返回 None",
                           "检查 applications 格式是否正确（应为应用集名称列表）")

            except ZabbixAPIException as e:
                error_msg = str(e)
                if 'tags' in error_msg.lower() or 'Invalid params' in error_msg:
                    record("TC-3.2b", "Items Sync", "High", "FAIL",
                           "Zabbix 5.0 item.create 拒绝 tags 参数",
                           error_msg,
                           "在 create_item() 中移除 tags 字段后再调用 API")
                elif 'applications' in error_msg.lower():
                    record("TC-3.2b", "Items Sync", "High", "FAIL",
                           "Zabbix 5.0 applications 参数格式错误",
                           error_msg,
                           "applications 应为应用集名称字符串数组，或需先创建应用集再传 applicationids")
                else:
                    record("TC-3.2b", "Items Sync", "Medium", "FAIL",
                           "Zabbix 5.0 item.create 未知错误", error_msg)

            # Test 3.3: Sync to non-existent host
            test_item_bad_host = {
                "hostid": "999999",
                "interfaceid": test_iface_id,
                "name": "[INTEGRATION TEST] Bad Host Item",
                "key_": f"test.bad.host[{int(time.time())}]",
                "type": 7,
                "value_type": 3,
                "delay": "30s",
            }
            try:
                client.create_item(test_item_bad_host)
                record("TC-3.3", "Items Sync", "Medium", "WARN",
                       "向不存在的主机下发监控项未报错（意外）",
                       "create_item(hostid=999999) 未抛出异常",
                       "在 create_item 前增加主机存在性校验")
            except ZabbixAPIException as e:
                record("TC-3.3", "Items Sync", "Low", "PASS",
                       f"向不存在主机下发监控项正确报错: {str(e)[:100]}")
            except Exception as e:
                record("TC-3.3", "Items Sync", "Low", "PASS",
                       f"向不存在主机下发监控项正确报错: {str(e)[:100]}")
        else:
            record("TC-3.2", "Items Sync", "Medium", "WARN",
                   "Zabbix 中无带接口的主机，无法测试监控项下发",
                   "",
                   "在 Zabbix 中创建一台带 Zabbix agent 接口的主机")

        cur.close()
        conn.close()

    except Exception as e:
        record("TC-3", "Items Sync", "High", "FAIL",
               "监控项同步测试异常", str(e) + "\n" + traceback.format_exc()[:300])

# ---------------------------------------------------------------------------
# Test 4: Trigger Sync
# ---------------------------------------------------------------------------

def test_4_trigger_sync():
    """用例 4.1 & 4.2: 触发器复核与下发"""
    header("Test 4: Trigger Review & Sync")

    try:
        from config_loader import load_config, get_db_config, get_zabbix_environments
        from zabbix_mac import ZabbixClient, ZabbixAPIException
        import psycopg2
        from psycopg2.extras import DictCursor

        os.environ['ENV'] = 'local'
        config = load_config()
        db_cfg = get_db_config(config)
        envs = get_zabbix_environments(config)
        local_env = envs.get('本地Docker沙箱')

        conn = psycopg2.connect(**db_cfg)
        cur = conn.cursor(cursor_factory=DictCursor)

        # Check triggers_review data
        cur.execute("SELECT COUNT(*) as cnt FROM triggers_review")
        review_count = cur.fetchone()['cnt']
        print(f"     triggers_review 记录数: {review_count}")

        cur.execute("""
            SELECT id, host_ip, name, expression, change_type, confirmed
            FROM triggers_review LIMIT 5
        """)
        sample_triggers = cur.fetchall()
        for tr in sample_triggers:
            expr_preview = (tr['expression'] or '')[:80]
            print(f"     Trigger: {tr['name']} "
                  f"host={tr['host_ip']} change={tr['change_type']}")
            print(f"       expr: {expr_preview}...")

        if review_count > 0:
            record("TC-4.1a", "Trigger Sync", "Low", "PASS",
                   f"triggers_review 包含 {review_count} 条记录")
        else:
            record("TC-4.1a", "Trigger Sync", "Medium", "WARN",
                   "triggers_review 无记录，跳过下发测试",
                   "",
                   "先执行触发器初始化填充数据")

        # Test 4.2: Trigger expression parsing compatibility with Zabbix 5.0
        # Test the regex parser from app.py
        import re
        test_expressions = [
            # Standard Zabbix 5.0 syntax
            ("{Zabbix server:system.cpu.util[,idle].last()}<20", True),
            ("{Zabbix server:mysql.status[uptime].last()}=0", True),
            ("{Zabbix server:net.if.in[eth0].avg(5m)}>1000000", True),
            # Complex expressions
            ("{host1:key1.last()}>100 and {host2:key2.last()}<50", True),
            # Edge case: key with dots
            ("{host:web.test.fail[name].last()}>0", True),
        ]

        # Use the actual _parse_trigger_item_keys from app.py
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from app import _parse_trigger_item_keys

        all_keys = []
        for expr, expected_valid in test_expressions:
            keys = _parse_trigger_item_keys(expr)
            all_keys.extend(keys)
            status = "OK" if len(keys) > 0 else "FAIL"
            print(f"     Parse: '{expr[:50]}...' → keys={keys} [{status}]")
            if len(keys) == 0 and expected_valid:
                record("TC-4.2", "Trigger Sync", "Medium", "WARN",
                       f"触发器表达式解析返回空: {expr[:60]}",
                       f"_parse_trigger_item_keys('{expr}') = []",
                       "检查正则表达式是否匹配 Zabbix 5.0 语法")

        if all_keys:
            record("TC-4.2", "Trigger Sync", "Low", "PASS",
                   f"触发器表达式解析器正常工作，提取到 keys: {all_keys[:5]}...")
        else:
            record("TC-4.2", "Trigger Sync", "Medium", "WARN",
                   "触发器表达式解析器未提取到任何 key", "",
                   "检查 _parse_trigger_item_keys 正则")

        # Test 4.1b: Actually create a trigger on Zabbix 5.0
        client = ZabbixClient(
            url=local_env['url'],
            username=local_env['username'],
            password=local_env['password'],
            dry_run=False
        )

        # Find a host to attach trigger to
        zabbix_hosts = client.api.host.get(output=["hostid", "host"])
        test_host = None
        for h in zabbix_hosts:
            # Get items for this host
            items = client.api.item.get(
                output=["itemid", "key_"],
                hostids=[h['hostid']],
                limit=1
            )
            if items:
                test_host = h
                test_item = items[0]
                print(f"     测试主机: {h['host']}, 测试 item: {test_item['key_']} (ID: {test_item['itemid']})")
                break

        if test_host and test_item:
            # Zabbix 5.0 trigger expression syntax
            trigger_expr = f"{{{test_host['host']}:{test_item['key_']}.last()}}=0"
            trigger_data = {
                "description": f"[INTEGRATION TEST] Trigger {int(time.time())}",
                "expression": trigger_expr,
                "priority": 2,  # Warning
            }
            try:
                trigger_id = client.create_trigger(trigger_data)
                if trigger_id:
                    print(f"     Created test trigger: {trigger_id}")
                    record("TC-4.1b", "Trigger Sync", "Low", "PASS",
                           f"Zabbix 5.0 trigger.create 成功: {trigger_expr[:60]}")

                    # Cleanup
                    client.delete_trigger(trigger_id)
                    print(f"     Cleaned up test trigger {trigger_id}")
                else:
                    record("TC-4.1b", "Trigger Sync", "High", "FAIL",
                           "trigger.create 返回 None",
                           "create_trigger 返回 None",
                           "检查 ZabbixClient.create_trigger() 返回值处理")
            except ZabbixAPIException as e:
                record("TC-4.1b", "Trigger Sync", "High", "FAIL",
                       "Zabbix 5.0 trigger.create 失败",
                       str(e),
                       "检查 expression 语法是否兼容 Zabbix 5.0")
        else:
            record("TC-4.1b", "Trigger Sync", "Medium", "WARN",
                   "Zabbix 中无带监控项的主机，无法测试触发器创建",
                   "",
                   "先创建主机和监控项")

        cur.close()
        conn.close()

    except Exception as e:
        record("TC-4", "Trigger Sync", "High", "FAIL",
               "触发器同步测试异常", str(e) + "\n" + traceback.format_exc()[:300])

# ---------------------------------------------------------------------------
# Test 5: Web Scenario Sync
# ---------------------------------------------------------------------------

def test_5_web_scenario_sync():
    """用例 5.1: Web 场景下发"""
    header("Test 5: Web Scenario Review & Sync")

    try:
        from config_loader import load_config, get_db_config, get_zabbix_environments
        from zabbix_mac import ZabbixClient, ZabbixAPIException
        import psycopg2
        from psycopg2.extras import DictCursor

        os.environ['ENV'] = 'local'
        config = load_config()
        db_cfg = get_db_config(config)
        envs = get_zabbix_environments(config)
        local_env = envs.get('本地Docker沙箱')

        conn = psycopg2.connect(**db_cfg)
        cur = conn.cursor(cursor_factory=DictCursor)

        # Check webscenario_items_review data
        cur.execute("SELECT COUNT(*) as cnt FROM webscenario_items_review")
        review_count = cur.fetchone()['cnt']
        print(f"     webscenario_items_review 记录数: {review_count}")

        if review_count > 0:
            cur.execute("""
                SELECT id, host, name, url, change_type, confirmed
                FROM webscenario_items_review LIMIT 3
            """)
            for ws in cur.fetchall():
                print(f"     WebScenario: {ws['name']} "
                      f"url={ws['url']} host={ws['host']} "
                      f"change={ws['change_type']}")
            record("TC-5.1a", "Web Scenario", "Low", "PASS",
                   f"webscenario_items_review 包含 {review_count} 条记录")
        else:
            record("TC-5.1a", "Web Scenario", "Medium", "WARN",
                   "webscenario_items_review 无记录",
                   "",
                   "先执行 web 场景初始化")

        client = ZabbixClient(
            url=local_env['url'],
            username=local_env['username'],
            password=local_env['password'],
            dry_run=False
        )

        # Find a host with HTTP agent for web scenario
        zabbix_hosts = client.api.host.get(output=["hostid", "host"])
        test_host_id = None
        for h in zabbix_hosts:
            test_host_id = h['hostid']
            print(f"     测试主机: {h['host']} (hostid={test_host_id})")
            break

        if test_host_id:
            ts = int(time.time())

            # Test web scenario create with STEPS (Zabbix 5.0 key feature)
            scenario_data = {
                "name": f"[INTEGRATION TEST] Web Scenario {ts}",
                "hostid": test_host_id,
                "steps": [
                    {
                        "name": f"Homepage Check {ts}",
                        "url": "http://example.com",
                        "status_codes": "200",
                        "no": 1,
                        "timeout": "15s",
                    },
                    {
                        "name": f"API Check {ts}",
                        "url": "http://example.com/api",
                        "status_codes": "200,404",  # Allow both 200 and 404
                        "no": 2,
                        "timeout": "10s",
                        "required": "http://example.com",  # Required string in response
                    },
                ],
            }

            try:
                scenario_id = client.create_web_scenario(scenario_data)
                if scenario_id:
                    print(f"     Created test web scenario: {scenario_id}")

                    # Verify with httptest.get
                    verify = client.api.httptest.get(
                        output=["httptestid", "name"],
                        httptestids=[scenario_id],
                        selectSteps="extend"
                    )
                    if verify and len(verify) > 0:
                        step_count = len(verify[0].get('steps', []))
                        print(f"     Verified: scenario has {step_count} steps")
                        record("TC-5.1b", "Web Scenario", "Low", "PASS",
                               f"Zabbix 5.0 httptest.create 成功 ({step_count} steps)")

                    # Cleanup
                    client.delete_web_scenario(scenario_id)
                    print(f"     Cleaned up test web scenario {scenario_id}")
                else:
                    record("TC-5.1b", "Web Scenario", "High", "FAIL",
                           "create_web_scenario 返回 None",
                           "",
                           "检查 ZabbixClient.create_web_scenario()")

            except ZabbixAPIException as e:
                error_msg = str(e)
                if 'tags' in error_msg.lower():
                    record("TC-5.1b", "Web Scenario", "High", "FAIL",
                           "Zabbix 5.0 httptest.create 拒绝 tags 参数",
                           error_msg,
                           "create_web_scenario() 中已有 tags 移除逻辑，检查是否生效")
                elif 'Invalid params' in error_msg:
                    record("TC-5.1b", "Web Scenario", "High", "FAIL",
                           "Zabbix 5.0 httptest.create 参数无效",
                           error_msg,
                           "检查 steps 格式、status_codes 字段名等是否兼容 Zabbix 5.0")
                else:
                    record("TC-5.1b", "Web Scenario", "High", "FAIL",
                           "Zabbix 5.0 httptest.create 失败", error_msg)

            # Test with tags (should be stripped by create_web_scenario)
            try:
                scenario_with_tags = {
                    "name": f"[INTEGRATION TEST] Web With Tags {ts+1}",
                    "hostid": test_host_id,
                    "steps": [
                        {
                            "name": f"Step 1",
                            "url": "http://example.com",
                            "status_codes": "200",
                            "no": 1,
                        }
                    ],
                    "tags": [{"tag": "env", "value": "test"}],  # Should be stripped
                }
                sid = client.create_web_scenario(scenario_with_tags)
                if sid:
                    print(f"     Created scenario with tags stripped: {sid}")
                    record("TC-5.1c", "Web Scenario", "Low", "PASS",
                           "Zabbix 5.0 httptest.create tags 自动清除成功")
                    client.delete_web_scenario(sid)
                else:
                    record("TC-5.1c", "Web Scenario", "Medium", "WARN",
                           "tags 清除后创建仍返回 None", "")
            except ZabbixAPIException as e:
                record("TC-5.1c", "Web Scenario", "High", "FAIL",
                       "Zabbix 5.0 httptest.create tags 清除失败",
                       str(e),
                       "create_web_scenario() 的 tags 移除逻辑可能未正确执行")
        else:
            record("TC-5.1", "Web Scenario", "Medium", "WARN",
                   "Zabbix 中无主机，无法测试 Web 场景下发",
                   "",
                   "在 Zabbix 中创建主机")

        cur.close()
        conn.close()

    except Exception as e:
        record("TC-5", "Web Scenario", "High", "FAIL",
               "Web 场景同步测试异常", str(e) + "\n" + traceback.format_exc()[:300])

# ---------------------------------------------------------------------------
# Test 6: End-to-End API Flow (via Flask routes)
# ---------------------------------------------------------------------------

def test_6_api_routes():
    """测试 API 路由端点"""
    header("Test 6: API Route Endpoints")

    import requests
    import re

    base_url = "http://localhost:5050"

    # Use a Session to maintain CSRF cookies across requests
    session = requests.Session()
    csrf_token = None
    try:
        resp = session.get(f"{base_url}/system-info", timeout=5)
        match = re.search(r'<meta name="csrf-token" content="([^"]+)"', resp.text)
        if match:
            csrf_token = match.group(1)
            print(f"     CSRF token obtained: {csrf_token[:8]}...")
    except Exception:
        pass

    csrf_headers = {"X-CSRF-Token": csrf_token} if csrf_token else {}

    endpoints = [
        ("GET", "/system-info", "系统信息页"),
        ("GET", "/items-review", "监控项复核页"),
        ("GET", "/triggers-review", "触发器复核页"),
        ("GET", "/webscenarios-review", "Web场景复核页"),
        ("GET", "/api/review/pending-counts", "待确认计数 API"),
    ]

    for method, path, desc in endpoints:
        try:
            if method == "GET":
                resp = session.get(f"{base_url}{path}", timeout=5)
            status = resp.status_code
            if status == 200:
                record(f"TC-6.{endpoints.index((method,path,desc))+1}", "API Routes", "Low", "PASS",
                       f"{desc} ({path}) → HTTP {status}")
            else:
                record(f"TC-6.{endpoints.index((method,path,desc))+1}", "API Routes", "Medium", "WARN",
                       f"{desc} ({path}) → HTTP {status}",
                       f"Expected 200, got {status}",
                       "检查路由注册和模板渲染")
        except requests.ConnectionError:
            record(f"TC-6.{endpoints.index((method,path,desc))+1}", "API Routes", "Medium", "WARN",
                   f"{desc} ({path}) → Connection refused",
                   f"Flask not running on port 5050",
                   "启动 Flask: APP_PORT=5050 APP_SECRET_KEY=dev-key ENV=local python3 app.py")
        except Exception as e:
            record(f"TC-6.{endpoints.index((method,path,desc))+1}", "API Routes", "Medium", "WARN",
                   f"{desc} ({path}) → Error: {str(e)[:80]}")

    # Test POST /api/sync/preview
    try:
        resp = session.post(
            f"{base_url}/api/sync/preview",
            json={
                "ids": [1],
                "table": "items_review",
                "action_type": "item",
                "environment": "本地Docker沙箱"
            },
            headers=csrf_headers,
            timeout=10
        )
        data = resp.json()
        print(f"     /api/sync/preview response: success={data.get('success')}, "
              f"status={data.get('status', 'N/A')}")

        if data.get('success') is False and data.get('message'):
            record("TC-6.6", "API Routes", "Medium", "WARN",
                   f"/api/sync/preview 返回错误: {data.get('message', '')[:100]}",
                   data.get('message', ''),
                   "检查 Zabbix 连接和主机是否存在")
        elif data.get('success'):
            record("TC-6.6", "API Routes", "Low", "PASS",
                   "/api/sync/preview 返回 success=True")
        else:
            record("TC-6.6", "API Routes", "Medium", "WARN",
                   f"/api/sync/preview 返回: {json.dumps(data, ensure_ascii=False)[:150]}")
    except requests.ConnectionError:
        record("TC-6.6", "API Routes", "Medium", "WARN",
               "/api/sync/preview → Connection refused (Flask not running)")
    except Exception as e:
        record("TC-6.6", "API Routes", "Medium", "WARN",
               f"/api/sync/preview → Error: {str(e)[:150]}")

    # Test POST /api/sync/execute with valid payload
    try:
        resp = session.post(
            f"{base_url}/api/sync/execute",
            json={
                "ids": [1],
                "action_type": "item",
                "environment": "本地Docker沙箱"
            },
            headers=csrf_headers,
            timeout=10
        )
        data = resp.json()
        print(f"     /api/sync/execute response: success={data.get('success')}, "
              f"status={data.get('status', 'N/A')}")

        if data.get('success') is False:
            msg = data.get('message', '')[:200]
            record("TC-6.7", "API Routes", "Medium", "WARN",
                   f"/api/sync/execute 返回错误: {msg}",
                   msg,
                   "根据具体错误消息分析原因")
        elif data.get('success'):
            record("TC-6.7", "API Routes", "Low", "PASS",
                   "/api/sync/execute 返回 success=True")
    except requests.ConnectionError:
        record("TC-6.7", "API Routes", "Medium", "WARN",
               "/api/sync/execute → Connection refused")
    except Exception as e:
        record("TC-6.7", "API Routes", "Medium", "WARN",
               f"/api/sync/execute → Error: {str(e)[:150]}")

# ---------------------------------------------------------------------------
# Report Generation
# ---------------------------------------------------------------------------

def generate_report():
    """生成 Markdown 缺陷报告"""
    header("缺陷与 Bug 报告")

    # Count by severity
    bugs = [r for r in RESULTS if r['status'] in ('FAIL', 'WARN')]
    passes = [r for r in RESULTS if r['status'] == 'PASS']
    high = [r for r in bugs if r['severity'] == 'High']
    medium = [r for r in bugs if r['severity'] == 'Medium']
    low = [r for r in bugs if r['severity'] == 'Low']

    print(f"""
## 📊 测试摘要

| 指标 | 数值 |
|:---|---:|
| 总测试用例数 | {len(RESULTS)} |
| ✅ 通过 | {len(passes)} |
| ❌ 失败 / ⚠️ 警告 | {len(bugs)} |
| 🔴 High | {len(high)} |
| 🟡 Medium | {len(medium)} |
| 🟢 Low | {len(low)} |
| 测试时间 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} |

---

## 🔴 缺陷列表

| Bug ID | 影响模块 | 严重程度 | 缺陷描述 & 错误堆栈 | 触发场景/用例 | 疑似原因分析及推荐修复方案 |
|:---|:---|:---|:---|:---|:---|
""")

    bug_id = 1
    for r in bugs:
        err = r['error'].replace('\n', '<br>').replace('|', '\\|')[:300]
        fix = r['fix_suggestion'].replace('\n', '<br>').replace('|', '\\|')[:200]
        print(f"| BUG-{bug_id:02d} | {r['module']} | {r['severity']} | "
              f"{r['description']} | {r['case_id']} | {fix if fix else '待分析'} |")
        if err:
            print(f"| | | | `{err}` | | |")
        bug_id += 1

    if not bugs:
        print("| — | — | — | 🎉 无缺陷发现 | — | — |")

    print(f"""
---

## ✅ 通过的测试用例 ({len(passes)})

| Case ID | Module | Description |
|:---|:---|:---|""")
    for r in passes:
        print(f"| {r['case_id']} | {r['module']} | {r['description']} |")

    print()

    # Save to file
    report_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               'INTEGRATION_TEST_REPORT.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"# Zabbix MaC 集成测试报告\n\n")
        f.write(f"**测试时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Zabbix 版本**: 5.0.x (Docker)\n")
        f.write(f"**测试环境**: ENV=local, http://localhost:8080/api_jsonrpc.php\n\n")
        f.write(f"## 摘要\n\n"
                f"- 总测试: {len(RESULTS)}\n"
                f"- 通过: {len(passes)}\n"
                f"- 缺陷/警告: {len(bugs)} (High: {len(high)}, Medium: {len(medium)}, Low: {len(low)})\n\n")
        f.write(f"详细结果请查看终端输出。\n")

    print(f"\n📄 报告已保存至: {report_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    print("""
╔══════════════════════════════════════════════════════════════════╗
║  Zabbix MaC — 本地 Zabbix 5.0 集成测试                          ║
║  ⚠️  铁律：只测试诊断，不修改任何业务代码                         ║
╚══════════════════════════════════════════════════════════════════╝
""")

    # Ensure we're in the right directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # Run all tests
    test_1_1_config_loading()
    test_1_2_zabbix_api_connectivity()
    test_2_host_sync()
    test_3_items_sync()
    test_4_trigger_sync()
    test_5_web_scenario_sync()
    test_6_api_routes()

    # Generate report
    generate_report()
