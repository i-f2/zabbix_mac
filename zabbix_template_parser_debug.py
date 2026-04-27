#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Zabbix 模板解析器 - 调试版本

功能：
1. 解析识别：查看 Zabbix server 链接了 "Template OS Linux by Zabbix agent" 模版后的监控项、触发器、自动发现规则
2. 数据重写：使用页面读取的 item name、trigger expression、优先级，直接写入数据库
3. 逻辑构成：支持监控项类型变化，触发器添加时支持依赖性
4. 标准化：为核心配置添加中文注释

调试特性：
- 更详细的日志输出
- 错误处理增强
- 数据验证
- 进度显示
"""

import argparse
import hashlib
import json
import logging
import os
import threading
import time
from typing import Dict, List, Optional, Any, Set, Tuple

import yaml
import psycopg2
from psycopg2.extras import DictCursor
from pyzabbix import ZabbixAPI, ZabbixAPIException

# 配置日志系统
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('zabbix_template_parser_debug')

# 管理标签
MANAGED_TAG = {"tag": "ManagedBy", "value": "TemplateParser"}


class ZabbixClient:
    """Zabbix API 客户端封装"""
    
    def __init__(self, url: str, username: str, password: str):
        """初始化 Zabbix 客户端
        
        Args:
            url: Zabbix API URL
            username: 用户名
            password: 密码
        """
        self.url = url
        self.username = username
        self.password = password
        self.api = None
        self._connect()
    
    def _connect(self):
        """建立 API 连接"""
        try:
            logger.debug(f"尝试连接到 Zabbix API: {self.url}")
            self.api = ZabbixAPI(self.url)
            self.api.login(self.username, self.password)
            logger.info(f"成功连接到 Zabbix API: {self.url}")
            logger.debug(f"Zabbix API 版本: {self.api.api_version()}")
        except ZabbixAPIException as e:
            logger.error(f"连接 Zabbix API 失败: {e}")
            raise
        except Exception as e:
            logger.error(f"连接 Zabbix API 时发生未知错误: {e}")
            raise
    
    def get_template_id(self, template_name: str) -> Optional[str]:
        """获取模板 ID
        
        Args:
            template_name: 模板名称
            
        Returns:
            模板 ID 或 None
        """
        try:
            logger.debug(f"获取模板 ID: {template_name}")
            templates = self.api.template.get(filter={"host": template_name}, output=["templateid", "host"])
            logger.debug(f"API 响应: {templates}")
            if templates:
                template_id = templates[0]["templateid"]
                logger.info(f"找到模板: {template_name} (ID: {template_id})")
                return template_id
            logger.warning(f"模板不存在: {template_name}")
            return None
        except ZabbixAPIException as e:
            logger.error(f"获取模板 ID 失败: {e}")
            return None
        except Exception as e:
            logger.error(f"获取模板 ID 时发生未知错误: {e}")
            return None
    
    def get_template_items(self, template_id: str) -> List[Dict[str, Any]]:
        """获取模板的监控项
        
        Args:
            template_id: 模板 ID
            
        Returns:
            监控项列表
        """
        try:
            logger.debug(f"获取模板监控项: {template_id}")
            items = self.api.item.get(
                templateids=template_id,
                output="extend"
            )
            logger.info(f"找到 {len(items)} 个监控项")
            if items:
                logger.debug(f"第一个监控项: {items[0].get('name')} ({items[0].get('key_')})")
            return items
        except ZabbixAPIException as e:
            logger.error(f"获取监控项失败: {e}")
            return []
        except Exception as e:
            logger.error(f"获取监控项时发生未知错误: {e}")
            return []
    
    def get_template_triggers(self, template_id: str) -> List[Dict[str, Any]]:
        """获取模板的触发器
        
        Args:
            template_id: 模板 ID
            
        Returns:
            触发器列表
        """
        try:
            logger.debug(f"获取模板触发器: {template_id}")
            triggers = self.api.trigger.get(
                templateids=template_id,
                output="extend",
                selectDependencies="extend"
            )
            logger.info(f"找到 {len(triggers)} 个触发器")
            if triggers:
                logger.debug(f"第一个触发器: {triggers[0].get('description')}")
            return triggers
        except ZabbixAPIException as e:
            logger.error(f"获取触发器失败: {e}")
            return []
        except Exception as e:
            logger.error(f"获取触发器时发生未知错误: {e}")
            return []
    
    def get_template_discovery_rules(self, template_id: str) -> List[Dict[str, Any]]:
        """获取模板的自动发现规则
        
        Args:
            template_id: 模板 ID
            
        Returns:
            自动发现规则列表
        """
        try:
            logger.debug(f"获取模板自动发现规则: {template_id}")
            rules = self.api.discoveryrule.get(
                templateids=template_id,
                output="extend"
            )
            logger.info(f"找到 {len(rules)} 个自动发现规则")
            if rules:
                logger.debug(f"第一个规则: {rules[0].get('name')} ({rules[0].get('key_')})")
            return rules
        except ZabbixAPIException as e:
            logger.error(f"获取自动发现规则失败: {e}")
            return []
        except Exception as e:
            logger.error(f"获取自动发现规则时发生未知错误: {e}")
            return []
    
    def get_item_prototypes(self, rule_id: str) -> List[Dict[str, Any]]:
        """获取自动发现规则的监控项原型
        
        Args:
            rule_id: 规则 ID
            
        Returns:
            监控项原型列表
        """
        try:
            logger.debug(f"获取监控项原型: {rule_id}")
            prototypes = self.api.itemprototype.get(
                discoveryids=rule_id,
                output="extend"
            )
            logger.info(f"找到 {len(prototypes)} 个监控项原型")
            if prototypes:
                logger.debug(f"第一个监控项原型: {prototypes[0].get('name')} ({prototypes[0].get('key_')})")
            return prototypes
        except ZabbixAPIException as e:
            logger.error(f"获取监控项原型失败: {e}")
            return []
        except Exception as e:
            logger.error(f"获取监控项原型时发生未知错误: {e}")
            return []
    
    def get_trigger_prototypes(self, rule_id: str) -> List[Dict[str, Any]]:
        """获取自动发现规则的触发器原型
        
        Args:
            rule_id: 规则 ID
            
        Returns:
            触发器原型列表
        """
        try:
            logger.debug(f"获取触发器原型: {rule_id}")
            prototypes = self.api.triggerprototype.get(
                discoveryids=rule_id,
                output="extend"
            )
            logger.info(f"找到 {len(prototypes)} 个触发器原型")
            if prototypes:
                logger.debug(f"第一个触发器原型: {prototypes[0].get('description')}")
            return prototypes
        except ZabbixAPIException as e:
            logger.error(f"获取触发器原型失败: {e}")
            return []
        except Exception as e:
            logger.error(f"获取触发器原型时发生未知错误: {e}")
            return []


class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, db_config: Dict[str, Any]):
        """初始化数据库管理器
        
        Args:
            db_config: 数据库配置
        """
        self.db_config = db_config
        self.connection = None
        self.connect()
    
    def connect(self):
        """连接数据库"""
        try:
            logger.debug(f"尝试连接数据库: {self.db_config.get('host')}:{self.db_config.get('port')}/{self.db_config.get('database')}")
            self.connection = psycopg2.connect(
                host=self.db_config.get('host', 'localhost'),
                port=self.db_config.get('port', 5433),
                database=self.db_config.get('database', 'zabbix'),
                user=self.db_config.get('user', 'zabbix'),
                password=self.db_config.get('password', 'zabbix')
            )
            logger.info("成功连接到 PostgreSQL 数据库")
        except Exception as e:
            logger.error(f"连接数据库失败: {e}")
            raise
    
    def create_tables(self):
        """创建必要的表"""
        try:
            with self.connection.cursor() as cur:
                logger.debug("开始创建数据库表")
                
                # 创建模板表
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS mac_templates (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(255) UNIQUE NOT NULL,
                        description TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                logger.debug("创建 mac_templates 表成功")
                
                # 创建监控项表
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS mac_items (
                        id SERIAL PRIMARY KEY,
                        template_name VARCHAR(255) NOT NULL,
                        item_key VARCHAR(255) NOT NULL,
                        name VARCHAR(255) NOT NULL,
                        type INTEGER NOT NULL,
                        value_type INTEGER NOT NULL,
                        delay VARCHAR(32) NOT NULL,
                        description TEXT,
                        units VARCHAR(64),
                        multiplier INTEGER,
                        delta INTEGER,
                        history VARCHAR(32),
                        trends VARCHAR(32),
                        status INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(template_name, item_key)
                    )
                """)
                logger.debug("创建 mac_items 表成功")
                
                # 创建触发器表
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS mac_triggers (
                        id SERIAL PRIMARY KEY,
                        template_name VARCHAR(255) NOT NULL,
                        name VARCHAR(255) NOT NULL,
                        expression TEXT NOT NULL,
                        priority INTEGER NOT NULL,
                        description TEXT,
                        status INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(template_name, name)
                    )
                """)
                logger.debug("创建 mac_triggers 表成功")
                
                # 创建触发器依赖表
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS mac_trigger_dependencies (
                        id SERIAL PRIMARY KEY,
                        template_name VARCHAR(255) NOT NULL,
                        trigger_name VARCHAR(255) NOT NULL,
                        dependency_name VARCHAR(255) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(template_name, trigger_name, dependency_name)
                    )
                """)
                logger.debug("创建 mac_trigger_dependencies 表成功")
                
                # 创建自动发现规则表
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS mac_discovery_rules (
                        id SERIAL PRIMARY KEY,
                        template_name VARCHAR(255) NOT NULL,
                        name VARCHAR(255) NOT NULL,
                        key VARCHAR(255) NOT NULL,
                        delay VARCHAR(32) NOT NULL,
                        evaltype INTEGER NOT NULL,
                        status INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(template_name, key)
                    )
                """)
                logger.debug("创建 mac_discovery_rules 表成功")
                
                # 创建过滤条件表
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS mac_filter_conditions (
                        id SERIAL PRIMARY KEY,
                        discovery_rule_id INTEGER NOT NULL,
                        macro VARCHAR(255) NOT NULL,
                        value VARCHAR(255) NOT NULL,
                        operator VARCHAR(32) DEFAULT 'equals',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(discovery_rule_id, macro, value)
                    )
                """)
                logger.debug("创建 mac_filter_conditions 表成功")
                
                # 创建监控项原型表
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS mac_item_prototypes (
                        id SERIAL PRIMARY KEY,
                        discovery_rule_id INTEGER NOT NULL,
                        name VARCHAR(255) NOT NULL,
                        key VARCHAR(255) NOT NULL,
                        value_type INTEGER NOT NULL,
                        delay VARCHAR(32) NOT NULL,
                        description TEXT,
                        units VARCHAR(64),
                        multiplier INTEGER,
                        delta INTEGER,
                        history VARCHAR(32),
                        trends VARCHAR(32),
                        status INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(discovery_rule_id, key)
                    )
                """)
                logger.debug("创建 mac_item_prototypes 表成功")
                
                # 创建触发器原型表
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS mac_trigger_prototypes (
                        id SERIAL PRIMARY KEY,
                        discovery_rule_id INTEGER NOT NULL,
                        description TEXT NOT NULL,
                        expression TEXT NOT NULL,
                        priority INTEGER NOT NULL,
                        status INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(discovery_rule_id, description)
                    )
                """)
                logger.debug("创建 mac_trigger_prototypes 表成功")
                
                self.connection.commit()
                logger.info("数据库表创建/更新成功")
        except Exception as e:
            logger.error(f"创建表失败: {e}")
            self.connection.rollback()
            raise
    
    def insert_template(self, template_name: str, description: str = None):
        """插入模板
        
        Args:
            template_name: 模板名称
            description: 模板描述
        """
        try:
            logger.debug(f"插入模板: {template_name}")
            with self.connection.cursor() as cur:
                cur.execute(
                    "INSERT INTO mac_templates (name, description) VALUES (%s, %s) ON CONFLICT (name) DO NOTHING",
                    (template_name, description)
                )
                self.connection.commit()
                logger.info(f"模板 {template_name} 插入/更新成功")
        except Exception as e:
            logger.error(f"插入模板失败: {e}")
            self.connection.rollback()
            raise
    
    def insert_item(self, template_name: str, item_data: Dict[str, Any]):
        """插入监控项
        
        Args:
            template_name: 模板名称
            item_data: 监控项数据
        """
        try:
            item_key = item_data.get('key_')
            item_name = item_data.get('name')
            logger.debug(f"插入监控项: {item_name} ({item_key})")
            
            with self.connection.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO mac_items 
                    (template_name, item_key, name, type, value_type, delay, description, units, multiplier, delta, history, trends, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (template_name, item_key) DO UPDATE SET
                        name = EXCLUDED.name,
                        type = EXCLUDED.type,
                        value_type = EXCLUDED.value_type,
                        delay = EXCLUDED.delay,
                        description = EXCLUDED.description,
                        units = EXCLUDED.units,
                        multiplier = EXCLUDED.multiplier,
                        delta = EXCLUDED.delta,
                        history = EXCLUDED.history,
                        trends = EXCLUDED.trends,
                        status = EXCLUDED.status
                    """,
                    (
                        template_name,
                        item_key,
                        item_name,
                        item_data.get('type', 0),
                        item_data.get('value_type', 0),
                        item_data.get('delay', '60s'),
                        item_data.get('description'),
                        item_data.get('units'),
                        item_data.get('multiplier'),
                        item_data.get('delta'),
                        item_data.get('history'),
                        item_data.get('trends'),
                        item_data.get('status', 0)
                    )
                )
                self.connection.commit()
                logger.debug(f"监控项 {item_name} 插入/更新成功")
        except Exception as e:
            logger.error(f"插入监控项失败: {e}")
            logger.debug(f"失败的监控项数据: {item_data}")
            self.connection.rollback()
            raise
    
    def insert_trigger(self, template_name: str, trigger_data: Dict[str, Any]):
        """插入触发器
        
        Args:
            template_name: 模板名称
            trigger_data: 触发器数据
        """
        try:
            trigger_name = trigger_data.get('description')
            logger.debug(f"插入触发器: {trigger_name}")
            
            with self.connection.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO mac_triggers 
                    (template_name, name, expression, priority, description, status)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (template_name, name) DO UPDATE SET
                        expression = EXCLUDED.expression,
                        priority = EXCLUDED.priority,
                        description = EXCLUDED.description,
                        status = EXCLUDED.status
                    """,
                    (
                        template_name,
                        trigger_name,
                        trigger_data['expression'],
                        trigger_data.get('priority', 0),
                        trigger_data.get('comments'),
                        trigger_data.get('status', 0)
                    )
                )
                self.connection.commit()
                logger.debug(f"触发器 {trigger_name} 插入/更新成功")
                
                # 处理触发器依赖
                if 'dependencies' in trigger_data:
                    for dependency in trigger_data['dependencies']:
                        dependency_name = dependency.get('description')
                        if dependency_name:
                            logger.debug(f"插入触发器依赖: {trigger_name} -> {dependency_name}")
                            cur.execute(
                                """
                                INSERT INTO mac_trigger_dependencies 
                                (template_name, trigger_name, dependency_name)
                                VALUES (%s, %s, %s)
                                ON CONFLICT (template_name, trigger_name, dependency_name) DO NOTHING
                                """,
                                (
                                    template_name,
                                    trigger_name,
                                    dependency_name
                                )
                            )
                    self.connection.commit()
                    logger.debug(f"触发器依赖处理完成")
        except Exception as e:
            logger.error(f"插入触发器失败: {e}")
            logger.debug(f"失败的触发器数据: {trigger_data}")
            self.connection.rollback()
            raise
    
    def insert_discovery_rule(self, template_name: str, rule_data: Dict[str, Any]) -> int:
        """插入自动发现规则
        
        Args:
            template_name: 模板名称
            rule_data: 规则数据
            
        Returns:
            规则 ID
        """
        try:
            rule_name = rule_data.get('name')
            rule_key = rule_data.get('key_')
            logger.debug(f"插入自动发现规则: {rule_name} ({rule_key})")
            
            with self.connection.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO mac_discovery_rules 
                    (template_name, name, key, delay, evaltype, status)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        template_name,
                        rule_name,
                        rule_key,
                        rule_data.get('delay', '3600s'),
                        rule_data.get('evaltype', 0),
                        rule_data.get('status', 0)
                    )
                )
                rule_id = cur.fetchone()[0]
                self.connection.commit()
                logger.info(f"自动发现规则 {rule_name} 插入/更新成功 (ID: {rule_id})")
                return rule_id
        except Exception as e:
            logger.error(f"插入自动发现规则失败: {e}")
            logger.debug(f"失败的规则数据: {rule_data}")
            self.connection.rollback()
            raise
    
    def insert_item_prototype(self, rule_id: int, prototype_data: Dict[str, Any]):
        """插入监控项原型
        
        Args:
            rule_id: 规则 ID
            prototype_data: 原型数据
        """
        try:
            prototype_name = prototype_data.get('name')
            prototype_key = prototype_data.get('key_')
            logger.debug(f"插入监控项原型: {prototype_name} ({prototype_key})")
            
            with self.connection.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO mac_item_prototypes 
                    (discovery_rule_id, name, key, value_type, delay, description, units, multiplier, delta, history, trends, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        rule_id,
                        prototype_name,
                        prototype_key,
                        prototype_data.get('value_type', 0),
                        prototype_data.get('delay', '60s'),
                        prototype_data.get('description'),
                        prototype_data.get('units'),
                        prototype_data.get('multiplier'),
                        prototype_data.get('delta'),
                        prototype_data.get('history'),
                        prototype_data.get('trends'),
                        prototype_data.get('status', 0)
                    )
                )
                self.connection.commit()
                logger.debug(f"监控项原型 {prototype_name} 插入/更新成功")
        except Exception as e:
            logger.error(f"插入监控项原型失败: {e}")
            logger.debug(f"失败的原型数据: {prototype_data}")
            self.connection.rollback()
            raise
    
    def insert_trigger_prototype(self, rule_id: int, prototype_data: Dict[str, Any]):
        """插入触发器原型
        
        Args:
            rule_id: 规则 ID
            prototype_data: 原型数据
        """
        try:
            prototype_desc = prototype_data.get('description')
            logger.debug(f"插入触发器原型: {prototype_desc}")
            
            with self.connection.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO mac_trigger_prototypes 
                    (discovery_rule_id, description, expression, priority, status)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        rule_id,
                        prototype_desc,
                        prototype_data['expression'],
                        prototype_data.get('priority', 0),
                        prototype_data.get('status', 0)
                    )
                )
                self.connection.commit()
                logger.debug(f"触发器原型 {prototype_desc} 插入/更新成功")
        except Exception as e:
            logger.error(f"插入触发器原型失败: {e}")
            logger.debug(f"失败的原型数据: {prototype_data}")
            self.connection.rollback()
            raise


