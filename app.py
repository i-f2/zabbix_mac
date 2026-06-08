#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Zabbix Monitor as Code (MaC) 管理界面

基于 Flask 的 Web 应用，用于管理 PostgreSQL 中的监控配置数据
"""

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import os
import psycopg2
from psycopg2.extras import DictCursor
import json

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# 数据库连接配置
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'ops',
    'user': 'postgres',
    'password': '',
    'client_encoding': 'utf8',
    'options': '-c search_path=zabbix_mac'
}

# Zabbix 环境机房配置（从环境变量读取，未配置则为空字符串）
ZABBIX_ENVIRONMENTS = {
    '深交所证联网': {
        'url': os.environ.get('ZABBIX_SZSE_ZW_URL', ''),
        'username': os.environ.get('ZABBIX_SZSE_ZW_USER', ''),
        'password': os.environ.get('ZABBIX_SZSE_ZW_PASS', ''),
    },
    '深交所互联网': {
        'url': os.environ.get('ZABBIX_SZSE_HLW_URL', ''),
        'username': os.environ.get('ZABBIX_SZSE_HLW_USER', ''),
        'password': os.environ.get('ZABBIX_SZSE_HLW_PASS', ''),
    },
    '上交所证联网': {
        'url': os.environ.get('ZABBIX_SSE_ZW_URL', ''),
        'username': os.environ.get('ZABBIX_SSE_ZW_USER', ''),
        'password': os.environ.get('ZABBIX_SSE_ZW_PASS', ''),
    },
    '上交所互联网': {
        'url': os.environ.get('ZABBIX_SSE_HLW_URL', ''),
        'username': os.environ.get('ZABBIX_SSE_HLW_USER', ''),
        'password': os.environ.get('ZABBIX_SSE_HLW_PASS', ''),
    },
}

def get_db_connection():
    """获取数据库连接"""
    conn = psycopg2.connect(**DB_CONFIG)
    conn.set_client_encoding('utf8')
    return conn

@app.context_processor
def inject_active_menu():
    """为所有模板注入当前活跃菜单项"""
    endpoint = request.endpoint
    menu_map = {
        'index': 'system_info',
        'system_info': 'system_info',
        'templates': 'templates',
        'template_detail': 'templates',
        'items': 'items',
        'add_item': 'items',
        'edit_item': 'items',
        'triggers': 'triggers',
        'add_trigger': 'triggers',
        'edit_trigger': 'triggers',
        'item_prototypes': 'item_prototypes',
        'edit_item_prototype': 'item_prototypes',
        'trigger_prototypes': 'trigger_prototypes',
        'edit_trigger_prototype': 'trigger_prototypes',
        'items_review': 'items_review',
        'edit_item_review': 'items_review',
        'triggers_review': 'triggers_review',
        'edit_trigger_review': 'triggers_review',
        'item_prototypes_review': 'item_prototypes_review',
        'edit_item_prototype_review': 'item_prototypes_review',
        'trigger_prototypes_review': 'trigger_prototypes_review',
        'edit_trigger_prototype_review': 'trigger_prototypes_review',
        'hosts': 'hosts',
        'add_host': 'hosts',
        'edit_host': 'hosts',
        'discovery_rules': 'discovery_rules',
        'edit_discovery_rule': 'discovery_rules',
        'filter_conditions': 'filter_conditions',
        'edit_filter_condition': 'filter_conditions',
    }
    return {'active_menu': menu_map.get(endpoint, '')}

@app.context_processor
def inject_breadcrumb():
    """为所有模板注入面包屑导航数据"""
    endpoint = request.endpoint
    breadcrumb_map = {
        'index': [('首页', url_for('index'))],
        'system_info': [('系统信息', url_for('system_info'))],
        'templates': [('预定义模版管理', None), ('模板管理', url_for('templates'))],
        'template_detail': [('预定义模版管理', None), ('模板管理', url_for('templates')), ('模板详情', None)],
        'items': [('预定义模版管理', None), ('监控项管理', url_for('items'))],
        'add_item': [('预定义模版管理', None), ('监控项管理', url_for('items')), ('添加监控项', None)],
        'edit_item': [('预定义模版管理', None), ('监控项管理', url_for('items')), ('编辑监控项', None)],
        'triggers': [('预定义模版管理', None), ('触发器管理', url_for('triggers'))],
        'add_trigger': [('预定义模版管理', None), ('触发器管理', url_for('triggers')), ('添加触发器', None)],
        'edit_trigger': [('预定义模版管理', None), ('触发器管理', url_for('triggers')), ('编辑触发器', None)],
        'item_prototypes': [('预定义模版管理', None), ('监控项原型管理', url_for('item_prototypes'))],
        'edit_item_prototype': [('预定义模版管理', None), ('监控项原型管理', url_for('item_prototypes')), ('编辑监控项原型', None)],
        'trigger_prototypes': [('预定义模版管理', None), ('触发器原型管理', url_for('trigger_prototypes'))],
        'edit_trigger_prototype': [('预定义模版管理', None), ('触发器原型管理', url_for('trigger_prototypes')), ('编辑触发器原型', None)],
        'items_review': [('复核表管理', None), ('监控项复核', url_for('items_review'))],
        'edit_item_review': [('复核表管理', None), ('监控项复核', url_for('items_review')), ('编辑复核记录', None)],
        'triggers_review': [('复核表管理', None), ('触发器复核', url_for('triggers_review'))],
        'edit_trigger_review': [('复核表管理', None), ('触发器复核', url_for('triggers_review')), ('编辑复核记录', None)],
        'item_prototypes_review': [('复核表管理', None), ('监控项原型复核', url_for('item_prototypes_review'))],
        'edit_item_prototype_review': [('复核表管理', None), ('监控项原型复核', url_for('item_prototypes_review')), ('编辑复核记录', None)],
        'trigger_prototypes_review': [('复核表管理', None), ('触发器原型复核', url_for('trigger_prototypes_review'))],
        'edit_trigger_prototype_review': [('复核表管理', None), ('触发器原型复核', url_for('trigger_prototypes_review')), ('编辑复核记录', None)],
        'hosts': [('主机管理', url_for('hosts'))],
        'add_host': [('主机管理', url_for('hosts')), ('添加主机', None)],
        'edit_host': [('主机管理', url_for('hosts')), ('编辑主机', None)],
        'discovery_rules': [('预定义模版管理', None), ('自动发现规则列表', url_for('discovery_rules'))],
        'edit_discovery_rule': [('预定义模版管理', None), ('自动发现规则列表', url_for('discovery_rules')), ('编辑规则', None)],
        'filter_conditions': [('预定义模版管理', None), ('自动发现过滤规则管理', url_for('filter_conditions'))],
        'edit_filter_condition': [('预定义模版管理', None), ('自动发现过滤规则管理', url_for('filter_conditions')), ('编辑过滤条件', None)],
    }
    return {'page_breadcrumb': breadcrumb_map.get(endpoint, [])}


@app.route('/')
def index():
    """首页 - 系统信息"""
    # 由于已删除所有 mac 开头的表，返回一个简单的系统信息页面
    stats = {
        'hosts': 0,
        'templates': 0,
        'items': 0,
        'triggers': 0,
        'discovery_rules': 0
    }
    hosts = []
    
    return render_template('index.html', stats=stats, hosts=hosts)

@app.route('/system-info')
def system_info():
    """系统信息详情页面"""
    # 由于已删除所有 mac 开头的表，返回一个简单的系统信息页面
    stats = {
        'hosts': 0,
        'templates': 0,
        'items': 0,
        'triggers': 0,
        'discovery_rules': 0,
        'item_prototypes': 0,
        'trigger_prototypes': 0
    }
    hosts = []
    all_items = []
    all_triggers = []
    
    return render_template('system_info.html', stats=stats, hosts=hosts, all_items=all_items, all_triggers=all_triggers)

@app.route('/templates')
def templates():
    """模板管理"""
    # 由于已删除所有 mac 开头的表，返回空列表
    templates = []
    return render_template('templates.html', templates=templates)

@app.route('/template/<int:template_id>')
def template_detail(template_id):
    """模板详情"""
    # 由于已删除所有 mac 开头的表，返回空数据
    flash('模板不存在')
    return redirect(url_for('templates'))

@app.route('/item-prototypes')
def item_prototypes():
    """监控项原型管理"""
    conn = get_db_connection()
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute("""
            SELECT ip.*, dr.name as rule_name, dr.template_name
            FROM item_prototypes ip
            JOIN discovery_rules dr ON ip.discovery_rule_id = dr.id
            ORDER BY ip.id
        """)
        prototypes = cur.fetchall()
    conn.close()
    return render_template('item_prototypes.html', prototypes=prototypes)

@app.route('/trigger-prototypes')
def trigger_prototypes():
    """触发器原型管理"""
    conn = get_db_connection()
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute("""
            SELECT tp.*, dr.name as rule_name, dr.template_name
            FROM trigger_prototypes tp
            JOIN discovery_rules dr ON tp.discovery_rule_id = dr.id
            ORDER BY tp.id
        """)
        prototypes = cur.fetchall()
    conn.close()
    return render_template('trigger_prototypes.html', prototypes=prototypes)

@app.route('/item-prototype/edit/<int:proto_id>', methods=['GET', 'POST'])
def edit_item_prototype(proto_id):
    """编辑监控项原型"""
    conn = get_db_connection()
    
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute("SELECT * FROM item_prototypes WHERE id = %s", (proto_id,))
        proto = cur.fetchone()
    
    if not proto:
        flash('监控项原型不存在')
        return redirect(url_for('item_prototypes'))
    
    if request.method == 'POST':
        name = request.form['name']
        key = request.form['key']
        value_type = int(request.form['value_type'])
        delay = request.form['delay']
        
        description = request.form.get('description')
        units = request.form.get('units')
        multiplier = request.form.get('multiplier', 0)
        delta = request.form.get('delta', 0)
        history = request.form.get('history', 7)
        trends = request.form.get('trends', 365)
        status = request.form.get('status', 0)
        
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE item_prototypes SET name = %s, key = %s, value_type = %s, 
                                               delay = %s, description = %s, units = %s, 
                                               multiplier = %s, delta = %s, history = %s, 
                                               trends = %s, status = %s
                    WHERE id = %s
                """, (name, key, value_type, delay, description, units, 
                       multiplier, delta, history, trends, status, proto_id))
            conn.commit()
            flash('监控项原型更新成功')
            return redirect(url_for('item_prototypes'))
        except Exception as e:
            conn.rollback()
            flash(f'更新失败: {e}')
    
    conn.close()
    return render_template('edit_item_prototype.html', proto=proto)

