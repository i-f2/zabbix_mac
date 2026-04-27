#!/usr/bin/env python3
import psycopg2
from pyzabbix import ZabbixAPI
from psycopg2.extras import DictCursor
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('read_template')

# Zabbix API 连接信息
zabbix_url = 'http://localhost:8080/api_jsonrpc.php'
username = 'Admin'
password = 'zabbix'

# 数据库连接参数
db_config = {
    'host': 'localhost',
    'port': 5433,
    'database': 'zabbix',
    'user': 'zabbix',
    'password': 'zabbix'
}

# 模板名称
template_name = 'Template OS Linux by Zabbix agent'
db_template_name = '21001'

def connect_zabbix():
    """连接到Zabbix API"""
    zapi = ZabbixAPI(zabbix_url)
    zapi.login(username, password)
    logger.info(f"成功连接到 Zabbix API，版本: {zapi.api_version()}")
    return zapi

def connect_db():
    """连接到数据库"""
    conn = psycopg2.connect(**db_config)
    logger.info("成功连接到数据库")
    return conn

def get_template_id(zapi, template_name):
    """获取模板ID"""
    templates = zapi.template.get(
        filter={'name': template_name},
        output=['templateid', 'name']
    )
    if templates:
        logger.info(f"找到模板: {templates[0]['name']}, ID: {templates[0]['templateid']}")
        return templates[0]['templateid']
    else:
        logger.error(f"未找到模板: {template_name}")
        return None

def clear_tables(conn):
    """清空所有相关表"""
    with conn.cursor() as cur:
        cur.execute("DELETE FROM mac_host_extra_items")
        cur.execute("DELETE FROM mac_host_templates")
        cur.execute("DELETE FROM mac_trigger_prototypes")
        cur.execute("DELETE FROM mac_item_prototypes")
        cur.execute("DELETE FROM mac_filter_conditions")
        cur.execute("DELETE FROM mac_discovery_rules")
        cur.execute("DELETE FROM mac_triggers")
        cur.execute("DELETE FROM mac_items")
        cur.execute("DELETE FROM mac_hosts")
        cur.execute("DELETE FROM mac_templates")
        logger.info("已清空所有相关表")
    conn.commit()

def insert_template(conn, name, description):
    """插入模板"""
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO mac_templates (name, description) VALUES (%s, %s) RETURNING id",
            (name, description)
        )
        template_id = cur.fetchone()[0]
        logger.info(f"插入模板: {name}, ID: {template_id}")
        return template_id

def convert_time_value(value_str, default):
    """转换时间值为天数"""
    if not value_str:
        return default
    
    try:
        # 尝试直接转换为整数
        return int(value_str)
    except ValueError:
        # 处理带单位的情况
        unit_map = {'d': 1, 'h': 24, 'm': 24*60, 's': 24*60*60}
        try:
            # 提取数字部分和单位
            import re
            match = re.match(r'(\d+)([dhms]?)$', str(value_str).lower())
            if match:
                num = int(match.group(1))
                unit = match.group(2)
                if unit:
                    num = num // unit_map[unit]
                return num
            else:
                return default
        except:
            return default

