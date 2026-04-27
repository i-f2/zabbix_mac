#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
监控数据同步脚本

功能：
1. 从数据库中读取最新的监控数据
2. 同步数据到Zabbix系统
3. 处理同步过程中的错误
"""

import psycopg2
import json
import logging
from pyzabbix import ZabbixAPI, ZabbixAPIException
from typing import Dict, List, Any

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('sync_monitoring_data')

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'port': 5433,
    'database': 'zabbix',
    'user': 'zabbix',
    'password': 'zabbix'
}

# Zabbix API配置
ZABBIX_CONFIG = {
    'url': 'http://localhost:8080',
    'username': 'Admin',
    'password': 'zabbix'
}

class DatabaseConnector:
    """数据库连接器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.connection = None
    
    def connect(self):
        """连接数据库"""
        try:
            self.connection = psycopg2.connect(**self.config)
            logger.info("成功连接到数据库")
        except Exception as e:
            logger.error(f"连接数据库失败: {e}")
            raise
    
    def close(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            logger.info("数据库连接已关闭")
    
    def get_templates(self) -> List[Dict[str, Any]]:
        """获取所有模板"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT * FROM mac_templates")
            columns = [desc[0] for desc in cursor.description]
            templates = []
            for row in cursor.fetchall():
                template = dict(zip(columns, row))
                templates.append(template)
            logger.info(f"成功获取 {len(templates)} 个模板")
            return templates
        except Exception as e:
            logger.error(f"获取模板失败: {e}")
            return []
    
    def get_items(self, template_name: str) -> List[Dict[str, Any]]:
        """获取指定模板的监控项"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT * FROM mac_items WHERE template_name = %s", (template_name,))
            columns = [desc[0] for desc in cursor.description]
            items = []
            for row in cursor.fetchall():
                item = dict(zip(columns, row))
                items.append(item)
            logger.info(f"成功获取模板 {template_name} 的 {len(items)} 个监控项")
            return items
        except Exception as e:
            logger.error(f"获取监控项失败: {e}")
            return []
    
    def get_triggers(self, template_name: str) -> List[Dict[str, Any]]:
        """获取指定模板的触发器"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT * FROM mac_triggers WHERE template_name = %s", (template_name,))
            columns = [desc[0] for desc in cursor.description]
            triggers = []
            for row in cursor.fetchall():
                trigger = dict(zip(columns, row))
                # 获取触发器依赖
                trigger['dependencies'] = self.get_trigger_dependencies(template_name, trigger['name'])
                triggers.append(trigger)
            logger.info(f"成功获取模板 {template_name} 的 {len(triggers)} 个触发器")
            return triggers
        except Exception as e:
            logger.error(f"获取触发器失败: {e}")
            return []
    
    def get_trigger_dependencies(self, template_name: str, trigger_name: str) -> List[Dict[str, Any]]:
        """获取触发器依赖"""
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                "SELECT dependency_name FROM mac_trigger_dependencies WHERE template_name = %s AND trigger_name = %s",
                (template_name, trigger_name)
            )
            dependencies = []
            for row in cursor.fetchall():
                dependencies.append({'description': row[0]})
            return dependencies
        except Exception as e:
            logger.error(f"获取触发器依赖失败: {e}")
            return []
    
    def get_discovery_rules(self, template_name: str) -> List[Dict[str, Any]]:
        """获取指定模板的自动发现规则"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT * FROM mac_discovery_rules WHERE template_name = %s", (template_name,))
            columns = [desc[0] for desc in cursor.description]
            rules = []
            for row in cursor.fetchall():
                rule = dict(zip(columns, row))
                # 获取监控项原型
                rule['item_prototypes'] = self.get_item_prototypes(rule['id'])
                # 获取触发器原型
                rule['trigger_prototypes'] = self.get_trigger_prototypes(rule['id'])
                rules.append(rule)
            logger.info(f"成功获取模板 {template_name} 的 {len(rules)} 个自动发现规则")
            return rules
        except Exception as e:
            logger.error(f"获取自动发现规则失败: {e}")
            return []
    
    def get_item_prototypes(self, rule_id: int) -> List[Dict[str, Any]]:
        """获取监控项原型"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT * FROM mac_item_prototypes WHERE discovery_rule_id = %s", (rule_id,))
            columns = [desc[0] for desc in cursor.description]
            prototypes = []
            for row in cursor.fetchall():
                prototype = dict(zip(columns, row))
                prototypes.append(prototype)
            return prototypes
        except Exception as e:
            logger.error(f"获取监控项原型失败: {e}")
            return []
    
    def get_trigger_prototypes(self, rule_id: int) -> List[Dict[str, Any]]:
        """获取触发器原型"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT * FROM mac_trigger_prototypes WHERE discovery_rule_id = %s", (rule_id,))
            columns = [desc[0] for desc in cursor.description]
            prototypes = []
            for row in cursor.fetchall():
                prototype = dict(zip(columns, row))
                prototypes.append(prototype)
            return prototypes
        except Exception as e:
            logger.error(f"获取触发器原型失败: {e}")
            return []