@app.route('/item-prototype/confirm/<int:proto_id>')
def confirm_item_prototype(proto_id):
    """确认监控项原型 - 复制到 item_prototypes_review"""
    conn = get_db_connection()
    
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            # 获取原型数据
            cur.execute("""
                SELECT ip.*, dr.host_ip, dr.system, dr.subsystem, dr.template_name
                FROM item_prototypes ip
                JOIN discovery_rules dr ON ip.discovery_rule_id = dr.id
                WHERE ip.id = %s
            """, (proto_id,))
            proto = cur.fetchone()
            
            if not proto:
                flash('监控项原型不存在')
                return redirect(url_for('item_prototypes'))
            
            # 复制到复核表
            cur.execute("""
                INSERT INTO item_prototypes_review (
                    item_prototype_id, discovery_rule_id, name, key, value_type, delay,
                    description, units, multiplier, delta, history, trends, status,
                    modified, confirmed, status_verification, host_ip, system, subsystem
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                proto['id'], proto['discovery_rule_id'], proto['name'], proto['key'],
                proto['value_type'], proto['delay'], proto['description'], proto['units'],
                proto['multiplier'], proto['delta'], proto['history'], proto['trends'],
                proto['status'], False, False, 'pending',
                proto['host_ip'], proto['system'], proto['subsystem']
            ))
        
        conn.commit()
        flash('监控项原型已添加到复核表')
    except Exception as e:
        conn.rollback()
        flash(f'添加失败: {e}')
    
    conn.close()
    return redirect(url_for('item_prototypes'))

@app.route('/trigger-prototype/edit/<int:proto_id>', methods=['GET', 'POST'])
def edit_trigger_prototype(proto_id):
    """编辑触发器原型"""
    conn = get_db_connection()
    
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute("SELECT * FROM trigger_prototypes WHERE id = %s", (proto_id,))
        proto = cur.fetchone()
    
    if not proto:
        flash('触发器原型不存在')
        return redirect(url_for('trigger_prototypes'))
    
    if request.method == 'POST':
        description = request.form['description']
        expression = request.form['expression']
        priority = int(request.form['priority'])
        status = request.form.get('status', 0)
        
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE trigger_prototypes SET description = %s, expression = %s, priority = %s, status = %s
                    WHERE id = %s
                """, (description, expression, priority, status, proto_id))
            conn.commit()
            flash('触发器原型更新成功')
            return redirect(url_for('trigger_prototypes'))
        except Exception as e:
            conn.rollback()
            flash(f'更新失败: {e}')
    
    conn.close()
    return render_template('edit_trigger_prototype.html', proto=proto)

