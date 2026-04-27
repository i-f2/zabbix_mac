#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证 Zabbix Server 中是否成功添加了监控项、触发器和自动发现规则
"""

from pyzabbix import ZabbixAPI

# Zabbix API 连接信息
ZABBIX_URL = 'http://localhost:8080/api_jsonrpc.php'
ZABBIX_USER = 'Admin'
ZABBIX_PASS = 'zabbix'

try:
    # 连接到 Zabbix API
    zapi = ZabbixAPI(ZABBIX_URL)
    zapi.login(ZABBIX_USER, ZABBIX_PASS)
    print(f"成功连接到 Zabbix API: {ZABBIX_URL}")
    
    # 获取 Zabbix server 主机 ID
    hosts = zapi.host.get(filter={"host": "Zabbix server"}, output=["hostid"])
    if not hosts:
        print("主机 'Zabbix server' 不存在")
        exit(1)
    
    host_id = hosts[0]['hostid']
    print(f"主机 'Zabbix server' ID: {host_id}")
    
    # 检查监控项
    print("\n=== 监控项 ===")
    items = zapi.item.get(hostids=host_id, output=["name", "key_"])
    print(f"发现 {len(items)} 个监控项:")
    for item in items[:10]:  # 只显示前 10 个
        print(f"  - {item['name']} ({item['key_']})")
    if len(items) > 10:
        print(f"  ... 还有 {len(items) - 10} 个监控项")
    
    # 检查触发器
    print("\n=== 触发器 ===")
    triggers = zapi.trigger.get(hostids=host_id, output=["description"])
    print(f"发现 {len(triggers)} 个触发器:")
    for trigger in triggers:
        print(f"  - {trigger['description']}")
    
    # 检查自动发现规则
    print("\n=== 自动发现规则 ===")
    discovery_rules = zapi.discoveryrule.get(hostids=host_id, output=["name", "key_"])
    print(f"发现 {len(discovery_rules)} 个自动发现规则:")
    for rule in discovery_rules:
        print(f"  - {rule['name']} ({rule['key_']})")
    
    zapi.logout()
    print("\n验证完成！")
except Exception as e:
    print(f"连接 Zabbix API 失败: {e}")