def insert_items(zapi, conn, template_id, db_template_name):
    """插入监控项"""
    # 获取模板的所有监控项，包括继承的
    items = zapi.item.get(
        templateids=template_id,
        output='extend',
        selectHosts=['hostid'],
        inherited=True
    )
    logger.info(f"找到 {len(items)} 个监控项")
    
    # 创建监控项ID到键的映射
    item_id_to_key = {}
    
    with conn.cursor() as cur:
        for item in items:
            # 转换history和trends从时间值到天数
            history = convert_time_value(item.get('history'), 7)
            trends = convert_time_value(item.get('trends'), 365)
            
            item_id = str(item.get('itemid'))
            item_key = item.get('key_')
            item_id_to_key[item_id] = item_key
            
            cur.execute("""
                INSERT INTO mac_items (
                    item_key, name, type, value_type, delay, description, 
                    units, multiplier, delta, history, trends, status, template_name
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    item_key,
                    item.get('name'),
                    int(item.get('type', 0)),
                    int(item.get('value_type', 0)),
                    item.get('delay', '1m'),
                    item.get('description'),
                    item.get('units'),
                    int(item.get('multiplier', 0)),
                    int(item.get('delta', 0)),
                    history if history > 0 else 7,
                    trends if trends > 0 else 365,
                    int(item.get('status', 0)),
                    db_template_name
                )
            )
    
    # 尝试获取所有可能的监控项，包括从其他模板继承的
    try:
        # 首先获取模板的所有监控项，包括继承的
        template_items = zapi.item.get(
            templateids=template_id,
            output='extend',
            inherited=True,
            limit=10000
        )
        
        # 然后获取所有主机的监控项
        hosts = zapi.host.get(
            output=['hostid']
        )
        host_ids = [host['hostid'] for host in hosts]
        
        host_items = []
        if host_ids:
            host_items = zapi.item.get(
                hostids=host_ids,
                output='extend',
                limit=10000
            )
        
        # 合并所有监控项
        all_items = template_items + host_items
        
        for item in all_items:
            item_id = str(item.get('itemid'))
            item_key = item.get('key_')
            if item_id not in item_id_to_key:
                item_id_to_key[item_id] = item_key
        logger.info(f"扩展监控项ID映射，现在包含 {len(item_id_to_key)} 个监控项")
    except Exception as e:
        logger.warning(f"获取所有监控项失败: {e}")
    
    # 尝试获取所有模板的所有监控项
    try:
        # 获取所有模板
        templates = zapi.template.get(
            output=['templateid'],
            limit=10000
        )
        template_ids = [template['templateid'] for template in templates]
        
        if template_ids:
            # 获取所有模板的监控项
            all_template_items = zapi.item.get(
                templateids=template_ids,
                output='extend',
                inherited=True,
                limit=10000
            )
            
            for item in all_template_items:
                item_id = str(item.get('itemid'))
                item_key = item.get('key_')
                if item_id not in item_id_to_key:
                    item_id_to_key[item_id] = item_key
            logger.info(f"扩展监控项ID映射，现在包含 {len(item_id_to_key)} 个监控项")
    except Exception as e:
        logger.warning(f"获取所有模板的监控项失败: {e}")
    
    conn.commit()
    logger.info(f"已插入 {len(items)} 个监控项")
    return item_id_to_key

def insert_triggers(zapi, conn, template_id, db_template_name, item_id_to_key):
    """插入触发器"""
    # 获取模板的所有监控项，包括继承的
    template_items = zapi.item.get(
        templateids=template_id,
        output=['itemid', 'key_'],
        inherited=True
    )
    # 创建模板监控项ID到键的映射
    template_item_id_to_key = {item['itemid']: item['key_'] for item in template_items}
    logger.info(f"获取到 {len(template_item_id_to_key)} 个模板监控项")
    
    # 合并两个映射，item_id_to_key优先级更高
    combined_item_id_to_key = {**template_item_id_to_key, **item_id_to_key}
    logger.info(f"合并后的监控项ID映射包含 {len(combined_item_id_to_key)} 个条目")
    
    triggers = zapi.trigger.get(
        templateids=template_id,
        output='extend',
        expandDescription=1
    )
    logger.info(f"找到 {len(triggers)} 个触发器")
    
    import re
    
    with conn.cursor() as cur:
        for trigger in triggers:
            expression = trigger.get('expression')
            
            # 替换表达式中的监控项ID
            if expression:
                logger.info(f"原始表达式: {expression}")
                # 匹配 {数字} 格式的监控项ID
                matches = re.findall(r'\{(\d+)\}', expression)
                logger.info(f"匹配到的监控项ID: {matches}")
                for item_id in matches:
                    if item_id in combined_item_id_to_key:
                        item_key = combined_item_id_to_key[item_id]
                        logger.info(f"替换监控项ID {item_id} 为 {item_key}")
                        # 替换为 {host:item_key} 格式
                        expression = expression.replace(f'{{{item_id}}}', '{{host:' + item_key + '}}')
                    else:
                        logger.warning(f"未找到监控项ID {item_id} 的映射，保留原始格式")
                logger.info(f"替换后的表达式: {expression}")
            
            # 不要替换宏变量，保留原始宏变量格式，等待同步时处理
            # 这样可以确保在同步时使用最新的宏变量值
            
            cur.execute("""
                INSERT INTO mac_triggers (
                    name, expression, priority, description, status, template_name
                ) VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    trigger.get('description'),
                    expression,
                    int(trigger.get('priority', 3)),
                    trigger.get('comments'),
                    int(trigger.get('status', 0)),
                    db_template_name
                )
            )
    conn.commit()
    logger.info(f"已插入 {len(triggers)} 个触发器")