@app.route('/trigger-prototype/confirm/<int:proto_id>')
def confirm_trigger_prototype(proto_id):
    """确认触发器原型 - 复制到 trigger_prototypes_review"""
    conn = get_db_connection()
    
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            # 获取原型数据
            cur.execute("""
                SELECT tp.*, dr.host_ip, dr.system, dr.subsystem
                FROM trigger_prototypes tp
                JOIN discovery_rules dr ON tp.discovery_rule_id = dr.id
                WHERE tp.id = %s
            """, (proto_id,))
            proto = cur.fetchone()
            
            if not proto:
                flash('触发器原型不存在')
                return redirect(url_for('trigger_prototypes'))
            
            # 复制到复核表
            cur.execute("""
                INSERT INTO trigger_prototypes_review (
                    trigger_prototype_id, discovery_rule_id, description, expression, 
                    priority, status, modified, confirmed, status_verification, 
                    host_ip, system, subsystem
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                proto['id'], proto['discovery_rule_id'], proto['description'],
                proto['expression'], proto['priority'], proto['status'],
                False, False, 'pending',
                proto['host_ip'], proto['system'], proto['subsystem']
            ))
        
        conn.commit()
        flash('触发器原型已添加到复核表')
    except Exception as e:
        conn.rollback()
        flash(f'添加失败: {e}')
    
    conn.close()
    return redirect(url_for('trigger_prototypes'))

@app.route('/items')
def items():
    """监控项管理"""
    conn = get_db_connection()
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute("SELECT * FROM items ORDER BY id")
        items = cur.fetchall()
    conn.close()
    return render_template('items.html', items=items)

@app.route('/item/add', methods=['GET', 'POST'])
def add_item():
    """添加监控项"""
    conn = get_db_connection()
    
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute("SELECT DISTINCT template_name FROM items ORDER BY template_name")
        templates = [row['template_name'] for row in cur.fetchall()]
    
    if request.method == 'POST':
        item_key = request.form['item_key']
        name = request.form['name']
        type = int(request.form['type'])
        value_type = int(request.form['value_type'])
        delay = request.form['delay']
        template_name = request.form['template_name']
        
        description = request.form.get('description')
        units = request.form.get('units')
        multiplier = request.form.get('multiplier', 0)
        delta = request.form.get('delta', 0)
        history = request.form.get('history', 7)
        trends = request.form.get('trends', 365)
        status = request.form.get('status', 0)
        master_item = request.form.get('master_item') or None
        preprocessing = request.form.get('preprocessing') or None
        
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO items (item_key, name, type, value_type, delay, description, units, 
                                          multiplier, delta, history, trends, status, template_name,
                                          master_item, preprocessing)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (item_key, name, type, value_type, delay, description, units, 
                       multiplier, delta, history, trends, status, template_name,
                       master_item, preprocessing))
            conn.commit()
            flash('监控项添加成功')
            return redirect(url_for('items'))
        except Exception as e:
            conn.rollback()
            flash(f'添加失败: {e}')
    
    conn.close()
    return render_template('add_item.html', templates=templates)

@app.route('/item/edit/<int:item_id>', methods=['GET', 'POST'])
def edit_item(item_id):
    """编辑监控项"""
    conn = get_db_connection()
    
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute("SELECT * FROM items WHERE id = %s", (item_id,))
        item = cur.fetchone()
    
    if not item:
        flash('监控项不存在')
        return redirect(url_for('items'))
    
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute("SELECT DISTINCT template_name FROM items ORDER BY template_name")
        templates = [row['template_name'] for row in cur.fetchall()]
    
    if request.method == 'POST':
        item_key = request.form['item_key']
        name = request.form['name']
        type = int(request.form['type'])
        value_type = int(request.form['value_type'])
        delay = request.form['delay']
        template_name = request.form['template_name']
        
        description = request.form.get('description')
        units = request.form.get('units')
        multiplier = request.form.get('multiplier', 0)
        delta = request.form.get('delta', 0)
        history = request.form.get('history', 7)
        trends = request.form.get('trends', 365)
        status = request.form.get('status', 0)
        master_item = request.form.get('master_item') or None
        preprocessing = request.form.get('preprocessing') or None
        
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE items SET item_key = %s, name = %s, type = %s, value_type = %s, 
                                        delay = %s, description = %s, units = %s, 
                                        multiplier = %s, delta = %s, history = %s, 
                                        trends = %s, status = %s, template_name = %s,
                                        master_item = %s, preprocessing = %s
                    WHERE id = %s
                """, (item_key, name, type, value_type, delay, description, units, 
                       multiplier, delta, history, trends, status, template_name,
                       master_item, preprocessing, item_id))
            conn.commit()
            flash('监控项更新成功')
            return redirect(url_for('items'))
        except Exception as e:
            conn.rollback()
            flash(f'更新失败: {e}')
    
    conn.close()
    return render_template('edit_item.html', item=item, templates=templates)

@app.route('/item/delete/<int:item_id>')
def delete_item(item_id):
    """删除监控项"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM items WHERE id = %s", (item_id,))
        conn.commit()
        flash('监控项删除成功')
    except Exception as e:
        conn.rollback()
        flash(f'删除失败: {e}')
    conn.close()
    return redirect(url_for('items'))

@app.route('/triggers')
def triggers():
    """触发器管理"""
    conn = get_db_connection()
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute("SELECT * FROM triggers ORDER BY id")
        triggers = cur.fetchall()
    conn.close()
    return render_template('triggers.html', triggers=triggers)

@app.route('/trigger/add', methods=['GET', 'POST'])
def add_trigger():
    """添加触发器"""
    conn = get_db_connection()
    
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute("SELECT DISTINCT template_name FROM triggers ORDER BY template_name")
        templates = [row['template_name'] for row in cur.fetchall()]
    
    if request.method == 'POST':
        name = request.form['name']
        expression = request.form['expression']
        priority = int(request.form['priority'])
        template_name = request.form['template_name']
        
        description = request.form.get('description')
        status = request.form.get('status', 0)
        
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO triggers (name, expression, priority, description, status, template_name)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (name, expression, priority, description, status, template_name))
            conn.commit()
            flash('触发器添加成功')
            return redirect(url_for('triggers'))
        except Exception as e:
            conn.rollback()
            flash(f'添加失败: {e}')
    
    conn.close()
    return render_template('add_trigger.html', templates=templates)

@app.route('/trigger/edit/<int:trigger_id>', methods=['GET', 'POST'])
def edit_trigger(trigger_id):
    """编辑触发器"""
    conn = get_db_connection()
    
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute("SELECT * FROM triggers WHERE id = %s", (trigger_id,))
        trigger = cur.fetchone()
    
    if not trigger:
        flash('触发器不存在')
        return redirect(url_for('triggers'))
    
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute("SELECT DISTINCT template_name FROM triggers ORDER BY template_name")
        templates = [row['template_name'] for row in cur.fetchall()]
    
    if request.method == 'POST':
        name = request.form['name']
        expression = request.form['expression']
        priority = int(request.form['priority'])
        template_name = request.form['template_name']
        
        description = request.form.get('description')
        status = request.form.get('status', 0)
        
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE triggers SET name = %s, expression = %s, priority = %s, 
                                           description = %s, status = %s, template_name = %s
                    WHERE id = %s
                """, (name, expression, priority, description, status, template_name, trigger_id))
            conn.commit()
            flash('触发器更新成功')
            return redirect(url_for('triggers'))
        except Exception as e:
            conn.rollback()
            flash(f'更新失败: {e}')
    
    conn.close()
    return render_template('edit_trigger.html', trigger=trigger, templates=templates)

