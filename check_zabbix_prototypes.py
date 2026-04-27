#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查Zabbix中自动发现规则及其原型的当前状态
"""

from pyzabbix import ZabbixAPI

# Zabbix API 配置
ZABBIX_URL = "http://localhost:8080"
ZABBIX_USERNAME = "Admin"
ZABBIX_PASSWORD = "zabbix"

try:
    # 连接到 Zabbix API
    zapi = ZabbixAPI(ZABBIX_URL)
    zapi.login(ZABBIX_USERNAME, ZABBIX_PASSWORD)
    print(f"成功连接到 Zabbix API: {ZABBIX_URL}")
    print(f"Zabbix API 版本: {zapi.api_version()}")
    
    # 获取主机 ID
    hosts = zapi.host.get(filter={"host": "Zabbix server"}, output=["hostid"])
    if not hosts:
        print("未找到主机 'Zabbix server'")
        exit(1)
    host_id = hosts[0]["hostid"]
    print(f"主机 'Zabbix server' 的 ID: {host_id}")
    
    # 获取自动发现规则
    rules = zapi.discoveryrule.get(
        hostids=host_id,
        output=["ruleid", "name", "key_"]
    )
    print(f"\n发现 {len(rules)} 个自动发现规则:")
    print(f"规则原始数据: {rules}")
    for rule in rules:
        print(f"规则详情: {rule}")
        # 尝试获取 ruleid 或 itemid
        rule_id = rule.get("ruleid") or rule.get("itemid")
        rule_name = rule.get("name")
        rule_key = rule.get("key_")
        print(f"  - {rule_name} (ID: {rule_id}, Key: {rule_key})")
        
        if rule_id:
            # 获取监控项原型
            try:
                item_prototypes = zapi.itemprototype.get(
                    discoveryids=rule_id,
                    output=["name", "key_"]
                )
                print(f"    监控项原型 ({len(item_prototypes)}):")
                for proto in item_prototypes:
                    print(f"      - {proto['name']} (Key: {proto['key_']})")
            except Exception as e:
                print(f"    获取监控项原型失败: {e}")
            
            # 获取触发器原型
            try:
                trigger_prototypes = zapi.triggerprototype.get(
                    discoveryids=rule_id,
                    output=["description"]
                )
                print(f"    触发器原型 ({len(trigger_prototypes)}):")
                for proto in trigger_prototypes:
                    print(f"      - {proto['description']}")
            except Exception as e:
                print(f"    获取触发器原型失败: {e}")
    
    zapi.logout()
    print("\n检查完成！")
except Exception as e:
    print(f"连接 Zabbix API 失败: {e}")