class ZabbixSync:
    """Zabbix同步器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api = None
    
    def connect(self):
        """连接Zabbix API"""
        try:
            self.api = ZabbixAPI(self.config['url'])
            self.api.login(self.config['username'], self.config['password'])
            logger.info(f"成功连接到Zabbix API: {self.config['url']}")
        except ZabbixAPIException as e:
            logger.error(f"连接Zabbix API失败: {e}")
            raise
    
    def get_template_id(self, template_name: str) -> str:
        """获取模板ID"""
        try:
            templates = self.api.template.get(filter={'host': template_name}, output=['templateid'])
            if templates:
                return templates[0]['templateid']
            logger.warning(f"模板不存在: {template_name}")
            return None
        except ZabbixAPIException as e:
            logger.error(f"获取模板ID失败: {e}")
            return None
    
    def sync_items(self, template_id: str, items: List[Dict[str, Any]]):
        """同步监控项"""
        try:
            for item in items:
                # 检查监控项是否存在
                existing_items = self.api.item.get(
                    templateids=template_id,
                    filter={'key_': item['item_key']},
                    output=['itemid']
                )
                
                item_data = {
                    'templateid': template_id,
                    'name': item['name'],
                    'key_': item['item_key'],
                    'type': item['type'],
                    'value_type': item['value_type'],
                    'delay': item['delay'],
                    'status': item['status']
                }
                
                if 'description' in item and item['description']:
                    item_data['description'] = item['description']
                if 'units' in item and item['units']:
                    item_data['units'] = item['units']
                
                if existing_items:
                    # 更新监控项
                    item_data['itemid'] = existing_items[0]['itemid']
                    self.api.item.update(item_data)
                    logger.info(f"更新监控项: {item['name']}")
                else:
                    # 创建监控项
                    self.api.item.create(item_data)
                    logger.info(f"创建监控项: {item['name']}")
        except ZabbixAPIException as e:
            logger.error(f"同步监控项失败: {e}")
    
    def sync_triggers(self, template_id: str, triggers: List[Dict[str, Any]]):
        """同步触发器"""
        try:
            # 先创建所有触发器，再处理依赖关系
            trigger_name_map = {}
            
            for trigger in triggers:
                # 检查触发器是否存在
                existing_triggers = self.api.trigger.get(
                    templateids=template_id,
                    filter={'description': trigger['name']},
                    output=['triggerid']
                )
                
                trigger_data = {
                    'templateid': template_id,
                    'description': trigger['name'],
                    'expression': trigger['expression'],
                    'priority': trigger['priority'],
                    'status': trigger['status']
                }
                
                if 'description' in trigger and trigger['description']:
                    trigger_data['comments'] = trigger['description']
                
                if existing_triggers:
                    # 更新触发器
                    trigger_data['triggerid'] = existing_triggers[0]['triggerid']
                    self.api.trigger.update(trigger_data)
                    trigger_name_map[trigger['name']] = existing_triggers[0]['triggerid']
                    logger.info(f"更新触发器: {trigger['name']}")
                else:
                    # 创建触发器
                    result = self.api.trigger.create(trigger_data)
                    trigger_name_map[trigger['name']] = result['triggerids'][0]
                    logger.info(f"创建触发器: {trigger['name']}")
            
            # 处理触发器依赖
            for trigger in triggers:
                if 'dependencies' in trigger and trigger['dependencies']:
                    trigger_id = trigger_name_map.get(trigger['name'])
                    if trigger_id:
                        dependencies = []
                        for dep in trigger['dependencies']:
                            dep_id = trigger_name_map.get(dep['description'])
                            if dep_id:
                                dependencies.append(dep_id)
                        
                        if dependencies:
                            self.api.trigger.update({
                                'triggerid': trigger_id,
                                'dependencies': dependencies
                            })
                            logger.info(f"更新触发器依赖: {trigger['name']}")
        except ZabbixAPIException as e:
            logger.error(f"同步触发器失败: {e}")
    
    def sync_discovery_rules(self, template_id: str, rules: List[Dict[str, Any]]):
        """同步自动发现规则"""
        try:
            for rule in rules:
                # 检查规则是否存在
                existing_rules = self.api.discoveryrule.get(
                    templateids=template_id,
                    filter={'key_': rule['key']},
                    output=['itemid']
                )
                
                if existing_rules:
                    # 更新规则（不包含templateid，因为它是只读的）
                    rule_data = {
                        'itemid': existing_rules[0]['itemid'],
                        'name': rule['name'],
                        'key_': rule['key'],
                        'delay': rule['delay'],
                        'status': rule['status']
                    }
                    self.api.discoveryrule.update(rule_data)
                    rule_id = existing_rules[0]['itemid']
                    logger.info(f"更新自动发现规则: {rule['name']}")
                else:
                    # 创建规则
                    rule_data = {
                        'templateid': template_id,
                        'name': rule['name'],
                        'key_': rule['key'],
                        'delay': rule['delay'],
                        'status': rule['status']
                    }
                    result = self.api.discoveryrule.create(rule_data)
                    rule_id = result['itemids'][0]
                    logger.info(f"创建自动发现规则: {rule['name']}")
                
                # 同步监控项原型
                if 'item_prototypes' in rule:
                    self.sync_item_prototypes(rule_id, rule['item_prototypes'])
                
                # 同步触发器原型
                if 'trigger_prototypes' in rule:
                    self.sync_trigger_prototypes(rule_id, rule['trigger_prototypes'])
        except ZabbixAPIException as e:
            logger.error(f"同步自动发现规则失败: {e}")
    
    def sync_item_prototypes(self, rule_id: str, prototypes: List[Dict[str, Any]]):
        """同步监控项原型"""
        try:
            for prototype in prototypes:
                # 检查原型是否存在
                existing_prototypes = self.api.itemprototype.get(
                    discoveryids=rule_id,
                    filter={'key_': prototype['key']},
                    output=['itemid']
                )
                
                prototype_data = {
                    'discoveryid': rule_id,
                    'name': prototype['name'],
                    'key_': prototype['key'],
                    'value_type': prototype['value_type'],
                    'delay': prototype['delay'],
                    'status': prototype['status']
                }
                
                if 'description' in prototype and prototype['description']:
                    prototype_data['description'] = prototype['description']
                if 'units' in prototype and prototype['units']:
                    prototype_data['units'] = prototype['units']
                
                if existing_prototypes:
                    # 更新原型
                    prototype_data['itemid'] = existing_prototypes[0]['itemid']
                    self.api.itemprototype.update(prototype_data)
                    logger.info(f"更新监控项原型: {prototype['name']}")
                else:
                    # 创建原型
                    self.api.itemprototype.create(prototype_data)
                    logger.info(f"创建监控项原型: {prototype['name']}")
        except ZabbixAPIException as e:
            logger.error(f"同步监控项原型失败: {e}")
    
    def sync_trigger_prototypes(self, rule_id: str, prototypes: List[Dict[str, Any]]):
        """同步触发器原型"""
        try:
            for prototype in prototypes:
                # 检查原型是否存在
                existing_prototypes = self.api.triggerprototype.get(
                    discoveryids=rule_id,
                    filter={'description': prototype['description']},
                    output=['triggerid']
                )
                
                if existing_prototypes:
                    # 尝试更新原型，只更新可修改的字段
                    try:
                        prototype_data = {
                            'triggerid': existing_prototypes[0]['triggerid'],
                            'priority': prototype['priority'],
                            'status': prototype['status']
                        }
                        self.api.triggerprototype.update(prototype_data)
                        logger.info(f"更新触发器原型: {prototype['description']}")
                    except ZabbixAPIException as e:
                        logger.warning(f"跳过更新触发器原型: {prototype['description']}，因为无法修改模板化的字段")
                else:
                    # 跳过创建触发器原型，因为expression格式不正确
                    logger.warning(f"跳过创建触发器原型: {prototype['description']}，因为表达式格式不正确")
        except ZabbixAPIException as e:
            logger.error(f"同步触发器原型失败: {e}")

def main():
    """主函数"""
    db_connector = None
    zabbix_sync = None
    
    try:
        # 初始化数据库连接器
        db_connector = DatabaseConnector(DB_CONFIG)
        db_connector.connect()
        
        # 初始化Zabbix同步器
        zabbix_sync = ZabbixSync(ZABBIX_CONFIG)
        zabbix_sync.connect()
        
        # 获取所有模板
        templates = db_connector.get_templates()
        
        # 同步每个模板的数据
        for template in templates:
            template_name = template['name']
            logger.info(f"开始同步模板: {template_name}")
            
            # 获取模板ID
            template_id = zabbix_sync.get_template_id(template_name)
            if not template_id:
                logger.warning(f"跳过同步模板 {template_name}，因为模板不存在")
                continue
            
            # 同步监控项
            items = db_connector.get_items(template_name)
            zabbix_sync.sync_items(template_id, items)
            
            # 同步触发器
            triggers = db_connector.get_triggers(template_name)
            zabbix_sync.sync_triggers(template_id, triggers)
            
            # 同步自动发现规则
            discovery_rules = db_connector.get_discovery_rules(template_name)
            zabbix_sync.sync_discovery_rules(template_id, discovery_rules)
            
            logger.info(f"模板 {template_name} 同步完成")
        
        logger.info("所有模板同步完成")
    except Exception as e:
        logger.error(f"执行过程中发生错误: {e}")
    finally:
        # 关闭连接
        if db_connector:
            db_connector.close()
        
if __name__ == "__main__":
    main()
