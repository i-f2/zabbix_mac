#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查 Zabbix Server 中是否存在指定主机
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
    
    # 检查 "Zabbix server" 主机是否存在
    hosts = zapi.host.get(filter={"host": "Zabbix server"}, output=["hostid", "host"])
    if hosts:
        print(f"主机 'Zabbix server' 存在，ID: {hosts[0]['hostid']}")
    else:
        print("主机 'Zabbix server' 不存在")
    
    # 检查 "Test Host 1" 主机是否存在
    hosts = zapi.host.get(filter={"host": "Test Host 1"}, output=["hostid", "host"])
    if hosts:
        print(f"主机 'Test Host 1' 存在，ID: {hosts[0]['hostid']}")
    else:
        print("主机 'Test Host 1' 不存在")
    
    zapi.logout()
except Exception as e:
    print(f"连接 Zabbix API 失败: {e}")
