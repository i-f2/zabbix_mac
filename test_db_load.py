#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

# 添加当前目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from zabbix_mac import ConfigLoader

def test_db_load():
    print("测试从数据库加载模板...")
    
    # 创建 ConfigLoader 实例
    db_config = {
        'host': 'localhost',
        'port': 5432,
        'database': 'zabbix_mac',
        'user': 'fan',
        'password': ''
    }
    
    config_loader = ConfigLoader(db_config=db_config)
    
    # 测试连接数据库
    print("\n1. 连接数据库...")
    if config_loader.connect_db():
        print("✅ 数据库连接成功！")
    else:
        print("❌ 数据库连接失败！")
        return
    
    # 测试加载模板
    print("\n2. 加载模板...")
    template_name = "Template OS Linux by Zabbix agent - Standardized"
    template = config_loader.load_template_from_db(template_name)
    
    if template:
        print(f"✅ 成功加载模板: {template_name}")
        
        # 打印模板信息
        print(f"\n3. 模板信息:")
        print(f"   监控项数量: {len(template.get('items', {}))}")
        print(f"   触发器数量: {len(template.get('triggers', {}))}")
        print(f"   自动发现规则数量: {len(template.get('discovery_rules', []))}")
        
        # 打印一些示例数据
        if template.get('items'):
            print(f"\n4. 前 3 个监控项:")
            for i, (key, item) in enumerate(list(template['items'].items())[:3]):
                print(f"   {i+1}. {key}: {item.get('name')}")
        
        if template.get('triggers'):
            print(f"\n5. 前 2 个触发器:")
            for i, (name, trigger) in enumerate(list(template['triggers'].items())[:2]):
                print(f"   {i+1}. {name}")
        
        if template.get('discovery_rules'):
            print(f"\n6. 自动发现规则:")
            for i, rule in enumerate(template['discovery_rules']):
                print(f"   {i+1}. {rule.get('name')}")
                print(f"      监控项原型数量: {len(rule.get('item_prototypes', []))}")
                print(f"      触发器原型数量: {len(rule.get('trigger_prototypes', []))}")
        
        print("\n✅ 测试成功！")
    else:
        print("❌ 加载模板失败！")
    
    config_loader.connection.close()

if __name__ == "__main__":
    test_db_load()