def insert_discovery_rules(zapi, conn, template_id, db_template_name):
    """插入自动发现规则"""
    rules = zapi.discoveryrule.get(
        templateids=template_id,
        output='extend',
        selectFilter='extend'
    )
    logger.info(f"找到 {len(rules)} 个自动发现规则")
    
    rule_map = {}
    
    with conn.cursor() as cur:
        for rule in rules:
            cur.execute("""
                INSERT INTO mac_discovery_rules (
                    name, key, delay, evaltype, status, template_name
                ) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
                """, (
                    rule.get('name'),
                    rule.get('key_'),
                    rule.get('delay', '1h'),
                    int(rule.get('evaltype', 0)),
                    int(rule.get('status', 0)),
                    db_template_name
                )
            )
            db_rule_id = cur.fetchone()[0]
            rule_map[rule['itemid']] = db_rule_id
            
            # 插入过滤条件
            if 'filter' in rule and 'conditions' in rule['filter']:
                for condition in rule['filter']['conditions']:
                    cur.execute("""
                        INSERT INTO mac_filter_conditions (
                            discovery_rule_id, macro, value, operator
                        ) VALUES (%s, %s, %s, %s)
                        """, (
                            db_rule_id,
                            condition.get('macro'),
                            condition.get('value'),
                            condition.get('operator', 'MATCHES_REGEX')
                        )
                    )
    
    conn.commit()
    return rule_map