@app.route('/trigger/delete/<int:trigger_id>')
def delete_trigger(trigger_id):
    """删除触发器"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM triggers WHERE id = %s", (trigger_id,))
        conn.commit()
        flash('触发器删除成功')
    except Exception as e:
        conn.rollback()
        flash(f'删除失败: {e}')
    conn.close()
    return redirect(url_for('triggers'))

@app.route('/hosts')
def hosts():
    """主机管理"""
    conn = get_db_connection()
    with conn.cursor(cursor_factory=DictCursor) as cur:
        # 直接从hosts表读取template_name
        cur.execute("SELECT * FROM hosts ORDER BY id")
        hosts = cur.fetchall()
    conn.close()
    return render_template('hosts.html', hosts=hosts)


@app.route('/host/sync', methods=['POST'])
def sync_hosts():
    """从 ops.sub_assets 同步主机资产到 zabbix_mac.hosts

    增量发现：通过 LEFT JOIN 对比源表与目标表，找出新增或变更的记录。
    幂等性：使用 ON CONFLICT (name) DO UPDATE 保证重复执行不产生重复数据。
    事务控制：整批操作在一个事务中，失败即 rollback。
    """
    conn = get_db_connection()
    synced_count = 0

    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            # 1. 增量发现：LEFT JOIN 对比，找出新增或变更的记录
            cur.execute("""
                SELECT sa.system, sa.subsystem, sa.hostname, sa.ip, sa.template_id
                FROM ops.sub_assets sa
                LEFT JOIN hosts h ON sa.ip = h.name
                WHERE h.id IS NULL
                   OR h.system IS DISTINCT FROM sa.system
                   OR h.subsystem IS DISTINCT FROM sa.subsystem
                   OR h.template_name IS DISTINCT FROM sa.template_id::varchar
            """)
            to_sync = cur.fetchall()

            # 2. 逐条 UPSERT 到 zabbix_mac.hosts
            for row in to_sync:
                cur.execute("""
                    INSERT INTO hosts (name, system, subsystem, template_name, description)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (name)
                    DO UPDATE SET
                        system = EXCLUDED.system,
                        subsystem = EXCLUDED.subsystem,
                        template_name = EXCLUDED.template_name,
                        description = EXCLUDED.description,
                        updated_at = CURRENT_TIMESTAMP
                """, (row['ip'], row['system'], row['subsystem'],
                      row['template_id'], row['hostname']))
                synced_count += 1

        conn.commit()
        return jsonify({
            'success': True,
            'message': f'同步成功：成功同步 {synced_count} 台主机',
            'synced_count': synced_count
        })
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': f'同步失败: {str(e)}'}), 500
    finally:
        conn.close()

@app.route('/host/add', methods=['GET', 'POST'])
def add_host():
    """添加主机"""
    if request.method == 'POST':
        name = request.form['name']
        template_name = request.form.get('template_name')
        description = request.form.get('description')
        system = request.form.get('system')
        subsystem = request.form.get('subsystem')
        
        conn = get_db_connection()
        try:
            # 插入主机基本信息，直接存储template_name
            with conn.cursor() as cur:
                cur.execute("INSERT INTO hosts (name, template_name, description, system, subsystem) VALUES (%s, %s, %s, %s, %s)", (name, template_name, description, system, subsystem))
            
            conn.commit()
            flash('主机添加成功')
            return redirect(url_for('hosts'))
        except Exception as e:
            conn.rollback()
            flash(f'添加失败: {e}')
        finally:
            conn.close()
    
    return render_template('add_host.html')

@app.route('/host/edit/<int:host_id>', methods=['GET', 'POST'])
def edit_host(host_id):
    """编辑主机"""
    conn = get_db_connection()
    
    # 获取主机信息，包括template_name
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute("SELECT * FROM hosts WHERE id = %s", (host_id,))
        host = cur.fetchone()
    
    if not host:
        flash('主机不存在')
        return redirect(url_for('hosts'))
    
    # 将host转换为普通字典
    host = dict(host)
    
    if request.method == 'POST':
        name = request.form['name']
        template_name = request.form.get('template_name')
        description = request.form.get('description')
        system = request.form.get('system')
        subsystem = request.form.get('subsystem')
        
        try:
            # 更新主机基本信息，直接更新template_name
            with conn.cursor() as cur:
                cur.execute("UPDATE hosts SET name = %s, template_name = %s, description = %s, system = %s, subsystem = %s WHERE id = %s", (name, template_name, description, system, subsystem, host_id))
            
            conn.commit()
            flash('主机更新成功')
            return redirect(url_for('hosts'))
        except Exception as e:
            conn.rollback()
            flash(f'更新失败: {e}')
    
    conn.close()
    return render_template('edit_host.html', host=host)

@app.route('/host/delete/<int:host_id>')
def delete_host(host_id):
    """删除主机"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM hosts WHERE id = %s", (host_id,))
        conn.commit()
        flash('主机删除成功')
    except Exception as e:
        conn.rollback()
        flash(f'删除失败: {e}')
    conn.close()
    return redirect(url_for('hosts'))

# 复核表管理路由

@app.route('/items-review')
def items_review():
    """监控项复核表管理 — 支持 ip/system/subsystem 过滤"""
    ip = request.args.get('ip', '').strip()
    system = request.args.get('system', '').strip()
    subsystem = request.args.get('subsystem', '').strip()

    conn = get_db_connection()
    with conn.cursor(cursor_factory=DictCursor) as cur:
        query = "SELECT * FROM items_review WHERE 1=1"
        params = []
        if ip:
            query += " AND host_ip ILIKE %s"
            params.append(f'%{ip}%')
        if system:
            query += " AND system ILIKE %s"
            params.append(f'%{system}%')
        if subsystem:
            query += " AND subsystem ILIKE %s"
            params.append(f'%{subsystem}%')
        query += " ORDER BY id"
        cur.execute(query, params)
        items = cur.fetchall()

        # 获取 system / subsystem 去重值供 datalist 下拉建议
        cur.execute("SELECT DISTINCT system FROM items_review WHERE system IS NOT NULL AND system != '' ORDER BY system")
        distinct_systems = [r['system'] for r in cur.fetchall()]
        cur.execute("SELECT DISTINCT subsystem FROM items_review WHERE subsystem IS NOT NULL AND subsystem != '' ORDER BY subsystem")
        distinct_subsystems = [r['subsystem'] for r in cur.fetchall()]

    conn.close()
    return render_template('items_review.html', items=items,
                           distinct_systems=distinct_systems,
                           distinct_subsystems=distinct_subsystems)


