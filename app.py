#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Zabbix Monitor as Code (MaC) 管理界面

基于 Flask 的 Web 应用，用于管理 PostgreSQL 中的监控配置数据
"""

from flask import Flask, render_template, request, redirect, url_for, flash
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

def get_db_connection():
    """获取数据库连接"""
    conn = psycopg2.connect(**DB_CONFIG)
    conn.set_client_encoding('utf8')
    return conn

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
            ORDER BY dr.template_name, dr.name, ip.name
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
            ORDER BY dr.template_name, dr.name, tp.description
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
        cur.execute("SELECT * FROM items ORDER BY template_name, item_key")
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
        cur.execute("SELECT * FROM triggers ORDER BY template_name, name")
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
        cur.execute("SELECT * FROM hosts ORDER BY name")
        hosts = cur.fetchall()
    conn.close()
    return render_template('hosts.html', hosts=hosts)

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
    """监控项复核表管理"""
    conn = get_db_connection()
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute("SELECT * FROM items_review ORDER BY host_ip, item_key")
        items = cur.fetchall()
    conn.close()
    return render_template('items_review.html', items=items)

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

@app.route('/triggers-review')
def triggers_review():
    """触发器复核表管理"""
    conn = get_db_connection()
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute("SELECT * FROM triggers_review ORDER BY host_ip, name")
        triggers = cur.fetchall()
    conn.close()
    return render_template('triggers_review.html', triggers=triggers)

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

@app.route('/item-prototypes-review')
def item_prototypes_review():
    """监控项原型复核表管理"""
    conn = get_db_connection()
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute("SELECT * FROM item_prototypes_review ORDER BY host_ip, name")
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
        cur.execute("SELECT * FROM trigger_prototypes_review ORDER BY host_ip, description")
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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