class TemplateParser:
    """模板解析器"""
    
    def __init__(self, zabbix_client: ZabbixClient, db_manager: DatabaseManager):
        """初始化模板解析器
        
        Args:
            zabbix_client: Zabbix 客户端
            db_manager: 数据库管理器
        """
        self.zabbix_client = zabbix_client
        self.db_manager = db_manager
    
    def parse_template(self, template_name: str):
        """解析模板
        
        Args:
            template_name: 模板名称
        """
        logger.info(f"开始解析模板: {template_name}")
        start_time = time.time()
        
        try:
            # 获取模板 ID
            template_id = self.zabbix_client.get_template_id(template_name)
            if not template_id:
                logger.error(f"模板不存在: {template_name}")
                return
            
            # 插入模板
            self.db_manager.insert_template(template_name, f"{template_name} 模板 - 自动解析")
            
            # 解析监控项
            self._parse_items(template_name, template_id)
            
            # 解析触发器
            self._parse_triggers(template_name, template_id)
            
            # 解析自动发现规则
            self._parse_discovery_rules(template_name, template_id)
            
            elapsed_time = time.time() - start_time
            logger.info(f"模板解析完成: {template_name} (耗时: {elapsed_time:.2f}秒)")
        except Exception as e:
            logger.error(f"解析模板时发生错误: {e}")
            raise
    
    def _parse_items(self, template_name: str, template_id: str):
        """解析监控项
        
        Args:
            template_name: 模板名称
            template_id: 模板 ID
        """
        logger.info(f"开始解析监控项: {template_name}")
        start_time = time.time()
        
        items = self.zabbix_client.get_template_items(template_id)
        logger.info(f"找到 {len(items)} 个监控项")
        
        processed = 0
        for item in items:
            try:
                # 验证必要字段
                if 'key_' not in item or 'name' not in item:
                    logger.warning(f"监控项缺少必要字段: {item}")
                    continue
                
                # 添加中文注释
                item['description'] = self._add_item_comment(item)
                
                # 插入数据库
                self.db_manager.insert_item(template_name, item)
                processed += 1
                
                # 显示进度
                if processed % 10 == 0:
                    logger.info(f"已处理 {processed}/{len(items)} 个监控项")
                    
            except Exception as e:
                logger.error(f"处理监控项失败: {e}")
                logger.debug(f"失败的监控项: {item}")
                continue
        
        elapsed_time = time.time() - start_time
        logger.info(f"监控项解析完成: 处理了 {processed}/{len(items)} 个监控项 (耗时: {elapsed_time:.2f}秒)")
    
    def _parse_triggers(self, template_name: str, template_id: str):
        """解析触发器
        
        Args:
            template_name: 模板名称
            template_id: 模板 ID
        """
        logger.info(f"开始解析触发器: {template_name}")
        start_time = time.time()
        
        triggers = self.zabbix_client.get_template_triggers(template_id)
        logger.info(f"找到 {len(triggers)} 个触发器")
        
        processed = 0
        for trigger in triggers:
            try:
                # 验证必要字段
                if 'description' not in trigger or 'expression' not in trigger:
                    logger.warning(f"触发器缺少必要字段: {trigger}")
                    continue
                
                # 处理触发器依赖
                if 'dependencies' in trigger:
                    # 转换依赖关系
                    trigger['dependencies'] = [
                        {'description': dep.get('description', '')}
                        for dep in trigger['dependencies']
                    ]
                
                # 添加中文注释
                trigger['comments'] = self._add_trigger_comment(trigger)
                
                # 插入数据库
                self.db_manager.insert_trigger(template_name, trigger)
                processed += 1
                
                # 显示进度
                if processed % 5 == 0:
                    logger.info(f"已处理 {processed}/{len(triggers)} 个触发器")
                    
            except Exception as e:
                logger.error(f"处理触发器失败: {e}")
                logger.debug(f"失败的触发器: {trigger}")
                continue
        
        elapsed_time = time.time() - start_time
        logger.info(f"触发器解析完成: 处理了 {processed}/{len(triggers)} 个触发器 (耗时: {elapsed_time:.2f}秒)")
    
    def _parse_discovery_rules(self, template_name: str, template_id: str):
        """解析自动发现规则
        
        Args:
            template_name: 模板名称
            template_id: 模板 ID
        """
        logger.info(f"开始解析自动发现规则: {template_name}")
        start_time = time.time()
        
        rules = self.zabbix_client.get_template_discovery_rules(template_id)
        logger.info(f"找到 {len(rules)} 个自动发现规则")
        
        processed_rules = 0
        for rule in rules:
            try:
                # 验证必要字段
                if 'name' not in rule or 'key_' not in rule:
                    logger.warning(f"自动发现规则缺少必要字段: {rule}")
                    continue
                
                # 插入规则
                rule_id = self.db_manager.insert_discovery_rule(template_name, rule)
                
                # 解析监控项原型
                item_prototypes = self.zabbix_client.get_item_prototypes(rule['itemid'])
                processed_items = 0
                for prototype in item_prototypes:
                    try:
                        # 验证必要字段
                        if 'name' not in prototype or 'key_' not in prototype:
                            logger.warning(f"监控项原型缺少必要字段: {prototype}")
                            continue
                        
                        # 添加中文注释
                        prototype['description'] = self._add_item_comment(prototype)
                        
                        # 插入数据库
                        self.db_manager.insert_item_prototype(rule_id, prototype)
                        processed_items += 1
                    except Exception as e:
                        logger.error(f"处理监控项原型失败: {e}")
                        continue
                
                # 解析触发器原型
                trigger_prototypes = self.zabbix_client.get_trigger_prototypes(rule['itemid'])
                processed_triggers = 0
                for prototype in trigger_prototypes:
                    try:
                        # 验证必要字段
                        if 'description' not in prototype or 'expression' not in prototype:
                            logger.warning(f"触发器原型缺少必要字段: {prototype}")
                            continue
                        
                        # 插入数据库
                        self.db_manager.insert_trigger_prototype(rule_id, prototype)
                        processed_triggers += 1
                    except Exception as e:
                        logger.error(f"处理触发器原型失败: {e}")
                        continue
                
                processed_rules += 1
                logger.info(f"规则 {rule['name']} 处理完成: {processed_items} 个监控项原型, {processed_triggers} 个触发器原型")
                
            except Exception as e:
                logger.error(f"处理自动发现规则失败: {e}")
                logger.debug(f"失败的规则: {rule}")
                continue
        
        elapsed_time = time.time() - start_time
        logger.info(f"自动发现规则解析完成: 处理了 {processed_rules}/{len(rules)} 个规则 (耗时: {elapsed_time:.2f}秒)")
    
    def _add_item_comment(self, item: Dict[str, Any]) -> str:
        """为监控项添加中文注释
        
        Args:
            item: 监控项数据
            
        Returns:
            注释文本
        """
        comments = []
        
        # 根据监控项类型添加注释
        item_type = item.get('type', 0)
        type_comments = {
            0: "Zabbix agent",
            1: "SNMPv1 agent",
            2: "Zabbix trapper",
            3: "simple check",
            4: "SNMPv2 agent",
            5: "Zabbix internal",
            6: "SNMPv3 agent",
            7: "Zabbix agent (active)",
            8: "aggregate",
            9: "web item",
            10: "external check",
            11: "database monitor",
            12: "IPMI agent",
            13: "SSH agent",
            14: "TELNET agent",
            15: "calculated",
            16: "JMX agent",
            17: "SNMP trap",
            18: "Dependent item",
            19: "HTTP agent",
            20: "SNMP agent",
            21: "Script"
        }
        
        if item_type in type_comments:
            comments.append(f"类型: {type_comments[item_type]}")
        
        # 根据值类型添加注释
        value_type = item.get('value_type', 0)
        value_type_comments = {
            0: "Numeric (float)",
            1: "Character",
            2: "Log",
            3: "Numeric (unsigned)",
            4: "Text"
        }
        
        if value_type in value_type_comments:
            comments.append(f"值类型: {value_type_comments[value_type]}")
        
        # 添加单位注释
        if 'units' in item and item['units']:
            comments.append(f"单位: {item['units']}")
        
        # 添加原有描述
        if 'description' in item and item['description']:
            comments.append(item['description'])
        
        return '; '.join(comments) if comments else None
    
    def _add_trigger_comment(self, trigger: Dict[str, Any]) -> str:
        """为触发器添加中文注释
        
        Args:
            trigger: 触发器数据
            
        Returns:
            注释文本
        """
        comments = []
        
        # 根据优先级添加注释
        priority = trigger.get('priority', 0)
        priority_comments = {
            0: "Not classified",
            1: "Information",
            2: "Warning",
            3: "Average",
            4: "High",
            5: "Disaster"
        }
        
        if priority in priority_comments:
            comments.append(f"优先级: {priority_comments[priority]}")
        
        # 添加原有注释
        if 'comments' in trigger and trigger['comments']:
            comments.append(trigger['comments'])
        
        return '; '.join(comments) if comments else None


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='Zabbix 模板解析器 - 调试版本')
    parser.add_argument('--url', required=True, help='Zabbix API URL')
    parser.add_argument('--username', default='Admin', help='Zabbix 用户名')
    parser.add_argument('--password', default='zabbix', help='Zabbix 密码')
    parser.add_argument('--template', default='Template OS Linux by Zabbix agent', help='模板名称')
    parser.add_argument('--db-host', default='localhost', help='数据库主机')
    parser.add_argument('--db-port', type=int, default=5433, help='数据库端口')
    parser.add_argument('--db-name', default='zabbix', help='数据库名称')
    parser.add_argument('--db-user', default='zabbix', help='数据库用户')
    parser.add_argument('--db-password', default='zabbix', help='数据库密码')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    
    args = parser.parse_args()
    
    # 调整日志级别
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    logger.info("=" * 80)
    logger.info("Zabbix 模板解析器 - 调试模式")
    logger.info("=" * 80)
    logger.info(f"Zabbix API URL: {args.url}")
    logger.info(f"模板名称: {args.template}")
    logger.info(f"数据库: {args.db_host}:{args.db_port}/{args.db_name}")
    logger.info("=" * 80)
    
    try:
        # 初始化 Zabbix 客户端
        zabbix_client = ZabbixClient(args.url, args.username, args.password)
        
        # 初始化数据库管理器
        db_config = {
            'host': args.db_host,
            'port': args.db_port,
            'database': args.db_name,
            'user': args.db_user,
            'password': args.db_password
        }
        db_manager = DatabaseManager(db_config)
        
        # 创建表
        db_manager.create_tables()
        
        # 初始化模板解析器
        parser = TemplateParser(zabbix_client, db_manager)
        
        # 解析模板
        parser.parse_template(args.template)
        
        logger.info("=" * 80)
        logger.info("模板解析任务完成")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"执行过程中发生错误: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        logger.info("=" * 80)
        logger.info("任务执行失败")
        logger.info("=" * 80)


if __name__ == "__main__":
    main()
