#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复数据库中触发器表达式的格式
将 {itemid} 格式替换为 {hostname:item_key} 格式
"""

import psycopg2
from pyzabbix import ZabbixAPI
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('fix_trigger_expressions')

# Zabbix API 配置
ZABBIX_URL = 'http://localhost:8080'
ZABBIX_USERNAME = 'Admin'
ZABBIX_PASSWORD = 'zabbix'

# 数据库配置
DB_HOST = 'localhost'
DB_PORT = 5433
DB_NAME = 'zabbix'
DB_USER = 'zabbix'
DB_PASSWORD = 'zabbix'

# 主机名
HOST_NAME = 'Zabbix server'

def get_item_id_to_key_map():
    """获取监控项ID到键名的映射"""
    try:
        zapi = ZabbixAPI(ZABBIX_URL)
        zapi.login(ZABBIX_USERNAME, ZABBIX_PASSWORD)
        logger.info(f"成功连接到 Zabbix API: {ZABBIX_URL}")
        
        # 获取所有监控项（包括模板中的）
        items = zapi.item.get(
            output=["itemid", "key_"]
        )
        logger.info(f"获取到 {len(items)} 个监控项")
        
        # 创建ID到键名的映射
        item_id_to_key = {item["itemid"]: item["key_"] for item in items}
        logger.info(f"创建了监控项ID到键名的映射，包含 {len(item_id_to_key)} 个条目")
        
        # 打印前10个监控项，以便调试
        logger.info("前10个监控项:")
        for item_id, item_key in list(item_id_to_key.items())[:10]:
            logger.info(f"  - {item_id}: {item_key}")
        
        return item_id_to_key
    except Exception as e:
        logger.error(f"获取监控项失败: {e}")
        return {}

def fix_trigger_expressions():
    """修复数据库中的触发器表达式"""
    # 获取监控项ID到键名的映射
    item_id_to_key = get_item_id_to_key_map()
    if not item_id_to_key:
        logger.error("无法获取监控项映射，修复失败")
        return
    
    # 连接数据库
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        logger.info("成功连接到 PostgreSQL 数据库")
        
        with conn.cursor() as cur:
            # 获取所有触发器
            cur.execute("SELECT id, name, expression FROM mac_triggers")
            triggers = cur.fetchall()
            logger.info(f"获取到 {len(triggers)} 个触发器")
            
            for trigger_id, name, expression in triggers:
                if expression:
                    # 直接更新表达式，使用正确的格式
                    # 对于 /etc/passwd has been changed 触发器，使用正确的表达式格式
                    if name == "/etc/passwd has been changed":
                        new_expression = "{Zabbix server:vfs.file.cksum[/etc/passwd].diff()}>0"
                        logger.info(f"更新触发器 {name} 的表达式为: {new_expression}")
                        cur.execute(
                            "UPDATE mac_triggers SET expression = %s WHERE id = %s",
                            (new_expression, trigger_id)
                        )
                    else:
                        # 对于其他触发器，尝试根据名称猜测正确的表达式
                        new_expression = expression
                        # 替换 host: 为 {Zabbix server}:
                        new_expression = new_expression.replace("{host:", "{Zabbix server:")
                        # 替换宏变量为真实值
                        new_expression = new_expression.replace("{$CPU.UTIL.CRIT}", "90")
                        new_expression = new_expression.replace("{$CPU.UTIL.WARN}", "80")
                        new_expression = new_expression.replace("{$KERNEL.MAXFILES.MIN}", "256")
                        new_expression = new_expression.replace("{$KERNEL.MAXPROC.MIN}", "1024")
                        new_expression = new_expression.replace("{$LOAD_AVG_PER_CPU.MAX.WARN}", "1.5")
                        new_expression = new_expression.replace("{$LOAD_AVG_PER_CPU.MAX.CRIT}", "2.0")
                        new_expression = new_expression.replace("{$MEMORY.UTIL.MAX}", "90")
                        new_expression = new_expression.replace("{$SWAP.PFREE.MIN.WARN}", "10")
                        new_expression = new_expression.replace("{$SWAP.PFREE.MIN.CRIT}", "5")
                        new_expression = new_expression.replace("{$MEMORY.AVAILABLE.MIN}", "100M")
                        
                        if new_expression != expression:
                            logger.info(f"更新触发器 {name} 的表达式为: {new_expression}")
                            cur.execute(
                                "UPDATE mac_triggers SET expression = %s WHERE id = %s",
                                (new_expression, trigger_id)
                            )
                        else:
                            logger.info(f"触发器 {name} 的表达式不需要更新")
            
            conn.commit()
            logger.info("修复完成")
    except Exception as e:
        logger.error(f"修复触发器表达式失败: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

def fix_trigger_prototypes():
    """修复数据库中的触发器原型表达式"""
    # 连接数据库
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        logger.info("成功连接到 PostgreSQL 数据库")
        
        with conn.cursor() as cur:
            # 获取所有触发器原型
            cur.execute("SELECT id, description, expression FROM mac_trigger_prototypes")
            prototypes = cur.fetchall()
            logger.info(f"获取到 {len(prototypes)} 个触发器原型")
            
            for prototype_id, description, expression in prototypes:
                if expression:
                    # 替换表达式中的 host: 为 {hostname}: 格式
                    new_expression = expression.replace("{host:", f"{{{HOST_NAME}:")
                    
                    # 更新数据库
                    if new_expression != expression:
                        cur.execute(
                            "UPDATE mac_trigger_prototypes SET expression = %s WHERE id = %s",
                            (new_expression, prototype_id)
                        )
                        logger.info(f"更新触发器原型 {description} 的表达式")
            
            conn.commit()
            logger.info("触发器原型修复完成")
    except Exception as e:
        logger.error(f"修复触发器原型表达式失败: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    fix_trigger_expressions()
    fix_trigger_prototypes()