@app.route('/items-review/initialize', methods=['POST'])
def initialize_items_review():
    """初始化 items_review 表：清空并重新从 items × hosts 填充"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM items_review")
            deleted = cur.rowcount
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
            inserted = cur.rowcount
        conn.commit()
        return jsonify({
            'success': True,
            'message': f'items_review 表初始化成功：删除 {deleted} 条，插入 {inserted} 条'
        })
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': f'初始化失败: {str(e)}'}), 500
    finally:
        conn.close()


@app.route('/items-review/sync', methods=['POST'])
def sync_items_to_zabbix():
    """将已确认的监控项同步至指定环境机房的 Zabbix Server"""
    data = request.get_json()
    environment = data.get('environment', '').strip() if data else ''

    if environment not in ZABBIX_ENVIRONMENTS:
        return jsonify({'success': False, 'message': f'无效的环境: {environment}'}), 400

    env_config = ZABBIX_ENVIRONMENTS[environment]
    if not env_config['url']:
        return jsonify({'success': False, 'message': f'环境 "{environment}" 未配置 Zabbix URL，请设置环境变量'}), 500

    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("SELECT * FROM items_review WHERE confirmed = TRUE ORDER BY host_ip, item_key")
            confirmed_items = cur.fetchall()
    finally:
        conn.close()

    if not confirmed_items:
        return jsonify({'success': True, 'message': '没有已确认的监控项需要同步', 'synced_count': 0})

    # 调用 Zabbix API 逐条同步
    from zabbix_mac import ZabbixClient, ZabbixAPIException

    client = ZabbixClient(env_config['url'], env_config['username'], env_config['password'])
    created = 0
    updated = 0
    errors = []

    for row in confirmed_items:
        try:
            host_ip = row['host_ip']
            host_id = client.get_host_id(host_ip)
            if not host_id:
                errors.append(f'主机 {host_ip} 在 Zabbix 中不存在')
                continue

            interface_id = client.get_host_interface_id(host_id)
            if not interface_id:
                errors.append(f'主机 {host_ip} 无可用接口')
                continue

            item_data = {
                'hostid': host_id,
                'key_': row['item_key'],
                'name': row['name'],
                'type': row['type'],
                'value_type': row['value_type'],
                'delay': row['delay'],
                'interfaceid': interface_id,
            }
            if row.get('description'):
                item_data['description'] = row['description']
            if row.get('units'):
                item_data['units'] = row['units']
            if row.get('history'):
                item_data['history'] = str(row['history'])
            if row.get('trends'):
                item_data['trends'] = str(row['trends'])
            if row.get('status'):
                item_data['status'] = row['status']
            if row.get('master_item'):
                item_data['master_item'] = row['master_item']
            if row.get('preprocessing'):
                item_data['preprocessing'] = row['preprocessing']

            # 检查是否已存在
            existing_items = client.get_managed_items(host_id)
            existing_keys = {item['key_']: item for item in existing_items}

            if row['item_key'] in existing_keys:
                existing = existing_keys[row['item_key']]
                target_fp = client.calculate_fingerprint(item_data)
                current_fp = client.calculate_fingerprint(existing)
                if target_fp != current_fp:
                    client.update_item(existing['itemid'], item_data)
                    updated += 1
            else:
                client.create_item(item_data)
                created += 1

        except ZabbixAPIException as e:
            errors.append(f'{host_ip}/{row["item_key"]}: Zabbix API 错误 - {e}')
        except Exception as e:
            errors.append(f'{host_ip}/{row["item_key"]}: {e}')

    msg = f'已成功同步至{environment} Zabbix：新建 {created}，更新 {updated}'
    if errors:
        msg += f'，{len(errors)} 个失败'
        return jsonify({'success': True, 'message': msg, 'synced_count': created + updated,
                        'errors': errors[:10]})
    return jsonify({'success': True, 'message': msg, 'synced_count': created + updated})

@app.route('/item-review/edit/<int:review_id>', methods=['GET', 'POST'])
def edit_item_review(review_id):
    """编辑监控项复核表记录"""
    conn = get_db_connection()
    
    # 获取记录信息
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute("SELECT * FROM items_review WHERE id = %s", (review_id,))
        item = cur.fetchone()
    
    if not item:
        flash('记录不存在')
        return redirect(url_for('items_review'))
    
    if request.method == 'POST':
        # 获取表单数据
        item_key = request.form['item_key']
        name = request.form['name']
        type = int(request.form['type'])
        value_type = int(request.form['value_type'])
        delay = request.form['delay']
        host_ip = request.form['host_ip']
        
        # 可选字段
        description = request.form.get('description')
        units = request.form.get('units')
        multiplier = request.form.get('multiplier', 0)
        delta = request.form.get('delta', 0)
        history = request.form.get('history', 7)
        trends = request.form.get('trends', 365)
        status = request.form.get('status', 0)
        master_item = request.form.get('master_item')
        preprocessing = request.form.get('preprocessing')
        template_name = request.form['template_name']
        system = request.form.get('system')
        subsystem = request.form.get('subsystem')
        
        # 更新数据
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE items_review SET item_key = %s, name = %s, type = %s, value_type = %s, 
                                        delay = %s, description = %s, units = %s, 
                                        multiplier = %s, delta = %s, history = %s, 
                                        trends = %s, status = %s, master_item = %s, 
                                        preprocessing = %s, template_name = %s,
                                        system = %s, subsystem = %s, host_ip = %s, modified = true
                    WHERE id = %s
                """, (item_key, name, type, value_type, delay, description, units, 
                       multiplier, delta, history, trends, status, master_item, 
                       preprocessing, template_name, system, subsystem, host_ip, review_id))
            conn.commit()
            flash('记录更新成功')
            return redirect(url_for('items_review'))
        except Exception as e:
            conn.rollback()
            flash(f'更新失败: {e}')
    
    conn.close()
    return render_template('edit_item_review.html', item=item)

