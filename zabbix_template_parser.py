#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Zabbix 模板解析器

功能：
1. 解析识别：查看 Zabbix server 链接了 "Template OS Linux by Zabbix agent" 模版后的监控项、触发器、自动发现规则
2. 数据重写：使用页面读取的 item name、trigger expression、优先级，直接写入数据库
3. 逻辑构成：支持监控项类型变化，触发器添加时支持依赖性
4. 标准化：为核心配置添加中文注释
"""

import argparse
import hashlib
import json
import logging
import os
import threading
from typing import Dict, List, Optional, Any, Set, Tuple

import yaml
import psycopg2
from psycopg2.extras import DictCursor
from pyzabbix import ZabbixAPI, ZabbixAPIException

# 配置日志系统
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('zabbix_template_parser')

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
            self.api = ZabbixAPI(self.url)
            self.api.login(self.username, self.password)
            logger.info(f"成功连接到 Zabbix API: {self.url}")
        except ZabbixAPIException as e:
            logger.error(f"连接 Zabbix API 失败: {e}")
            raise
    
    def get_template_id(self, template_name: str) -> Optional[str]:
        """获取模板 ID
        
        Args:
            template_name: 模板名称
            
        Returns:
            模板 ID 或 None
        """
        try:
            templates = self.api.template.get(filter={"host": template_name}, output=["templateid"])
            if templates:
                return templates[0]["templateid"]
            return None
        except ZabbixAPIException as e:
            logger.error(f"获取模板 ID 失败: {e}")
            return None
    
    def get_template_items(self, template_id: str) -> List[Dict[str, Any]]:
        """获取模板的监控项
        
        Args:
            template_id: 模板 ID
            
        Returns:
            监控项列表
        """
        try:
            items = self.api.item.get(
                templateids=template_id,
                output="extend"
            )
            return items
        except ZabbixAPIException as e:
            logger.error(f"获取监控项失败: {e}")
            return []
    
    def get_template_triggers(self, template_id: str) -> List[Dict[str, Any]]:
        """获取模板的触发器
        
        Args:
            template_id: 模板 ID
            
        Returns:
            触发器列表
        """
        try:
            triggers = self.api.trigger.get(
                templateids=template_id,
                output="extend",
                selectDependencies="extend"
            )
            return triggers
        except ZabbixAPIException as e:
            logger.error(f"获取触发器失败: {e}")
            return []
    
    def get_template_discovery_rules(self, template_id: str) -> List[Dict[str, Any]]:
        """获取模板的自动发现规则
        
        Args:
            template_id: 模板 ID
            
        Returns:
            自动发现规则列表
        """
        try:
            rules = self.api.discoveryrule.get(
                templateids=template_id,
                output="extend"
            )
            return rules
        except ZabbixAPIException as e:
            logger.error(f"获取自动发现规则失败: {e}")
            return []
    
    def get_item_prototypes(self, rule_id: str) -> List[Dict[str, Any]]:
        """获取自动发现规则的监控项原型
        
        Args:
            rule_id: 规则 ID
            
        Returns:
            监控项原型列表
        """
        try:
            prototypes = self.api.itemprototype.get(
                discoveryids=rule_id,
                output="extend"
            )
            return prototypes
        except ZabbixAPIException as e:
            logger.error(f"获取监控项原型失败: {e}")
            return []
    
    def get_trigger_prototypes(self, rule_id: str) -> List[Dict[str, Any]]:
        """获取自动发现规则的触发器原型
        
        Args:
            rule_id: 规则 ID
            
        Returns:
            触发器原型列表
        """
        try:
            prototypes = self.api.triggerprototype.get(
                discoveryids=rule_id,
                output="extend"
            )
            return prototypes
        except ZabbixAPIException as e:
            logger.error(f"获取触发器原型失败: {e}")
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
                # 创建模板表
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS mac_templates (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(255) UNIQUE NOT NULL,
                        description TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
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
                        history INTEGER,
                        trends INTEGER,
                        status INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(template_name, item_key)
                    )
                """)
                
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
                        UNIQUE(template_name, name)
                    )
                """)
                
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
                        history INTEGER,
                        trends INTEGER,
                        status INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(discovery_rule_id, key)
                    )
                """)
                
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
            with self.connection.cursor() as cur:
                cur.execute(
                    "INSERT INTO mac_templates (name, description) VALUES (%s, %s) ON CONFLICT (name) DO NOTHING",
                    (template_name, description)
                )
                self.connection.commit()
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
                        item_data['key_'],
                        item_data['name'],
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
        except Exception as e:
            logger.error(f"插入监控项失败: {e}")
            self.connection.rollback()
            raise
    
    def insert_trigger(self, template_name: str, trigger_data: Dict[str, Any]):
        """插入触发器
        
        Args:
            template_name: 模板名称
            trigger_data: 触发器数据
        """
        try:
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
                        trigger_data['description'],
                        trigger_data['expression'],
                        trigger_data.get('priority', 0),
                        trigger_data.get('comments'),
                        trigger_data.get('status', 0)
                    )
                )
                self.connection.commit()
                
                # 处理触发器依赖
                if 'dependencies' in trigger_data:
                    for dependency in trigger_data['dependencies']:
                        cur.execute(
                            """
                            INSERT INTO mac_trigger_dependencies 
                            (template_name, trigger_name, dependency_name)
                            VALUES (%s, %s, %s)
                            ON CONFLICT (template_name, trigger_name, dependency_name) DO NOTHING
                            """,
                            (
                                template_name,
                                trigger_data['description'],
                                dependency.get('description')
                            )
                        )
                    self.connection.commit()
        except Exception as e:
            logger.error(f"插入触发器失败: {e}")
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
            with self.connection.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO mac_discovery_rules 
                    (template_name, name, key, delay, evaltype, status)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (template_name, name) DO UPDATE SET
                        key = EXCLUDED.key,
                        delay = EXCLUDED.delay,
                        evaltype = EXCLUDED.evaltype,
                        status = EXCLUDED.status
                    RETURNING id
                    """,
                    (
                        template_name,
                        rule_data['name'],
                        rule_data['key_'],
                        rule_data.get('delay', '3600s'),
                        rule_data.get('evaltype', 0),
                        rule_data.get('status', 0)
                    )
                )
                rule_id = cur.fetchone()[0]
                self.connection.commit()
                return rule_id
        except Exception as e:
            logger.error(f"插入自动发现规则失败: {e}")
            self.connection.rollback()
            raise
    
    def insert_item_prototype(self, rule_id: int, prototype_data: Dict[str, Any]):
        """插入监控项原型
        
        Args:
            rule_id: 规则 ID
            prototype_data: 原型数据
        """
        try:
            with self.connection.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO mac_item_prototypes 
                    (discovery_rule_id, name, key, value_type, delay, description, units, multiplier, delta, history, trends, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (discovery_rule_id, key) DO UPDATE SET
                        name = EXCLUDED.name,
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
                        rule_id,
                        prototype_data['name'],
                        prototype_data['key_'],
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
        except Exception as e:
            logger.error(f"插入监控项原型失败: {e}")
            self.connection.rollback()
            raise
    
    def insert_trigger_prototype(self, rule_id: int, prototype_data: Dict[str, Any]):
        """插入触发器原型
        
        Args:
            rule_id: 规则 ID
            prototype_data: 原型数据
        """
        try:
            with self.connection.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO mac_trigger_prototypes 
                    (discovery_rule_id, description, expression, priority, status)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (discovery_rule_id, description) DO UPDATE SET
                        expression = EXCLUDED.expression,
                        priority = EXCLUDED.priority,
                        status = EXCLUDED.status
                    """,
                    (
                        rule_id,
                        prototype_data['description'],
                        prototype_data['expression'],
                        prototype_data.get('priority', 0),
                        prototype_data.get('status', 0)
                    )
                )
                self.connection.commit()
        except Exception as e:
            logger.error(f"插入触发器原型失败: {e}")
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
        
        logger.info(f"模板解析完成: {template_name}")
    
    def _parse_items(self, template_name: str, template_id: str):
        """解析监控项
        
        Args:
            template_name: 模板名称
            template_id: 模板 ID
        """
        logger.info(f"解析监控项: {template_name}")
        
        items = self.zabbix_client.get_template_items(template_id)
        logger.info(f"找到 {len(items)} 个监控项")
        
        for item in items:
            # 添加中文注释
            item['description'] = self._add_item_comment(item)
            self.db_manager.insert_item(template_name, item)
    
    def _parse_triggers(self, template_name: str, template_id: str):
        """解析触发器
        
        Args:
            template_name: 模板名称
            template_id: 模板 ID
        """
        logger.info(f"解析触发器: {template_name}")
        
        triggers = self.zabbix_client.get_template_triggers(template_id)
        logger.info(f"找到 {len(triggers)} 个触发器")
        
        for trigger in triggers:
            # 处理触发器依赖
            if 'dependencies' in trigger:
                # 转换依赖关系
                trigger['dependencies'] = [
                    {'description': dep.get('description', '')}
                    for dep in trigger['dependencies']
                ]
            
            # 添加中文注释
            trigger['comments'] = self._add_trigger_comment(trigger)
            self.db_manager.insert_trigger(template_name, trigger)
    
    def _parse_discovery_rules(self, template_name: str, template_id: str):
        """解析自动发现规则
        
        Args:
            template_name: 模板名称
            template_id: 模板 ID
        """
        logger.info(f"解析自动发现规则: {template_name}")
        
        rules = self.zabbix_client.get_template_discovery_rules(template_id)
        logger.info(f"找到 {len(rules)} 个自动发现规则")
        
        for rule in rules:
            # 插入规则
            rule_id = self.db_manager.insert_discovery_rule(template_name, rule)
            
            # 解析监控项原型
            item_prototypes = self.zabbix_client.get_item_prototypes(rule['itemid'])
            for prototype in item_prototypes:
                # 添加中文注释
                prototype['description'] = self._add_item_comment(prototype)
                self.db_manager.insert_item_prototype(rule_id, prototype)
            
            # 解析触发器原型
            trigger_prototypes = self.zabbix_client.get_trigger_prototypes(rule['itemid'])
            for prototype in trigger_prototypes:
                # 添加中文注释
                # 触发器原型的注释可以存储在 description 中
                self.db_manager.insert_trigger_prototype(rule_id, prototype)
    
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
    parser = argparse.ArgumentParser(description='Zabbix 模板解析器')
    parser.add_argument('--url', required=True, help='Zabbix API URL')
    parser.add_argument('--username', default='Admin', help='Zabbix 用户名')
    parser.add_argument('--password', default='zabbix', help='Zabbix 密码')
    parser.add_argument('--template', default='Template OS Linux by Zabbix agent', help='模板名称')
    parser.add_argument('--db-host', default='localhost', help='数据库主机')
    parser.add_argument('--db-port', type=int, default=5433, help='数据库端口')
    parser.add_argument('--db-name', default='zabbix', help='数据库名称')
    parser.add_argument('--db-user', default='zabbix', help='数据库用户')
    parser.add_argument('--db-password', default='zabbix', help='数据库密码')
    
    args = parser.parse_args()
    
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
    
    logger.info("模板解析任务完成")


if __name__ == "__main__":
    main()
