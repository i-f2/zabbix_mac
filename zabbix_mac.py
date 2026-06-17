#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Zabbix Monitor as Code (MaC) 自动化系统

基于 Python 3 的自动化工具，通过调用 Zabbix 5.0 API，实现监控项（Items）、触发器（Triggers）及自动发现规则（LLD）的声明式同步。
"""

import argparse
import hashlib
import json
import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Any, Set, Tuple

import yaml
import psycopg2
from psycopg2.extras import DictCursor
from pyzabbix import ZabbixAPI, ZabbixAPIException
import pandas as pd

# 配置日志系统
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('zabbix_mac')

# 管理标签
MANAGED_TAG = {"tag": "ManagedBy", "value": "PythonScript"}

# 全局变量
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY = 2  # 秒


class ZabbixClient:
    """Zabbix API 客户端封装"""
    
    def __init__(self, url: str, username: str, password: str, dry_run: bool = False):
        """初始化 Zabbix 客户端
        
        Args:
            url: Zabbix API URL
            username: 用户名
            password: 密码
            dry_run: 是否模拟运行
        """
        self.url = url
        self.username = username
        self.password = password
        self.api = None
        self.dry_run = dry_run
        # 只有在提供了 URL、用户名和密码时才连接
        if url and username and password and not dry_run:
            self._connect()
    
    def _connect(self):
        """建立 API 连接"""
        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                self.api = ZabbixAPI(self.url)
                self.api.login(self.username, self.password)
                logger.info(f"成功连接到 Zabbix API: {self.url}")
                return
            except ZabbixAPIException as e:
                logger.error(f"连接 Zabbix API 失败 (尝试 {attempt+1}/{MAX_RETRY_ATTEMPTS}): {e}")
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    logger.info(f"{RETRY_DELAY} 秒后重试...")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error("达到最大重试次数，连接失败")
                    raise
            except Exception as e:
                logger.error(f"连接 Zabbix API 时发生未知错误: {e}")
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    logger.info(f"{RETRY_DELAY} 秒后重试...")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error("达到最大重试次数，连接失败")
                    raise
    
    def get_host_id(self, host_name: str) -> Optional[str]:
        """获取主机 ID
        
        Args:
            host_name: 主机名
            
        Returns:
            主机 ID 或 None
        """
        if self.dry_run:
            logger.info(f"[模拟] 获取主机 {host_name} 的 ID")
            return "12345"  # 模拟返回一个主机 ID
        
        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                hosts = self.api.host.get(filter={"host": host_name}, output=["hostid"])
                if hosts:
                    logger.info(f"成功获取主机 {host_name} 的 ID: {hosts[0]['hostid']}")
                    return hosts[0]["hostid"]
                logger.warning(f"主机 {host_name} 不存在")
                return None
            except ZabbixAPIException as e:
                logger.error(f"获取主机 ID 失败 (尝试 {attempt+1}/{MAX_RETRY_ATTEMPTS}): {e}")
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    logger.info(f"{RETRY_DELAY} 秒后重试...")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error("达到最大重试次数，获取主机 ID 失败")
                    return None
            except Exception as e:
                logger.error(f"获取主机 ID 时发生未知错误: {e}")
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    logger.info(f"{RETRY_DELAY} 秒后重试...")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error("达到最大重试次数，获取主机 ID 失败")
                    return None
    
    def get_host_interface_id(self, host_id: str) -> Optional[str]:
        """获取主机的第一个 Zabbix agent 接口 ID
        
        Args:
            host_id: 主机 ID
            
        Returns:
            接口 ID 或 None
        """
        if self.dry_run:
            logger.info(f"[模拟] 获取主机 {host_id} 的接口 ID")
            return "67890"  # 模拟返回一个接口 ID
        
        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                # 先尝试获取 Zabbix agent 接口
                interfaces = self.api.hostinterface.get(
                    hostids=host_id,
                    output=["interfaceid", "type"]
                )
                
                # 优先选择 Zabbix agent 接口 (type=1)
                for interface in interfaces:
                    if interface.get("type") == "1":
                        logger.info(f"找到 Zabbix agent 接口: {interface['interfaceid']}")
                        return interface["interfaceid"]
                
                # 如果没有 Zabbix agent 接口，使用第一个可用接口
                if interfaces:
                    logger.info(f"使用第一个可用接口: {interfaces[0]['interfaceid']}")
                    return interfaces[0]["interfaceid"]
                
                logger.error(f"主机 {host_id} 没有可用的接口")
                return None
            except ZabbixAPIException as e:
                logger.error(f"获取主机接口失败 (尝试 {attempt+1}/{MAX_RETRY_ATTEMPTS}): {e}")
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    logger.info(f"{RETRY_DELAY} 秒后重试...")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error("达到最大重试次数，获取主机接口失败")
                    return None
            except Exception as e:
                logger.error(f"获取主机接口时发生未知错误: {e}")
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    logger.info(f"{RETRY_DELAY} 秒后重试...")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error("达到最大重试次数，获取主机接口失败")
                    return None
    
    def calculate_fingerprint(self, obj: Dict[str, Any]) -> str:
        """计算对象的 MD5 指纹
        
        Args:
            obj: 要计算指纹的对象
            
        Returns:
            MD5 指纹
        """
        # 排除不参与比对的字段
        exclude_keys = ["itemid", "hostid", "triggerid", "ruleid", "prototypeid", "created", "lastclock", "httptestid", "templateid", "nextcheck"]
        filtered_obj = {k: v for k, v in obj.items() if k not in exclude_keys}
        # 排序键以确保一致性
        sorted_obj = json.dumps(filtered_obj, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(sorted_obj.encode()).hexdigest()
    
    def get_managed_items(self, host_id: str) -> List[Dict[str, Any]]:
        """获取主机的所有监控项
        
        Args:
            host_id: 主机 ID
            
        Returns:
            监控项列表
        """
        if self.dry_run:
            logger.info(f"[模拟] 获取主机 {host_id} 的监控项")
            return []  # 模拟返回空列表
        
        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                items = self.api.item.get(
                    hostids=host_id,
                    output="extend"
                )
                # 过滤掉模板继承的监控项（templateid != "0"），只保留主机自有监控项
                # 模板继承的监控项无法在主机级别删除，必须排除以避免删除时报错
                owned_items = [item for item in items if item.get("templateid") == "0"]
                logger.info(f"成功获取主机 {host_id} 的 {len(items)} 个监控项（其中 {len(owned_items)} 个为自有监控项）")
                return owned_items
            except ZabbixAPIException as e:
                logger.error(f"获取监控项失败 (尝试 {attempt+1}/{MAX_RETRY_ATTEMPTS}): {e}")
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    logger.info(f"{RETRY_DELAY} 秒后重试...")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error("达到最大重试次数，获取监控项失败")
                    return []
            except Exception as e:
                logger.error(f"获取监控项时发生未知错误: {e}")
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    logger.info(f"{RETRY_DELAY} 秒后重试...")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error("达到最大重试次数，获取监控项失败")
                    return []
    
    def create_item(self, item_data: Dict[str, Any]) -> Optional[str]:
        """创建监控项
        
        Args:
            item_data: 监控项数据
            
        Returns:
            监控项 ID 或 None
        """
        if self.dry_run:
            logger.info(f"[模拟] 创建监控项: {item_data.get('key_')}")
            return "98765"  # 模拟返回一个监控项 ID
        
        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                # 在 Zabbix 5.0 中，监控项没有标签功能，不添加管理标签
                result = self.api.item.create(item_data)
                item_id = result["itemids"][0]
                logger.info(f"成功创建监控项: {item_data.get('key_')} (ID: {item_id})")
                return item_id
            except ZabbixAPIException as e:
                logger.error(f"创建监控项失败 (尝试 {attempt+1}/{MAX_RETRY_ATTEMPTS}): {e}")
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    logger.info(f"{RETRY_DELAY} 秒后重试...")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error("达到最大重试次数，创建监控项失败")
                    return None
            except Exception as e:
                logger.error(f"创建监控项时发生未知错误: {e}")
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    logger.info(f"{RETRY_DELAY} 秒后重试...")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error("达到最大重试次数，创建监控项失败")
                    return None
    
    def update_item(self, item_id: str, item_data: Dict[str, Any]) -> bool:
        """更新监控项
        
        Args:
            item_id: 监控项 ID
            item_data: 监控项数据
            
        Returns:
            是否成功
        """
        if self.dry_run:
            logger.info(f"[模拟] 更新监控项: {item_data.get('key_')} (ID: {item_id})")
            return True  # 模拟更新成功
        
        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                # 在 Zabbix 5.0 中，监控项没有标签功能，不添加管理标签
                item_data["itemid"] = item_id
                self.api.item.update(item_data)
                logger.info(f"成功更新监控项: {item_data.get('key_')} (ID: {item_id})")
                return True
            except ZabbixAPIException as e:
                logger.error(f"更新监控项失败 (尝试 {attempt+1}/{MAX_RETRY_ATTEMPTS}): {e}")
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    logger.info(f"{RETRY_DELAY} 秒后重试...")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error("达到最大重试次数，更新监控项失败")
                    return False
            except Exception as e:
                logger.error(f"更新监控项时发生未知错误: {e}")
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    logger.info(f"{RETRY_DELAY} 秒后重试...")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error("达到最大重试次数，更新监控项失败")
                    return False
    
    def delete_item(self, item_id: str) -> bool:
        """删除监控项
        
        Args:
            item_id: 监控项 ID
            
        Returns:
            是否成功
        """
        if self.dry_run:
            logger.info(f"[模拟] 删除监控项 (ID: {item_id})")
            return True  # 模拟删除成功
        
        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                self.api.item.delete([item_id])
                logger.info(f"成功删除监控项 (ID: {item_id})")
                return True
            except ZabbixAPIException as e:
                logger.error(f"删除监控项失败 (尝试 {attempt+1}/{MAX_RETRY_ATTEMPTS}): {e}")
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    logger.info(f"{RETRY_DELAY} 秒后重试...")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error("达到最大重试次数，删除监控项失败")
                    return False
            except Exception as e:
                logger.error(f"删除监控项时发生未知错误: {e}")
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    logger.info(f"{RETRY_DELAY} 秒后重试...")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error("达到最大重试次数，删除监控项失败")
                    return False
    
    def get_managed_triggers(self, host_id: str) -> List[Dict[str, Any]]:
        """获取主机的所有受管理触发器
        
        Args:
            host_id: 主机 ID
            
        Returns:
            触发器列表
        """
        if self.dry_run:
            logger.info(f"[模拟] 获取主机 {host_id} 的受管理触发器")
            return []  # 模拟返回空列表
        
        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                triggers = self.api.trigger.get(
                    hostids=host_id,
                    output="extend"
                )
                # 过滤出带有管理标签的触发器
                managed_triggers = []
                for trigger in triggers:
                    tags = trigger.get("tags", [])
                    # 检查是否有管理标签
                    if any(
                        tag.get("tag") == MANAGED_TAG["tag"] and tag.get("value") == MANAGED_TAG["value"]
                        for tag in tags
                    ):
                        managed_triggers.append(trigger)
                logger.info(f"成功获取主机 {host_id} 的 {len(managed_triggers)} 个受管理触发器")
                return managed_triggers
            except ZabbixAPIException as e:
                logger.error(f"获取触发器失败 (尝试 {attempt+1}/{MAX_RETRY_ATTEMPTS}): {e}")
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    logger.info(f"{RETRY_DELAY} 秒后重试...")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error("达到最大重试次数，获取触发器失败")
                    return []
            except Exception as e:
                logger.error(f"获取触发器时发生未知错误: {e}")
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    logger.info(f"{RETRY_DELAY} 秒后重试...")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error("达到最大重试次数，获取触发器失败")
                    return []
    
    def create_trigger(self, trigger_data: Dict[str, Any]) -> Optional[str]:
        """创建触发器
        
        Args:
            trigger_data: 触发器数据
            
        Returns:
            触发器 ID 或 None
        """
        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                # 添加管理标签
                if "tags" not in trigger_data:
                    trigger_data["tags"] = []
                trigger_data["tags"].append(MANAGED_TAG)
                
                result = self.api.trigger.create(trigger_data)
                trigger_id = result["triggerids"][0]
                logger.info(f"成功创建触发器: {trigger_data.get('description')} (ID: {trigger_id})")
                return trigger_id
            except ZabbixAPIException as e:
                logger.error(f"创建触发器失败 (尝试 {attempt+1}/{MAX_RETRY_ATTEMPTS}): {e}")
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    logger.info(f"{RETRY_DELAY} 秒后重试...")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error("达到最大重试次数，创建触发器失败")
                    return None
            except Exception as e:
                logger.error(f"创建触发器时发生未知错误: {e}")
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    logger.info(f"{RETRY_DELAY} 秒后重试...")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error("达到最大重试次数，创建触发器失败")
                    return None
    
    def update_trigger(self, trigger_id: str, trigger_data: Dict[str, Any]) -> bool:
        """更新触发器
        
        Args:
            trigger_id: 触发器 ID
            trigger_data: 触发器数据
            
        Returns:
            是否成功
        """
        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                # 添加管理标签
                if "tags" not in trigger_data:
                    trigger_data["tags"] = []
                trigger_data["tags"].append(MANAGED_TAG)
                
                trigger_data["triggerid"] = trigger_id
                self.api.trigger.update(trigger_data)
                logger.info(f"成功更新触发器: {trigger_data.get('description')} (ID: {trigger_id})")
                return True
            except ZabbixAPIException as e:
                logger.error(f"更新触发器失败 (尝试 {attempt+1}/{MAX_RETRY_ATTEMPTS}): {e}")
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    logger.info(f"{RETRY_DELAY} 秒后重试...")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error("达到最大重试次数，更新触发器失败")
                    return False
            except Exception as e:
                logger.error(f"更新触发器时发生未知错误: {e}")
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    logger.info(f"{RETRY_DELAY} 秒后重试...")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error("达到最大重试次数，更新触发器失败")
                    return False
    
    def get_managed_discovery_rules(self, host_id: str) -> List[Dict[str, Any]]:
        """获取主机的所有受管理自动发现规则
        
        Args:
            host_id: 主机 ID
            
        Returns:
            自动发现规则列表
        """
        if self.dry_run:
            logger.info(f"[模拟] 获取主机 {host_id} 的受管理自动发现规则")
            return []  # 模拟返回空列表
        
        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                rules = self.api.discoveryrule.get(
                    hostids=host_id,
                    output="extend"
                )
                # 在 Zabbix 5.0 中，自动发现规则可能没有标签功能，返回所有规则
                logger.info(f"成功获取主机 {host_id} 的 {len(rules)} 个自动发现规则")
                return rules
            except ZabbixAPIException as e:
                logger.error(f"获取自动发现规则失败 (尝试 {attempt+1}/{MAX_RETRY_ATTEMPTS}): {e}")
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    logger.info(f"{RETRY_DELAY} 秒后重试...")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error("达到最大重试次数，获取自动发现规则失败")
                    return []
            except Exception as e:
                logger.error(f"获取自动发现规则时发生未知错误: {e}")
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    logger.info(f"{RETRY_DELAY} 秒后重试...")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error("达到最大重试次数，获取自动发现规则失败")
                    return []
    
    def create_discovery_rule(self, rule_data: Dict[str, Any]) -> Optional[str]:
        """创建自动发现规则
        
        Args:
            rule_data: 自动发现规则数据
            
        Returns:
            规则 ID 或 None
        """
        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                # 添加管理标签
                if "tags" not in rule_data:
                    rule_data["tags"] = []
                rule_data["tags"].append(MANAGED_TAG)
                
                result = self.api.discoveryrule.create(rule_data)
                # 检查 result 是否包含 ruleids 键
                if "ruleids" in result and result["ruleids"]:
                    rule_id = result["ruleids"][0]
                    logger.info(f"成功创建自动发现规则: {rule_data.get('name')} (ID: {rule_id})")
                    return rule_id
                # 检查 result 是否包含 itemids 键（某些 Zabbix 版本可能返回这个）
                elif "itemids" in result and result["itemids"]:
                    rule_id = result["itemids"][0]
                    logger.warning(f"API 返回了 itemids 而不是 ruleids: {result}")
                    logger.info(f"成功创建自动发现规则: {rule_data.get('name')} (ID: {rule_id})")
                    return rule_id
                else:
                    logger.error(f"创建自动发现规则失败: API 返回结果中没有 ruleids 或 itemids 键: {result}")
                    if attempt < MAX_RETRY_ATTEMPTS - 1:
                        logger.info(f"{RETRY_DELAY} 秒后重试...")
                        time.sleep(RETRY_DELAY)
                    else:
                        logger.error("达到最大重试次数，创建自动发现规则失败")
                        return None
            except ZabbixAPIException as e:
                logger.error(f"创建自动发现规则失败 (尝试 {attempt+1}/{MAX_RETRY_ATTEMPTS}): {e}")
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    logger.info(f"{RETRY_DELAY} 秒后重试...")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error("达到最大重试次数，创建自动发现规则失败")
                    return None
            except Exception as e:
                logger.error(f"创建自动发现规则时发生未知错误: {e}")
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    logger.info(f"{RETRY_DELAY} 秒后重试...")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error("达到最大重试次数，创建自动发现规则失败")
                    return None
    
    def update_discovery_rule(self, rule_id: str, rule_data: Dict[str, Any]) -> bool:
        """更新自动发现规则
        
        Args:
            rule_id: 规则 ID
            rule_data: 规则数据
            
        Returns:
            是否成功
        """
        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                # 添加管理标签
                if "tags" not in rule_data:
                    rule_data["tags"] = []
                rule_data["tags"].append(MANAGED_TAG)
                
                rule_data["ruleid"] = rule_id
                self.api.discoveryrule.update(rule_data)
                logger.info(f"成功更新自动发现规则: {rule_data.get('name')} (ID: {rule_id})")
                return True
            except ZabbixAPIException as e:
                logger.error(f"更新自动发现规则失败 (尝试 {attempt+1}/{MAX_RETRY_ATTEMPTS}): {e}")
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    logger.info(f"{RETRY_DELAY} 秒后重试...")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error("达到最大重试次数，更新自动发现规则失败")
                    return False
            except Exception as e:
                logger.error(f"更新自动发现规则时发生未知错误: {e}")
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    logger.info(f"{RETRY_DELAY} 秒后重试...")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error("达到最大重试次数，更新自动发现规则失败")
                    return False
    
    def get_item_prototypes(self, rule_id: str) -> List[Dict[str, Any]]:
        """获取自动发现规则的监控项原型
        
        Args:
            rule_id: 规则 ID
            
        Returns:
            监控项原型列表
        """
        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                prototypes = self.api.itemprototype.get(
                    discoveryids=rule_id,
                    output="extend"
                )
                logger.info(f"成功获取规则 {rule_id} 的 {len(prototypes)} 个监控项原型")
                return prototypes
            except ZabbixAPIException as e:
                logger.error(f"获取监控项原型失败 (尝试 {attempt+1}/{MAX_RETRY_ATTEMPTS}): {e}")
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    logger.info(f"{RETRY_DELAY} 秒后重试...")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error("达到最大重试次数，获取监控项原型失败")
                    return []
            except Exception as e:
                logger.error(f"获取监控项原型时发生未知错误: {e}")
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    logger.info(f"{RETRY_DELAY} 秒后重试...")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error("达到最大重试次数，获取监控项原型失败")
                    return []
    
    def create_item_prototype(self, prototype_data: Dict[str, Any]) -> Optional[str]:
        """创建监控项原型
        
        Args:
            prototype_data: 监控项原型数据
            
        Returns:
            原型 ID 或 None
        """
        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                # 添加管理标签
                if "tags" not in prototype_data:
                    prototype_data["tags"] = []
                prototype_data["tags"].append(MANAGED_TAG)
                
                result = self.api.itemprototype.create(prototype_data)
                prototype_id = result["itemids"][0]
                logger.info(f"成功创建监控项原型: {prototype_data.get('name')} (ID: {prototype_id})")
                return prototype_id
            except ZabbixAPIException as e:
                logger.error(f"创建监控项原型失败 (尝试 {attempt+1}/{MAX_RETRY_ATTEMPTS}): {e}")
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    logger.info(f"{RETRY_DELAY} 秒后重试...")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error("达到最大重试次数，创建监控项原型失败")
                    return None
            except Exception as e:
                logger.error(f"创建监控项原型时发生未知错误: {e}")
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    logger.info(f"{RETRY_DELAY} 秒后重试...")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error("达到最大重试次数，创建监控项原型失败")
                    return None
    
    def get_trigger_prototypes(self, rule_id: str) -> List[Dict[str, Any]]:
        """获取自动发现规则的触发器原型
        
        Args:
            rule_id: 规则 ID
            
        Returns:
            触发器原型列表
        """
        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                prototypes = self.api.triggerprototype.get(
                    discoveryids=rule_id,
                    output="extend"
                )
                logger.info(f"成功获取规则 {rule_id} 的 {len(prototypes)} 个触发器原型")
                return prototypes
            except ZabbixAPIException as e:
                logger.error(f"获取触发器原型失败 (尝试 {attempt+1}/{MAX_RETRY_ATTEMPTS}): {e}")
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    logger.info(f"{RETRY_DELAY} 秒后重试...")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error("达到最大重试次数，获取触发器原型失败")
                    return []
            except Exception as e:
                logger.error(f"获取触发器原型时发生未知错误: {e}")
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    logger.info(f"{RETRY_DELAY} 秒后重试...")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error("达到最大重试次数，获取触发器原型失败")
                    return []
    
    def get_managed_web_scenarios(self, host_id: str) -> List[Dict[str, Any]]:
        """获取主机的所有受管理 web 场景
        
        Args:
            host_id: 主机 ID
            
        Returns:
            web 场景列表
        """
        if self.dry_run:
            logger.info(f"[模拟] 获取主机 {host_id} 的受管理 web 场景")
            return []  # 模拟返回空列表
        
        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                scenarios = self.api.httptest.get(
                    hostids=host_id,
                    output="extend",
                    selectSteps="extend"
                )
                # 过滤出带有管理标签的 web 场景
                managed_scenarios = []
                for scenario in scenarios:
                    tags = scenario.get("tags", [])
                    # 检查是否有管理标签
                    if any(
                        tag.get("tag") == MANAGED_TAG["tag"] and tag.get("value") == MANAGED_TAG["value"]
                        for tag in tags
                    ):
                        managed_scenarios.append(scenario)
                logger.info(f"成功获取主机 {host_id} 的 {len(managed_scenarios)} 个受管理 web 场景")
                return managed_scenarios
            except ZabbixAPIException as e:
                logger.error(f"获取 web 场景失败 (尝试 {attempt+1}/{MAX_RETRY_ATTEMPTS}): {e}")
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    logger.info(f"{RETRY_DELAY} 秒后重试...")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error("达到最大重试次数，获取 web 场景失败")
                    return []
            except Exception as e:
                logger.error(f"获取 web 场景时发生未知错误: {e}")
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    logger.info(f"{RETRY_DELAY} 秒后重试...")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error("达到最大重试次数，获取 web 场景失败")
                    return []
    
    def create_web_scenario(self, scenario_data: Dict[str, Any]) -> Optional[str]:
        """创建 web 场景
        
        Args:
            scenario_data: web 场景数据
            
        Returns:
            web 场景 ID 或 None
        """
        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                # 注意：Zabbix 5.0 API 不支持 web 场景的 tags 参数
                # 移除可能存在的 tags 参数
                if "tags" in scenario_data:
                    del scenario_data["tags"]
                
                result = self.api.httptest.create(scenario_data)
                if "httptestids" in result and result["httptestids"]:
                    scenario_id = result["httptestids"][0]
                    logger.info(f"成功创建 web 场景: {scenario_data.get('name')} (ID: {scenario_id})")
                    return scenario_id
                else:
                    logger.error(f"创建 web 场景失败: API 返回结果中没有 httptestids 键: {result}")
                    if attempt < MAX_RETRY_ATTEMPTS - 1:
                        logger.info(f"{RETRY_DELAY} 秒后重试...")
                        time.sleep(RETRY_DELAY)
                    else:
                        logger.error("达到最大重试次数，创建 web 场景失败")
                        return None
            except ZabbixAPIException as e:
                logger.error(f"创建 web 场景失败 (尝试 {attempt+1}/{MAX_RETRY_ATTEMPTS}): {e}")
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    logger.info(f"{RETRY_DELAY} 秒后重试...")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error("达到最大重试次数，创建 web 场景失败")
                    return None
            except Exception as e:
                logger.error(f"创建 web 场景时发生未知错误: {e}")
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    logger.info(f"{RETRY_DELAY} 秒后重试...")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error("达到最大重试次数，创建 web 场景失败")
                    return None
    
    def update_web_scenario(self, scenario_id: str, scenario_data: Dict[str, Any]) -> bool:
        """更新 web 场景
        
        Args:
            scenario_id: web 场景 ID
            scenario_data: web 场景数据
            
        Returns:
            是否成功
        """
        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                # 添加管理标签
                if "tags" not in scenario_data:
                    scenario_data["tags"] = []
                scenario_data["tags"].append(MANAGED_TAG)
                
                scenario_data["httptestid"] = scenario_id
                self.api.httptest.update(scenario_data)
                logger.info(f"成功更新 web 场景: {scenario_data.get('name')} (ID: {scenario_id})")
                return True
            except ZabbixAPIException as e:
                logger.error(f"更新 web 场景失败 (尝试 {attempt+1}/{MAX_RETRY_ATTEMPTS}): {e}")
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    logger.info(f"{RETRY_DELAY} 秒后重试...")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error("达到最大重试次数，更新 web 场景失败")
                    return False
            except Exception as e:
                logger.error(f"更新 web 场景时发生未知错误: {e}")
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    logger.info(f"{RETRY_DELAY} 秒后重试...")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error("达到最大重试次数，更新 web 场景失败")
                    return False
    
    def delete_web_scenario(self, scenario_id: str) -> bool:
        """删除 web 场景
        
        Args:
            scenario_id: web 场景 ID
            
        Returns:
            是否成功
        """
        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                self.api.httptest.delete([scenario_id])
                logger.info(f"成功删除 web 场景 (ID: {scenario_id})")
                return True
            except ZabbixAPIException as e:
                logger.error(f"删除 web 场景失败 (尝试 {attempt+1}/{MAX_RETRY_ATTEMPTS}): {e}")
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    logger.info(f"{RETRY_DELAY} 秒后重试...")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error("达到最大重试次数，删除 web 场景失败")
                    return False
            except Exception as e:
                logger.error(f"删除 web 场景时发生未知错误: {e}")
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    logger.info(f"{RETRY_DELAY} 秒后重试...")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error("达到最大重试次数，删除 web 场景失败")
                    return False
    
    def create_trigger_prototype(self, prototype_data: Dict[str, Any]) -> Optional[str]:
        """创建触发器原型
        
        Args:
            prototype_data: 触发器原型数据
            
        Returns:
            原型 ID 或 None
        """
        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                # 添加管理标签
                if "tags" not in prototype_data:
                    prototype_data["tags"] = []
                prototype_data["tags"].append(MANAGED_TAG)
                
                # 直接使用完整的prototype_data创建，包含discoveryruleid
                result = self.api.triggerprototype.create(prototype_data)
                
                prototype_id = result["triggerids"][0]
                logger.info(f"成功创建触发器原型: {prototype_data.get('description')} (ID: {prototype_id})")
                return prototype_id
            except ZabbixAPIException as e:
                logger.error(f"创建触发器原型失败 (尝试 {attempt+1}/{MAX_RETRY_ATTEMPTS}): {e}")
                logger.debug(f"失败的原型数据: {prototype_data}")
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    logger.info(f"{RETRY_DELAY} 秒后重试...")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error("达到最大重试次数，创建触发器原型失败")
                    return None
            except Exception as e:
                logger.error(f"创建触发器原型时发生未知错误: {e}")
                logger.debug(f"失败的原型数据: {prototype_data}")
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    logger.info(f"{RETRY_DELAY} 秒后重试...")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error("达到最大重试次数，创建触发器原型失败")
                    return None


class ConfigLoader:
    """配置加载器"""
    
    def __init__(self, db_config: Optional[Dict[str, Any]] = None):
        """初始化配置加载器
        
        Args:
            db_config: 数据库配置
        """
        self.db_config = db_config
        self.connection = None
    
    def connect_db(self):
        """连接数据库
        
        Returns:
            bool: 连接是否成功
        """
        if not self.db_config:
            logger.error("数据库配置未提供")
            return False
        
        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                # 构建连接参数
                conn_params = {
                    'host': self.db_config.get('host', 'localhost'),
                    'port': self.db_config.get('port', 5432),
                    'database': self.db_config.get('database', 'zabbix_mac'),
                    'user': self.db_config.get('user', 'fan'),
                    'password': self.db_config.get('password', '')
                }
                
                logger.debug(f"尝试连接数据库 (尝试 {attempt+1}/{MAX_RETRY_ATTEMPTS}): {conn_params['host']}:{conn_params['port']}/{conn_params['database']}")
                self.connection = psycopg2.connect(**conn_params)
                # 设置连接参数
                self.connection.autocommit = True
                # 设置客户端编码为 UTF-8，以正确处理中文字符
                self.connection.set_client_encoding('UTF8')
                logger.info("成功连接到 PostgreSQL 数据库")
                return True
            except psycopg2.OperationalError as e:
                logger.error(f"数据库连接失败 (尝试 {attempt+1}/{MAX_RETRY_ATTEMPTS}): {e}")
                logger.debug(f"连接参数: {conn_params}")
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    logger.info(f"{RETRY_DELAY} 秒后重试...")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error("达到最大重试次数，数据库连接失败")
                    return False
            except Exception as e:
                logger.error(f"连接数据库时发生未知错误 (尝试 {attempt+1}/{MAX_RETRY_ATTEMPTS}): {e}")
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    logger.info(f"{RETRY_DELAY} 秒后重试...")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error("达到最大重试次数，数据库连接失败")
                    return False
    
    def reset_connection(self):
        """重置数据库连接"""
        try:
            if self.connection:
                logger.info("关闭现有数据库连接")
                self.connection.close()
                self.connection = None
            logger.info("正在重置数据库连接...")
            return self.connect_db()
        except Exception as e:
            logger.error(f"重置数据库连接失败: {e}")
            return False
    
    def load_config(self) -> Dict[str, Any]:
        """从数据库加载配置
        
        Returns:
            配置字典
        """
        # 从数据库加载配置
        if self.db_config:
            logger.info("尝试从数据库加载配置...")
            config = self.load_config_from_db()
            if config:
                logger.info("成功从数据库加载配置")
                return config
            logger.error("从数据库加载配置失败")
        else:
            logger.error("数据库配置未提供")
        return {}
    
    def load_config_from_db(self) -> Dict[str, Any]:
        """从数据库加载配置
        
        Returns:
            配置字典
        """
        if not self.connection:
            if not self.connect_db():
                return {}
        
        config = {"hosts": {}}
        
        try:
            # 加载主机配置
            logger.info("从数据库加载主机配置...")
            with self.connection.cursor(cursor_factory=DictCursor) as cur:
                cur.execute("""
                    SELECT name, description, template_name
                    FROM hosts
                    WHERE template_name IS NOT NULL AND template_name != ''
                """)
                
                host_templates = {}
                rows = cur.fetchall()
                logger.info(f"获取到 {len(rows)} 条主机模板关联记录")
                
                for row in rows:
                    host_name = row['name']
                    template_name = row['template_name']
                    
                    if host_name not in host_templates:
                        host_templates[host_name] = {
                            "description": row['description'],
                            "templates": []
                        }
                    
                    host_templates[host_name]["templates"].append(template_name)
                
                # 加载主机的额外监控项
                logger.info(f"加载 {len(host_templates)} 台主机的额外监控项...")
                for host_name in host_templates:
                    with self.connection.cursor(cursor_factory=DictCursor) as cur2:
                        cur2.execute(
                            'SELECT item_key, name, type, value_type, delay, description, units, multiplier, delta, history, trends, status FROM host_extra_items WHERE host_name = %s',
                            (host_name,)
                        )
                        
                        extra_items = {}
                        items_rows = cur2.fetchall()
                        logger.info(f"主机 {host_name} 有 {len(items_rows)} 个额外监控项")
                        
                        for row in items_rows:
                            item_config = {
                                "name": row['name'],
                                "type": row['type'],
                                "value_type": row['value_type'],
                                "delay": row['delay'],
                            }
                            
                            if row['description']:
                                item_config['description'] = row['description']
                            if row['units']:
                                item_config['units'] = row['units']
                            if row['multiplier']:
                                item_config['multiplier'] = row['multiplier']
                            if row['delta']:
                                item_config['delta'] = row['delta']
                            if row['history']:
                                item_config['history'] = row['history']
                            if row['trends']:
                                item_config['trends'] = row['trends']
                            if row['status']:
                                item_config['status'] = row['status']
                            
                            extra_items[row['item_key']] = item_config
                        
                        if extra_items:
                            host_templates[host_name]["extra_items"] = extra_items
                
                config["hosts"] = host_templates
                logger.info(f"成功从数据库加载配置，包含 {len(host_templates)} 台主机")
                return config
        except psycopg2.OperationalError as e:
            logger.error(f"数据库操作失败: {e}")
            # 重置连接以解决连接问题
            self.reset_connection()
            return {}
        except Exception as e:
            logger.error(f"从数据库加载配置失败: {e}")
            # 重置连接以解决事务中止问题
            self.reset_connection()
            return {}
    
    def load_template_from_db(self, template_name: str) -> Dict[str, Any]:
        """从数据库加载模板
        
        Args:
            template_name: 模板名称
            
        Returns:
            模板字典
        """
        if not self.connection:
            if not self.connect_db():
                return {}
        
        template = {
            "items": {},
            "triggers": {},
            "discovery_rules": []
        }
        
        try:
            # 加载监控项（从复核表）
            logger.info(f"从数据库加载模板 {template_name} 的监控项...")
            with self.connection.cursor(cursor_factory=DictCursor) as cur:
                cur.execute("""
                    SELECT ir.item_key, ir.name, ir.type, ir.value_type, ir.delay, ir.description, ir.units,
                           ir.multiplier, ir.delta, ir.history, ir.trends, ir.status, ir.master_item, ir.preprocessing
                    FROM items_review ir
                    WHERE ir.template_name = %s AND ir.confirmed = true
                    LIMIT 100
                """, (template_name,))
                
                items_rows = cur.fetchall()
                logger.info(f"从复核表获取到 {len(items_rows)} 个监控项")
                
                # 如果复核表中没有确认的记录，从原始表加载
                if len(items_rows) == 0:
                    logger.info(f"复核表中没有确认的记录，从原始表加载监控项...")
                    with self.connection.cursor(cursor_factory=DictCursor) as cur2:
                        cur2.execute("""
                            SELECT item_key, name, type, value_type, delay, description, units,
                                   multiplier, delta, history, trends, status, master_item, preprocessing
                            FROM items
                            WHERE template_name = %s
                            LIMIT 100
                        """, (template_name,))
                        
                        items_rows = cur2.fetchall()
                        logger.info(f"从原始表获取到 {len(items_rows)} 个监控项")
                
                for row in items_rows:
                    item_config = {
                        "name": row['name'],
                        "type": row['type'],
                        "value_type": row['value_type'],
                        "delay": row['delay'],
                    }
                    
                    if row['description']:
                        item_config['description'] = row['description']
                    if row['units']:
                        item_config['units'] = row['units']
                    if row['multiplier']:
                        item_config['multiplier'] = row['multiplier']
                    if row['delta']:
                        item_config['delta'] = row['delta']
                    if row['history']:
                        try:
                            # 直接使用字符串格式，如 "7d"
                            if isinstance(row['history'], int):
                                item_config['history'] = f"{row['history']}d"
                            else:
                                item_config['history'] = str(row['history'])
                        except (ValueError, TypeError):
                            logger.warning(f"Invalid history value: {row['history']}, using default")
                    if row['trends']:
                        try:
                            # 直接使用字符串格式，如 "365d"
                            if isinstance(row['trends'], int):
                                item_config['trends'] = f"{row['trends']}d"
                            else:
                                item_config['trends'] = str(row['trends'])
                        except (ValueError, TypeError):
                            logger.warning(f"Invalid trends value: {row['trends']}, using default")
                    if row['status']:
                        item_config['status'] = row['status']
                    if row['master_item']:
                        item_config['master_item'] = row['master_item']
                    if row['preprocessing']:
                        item_config['preprocessing'] = row['preprocessing']
                    
                    template["items"][row['item_key']] = item_config
            
            # 加载触发器（从复核表）
            logger.info(f"从数据库加载模板 {template_name} 的触发器...")
            with self.connection.cursor(cursor_factory=DictCursor) as cur:
                cur.execute("""
                    SELECT tr.name, tr.expression, tr.priority, tr.description, tr.status
                    FROM triggers_review tr
                    WHERE tr.template_name = %s AND tr.confirmed = true
                    LIMIT 100
                """, (template_name,))
                
                triggers_rows = cur.fetchall()
                logger.info(f"从复核表获取到 {len(triggers_rows)} 个触发器")
                
                # 如果复核表中没有确认的记录，从原始表加载
                if len(triggers_rows) == 0:
                    logger.info(f"复核表中没有确认的记录，从原始表加载触发器...")
                    with self.connection.cursor(cursor_factory=DictCursor) as cur2:
                        cur2.execute("""
                            SELECT name, expression, priority, description, status
                            FROM triggers
                            WHERE template_name = %s
                            LIMIT 100
                        """, (template_name,))
                        
                        triggers_rows = cur2.fetchall()
                        logger.info(f"从原始表获取到 {len(triggers_rows)} 个触发器")
                
                for row in triggers_rows:
                    trigger_config = {
                        "expression": row['expression'],
                        "priority": row['priority'],
                    }
                    
                    if row['description'] and row['description'] != 'None':
                        trigger_config['description'] = row['description']
                    if row['status']:
                        trigger_config['status'] = row['status']
                    
                    template["triggers"][row['name']] = trigger_config
            
            # 加载自动发现规则
            logger.info(f"从数据库加载模板 {template_name} 的自动发现规则...")
            with self.connection.cursor(cursor_factory=DictCursor) as cur:
                cur.execute("""
                    SELECT id, name, key, delay, evaltype, status
                    FROM discovery_rules
                    WHERE template_name = %s
                """, (template_name,))
                
                rules_rows = cur.fetchall()
                logger.info(f"获取到 {len(rules_rows)} 个自动发现规则")
                
                for row in rules_rows:
                    rule_id = row['id']
                    rule_config = {
                        "name": row['name'],
                        "key": row['key'],
                        "delay": row['delay'],
                        "filter": {
                            "evaltype": row['evaltype'],
                            "conditions": []
                        },
                        "item_prototypes": [],
                        "trigger_prototypes": []
                    }
                    
                    if row['status']:
                        rule_config['status'] = row['status']
                    
                    # 加载过滤条件
                    with self.connection.cursor(cursor_factory=DictCursor) as cur2:
                        cur2.execute(
                            'SELECT macro, value, operator FROM filter_conditions WHERE discovery_rule_id = %s',
                            (rule_id,)
                        )
                        
                        cond_rows = cur2.fetchall()
                        logger.info(f"规则 {row['name']} 有 {len(cond_rows)} 个过滤条件")
                        
                        # Zabbix API 发现规则过滤条件运算符:
                        #   8 = 匹配正则 (CONDITION_OPERATOR_REGEXP)
                        #   9 = 不匹配正则 (CONDITION_OPERATOR_NOT_REGEXP)
                        # 其他运算符需要转换为正则模式
                        for cond_row in cond_rows:
                            operator_str = cond_row['operator']
                            value = cond_row['value']

                            if operator_str == 'MATCHES_REGEX':
                                operator_num = 8
                            elif operator_str == 'NOT_MATCHES_REGEX':
                                operator_num = 9
                            elif operator_str == 'EQUALS':
                                operator_num = 8
                                value = f'^{value}$'
                            elif operator_str == 'NOT_EQUAL':
                                operator_num = 9
                                value = f'^{value}$'
                            elif operator_str == 'CONTAINS':
                                operator_num = 8
                            elif operator_str == 'NOT_CONTAINS':
                                operator_num = 9
                            else:
                                logger.warning(f"未知的过滤运算符: {operator_str}，默认使用匹配正则")
                                operator_num = 8

                            rule_config['filter']['conditions'].append({
                                "macro": cond_row['macro'],
                                "value": value,
                                "operator": operator_num
                            })
                    
                    # 加载监控项原型（从复核表）
                    with self.connection.cursor(cursor_factory=DictCursor) as cur2:
                        cur2.execute("""
                            SELECT ipr.name, ipr.key, ipr.value_type, ipr.delay, ipr.description, ipr.units, 
                                   ipr.multiplier, ipr.delta, ipr.history, ipr.trends, ipr.status
                            FROM item_prototypes_review ipr
                            WHERE ipr.discovery_rule_id = %s AND ipr.confirmed = true
                            LIMIT 100
                        """, (rule_id,))
                        
                        proto_rows = cur2.fetchall()
                        logger.info(f"从复核表获取到规则 {row['name']} 的 {len(proto_rows)} 个监控项原型")
                        
                        # 如果复核表中没有确认的记录，从原始表加载
                        if len(proto_rows) == 0:
                            logger.info(f"复核表中没有确认的记录，从原始表加载监控项原型...")
                            with self.connection.cursor(cursor_factory=DictCursor) as cur3:
                                cur3.execute(
                                    'SELECT name, key, value_type, delay, description, units, multiplier, delta, history, trends, status FROM item_prototypes WHERE discovery_rule_id = %s',
                                    (rule_id,)
                                )
                                
                                proto_rows = cur3.fetchall()
                                logger.info(f"从原始表获取到规则 {row['name']} 的 {len(proto_rows)} 个监控项原型")
                        
                        for proto_row in proto_rows:
                            proto_config = {
                                "name": proto_row['name'],
                                "key": proto_row['key'],
                                "value_type": proto_row['value_type'],
                                "delay": proto_row['delay'],
                            }
                            
                            if proto_row['description']:
                                proto_config['description'] = proto_row['description']
                            if proto_row['units']:
                                proto_config['units'] = proto_row['units']
                            if proto_row['multiplier']:
                                proto_config['multiplier'] = proto_row['multiplier']
                            if proto_row['delta']:
                                proto_config['delta'] = proto_row['delta']
                            if proto_row['history']:
                                try:
                                    # 将天数转换为秒
                                    history_days = int(proto_row['history'])
                                    proto_config['history'] = history_days * 86400
                                except (ValueError, TypeError):
                                    logger.warning(f"Invalid history value: {proto_row['history']}, using default")
                            if proto_row['trends']:
                                try:
                                    # 将天数转换为秒
                                    trends_days = int(proto_row['trends'])
                                    proto_config['trends'] = trends_days * 86400
                                except (ValueError, TypeError):
                                    logger.warning(f"Invalid trends value: {proto_row['trends']}, using default")
                            if proto_row['status']:
                                proto_config['status'] = proto_row['status']
                            
                            rule_config['item_prototypes'].append(proto_config)
                    
                    # 加载触发器原型（从复核表）
                    with self.connection.cursor(cursor_factory=DictCursor) as cur2:
                        cur2.execute("""
                            SELECT tpr.description, tpr.expression, tpr.priority, tpr.status
                            FROM trigger_prototypes_review tpr
                            WHERE tpr.discovery_rule_id = %s AND tpr.confirmed = true
                            LIMIT 100
                        """, (rule_id,))
                        
                        proto_rows = cur2.fetchall()
                        logger.info(f"从复核表获取到规则 {row['name']} 的 {len(proto_rows)} 个触发器原型")
                        
                        # 如果复核表中没有确认的记录，从原始表加载
                        if len(proto_rows) == 0:
                            logger.info(f"复核表中没有确认的记录，从原始表加载触发器原型...")
                            with self.connection.cursor(cursor_factory=DictCursor) as cur3:
                                cur3.execute(
                                    'SELECT description, expression, priority, status FROM trigger_prototypes WHERE discovery_rule_id = %s',
                                    (rule_id,)
                                )
                                
                                proto_rows = cur3.fetchall()
                                logger.info(f"从原始表获取到规则 {row['name']} 的 {len(proto_rows)} 个触发器原型")
                        
                        for proto_row in proto_rows:
                            proto_config = {
                                "description": proto_row['description'],
                                "expression": proto_row['expression'],
                                "priority": proto_row['priority'],
                            }
                            
                            if proto_row['status']:
                                proto_config['status'] = proto_row['status']
                            
                            rule_config['trigger_prototypes'].append(proto_config)
                    
                    template["discovery_rules"].append(rule_config)
            
            logger.info(f"成功从数据库加载模板 {template_name}")
            return template
        except psycopg2.OperationalError as e:
            logger.error(f"数据库操作失败: {e}")
            # 重置连接以解决连接问题
            self.reset_connection()
            return {}
        except Exception as e:
            logger.error(f"从数据库加载模板失败: {e}")
            # 重置连接以解决事务中止问题
            self.reset_connection()
            return {}
    
    def load_template(self, template_name: str) -> Dict[str, Any]:
        """从数据库加载模板
        
        Args:
            template_name: 模板名称
            
        Returns:
            模板字典
        """
        # 从数据库加载模板
        if self.db_config:
            logger.info(f"尝试从数据库加载模板 {template_name}...")
            template = self.load_template_from_db(template_name)
            if template:
                logger.info(f"成功从数据库加载模板 {template_name}")
                return template
            logger.error(f"从数据库加载模板 {template_name} 失败")
        else:
            logger.error("数据库配置未提供")
        return {}
    
    def initialize_items_review(self) -> bool:
        """初始化 items_review 表
        
        Returns:
            是否成功
        """
        if not self.connection:
            if not self.connect_db():
                return False
        
        try:
            logger.info("开始初始化 items_review 表...")
            
            with self.connection.cursor() as cur:
                logger.info("清空 items_review 表...")
                cur.execute("DELETE FROM items_review")
                logger.info(f"删除了 {cur.rowcount} 条记录")
                
                logger.info("初始化 items_review 表...")
                # 只选择 template_name 为 '21001' 的监控项
                cur.execute("""
                    INSERT INTO items_review (
                        item_id, host_ip, item_key, name, type, value_type, delay,
                        description, units, multiplier, delta, history, trends,
                        status, template_name, master_item, preprocessing, system, subsystem,
                        modified, confirmed, status_verification
                    )
                    SELECT 
                        i.id,
                        h.name as host_ip,
                        i.item_key,
                        i.name,
                        i.type,
                        i.value_type,
                        i.delay,
                        i.description,
                        i.units,
                        i.multiplier,
                        i.delta,
                        i.history,
                        i.trends,
                        i.status,
                        i.template_name,
                        i.master_item,
                        i.preprocessing,
                        h.system,
                        h.subsystem,
                        false,
                        false,
                        'pending'
                    FROM items i
                    CROSS JOIN hosts h
                    WHERE i.template_name = '21001'
                """)
                logger.info(f"插入了 {cur.rowcount} 条记录到 items_review 表")
            
            return True
        except Exception as e:
            logger.error(f"初始化 items_review 表失败: {e}")
            return False
    
    def initialize_triggers_review(self) -> bool:
        """初始化 triggers_review 表
        
        Returns:
            是否成功
        """
        if not self.connection:
            if not self.connect_db():
                return False
        
        try:
            logger.info("开始初始化 triggers_review 表...")
            
            with self.connection.cursor() as cur:
                logger.info("清空 triggers_review 表...")
                cur.execute("DELETE FROM triggers_review")
                logger.info(f"删除了 {cur.rowcount} 条记录")
                
                logger.info("初始化 triggers_review 表...")
                cur.execute("""
                    SELECT * FROM triggers LIMIT 1
                """)
                trigger_columns = [desc[0] for desc in cur.description]
                
                if 'id' in trigger_columns:
                    # 如果 triggers 表有 id 字段
                    # 只选择 template_name 为 '21001' 的触发器
                    cur.execute("""
                        INSERT INTO triggers_review (
                            trigger_id, host_ip, name, expression, priority, description,
                            status, template_name, system, subsystem,
                            modified, confirmed, status_verification
                        )
                        SELECT 
                            tr.id,
                            h.name as host_ip,
                            tr.name,
                            tr.expression,
                            tr.priority,
                            tr.description,
                            tr.status,
                            tr.template_name,
                            h.system,
                            h.subsystem,
                            false,
                            false,
                            'pending'
                        FROM triggers tr
                        CROSS JOIN hosts h
                        WHERE tr.template_name = '21001'
                    """)
                else:
                    # 或者我们假设触发器主键是其他字段
                    # 只选择 template_name 为 '21001' 的触发器
                    cur.execute("""
                        INSERT INTO triggers_review (
                            host_ip, name, expression, priority, description,
                            status, template_name, system, subsystem,
                            modified, confirmed, status_verification
                        )
                        SELECT 
                            h.name as host_ip,
                            tr.name,
                            tr.expression,
                            tr.priority,
                            tr.description,
                            tr.status,
                            tr.template_name,
                            h.system,
                            h.subsystem,
                            false,
                            false,
                            'pending'
                        FROM triggers tr
                        CROSS JOIN hosts h
                        WHERE tr.template_name = '21001'
                    """)
                logger.info(f"插入了 {cur.rowcount} 条记录到 triggers_review 表")
            
            return True
        except Exception as e:
            logger.error(f"初始化 triggers_review 表失败: {e}")
            return False
    
    def initialize_item_prototypes_review(self) -> bool:
        """初始化 item_prototypes_review 表
        
        Returns:
            是否成功
        """
        if not self.connection:
            if not self.connect_db():
                return False
        
        try:
            logger.info("开始初始化 item_prototypes_review 表...")
            
            with self.connection.cursor() as cur:
                logger.info("清空 item_prototypes_review 表...")
                cur.execute("DELETE FROM item_prototypes_review")
                logger.info(f"删除了 {cur.rowcount} 条记录")
                
                logger.info("初始化 item_prototypes_review 表...")
                cur.execute("""
                    INSERT INTO item_prototypes_review (
                        item_prototype_id, discovery_rule_id, host_ip, name, key, value_type, delay,
                        description, units, multiplier, delta, history, trends, status,
                        system, subsystem, modified, confirmed, status_verification
                    )
                    SELECT 
                        ip.id,
                        ip.discovery_rule_id,
                        h.name as host_ip,
                        ip.name,
                        ip.key,
                        ip.value_type,
                        ip.delay,
                        ip.description,
                        ip.units,
                        ip.multiplier,
                        ip.delta,
                        ip.history,
                        ip.trends,
                        ip.status,
                        h.system,
                        h.subsystem,
                        false,
                        false,
                        'pending'
                    FROM item_prototypes ip
                    CROSS JOIN hosts h
                    JOIN discovery_rules dr ON ip.discovery_rule_id = dr.id
                    WHERE dr.template_name = '21001'
                """)
                logger.info(f"插入了 {cur.rowcount} 条记录到 item_prototypes_review 表")
            
            return True
        except Exception as e:
            logger.error(f"初始化 item_prototypes_review 表失败: {e}")
            return False
    
    def initialize_trigger_prototypes_review(self) -> bool:
        """初始化 trigger_prototypes_review 表
        
        Returns:
            是否成功
        """
        if not self.connection:
            if not self.connect_db():
                return False
        
        try:
            logger.info("开始初始化 trigger_prototypes_review 表...")
            
            with self.connection.cursor() as cur:
                logger.info("清空 trigger_prototypes_review 表...")
                cur.execute("DELETE FROM trigger_prototypes_review")
                logger.info(f"删除了 {cur.rowcount} 条记录")
                
                logger.info("初始化 trigger_prototypes_review 表...")
                cur.execute("""
                    INSERT INTO trigger_prototypes_review (
                        trigger_prototype_id, discovery_rule_id, host_ip, description, expression, priority, status,
                        system, subsystem, modified, confirmed, status_verification
                    )
                    SELECT 
                        tp.id,
                        tp.discovery_rule_id,
                        h.name as host_ip,
                        tp.description,
                        tp.expression,
                        tp.priority,
                        tp.status,
                        h.system,
                        h.subsystem,
                        false,
                        false,
                        'pending'
                    FROM trigger_prototypes tp
                    CROSS JOIN hosts h
                    JOIN discovery_rules dr ON tp.discovery_rule_id = dr.id
                    WHERE dr.template_name = '21001'
                """)
                logger.info(f"插入了 {cur.rowcount} 条记录到 trigger_prototypes_review 表")
            
            return True
        except Exception as e:
            logger.error(f"初始化 trigger_prototypes_review 表失败: {e}")
            return False
    
    def initialize_review_tables(self) -> bool:
        """初始化复核表（items_review、triggers_review、item_prototypes_review 和 trigger_prototypes_review）
        
        Returns:
            是否成功
        """
        if not self.connection:
            if not self.connect_db():
                return False
        
        try:
            logger.info("开始初始化复核表...")
            
            # 初始化 items_review 表
            success1 = self.initialize_items_review()
            
            # 初始化 triggers_review 表
            success2 = self.initialize_triggers_review()
            
            # 初始化 item_prototypes_review 表
            success3 = self.initialize_item_prototypes_review()
            
            # 初始化 trigger_prototypes_review 表
            success4 = self.initialize_trigger_prototypes_review()
            
            # 提交事务
            self.connection.commit()
            logger.info("复核表初始化完成")
            return success1 and success2 and success3 and success4
            
        except psycopg2.OperationalError as e:
            logger.error(f"数据库操作失败: {e}")
            self.connection.rollback()
            self.reset_connection()
            return False
        except Exception as e:
            logger.error(f"初始化复核表失败: {e}")
            self.connection.rollback()
            self.reset_connection()
            return False
    
    def export_items_review_to_excel(self, output_file: str) -> bool:
        """导出 items_review 表到 Excel 文件
        
        Args:
            output_file: 输出文件路径
            
        Returns:
            是否成功
        """
        if not self.connection:
            if not self.connect_db():
                return False
        
        try:
            logger.info(f"开始导出 items_review 表到 {output_file}...")
            
            with self.connection.cursor(cursor_factory=DictCursor) as cur:
                cur.execute("""
                    SELECT * FROM items_review
                    ORDER BY host_ip, item_key
                """)
                rows = cur.fetchall()
                
                if not rows:
                    logger.warning("items_review 表为空")
                    return False
                
                # 转换为 DataFrame
                df = pd.DataFrame(rows)
                
                # 导出到 Excel
                df.to_excel(output_file, index=False)
                logger.info(f"成功导出 {len(rows)} 条记录到 {output_file}")
                return True
        except Exception as e:
            logger.error(f"导出 items_review 表失败: {e}")
            return False
    
    def export_triggers_review_to_excel(self, output_file: str) -> bool:
        """导出 triggers_review 表到 Excel 文件
        
        Args:
            output_file: 输出文件路径
            
        Returns:
            是否成功
        """
        if not self.connection:
            if not self.connect_db():
                return False
        
        try:
            logger.info(f"开始导出 triggers_review 表到 {output_file}...")
            
            with self.connection.cursor(cursor_factory=DictCursor) as cur:
                cur.execute("""
                    SELECT * FROM triggers_review
                    ORDER BY host_ip, name
                """)
                rows = cur.fetchall()
                
                if not rows:
                    logger.warning("triggers_review 表为空")
                    return False
                
                # 转换为 DataFrame
                df = pd.DataFrame(rows)
                
                # 导出到 Excel
                df.to_excel(output_file, index=False)
                logger.info(f"成功导出 {len(rows)} 条记录到 {output_file}")
                return True
        except Exception as e:
            logger.error(f"导出 triggers_review 表失败: {e}")
            return False
    
    def import_items_review_from_excel(self, input_file: str) -> bool:
        """从 Excel 文件导入数据到 items_review 表
        
        Args:
            input_file: 输入文件路径
            
        Returns:
            是否成功
        """
        if not self.connection:
            if not self.connect_db():
                return False
        
        try:
            logger.info(f"开始从 {input_file} 导入数据到 items_review 表...")
            
            # 读取 Excel 文件
            df = pd.read_excel(input_file)
            logger.info(f"读取到 {len(df)} 条记录")
            
            # 清空表
            with self.connection.cursor() as cur:
                cur.execute("DELETE FROM items_review")
                logger.info(f"清空了 {cur.rowcount} 条记录")
                
                # 插入数据
                inserted = 0
                for _, row in df.iterrows():
                    try:
                        # 构建插入语句
                        columns = list(df.columns)
                        placeholders = ', '.join(['%s'] * len(columns))
                        column_names = ', '.join(columns)
                        
                        # 准备数据
                        values = [row[col] if pd.notna(row[col]) else None for col in columns]
                        
                        # 执行插入
                        cur.execute(
                            f"INSERT INTO items_review ({column_names}) VALUES ({placeholders})",
                            values
                        )
                        inserted += 1
                    except Exception as e:
                        logger.error(f"插入记录失败: {e}")
                        continue
                
                # 提交事务
                self.connection.commit()
                logger.info(f"成功导入 {inserted} 条记录到 items_review 表")
                return True
        except Exception as e:
            logger.error(f"导入 items_review 表失败: {e}")
            self.connection.rollback()
            return False
    
    def import_triggers_review_from_excel(self, input_file: str) -> bool:
        """从 Excel 文件导入数据到 triggers_review 表
        
        Args:
            input_file: 输入文件路径
            
        Returns:
            是否成功
        """
        if not self.connection:
            if not self.connect_db():
                return False
        
        try:
            logger.info(f"开始从 {input_file} 导入数据到 triggers_review 表...")
            
            # 读取 Excel 文件
            df = pd.read_excel(input_file)
            logger.info(f"读取到 {len(df)} 条记录")
            
            # 清空表
            with self.connection.cursor() as cur:
                cur.execute("DELETE FROM triggers_review")
                logger.info(f"清空了 {cur.rowcount} 条记录")
                
                # 插入数据
                inserted = 0
                for _, row in df.iterrows():
                    try:
                        # 构建插入语句
                        columns = list(df.columns)
                        placeholders = ', '.join(['%s'] * len(columns))
                        column_names = ', '.join(columns)
                        
                        # 准备数据
                        values = [row[col] if pd.notna(row[col]) else None for col in columns]
                        
                        # 执行插入
                        cur.execute(
                            f"INSERT INTO triggers_review ({column_names}) VALUES ({placeholders})",
                            values
                        )
                        inserted += 1
                    except Exception as e:
                        logger.error(f"插入记录失败: {e}")
                        continue
                
                # 提交事务
                self.connection.commit()
                logger.info(f"成功导入 {inserted} 条记录到 triggers_review 表")
                return True
        except Exception as e:
            logger.error(f"导入 triggers_review 表失败: {e}")
            self.connection.rollback()
            return False
    
    def get_webscenario_items(self) -> List[Dict[str, Any]]:
        """从数据库获取 webscenario_items 表数据
        
        Returns:
            webscenario_items 列表
        """
        if not self.connection:
            if not self.connect_db():
                return []
        
        try:
            logger.info("从数据库获取 webscenario_items 表数据...")
            
            with self.connection.cursor(cursor_factory=DictCursor) as cur:
                cur.execute("""
                    SELECT * FROM webscenario_items
                    ORDER BY id
                """)
                rows = cur.fetchall()
                
                # 转换为字典列表
                webscenario_items = []
                for row in rows:
                    item = dict(row)
                    webscenario_items.append(item)
                
                logger.info(f"获取到 {len(webscenario_items)} 条 webscenario_items 记录")
                return webscenario_items
        except Exception as e:
            logger.error(f"获取 webscenario_items 表数据失败: {e}")
            return []
    
    def initialize_webscenario_items_review(self) -> bool:
        """初始化 webscenario_items_review 表
        
        Returns:
            是否成功
        """
        if not self.connection:
            if not self.connect_db():
                return False
        
        try:
            logger.info("开始初始化 webscenario_items_review 表...")
            
            with self.connection.cursor() as cur:
                logger.info("清空 webscenario_items_review 表...")
                cur.execute("DELETE FROM webscenario_items_review")
                logger.info(f"删除了 {cur.rowcount} 条记录")
                
                logger.info("从 webscenario_items 表导入数据到 webscenario_items_review 表...")
                
                # 处理 nginx_clb
                cur.execute("""
                    INSERT INTO webscenario_items_review (
                        system, subsystem, host, name, url, status_code
                    )
                    SELECT 
                        system, 
                        subsystem, 
                        'Zabbix server' as host,
                        CONCAT('http://', nginx_clb, webtest_nginx_api, '_interface') as name,
                        CONCAT('http://', nginx_clb, webtest_nginx_api) as url,
                        '200' as status_code
                    FROM webscenario_items
                    WHERE nginx_clb IS NOT NULL AND nginx_clb != ''
                """)
                logger.info(f"导入了 {cur.rowcount} 条 nginx_clb 记录")
                
                # 处理 nginx
                cur.execute("""
                    INSERT INTO webscenario_items_review (
                        system, subsystem, host, name, url, status_code
                    )
                    SELECT 
                        system, 
                        subsystem, 
                        'Zabbix server' as host,
                        CONCAT('http://', nginx, webtest_nginx_api, '_interface') as name,
                        CONCAT('http://', nginx, webtest_nginx_api) as url,
                        '200' as status_code
                    FROM webscenario_items
                    WHERE nginx IS NOT NULL AND nginx != ''
                """)
                logger.info(f"导入了 {cur.rowcount} 条 nginx 记录")
                
                # 处理 clb
                cur.execute("""
                    INSERT INTO webscenario_items_review (
                        system, subsystem, host, name, url, status_code
                    )
                    SELECT 
                        system, 
                        subsystem, 
                        'Zabbix server' as host,
                        CONCAT('http://', clb, webtest_api, '_interface') as name,
                        CONCAT('http://', clb, webtest_api) as url,
                        '200' as status_code
                    FROM webscenario_items
                    WHERE clb IS NOT NULL AND clb != ''
                """)
                logger.info(f"导入了 {cur.rowcount} 条 clb 记录")
                
                # 处理 pod
                cur.execute("""
                    INSERT INTO webscenario_items_review (
                        system, subsystem, host, name, url, status_code
                    )
                    SELECT 
                        system, 
                        subsystem, 
                        'Zabbix server' as host,
                        CONCAT('http://', pod, webtest_api, '_interface') as name,
                        CONCAT('http://', pod, webtest_api) as url,
                        '200' as status_code
                    FROM webscenario_items
                    WHERE pod IS NOT NULL AND pod != ''
                """)
                logger.info(f"导入了 {cur.rowcount} 条 pod 记录")
                
                # 提交事务
                self.connection.commit()
                logger.info("webscenario_items_review 表初始化完成")
                return True
        except Exception as e:
            logger.error(f"初始化 webscenario_items_review 表失败: {e}")
            self.connection.rollback()
            return False
    
    def get_webscenario_items_review(self) -> List[Dict[str, Any]]:
        """从数据库获取 webscenario_items_review 表数据
        
        Returns:
            webscenario_items_review 列表
        """
        if not self.connection:
            if not self.connect_db():
                return []
        
        try:
            logger.info("从数据库获取 webscenario_items_review 表数据...")
            
            with self.connection.cursor(cursor_factory=DictCursor) as cur:
                cur.execute("""
                    SELECT * FROM webscenario_items_review
                    WHERE confirmed = true
                    ORDER BY id
                """)
                rows = cur.fetchall()
                
                # 转换为字典列表
                webscenario_items = []
                for row in rows:
                    item = dict(row)
                    webscenario_items.append(item)
                
                logger.info(f"获取到 {len(webscenario_items)} 条已确认的 webscenario_items_review 记录")
                return webscenario_items
        except Exception as e:
            logger.error(f"获取 webscenario_items_review 表数据失败: {e}")
            return []
    
    def deep_merge(self, target: Dict[str, Any], source: Dict[str, Any]) -> Dict[str, Any]:
        """深层合并字典
        
        Args:
            target: 目标字典
            source: 源字典
            
        Returns:
            合并后的字典
        """
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self.deep_merge(target[key], value)
            else:
                target[key] = value
        return target
    
    def get_host_config(self, config: Dict[str, Any], host_name: str) -> Optional[Dict[str, Any]]:
        """获取主机配置
        
        Args:
            config: 总配置
            host_name: 主机名
            
        Returns:
            主机配置或 None
        """
        hosts = config.get("hosts", {})
        return hosts.get(host_name)
    
    def build_host_config(self, config: Dict[str, Any], host_name: str) -> Dict[str, Any]:
        """构建主机完整配置
        
        Args:
            config: 总配置
            host_name: 主机名
            
        Returns:
            完整的主机配置
        """
        host_config = self.get_host_config(config, host_name)
        if not host_config:
            return {}
        
        # 合并模板
        merged_config = {}
        templates = host_config.get("templates", [])
        for template_name in templates:
            template = self.load_template(template_name)
            self.deep_merge(merged_config, template)
        
        # 合并额外项（最高优先级）
        extra_items = host_config.get("extra_items", {})
        self.deep_merge(merged_config, extra_items)
        
        return merged_config


class ReportGenerator:
    """变更报告生成器"""
    
    def __init__(self):
        """初始化报告生成器"""
        self.changes = {
            "created": [],
            "updated": [],
            "deleted": []
        }
        self.lock = threading.Lock()
    
    def log_change(self, action: str, obj_type: str, name: str, details: Optional[Dict[str, Any]] = None):
        """记录变更
        
        Args:
            action: 动作类型 (created/updated/deleted)
            obj_type: 对象类型 (item/trigger/rule)
            name: 对象名称
            details: 变更详情
        """
        with self.lock:
            self.changes[action].append({
                "type": obj_type,
                "name": name,
                "details": details
            })
    
    def generate_report(self, format: str = "json") -> str:
        """生成变更报告
        
        Args:
            format: 报告格式 (json/table)
            
        Returns:
            报告字符串
        """
        if format == "json":
            return json.dumps(self.changes, indent=2, ensure_ascii=False)
        elif format == "table":
            report = "\n变更摘要:\n"
            report += "-" * 80 + "\n"
            report += f"新增: {len(self.changes['created'])}\n"
            report += f"修改: {len(self.changes['updated'])}\n"
            report += f"删除: {len(self.changes['deleted'])}\n"
            report += "-" * 80 + "\n"
            
            if self.changes['created']:
                report += "\n新增对象:\n"
                for item in self.changes['created']:
                    report += f"  - {item['type']}: {item['name']}\n"
            
            if self.changes['updated']:
                report += "\n修改对象:\n"
                for item in self.changes['updated']:
                    report += f"  - {item['type']}: {item['name']}\n"
            
            if self.changes['deleted']:
                report += "\n删除对象:\n"
                for item in self.changes['deleted']:
                    report += f"  - {item['type']}: {item['name']}\n"
            
            return report
        else:
            return "不支持的报告格式"


class SyncEngine:
    """同步引擎"""
    
    def __init__(self, zabbix_client: ZabbixClient, config_loader: ConfigLoader, report_generator: ReportGenerator):
        """初始化同步引擎
        
        Args:
            zabbix_client: Zabbix 客户端
            config_loader: 配置加载器
            report_generator: 报告生成器
        """
        self.zabbix_client = zabbix_client
        self.config_loader = config_loader
        self.report_generator = report_generator
    
    def sync_host(self, host_name: str, config: Dict[str, Any], dry_run: bool = False):
        """同步单个主机
        
        Args:
            host_name: 主机名
            config: 总配置
            dry_run: 是否模拟运行
        """
        logger.info(f"开始同步主机: {host_name}")
        
        # 首先使用 host_ip 获取 host_id
        host_ip = host_name  # 这里 host_name 实际上是 host_ip
        logger.info(f"使用 host_ip: {host_ip} 获取 host_id")
        
        # 获取主机 ID
        host_id = self.zabbix_client.get_host_id(host_ip)
        if not host_id:
            logger.error(f"主机不存在: {host_ip}")
            return
        
        # 构建目标配置
        target_config = self.config_loader.build_host_config(config, host_name)
        if not target_config:
            logger.error(f"主机配置不存在: {host_name}")
            return
        
        # 获取目标配置中的监控项和触发器
        target_items = target_config.get("items", {})
        target_triggers = target_config.get("triggers", {})
        
        # 同步监控项
        self._sync_items(host_id, target_items, dry_run)
        
        # 同步触发器
        self._sync_triggers(host_id, host_name, target_triggers, dry_run)
        
        # 同步自动发现规则
        self._sync_discovery_rules(host_id, host_name, target_config.get("discovery_rules", []), dry_run)
        
        # 同步 web 场景
        self._sync_web_scenarios(host_id, host_name, target_config.get("web_scenarios", []), dry_run)
        
        # 验证机制：同步完成后，对比两端数据库的状态
        if not dry_run:
            self._validate_sync(host_id, host_name, target_items, target_triggers)
        
        logger.info(f"主机同步完成: {host_name}")
    
    def _sync_items(self, host_id: str, target_items: Dict[str, Any], dry_run: bool):
        """同步监控项
        
        Args:
            host_id: 主机 ID
            target_items: 目标监控项配置
            dry_run: 是否模拟运行
        """
        try:
            # 获取当前监控项
            logger.debug(f"获取主机 {host_id} 的当前监控项")
            current_items = self.zabbix_client.get_managed_items(host_id)
            current_items_map = {item["key_"]: item for item in current_items}
            logger.info(f"获取到 {len(current_items)} 个当前监控项")
            
            # 获取主机接口 ID
            interface_id = self.zabbix_client.get_host_interface_id(host_id)
            if not interface_id:
                logger.error(f"无法获取主机接口 ID，监控项同步将跳过")
                return
            
            # 同步目标监控项
            # 首先创建所有不依赖其他项的监控项
            # 然后再创建依赖其他项的监控项
            
            # 第一遍：分离不依赖和依赖其他项的监控项
            independent_items = {}
            dependent_items = {}
            
            for key, item_config in target_items.items():
                # 只有当 type 为 15（相关项目）或 18（依赖项）且有 master_item 配置时，才视为依赖项
                if (item_config.get("type") in [15, 18]) and "master_item" in item_config:
                    dependent_items[key] = item_config
                else:
                    independent_items[key] = item_config
            
            logger.info(f"分离出 {len(independent_items)} 个独立监控项和 {len(dependent_items)} 个依赖监控项")
            
            # 第二遍：创建不依赖其他项的监控项
            for key, item_config in independent_items.items():
                try:
                    # 构建监控项数据
                    item_data = {
                        "hostid": host_id,
                        "key_": key,
                        "interfaceid": interface_id,
                        **item_config
                    }
                    
                    # 为不同类型的监控项添加必要的参数
                    item_type = item_config.get("type", 0)
                    if item_type == 15:  # 计算型监控项
                        if "formula" in item_config:
                            item_data["formula"] = item_config["formula"]
                        else:
                            logger.warning(f"计算型监控项 {key} 缺少 formula 参数")
                    
                    # 处理预处理步骤
                    if "preprocessing" in item_config:
                        item_data["preprocessing"] = item_config["preprocessing"]
                    
                    if key in current_items_map:
                        # 检查是否需要更新
                        current_item = current_items_map[key]
                        target_fingerprint = self.zabbix_client.calculate_fingerprint(item_data)
                        current_fingerprint = self.zabbix_client.calculate_fingerprint(current_item)
                        
                        if target_fingerprint != current_fingerprint:
                            if not dry_run:
                                logger.debug(f"更新监控项: {key}")
                                success = self.zabbix_client.update_item(current_item["itemid"], item_data)
                                if success:
                                    self.report_generator.log_change("updated", "item", key)
                                    logger.info(f"监控项 {key} 更新成功")
                                else:
                                    logger.error(f"监控项 {key} 更新失败")
                            else:
                                self.report_generator.log_change("updated", "item", key)
                                logger.debug(f"[模拟] 更新监控项: {key}")
                    else:
                        # 创建新监控项
                        if not dry_run:
                            logger.debug(f"创建监控项: {key}")
                            item_id = self.zabbix_client.create_item(item_data)
                            if item_id:
                                # 更新 current_items_map，以便后续的依赖项可以找到
                                current_items_map[key] = {"itemid": item_id, "key_": key}
                                self.report_generator.log_change("created", "item", key)
                                logger.info(f"监控项 {key} 创建成功")
                            else:
                                logger.error(f"监控项 {key} 创建失败")
                        else:
                            self.report_generator.log_change("created", "item", key)
                            logger.debug(f"[模拟] 创建监控项: {key}")
                except Exception as e:
                    logger.error(f"处理监控项 {key} 失败: {e}")
                    continue
            
            # 第三遍：创建依赖其他项的监控项
            for key, item_config in dependent_items.items():
                try:
                    # 构建监控项数据
                    item_data = {
                        "hostid": host_id,
                        "key_": key,
                        "interfaceid": interface_id,
                        **item_config
                    }
                    
                    # 处理 master_item
                    master_key = item_config["master_item"]
                    # 查找主监控项的 ID
                    if master_key in current_items_map:
                        item_data["master_itemid"] = current_items_map[master_key]["itemid"]
                        logger.debug(f"为监控项 {key} 找到主监控项 {master_key} (ID: {item_data['master_itemid']})")
                    else:
                        logger.warning(f"主监控项 {master_key} 不存在，无法设置 master_itemid")
                        # 跳过创建依赖项
                        continue
                    
                    # 处理预处理步骤
                    if "preprocessing" in item_config:
                        item_data["preprocessing"] = item_config["preprocessing"]
                    
                    if key in current_items_map:
                        # 检查是否需要更新
                        current_item = current_items_map[key]
                        target_fingerprint = self.zabbix_client.calculate_fingerprint(item_data)
                        current_fingerprint = self.zabbix_client.calculate_fingerprint(current_item)
                        
                        if target_fingerprint != current_fingerprint:
                            if not dry_run:
                                logger.debug(f"更新依赖监控项: {key}")
                                success = self.zabbix_client.update_item(current_item["itemid"], item_data)
                                if success:
                                    self.report_generator.log_change("updated", "item", key)
                                    logger.info(f"依赖监控项 {key} 更新成功")
                                else:
                                    logger.error(f"依赖监控项 {key} 更新失败")
                            else:
                                self.report_generator.log_change("updated", "item", key)
                                logger.debug(f"[模拟] 更新依赖监控项: {key}")
                    else:
                        # 创建新监控项
                        if not dry_run:
                            logger.debug(f"创建依赖监控项: {key}")
                            item_id = self.zabbix_client.create_item(item_data)
                            if item_id:
                                self.report_generator.log_change("created", "item", key)
                                logger.info(f"依赖监控项 {key} 创建成功")
                            else:
                                logger.error(f"依赖监控项 {key} 创建失败")
                        else:
                            self.report_generator.log_change("created", "item", key)
                            logger.debug(f"[模拟] 创建依赖监控项: {key}")
                except Exception as e:
                    logger.error(f"处理依赖监控项 {key} 失败: {e}")
                    continue
            
            # 清理多余的监控项
            for key, item in current_items_map.items():
                if key not in target_items:
                    if not dry_run:
                        logger.debug(f"删除多余监控项: {key}")
                        success = self.zabbix_client.delete_item(item["itemid"])
                        if success:
                            self.report_generator.log_change("deleted", "item", key)
                            logger.info(f"监控项 {key} 删除成功")
                        else:
                            logger.error(f"监控项 {key} 删除失败")
                    else:
                        self.report_generator.log_change("deleted", "item", key)
                        logger.debug(f"[模拟] 删除多余监控项: {key}")
        except Exception as e:
            logger.error(f"同步监控项时发生错误: {e}")
    
    def _resolve_item_ids(self, expression: str, host_id: str) -> str:
        """解析表达式中的监控项ID，替换为 {host:key} 格式
        
        Args:
            expression: 触发器表达式
            host_id: 主机 ID
            
        Returns:
            解析后的表达式
        """
        import re
        
        # 匹配 {数字} 格式的监控项ID
        matches = re.findall(r'\{(\d+)\}', expression)
        
        if not matches:
            return expression
        
        logger.info(f"在表达式中找到监控项ID: {matches}")
        
        # 获取主机的所有监控项
        try:
            items = self.zabbix_client.api.item.get(
                hostids=host_id,
                output=["itemid", "key_"]
            )
            
            logger.info(f"获取到 {len(items)} 个监控项")
            
            # 创建监控项ID到键的映射
            item_id_to_key = {str(item["itemid"]): item["key_"] for item in items}
            
            logger.info(f"创建了监控项ID到键的映射，包含 {len(item_id_to_key)} 个条目")
            
            # 替换表达式中的监控项ID
            for item_id in matches:
                if item_id in item_id_to_key:
                    # 确保替换整个匹配项，包括花括号
                    old_pattern = f'{{{item_id}}}'
                    new_pattern = f'{{host:{item_id_to_key[item_id]}}}'
                    expression = expression.replace(old_pattern, new_pattern)
                    logger.info(f"替换监控项ID {item_id} 为 {item_id_to_key[item_id]}")
                else:
                    logger.warning(f"监控项ID {item_id} 不在映射中")
        except Exception as e:
            logger.warning(f"解析监控项ID失败: {e}")
        
        return expression
    
    def _replace_macros(self, expression: str) -> str:
        """替换表达式中的宏变量为默认值
        
        Args:
            expression: 触发器表达式
            
        Returns:
            替换后的表达式
        """
        # 替换常见宏变量为默认值
        macros = {
            '{$CPU.UTIL.CRIT}': '90',
            '{$CPU.UTIL.WARN}': '80',
            '{$KERNEL.MAXFILES.MIN}': '256',
            '{$KERNEL.MAXPROC.MIN}': '1024',
            '{$LOAD_AVG_PER_CPU.MAX.WARN}': '1.5',
            '{$LOAD_AVG_PER_CPU.MAX.CRIT}': '2.0',
            '{$MEMORY.UTIL.MAX}': '90',
            '{$SWAP.PFREE.MIN.WARN}': '10',
            '{$SWAP.PFREE.MIN.CRIT}': '5',
            '{$MEMORY.AVAILABLE.MIN}': '100M',
            '{$IF.ERRORS.WARN}': '10',
            '{$IF.ERRORS.CRIT}': '50',
            '{$IF.UTIL.MAX}': '90',
            '{$IF.UTIL.CRIT}': '95',
            '{$VFS.FS.INODE.PFREE.MIN.CRIT}': '5',
            '{$VFS.FS.INODE.PFREE.MIN.WARN}': '10',
            '{$VFS.FS.PUSED.MAX.CRIT}': '95',
            '{$VFS.FS.PUSED.MAX.WARN}': '90',
            '{$VFS.FS.FREE.MIN.CRIT}': '1G',
            '{$VFS.FS.FREE.MIN.WARN}': '5G',
            '{$VFS.DEV.READ.AWAIT.WARN}': '20',
            '{$VFS.DEV.READ.AWAIT.CRIT}': '50',
            '{$VFS.DEV.WRITE.AWAIT.WARN}': '20',
            '{$VFS.DEV.WRITE.AWAIT.CRIT}': '50',
            '{$DISK.IOWAIT.MAX.WARN}': '10',
            '{$DISK.IOWAIT.MAX.CRIT}': '20',
            '{$NET.IF.IN.ERRORS.WARN}': '10',
            '{$NET.IF.OUT.ERRORS.WARN}': '10'
        }
        
        for macro, value in macros.items():
            expression = expression.replace(macro, value)
        
        return expression
    
    def _sync_triggers(self, host_id: str, host_name: str, target_triggers: Dict[str, Any], dry_run: bool):
        """同步触发器
        
        Args:
            host_id: 主机 ID
            host_name: 主机名
            target_triggers: 目标触发器配置
            dry_run: 是否模拟运行
        """
        # 获取当前触发器
        current_triggers = self.zabbix_client.get_managed_triggers(host_id)
        current_triggers_map = {trigger["description"]: trigger for trigger in current_triggers}
        
        # 先同步所有监控项，确保它们都已创建
        # 注意：这里假设 _sync_items 已经在调用此方法之前被调用
        
        # 获取主机的所有监控项，用于构建item_key到itemid的映射
        item_key_to_id = {}
        if not dry_run:
            try:
                items = self.zabbix_client.api.item.get(
                    hostids=host_id,
                    output=["itemid", "key_"]
                )
                item_key_to_id = {item["key_"]: item["itemid"] for item in items}
                logger.info(f"获取到 {len(items)} 个监控项，构建了 item_key 到 itemid 的映射")
                
                # 打印所有监控项的key和id，方便调试
                logger.info("主机监控项列表:")
                for item in items:
                    logger.info(f"  - {item['key_']}: {item['itemid']}")
            except Exception as e:
                logger.error(f"获取监控项失败: {e}")
                item_key_to_id = {}
        
        # 第一遍：分离不依赖和依赖其他触发器的触发器
        independent_triggers = {}
        dependent_triggers = {}
        
        for name, trigger_config in target_triggers.items():
            if "dependencies" in trigger_config:
                dependent_triggers[name] = trigger_config
            else:
                independent_triggers[name] = trigger_config
        
        # 第二遍：创建不依赖其他触发器的触发器
        for name, trigger_config in independent_triggers.items():
            # 复制触发器配置
            trigger_config_copy = trigger_config.copy()
            # 处理表达式
            if "expression" in trigger_config_copy:
                expression = trigger_config_copy["expression"]
                # 替换宏变量为默认值
                expression = self._replace_macros(expression)
                # 处理监控项引用
                import re
                
                # 确保表达式使用 {hostname:item_key} 格式，而不是 {itemid} 格式
                # 这样可以通过界面正确读取表达式
                # 首先将 {host:item_key} 替换为 {hostname:item_key} 格式
                expression = expression.replace("{host:", f"{{{host_name}:")
                logger.info(f"将表达式中的 'host:' 替换为 '{host_name}:'，结果: {expression}")
                
                # 跳过将 {hostname:item_key} 格式替换为 {itemid} 格式的步骤
                # 保持 {hostname:item_key} 格式，这样可以通过界面正确读取
                
                # 再次检查并替换剩余的宏变量
                expression = self._replace_macros(expression)
                logger.info(f"最终处理后的表达式: {expression}")
                
                trigger_config_copy["expression"] = expression
            
            trigger_data = {
                "description": name,
                **trigger_config_copy
            }
            
            if name in current_triggers_map:
                # 检查是否需要更新
                current_trigger = current_triggers_map[name]
                target_fingerprint = self.zabbix_client.calculate_fingerprint(trigger_data)
                current_fingerprint = self.zabbix_client.calculate_fingerprint(current_trigger)
                
                if target_fingerprint != current_fingerprint:
                    if not dry_run:
                        try:
                            success = self.zabbix_client.update_trigger(current_trigger["triggerid"], trigger_data)
                            if success:
                                self.report_generator.log_change("updated", "trigger", name)
                        except Exception as e:
                            logger.error(f"更新触发器 {name} 失败: {e}")
                    else:
                        self.report_generator.log_change("updated", "trigger", name)
            else:
                # 创建新触发器
                if not dry_run:
                    try:
                        trigger_id = self.zabbix_client.create_trigger(trigger_data)
                        if trigger_id:
                            # 更新 current_triggers_map，以便后续的依赖项可以找到
                            current_triggers_map[name] = {"triggerid": trigger_id, "description": name}
                            self.report_generator.log_change("created", "trigger", name)
                    except Exception as e:
                        logger.error(f"创建触发器 {name} 失败: {e}")
                else:
                    self.report_generator.log_change("created", "trigger", name)
        
        # 第三遍：创建依赖其他触发器的触发器
        for name, trigger_config in dependent_triggers.items():
            # 复制触发器配置
            trigger_config_copy = trigger_config.copy()
            # 处理表达式
            if "expression" in trigger_config_copy:
                expression = trigger_config_copy["expression"]
                # 替换宏变量为默认值
                expression = self._replace_macros(expression)
                # 处理监控项引用
                import re
                
                # 确保表达式使用 {hostname:item_key} 格式，而不是 {itemid} 格式
                # 这样可以通过界面正确读取表达式
                # 首先将 {host:item_key} 替换为 {hostname:item_key} 格式
                expression = expression.replace("{host:", f"{{{host_name}:")
                logger.info(f"将表达式中的 'host:' 替换为 '{host_name}:'，结果: {expression}")
                
                # 跳过将 {hostname:item_key} 格式替换为 {itemid} 格式的步骤
                # 保持 {hostname:item_key} 格式，这样可以通过界面正确读取
                
                # 再次检查并替换剩余的宏变量
                expression = self._replace_macros(expression)
                logger.info(f"最终处理后的表达式: {expression}")
                
                trigger_config_copy["expression"] = expression
            
            # 处理依赖关系
            if "dependencies" in trigger_config_copy:
                dependency_names = trigger_config_copy["dependencies"]
                dependency_ids = []
                for dep_name in dependency_names:
                    if dep_name in current_triggers_map:
                        dependency_ids.append(current_triggers_map[dep_name]["triggerid"])
                    else:
                        logger.warning(f"依赖的触发器 {dep_name} 不存在，无法设置依赖关系")
                # 替换依赖名称为依赖 ID
                if dependency_ids:
                    trigger_config_copy["dependencies"] = dependency_ids
                else:
                    # 如果没有找到依赖的触发器，移除 dependencies 参数
                    del trigger_config_copy["dependencies"]
            
            trigger_data = {
                "description": name,
                **trigger_config_copy
            }
            
            if name in current_triggers_map:
                # 检查是否需要更新
                current_trigger = current_triggers_map[name]
                target_fingerprint = self.zabbix_client.calculate_fingerprint(trigger_data)
                current_fingerprint = self.zabbix_client.calculate_fingerprint(current_trigger)
                
                if target_fingerprint != current_fingerprint:
                    if not dry_run:
                        try:
                            success = self.zabbix_client.update_trigger(current_trigger["triggerid"], trigger_data)
                            if success:
                                self.report_generator.log_change("updated", "trigger", name)
                        except Exception as e:
                            logger.error(f"更新触发器 {name} 失败: {e}")
                    else:
                        self.report_generator.log_change("updated", "trigger", name)
            else:
                # 创建新触发器
                if not dry_run:
                    try:
                        trigger_id = self.zabbix_client.create_trigger(trigger_data)
                        if trigger_id:
                            self.report_generator.log_change("created", "trigger", name)
                    except Exception as e:
                        logger.error(f"创建触发器 {name} 失败: {e}")
                else:
                    self.report_generator.log_change("created", "trigger", name)
        
        # 二次更新法：触发器同步完成后，再单独执行一次依赖关系扫描
        if not dry_run:
            logger.info("执行二次更新，处理触发器依赖关系...")
            # 重新获取所有触发器，确保获取到最新的 triggerid
            try:
                all_triggers = self.zabbix_client.api.trigger.get(
                    hostids=host_id,
                    output=["triggerid", "description"]
                )
                # 构建触发器名称到 triggerid 的映射
                trigger_name_to_id = {trigger["description"]: trigger["triggerid"] for trigger in all_triggers}
                logger.info(f"重新获取到 {len(all_triggers)} 个触发器，构建了名称到 triggerid 的映射")
                
                # 再次处理所有带依赖的触发器
                for name, trigger_config in target_triggers.items():
                    if "dependencies" in trigger_config:
                        dependency_names = trigger_config["dependencies"]
                        dependency_ids = []
                        for dep_name in dependency_names:
                            if dep_name in trigger_name_to_id:
                                dependency_ids.append(trigger_name_to_id[dep_name])
                            else:
                                logger.warning(f"依赖的触发器 {dep_name} 不存在，无法设置依赖关系")
                        
                        if dependency_ids:
                            # 查找当前触发器的 triggerid
                            if name in trigger_name_to_id:
                                trigger_id = trigger_name_to_id[name]
                                # 构建更新数据
                                update_data = {
                                    "triggerid": trigger_id,
                                    "dependencies": dependency_ids
                                }
                                # 更新触发器依赖关系
                                try:
                                    self.zabbix_client.api.trigger.update(update_data)
                                    logger.info(f"更新触发器 {name} 的依赖关系成功")
                                except Exception as e:
                                    logger.error(f"更新触发器 {name} 的依赖关系失败: {e}")
            except Exception as e:
                logger.error(f"执行二次更新失败: {e}")
    
    def _sync_discovery_rules(self, host_id: str, host_name: str, discovery_rules: List[Dict[str, Any]], dry_run: bool):
        """同步自动发现规则
        
        Args:
            host_id: 主机 ID
            host_name: 主机名
            discovery_rules: 目标自动发现规则配置列表
            dry_run: 是否模拟运行
        """
        # 获取当前自动发现规则
        current_rules = self.zabbix_client.get_managed_discovery_rules(host_id)
        # 只处理有ruleid或itemid键的规则（不同Zabbix版本可能返回不同的字段名）
        current_rules_map = {}
        for rule in current_rules:
            if "key_" in rule:
                key = rule["key_"]
                # 检查规则是否有ruleid或itemid字段
                if "ruleid" in rule:
                    current_rules_map[key] = rule
                elif "itemid" in rule:
                    # 某些Zabbix版本可能返回itemid而不是ruleid
                    rule["ruleid"] = rule["itemid"]
                    current_rules_map[key] = rule
        
        # 获取主机接口 ID
        interface_id = self.zabbix_client.get_host_interface_id(host_id)
        if not interface_id:
            logger.error(f"无法获取主机接口 ID，自动发现规则同步将跳过")
            return
        
        # 同步目标自动发现规则
        for rule_config in discovery_rules:
            try:
                rule_name = rule_config.get("name")
                rule_key = rule_config.get("key")
                
                if not rule_key:
                    logger.error(f"LLD 规则缺少 key: {rule_name}")
                    continue
                
                # 构建规则数据
                rule_data = {
                    "hostid": host_id,
                    "name": rule_name,
                    "key_": rule_key,
                    "type": 0,  # 0 表示 Zabbix agent 类型
                    "delay": rule_config.get("delay", "1m")
                }

                # 添加 filter 过滤条件（如果存在）
                filter_config = rule_config.get("filter", {})
                if filter_config.get("conditions"):
                    rule_data["filter"] = {
                        "evaltype": filter_config.get("evaltype", 0),
                        "conditions": filter_config["conditions"]
                    }
                    logger.info(f"规则 {rule_name} 包含 {len(filter_config['conditions'])} 个过滤条件")
                    for cond in filter_config["conditions"]:
                        logger.debug(f"  过滤条件: macro={cond['macro']}, value={cond['value']}, operator={cond['operator']}")
                
                # 尝试同时添加不同格式的接口参数，以适应不同 Zabbix 版本
                if interface_id:
                    # 某些 Zabbix 版本可能使用 interfaceid
                    rule_data["interfaceid"] = interface_id
                    # 某些 Zabbix 版本可能使用 interface
                    rule_data["interface"] = interface_id
                
                rule_id = None
                if rule_key in current_rules_map:
                    # 规则已存在，检查是否需要更新
                    current_rule = current_rules_map[rule_key]
                    rule_id = current_rule["ruleid"]
                    
                    # 计算指纹
                    target_fingerprint = self.zabbix_client.calculate_fingerprint(rule_data)
                    current_fingerprint = self.zabbix_client.calculate_fingerprint(current_rule)
                    
                    if target_fingerprint != current_fingerprint:
                        if not dry_run:
                            success = self.zabbix_client.update_discovery_rule(rule_id, rule_data)
                            if success:
                                self.report_generator.log_change("updated", "discovery_rule", rule_name)
                        else:
                            self.report_generator.log_change("updated", "discovery_rule", rule_name)
                else:
                    # 创建新自动发现规则
                    if not dry_run:
                        rule_id = self.zabbix_client.create_discovery_rule(rule_data)
                        if rule_id:
                            self.report_generator.log_change("created", "discovery_rule", rule_name)
                        else:
                            # 如果创建失败，可能是因为规则已存在，尝试通过key获取规则ID
                            logger.warning(f"创建自动发现规则失败，尝试通过key获取规则ID: {rule_key}")
                            try:
                                rules = self.zabbix_client.api.discoveryrule.get(
                                    hostids=host_id,
                                    filter={"key_": rule_key},
                                    output=["ruleid"]
                                )
                                if rules and "ruleid" in rules[0]:
                                    rule_id = rules[0]["ruleid"]
                                    logger.info(f"通过key获取到规则ID: {rule_id}")
                                else:
                                    logger.error(f"通过key获取的规则没有ruleid键: {rules}")
                            except ZabbixAPIException as e:
                                logger.error(f"通过key获取规则ID失败: {e}")
                    else:
                        self.report_generator.log_change("created", "discovery_rule", rule_name)
                        # 在dry_run模式下，为了模拟原型同步，使用一个临时的rule_id
                        rule_id = "temp_rule_id"
                
                # 同步监控项原型
                if rule_id:
                    item_prototypes = rule_config.get("item_prototypes", [])
                    if item_prototypes:
                        try:
                            self._sync_item_prototypes(rule_id, host_id, interface_id, host_name, item_prototypes, dry_run)
                            logger.info(f"同步了 {len(item_prototypes)} 个监控项原型到规则 {rule_name}")
                        except Exception as e:
                            logger.error(f"同步监控项原型失败: {e}")
                
                # 同步触发器原型（从 rule 级别）
                if rule_id:
                    rule_trigger_prototypes = rule_config.get("trigger_prototypes", [])
                    if rule_trigger_prototypes:
                        try:
                            self._sync_trigger_prototypes(rule_id, host_id, host_name, rule_trigger_prototypes, dry_run)
                            logger.info(f"同步了 {len(rule_trigger_prototypes)} 个触发器原型到规则 {rule_name}")
                        except Exception as e:
                            logger.error(f"同步触发器原型失败: {e}")
            except Exception as e:
                logger.error(f"同步 LLD 规则失败: {e}")
                # 跳过该规则下的所有原型同步，但不中断其他规则
                continue
        
        # 清理多余的规则
        target_rule_keys = {rule.get("key") for rule in discovery_rules}
        for rule_key, rule in current_rules_map.items():
            if rule_key not in target_rule_keys:
                if not dry_run:
                    try:
                        # 删除规则（会级联删除关联的原型）
                        delete_id = rule.get("itemid") or rule.get("ruleid")
                        if delete_id:
                            self.zabbix_client.api.discoveryrule.delete([delete_id])
                            self.report_generator.log_change("deleted", "discovery_rule", rule["name"])
                    except ZabbixAPIException as e:
                        logger.error(f"删除 LLD 规则失败: {e}")
                else:
                    self.report_generator.log_change("deleted", "discovery_rule", rule["name"])
    
    def _sync_web_scenarios(self, host_id: str, host_name: str, web_scenarios: List[Dict[str, Any]], dry_run: bool):
        """同步 web 场景
        
        Args:
            host_id: 主机 ID
            host_name: 主机名
            web_scenarios: 目标 web 场景配置列表
            dry_run: 是否模拟运行
        """
        # 获取当前 web 场景
        current_scenarios = self.zabbix_client.get_managed_web_scenarios(host_id)
        current_scenarios_map = {scenario["name"]: scenario for scenario in current_scenarios}
        
        # 同步目标 web 场景
        for scenario_config in web_scenarios:
            try:
                scenario_name = scenario_config.get("name")
                scenario_key = scenario_config.get("key")
                
                if not scenario_name:
                    logger.error("Web 场景缺少 name")
                    continue
                
                # 构建 web 场景数据
                scenario_data = {
                    "hostid": host_id,
                    "name": scenario_name,
                    "key_": scenario_key,
                    "delay": scenario_config.get("delay", "5m"),
                    "status": scenario_config.get("status", 0),
                    "steps": scenario_config.get("steps", [])
                }
                
                scenario_id = None
                if scenario_name in current_scenarios_map:
                    # 场景已存在，检查是否需要更新
                    current_scenario = current_scenarios_map[scenario_name]
                    scenario_id = current_scenario["httptestid"]
                    
                    # 计算指纹
                    target_fingerprint = self.zabbix_client.calculate_fingerprint(scenario_data)
                    current_fingerprint = self.zabbix_client.calculate_fingerprint(current_scenario)
                    
                    if target_fingerprint != current_fingerprint:
                        if not dry_run:
                            success = self.zabbix_client.update_web_scenario(scenario_id, scenario_data)
                            if success:
                                self.report_generator.log_change("updated", "web_scenario", scenario_name)
                        else:
                            self.report_generator.log_change("updated", "web_scenario", scenario_name)
                else:
                    # 创建新 web 场景
                    if not dry_run:
                        scenario_id = self.zabbix_client.create_web_scenario(scenario_data)
                        if scenario_id:
                            self.report_generator.log_change("created", "web_scenario", scenario_name)
                    else:
                        self.report_generator.log_change("created", "web_scenario", scenario_name)
                
                # 同步 web 场景的触发器
                if scenario_id and not dry_run:
                    # 这里可以添加同步 web 场景触发器的逻辑
                    pass
            except ZabbixAPIException as e:
                logger.error(f"同步 web 场景失败: {e}")
                # 跳过该场景，但不中断其他场景
                continue
        
        # 清理多余的 web 场景
        target_scenario_names = {scenario.get("name") for scenario in web_scenarios}
        for scenario_name, scenario in current_scenarios_map.items():
            if scenario_name not in target_scenario_names:
                if not dry_run:
                    try:
                        success = self.zabbix_client.delete_web_scenario(scenario["httptestid"])
                        if success:
                            self.report_generator.log_change("deleted", "web_scenario", scenario_name)
                    except ZabbixAPIException as e:
                        logger.error(f"删除 web 场景失败: {e}")
                else:
                    self.report_generator.log_change("deleted", "web_scenario", scenario_name)
    
    def _sync_item_prototypes(self, rule_id: str, host_id: str, interface_id: str, host_name: str, item_prototypes: List[Dict[str, Any]], dry_run: bool):
        """同步监控项原型
        
        Args:
            rule_id: 规则 ID
            host_id: 主机 ID
            interface_id: 接口 ID
            host_name: 主机名
            item_prototypes: 监控项原型列表
            dry_run: 是否模拟运行
        """
        # 初始化当前原型映射
        current_prototypes_map = {}
        
        # 只有在非dry_run模式且rule_id不是临时ID时，才获取当前原型
        if not dry_run and rule_id != "temp_rule_id":
            # 获取当前监控项原型
            current_prototypes = self.zabbix_client.get_item_prototypes(rule_id)
            current_prototypes_map = {proto["key_"]: proto for proto in current_prototypes}
        
        # 同步目标监控项原型
        for proto_config in item_prototypes:
            try:
                proto_name = proto_config.get("name")
                proto_key = proto_config.get("key")
                
                if not proto_key:
                    logger.error(f"监控项原型缺少 key: {proto_name}")
                    continue
                
                # 构建原型数据
                # 确保delay有有效的值
                delay = proto_config.get("delay", "1m")
                if delay == 0 or delay == "0":
                    delay = "1m"
                
                proto_data = {
                    "ruleid": rule_id,
                    "hostid": host_id,
                    "name": proto_name,
                    "key_": proto_key,
                    "type": proto_config.get("type", 0),  # 支持不同类型，包括 18（Dependent item）
                    "value_type": proto_config.get("value_type", 0),
                    "delay": delay,
                    "units": proto_config.get("units", "")
                }
                
                # 添加预处理步骤
                if "preprocessing" in proto_config:
                    proto_data["preprocessing"] = proto_config["preprocessing"]
                
                # 对于 Dependent item (type 18)，添加 interfaceid 和 master_itemid
                if proto_config.get("type") == 18:
                    # 添加接口 ID
                    proto_data["interfaceid"] = interface_id
                    # 处理 master_item
                    if "master_item" in proto_config:
                        master_key = proto_config["master_item"]
                        # 查找主监控项原型的 ID
                        if master_key in current_prototypes_map:
                            proto_data["master_itemid"] = current_prototypes_map[master_key]["itemid"]
                        else:
                            logger.warning(f"主监控项原型 {master_key} 不存在，无法设置 master_itemid")
                # 对于 Calculated item (type 15)，添加 formula 参数
                elif proto_config.get("type") == 15:
                    # 添加接口 ID
                    proto_data["interfaceid"] = interface_id
                    # 添加 formula 参数
                    if "formula" in proto_config:
                        proto_data["formula"] = proto_config["formula"]
                    else:
                        logger.warning(f"计算型监控项原型缺少 formula 参数")
                else:
                    # 对于其他类型，添加接口 ID
                    proto_data["interfaceid"] = interface_id
                
                proto_id = None
                if proto_key in current_prototypes_map:
                    # 原型已存在，检查是否需要更新
                    current_proto = current_prototypes_map[proto_key]
                    proto_id = current_proto["itemid"]
                    
                    # 计算指纹
                    target_fingerprint = self.zabbix_client.calculate_fingerprint(proto_data)
                    current_fingerprint = self.zabbix_client.calculate_fingerprint(current_proto)
                    
                    if target_fingerprint != current_fingerprint:
                        if not dry_run:
                            # 更新原型
                            proto_data["itemid"] = proto_id
                            self.zabbix_client.api.itemprototype.update(proto_data)
                            self.report_generator.log_change("updated", "item_prototype", proto_name)
                        else:
                            self.report_generator.log_change("updated", "item_prototype", proto_name)
                else:
                    # 创建新监控项原型
                    if not dry_run and rule_id != "temp_rule_id":
                        proto_id = self.zabbix_client.create_item_prototype(proto_data)
                        if proto_id:
                            self.report_generator.log_change("created", "item_prototype", proto_name)
                    else:
                        self.report_generator.log_change("created", "item_prototype", proto_name)
                
                # 触发器原型已在 discovery rule 级别同步，此处不再处理
            except ZabbixAPIException as e:
                logger.error(f"同步监控项原型失败: {e}")
                continue
    
    def _sync_trigger_prototypes(self, rule_id: str, host_id: str, host_name: str, trigger_prototypes: List[Dict[str, Any]], dry_run: bool):
        """同步触发器原型
        
        Args:
            rule_id: 规则 ID
            host_id: 主机 ID
            host_name: 主机名
            trigger_prototypes: 触发器原型列表
            dry_run: 是否模拟运行
        """
        # 初始化当前原型映射
        current_prototypes_map = {}
        
        # 只有在非dry_run模式且rule_id不是临时ID时，才获取当前原型
        if not dry_run and rule_id != "temp_rule_id":
            # 获取当前触发器原型
            current_prototypes = self.zabbix_client.get_trigger_prototypes(rule_id)
            current_prototypes_map = {proto["description"]: proto for proto in current_prototypes}
        
        # 获取主机的所有监控项，用于构建item_key到itemid的映射
        item_key_to_id = {}
        if not dry_run:
            try:
                items = self.zabbix_client.api.item.get(
                    hostids=host_id,
                    output=["itemid", "key_"]
                )
                item_key_to_id = {item["key_"]: item["itemid"] for item in items}
                logger.info(f"获取到 {len(items)} 个监控项，构建了 item_key 到 itemid 的映射")
            except Exception as e:
                logger.error(f"获取监控项失败: {e}")
                item_key_to_id = {}
        
        # 同步目标触发器原型
        for proto_config in trigger_prototypes:
            try:
                description = proto_config.get("description")
                expression = proto_config.get("expression")
                priority = proto_config.get("priority", 3)
                
                if not description or not expression:
                    logger.error(f"触发器原型缺少必要字段")
                    continue
                
                # 处理表达式
                if expression:
                    # 替换宏变量为默认值
                    expression = self._replace_macros(expression)
                    # 处理监控项引用
                    import re
                    
                    # 首先将 {host:item_key} 替换为 {hostname:item_key} 格式
                    expression = expression.replace("{host:", f"{{{host_name}:")
                    logger.info(f"将触发器原型表达式中的 'host:' 替换为 '{host_name}:'，结果: {expression}")
                    
                    # 然后处理 {hostname:item_key} 格式，替换为 {itemid} 格式
                    host_item_matches = re.findall(r'\{[^:]+:([^}]+)\}', expression)
                    for match in host_item_matches:
                        # 跳过LLD宏变量，如 {#IFNAME}
                        if match.startswith('#'):
                            continue
                        if match in item_key_to_id:
                            # 替换为 {itemid} 格式
                            old_pattern = f'{{[^:]+:{match}}}'
                            new_pattern = f'{{{item_key_to_id[match]}}}'
                            # 使用正则替换，确保只替换完整的匹配项
                            expression = re.sub(rf'\{{[^:]+:{re.escape(match)}\}}', new_pattern, expression)
                            logger.info(f"替换触发器原型中的 {{hostname:{match}}} 为 {{itemid}} 格式: {new_pattern}")
                        else:
                            # 尝试直接使用数字作为itemid
                            if match.isdigit():
                                old_pattern = f'{{[^:]+:{match}}}'
                                new_pattern = f'{{{match}}}'
                                # 使用正则替换，确保只替换完整的匹配项
                                expression = re.sub(rf'\{{[^:]+:{re.escape(match)}\}}', new_pattern, expression)
                                logger.info(f"替换触发器原型中的 {{hostname:{match}}} 为 {{itemid}} 格式: {new_pattern}")
                    
                    # 再次检查并替换剩余的宏变量
                    expression = self._replace_macros(expression)
                    logger.info(f"最终处理后的触发器原型表达式: {expression}")
                    # 保留LLD宏变量，不做删除处理
                
                # 构建原型数据
                proto_data = {
                    "description": description,
                    "expression": expression,
                    "priority": priority
                }
                
                if description in current_prototypes_map:
                    # 原型已存在，检查是否需要更新
                    current_proto = current_prototypes_map[description]
                    
                    # 计算指纹
                    target_fingerprint = self.zabbix_client.calculate_fingerprint(proto_data)
                    current_fingerprint = self.zabbix_client.calculate_fingerprint(current_proto)
                    
                    if target_fingerprint != current_fingerprint:
                        if not dry_run:
                            # 更新原型
                            proto_data["triggerid"] = current_proto["triggerid"]
                            self.zabbix_client.api.triggerprototype.update(proto_data)
                            self.report_generator.log_change("updated", "trigger_prototype", description)
                        else:
                            self.report_generator.log_change("updated", "trigger_prototype", description)
                else:
                    # 创建新触发器原型
                    if not dry_run and rule_id != "temp_rule_id":
                        try:
                            proto_data = {
                                "description": description,
                                "expression": expression,
                                "priority": priority
                            }
                            proto_id = self.zabbix_client.create_trigger_prototype(proto_data)
                            if proto_id:
                                self.report_generator.log_change("created", "trigger_prototype", description)
                        except Exception as e:
                            logger.error(f"创建触发器原型失败: {e}")
                    else:
                        self.report_generator.log_change("created", "trigger_prototype", description)
            except Exception as e:
                logger.error(f"同步触发器原型失败: {e}")
                continue
    
    def _validate_sync(self, host_id: str, host_name: str, target_items: Dict[str, Any], target_triggers: Dict[str, Any]):
        """验证同步结果
        
        Args:
            host_id: 主机 ID
            host_name: 主机名
            target_items: 目标监控项配置
            target_triggers: 目标触发器配置
        """
        logger.info(f"开始验证主机 {host_name} 的同步结果...")
        
        # 验证 1: 检查依赖监控项的 master_itemid 是否正确设置
        try:
            # 获取所有监控项
            items = self.zabbix_client.api.item.get(
                hostids=host_id,
                output=["itemid", "key_", "master_itemid", "type"]
            )
            
            # 统计依赖监控项
            dependent_items = [item for item in items if item.get("type") in [15, 18] and item.get("master_itemid")]
            missing_master_items = [item for item in items if item.get("type") in [15, 18] and not item.get("master_itemid")]
            
            logger.info(f"验证监控项依赖关系:")
            logger.info(f"  总监控项数: {len(items)}")
            logger.info(f"  依赖监控项数: {len(dependent_items)}")
            logger.info(f"  缺少 master_itemid 的依赖监控项数: {len(missing_master_items)}")
            
            if missing_master_items:
                logger.warning("以下依赖监控项缺少 master_itemid:")
                for item in missing_master_items:
                    logger.warning(f"  - {item['key_']} (ID: {item['itemid']})")
            else:
                logger.info("所有依赖监控项的 master_itemid 都已正确设置")
        except Exception as e:
            logger.error(f"验证监控项依赖关系失败: {e}")
        
        # 验证 2: 检查触发器依赖关系
        try:
            # 获取所有触发器
            triggers = self.zabbix_client.api.trigger.get(
                hostids=host_id,
                output=["triggerid", "description"],
                selectDependencies=["triggerid"]
            )
            
            # 统计有依赖的触发器
            triggers_with_dependencies = [trigger for trigger in triggers if trigger.get("dependencies")]
            total_dependencies = sum(len(trigger.get("dependencies", [])) for trigger in triggers)
            
            # 统计目标配置中应该有依赖的触发器
            target_triggers_with_deps = [name for name, config in target_triggers.items() if "dependencies" in config]
            expected_dependencies = sum(len(config.get("dependencies", [])) for config in target_triggers.values() if "dependencies" in config)
            
            logger.info(f"验证触发器依赖关系:")
            logger.info(f"  总触发器数: {len(triggers)}")
            logger.info(f"  有依赖的触发器数: {len(triggers_with_dependencies)}")
            logger.info(f"  实际依赖关系数: {total_dependencies}")
            logger.info(f"  目标配置中有依赖的触发器数: {len(target_triggers_with_deps)}")
            logger.info(f"  期望依赖关系数: {expected_dependencies}")
            
            if total_dependencies == expected_dependencies:
                logger.info("触发器依赖关系数量与期望一致")
            else:
                logger.warning(f"触发器依赖关系数量与期望不一致: 实际 {total_dependencies}, 期望 {expected_dependencies}")
        except Exception as e:
            logger.error(f"验证触发器依赖关系失败: {e}")
        
        logger.info(f"主机 {host_name} 的同步验证完成")
    
    def sync_all_hosts(self, config: Dict[str, Any], dry_run: bool = False, workers: int = 5):
        """同步所有主机
        
        Args:
            config: 总配置
            dry_run: 是否模拟运行
            workers: 并发线程数
        """
        hosts = config.get("hosts", {})
        host_names = list(hosts.keys())
        
        logger.info(f"开始同步 {len(host_names)} 台主机")
        
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(self.sync_host, host_name, config, dry_run)
                for host_name in host_names
            ]
            
            # 等待所有任务完成
            for future in futures:
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"同步主机时出错: {e}")
        
        logger.info("所有主机同步完成")


class StatusVerifier:
    """状态核验器 - 从 Zabbix 拉取实际状态并与复核表比对"""

    def __init__(self, zabbix_client: ZabbixClient, db_config: Dict[str, Any], db_conn=None):
        """初始化状态核验器

        Args:
            zabbix_client: Zabbix 客户端
            db_config: 数据库配置
            db_conn: 可选的已有数据库连接（用于 Web UI 复用连接）
        """
        self.zabbix_client = zabbix_client
        self.db_config = db_config
        self.connection = db_conn  # 允许外部传入已有连接

    def _get_db_connection(self):
        """获取数据库连接"""
        if self.connection and not self.connection.closed:
            return self.connection

        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                conn_params = {
                    'host': self.db_config.get('host', 'localhost'),
                    'port': self.db_config.get('port', 5432),
                    'database': self.db_config.get('database', 'zabbix_mac'),
                    'user': self.db_config.get('user', 'fan'),
                    'password': self.db_config.get('password', '')
                }
                self.connection = psycopg2.connect(**conn_params)
                self.connection.autocommit = True
                self.connection.set_client_encoding('UTF8')
                logger.info("StatusVerifier 成功连接到数据库")
                return self.connection
            except psycopg2.OperationalError as e:
                logger.error(f"数据库连接失败 (尝试 {attempt+1}/{MAX_RETRY_ATTEMPTS}): {e}")
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    time.sleep(RETRY_DELAY)
                else:
                    raise
            except Exception as e:
                logger.error(f"连接数据库时发生未知错误: {e}")
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    time.sleep(RETRY_DELAY)
                else:
                    raise

    def verify_items(self, host_ip: str) -> Dict[str, int]:
        """核验单个主机的监控项

        Args:
            host_ip: 主机 IP（Zabbix 中的 host name）

        Returns:
            统计字典 {'verified': n, 'mismatch': n, 'not_found': n}
        """
        stats = {'verified': 0, 'mismatch': 0, 'not_found': 0}

        # 1. 从 DB 获取该 host_ip 的所有 items_review 记录
        conn = self._get_db_connection()
        review_items = []
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(
                "SELECT id, item_key, name, type, value_type, delay FROM items_review WHERE host_ip = %s",
                (host_ip,)
            )
            review_items = cur.fetchall()

        if not review_items:
            logger.info(f"主机 {host_ip} 的 items_review 表中没有记录，跳过监控项核验")
            return stats

        logger.info(f"开始核验主机 {host_ip} 的 {len(review_items)} 个监控项...")

        # 2. 获取 Zabbix 主机 ID
        host_id = self.zabbix_client.get_host_id(host_ip)
        if not host_id:
            logger.warning(f"主机 {host_ip} 在 Zabbix 中不存在，所有监控项标记为 not_found")
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE items_review SET status_verification = 'not_found' WHERE host_ip = %s",
                    (host_ip,)
                )
            stats['not_found'] = len(review_items)
            return stats

        # 3. 从 Zabbix 拉取实际监控项
        try:
            zabbix_items = self.zabbix_client.api.item.get(
                hostids=host_id,
                output=["itemid", "key_", "name", "type", "value_type", "delay"]
            )
            zabbix_items_map = {item["key_"]: item for item in zabbix_items}
            logger.info(f"从 Zabbix 获取到 {len(zabbix_items)} 个监控项")
        except ZabbixAPIException as e:
            logger.error(f"从 Zabbix 获取监控项失败: {e}")
            return stats
        except Exception as e:
            logger.error(f"从 Zabbix 获取监控项时发生未知错误: {e}")
            return stats

        # 4. 逐条比对
        updates = []
        for ritem in review_items:
            item_key = ritem['item_key']
            if item_key not in zabbix_items_map:
                updates.append(('not_found', ritem['id']))
                stats['not_found'] += 1
                logger.debug(f"  监控项 {item_key}: not_found")
            else:
                zitem = zabbix_items_map[item_key]
                # 比对关键字段：name, type, value_type, delay
                z_name = str(zitem.get('name', ''))
                z_type = int(zitem.get('type', -1))
                z_value_type = int(zitem.get('value_type', -1))
                z_delay = str(zitem.get('delay', ''))

                r_name = str(ritem.get('name', ''))
                r_type = int(ritem.get('type', -1))
                r_value_type = int(ritem.get('value_type', -1))
                r_delay = str(ritem.get('delay', ''))

                mismatch_fields = []
                if z_name != r_name:
                    mismatch_fields.append(f"name: '{r_name}' vs '{z_name}'")
                if z_type != r_type:
                    mismatch_fields.append(f"type: {r_type} vs {z_type}")
                if z_value_type != r_value_type:
                    mismatch_fields.append(f"value_type: {r_value_type} vs {z_value_type}")
                if z_delay.rstrip('s') != r_delay.rstrip('s'):
                    mismatch_fields.append(f"delay: '{r_delay}' vs '{z_delay}'")

                if mismatch_fields:
                    updates.append(('mismatch', ritem['id']))
                    stats['mismatch'] += 1
                    logger.info(f"  监控项 {item_key}: mismatch — {', '.join(mismatch_fields)}")
                else:
                    updates.append(('verified', ritem['id']))
                    stats['verified'] += 1

        # 5. 批量更新
        with conn.cursor() as cur:
            for status, review_id in updates:
                cur.execute(
                    "UPDATE items_review SET status_verification = %s WHERE id = %s",
                    (status, review_id)
                )

        logger.info(f"主机 {host_ip} 监控项核验完成: verified={stats['verified']}, "
                    f"mismatch={stats['mismatch']}, not_found={stats['not_found']}")
        return stats

    def verify_triggers(self, host_ip: str) -> Dict[str, int]:
        """核验单个主机的触发器（仅核验存在性）

        Args:
            host_ip: 主机 IP（Zabbix 中的 host name）

        Returns:
            统计字典 {'verified': n, 'not_found': n}
        """
        stats = {'verified': 0, 'not_found': 0}

        # 1. 从 DB 获取该 host_ip 的所有 triggers_review 记录
        conn = self._get_db_connection()
        review_triggers = []
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(
                "SELECT id, name FROM triggers_review WHERE host_ip = %s",
                (host_ip,)
            )
            review_triggers = cur.fetchall()

        if not review_triggers:
            logger.info(f"主机 {host_ip} 的 triggers_review 表中没有记录，跳过触发器核验")
            return stats

        logger.info(f"开始核验主机 {host_ip} 的 {len(review_triggers)} 个触发器...")

        # 2. 获取 Zabbix 主机 ID
        host_id = self.zabbix_client.get_host_id(host_ip)
        if not host_id:
            logger.warning(f"主机 {host_ip} 在 Zabbix 中不存在，所有触发器标记为 not_found")
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE triggers_review SET status_verification = 'not_found' WHERE host_ip = %s",
                    (host_ip,)
                )
            stats['not_found'] = len(review_triggers)
            return stats

        # 3. 从 Zabbix 拉取实际触发器
        try:
            zabbix_triggers = self.zabbix_client.api.trigger.get(
                hostids=host_id,
                output=["triggerid", "description"]
            )
            zabbix_triggers_set = {trigger["description"] for trigger in zabbix_triggers}
            logger.info(f"从 Zabbix 获取到 {len(zabbix_triggers)} 个触发器")
        except ZabbixAPIException as e:
            logger.error(f"从 Zabbix 获取触发器失败: {e}")
            return stats
        except Exception as e:
            logger.error(f"从 Zabbix 获取触发器时发生未知错误: {e}")
            return stats

        # 4. 逐条比对（仅存在性检查）
        updates = []
        for rtrigger in review_triggers:
            trigger_name = rtrigger['name']
            if trigger_name in zabbix_triggers_set:
                updates.append(('verified', rtrigger['id']))
                stats['verified'] += 1
            else:
                updates.append(('not_found', rtrigger['id']))
                stats['not_found'] += 1
                logger.debug(f"  触发器 {trigger_name}: not_found")

        # 5. 批量更新
        with conn.cursor() as cur:
            for status, review_id in updates:
                cur.execute(
                    "UPDATE triggers_review SET status_verification = %s WHERE id = %s",
                    (status, review_id)
                )

        logger.info(f"主机 {host_ip} 触发器核验完成: verified={stats['verified']}, "
                    f"not_found={stats['not_found']}")
        return stats

    def verify_all(self):
        """核验所有主机的复核表

        遍历 items_review 和 triggers_review 中出现的所有唯一 host_ip，
        对每个主机执行监控项和触发器核验，最后打印汇总报告。
        """
        conn = self._get_db_connection()

        # 收集所有需要核验的 host_ip
        host_ips = []
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("""
                SELECT DISTINCT host_ip FROM items_review
                UNION
                SELECT DISTINCT host_ip FROM triggers_review
                ORDER BY host_ip
            """)
            rows = cur.fetchall()
            host_ips = [row['host_ip'] for row in rows]

        if not host_ips:
            logger.warning("复核表中没有任何记录，跳过核验")
            return

        logger.info(f"=" * 60)
        logger.info(f"开始核验 {len(host_ips)} 台主机的复核表状态")
        logger.info(f"=" * 60)

        total_item_stats = {'verified': 0, 'mismatch': 0, 'not_found': 0}
        total_trigger_stats = {'verified': 0, 'not_found': 0}

        for host_ip in host_ips:
            logger.info(f"\n--- 核验主机: {host_ip} ---")

            # 核验监控项
            item_stats = self.verify_items(host_ip)
            total_item_stats['verified'] += item_stats['verified']
            total_item_stats['mismatch'] += item_stats['mismatch']
            total_item_stats['not_found'] += item_stats['not_found']

            # 核验触发器
            trigger_stats = self.verify_triggers(host_ip)
            total_trigger_stats['verified'] += trigger_stats['verified']
            total_trigger_stats['not_found'] += trigger_stats['not_found']

        # 打印汇总报告
        logger.info(f"\n" + "=" * 60)
        logger.info("状态核验汇总报告")
        logger.info("=" * 60)
        logger.info(f"监控项核验: verified={total_item_stats['verified']}, "
                    f"mismatch={total_item_stats['mismatch']}, "
                    f"not_found={total_item_stats['not_found']}")
        logger.info(f"触发器核验: verified={total_trigger_stats['verified']}, "
                    f"not_found={total_trigger_stats['not_found']}")
        logger.info(f"总计核验记录: {sum(total_item_stats.values()) + sum(total_trigger_stats.values())}")
        logger.info("=" * 60)

        # 关闭数据库连接
        if self.connection and not self.connection.closed:
            self.connection.close()
            self.connection = None

    def verify_web_scenarios(self, host_ip: str) -> Dict[str, int]:
        """核验单个主机的 Web 场景

        Args:
            host_ip: 主机 IP（Zabbix 中的 host name）

        Returns:
            统计字典 {'verified': n, 'mismatch': n, 'not_found': n}
        """
        stats = {'verified': 0, 'mismatch': 0, 'not_found': 0}

        conn = self._get_db_connection()
        review_scenarios = []
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(
                "SELECT id, host, name, url, status_code FROM webscenario_items_review WHERE host = %s",
                (host_ip,)
            )
            review_scenarios = cur.fetchall()

        if not review_scenarios:
            logger.info(f"主机 {host_ip} 的 webscenario_items_review 表中没有记录，跳过 Web 场景核验")
            return stats

        logger.info(f"开始核验主机 {host_ip} 的 {len(review_scenarios)} 个 Web 场景...")

        # 获取 Zabbix 主机 ID
        host_id = self.zabbix_client.get_host_id(host_ip)
        if not host_id:
            logger.warning(f"主机 {host_ip} 在 Zabbix 中不存在，所有 Web 场景标记为 not_found")
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE webscenario_items_review SET status_verification = 'not_found' WHERE host = %s",
                    (host_ip,)
                )
            stats['not_found'] = len(review_scenarios)
            return stats

        # 从 Zabbix 拉取实际 Web 场景
        try:
            zabbix_scenarios = self.zabbix_client.api.httptest.get(
                hostids=host_id,
                output=["httptestid", "name"],
                selectSteps="extend"
            )
            # 构建 name -> {name, url, status_codes} 的映射
            zabbix_scenarios_map = {}
            for scenario in zabbix_scenarios:
                name = scenario.get("name", "")
                steps = scenario.get("steps", [])
                if steps:
                    first_step = steps[0]
                    zabbix_scenarios_map[name] = {
                        "url": first_step.get("url", ""),
                        "status_codes": first_step.get("status_codes", ""),
                    }
                else:
                    zabbix_scenarios_map[name] = {"url": "", "status_codes": ""}
            logger.info(f"从 Zabbix 获取到 {len(zabbix_scenarios)} 个 Web 场景")
        except ZabbixAPIException as e:
            logger.error(f"从 Zabbix 获取 Web 场景失败: {e}")
            return stats
        except Exception as e:
            logger.error(f"从 Zabbix 获取 Web 场景时发生未知错误: {e}")
            return stats

        # 逐条比对
        updates = []
        for rscenario in review_scenarios:
            scenario_name = rscenario['name']
            if scenario_name not in zabbix_scenarios_map:
                updates.append(('not_found', rscenario['id']))
                stats['not_found'] += 1
                logger.debug(f"  Web 场景 {scenario_name}: not_found")
            else:
                zs = zabbix_scenarios_map[scenario_name]
                r_url = str(rscenario.get('url', '')).strip()
                z_url = str(zs.get('url', '')).strip()
                r_status = str(rscenario.get('status_code', '200')).strip()
                z_status = str(zs.get('status_codes', '200')).strip()

                if r_url != z_url or r_status != z_status:
                    updates.append(('mismatch', rscenario['id']))
                    stats['mismatch'] += 1
                    logger.info(f"  Web 场景 {scenario_name}: mismatch — "
                                f"url: '{r_url}' vs '{z_url}', status: '{r_status}' vs '{z_status}'")
                else:
                    updates.append(('verified', rscenario['id']))
                    stats['verified'] += 1

        # 批量更新
        with conn.cursor() as cur:
            for status, review_id in updates:
                cur.execute(
                    "UPDATE webscenario_items_review SET status_verification = %s WHERE id = %s",
                    (status, review_id)
                )

        logger.info(f"主机 {host_ip} Web 场景核验完成: verified={stats['verified']}, "
                    f"mismatch={stats['mismatch']}, not_found={stats['not_found']}")
        return stats

    def verify_item_prototypes(self, host_ip: str) -> Dict[str, int]:
        """核验单个主机的监控项原型

        通过 主机 → 发现规则 → 监控项原型 的路径进行比对。
        匹配方式: 按 item_prototype 的 key_ 匹配，比对 name/type/value_type/delay。

        Args:
            host_ip: 主机 IP（Zabbix 中的 host name）

        Returns:
            统计字典 {'verified': n, 'mismatch': n, 'not_found': n}
        """
        stats = {'verified': 0, 'mismatch': 0, 'not_found': 0}

        conn = self._get_db_connection()
        review_protos = []
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(
                "SELECT id, discovery_rule_id, host_ip, name, key, value_type, delay "
                "FROM item_prototypes_review WHERE host_ip = %s",
                (host_ip,)
            )
            review_protos = cur.fetchall()

        if not review_protos:
            logger.info(f"主机 {host_ip} 的 item_prototypes_review 表中没有记录，跳过监控项原型核验")
            return stats

        logger.info(f"开始核验主机 {host_ip} 的 {len(review_protos)} 个监控项原型...")

        # 获取 Zabbix 主机 ID
        host_id = self.zabbix_client.get_host_id(host_ip)
        if not host_id:
            logger.warning(f"主机 {host_ip} 在 Zabbix 中不存在，所有监控项原型标记为 not_found")
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE item_prototypes_review SET status_verification = 'not_found' WHERE host_ip = %s",
                    (host_ip,)
                )
            stats['not_found'] = len(review_protos)
            return stats

        # 按 discovery_rule_id 分组
        rule_ids = set(p['discovery_rule_id'] for p in review_protos)
        # 获取 discovery_rules 信息用于匹配 Zabbix 上的发现规则
        from collections import defaultdict
        rule_info = {}
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(
                "SELECT id, name, key FROM discovery_rules WHERE id = ANY(%s)",
                (list(rule_ids),)
            )
            for r in cur.fetchall():
                rule_info[r['id']] = r

        # 从 Zabbix 获取该主机所有发现规则
        try:
            zabbix_rules = self.zabbix_client.api.discoveryrule.get(
                hostids=host_id,
                output=["itemid", "key_", "name"]
            )
            zabbix_rules_map = {r["key_"]: r for r in zabbix_rules}
            logger.info(f"从 Zabbix 获取到 {len(zabbix_rules)} 个发现规则")
        except ZabbixAPIException as e:
            logger.error(f"从 Zabbix 获取发现规则失败: {e}")
            return stats
        except Exception as e:
            logger.error(f"从 Zabbix 获取发现规则时发生未知错误: {e}")
            return stats

        # 获取所有发现规则的监控项原型
        all_zabbix_protos = {}  # key_ -> item prototype
        for rule_key, zrule in zabbix_rules_map.items():
            try:
                zabbix_protos = self.zabbix_client.api.itemprototype.get(
                    discoveryids=zrule["itemid"],
                    output=["itemid", "key_", "name", "type", "value_type", "delay"]
                )
                for zp in zabbix_protos:
                    all_zabbix_protos[zp["key_"]] = zp
            except Exception as e:
                logger.warning(f"获取发现规则 {rule_key} 的监控项原型失败: {e}")

        logger.info(f"从 Zabbix 获取到共 {len(all_zabbix_protos)} 个监控项原型")

        # 逐条比对
        updates = []
        for rp in review_protos:
            proto_key = rp['key']
            if proto_key not in all_zabbix_protos:
                updates.append(('not_found', rp['id']))
                stats['not_found'] += 1
                logger.debug(f"  监控项原型 {proto_key}: not_found")
            else:
                zp = all_zabbix_protos[proto_key]
                z_name = str(zp.get('name', ''))
                z_type = int(zp.get('type', -1))
                z_value_type = int(zp.get('value_type', -1))
                z_delay = str(zp.get('delay', ''))

                r_name = str(rp.get('name', ''))
                r_type = int(rp.get('type', -1)) if rp.get('type') is not None else -1
                r_value_type = int(rp.get('value_type', -1)) if rp.get('value_type') is not None else -1
                r_delay = str(rp.get('delay', ''))

                mismatch_fields = []
                if z_name != r_name:
                    mismatch_fields.append(f"name: '{r_name}' vs '{z_name}'")
                if z_type != r_type:
                    mismatch_fields.append(f"type: {r_type} vs {z_type}")
                if z_value_type != r_value_type:
                    mismatch_fields.append(f"value_type: {r_value_type} vs {z_value_type}")
                if z_delay.rstrip('s') != r_delay.rstrip('s'):
                    mismatch_fields.append(f"delay: '{r_delay}' vs '{z_delay}'")

                if mismatch_fields:
                    updates.append(('mismatch', rp['id']))
                    stats['mismatch'] += 1
                    logger.info(f"  监控项原型 {proto_key}: mismatch — {', '.join(mismatch_fields)}")
                else:
                    updates.append(('verified', rp['id']))
                    stats['verified'] += 1

        # 批量更新
        with conn.cursor() as cur:
            for status, review_id in updates:
                cur.execute(
                    "UPDATE item_prototypes_review SET status_verification = %s WHERE id = %s",
                    (status, review_id)
                )

        logger.info(f"主机 {host_ip} 监控项原型核验完成: verified={stats['verified']}, "
                    f"mismatch={stats['mismatch']}, not_found={stats['not_found']}")
        return stats

    def verify_trigger_prototypes(self, host_ip: str) -> Dict[str, int]:
        """核验单个主机的触发器原型

        通过 主机 → 发现规则 → 触发器原型 的路径进行存在性比对。
        匹配方式: 按 trigger_prototype 的 description 匹配。

        Args:
            host_ip: 主机 IP（Zabbix 中的 host name）

        Returns:
            统计字典 {'verified': n, 'not_found': n}
        """
        stats = {'verified': 0, 'not_found': 0}

        conn = self._get_db_connection()
        review_protos = []
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(
                "SELECT id, discovery_rule_id, host_ip, description "
                "FROM trigger_prototypes_review WHERE host_ip = %s",
                (host_ip,)
            )
            review_protos = cur.fetchall()

        if not review_protos:
            logger.info(f"主机 {host_ip} 的 trigger_prototypes_review 表中没有记录，跳过触发器原型核验")
            return stats

        logger.info(f"开始核验主机 {host_ip} 的 {len(review_protos)} 个触发器原型...")

        # 获取 Zabbix 主机 ID
        host_id = self.zabbix_client.get_host_id(host_ip)
        if not host_id:
            logger.warning(f"主机 {host_ip} 在 Zabbix 中不存在，所有触发器原型标记为 not_found")
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE trigger_prototypes_review SET status_verification = 'not_found' WHERE host_ip = %s",
                    (host_ip,)
                )
            stats['not_found'] = len(review_protos)
            return stats

        # 从 Zabbix 获取该主机所有发现规则
        try:
            zabbix_rules = self.zabbix_client.api.discoveryrule.get(
                hostids=host_id,
                output=["itemid", "key_", "name"]
            )
            zabbix_rules_map = {r["key_"]: r for r in zabbix_rules}
            logger.info(f"从 Zabbix 获取到 {len(zabbix_rules)} 个发现规则")
        except ZabbixAPIException as e:
            logger.error(f"从 Zabbix 获取发现规则失败: {e}")
            return stats
        except Exception as e:
            logger.error(f"从 Zabbix 获取发现规则时发生未知错误: {e}")
            return stats

        # 获取所有发现规则的触发器原型
        all_zabbix_protos = set()  # set of descriptions
        for rule_key, zrule in zabbix_rules_map.items():
            try:
                zabbix_protos = self.zabbix_client.api.triggerprototype.get(
                    discoveryids=zrule["itemid"],
                    output=["triggerid", "description"]
                )
                for zp in zabbix_protos:
                    all_zabbix_protos.add(zp["description"])
            except Exception as e:
                logger.warning(f"获取发现规则 {rule_key} 的触发器原型失败: {e}")

        logger.info(f"从 Zabbix 获取到共 {len(all_zabbix_protos)} 个触发器原型")

        # 逐条比对（存在性检查）
        updates = []
        for rp in review_protos:
            proto_desc = rp['description']
            if proto_desc in all_zabbix_protos:
                updates.append(('verified', rp['id']))
                stats['verified'] += 1
            else:
                updates.append(('not_found', rp['id']))
                stats['not_found'] += 1
                logger.debug(f"  触发器原型 {proto_desc}: not_found")

        # 批量更新
        with conn.cursor() as cur:
            for status, review_id in updates:
                cur.execute(
                    "UPDATE trigger_prototypes_review SET status_verification = %s WHERE id = %s",
                    (status, review_id)
                )

        logger.info(f"主机 {host_ip} 触发器原型核验完成: verified={stats['verified']}, "
                    f"not_found={stats['not_found']}")
        return stats


class ZabbixUltimateAutomator:
    """Zabbix 自动化主类"""
    
    def __init__(self, zabbix_url: str, username: str, password: str, db_config: Optional[Dict[str, Any]] = None, dry_run: bool = False):
        """初始化自动化器
        
        Args:
            zabbix_url: Zabbix API URL
            username: 用户名
            password: 密码
            db_config: 数据库配置
            dry_run: 是否模拟运行
        """
        self.zabbix_client = ZabbixClient(zabbix_url, username, password, dry_run)
        self.config_loader = ConfigLoader(db_config=db_config)
        self.report_generator = ReportGenerator()
        self.sync_engine = SyncEngine(self.zabbix_client, self.config_loader, self.report_generator)
        self.dry_run = dry_run

    def verify_status(self):
        """核验复核表状态 — 从 Zabbix 拉取实际状态并与 items_review、triggers_review 对比"""
        logger.info("开始状态核验...")
        verifier = StatusVerifier(self.zabbix_client, self.config_loader.db_config)
        verifier.verify_all()
        logger.info("状态核验完成")
    
    def create_web_scenarios(self):
        """从 webscenario_items_review 表创建 web scenario"""
        try:
            logger.info("开始创建 web scenario...")
            
            # 获取 webscenario_items_review 数据
            webscenario_items = self.config_loader.get_webscenario_items_review()
            if not webscenario_items:
                logger.warning("没有获取到已确认的 webscenario_items_review 数据")
                return
            
            # 默认参数
            default_agent = 0
            default_retries = 1
            default_timeout = 30
            default_follow_redirects = 1
            default_applicationid = "166340"
            
            # 遍历 webscenario_items_review 数据
            for item in webscenario_items:
                # 获取主机 ID
                host_id = self.zabbix_client.get_host_id(item.get("host", "Zabbix server"))
                if not host_id:
                    logger.error(f"无法获取主机 {item.get('host', 'Zabbix server')} 的 ID")
                    continue
                
                # 构建 scenario 数据
                scenario_data = {
                    "name": item.get("name"),
                    "hostid": host_id,
                    "agent": str(default_agent),  # 转换为字符串类型
                    "retries": str(default_retries),  # 转换为字符串类型
                    "steps": [{
                        "no": 1,
                        "name": item.get("name"),
                        "url": item.get("url"),
                        "timeout": str(default_timeout),  # 转换为字符串类型
                        "status_codes": item.get("status_code", "200"),
                        "follow_redirects": str(default_follow_redirects)  # 转换为字符串类型
                    }]
                }
                
                # 创建 web scenario
                scenario_id = self.zabbix_client.create_web_scenario(scenario_data)
                if scenario_id:
                    logger.info(f"成功创建 web scenario: {item.get('name')}")
            
            logger.info("web scenario 创建完成！")
        except Exception as e:
            logger.error(f"创建 web scenario 失败: {e}")
    
    def create_web_scenario_triggers(self):
        """为 web scenario 创建触发器"""
        try:
            logger.info("开始为 web scenario 创建触发器...")
            
            # 获取 webscenario_items_review 数据
            webscenario_items = self.config_loader.get_webscenario_items_review()
            if not webscenario_items:
                logger.warning("没有获取到已确认的 webscenario_items_review 数据")
                return
            
            # 默认参数
            default_priority = 2  # 一般严重度
            default_status = 0  # 启用
            
            # 遍历 webscenario_items_review 数据
            for item in webscenario_items:
                # 获取主机 ID
                host_name = item.get("host", "Zabbix server")
                host_id = self.zabbix_client.get_host_id(host_name)
                if not host_id:
                    logger.error(f"无法获取主机 {host_name} 的 ID")
                    continue
                
                # 获取 web scenario 名称
                scenario_name = item.get("name")
                if not scenario_name:
                    logger.error("web scenario 名称为空")
                    continue
                
                # 构建触发器数据
                # 注意：Zabbix 5.0 API 创建触发器时不需要指定 hostid 或 hosts 参数
                # 触发器会根据表达式中的主机引用自动关联到相应的主机
                trigger_data = {
                    "description": f"Web 场景 {scenario_name} 失败",
                    "expression": f"{{{host_name}:web.test.fail[{scenario_name}].count(#3,0,ne)}}>2",
                    "priority": default_priority,
                    "status": default_status
                }
                
                # 创建触发器
                trigger_id = self.zabbix_client.create_trigger(trigger_data)
                if trigger_id:
                    logger.info(f"成功为 web scenario 创建触发器: {scenario_name}")
            
            logger.info("web scenario 触发器创建完成！")
        except Exception as e:
            logger.error(f"为 web scenario 创建触发器失败: {e}")
    
    def run(self, dry_run: bool = False, workers: int = 5, initialize_reviews: bool = False,
            initialize_items_review: bool = False, initialize_triggers_review: bool = False,
            initialize_webscenario_items_review: bool = False,
            export_items_review: str = None, export_triggers_review: str = None,
            import_items_review: str = None, import_triggers_review: str = None,
            create_web_scenarios: bool = False, create_web_scenario_triggers: bool = False,
            verify_status: bool = False):
        """运行同步或初始化复核表

        Args:
            dry_run: 是否模拟运行
            workers: 并发线程数
            initialize_reviews: 是否初始化四个复核表（items_review、triggers_review、item_prototypes_review 和 trigger_prototypes_review）
            initialize_items_review: 是否只初始化 items_review 表
            initialize_triggers_review: 是否只初始化 triggers_review 表
            initialize_webscenario_items_review: 是否初始化 webscenario_items_review 表
            export_items_review: 导出 items_review 表到指定 Excel 文件
            export_triggers_review: 导出 triggers_review 表到指定 Excel 文件
            import_items_review: 从指定 Excel 文件导入数据到 items_review 表
            import_triggers_review: 从指定 Excel 文件导入数据到 triggers_review 表
            create_web_scenarios: 是否从 webscenario_items_review 表创建 web scenario
            create_web_scenario_triggers: 是否为 web scenario 创建触发器
            verify_status: 是否核验复核表状态（从 Zabbix 拉取实际状态对比）
        """
        if verify_status:
            self.verify_status()
            return

        if initialize_reviews:
            logger.info("开始初始化复核表...")
            success = self.config_loader.initialize_review_tables()
            if success:
                logger.info("复核表初始化成功")
            else:
                logger.error("复核表初始化失败")
            return
        
        if initialize_items_review:
            logger.info("开始初始化 items_review 表...")
            success = self.config_loader.initialize_items_review()
            if success:
                self.config_loader.connection.commit()
                logger.info("items_review 表初始化成功")
            else:
                logger.error("items_review 表初始化失败")
            return
        
        if initialize_triggers_review:
            logger.info("开始初始化 triggers_review 表...")
            success = self.config_loader.initialize_triggers_review()
            if success:
                self.config_loader.connection.commit()
                logger.info("triggers_review 表初始化成功")
            else:
                logger.error("triggers_review 表初始化失败")
            return
        
        if initialize_webscenario_items_review:
            logger.info("开始初始化 webscenario_items_review 表...")
            success = self.config_loader.initialize_webscenario_items_review()
            if success:
                logger.info("webscenario_items_review 表初始化成功")
            else:
                logger.error("webscenario_items_review 表初始化失败")
            return
        
        if export_items_review:
            success = self.config_loader.export_items_review_to_excel(export_items_review)
            if success:
                logger.info("items_review 表导出成功")
            else:
                logger.error("items_review 表导出失败")
            return
        
        if export_triggers_review:
            success = self.config_loader.export_triggers_review_to_excel(export_triggers_review)
            if success:
                logger.info("triggers_review 表导出成功")
            else:
                logger.error("triggers_review 表导出失败")
            return
        
        if import_items_review:
            success = self.config_loader.import_items_review_from_excel(import_items_review)
            if success:
                logger.info("items_review 表导入成功")
            else:
                logger.error("items_review 表导入失败")
            return
        
        if import_triggers_review:
            success = self.config_loader.import_triggers_review_from_excel(import_triggers_review)
            if success:
                logger.info("triggers_review 表导入成功")
            else:
                logger.error("triggers_review 表导入失败")
            return
        
        if create_web_scenarios:
            self.create_web_scenarios()
            return
        
        if create_web_scenario_triggers:
            self.create_web_scenario_triggers()
            return
        
        # 加载配置
        config = self.config_loader.load_config()
        if not config:
            logger.error("加载配置失败")
            return
        
        # 同步所有主机
        self.sync_engine.sync_all_hosts(config, dry_run, workers)
        
        # 生成报告
        report = self.report_generator.generate_report(format="table")
        logger.info(f"\n{report}")


def main():
    """主函数"""
    # 加载外部配置（优先从 --config 指定路径，否则 APP_CONFIG 环境变量，否则 config.yaml）
    import config_loader
    # 先用临时 parser 解析 --config，剩下的参数留给主 parser
    import argparse as argparse_module
    _pre_parser = argparse_module.ArgumentParser(add_help=False)
    _pre_parser.add_argument('--config', default=None, help='配置文件路径（默认: config.yaml）')
    _pre_args, _remaining = _pre_parser.parse_known_args()
    cfg = config_loader.load_config(_pre_args.config)

    parser = argparse_module.ArgumentParser(description="Zabbix Monitor as Code 自动化工具")
    
    # 操作模式选择
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument("--sync", action="store_true", help="执行同步操作")
    mode_group.add_argument("--initialize-reviews", action="store_true", help="初始化复核表（items_review、triggers_review、item_prototypes_review 和 trigger_prototypes_review）")
    mode_group.add_argument("--initialize-items-review", action="store_true", help="只初始化 items_review 表")
    mode_group.add_argument("--initialize-triggers-review", action="store_true", help="只初始化 triggers_review 表")
    mode_group.add_argument("--initialize-webscenario-items-review", action="store_true", help="初始化 webscenario_items_review 表")
    mode_group.add_argument("--export-items-review", type=str, metavar="FILE", help="导出 items_review 表到指定 Excel 文件")
    mode_group.add_argument("--export-triggers-review", type=str, metavar="FILE", help="导出 triggers_review 表到指定 Excel 文件")
    mode_group.add_argument("--import-items-review", type=str, metavar="FILE", help="从指定 Excel 文件导入数据到 items_review 表")
    mode_group.add_argument("--import-triggers-review", type=str, metavar="FILE", help="从指定 Excel 文件导入数据到 triggers_review 表")
    mode_group.add_argument("--create-web-scenarios", action="store_true", help="从 webscenario_items_review 表创建 web scenario")
    mode_group.add_argument("--create-web-scenario-triggers", action="store_true", help="为 web scenario 创建触发器")
    mode_group.add_argument("--verify-status", action="store_true", help="从 Zabbix 拉取实际状态核验复核表（items_review、triggers_review）")
    
    # 配置文件
    parser.add_argument("--config", default=None, help="配置文件路径（默认: config.yaml，支持环境变量 APP_CONFIG 覆盖）")

    # Zabbix API 配置
    parser.add_argument("--url", help="Zabbix API URL")
    parser.add_argument("--username", help="Zabbix 用户名")
    parser.add_argument("--password", help="Zabbix 密码")
    
    # 同步操作参数
    parser.add_argument("--dry-run", action="store_true", help="模拟运行，不实际执行操作")
    parser.add_argument("--workers", type=int, default=cfg['sync']['default_workers'], help="并发线程数")

    # 数据库配置参数（默认值从配置文件读取）
    db_cfg = cfg['database']
    parser.add_argument("--db-host", default=db_cfg['host'], help="PostgreSQL 主机地址")
    parser.add_argument("--db-port", type=int, default=db_cfg['port'], help="PostgreSQL 端口")
    parser.add_argument("--db-name", default=db_cfg['name'], help="PostgreSQL 数据库名称")
    parser.add_argument("--db-user", default=db_cfg['user'], help="PostgreSQL 用户名")
    parser.add_argument("--db-password", default=db_cfg['password'], help="PostgreSQL 密码")
    
    args = parser.parse_args()
    
    # 验证参数
    if args.sync or args.create_web_scenarios or args.create_web_scenario_triggers or args.verify_status:
        # 同步操作、创建 web scenario、创建 web scenario 触发器 和 状态核验 需要 Zabbix API 配置
        if not args.url or not args.username or not args.password:
            parser.error("--sync、--create-web-scenarios、--create-web-scenario-triggers 或 --verify-status 操作需要 --url、--username 和 --password 参数")
    elif (args.initialize_reviews or args.initialize_items_review or args.initialize_triggers_review or
          args.initialize_webscenario_items_review or
          args.export_items_review or args.export_triggers_review or
          args.import_items_review or args.import_triggers_review):
        # 这些操作需要数据库配置，但不需要 Zabbix API
        pass
    
    # 构建数据库配置
    db_config = {
        'host': args.db_host,
        'port': args.db_port,
        'database': args.db_name,
        'user': args.db_user,
        'password': args.db_password
    }
    
    # 需要 Zabbix API 的操作
    need_zabbix_api = args.sync or args.create_web_scenarios or args.create_web_scenario_triggers or args.verify_status
    
    # 构建 Zabbix API 配置
    automator = ZabbixUltimateAutomator(
        zabbix_url=args.url if need_zabbix_api else "",
        username=args.username if need_zabbix_api else "",
        password=args.password if need_zabbix_api else "",
        db_config=db_config,
        dry_run=args.dry_run
    )
    
    # 执行相应操作
    if args.initialize_reviews:
        automator.run(initialize_reviews=True)
    elif args.initialize_items_review:
        automator.run(initialize_items_review=True)
    elif args.initialize_triggers_review:
        automator.run(initialize_triggers_review=True)
    elif args.initialize_webscenario_items_review:
        automator.run(initialize_webscenario_items_review=True)
    elif args.export_items_review:
        automator.run(export_items_review=args.export_items_review)
    elif args.export_triggers_review:
        automator.run(export_triggers_review=args.export_triggers_review)
    elif args.import_items_review:
        automator.run(import_items_review=args.import_items_review)
    elif args.import_triggers_review:
        automator.run(import_triggers_review=args.import_triggers_review)
    elif args.create_web_scenarios:
        automator.run(create_web_scenarios=True)
    elif args.create_web_scenario_triggers:
        automator.run(create_web_scenario_triggers=True)
    elif args.verify_status:
        automator.run(verify_status=True)
    else:
        automator.run(dry_run=args.dry_run, workers=args.workers, initialize_reviews=False)


if __name__ == "__main__":
    main()