@app.route('/item-review/confirm/<int:review_id>')
def confirm_item_review(review_id):
    """确认监控项复核表记录"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE items_review SET confirmed = true WHERE id = %s", (review_id,))
        conn.commit()
        flash('记录已确认')
    except Exception as e:
        conn.rollback()
        flash(f'确认失败: {e}')
    conn.close()
    return redirect(url_for('items_review'))

@app.route('/item-review/unconfirm/<int:review_id>')
def unconfirm_item_review(review_id):
    """取消确认监控项复核表记录"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE items_review SET confirmed = false WHERE id = %s", (review_id,))
        conn.commit()
        flash('记录已取消确认')
    except Exception as e:
        conn.rollback()
        flash(f'取消确认失败: {e}')
    conn.close()
    return redirect(url_for('items_review'))


@app.route('/item-review/add', methods=['POST'])
def add_item_from_review():
    """从复核页面添加监控项：写入 items 主表 + items_review 复核表"""
    conn = get_db_connection()
    try:
        item_key = request.form['item_key']
        name = request.form['name']
        type_val = int(request.form['type'])
        value_type = int(request.form['value_type'])
        delay = request.form['delay']
        template_name = request.form['template_name']
        host_ip = request.form.get('host_ip', '').strip()

        description = request.form.get('description')
        units = request.form.get('units')
        multiplier = request.form.get('multiplier', 0)
        delta = request.form.get('delta', 0)
        history = request.form.get('history', 7)
        trends = request.form.get('trends', 365)
        status = request.form.get('status', 0)
        master_item = request.form.get('master_item') or None
        preprocessing = request.form.get('preprocessing') or None

        with conn.cursor() as cur:
            # 1. 写入主表 items，返回新 ID
            cur.execute("""
                INSERT INTO items (item_key, name, type, value_type, delay, description, units,
                                   multiplier, delta, history, trends, status, template_name,
                                   master_item, preprocessing)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (item_key, name, type_val, value_type, delay, description, units,
                   multiplier, delta, history, trends, status, template_name,
                   master_item, preprocessing))
            new_item_id = cur.fetchone()[0]

            # 2. 写入复核表 items_review
            cur.execute("""
                INSERT INTO items_review (
                    item_id, host_ip, item_key, name, type, value_type, delay,
                    description, units, multiplier, delta, history, trends,
                    status, template_name, master_item, preprocessing,
                    modified, confirmed, status_verification
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (new_item_id, host_ip, item_key, name, type_val, value_type, delay,
                   description, units, multiplier, delta, history, trends, status,
                   template_name, master_item, preprocessing,
                   False, False, 'pending'))

        conn.commit()
        return jsonify({'success': True, 'message': '监控项添加成功'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': f'添加失败: {str(e)}'}), 500
    finally:
        conn.close()


@app.route('/triggers-review')
def triggers_review():
    """触发器复核表管理 — 支持 ip/system/subsystem 过滤"""
    ip = request.args.get('ip', '').strip()
    system = request.args.get('system', '').strip()
    subsystem = request.args.get('subsystem', '').strip()

    conn = get_db_connection()
    with conn.cursor(cursor_factory=DictCursor) as cur:
        query = "SELECT * FROM triggers_review WHERE 1=1"
        params = []
        if ip:
            query += " AND host_ip ILIKE %s"
            params.append(f'%{ip}%')
        if system:
            query += " AND system ILIKE %s"
            params.append(f'%{system}%')
        if subsystem:
            query += " AND subsystem ILIKE %s"
            params.append(f'%{subsystem}%')
        query += " ORDER BY id"
        cur.execute(query, params)
        triggers = cur.fetchall()

        # datalist 数据
        cur.execute("SELECT DISTINCT system FROM triggers_review WHERE system IS NOT NULL AND system != '' ORDER BY system")
        distinct_systems = [r['system'] for r in cur.fetchall()]
        cur.execute("SELECT DISTINCT subsystem FROM triggers_review WHERE subsystem IS NOT NULL AND subsystem != '' ORDER BY subsystem")
        distinct_subsystems = [r['subsystem'] for r in cur.fetchall()]

    conn.close()
    return render_template('triggers_review.html', triggers=triggers,
                           distinct_systems=distinct_systems,
                           distinct_subsystems=distinct_subsystems)


@app.route('/triggers-review/initialize', methods=['POST'])
def initialize_triggers_review():
    """初始化 triggers_review 表：清空并重新从 triggers × hosts 填充"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM triggers_review")
            deleted = cur.rowcount
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
            inserted = cur.rowcount
        conn.commit()
        return jsonify({
            'success': True,
            'message': f'triggers_review 表初始化成功：删除 {deleted} 条，插入 {inserted} 条'
        })
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': f'初始化失败: {str(e)}'}), 500
    finally:
        conn.close()

@app.route('/trigger-review/edit/<int:review_id>', methods=['GET', 'POST'])
def edit_trigger_review(review_id):
    """编辑触发器复核表记录"""
    conn = get_db_connection()
    
    # 获取记录信息
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute("SELECT * FROM triggers_review WHERE id = %s", (review_id,))
        trigger = cur.fetchone()
    
    if not trigger:
        flash('记录不存在')
        return redirect(url_for('triggers_review'))
    
    if request.method == 'POST':
        # 获取表单数据
        name = request.form['name']
        expression = request.form['expression']
        priority = int(request.form['priority'])
        host_ip = request.form['host_ip']
        template_name = request.form['template_name']
        
        # 可选字段
        description = request.form.get('description')
        status = request.form.get('status', 0)
        
        # 更新数据
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE triggers_review SET name = %s, expression = %s, priority = %s, 
                                           description = %s, status = %s, template_name = %s,
                                           host_ip = %s, modified = true
                    WHERE id = %s
                """, (name, expression, priority, description, status, template_name, host_ip, review_id))
            conn.commit()
            flash('记录更新成功')
            return redirect(url_for('triggers_review'))
        except Exception as e:
            conn.rollback()
            flash(f'更新失败: {e}')
    
    conn.close()
    return render_template('edit_trigger_review.html', trigger=trigger)

@app.route('/trigger-review/confirm/<int:review_id>')
def confirm_trigger_review(review_id):
    """确认触发器复核表记录"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE triggers_review SET confirmed = true WHERE id = %s", (review_id,))
        conn.commit()
        flash('记录已确认')
    except Exception as e:
        conn.rollback()
        flash(f'确认失败: {e}')
    conn.close()
    return redirect(url_for('triggers_review'))

@app.route('/trigger-review/unconfirm/<int:review_id>')
def unconfirm_trigger_review(review_id):
    """取消确认触发器复核表记录"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE triggers_review SET confirmed = false WHERE id = %s", (review_id,))
        conn.commit()
        flash('记录已取消确认')
    except Exception as e:
        conn.rollback()
        flash(f'取消确认失败: {e}')
    conn.close()
    return redirect(url_for('triggers_review'))


@app.route('/trigger-review/add', methods=['POST'])
def add_trigger_from_review():
    """从复核页面添加触发器：写入 triggers 主表 + triggers_review 复核表"""
    conn = get_db_connection()
    try:
        name = request.form['name']
        expression = request.form['expression']
        priority = int(request.form['priority'])
        template_name = request.form['template_name']
        host_ip = request.form.get('host_ip', '').strip()

        description = request.form.get('description')
        status = request.form.get('status', 0)

        with conn.cursor() as cur:
            # 1. 写入主表 triggers，返回新 ID
            cur.execute("""
                INSERT INTO triggers (name, expression, priority, description, status, template_name)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (name, expression, priority, description, status, template_name))
            new_trigger_id = cur.fetchone()[0]

            # 2. 写入复核表 triggers_review
            cur.execute("""
                INSERT INTO triggers_review (
                    trigger_id, host_ip, name, expression, priority, description,
                    status, template_name,
                    modified, confirmed, status_verification
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (new_trigger_id, host_ip, name, expression, priority, description,
                   status, template_name,
                   False, False, 'pending'))

        conn.commit()
        return jsonify({'success': True, 'message': '触发器添加成功'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': f'添加失败: {str(e)}'}), 500
    finally:
        conn.close()


@app.route('/item-prototypes-review')
def item_prototypes_review():
    """监控项原型复核表管理"""
    conn = get_db_connection()
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute("SELECT * FROM item_prototypes_review ORDER BY id")
        prototypes = cur.fetchall()
    conn.close()
    return render_template('item_prototypes_review.html', prototypes=prototypes)

@app.route('/item-prototype-review/edit/<int:review_id>', methods=['GET', 'POST'])
def edit_item_prototype_review(review_id):
    """编辑监控项原型复核表记录"""
    conn = get_db_connection()
    
    # 获取记录信息
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute("SELECT * FROM item_prototypes_review WHERE id = %s", (review_id,))
        prototype = cur.fetchone()
    
    if not prototype:
        flash('记录不存在')
        return redirect(url_for('item_prototypes_review'))
    
    if request.method == 'POST':
        # 获取表单数据
        name = request.form['name']
        key = request.form['key']
        value_type = int(request.form['value_type'])
        delay = request.form['delay']
        host_ip = request.form['host_ip']
        
        # 可选字段
        description = request.form.get('description')
        units = request.form.get('units')
        multiplier = request.form.get('multiplier', 0)
        delta = request.form.get('delta', 0)
        history = request.form.get('history', 7)
        trends = request.form.get('trends', 365)
        status = request.form.get('status', 0)
        
        # 更新数据
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE item_prototypes_review SET name = %s, key = %s, value_type = %s, 
                                               delay = %s, description = %s, units = %s, 
                                               multiplier = %s, delta = %s, history = %s, 
                                               trends = %s, status = %s, host_ip = %s,
                                               modified = true
                    WHERE id = %s
                """, (name, key, value_type, delay, description, units, 
                       multiplier, delta, history, trends, status, host_ip, review_id))
            conn.commit()
            flash('记录更新成功')
            return redirect(url_for('item_prototypes_review'))
        except Exception as e:
            conn.rollback()
            flash(f'更新失败: {e}')
    
    conn.close()
    return render_template('edit_item_prototype_review.html', prototype=prototype)

@app.route('/item-prototype-review/confirm/<int:review_id>')
def confirm_item_prototype_review(review_id):
    """确认监控项原型复核表记录"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE item_prototypes_review SET confirmed = true WHERE id = %s", (review_id,))
        conn.commit()
        flash('记录已确认')
    except Exception as e:
        conn.rollback()
        flash(f'确认失败: {e}')
    conn.close()
    return redirect(url_for('item_prototypes_review'))

@app.route('/item-prototype-review/unconfirm/<int:review_id>')
def unconfirm_item_prototype_review(review_id):
    """取消确认监控项原型复核表记录"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE item_prototypes_review SET confirmed = false WHERE id = %s", (review_id,))
        conn.commit()
        flash('记录已取消确认')
    except Exception as e:
        conn.rollback()
        flash(f'取消确认失败: {e}')
    conn.close()
    return redirect(url_for('item_prototypes_review'))

@app.route('/trigger-prototypes-review')
def trigger_prototypes_review():
    """触发器原型复核表管理"""
    conn = get_db_connection()
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute("SELECT * FROM trigger_prototypes_review ORDER BY id")
        prototypes = cur.fetchall()
    conn.close()
    return render_template('trigger_prototypes_review.html', prototypes=prototypes)

@app.route('/trigger-prototype-review/edit/<int:review_id>', methods=['GET', 'POST'])
def edit_trigger_prototype_review(review_id):
    """编辑触发器原型复核表记录"""
    conn = get_db_connection()
    
    # 获取记录信息
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute("SELECT * FROM trigger_prototypes_review WHERE id = %s", (review_id,))
        prototype = cur.fetchone()
    
    if not prototype:
        flash('记录不存在')
        return redirect(url_for('trigger_prototypes_review'))
    
    if request.method == 'POST':
        # 获取表单数据
        description = request.form['description']
        expression = request.form['expression']
        priority = int(request.form['priority'])
        host_ip = request.form['host_ip']
        
        # 可选字段
        status = request.form.get('status', 0)
        
        # 更新数据
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE trigger_prototypes_review SET description = %s, expression = %s, 
                                                   priority = %s, status = %s, host_ip = %s,
                                                   modified = true
                    WHERE id = %s
                """, (description, expression, priority, status, host_ip, review_id))
            conn.commit()
            flash('记录更新成功')
            return redirect(url_for('trigger_prototypes_review'))
        except Exception as e:
            conn.rollback()
            flash(f'更新失败: {e}')
    
    conn.close()
    return render_template('edit_trigger_prototype_review.html', prototype=prototype)

@app.route('/trigger-prototype-review/confirm/<int:review_id>')
def confirm_trigger_prototype_review(review_id):
    """确认触发器原型复核表记录"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE trigger_prototypes_review SET confirmed = true WHERE id = %s", (review_id,))
        conn.commit()
        flash('记录已确认')
    except Exception as e:
        conn.rollback()
        flash(f'确认失败: {e}')
    conn.close()
    return redirect(url_for('trigger_prototypes_review'))

@app.route('/trigger-prototype-review/unconfirm/<int:review_id>')
def unconfirm_trigger_prototype_review(review_id):
    """取消确认触发器原型复核表记录"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE trigger_prototypes_review SET confirmed = false WHERE id = %s", (review_id,))
        conn.commit()
        flash('记录已取消确认')
    except Exception as e:
        conn.rollback()
        flash(f'取消确认失败: {e}')
    conn.close()
    return redirect(url_for('trigger_prototypes_review'))

# ============================================================
# 自动发现规则管理
# ============================================================

@app.route('/discovery-rules')
def discovery_rules():
    """自动发现规则列表"""
    conn = get_db_connection()
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute("""
            SELECT dr.*,
                   (SELECT COUNT(*) FROM filter_conditions fc WHERE fc.discovery_rule_id = dr.id) as filter_count
            FROM discovery_rules dr
            ORDER BY dr.id
        """)
        rules = cur.fetchall()
    conn.close()
    return render_template('discovery_rules.html', rules=rules)

@app.route('/discovery-rule/edit/<int:rule_id>', methods=['GET', 'POST'])
def edit_discovery_rule(rule_id):
    """编辑自动发现规则"""
    conn = get_db_connection()

    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute("SELECT * FROM discovery_rules WHERE id = %s", (rule_id,))
        rule = cur.fetchone()

    if not rule:
        flash('自动发现规则不存在')
        return redirect(url_for('discovery_rules'))

    if request.method == 'POST':
        name = request.form['name']
        key = request.form['key']
        delay = request.form['delay']
        evaltype = int(request.form.get('evaltype', 0))
        status = int(request.form.get('status', 0))
        template_name = request.form['template_name']

        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE discovery_rules
                    SET name = %s, key = %s, delay = %s, evaltype = %s, status = %s, template_name = %s
                    WHERE id = %s
                """, (name, key, delay, evaltype, status, template_name, rule_id))
            conn.commit()
            flash('自动发现规则更新成功')
            return redirect(url_for('discovery_rules'))
        except Exception as e:
            conn.rollback()
            flash(f'更新失败: {e}')

    conn.close()
    return render_template('edit_discovery_rule.html', rule=rule)


# ============================================================
# 自动发现过滤规则管理
# ============================================================

@app.route('/filter-conditions')
def filter_conditions():
    """自动发现过滤规则管理列表"""
    conn = get_db_connection()
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute("""
            SELECT fc.*, dr.name as rule_name, dr.template_name
            FROM filter_conditions fc
            JOIN discovery_rules dr ON fc.discovery_rule_id = dr.id
            ORDER BY fc.id
        """)
        conditions = cur.fetchall()
    conn.close()
    return render_template('filter_conditions.html', conditions=conditions)

@app.route('/filter-condition/edit/<int:cond_id>', methods=['GET', 'POST'])
def edit_filter_condition(cond_id):
    """编辑过滤条件"""
    conn = get_db_connection()

    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute("SELECT * FROM filter_conditions WHERE id = %s", (cond_id,))
        cond = cur.fetchone()

    if not cond:
        flash('过滤条件不存在')
        return redirect(url_for('filter_conditions'))

    # 获取所有自动发现规则用于下拉选择
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute("SELECT id, name, template_name FROM discovery_rules ORDER BY template_name, name")
        discovery_rules_list = cur.fetchall()

    if request.method == 'POST':
        macro = request.form['macro']
        value = request.form['value']
        operator = request.form['operator']
        discovery_rule_id = int(request.form['discovery_rule_id'])

        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE filter_conditions
                    SET macro = %s, value = %s, operator = %s, discovery_rule_id = %s
                    WHERE id = %s
                """, (macro, value, operator, discovery_rule_id, cond_id))
            conn.commit()
            flash('过滤条件更新成功')
            return redirect(url_for('filter_conditions'))
        except Exception as e:
            conn.rollback()
            flash(f'更新失败: {e}')

    conn.close()
    return render_template('edit_filter_condition.html', cond=cond, discovery_rules=discovery_rules_list)


