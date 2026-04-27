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
    
    # 获取 triggerprototype.create 方法的参数信息
    result = zapi.apiinfo.method.get(
        output=['name', 'parameters'],
        filter={'name': 'triggerprototype.create'}
    )
    
    if result:
        print("\ntriggerprototype.create 方法参数:")
        print(result[0]['parameters'])
    else:
        print("未找到 triggerprototype.create 方法")
    
    # 获取 itemprototype.create 方法的参数信息，作为参考
    result_item = zapi.apiinfo.method.get(
        output=['name', 'parameters'],
        filter={'name': 'itemprototype.create'}
    )
    
    if result_item:
        print("\nitemprototype.create 方法参数:")
        print(result_item[0]['parameters'])
    else:
        print("未找到 itemprototype.create 方法")
    
    zapi.logout()
except Exception as e:
    print(f"API 调用失败: {e}")
