#!/usr/bin/env python3
from pyzabbix import ZabbixAPI

# Zabbix API 连接信息
zabbix_url = 'http://localhost:8080/api_jsonrpc.php'
username = 'Admin'
password = 'zabbix'

try:
    # 连接到 Zabbix API
    zapi = ZabbixAPI(zabbix_url)
    zapi.login(username, password)
    print(f"成功连接到 Zabbix API，版本: {zapi.api_version()}")
    
    # 尝试创建一个简单的触发器原型
    # 首先获取一个自动发现规则的ID
    rules = zapi.discoveryrule.get(
        hostids='10084',  # Zabbix server host ID
        output=['ruleid', 'name']
    )
    
    if rules:
        rule_id = rules[0]['ruleid']
        print(f"找到自动发现规则: {rules[0]['name']}, ID: {rule_id}")
        
        # 尝试创建触发器原型
        try:
            result = zapi.triggerprototype.create(
                {
                    "description": "Test trigger prototype",
                    "expression": "{vfs.dev.read.await[{#DEVNAME}].min(15m)} > 20",
                    "priority": 3,
                    "discoveryruleid": rule_id
                }
            )
            print(f"成功创建触发器原型: {result}")
        except Exception as e:
            print(f"创建触发器原型失败: {e}")
    else:
        print("未找到自动发现规则")
    
    zapi.logout()
except Exception as e:
    print(f"API 调用失败: {e}")