# ============================================================
# 全局搜索
# ============================================================

@app.route('/api/search')
def api_search():
    """全局搜索 API - 搜索监控项、触发器、主机、模板、自动发现规则"""
    q = request.args.get('q', '').strip()
    if not q or len(q) < 2:
        return jsonify({'results': []})

    search_term = f'%{q}%'
    conn = get_db_connection()
    results = []

    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            # 搜索监控项
            cur.execute(
                "SELECT id, name, item_key, template_name, 'item' as type FROM items WHERE name ILIKE %s OR item_key ILIKE %s LIMIT 10",
                (search_term, search_term)
            )
            for row in cur.fetchall():
                results.append({
                    'id': row['id'],
                    'name': row['name'],
                    'detail': row['item_key'],
                    'type': 'item',
                    'type_label': '监控项',
                    'url': url_for('edit_item', item_id=row['id'])
                })

            # 搜索触发器
            cur.execute(
                "SELECT id, name, expression, template_name, 'trigger' as type FROM triggers WHERE name ILIKE %s OR expression ILIKE %s LIMIT 10",
                (search_term, search_term)
            )
            for row in cur.fetchall():
                results.append({
                    'id': row['id'],
                    'name': row['name'],
                    'detail': (row['expression'] or '')[:50],
                    'type': 'trigger',
                    'type_label': '触发器',
                    'url': url_for('edit_trigger', trigger_id=row['id'])
                })

            # 搜索主机
            cur.execute(
                "SELECT id, name, template_name, 'host' as type FROM hosts WHERE name ILIKE %s OR template_name ILIKE %s LIMIT 10",
                (search_term, search_term)
            )
            for row in cur.fetchall():
                results.append({
                    'id': row['id'],
                    'name': row['name'],
                    'detail': row.get('template_name', ''),
                    'type': 'host',
                    'type_label': '主机',
                    'url': url_for('edit_host', host_id=row['id'])
                })

            # 搜索模板
            cur.execute(
                "SELECT id, name, 'template' as type FROM templates WHERE name ILIKE %s LIMIT 10",
                (search_term,)
            )
            for row in cur.fetchall():
                results.append({
                    'id': row['id'],
                    'name': row['name'],
                    'detail': '',
                    'type': 'template',
                    'type_label': '模板',
                    'url': url_for('template_detail', template_id=row['id'])
                })

            # 搜索自动发现规则
            cur.execute(
                "SELECT id, name, key, template_name, 'discovery_rule' as type FROM discovery_rules WHERE name ILIKE %s OR key ILIKE %s LIMIT 10",
                (search_term, search_term)
            )
            for row in cur.fetchall():
                results.append({
                    'id': row['id'],
                    'name': row['name'],
                    'detail': row['key'],
                    'type': 'discovery_rule',
                    'type_label': '自动发现规则',
                    'url': url_for('edit_discovery_rule', rule_id=row['id'])
                })
    finally:
        conn.close()

    return jsonify({'results': results, 'query': q})

@app.route('/search')
def search():
    """全局搜索结果页"""
    q = request.args.get('q', '')
    return render_template('search.html', query=q)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