def insert_item_prototypes(zapi, conn, template_id, rule_map):
    """插入监控项原型"""
    total_prototypes = 0
    
    for zabbix_rule_id, db_rule_id in rule_map.items():
        prototypes = zapi.itemprototype.get(
            discoveryids=zabbix_rule_id,
            output='extend'
        )
        total_prototypes += len(prototypes)
        
        with conn.cursor() as cur:
            for proto in prototypes:
                # 转换history和trends从时间值到天数
                history = convert_time_value(proto.get('history'), 7)
                trends = convert_time_value(proto.get('trends'), 365)
                
                cur.execute("""
                    INSERT INTO mac_item_prototypes (
                        discovery_rule_id, name, key, value_type, delay, 
                        description, units, multiplier, delta, history, trends, status
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        db_rule_id,
                        proto.get('name'),
                        proto.get('key_'),
                        int(proto.get('value_type', 0)),
                        proto.get('delay', '1m'),
                        proto.get('description'),
                        proto.get('units'),
                        int(proto.get('multiplier', 0)),
                        int(proto.get('delta', 0)),
                        history if history > 0 else 7,
                        trends if trends > 0 else 365,
                        int(proto.get('status', 0))
                    )
                )
    conn.commit()
    logger.info(f"已插入 {total_prototypes} 个监控项原型")

def insert_trigger_prototypes(zapi, conn, template_id, rule_map):
    """插入触发器原型"""
    total_prototypes = 0
    
    import re
    
    for zabbix_rule_id, db_rule_id in rule_map.items():
        # 获取该规则下的所有监控项原型，用于ID到键的映射
        item_prototypes = zapi.itemprototype.get(
            discoveryids=zabbix_rule_id,
            output=['itemid', 'key_']
        )
        item_id_to_key = {proto['itemid']: proto['key_'] for proto in item_prototypes}
        logger.info(f"获取到 {len(item_id_to_key)} 个监控项原型")
        
        prototypes = zapi.triggerprototype.get(
            discoveryids=zabbix_rule_id,
            output='extend'
        )
        total_prototypes += len(prototypes)
        
        with conn.cursor() as cur:
            for proto in prototypes:
                expression = proto.get('expression')
                
                # 替换表达式中的监控项ID为监控项键
                if expression:
                    logger.info(f"原始触发器原型表达式: {expression}")
                    # 匹配 {数字} 格式的监控项ID
                    matches = re.findall(r'\{(\d+)\}', expression)
                    logger.info(f"匹配到的监控项ID: {matches}")
                    for item_id in matches:
                        if item_id in item_id_to_key:
                            item_key = item_id_to_key[item_id]
                            logger.info(f"替换监控项ID {item_id} 为 {item_key}")
                            # 替换为 {host:item_key} 格式
                            expression = expression.replace(f'{{{item_id}}}', '{{host:' + item_key + '}}')
                        else:
                            logger.warning(f"未找到监控项ID {item_id} 的映射，保留原始格式")
                    logger.info(f"替换后的表达式: {expression}")
                
                # 不要替换宏变量，保留原始宏变量格式，等待同步时处理
                # 这样可以确保在同步时使用最新的宏变量值
                
                # 保留LLD宏变量，不做删除处理
                
                cur.execute("""
                    INSERT INTO mac_trigger_prototypes (
                        discovery_rule_id, description, expression, priority, status
                    ) VALUES (%s, %s, %s, %s, %s)
                    """, (
                        db_rule_id,
                        proto.get('description'),
                        expression,
                        int(proto.get('priority', 3)),
                        int(proto.get('status', 0))
                    )
                )
    conn.commit()
    logger.info(f"已插入 {total_prototypes} 个触发器原型")

def insert_hosts(conn):
    """插入主机"""
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO mac_hosts (name, description) VALUES (%s, %s) RETURNING id",
            ('Zabbix server', 'Local Zabbix server')
        )
        host_id = cur.fetchone()[0]
        logger.info(f"插入主机: Zabbix server, ID: {host_id}")
    
    conn.commit()
    return host_id

def link_host_template(conn, host_id, template_id):
    """关联主机和模板"""
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO mac_host_templates (host_id, template_id) VALUES (%s, %s)",
            (host_id, template_id)
        )
        logger.info(f"关联主机 {host_id} 和模板 {template_id}")
    conn.commit()

def main():
    """主函数"""
    try:
        zapi = connect_zabbix()
        conn = connect_db()
        
        # 获取模板ID
        template_id = get_template_id(zapi, template_name)
        if not template_id:
            return
        
        # 清空表
        clear_tables(conn)
        
        # 插入模板
        db_template_id = insert_template(conn, db_template_name, 'Template OS Linux by Zabbix agent')
        
        # 插入监控项
        item_id_to_key = insert_items(zapi, conn, template_id, db_template_name)
        
        # 插入触发器
        insert_triggers(zapi, conn, template_id, db_template_name, item_id_to_key)
        
        # 插入自动发现规则
        rule_map = insert_discovery_rules(zapi, conn, template_id, db_template_name)
        
        # 插入监控项原型
        insert_item_prototypes(zapi, conn, template_id, rule_map)
        
        # 插入触发器原型
        insert_trigger_prototypes(zapi, conn, template_id, rule_map)
        
        # 插入主机
        host_id = insert_hosts(conn)
        
        # 关联主机和模板
        link_host_template(conn, host_id, db_template_id)
        
        logger.info("完成！")
        
        zapi.logout()
        conn.close()
    except Exception as e:
        logger.error(f"发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
