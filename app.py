#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Zabbix Monitor as Code (MaC) 管理界面

基于 Flask 的 Web 应用，用于管理 PostgreSQL 中的监控配置数据
"""

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file, session
import logging
import os
import itertools
import re
import secrets
import ast
import io
import tempfile
import sys
import platform
import time
from datetime import datetime
import psycopg2
from psycopg2.extras import DictCursor
import pandas as pd
import json

from config_loader import load_config, get_db_config, get_zabbix_environments

from typing import Any, List

app = Flask(__name__)

# 请求结束时自动关闭数据库连接（防止连接泄漏）
@app.teardown_appcontext
def _close_db_connection(exception=None):
    from flask import g
    conn = g.pop('_db_conn', None)
    if conn is not None:
        try:
            conn.close()
        except Exception:
            pass

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
app.logger.setLevel(logging.INFO)

# 加载外部配置（环境变量 > config.yaml > 内置默认值）
_config = load_config()
app.secret_key = _config['app']['secret_key']

# 安全检查：拒绝默认密钥
if app.secret_key == 'dev-secret-key-change-me':
    app.logger.critical("SECURITY: 使用默认 secret_key，请设置 APP_SECRET_KEY 环境变量!")
    raise RuntimeError("默认 secret_key 不允许用于生产环境，请设置 APP_SECRET_KEY 环境变量")

app.config['DEFAULT_TEMPLATE_NAME'] = _config['app'].get('default_template_name', '21001')

# ---- CSRF 保护 ----
def _generate_csrf_token():
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_hex(32)
    return session['_csrf_token']

@app.before_request
def _validate_csrf():
    if request.method in ('POST', 'PUT', 'DELETE', 'PATCH'):
        token = session.get('_csrf_token')
        if not token:
            _generate_csrf_token()
            token = session['_csrf_token']
        req_token = request.form.get('_csrf_token') or request.headers.get('X-CSRF-Token')
        if not req_token or not secrets.compare_digest(token, req_token):
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': 'CSRF 验证失败，请刷新页面重试'}), 403
            flash('CSRF 验证失败，请刷新页面重试')
            return redirect(request.referrer or url_for('index'))

# 数据库连接配置
DB_CONFIG = get_db_config(_config)

# Zabbix 环境机房配置
ZABBIX_ENVIRONMENTS = get_zabbix_environments(_config)

# ---- 系统运行时间追踪 ----
START_TIME = time.time()


def _format_uptime():
    seconds = int(time.time() - START_TIME)
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60
    return f"{days}天 {hours}小时 {minutes}分钟"


# ---- Excel 导入安全工具 ----
# 每个表允许的列名白名单
_ALLOWED_IMPORT_COLUMNS = {
    'items': {'item_key', 'name', 'type', 'value_type', 'delay', 'description', 'units',
              'multiplier', 'delta', 'history', 'trends', 'status', 'template_name',
              'master_item', 'preprocessing'},
    'triggers': {'name', 'expression', 'priority', 'description', 'status', 'template_name'},
    'item_prototypes': {'name', 'key', 'value_type', 'delay', 'description', 'units',
                        'multiplier', 'delta', 'history', 'trends', 'status',
                        'discovery_rule_id'},
    'trigger_prototypes': {'description', 'expression', 'priority', 'status', 'discovery_rule_id'},
    'discovery_rules': {'name', 'key', 'delay', 'type', 'status', 'template_name'},
    'filter_conditions': {'macro', 'value', 'operator', 'discovery_rule_id'},
    'items_review': {'item_key', 'name', 'type', 'value_type', 'delay', 'description', 'units',
                     'multiplier', 'delta', 'history', 'trends', 'status', 'template_name',
                     'host_ip', 'master_item', 'preprocessing', 'system', 'subsystem',
                     'confirmed', 'modified', 'status_verification', 'in_room',
                     'sync_status', 'change_type'},
    'triggers_review': {'name', 'expression', 'priority', 'description', 'status',
                        'template_name', 'host_ip', 'system', 'subsystem',
                        'confirmed', 'modified', 'status_verification', 'in_room',
                        'sync_status', 'change_type'},
    'item_prototypes_review': {'name', 'key', 'value_type', 'delay', 'description', 'units',
                               'multiplier', 'delta', 'history', 'trends', 'status',
                               'host_ip', 'discovery_rule_id', 'system', 'subsystem',
                               'confirmed', 'modified', 'status_verification', 'in_room',
                               'sync_status', 'change_type'},
    'trigger_prototypes_review': {'description', 'expression', 'priority', 'status',
                                  'host_ip', 'discovery_rule_id', 'system', 'subsystem',
                                  'confirmed', 'modified', 'status_verification', 'in_room',
                                  'sync_status', 'change_type'},
    'webscenario_items_review': {'name', 'host', 'url', 'status_code', 'system', 'subsystem',
                                  'confirmed', 'modified', 'status_verification', 'in_room',
                                  'sync_status', 'change_type'},
    'webscenario_items': {'system', 'subsystem', 'nginx_clb', 'nginx', 'clb', 'pod',
                          'webtest_api', 'webtest_nginx_api', 'in_room'},
    'web_trigger_review': {'host', 'web_scenario_name', 'trigger_name', 'expression',
                           'priority', 'status', 'system', 'subsystem',
                           'confirmed', 'modified', 'status_verification', 'in_room',
                           'sync_status', 'change_type'},
}

def _sanitize_import_columns(table_name, columns):
    """防止 SQL 注入：仅允许白名单内的列名"""
    allowed = _ALLOWED_IMPORT_COLUMNS.get(table_name, set())
    invalid = [c for c in columns if c not in allowed]
    if invalid:
        raise ValueError(f"非法列名: {', '.join(invalid)}")
    return columns

def get_db_connection():
    """获取数据库连接（请求结束时自动关闭，防止泄漏）"""
    from flask import g
    conn = g.get('_db_conn')
    if conn is None or conn.closed:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.set_client_encoding('utf8')
        g._db_conn = conn
    return conn


import threading
from functools import wraps

_sync_lock = threading.Lock()
_sync_abort_event = threading.Event()
_sync_progress = {
    'running': False,
    'current_host': '',
    'hosts_done': 0,
    'hosts_total': 0,
    'message': '',
    'errors': []
}
_sync_progress_lock = threading.Lock()


def _with_sync_lock(f):
    """装饰器：防止并发同步/初始化操作"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not _sync_lock.acquire(blocking=False):
            return jsonify({'success': False, 'message': '另一个同步/初始化操作正在进行，请稍后再试'}), 409
        try:
            return f(*args, **kwargs)
        finally:
            _sync_lock.release()
    return wrapper

def _safe_pagination(page, per_page):
    """安全分页参数：page>=1, per_page 在 1-200 之间"""
    page = max(1, page)
    per_page = max(1, min(200, per_page))
    return page, per_page


# ---- UI 重构：技术字段翻译映射 ----
_ITEM_TYPE_MAP = {
    0: "Zabbix Agent", 1: "SNMPv1 Agent", 2: "Zabbix Trapper",
    3: "Simple Check", 4: "SNMPv2 Agent", 5: "Zabbix Internal",
    6: "SNMPv3 Agent", 7: "Zabbix Agent (Active)",
    8: "Zabbix Aggregate", 9: "Web Item", 10: "External Check",
    11: "Database Monitor", 12: "IPMI Agent", 13: "SSH Agent",
    14: "TELNET Agent", 15: "Calculated", 16: "JMX Agent",
    17: "SNMP Trap", 18: "Dependent Item", 19: "HTTP Agent",
    20: "Prometheus", 21: "Script Item",
}
_VALUE_TYPE_MAP = {0: "Numeric (Float)", 1: "Character", 2: "Log", 3: "Numeric (Unsigned)", 4: "Text"}
_ITEM_TYPE_COLOR = {0: "primary", 3: "info", 5: "secondary", 7: "primary", 11: "warning", 18: "dark", 19: "success"}

def _translate_item_type(type_val):
    return _ITEM_TYPE_MAP.get(int(type_val) if type_val is not None else -1, f"Unknown ({type_val})")

def _translate_value_type(valuetype_val):
    return _VALUE_TYPE_MAP.get(int(valuetype_val) if valuetype_val is not None else -1, f"Unknown ({valuetype_val})")

def _type_badge_color(type_val):
    return _ITEM_TYPE_COLOR.get(int(type_val) if type_val is not None else -1, "secondary")

# ---- UI 重构：基线分类 ----
_BASELINE_MANDATORY_PREFIXES = [
    "system.cpu.", "vm.memory.", "vfs.fs.", "vfs.dev.",
    "agent.ping", "kernel.", "system.swap.", "system.boottime",
    "system.hostname", "system.localtime", "system.uname",
    "system.uptime", "system.hw.",
]
_BASELINE_HARDWARE_PREFIXES = ["sensor.", "fan.", "power.", "psu."]
_BASELINE_MIDDLEWARE_PREFIXES = [
    "proc.num.", "proc.mem.", "net.tcp.service[", "net.tcp.port",
    "net.udp.port", "net.tcp.listen", "net.tcp.conn",
]

def _classify_baseline(item_key):
    if not item_key:
        return "业务指标"
    key_lower = item_key.lower()
    if any(key_lower.startswith(p) for p in _BASELINE_MANDATORY_PREFIXES):
        return "必选基线"
    if any(key_lower.startswith(p) for p in _BASELINE_HARDWARE_PREFIXES):
        return "硬件外设"
    if any(key_lower.startswith(p) for p in _BASELINE_MIDDLEWARE_PREFIXES):
        return "中间件/服务"
    return "业务指标"

_BASELINE_CSS = {"必选基线": "bb-mandatory", "硬件外设": "bb-hardware", "中间件/服务": "bb-middleware", "业务指标": "bb-business"}
def _baseline_css_class(item_key):
    return _BASELINE_CSS.get(_classify_baseline(item_key), "bb-business")

_TRIGGER_PRIORITY_MAP = {0: ("未分类", "secondary"), 1: ("信息", "info"), 2: ("警告", "warning"), 3: ("一般", "warning"), 4: ("严重", "danger"), 5: ("灾难", "danger")}
def _trigger_priority_info(priority_val):
    if priority_val is None:
        return ("未知", "secondary")
    return _TRIGGER_PRIORITY_MAP.get(int(priority_val), (f"未知({priority_val})", "secondary"))

# 注册 Jinja2 模板全局函数
app.jinja_env.globals['translate_item_type'] = _translate_item_type
app.jinja_env.globals['translate_value_type'] = _translate_value_type
app.jinja_env.globals['type_badge_color'] = _type_badge_color
app.jinja_env.globals['classify_baseline'] = _classify_baseline
app.jinja_env.globals['baseline_css_class'] = _baseline_css_class
app.jinja_env.globals['trigger_priority_info'] = _trigger_priority_info

def _safe_sql_value(v):
    """Convert Python objects to psycopg2-adaptable types.
    JSONB columns parsed by DictCursor return Python dicts, which
    psycopg2 can't natively adapt. Convert to JSON string."""
    if isinstance(v, dict):
        import json
        return json.dumps(v, ensure_ascii=False)
    if isinstance(v, list):
        import json
        return json.dumps(v, ensure_ascii=False)
    return v

def _diff_and_merge(
    cur: psycopg2.extensions.cursor,
    table_name: str,
    unique_keys: list,
    content_columns: list,
    new_rows: list,
    existing_rows: list,
    all_insert_cols: list,
) -> dict:
    """基于 Diff 算法的复核表增量合并

    在单个事务中处理三件事：
      1. INSERT 上游存在但复核表不存在的新记录（change_type='new'）
      2. UPDATE 内容已变化且 sync_status='synced' 的记录为 pending_confirm（change_type='update'）
      3. UPDATE sync_status='synced' 但上游已不存在的记录为 pending_delete（change_type='delete'）

    Args:
        cur: 数据库游标
        table_name: 复核表名
        unique_keys: 唯一键列名列表（用于比对主键，如 ['item_id', 'host_ip']）
        content_columns: 内容比对列名列表（用于检测是否变更）
        new_rows: dict 列表，上游查询的最新数据
        existing_rows: DictRow 列表，复核表现有数据
        all_insert_cols: 需要 INSERT/UPDATE 的所有列名（含唯一键、内容列、系统字段等）

    Returns: dict {new: N, update: N, delete: N, unchanged: N}
    """
    # 构建现有记录索引 {(uk1, uk2): row}
    existing_by_key = {}
    for row in existing_rows:
        key = tuple(str(row.get(k, '')) for k in unique_keys)
        existing_by_key[key] = row

    new_keys = set()
    inserts = []   # (row_dict) – 全新
    updates = []   # (existing_id, row_dict) – 内容变更
    unchanged_synced = 0
    unchanged_pending = 0

    for src in new_rows:
        key = tuple(str(src.get(k, '')) for k in unique_keys)
        new_keys.add(key)

        if key not in existing_by_key:
            inserts.append(src)
        else:
            existing = existing_by_key[key]
            # 比较内容列是否变化
            changed = any(
                str(src.get(col, '')) != str(existing.get(col, ''))
                for col in content_columns
            )
            if changed and existing.get('sync_status') == 'synced':
                updates.append((existing['id'], src))
            elif changed:
                # 未 synced 的记录内容变了，也要更新内容但不改变状态
                updates.append((existing['id'], src))
            elif existing.get('sync_status') == 'synced':
                unchanged_synced += 1
            else:
                unchanged_pending += 1

    # 检测删除：现有记录在上游不存在
    deletions = []
    for key, row in existing_by_key.items():
        if key not in new_keys and row.get('sync_status') == 'synced' and not row.get('confirmed', False):
            deletions.append(row['id'])

    # --- 批量执行 ---
    col_list = ", ".join(all_insert_cols)
    placeholders = ", ".join(f"%s" for _ in all_insert_cols)
    conflict_cols = ", ".join(unique_keys)

    # 1. INSERT new
    if inserts:
        insert_values = []
        for src in inserts:
            vals = [_safe_sql_value(src.get(c)) for c in all_insert_cols]
            vals += ['pending_confirm', 'new']
            insert_values.append(vals)
        icols = col_list + ", sync_status, change_type"
        iplaceholders = placeholders + ", %s, %s"
        from psycopg2.extras import execute_values
        execute_values(cur,
            f"INSERT INTO {table_name} ({icols}) VALUES %s ON CONFLICT ({conflict_cols}) DO NOTHING",
            insert_values, page_size=100)

    # 2. UPDATE changed
    if updates:
        for existing_id, src in updates:
            set_parts = ", ".join(
                f"{c} = %s" for c in all_insert_cols
            )
            vals = [_safe_sql_value(src.get(c)) for c in all_insert_cols]
            cur.execute(f"""
                UPDATE {table_name}
                SET {set_parts},
                    sync_status = 'pending_confirm',
                    change_type = 'update',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, vals + [existing_id])

    # 3. UPDATE deletions
    if deletions:
        for del_id in deletions:
            cur.execute(f"""
                UPDATE {table_name}
                SET sync_status = 'pending_delete',
                    change_type = 'delete',
                    confirmed = false,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s AND sync_status = 'synced'
            """, (del_id,))

    return {
        'new': len(inserts),
        'update': len(updates),
        'delete': len(deletions),
        'unchanged': unchanged_synced + unchanged_pending
    }


@app.context_processor
def inject_globals():
    """为所有模板注入全局变量"""
    return {'csrf_token': _generate_csrf_token()}


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
        'webscenarios_review': 'webscenarios_review',
        'edit_webscenario_review': 'webscenarios_review',
        'web_triggers_review': 'web_triggers_review',
        'edit_web_trigger_review': 'web_triggers_review',
        'hosts': 'hosts',
        'add_host': 'hosts',
        'edit_host': 'hosts',
        'discovery_rules': 'discovery_rules',
        'edit_discovery_rule': 'discovery_rules',
        'filter_conditions': 'filter_conditions',
        'edit_filter_condition': 'filter_conditions',
        'webscenarios': 'webscenarios',
        'add_webscenario': 'webscenarios',
        'edit_webscenario': 'webscenarios',
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
        'webscenarios_review': [('复核表管理', None), ('Web场景复核', url_for('webscenarios_review'))],
        'edit_webscenario_review': [('复核表管理', None), ('Web场景复核', url_for('webscenarios_review')), ('编辑复核记录', None)],
        'web_triggers_review': [('复核表管理', None), ('Web触发器复核', url_for('web_triggers_review'))],
        'edit_web_trigger_review': [('复核表管理', None), ('Web触发器复核', url_for('web_triggers_review')), ('编辑复核记录', None)],
        'hosts': [('主机管理', url_for('hosts'))],
        'add_host': [('主机管理', url_for('hosts')), ('添加主机', None)],
        'edit_host': [('主机管理', url_for('hosts')), ('编辑主机', None)],
        'discovery_rules': [('预定义模版管理', None), ('自动发现规则列表', url_for('discovery_rules'))],
        'edit_discovery_rule': [('预定义模版管理', None), ('自动发现规则列表', url_for('discovery_rules')), ('编辑规则', None)],
        'filter_conditions': [('预定义模版管理', None), ('自动发现过滤规则管理', url_for('filter_conditions'))],
        'edit_filter_condition': [('预定义模版管理', None), ('自动发现过滤规则管理', url_for('filter_conditions')), ('编辑过滤条件', None)],
        'webscenarios': [('预定义模版管理', None), ('Web场景管理', url_for('webscenarios'))],
        'add_webscenario': [('预定义模版管理', None), ('Web场景管理', url_for('webscenarios')), ('添加Web场景', None)],
        'edit_webscenario': [('预定义模版管理', None), ('Web场景管理', url_for('webscenarios')), ('编辑Web场景', None)],
    }
    return {'page_breadcrumb': breadcrumb_map.get(endpoint, [])}


@app.context_processor
def inject_zabbix_environments():
    """为所有模板注入 Zabbix 环境列表（用于环境下拉框动态渲染）"""
    return {'zabbix_environments': _config.get('zabbix_environments', [])}


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


@app.route('/api/review/pending-counts')
def api_review_pending_counts():
    """返回各复核表的未确认记录数（用于侧边栏待办 Badge）"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM items_review WHERE confirmed = false")
            items = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM triggers_review WHERE confirmed = false")
            triggers = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM webscenario_items_review WHERE confirmed = false")
            web = cur.fetchone()[0]
        conn.close()
        return jsonify({'success': True, 'data': {'items': items, 'triggers': triggers, 'web': web}})
    except Exception as e:
        app.logger.error(f"待办计数查询失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/review/dashboard-stats')
def api_review_dashboard_stats():
    """返回复核仪表盘统计数据"""
    table = request.args.get('table', 'items_review').strip()
    allowed_tables = {'items_review', 'triggers_review', 'webscenario_items_review', 'web_trigger_review', 'item_prototypes_review', 'trigger_prototypes_review'}
    if table not in allowed_tables:
        return jsonify({'success': False, 'message': f'不支持的表: {table}'}), 400
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(f"SELECT COUNT(*) AS total, COALESCE(SUM(CASE WHEN confirmed = true THEN 1 ELSE 0 END), 0) AS confirmed FROM {table}")
            row = cur.fetchone()
            total = row['total']
            confirmed = row['confirmed']
            pending = total - confirmed
            cur.execute(f"SELECT sync_status, COUNT(*) AS cnt FROM {table} GROUP BY sync_status")
            sync_rows = cur.fetchall()
            synced = pending_sync = pending_delete = 0
            for r in sync_rows:
                s = r['sync_status']
                if s == 'synced': synced = r['cnt']
                elif s == 'pending_delete': pending_delete = r['cnt']
                else: pending_sync += r['cnt']
            triggers_total = 0
            triggers_by_priority = {}
            if table == 'items_review':
                cur.execute("SELECT COUNT(*) AS total FROM triggers_review")
                triggers_total = cur.fetchone()['total']
                cur.execute("SELECT priority, COUNT(*) AS cnt FROM triggers_review GROUP BY priority")
                for r in cur.fetchall():
                    prio = r['priority'] if r['priority'] is not None else 0
                    triggers_by_priority[str(prio)] = r['cnt']
        conn.close()
        return jsonify({'success': True, 'data': {
            'total': total, 'confirmed': confirmed, 'pending': pending,
            'completion_pct': round(confirmed / total * 100, 1) if total > 0 else 0,
            'synced': synced, 'pending_sync': pending_sync, 'pending_delete': pending_delete,
            'triggers_total': triggers_total, 'triggers_by_priority': triggers_by_priority,
        }})
    except Exception as e:
        app.logger.error(f"仪表盘统计查询失败: {e}")
        try: conn.close()
        except Exception: pass
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/review/item-triggers')
def api_item_triggers():
    """返回与指定 host_ip + template_name 关联的触发器复核记录"""
    host_ip = request.args.get('host_ip', '').strip()
    template_name = request.args.get('template_name', '').strip()
    if not host_ip or not template_name:
        return jsonify({'success': False, 'message': '缺少 host_ip 或 template_name 参数'}), 400
    conn = get_db_connection()
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute("SELECT * FROM triggers_review WHERE host_ip = %s AND template_name = %s ORDER BY id",
                    (host_ip, template_name))
        trigger_list = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify({'success': True, 'triggers': trigger_list})


@app.route('/api/review/verify', methods=['POST'])
def api_review_verify():
    """统一核验端点：按选中 ID 去远程 Zabbix 逐条审计存在性。

    接受 JSON: {action_type, ids, environment}
    返回: {success, status, message, verified, not_found, failed_ids, errors}
    """
    data = request.get_json()
    ids = data.get('ids', []) if data else []
    action_type = data.get('action_type', '').strip() if data else ''
    environment = data.get('environment', '').strip() if data else ''

    if not action_type or not ids or environment not in ZABBIX_ENVIRONMENTS:
        return jsonify({'success': False, 'message': '参数无效'}), 400

    try:
        table = _resolve_table(action_type=action_type)
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400

    env_config = ZABBIX_ENVIRONMENTS[environment]
    if not env_config.get('url'):
        return jsonify({'success': False, 'message': f'环境 "{environment}" 未配置 URL'}), 500

    from zabbix_mac import ZabbixClient, ZabbixAPIException
    client = ZabbixClient(env_config['url'], env_config['username'], env_config['password'])
    if not getattr(client, 'api', None):
        return jsonify({'success': False, 'message': f'无法连接 {environment}'}), 500

    # Table → (host_col, key_col, zabbix_api_method)
    table_meta = {
        'items_review': ('host_ip', 'item_key', 'item'),
        'triggers_review': ('host_ip', 'name', 'trigger'),
        'item_prototypes_review': ('host_ip', 'key', 'itemprototype'),
        'trigger_prototypes_review': ('host_ip', 'description', 'triggerprototype'),
        'webscenario_items_review': ('host', 'name', 'httptest'),
        'web_trigger_review': ('host', 'trigger_name', 'trigger'),
    }
    meta = table_meta.get(table)
    if not meta:
        return jsonify({'success': False, 'message': f'不支持的表: {table}'}), 400

    host_col, key_col, ztype = meta

    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            placeholders = ','.join(['%s'] * len(ids))
            cur.execute(f"SELECT * FROM {table} WHERE id IN ({placeholders})", ids)
            rows = cur.fetchall()

        if not rows:
            return jsonify({'success': False, 'message': '未找到匹配的记录'}), 404

        verified = 0
        not_found = 0
        failed_ids = []
        errors = []

        for row in rows:
            rid = row['id']
            host_name = row[host_col]
            key_val = row.get(key_col, '')

            if not key_val:
                not_found += 1
                failed_ids.append(rid)
                continue

            try:
                host_id = client.get_host_id(host_name)
                if not host_id:
                    not_found += 1
                    failed_ids.append(rid)
                    continue

                # Remote Zabbix audit — per-item existence check
                found = False
                if ztype == 'item':
                    result = client.api.item.get(
                        hostids=[host_id], output=['itemid'],
                        search={'key_': key_val})
                    found = bool(result)
                elif ztype == 'trigger':
                    result = client.api.trigger.get(
                        hostids=[host_id], output=['triggerid'],
                        search={'description': key_val})
                    found = bool(result)
                elif ztype == 'itemprototype':
                    result = client.api.itemprototype.get(
                        hostids=[host_id], output=['itemid'],
                        search={'key_': key_val})
                    found = bool(result)
                elif ztype == 'triggerprototype':
                    result = client.api.triggerprototype.get(
                        hostids=[host_id], output=['triggerid'],
                        search={'description': key_val})
                    found = bool(result)
                elif ztype == 'httptest':
                    result = client.api.httptest.get(
                        hostids=[host_id], output=['httptestid'],
                        search={'name': key_val})
                    found = bool(result)

                status = 'verified' if found else 'not_found'
                with conn.cursor() as cur:
                    cur.execute(
                        f"UPDATE {table} SET status_verification = %s WHERE id = %s",
                        (status, rid))

                if found:
                    verified += 1
                else:
                    not_found += 1
                    failed_ids.append(rid)

            except ZabbixAPIException as e:
                errors.append(f'{host_name}/{key_val}: {e}')
                app.logger.error(f"核验 {ztype} {key_val} 失败: {e}")
            except Exception as e:
                errors.append(f'{host_name}/{key_val}: {e}')

        conn.commit()

        msg = f'核验完成：{verified} 条已确认'
        if not_found > 0:
            msg += f'，{not_found} 条在 Zabbix 中未找到，请重新进行监控同步！'

        resp_status = 'warning' if not_found > 0 else 'success'
        return jsonify({
            'success': True,
            'status': resp_status,
            'message': msg,
            'verified': verified,
            'not_found': not_found,
            'failed_ids': failed_ids,
            'errors': errors[:10] if errors else None,
        })
    except Exception as e:
        app.logger.error(f"核验失败: {e}")
        return jsonify({'success': False, 'message': f'核验失败: {str(e)}'}), 500
    finally:
        conn.close()


@app.route('/system-info')
def system_info():
    """系统信息详情页面 — 实时采集运行环境、组件连通性与资产统计"""
    # ---- 运行环境数据 ----
    sys_info = {
        'version': app.config.get('APP_VERSION', 'v1.2.5'),
        'python_version': sys.version.split()[0],
        'os_version': f"{platform.system()} {platform.release()} ({platform.version() or 'N/A'})",
        'uptime': _format_uptime(),
        'deploy_mode': 'Docker Container (K8s)' if os.path.exists('/.dockerenv') else 'Standalone (systemd)',
    }

    # ---- Zabbix API 连通性检测 ----
    zabbix_connected = False
    zabbix_version = 'N/A'
    zabbix_latency = 0
    zabbix_url_display = 'N/A'

    for env_name, env_cfg in ZABBIX_ENVIRONMENTS.items():
        if env_cfg.get('url'):
            zabbix_url_display = env_cfg['url']
            try:
                from zabbix_mac import ZabbixAPI
                t0 = time.time()
                api = ZabbixAPI(env_cfg['url'])
                ver = api.api_version()
                latency = int((time.time() - t0) * 1000)
                zabbix_connected = True
                zabbix_version = ver
                zabbix_latency = latency
                app.logger.info(f"Zabbix API ({env_name}) 连通正常: version={ver}, latency={latency}ms")
            except Exception as e:
                app.logger.warning(f"Zabbix API ({env_name}) 连通检测失败: {e}")
            break  # 只检测第一个已配置的环境

    sys_info['zabbix_connected'] = zabbix_connected
    sys_info['zabbix_version'] = zabbix_version
    sys_info['zabbix_latency'] = zabbix_latency
    sys_info['zabbix_url'] = zabbix_url_display

    # ---- 数据库连通性与资产统计 ----
    db_online = False
    stats = {'hosts': 0, 'items': 0, 'triggers': 0, 'web_scenarios': 0}

    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM hosts")
            stats['hosts'] = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM items_review")
            stats['items'] = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM triggers_review")
            stats['triggers'] = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM webscenario_items_review")
            stats['web_scenarios'] = cur.fetchone()[0]
        conn.close()
        db_online = True
    except Exception as e:
        app.logger.error(f"系统信息页 DB 统计查询失败: {e}")

    sys_info['db_online'] = db_online
    sys_info['last_check_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    return render_template('system_info.html', sys_info=sys_info, stats=stats)

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
    template = request.args.get('template', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    page, per_page = _safe_pagination(page, per_page)
    offset = (page - 1) * per_page

    conn = get_db_connection()
    with conn.cursor(cursor_factory=DictCursor) as cur:
        where_clause = ""
        where_join = ""
        params = []
        if template:
            where_clause = " WHERE dr.template_name ILIKE %s"
            where_join = " AND dr.template_name ILIKE %s"
            params.append(f'%{template}%')
        cur.execute(f"SELECT COUNT(*) FROM item_prototypes ip JOIN discovery_rules dr ON ip.discovery_rule_id = dr.id{where_clause}", params)
        total = cur.fetchone()['count']
        cur.execute(f"""
            SELECT ip.*, dr.name as rule_name, dr.template_name
            FROM item_prototypes ip
            JOIN discovery_rules dr ON ip.discovery_rule_id = dr.id
            {where_join}
            ORDER BY ip.id LIMIT %s OFFSET %s
        """, params + [per_page, offset])
        prototypes = cur.fetchall()
    conn.close()

    total_pages = (total + per_page - 1) // per_page
    return render_template('item_prototypes.html', prototypes=prototypes,
                           page=page, per_page=per_page,
                           total=total, total_pages=total_pages)


@app.route('/item-prototypes/export')
def export_item_prototypes():
    """导出 item_prototypes 表到 Excel"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM item_prototypes ORDER BY id")
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
        df = pd.DataFrame(rows, columns=columns)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='item_prototypes')
        output.seek(0)
        return send_file(output, download_name='item_prototypes.xlsx',
                         mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                         as_attachment=True)
    except Exception as e:
        return jsonify({'success': False, 'message': f'导出失败: {str(e)}'}), 500
    finally:
        conn.close()


@app.route('/item-prototypes/import', methods=['POST'])
def import_item_prototypes():
    """从 Excel 导入数据到 item_prototypes 表（清空后写入）"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '未选择文件'}), 400
    file = request.files['file']
    if not file.filename:
        return jsonify({'success': False, 'message': '文件名为空'}), 400
    conn = get_db_connection()
    try:
        df = pd.read_excel(file, engine='openpyxl')
        with conn.cursor() as cur:
            cur.execute("DELETE FROM item_prototypes")
            deleted = cur.rowcount
            columns = _sanitize_import_columns('item_prototypes', list(df.columns))
            placeholders = ', '.join(['%s'] * len(columns))
            column_names = ', '.join(columns)
            all_values = []
            for _, row in df.iterrows():
                values = []
                for col in columns:
                    val = row[col]
                    if pd.isna(val):
                        values.append(None)
                    elif isinstance(val, str) and (val.startswith('{') or val.startswith('[')):
                        try:
                            values.append(json.dumps(ast.literal_eval(val)))
                        except (ValueError, SyntaxError):
                            values.append(val)
                    else:
                        values.append(val)
                all_values.append(values)
            cur.executemany(f"INSERT INTO item_prototypes ({column_names}) VALUES ({placeholders})", all_values)
            inserted = len(all_values)
        conn.commit()
        return jsonify({'success': True, 'message': f'item_prototypes 导入成功：删除 {deleted} 条，导入 {inserted} 条'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': f'导入失败: {str(e)}'}), 500
    finally:
        conn.close()


@app.route('/webscenarios')
def webscenarios():
    """Web场景管理"""
    system = request.args.get('system', '').strip()
    subsystem = request.args.get('subsystem', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    page, per_page = _safe_pagination(page, per_page)
    offset = (page - 1) * per_page

    conn = get_db_connection()
    with conn.cursor(cursor_factory=DictCursor) as cur:
        where_clause = ""
        params = []
        conditions = []
        if system:
            conditions.append("system ILIKE %s")
            params.append(f'%{system}%')
        if subsystem:
            conditions.append("subsystem ILIKE %s")
            params.append(f'%{subsystem}%')
        if conditions:
            where_clause = " WHERE " + " AND ".join(conditions)
        cur.execute(f"SELECT COUNT(*) FROM webscenario_items{where_clause}", params)
        total = cur.fetchone()['count']
        cur.execute(f"SELECT * FROM webscenario_items{where_clause} ORDER BY id LIMIT %s OFFSET %s", params + [per_page, offset])
        webscenarios = cur.fetchall()
    conn.close()

    total_pages = (total + per_page - 1) // per_page
    app.logger.info(f"Web场景管理: 查询到 {total} 条记录 (page={page}, per_page={per_page})")
    return render_template('webscenarios.html', webscenarios=webscenarios,
                           page=page, per_page=per_page,
                           total=total, total_pages=total_pages)


@app.route('/webscenarios/seed', methods=['POST'])
def seed_webscenarios():
    """初始化测试数据到 webscenario_items 表"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO webscenario_items (system, subsystem, nginx_clb, nginx, clb, pod, webtest_api, webtest_nginx_api, in_room)
                VALUES
                ('Seeded System 1', 'Seeded Sub 1', '10.0.1.1:8080', '10.0.1.2:8080', '10.0.1.3:8080', '10.0.1.4:8080', '/api/health', '/nginx/api/health', 'Seed Room A'),
                ('Seeded System 2', 'Seeded Sub 2', '10.0.2.1:8080', '10.0.2.2:8080', '10.0.2.3:8080', '10.0.2.4:8080', '/api/status', '/nginx/api/status', 'Seed Room B')
            """)
        conn.commit()
        app.logger.info("Web场景管理: 已插入 2 条测试数据")
        return jsonify({'success': True, 'message': '已插入 2 条测试数据'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@app.route('/webscenarios/export')
def export_webscenarios():
    """导出 webscenario_items 表到 Excel"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM webscenario_items ORDER BY id")
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
        df = pd.DataFrame(rows, columns=columns)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='webscenario_items')
        output.seek(0)
        return send_file(output, download_name='webscenario_items.xlsx',
                         mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                         as_attachment=True)
    except Exception as e:
        return jsonify({'success': False, 'message': f'导出失败: {str(e)}'}), 500
    finally:
        conn.close()


@app.route('/webscenarios/import', methods=['POST'])
def import_webscenarios():
    """从 Excel 导入数据到 webscenario_items 表（清空后写入）"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '未选择文件'}), 400
    file = request.files['file']
    if not file.filename:
        return jsonify({'success': False, 'message': '文件名为空'}), 400
    conn = get_db_connection()
    try:
        df = pd.read_excel(file, engine='openpyxl')
        with conn.cursor() as cur:
            cur.execute("DELETE FROM webscenario_items")
            deleted = cur.rowcount
            columns = _sanitize_import_columns('webscenario_items', list(df.columns))
            placeholders = ', '.join(['%s'] * len(columns))
            column_names = ', '.join(columns)
            all_values = []
            for _, row in df.iterrows():
                values = []
                for col in columns:
                    val = row[col]
                    if pd.isna(val):
                        values.append(None)
                    elif isinstance(val, str) and (val.startswith('{') or val.startswith('[')):
                        try:
                            values.append(json.dumps(ast.literal_eval(val)))
                        except (ValueError, SyntaxError):
                            values.append(val)
                    else:
                        values.append(val)
                all_values.append(values)
            cur.executemany(f"INSERT INTO webscenario_items ({column_names}) VALUES ({placeholders})", all_values)
            inserted = len(all_values)
        conn.commit()
        return jsonify({'success': True, 'message': f'webscenario_items 导入成功：删除 {deleted} 条，导入 {inserted} 条'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': f'导入失败: {str(e)}'}), 500
    finally:
        conn.close()


@app.route('/webscenario/add', methods=['GET', 'POST'])
def add_webscenario():
    """添加Web场景"""
    conn = get_db_connection()

    if request.method == 'POST':
        system = request.form.get('system', '')
        subsystem = request.form.get('subsystem', '')
        nginx_clb = request.form.get('nginx_clb') or None
        nginx = request.form.get('nginx') or None
        clb = request.form.get('clb') or None
        pod = request.form.get('pod') or None
        webtest_api = request.form['webtest_api']
        webtest_nginx_api = request.form['webtest_nginx_api']
        in_room = request.form.get('in_room') or None

        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO webscenario_items (system, subsystem, nginx_clb, nginx, clb, pod,
                                                    webtest_api, webtest_nginx_api, in_room)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (system, subsystem, nginx_clb, nginx, clb, pod,
                      webtest_api, webtest_nginx_api, in_room))
            conn.commit()
            flash('Web场景添加成功')
            return redirect(url_for('webscenarios'))
        except Exception as e:
            conn.rollback()
            flash(f'添加失败: {e}')

    conn.close()
    return render_template('add_webscenario.html')


@app.route('/webscenario/edit/<int:ws_id>', methods=['GET', 'POST'])
def edit_webscenario(ws_id):
    """编辑Web场景"""
    conn = get_db_connection()
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute("SELECT * FROM webscenario_items WHERE id = %s", (ws_id,))
        ws = cur.fetchone()

    if not ws:
        flash('Web场景不存在')
        return redirect(url_for('webscenarios'))

    if request.method == 'POST':
        system = request.form.get('system', '')
        subsystem = request.form.get('subsystem', '')
        nginx_clb = request.form.get('nginx_clb') or None
        nginx = request.form.get('nginx') or None
        clb = request.form.get('clb') or None
        pod = request.form.get('pod') or None
        webtest_api = request.form['webtest_api']
        webtest_nginx_api = request.form['webtest_nginx_api']
        in_room = request.form.get('in_room') or None

        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE webscenario_items SET system=%s, subsystem=%s,
                        nginx_clb=%s, nginx=%s, clb=%s, pod=%s,
                        webtest_api=%s, webtest_nginx_api=%s, in_room=%s,
                        updated_at=CURRENT_TIMESTAMP
                    WHERE id=%s
                """, (system, subsystem, nginx_clb, nginx, clb, pod,
                      webtest_api, webtest_nginx_api, in_room, ws_id))
            conn.commit()
            flash('Web场景更新成功')
            return redirect(url_for('webscenarios'))
        except Exception as e:
            conn.rollback()
            flash(f'更新失败: {e}')

    conn.close()
    return render_template('edit_webscenario.html', ws=ws)


@app.route('/webscenario/delete/<int:ws_id>')
def delete_webscenario(ws_id):
    """删除Web场景"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM webscenario_items WHERE id = %s", (ws_id,))
        conn.commit()
        flash('Web场景删除成功')
    except Exception as e:
        conn.rollback()
        flash(f'删除失败: {e}')
    conn.close()
    return redirect(url_for('webscenarios'))


@app.route('/trigger-prototypes')
def trigger_prototypes():
    """触发器原型管理"""
    template = request.args.get('template', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    page, per_page = _safe_pagination(page, per_page)
    offset = (page - 1) * per_page

    conn = get_db_connection()
    with conn.cursor(cursor_factory=DictCursor) as cur:
        where_clause = ""
        where_join = ""
        params = []
        if template:
            where_clause = " WHERE dr.template_name ILIKE %s"
            where_join = " AND dr.template_name ILIKE %s"
            params.append(f'%{template}%')
        cur.execute(f"SELECT COUNT(*) FROM trigger_prototypes tp JOIN discovery_rules dr ON tp.discovery_rule_id = dr.id{where_clause}", params)
        total = cur.fetchone()['count']
        cur.execute(f"""
            SELECT tp.*, dr.name as rule_name, dr.template_name
            FROM trigger_prototypes tp
            JOIN discovery_rules dr ON tp.discovery_rule_id = dr.id
            {where_join}
            ORDER BY tp.id LIMIT %s OFFSET %s
        """, params + [per_page, offset])
        prototypes = cur.fetchall()
    conn.close()

    total_pages = (total + per_page - 1) // per_page
    return render_template('trigger_prototypes.html', prototypes=prototypes,
                           page=page, per_page=per_page,
                           total=total, total_pages=total_pages)


@app.route('/trigger-prototypes/export')
def export_trigger_prototypes():
    """导出 trigger_prototypes 表到 Excel"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM trigger_prototypes ORDER BY id")
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
        df = pd.DataFrame(rows, columns=columns)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='trigger_prototypes')
        output.seek(0)
        return send_file(output, download_name='trigger_prototypes.xlsx',
                         mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                         as_attachment=True)
    except Exception as e:
        return jsonify({'success': False, 'message': f'导出失败: {str(e)}'}), 500
    finally:
        conn.close()


@app.route('/trigger-prototypes/import', methods=['POST'])
def import_trigger_prototypes():
    """从 Excel 导入数据到 trigger_prototypes 表（清空后写入）"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '未选择文件'}), 400
    file = request.files['file']
    if not file.filename:
        return jsonify({'success': False, 'message': '文件名为空'}), 400
    conn = get_db_connection()
    try:
        df = pd.read_excel(file, engine='openpyxl')
        with conn.cursor() as cur:
            cur.execute("DELETE FROM trigger_prototypes")
            deleted = cur.rowcount
            columns = _sanitize_import_columns('trigger_prototypes', list(df.columns))
            placeholders = ', '.join(['%s'] * len(columns))
            column_names = ', '.join(columns)
            all_values = []
            for _, row in df.iterrows():
                values = []
                for col in columns:
                    val = row[col]
                    if pd.isna(val):
                        values.append(None)
                    elif isinstance(val, str) and (val.startswith('{') or val.startswith('[')):
                        try:
                            values.append(json.dumps(ast.literal_eval(val)))
                        except (ValueError, SyntaxError):
                            values.append(val)
                    else:
                        values.append(val)
                all_values.append(values)
            cur.executemany(f"INSERT INTO trigger_prototypes ({column_names}) VALUES ({placeholders})", all_values)
            inserted = len(all_values)
        conn.commit()
        return jsonify({'success': True, 'message': f'trigger_prototypes 导入成功：删除 {deleted} 条，导入 {inserted} 条'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': f'导入失败: {str(e)}'}), 500
    finally:
        conn.close()


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
    template = request.args.get('template', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    page, per_page = _safe_pagination(page, per_page)
    offset = (page - 1) * per_page

    conn = get_db_connection()
    with conn.cursor(cursor_factory=DictCursor) as cur:
        where_clause = ""
        params = []
        if template:
            where_clause = " WHERE template_name ILIKE %s"
            params.append(f'%{template}%')
        cur.execute(f"SELECT COUNT(*) FROM items{where_clause}", params)
        total = cur.fetchone()['count']
        cur.execute(f"SELECT * FROM items{where_clause} ORDER BY id LIMIT %s OFFSET %s", params + [per_page, offset])
        items = cur.fetchall()
    conn.close()

    total_pages = (total + per_page - 1) // per_page
    return render_template('items.html', items=items, page=page, per_page=per_page,
                           total=total, total_pages=total_pages)


@app.route('/items/export')
def export_items():
    """导出 items 表到 Excel"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM items ORDER BY id")
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
        df = pd.DataFrame(rows, columns=columns)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='items')
        output.seek(0)
        return send_file(output, download_name='items.xlsx',
                         mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                         as_attachment=True)
    except Exception as e:
        return jsonify({'success': False, 'message': f'导出失败: {str(e)}'}), 500
    finally:
        conn.close()


@app.route('/items/import', methods=['POST'])
def import_items():
    """从 Excel 导入数据到 items 表（清空后写入）"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '未选择文件'}), 400
    file = request.files['file']
    if not file.filename:
        return jsonify({'success': False, 'message': '文件名为空'}), 400
    conn = get_db_connection()
    try:
        df = pd.read_excel(file, engine='openpyxl')
        with conn.cursor() as cur:
            cur.execute("DELETE FROM items")
            deleted = cur.rowcount
            columns = _sanitize_import_columns('items', list(df.columns))
            placeholders = ', '.join(['%s'] * len(columns))
            column_names = ', '.join(columns)
            all_values = []
            for _, row in df.iterrows():
                values = []
                for col in columns:
                    val = row[col]
                    if pd.isna(val):
                        values.append(None)
                    elif isinstance(val, str) and (val.startswith('{') or val.startswith('[')):
                        try:
                            values.append(json.dumps(ast.literal_eval(val)))
                        except (ValueError, SyntaxError):
                            values.append(val)
                    else:
                        values.append(val)
                all_values.append(values)
            cur.executemany(f"INSERT INTO items ({column_names}) VALUES ({placeholders})", all_values)
            inserted = len(all_values)
        conn.commit()
        return jsonify({'success': True, 'message': f'items 导入成功：删除 {deleted} 条，导入 {inserted} 条'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': f'导入失败: {str(e)}'}), 500
    finally:
        conn.close()


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
        preprocessing_raw = request.form.get('preprocessing')
        if preprocessing_raw and preprocessing_raw.strip():
            try:
                preprocessing = json.loads(preprocessing_raw)
                if preprocessing == '':
                    preprocessing = None
            except json.JSONDecodeError:
                preprocessing = None
        else:
            preprocessing = None

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
        preprocessing_raw = request.form.get('preprocessing')
        if preprocessing_raw and preprocessing_raw.strip():
            try:
                preprocessing = json.loads(preprocessing_raw)
                if preprocessing == '':
                    preprocessing = None
            except json.JSONDecodeError:
                preprocessing = None
        else:
            preprocessing = None

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
    template = request.args.get('template', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    page, per_page = _safe_pagination(page, per_page)
    offset = (page - 1) * per_page

    conn = get_db_connection()
    with conn.cursor(cursor_factory=DictCursor) as cur:
        where_clause = ""
        params = []
        if template:
            where_clause = " WHERE template_name ILIKE %s"
            params.append(f'%{template}%')
        cur.execute(f"SELECT COUNT(*) FROM triggers{where_clause}", params)
        total = cur.fetchone()['count']
        cur.execute(f"SELECT * FROM triggers{where_clause} ORDER BY id LIMIT %s OFFSET %s", params + [per_page, offset])
        triggers = cur.fetchall()
    conn.close()

    total_pages = (total + per_page - 1) // per_page
    return render_template('triggers.html', triggers=triggers, page=page, per_page=per_page,
                           total=total, total_pages=total_pages)


@app.route('/triggers/export')
def export_triggers():
    """导出 triggers 表到 Excel"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM triggers ORDER BY id")
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
        df = pd.DataFrame(rows, columns=columns)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='triggers')
        output.seek(0)
        return send_file(output, download_name='triggers.xlsx',
                         mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                         as_attachment=True)
    except Exception as e:
        return jsonify({'success': False, 'message': f'导出失败: {str(e)}'}), 500
    finally:
        conn.close()


@app.route('/triggers/import', methods=['POST'])
def import_triggers():
    """从 Excel 导入数据到 triggers 表（清空后写入）"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '未选择文件'}), 400
    file = request.files['file']
    if not file.filename:
        return jsonify({'success': False, 'message': '文件名为空'}), 400
    conn = get_db_connection()
    try:
        df = pd.read_excel(file, engine='openpyxl')
        with conn.cursor() as cur:
            cur.execute("DELETE FROM triggers")
            deleted = cur.rowcount
            columns = _sanitize_import_columns('triggers', list(df.columns))
            placeholders = ', '.join(['%s'] * len(columns))
            column_names = ', '.join(columns)
            all_values = []
            for _, row in df.iterrows():
                values = []
                for col in columns:
                    val = row[col]
                    if pd.isna(val):
                        values.append(None)
                    elif isinstance(val, str) and (val.startswith('{') or val.startswith('[')):
                        try:
                            values.append(json.dumps(ast.literal_eval(val)))
                        except (ValueError, SyntaxError):
                            values.append(val)
                    else:
                        values.append(val)
                all_values.append(values)
            cur.executemany(f"INSERT INTO triggers ({column_names}) VALUES ({placeholders})", all_values)
            inserted = len(all_values)
        conn.commit()
        return jsonify({'success': True, 'message': f'triggers 导入成功：删除 {deleted} 条，导入 {inserted} 条'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': f'导入失败: {str(e)}'}), 500
    finally:
        conn.close()


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
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    page, per_page = _safe_pagination(page, per_page)
    offset = (page - 1) * per_page

    conn = get_db_connection()
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute("SELECT COUNT(*) FROM hosts")
        total = cur.fetchone()['count']
        cur.execute("SELECT * FROM hosts ORDER BY id LIMIT %s OFFSET %s", (per_page, offset))
        hosts = cur.fetchall()
    conn.close()

    total_pages = (total + per_page - 1) // per_page
    return render_template('hosts.html', hosts=hosts, page=page, per_page=per_page,
                           total=total, total_pages=total_pages)


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
                SELECT sa.system, sa.subsystem, sa.hostname, sa.ip, sa.template_id, sa.in_room
                FROM ops.sub_assets sa
                LEFT JOIN hosts h ON sa.ip = h.name
                WHERE h.id IS NULL
                   OR h.system IS DISTINCT FROM sa.system
                   OR h.subsystem IS DISTINCT FROM sa.subsystem
                   OR h.template_id IS DISTINCT FROM sa.template_id::varchar
                   OR h.in_room IS DISTINCT FROM sa.in_room
            """)
            to_sync = cur.fetchall()

            # 2. 逐条 UPSERT 到 zabbix_mac.hosts
            for row in to_sync:
                cur.execute("""
                    INSERT INTO hosts (name, system, subsystem, template_id, description, in_room)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (name)
                    DO UPDATE SET
                        system = EXCLUDED.system,
                        subsystem = EXCLUDED.subsystem,
                        template_name = EXCLUDED.template_name,
                        description = EXCLUDED.description,
                        in_room = EXCLUDED.in_room,
                        updated_at = CURRENT_TIMESTAMP
                """, (row['ip'], row['system'], row['subsystem'],
                      row['template_id'], row['hostname'], row['in_room']))
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
        template_id = request.form.get('template_id')
        description = request.form.get('description')
        system = request.form.get('system')
        subsystem = request.form.get('subsystem')
        in_room = request.form.get('in_room') or None

        conn = get_db_connection()
        try:
            # 插入主机基本信息
            with conn.cursor() as cur:
                cur.execute("INSERT INTO hosts (name, template_id, description, system, subsystem, in_room) VALUES (%s, %s, %s, %s, %s, %s)", (name, template_id, description, system, subsystem, in_room))
            
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
        template_id = request.form.get('template_id')
        description = request.form.get('description')
        system = request.form.get('system')
        subsystem = request.form.get('subsystem')
        in_room = request.form.get('in_room') or None

        try:
            # 更新主机基本信息
            with conn.cursor() as cur:
                cur.execute("UPDATE hosts SET name = %s, template_id = %s, description = %s, system = %s, subsystem = %s, in_room = %s WHERE id = %s", (name, template_id, description, system, subsystem, in_room, host_id))
            
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
    """监控项复核表管理 — 支持 ip/system/subsystem 过滤 + 分页"""
    ip = request.args.get('ip', '').strip()
    system = request.args.get('system', '').strip()
    subsystem = request.args.get('subsystem', '').strip()
    sync_filter = request.args.get('sync_filter', 'all').strip()
    baseline = request.args.get('baseline', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    page, per_page = _safe_pagination(page, per_page)
    offset = (page - 1) * per_page

    conn = get_db_connection()
    with conn.cursor(cursor_factory=DictCursor) as cur:
        where_clause = " WHERE 1=1"
        params = []
        if ip:
            where_clause += " AND host_ip ILIKE %s"
            params.append(f'%{ip}%')
        if system:
            where_clause += " AND system ILIKE %s"
            params.append(f'%{system}%')
        if subsystem:
            where_clause += " AND subsystem ILIKE %s"
            params.append(f'%{subsystem}%')
        if sync_filter == 'pending':
            where_clause += " AND (sync_status != 'synced' OR sync_status IS NULL)"

        if baseline:
            _baseline_sql_patterns = {
                '必选基线': ["system.cpu.%%", "vm.memory.%%", "vfs.fs.%%", "vfs.dev.%%", "agent.ping", "kernel.%%", "system.swap.%%", "system.boottime", "system.hostname", "system.localtime", "system.uname", "system.uptime", "system.hw.%%"],
                '硬件外设': ["sensor.%%", "fan.%%", "power.%%", "psu.%%"],
                '中间件/服务': ["proc.num.%%", "proc.mem.%%", "net.tcp.service[%%", "net.tcp.port", "net.udp.port", "net.tcp.listen%%", "net.tcp.conn%%"],
            }
            if baseline == '业务指标':
                all_exclude = []
                for pat_list in _baseline_sql_patterns.values():
                    all_exclude.extend(pat_list)
                for pattern in all_exclude:
                    where_clause += " AND item_key NOT ILIKE %s"
                    params.append(pattern)
            elif baseline in _baseline_sql_patterns:
                like_clauses = []
                for pattern in _baseline_sql_patterns[baseline]:
                    like_clauses.append("item_key ILIKE %s")
                    params.append(pattern)
                if like_clauses:
                    where_clause += " AND (" + " OR ".join(like_clauses) + ")"

        # 获取 system / subsystem 去重值供 datalist 下拉建议
        cur.execute("SELECT DISTINCT system FROM items_review WHERE system IS NOT NULL AND system != '' ORDER BY system")
        distinct_systems = [r['system'] for r in cur.fetchall()]
        cur.execute("SELECT DISTINCT subsystem FROM items_review WHERE subsystem IS NOT NULL AND subsystem != '' ORDER BY subsystem")
        distinct_subsystems = [r['subsystem'] for r in cur.fetchall()]

        # COUNT
        cur.execute(f"SELECT COUNT(*) FROM items_review{where_clause}", params)
        total = cur.fetchone()['count']

        # DATA with pagination
        cur.execute(f"SELECT * FROM items_review{where_clause} ORDER BY id LIMIT %s OFFSET %s",
                    params + [per_page, offset])
        items = cur.fetchall()

    conn.close()

    total_pages = (total + per_page - 1) // per_page
    return render_template('items_review.html', items=items,
                           distinct_systems=distinct_systems,
                           distinct_subsystems=distinct_subsystems,
                           sync_filter=sync_filter,
                           baseline=baseline,
                           page=page, per_page=per_page,
                           total=total, total_pages=total_pages)


@app.route('/items-review/initialize', methods=['POST'])
@_with_sync_lock
def initialize_items_review():
    """初始化 items_review 表：基于 Diff 算法增量更新
    （已同步记录保持不变，新增/变更/删除均通过 change_type 标记）
    支持未绑定模板的主机：自动使用 DEFAULT_TEMPLATE_NAME 兜底。"""
    data = request.get_json() if request.is_json else {}
    system_filter = data.get('system', '').strip() if data else ''
    subsystem_filter = data.get('subsystem', '').strip() if data else ''

    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            # 0. 统计主机信息（用于反馈跳过/处理数量）
            host_conditions = ["1=1"]
            host_params = []
            if system_filter:
                host_conditions.append("h.system = %s")
                host_params.append(system_filter)
            if subsystem_filter:
                host_conditions.append("h.subsystem = %s")
                host_params.append(subsystem_filter)
            host_where = " AND ".join(host_conditions)

            cur.execute(f"SELECT COUNT(*) as cnt FROM hosts h WHERE {host_where}", host_params)
            total_hosts = cur.fetchone()['cnt']

            cur.execute(
                f"SELECT COUNT(*) as cnt FROM hosts h WHERE {host_where} AND (h.template_id IS NULL OR h.template_id = '')",
                host_params
            )
            no_template_hosts = cur.fetchone()['cnt']

            cur.execute(
                f"SELECT h.name FROM hosts h WHERE {host_where} AND (h.template_id IS NULL OR h.template_id = '') ORDER BY h.name",
                host_params
            )
            skipped_host_names = [r['name'] for r in cur.fetchall()]

            # 1. 获取现有记录
            existing_conditions = ["1=1"]
            existing_params = []
            if system_filter:
                existing_conditions.append("system = %s")
                existing_params.append(system_filter)
            if subsystem_filter:
                existing_conditions.append("subsystem = %s")
                existing_params.append(subsystem_filter)
            existing_where = " AND ".join(existing_conditions)
            cur.execute(f"SELECT * FROM items_review WHERE {existing_where}", existing_params)
            existing_rows = cur.fetchall()

            # 2. 获取上游最新数据
            # 关键修复：COALESCE(NULLIF(h.template_id, ''), %s) 让未绑定模板的主机
            # 也能用 DEFAULT_TEMPLATE_NAME 匹配 items，避免初始化跳过这类主机
            default_tmpl = app.config['DEFAULT_TEMPLATE_NAME']
            where_parts = [
                "i.template_name = COALESCE(NULLIF(h.template_id, ''), %s)"
            ]
            query_params = [default_tmpl]
            if system_filter:
                where_parts.append("h.system = %s")
                query_params.append(system_filter)
            if subsystem_filter:
                where_parts.append("h.subsystem = %s")
                query_params.append(subsystem_filter)
            where_clause = " AND ".join(where_parts)

            cur.execute(f"""
                SELECT
                    i.id as item_id,
                    h.name as host_ip,
                    i.item_key, i.name, i.type, i.value_type, i.delay,
                    i.description, i.units, i.multiplier, i.delta, i.history, i.trends,
                    i.status, i.template_name, i.master_item, i.preprocessing,
                    h.system, h.subsystem, h.in_room
                FROM items i
                CROSS JOIN hosts h
                WHERE {where_clause}
                ORDER BY i.id, h.name
            """, query_params)
            new_rows = cur.fetchall()

            all_insert_cols = [
                'item_id', 'host_ip', 'item_key', 'name', 'type', 'value_type', 'delay',
                'description', 'units', 'multiplier', 'delta', 'history', 'trends',
                'status', 'template_name', 'master_item', 'preprocessing', 'system', 'subsystem', 'in_room'
            ]
            content_columns = [
                'item_key', 'name', 'type', 'value_type', 'delay', 'description', 'units',
                'multiplier', 'delta', 'history', 'trends', 'status', 'template_name',
                'master_item', 'preprocessing', 'system', 'subsystem', 'in_room'
            ]
            unique_keys = ['item_id', 'host_ip']

            result = _diff_and_merge(
                cur, 'items_review', unique_keys, content_columns,
                new_rows, existing_rows, all_insert_cols
            )
        conn.commit()

        # 构建增强响应
        processed = total_hosts - no_template_hosts
        msg = (f'items_review 表 Diff 完成：新增 {result["new"]} 条，变更 {result["update"]} 条，'
               f'标记删除 {result["delete"]} 条，无变化 {result["unchanged"]} 条')
        if no_template_hosts > 0:
            msg += f'（{no_template_hosts} 台主机未绑定模板，已用默认模板 "{default_tmpl}" 兜底）'

        return jsonify({
            'success': True,
            'message': msg,
            'data': {
                'total_hosts': total_hosts,
                'processed_hosts': processed,
                'skipped_hosts': no_template_hosts,
                'skip_reasons': {name: '主机未绑定模板，已用默认模板兜底' for name in skipped_host_names[:10]},
                'created': result['new'],
                'updated': result['update'],
                'deleted': result['delete'],
                'unchanged': result['unchanged']
            }
        })
    except Exception as e:
        conn.rollback()
        app.logger.error(f"items-review/initialize 失败: {e}", exc_info=True)
        return jsonify({'success': False, 'message': f'初始化失败: {str(e)}'}), 500
    finally:
        conn.close()


@app.route('/items-review/sync', methods=['POST'])
@_with_sync_lock
def sync_items_to_zabbix():
    """将已确认的监控项同步至指定环境机房的 Zabbix Server（含孤儿清理）"""
    data = request.get_json()
    ids = data.get('ids', []) if data else []
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

    from zabbix_mac import ZabbixClient, ZabbixAPIException

    client = ZabbixClient(env_config['url'], env_config['username'], env_config['password'])
    created = 0
    updated = 0
    deleted = 0
    errors = []

    # 按主机 IP 分组，避免对同一主机多次调用 get_managed_items()
    hosts = {}
    for row in confirmed_items:
        host_ip = row['host_ip']
        if host_ip not in hosts:
            hosts[host_ip] = []
        hosts[host_ip].append(row)

    for host_ip, rows in hosts.items():
        try:
            host_id = client.get_host_id(host_ip)
            if not host_id:
                errors.append(f'主机 {host_ip} 在 Zabbix 中不存在')
                continue

            interface_id = client.get_host_interface_id(host_id)
            if not interface_id:
                errors.append(f'主机 {host_ip} 无可用接口')
                continue

            # 一次性获取该主机所有自有监控项，构建当前状态映射
            existing_items = client.get_managed_items(host_id)
            current_items_map = {item['key_']: item for item in existing_items}

            # 构建该主机下已确认的目标监控项 key 集合
            target_keys = set()

            # 第一轮：分离独立监控项和依赖监控项（type=18 依赖项 / type=15 计算项）
            independent_rows = []
            dependent_rows = []
            for row in rows:
                item_type = int(row.get('type', 0))
                if item_type in (15, 18) and row.get('master_item'):
                    dependent_rows.append(row)
                else:
                    independent_rows.append(row)

            # 第二轮：创建/更新独立监控项（先于依赖项，确保 master 存在）
            def _build_item_data(host_id, row, interface_id):
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
                    item_data['history'] = f"{row['history']}d"
                if row.get('trends'):
                    item_data['trends'] = f"{row['trends']}d"
                if row.get('status'):
                    item_data['status'] = row['status']
                if row.get('preprocessing'):
                    item_data['preprocessing'] = row['preprocessing']
                return item_data

            def _sync_item_row(row, item_data):
                nonlocal created, updated
                target_keys.add(row['item_key'])
                if row['item_key'] in current_items_map:
                    existing = current_items_map[row['item_key']]
                    target_fp = client.calculate_fingerprint(item_data)
                    current_fp = client.calculate_fingerprint(existing)
                    if target_fp != current_fp:
                        client.update_item(existing['itemid'], item_data)
                        updated += 1
                else:
                    item_id = client.create_item(item_data)
                    if item_id:
                        # 记录新创建的 itemid，供依赖项查找 master_itemid
                        current_items_map[row['item_key']] = {'itemid': item_id, 'key_': row['item_key']}
                        created += 1

            for row in independent_rows:
                try:
                    item_data = _build_item_data(host_id, row, interface_id)
                    _sync_item_row(row, item_data)
                except ZabbixAPIException as e:
                    errors.append(f'{host_ip}/{row["item_key"]}: Zabbix API 错误 - {e}')
                except Exception as e:
                    errors.append(f'{host_ip}/{row["item_key"]}: {e}')

            # 第三轮：创建/更新依赖监控项（此时 master 已存在，可解析 master_itemid）
            for row in dependent_rows:
                try:
                    item_data = _build_item_data(host_id, row, interface_id)
                    master_key = row['master_item']
                    if master_key in current_items_map:
                        item_data['master_itemid'] = current_items_map[master_key]['itemid']
                        app.logger.info(
                            f"为依赖监控项 {row['item_key']} 解析 master_itemid: "
                            f"{master_key} -> {item_data['master_itemid']}"
                        )
                    else:
                        errors.append(
                            f'{host_ip}/{row["item_key"]}: 主监控项 {master_key} 不存在，'
                            f'无法设置 master_itemid，跳过'
                        )
                        continue
                    _sync_item_row(row, item_data)
                except ZabbixAPIException as e:
                    errors.append(f'{host_ip}/{row["item_key"]}: Zabbix API 错误 - {e}')
                except Exception as e:
                    errors.append(f'{host_ip}/{row["item_key"]}: {e}')

            # 第二轮：清理孤儿监控项（Zabbix 中存在但不在已确认列表中的）
            for key, item in current_items_map.items():
                if key not in target_keys:
                    try:
                        client.delete_item(item['itemid'])
                        deleted += 1
                    except ZabbixAPIException as e:
                        errors.append(f'{host_ip}/{key}: 删除失败 - {e}')
                    except Exception as e:
                        errors.append(f'{host_ip}/{key}: 删除异常 - {e}')

        except ZabbixAPIException as e:
            errors.append(f'主机 {host_ip}: Zabbix API 错误 - {e}')
        except Exception as e:
            errors.append(f'主机 {host_ip}: {e}')

    msg = f'已成功同步至{environment} Zabbix：新建 {created}，更新 {updated}，删除 {deleted}'
    if errors:
        msg += f'，{len(errors)} 个失败'
        return jsonify({'success': True, 'message': msg, 'synced_count': created + updated,
                        'deleted_count': deleted, 'errors': errors[:10]})
    return jsonify({'success': True, 'message': msg, 'synced_count': created + updated,
                    'deleted_count': deleted})


@app.route('/review/sync-progress')
def sync_progress():
    """同步进度查询（非阻塞）"""
    with _sync_progress_lock:
        return jsonify(dict(_sync_progress))


@app.route('/review/sync-abort', methods=['POST'])
def abort_sync():
    """中止正在运行的同步操作"""
    _sync_abort_event.set()
    return jsonify({'success': True, 'message': '已发出中止信号，同步将在当前主机完成后停止'})


@app.route('/review/sync-all', methods=['POST'])
@_with_sync_lock
def sync_all_to_zabbix():
    """一键同步所有已确认的复核表记录至 Zabbix（监控项 + 触发器 + 监控项原型 + 触发器原型）

    设计说明：同步操作是幂等的 — 已创建的实体就是"应该存在"的已确认配置。
    部分失败不会回滚已成功的操作，而是报告错误让用户修复后重新同步。
    get_managed_* 方法失败时会 raise（而非返回[]），避免误判"零实体"导致批量重建。

    TODO(v2): 重构同步引擎 — 消除 3 处重复实现
    重复现状:
      a) sync_all_to_zabbix() (本函数) — 4 实体类型, 约 400 行
      b) sync_items_to_zabbix() 行 2130 — 仅监控项, 约 140 行
      c) sync_webscenarios_to_zabbix() 行 3568 — 仅 Web 场景, 约 120 行
      d) zabbix_mac.py SyncEngine — 配置文件驱动, 不同职责
    重构方案:
      1. 定义 SyncEntity 协议类, 方法: fetch_existing() / build_data() /
         compare_fingerprint() / create() / update() / delete()
      2. 每个实体类型(Item/Trigger/ItemPrototype/TriggerPrototype/WebScenario)
         实现该协议, 封装表名列名映射 + Zabbix API 调用
      3. sync_all_to_zabbix() 降级为循环: for entity in entities: entity.sync()
      4. 合并 sync_items_to_zabbix() 和 sync_webscenarios_to_zabbix()
    约束: 保持幂等性, get_managed_* 失败时 raise 而非返回 []
    估算: ~400 行新代码, 需要 live Zabbix 回归测试 2-3 天
    """
    data = request.get_json()
    ids = data.get('ids', []) if data else []
    environment = data.get('environment', '').strip() if data else ''

    if environment not in ZABBIX_ENVIRONMENTS:
        return jsonify({'success': False, 'message': f'无效的环境: {environment}'}), 400

    env_config = ZABBIX_ENVIRONMENTS[environment]
    if not env_config['url']:
        return jsonify({'success': False, 'message': f'环境 "{environment}" 未配置 Zabbix URL'}), 500

    # Feature 2: 初始化中止事件和进度
    _sync_abort_event.clear()
    _sync_progress['running'] = True
    _sync_progress['errors'] = []

    # Feature 4: 系统/模块筛选
    system_filter = data.get('system', '').strip() if data else ''
    subsystem_filter = data.get('subsystem', '').strip() if data else ''

    from zabbix_mac import ZabbixClient, ZabbixAPIException
    client = ZabbixClient(env_config['url'], env_config['username'], env_config['password'])

    result = {
        'environment': environment,
        'items': {'created': 0, 'updated': 0, 'deleted': 0},
        'triggers': {'created': 0, 'updated': 0, 'deleted': 0},
        'item_prototypes': {'created': 0, 'updated': 0, 'deleted': 0},
        'trigger_prototypes': {'created': 0, 'updated': 0, 'deleted': 0},
        'errors': [],
        'aborted': False
    }

    # Feature 2: 预计算所有已确认实体涉及的总主机数
    _sync_progress['hosts_done'] = 0
    _sync_progress['current_host'] = ''
    _sync_progress['message'] = '正在收集已确认的实体数据...'

    all_hosts = set()
    _build_where = lambda filters: (
        " AND ".join(["confirmed = TRUE"] + [f"{k} = %s" for k in filters]),
        list(filters.values())
    )

    # 先扫描所有 4 张复核表，收集唯一主机列表
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            filter_clause, filter_params = _build_where(
                {k: v for k, v in [('system', system_filter), ('subsystem', subsystem_filter)] if v}
            )
            for table, col in [('items_review', 'host_ip'), ('triggers_review', 'host_ip'),
                               ('item_prototypes_review', 'host_ip'), ('trigger_prototypes_review', 'host_ip')]:
                cur.execute(f"SELECT DISTINCT {col} FROM {table} WHERE {filter_clause}", filter_params)
                for row in cur.fetchall():
                    all_hosts.add(row[col])
    finally:
        conn.close()

    _sync_progress['hosts_total'] = len(all_hosts)
    _sync_progress['message'] = ''

    def _check_abort(result_obj):
        if _sync_abort_event.is_set():
            result_obj['aborted'] = True
            result_obj['errors'].append('用户中止了同步操作')
            return True
        return False

    def _update_progress(host_ip):
        with _sync_progress_lock:
            _sync_progress['hosts_done'] += 1
            _sync_progress['current_host'] = host_ip

    # ==================== 1. 同步监控项 ====================
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            filter_clause, filter_params = _build_where(
                {k: v for k, v in [('system', system_filter), ('subsystem', subsystem_filter)] if v}
            )
            cur.execute(f"SELECT * FROM items_review WHERE {filter_clause} ORDER BY host_ip, item_key", filter_params)
            confirmed_items = cur.fetchall()
    finally:
        conn.close()

    if confirmed_items:
        hosts = {}
        for row in confirmed_items:
            hosts.setdefault(row['host_ip'], []).append(row)

        for host_ip, rows in hosts.items():
            if _check_abort(result):
                break
            try:
                host_id = client.get_host_id(host_ip)
                if not host_id:
                    result['errors'].append(f'[监控项] 主机 {host_ip} 不存在')
                    continue
                interface_id = client.get_host_interface_id(host_id)
                if not interface_id:
                    result['errors'].append(f'[监控项] 主机 {host_ip} 无可用接口')
                    continue

                existing_items = client.get_managed_items(host_id)
                current_map = {it['key_']: it for it in existing_items}
                target_keys = set()

                # 分离独立监控项和依赖监控项（type=18 依赖项 / type=15 计算项）
                independent_rows = []
                dependent_rows = []
                for row in rows:
                    item_type = int(row.get('type', 0))
                    if item_type in (15, 18) and row.get('master_item'):
                        dependent_rows.append(row)
                    else:
                        independent_rows.append(row)

                def _sync_item_inline(row, item_data):
                    target_keys.add(row['item_key'])
                    if row['item_key'] in current_map:
                        if client.calculate_fingerprint(item_data) != client.calculate_fingerprint(current_map[row['item_key']]):
                            client.update_item(current_map[row['item_key']]['itemid'], item_data)
                            result['items']['updated'] += 1
                    else:
                        item_id = client.create_item(item_data)
                        if item_id:
                            current_map[row['item_key']] = {'itemid': item_id, 'key_': row['item_key']}
                            result['items']['created'] += 1

                # 先处理独立监控项
                for row in independent_rows:
                    try:
                        item_data = {
                            'hostid': host_id, 'key_': row['item_key'], 'name': row['name'],
                            'type': row['type'], 'value_type': row['value_type'],
                            'delay': row['delay'], 'interfaceid': interface_id,
                        }
                        if row.get('description'): item_data['description'] = row['description']
                        if row.get('units'): item_data['units'] = row['units']
                        if row.get('history'): item_data['history'] = f"{row['history']}d"
                        if row.get('trends'): item_data['trends'] = f"{row['trends']}d"
                        if row.get('status'): item_data['status'] = row['status']
                        if row.get('preprocessing'): item_data['preprocessing'] = row['preprocessing']
                        _sync_item_inline(row, item_data)
                    except ZabbixAPIException as e:
                        result['errors'].append(f'[监控项] {host_ip}/{row["item_key"]}: {e}')
                    except Exception as e:
                        result['errors'].append(f'[监控项] {host_ip}/{row["item_key"]}: {e}')

                # 再处理依赖监控项（解析 master_item -> master_itemid）
                for row in dependent_rows:
                    try:
                        item_data = {
                            'hostid': host_id, 'key_': row['item_key'], 'name': row['name'],
                            'type': row['type'], 'value_type': row['value_type'],
                            'delay': row['delay'], 'interfaceid': interface_id,
                        }
                        if row.get('description'): item_data['description'] = row['description']
                        if row.get('units'): item_data['units'] = row['units']
                        if row.get('history'): item_data['history'] = f"{row['history']}d"
                        if row.get('trends'): item_data['trends'] = f"{row['trends']}d"
                        if row.get('status'): item_data['status'] = row['status']
                        if row.get('preprocessing'): item_data['preprocessing'] = row['preprocessing']
                        master_key = row['master_item']
                        if master_key in current_map:
                            item_data['master_itemid'] = current_map[master_key]['itemid']
                        else:
                            result['errors'].append(
                                f'[监控项] {host_ip}/{row["item_key"]}: 主监控项 {master_key} 不存在，'
                                f'无法设置 master_itemid，跳过'
                            )
                            continue
                        _sync_item_inline(row, item_data)
                    except ZabbixAPIException as e:
                        result['errors'].append(f'[监控项] {host_ip}/{row["item_key"]}: {e}')
                    except Exception as e:
                        result['errors'].append(f'[监控项] {host_ip}/{row["item_key"]}: {e}')

                for key, it in current_map.items():
                    if key not in target_keys:
                        try:
                            client.delete_item(it['itemid'])
                            result['items']['deleted'] += 1
                        except ZabbixAPIException as e:
                            result['errors'].append(f'[监控项] 删除 {host_ip}/{key}: {e}')
                _update_progress(host_ip)
            except ZabbixAPIException as e:
                result['errors'].append(f'[监控项] 主机 {host_ip}: {e}')
                _update_progress(host_ip)

    # ==================== 2. 同步触发器 ====================
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            filter_clause, filter_params = _build_where(
                {k: v for k, v in [('system', system_filter), ('subsystem', subsystem_filter)] if v}
            )
            cur.execute(f"SELECT * FROM triggers_review WHERE {filter_clause} ORDER BY host_ip, name", filter_params)
            confirmed_triggers = cur.fetchall()
    finally:
        conn.close()

    if confirmed_triggers:
        hosts = {}
        for row in confirmed_triggers:
            hosts.setdefault(row['host_ip'], []).append(row)

        for host_ip, rows in hosts.items():
            if _check_abort(result):
                break
            try:
                host_id = client.get_host_id(host_ip)
                if not host_id:
                    result['errors'].append(f'[触发器] 主机 {host_ip} 不存在')
                    continue

                existing = client.get_managed_triggers(host_id)
                current_map = {}
                for t in existing:
                    desc = t.get('description', '') or t.get('name', '')
                    if desc:
                        current_map[desc] = t

                target_descs = set()
                for row in rows:
                    try:
                        trigger_data = {
                            'description': row['name'],
                            'expression': row['expression'],
                            'priority': int(row['priority']),
                        }
                        if row.get('status') is not None:
                            trigger_data['status'] = int(row['status'])

                        target_descs.add(row['name'])
                        if row['name'] in current_map:
                            existing_t = current_map[row['name']]
                            if client.calculate_fingerprint(trigger_data) != client.calculate_fingerprint(existing_t):
                                client.update_trigger(existing_t['triggerid'], trigger_data)
                                result['triggers']['updated'] += 1
                        else:
                            client.create_trigger(trigger_data)
                            result['triggers']['created'] += 1
                    except ZabbixAPIException as e:
                        result['errors'].append(f'[触发器] {host_ip}/{row["name"]}: {e}')
                    except Exception as e:
                        result['errors'].append(f'[触发器] {host_ip}/{row["name"]}: {e}')

                for desc, t in current_map.items():
                    if desc not in target_descs:
                        try:
                            client.api.trigger.delete(t['triggerid'])
                            result['triggers']['deleted'] += 1
                        except ZabbixAPIException as e:
                            result['errors'].append(f'[触发器] 删除 {host_ip}/{desc}: {e}')
                _update_progress(host_ip)
            except ZabbixAPIException as e:
                result['errors'].append(f'[触发器] 主机 {host_ip}: {e}')
                _update_progress(host_ip)

    # ==================== 3 & 4. 同步监控项原型和触发器原型 ====================
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            # 加载 discovery_rules 完整配置（供 LLD 自动补齐使用）
            cur.execute("SELECT id, name, key, delay, evaltype, status FROM discovery_rules")
            dr_map = {row['key']: row for row in cur.fetchall()}

            ip_filter_clause, ip_filter_params = _build_where(
                {k: v for k, v in [('ipr.system', system_filter), ('ipr.subsystem', subsystem_filter)] if v}
            )
            cur.execute(f"""
                SELECT ipr.*, dr.key as dr_key, dr.name as dr_name
                FROM item_prototypes_review ipr
                JOIN discovery_rules dr ON ipr.discovery_rule_id = dr.id
                WHERE ipr.confirmed = TRUE AND {ip_filter_clause}
                ORDER BY ipr.host_ip, ipr.key
            """, ip_filter_params)
            confirmed_ip = cur.fetchall()

            tp_filter_clause, tp_filter_params = _build_where(
                {k: v for k, v in [('tpr.system', system_filter), ('tpr.subsystem', subsystem_filter)] if v}
            )
            cur.execute(f"""
                SELECT tpr.*, dr.key as dr_key, dr.name as dr_name
                FROM trigger_prototypes_review tpr
                JOIN discovery_rules dr ON tpr.discovery_rule_id = dr.id
                WHERE tpr.confirmed = TRUE AND {tp_filter_clause}
                ORDER BY tpr.host_ip, tpr.description
            """, tp_filter_params)
            confirmed_tp = cur.fetchall()
    finally:
        conn.close()

    # 按 (host_ip, dr_key) 分组同步
    if confirmed_ip or confirmed_tp:
        # 收集所有需要的主机+发现规则组合
        host_dr_pairs = set()
        for row in confirmed_ip:
            host_dr_pairs.add((row['host_ip'], row['dr_key'], row['dr_name']))
        for row in confirmed_tp:
            host_dr_pairs.add((row['host_ip'], row['dr_key'], row['dr_name']))

        for host_ip, dr_key, dr_name in host_dr_pairs:
            if _check_abort(result):
                break
            try:
                host_id = client.get_host_id(host_ip)
                if not host_id:
                    result['errors'].append(f'[原型] 主机 {host_ip} 不存在')
                    continue
                interface_id = client.get_host_interface_id(host_id)
                if not interface_id:
                    result['errors'].append(f'[原型] 主机 {host_ip} 无可用接口')
                    continue

                # 确保 Zabbix 上存在对应的 LLD 规则（查/创建）
                try:
                    rule_config = dr_map.get(dr_key, {})
                    rule_id = client.ensure_discovery_rule(
                        host_id, dr_key, rule_config, interface_id)
                    result.setdefault('discovery_rules_created', 0)
                    # ensure_discovery_rule 内部会创建，但我们只在新创建时计数
                except ZabbixAPIException as e:
                    result['errors'].append(
                        f'[原型] {host_ip}: LLD规则 {dr_key} 创建失败 - {e}')
                    continue

                # 同步监控项原型
                ip_rows = [r for r in confirmed_ip if r['host_ip'] == host_ip and r['dr_key'] == dr_key]
                if ip_rows:
                    existing_protos = client.get_item_prototypes(rule_id)
                    current_map = {p['key_']: p for p in existing_protos}
                    target_keys = set()

                    # 分离独立和依赖原型
                    ip_independent = []
                    ip_dependent = []
                    for row in ip_rows:
                        proto_type = int(row.get('type', 0))
                        if proto_type == 18 and row.get('master_item'):
                            ip_dependent.append(row)
                        else:
                            ip_independent.append(row)

                    def _build_proto_data(row):
                        proto_data = {
                            'ruleid': rule_id, 'hostid': host_id,
                            'name': row['name'], 'key_': row['key'],
                            'type': row.get('type', 0), 'value_type': row['value_type'],
                            'delay': _normalize_delay(row.get('delay')), 'units': row.get('units', ''),
                            'history': f"{row['history']}d" if row.get('history') else '7d',
                            'trends': f"{row['trends']}d" if row.get('trends') else '365d',
                        }
                        if interface_id:
                            proto_data['interfaceid'] = interface_id
                        if row.get('description'):
                            proto_data['description'] = row['description']
                        if row.get('status'):
                            proto_data['status'] = row['status']
                        return proto_data

                    def _sync_proto_row(row, proto_data):
                        target_keys.add(row['key'])
                        if row['key'] in current_map:
                            if client.calculate_fingerprint(proto_data) != client.calculate_fingerprint(current_map[row['key']]):
                                client.api.itemprototype.update({'itemid': current_map[row['key']]['itemid'], **proto_data})
                                result['item_prototypes']['updated'] += 1
                        else:
                            proto_id = client.create_item_prototype(proto_data)
                            if proto_id:
                                current_map[row['key']] = {'itemid': proto_id, 'key_': row['key']}
                                result['item_prototypes']['created'] += 1

                    # 先处理独立原型
                    for row in ip_independent:
                        try:
                            proto_data = _build_proto_data(row)
                            _sync_proto_row(row, proto_data)
                        except ZabbixAPIException as e:
                            result['errors'].append(f'[监控项原型] {host_ip}/{row["key"]}: {e}')

                    # 再处理依赖原型（解析 master_item -> master_itemid）
                    for row in ip_dependent:
                        try:
                            proto_data = _build_proto_data(row)
                            master_key = row['master_item']
                            if master_key in current_map:
                                proto_data['master_itemid'] = current_map[master_key]['itemid']
                            else:
                                result['errors'].append(
                                    f'[监控项原型] {host_ip}/{row["key"]}: 主监控项原型 {master_key} 不存在，'
                                    f'无法设置 master_itemid，跳过'
                                )
                                continue
                            _sync_proto_row(row, proto_data)
                        except ZabbixAPIException as e:
                            result['errors'].append(f'[监控项原型] {host_ip}/{row["key"]}: {e}')

                    for key, p in current_map.items():
                        if key not in target_keys:
                            try:
                                client.api.itemprototype.delete(p['itemid'])
                                result['item_prototypes']['deleted'] += 1
                            except ZabbixAPIException as e:
                                result['errors'].append(f'[监控项原型] 删除 {host_ip}/{key}: {e}')

                # 同步触发器原型
                tp_rows = [r for r in confirmed_tp if r['host_ip'] == host_ip and r['dr_key'] == dr_key]
                if tp_rows:
                    existing_tprotos = client.get_trigger_prototypes(rule_id)
                    current_map = {t['description']: t for t in existing_tprotos}
                    target_descs = set()
                    for row in tp_rows:
                        try:
                            tp_data = {
                                'description': row['description'],
                                'expression': row['expression'],
                                'priority': int(row['priority']),
                            }
                            if row.get('status') is not None:
                                tp_data['status'] = int(row['status'])

                            target_descs.add(row['description'])
                            if row['description'] in current_map:
                                if client.calculate_fingerprint(tp_data) != client.calculate_fingerprint(current_map[row['description']]):
                                    tp_data['triggerid'] = current_map[row['description']]['triggerid']
                                    client.api.triggerprototype.update(tp_data)
                                    result['trigger_prototypes']['updated'] += 1
                            else:
                                tp_data['discoveryruleid'] = rule_id
                                client.create_trigger_prototype(tp_data)
                                result['trigger_prototypes']['created'] += 1
                        except ZabbixAPIException as e:
                            result['errors'].append(f'[触发器原型] {host_ip}/{row["description"]}: {e}')

                    for desc, t in current_map.items():
                        if desc not in target_descs:
                            try:
                                client.api.triggerprototype.delete(t['triggerid'])
                                result['trigger_prototypes']['deleted'] += 1
                            except ZabbixAPIException as e:
                                result['errors'].append(f'[触发器原型] 删除 {host_ip}/{desc}: {e}')

                _update_progress(host_ip)
            except ZabbixAPIException as e:
                result['errors'].append(f'[原型] {host_ip}/{dr_key}: {e}')
                _update_progress(host_ip)

    # 构建汇总消息
    parts = []
    for label, key in [('监控项', 'items'), ('触发器', 'triggers'),
                        ('监控项原型', 'item_prototypes'), ('触发器原型', 'trigger_prototypes')]:
        stats = result[key]
        total = stats['created'] + stats['updated'] + stats['deleted']
        if total > 0:
            parts.append(f'{label} 新建{stats["created"]} 更新{stats["updated"]} 删除{stats["deleted"]}')

    msg = f'同步至{environment}: ' + ('; '.join(parts) if parts else '无变更')
    if result['errors']:
        msg += f'，{len(result["errors"])} 个错误'

    _sync_progress['running'] = False
    _sync_progress['message'] = msg

    return jsonify({
        'success': True, 'message': msg,
        'result': result,
        'errors': result['errors'][:10] if result['errors'] else [],
        'aborted': result['aborted']
    })


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
        master_item = request.form.get('master_item') or None
        preprocessing_raw = request.form.get('preprocessing')
        if preprocessing_raw and preprocessing_raw.strip():
            try:
                preprocessing = json.loads(preprocessing_raw)
                if preprocessing == '':
                    preprocessing = None
            except json.JSONDecodeError:
                preprocessing = None
        else:
            preprocessing = None
        template_name = request.form['template_name']
        system = request.form.get('system') or None
        subsystem = request.form.get('subsystem') or None

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

@app.route('/item-review/confirm/<int:review_id>', methods=['POST'])
def confirm_item_review(review_id):
    """确认监控项复核表记录（含 Diff 状态更新）"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE items_review
                SET confirmed = true,
                    sync_status = 'synced',
                    change_type = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (review_id,))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

@app.route('/item-review/unconfirm/<int:review_id>', methods=['POST'])
def unconfirm_item_review(review_id):
    """取消确认监控项复核表记录（已废弃，前端已移除对应按钮）"""
    logging.warning('DEPRECATED route /item-review/unconfirm called for review_id=%s', review_id)
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE items_review SET confirmed = false,
                    sync_status = 'pending_confirm',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (review_id,))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


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
        system = request.form.get('system', '').strip() or None
        subsystem = request.form.get('subsystem', '').strip() or None
        master_item = request.form.get('master_item') or None
        preprocessing_raw = request.form.get('preprocessing')
        if preprocessing_raw and preprocessing_raw.strip():
            try:
                preprocessing = json.loads(preprocessing_raw)
                if preprocessing == '':
                    preprocessing = None
            except json.JSONDecodeError:
                preprocessing = None
        else:
            preprocessing = None

        with conn.cursor() as cur:
            # 1. 写入主表 items，返回新 ID（items 表无 system/subsystem 字段）
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

            # 2. 写入复核表 items_review（含 system/subsystem）
            cur.execute("""
                INSERT INTO items_review (
                    item_id, host_ip, item_key, name, type, value_type, delay,
                    description, units, multiplier, delta, history, trends,
                    status, template_name, master_item, preprocessing,
                    system, subsystem,
                    modified, confirmed, status_verification
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (new_item_id, host_ip, item_key, name, type_val, value_type, delay,
                   description, units, multiplier, delta, history, trends, status,
                   template_name, master_item, preprocessing,
                   system, subsystem,
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
    """触发器复核表管理 — 支持 ip/system/subsystem 过滤 + 分页"""
    ip = request.args.get('ip', '').strip()
    system = request.args.get('system', '').strip()
    subsystem = request.args.get('subsystem', '').strip()
    sync_filter = request.args.get('sync_filter', 'all').strip()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    page, per_page = _safe_pagination(page, per_page)
    offset = (page - 1) * per_page

    conn = get_db_connection()
    with conn.cursor(cursor_factory=DictCursor) as cur:
        where_clause = " WHERE 1=1"
        params = []
        if ip:
            where_clause += " AND host_ip ILIKE %s"
            params.append(f'%{ip}%')
        if system:
            where_clause += " AND system ILIKE %s"
            params.append(f'%{system}%')
        if subsystem:
            where_clause += " AND subsystem ILIKE %s"
            params.append(f'%{subsystem}%')
        if sync_filter == 'pending':
            where_clause += " AND (sync_status != 'synced' OR sync_status IS NULL)"

        # datalist 数据
        cur.execute("SELECT DISTINCT system FROM triggers_review WHERE system IS NOT NULL AND system != '' ORDER BY system")
        distinct_systems = [r['system'] for r in cur.fetchall()]
        cur.execute("SELECT DISTINCT subsystem FROM triggers_review WHERE subsystem IS NOT NULL AND subsystem != '' ORDER BY subsystem")
        distinct_subsystems = [r['subsystem'] for r in cur.fetchall()]

        # COUNT
        cur.execute(f"SELECT COUNT(*) FROM triggers_review{where_clause}", params)
        total = cur.fetchone()['count']

        # DATA with pagination
        cur.execute(f"SELECT * FROM triggers_review{where_clause} ORDER BY id LIMIT %s OFFSET %s",
                    params + [per_page, offset])
        triggers = cur.fetchall()

    conn.close()

    total_pages = (total + per_page - 1) // per_page
    return render_template('triggers_review.html', triggers=triggers,
                           distinct_systems=distinct_systems,
                           distinct_subsystems=distinct_subsystems,
                           sync_filter=sync_filter,
                           page=page, per_page=per_page,
                           total=total, total_pages=total_pages)


@app.route('/triggers-review/initialize', methods=['POST'])
@_with_sync_lock
def initialize_triggers_review():
    """初始化 triggers_review 表：基于 Diff 算法增量更新
    （已同步记录保持不变，新增/变更/删除均通过 change_type 标记）"""
    data = request.get_json() if request.is_json else {}
    system_filter = data.get('system', '').strip() if data else ''
    subsystem_filter = data.get('subsystem', '').strip() if data else ''

    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            # 1. 获取现有记录
            existing_conditions = ["1=1"]
            existing_params = []
            if system_filter:
                existing_conditions.append("system = %s")
                existing_params.append(system_filter)
            if subsystem_filter:
                existing_conditions.append("subsystem = %s")
                existing_params.append(subsystem_filter)
            existing_where = " AND ".join(existing_conditions)
            cur.execute(f"SELECT * FROM triggers_review WHERE {existing_where}", existing_params)
            existing_rows = cur.fetchall()

            # 2. 获取上游最新数据
            where_parts = ["tr.template_name = %s", "h.template_id = tr.template_name"]
            query_params = [app.config['DEFAULT_TEMPLATE_NAME']]
            if system_filter:
                where_parts.append("h.system = %s")
                query_params.append(system_filter)
            if subsystem_filter:
                where_parts.append("h.subsystem = %s")
                query_params.append(subsystem_filter)
            where_clause = " AND ".join(where_parts)

            cur.execute(f"""
                SELECT
                    tr.id as trigger_id,
                    h.name as host_ip,
                    tr.name,
                    REPLACE(tr.expression, '{{host:', '{{' || h.name || ':') as expression,
                    tr.priority,
                    tr.description,
                    tr.status,
                    tr.template_name,
                    h.system,
                    h.subsystem,
                    h.in_room
                FROM triggers tr
                CROSS JOIN hosts h
                WHERE {where_clause}
                ORDER BY tr.id, h.name
            """, query_params)
            new_rows = cur.fetchall()

            all_insert_cols = [
                'trigger_id', 'host_ip', 'name', 'expression', 'priority', 'description',
                'status', 'template_name', 'system', 'subsystem', 'in_room'
            ]
            content_columns = [
                'name', 'expression', 'priority', 'description', 'status',
                'template_name', 'system', 'subsystem', 'in_room'
            ]
            unique_keys = ['trigger_id', 'host_ip']

            result = _diff_and_merge(
                cur, 'triggers_review', unique_keys, content_columns,
                new_rows, existing_rows, all_insert_cols
            )
        conn.commit()
        return jsonify({
            'success': True,
            'message': f'triggers_review 表 Diff 完成：新增 {result["new"]} 条，变更 {result["update"]} 条，标记删除 {result["delete"]} 条，无变化 {result["unchanged"]} 条'
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
        system = request.form.get('system', '').strip() or None
        subsystem = request.form.get('subsystem', '').strip() or None

        # 更新数据
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE triggers_review SET name = %s, expression = %s, priority = %s,
                                           description = %s, status = %s, template_name = %s,
                                           host_ip = %s, system = %s, subsystem = %s,
                                           modified = true
                    WHERE id = %s
                """, (name, expression, priority, description, status, template_name,
                      host_ip, system, subsystem, review_id))
            conn.commit()
            flash('记录更新成功')
            return redirect(url_for('triggers_review'))
        except Exception as e:
            conn.rollback()
            flash(f'更新失败: {e}')
    
    conn.close()
    return render_template('edit_trigger_review.html', trigger=trigger)

@app.route('/trigger-review/confirm/<int:review_id>', methods=['POST'])
def confirm_trigger_review(review_id):
    """确认触发器复核表记录"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE triggers_review SET confirmed = true, sync_status = 'synced', change_type = NULL, updated_at = CURRENT_TIMESTAMP WHERE id = %s", (review_id,))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

@app.route('/trigger-review/unconfirm/<int:review_id>', methods=['POST'])
def unconfirm_trigger_review(review_id):
    """取消确认触发器复核表记录（已废弃，前端已移除对应按钮）"""
    logging.warning('DEPRECATED route /trigger-review/unconfirm called for review_id=%s', review_id)
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE triggers_review SET confirmed = false, sync_status = 'pending_confirm', updated_at = CURRENT_TIMESTAMP WHERE id = %s", (review_id,))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@app.route('/trigger-review/add', methods=['POST'])
def add_trigger_from_review():
    """从复核页面添加触发器：仅写入 triggers_review 复核表（不改动 triggers 主表）"""
    conn = get_db_connection()
    try:
        name = request.form['name']
        expression = request.form['expression']
        priority = int(request.form['priority'])
        template_name = request.form['template_name']
        host_ip = request.form.get('host_ip', '').strip()

        description = request.form.get('description')
        status = request.form.get('status', 0)
        system = request.form.get('system', '').strip() or None
        subsystem = request.form.get('subsystem', '').strip() or None

        with conn.cursor() as cur:
            # 从 triggers 主表查找同模板的已有触发器作为 FK 引用（不改动 triggers 表）
            cur.execute(
                "SELECT id FROM triggers WHERE template_name = %s LIMIT 1",
                (template_name,)
            )
            ref = cur.fetchone()
            if not ref:
                return jsonify({
                    'success': False,
                    'message': f'模板 {template_name} 下无已有触发器可作为引用，请先在触发器管理中创建'
                }), 400
            ref_trigger_id = ref[0]

            # 写入复核表 triggers_review（system/subsystem 仅存此处）
            cur.execute("""
                INSERT INTO triggers_review (
                    trigger_id, host_ip, name, expression, priority, description,
                    status, template_name,
                    system, subsystem,
                    modified, confirmed, status_verification
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (ref_trigger_id, host_ip, name, expression, priority, description,
                   status, template_name,
                   system, subsystem,
                   False, False, 'pending'))

        conn.commit()
        return jsonify({'success': True, 'message': '触发器添加成功'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': f'添加失败: {str(e)}'}), 500
    finally:
        conn.close()


# ============================================================
# 复核表导出 / 导入 Excel
# ============================================================

@app.route('/items-review/export')
def export_items_review():
    """导出 items_review 表到 Excel 文件"""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("SELECT * FROM items_review ORDER BY host_ip, item_key")
            rows = cur.fetchall()
        if not rows:
            return jsonify({'success': False, 'message': 'items_review 表为空'}), 400

        df = pd.DataFrame([dict(r) for r in rows])
        # 写入临时文件
        tmp = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
        df.to_excel(tmp.name, index=False, engine='openpyxl')
        tmp.close()

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return send_file(tmp.name, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                         as_attachment=True, download_name=f'items_review_{timestamp}.xlsx')
    except Exception as e:
        return jsonify({'success': False, 'message': f'导出失败: {str(e)}'}), 500
    finally:
        conn.close()


@app.route('/items-review/import', methods=['POST'])
def import_items_review():
    """从 Excel 文件导入数据到 items_review 表（清空后写入）"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '未选择文件'}), 400

    file = request.files['file']
    if not file.filename:
        return jsonify({'success': False, 'message': '文件名为空'}), 400

    conn = get_db_connection()
    try:
        df = pd.read_excel(file, engine='openpyxl')

        with conn.cursor() as cur:
            cur.execute("DELETE FROM items_review")
            deleted = cur.rowcount

            columns = _sanitize_import_columns('items_review', list(df.columns))
            placeholders = ', '.join(['%s'] * len(columns))
            column_names = ', '.join(columns)
            all_values = []
            for _, row in df.iterrows():
                values = []
                for col in columns:
                    val = row[col]
                    if pd.isna(val):
                        values.append(None)
                    elif isinstance(val, str) and (val.startswith('{') or val.startswith('[')):
                        try:
                            values.append(json.dumps(ast.literal_eval(val)))
                        except (ValueError, SyntaxError):
                            values.append(val)
                    else:
                        values.append(val)
                all_values.append(values)
            cur.executemany(
                f"INSERT INTO items_review ({column_names}) VALUES ({placeholders})",
                all_values
            )
            inserted = len(all_values)
        conn.commit()
        return jsonify({
            'success': True,
            'message': f'items_review 导入成功：删除 {deleted} 条，导入 {inserted} 条'
        })
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': f'导入失败: {str(e)}'}), 500
    finally:
        conn.close()


@app.route('/triggers-review/export')
def export_triggers_review():
    """导出 triggers_review 表到 Excel 文件"""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("SELECT * FROM triggers_review ORDER BY host_ip, name")
            rows = cur.fetchall()
        if not rows:
            return jsonify({'success': False, 'message': 'triggers_review 表为空'}), 400

        df = pd.DataFrame([dict(r) for r in rows])
        tmp = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
        df.to_excel(tmp.name, index=False, engine='openpyxl')
        tmp.close()

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return send_file(tmp.name, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                         as_attachment=True, download_name=f'triggers_review_{timestamp}.xlsx')
    except Exception as e:
        return jsonify({'success': False, 'message': f'导出失败: {str(e)}'}), 500
    finally:
        conn.close()


@app.route('/triggers-review/import', methods=['POST'])
def import_triggers_review():
    """从 Excel 文件导入数据到 triggers_review 表（清空后写入）"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '未选择文件'}), 400

    file = request.files['file']
    if not file.filename:
        return jsonify({'success': False, 'message': '文件名为空'}), 400

    conn = get_db_connection()
    try:
        df = pd.read_excel(file, engine='openpyxl')

        with conn.cursor() as cur:
            cur.execute("DELETE FROM triggers_review")
            deleted = cur.rowcount

            columns = _sanitize_import_columns('triggers_review', list(df.columns))
            placeholders = ', '.join(['%s'] * len(columns))
            column_names = ', '.join(columns)
            all_values = []
            for _, row in df.iterrows():
                values = []
                for col in columns:
                    val = row[col]
                    if pd.isna(val):
                        values.append(None)
                    elif isinstance(val, str) and (val.startswith('{') or val.startswith('[')):
                        try:
                            values.append(json.dumps(ast.literal_eval(val)))
                        except (ValueError, SyntaxError):
                            values.append(val)
                    else:
                        values.append(val)
                all_values.append(values)
            cur.executemany(
                f"INSERT INTO triggers_review ({column_names}) VALUES ({placeholders})",
                all_values
            )
            inserted = len(all_values)
        conn.commit()
        return jsonify({
            'success': True,
            'message': f'triggers_review 导入成功：删除 {deleted} 条，导入 {inserted} 条'
        })
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': f'导入失败: {str(e)}'}), 500
    finally:
        conn.close()


# ============================================================
# Web场景复核表管理路由
# ============================================================

@app.route('/webscenarios-review')
def webscenarios_review():
    """Web场景复核表管理 — 支持 host/system/subsystem 过滤 + 分页"""
    host = request.args.get('host', '').strip()
    system = request.args.get('system', '').strip()
    subsystem = request.args.get('subsystem', '').strip()
    sync_filter = request.args.get('sync_filter', 'all').strip()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    page, per_page = _safe_pagination(page, per_page)
    offset = (page - 1) * per_page

    conn = get_db_connection()
    with conn.cursor(cursor_factory=DictCursor) as cur:
        where_clause = " WHERE 1=1"
        params = []
        if host:
            where_clause += " AND host ILIKE %s"
            params.append(f'%{host}%')
        if system:
            where_clause += " AND system ILIKE %s"
            params.append(f'%{system}%')
        if subsystem:
            where_clause += " AND subsystem ILIKE %s"
            params.append(f'%{subsystem}%')
        if sync_filter == 'pending':
            where_clause += " AND (sync_status != 'synced' OR sync_status IS NULL)"

        cur.execute("SELECT DISTINCT system FROM webscenario_items_review WHERE system IS NOT NULL AND system != '' ORDER BY system")
        distinct_systems = [r['system'] for r in cur.fetchall()]
        cur.execute("SELECT DISTINCT subsystem FROM webscenario_items_review WHERE subsystem IS NOT NULL AND subsystem != '' ORDER BY subsystem")
        distinct_subsystems = [r['subsystem'] for r in cur.fetchall()]

        cur.execute(f"SELECT COUNT(*) FROM webscenario_items_review{where_clause}", params)
        total = cur.fetchone()['count']

        cur.execute(f"SELECT * FROM webscenario_items_review{where_clause} ORDER BY id LIMIT %s OFFSET %s",
                    params + [per_page, offset])
        webscenarios = cur.fetchall()

    conn.close()

    total_pages = (total + per_page - 1) // per_page
    return render_template('webscenarios_review.html', webscenarios=webscenarios,
                           distinct_systems=distinct_systems,
                           distinct_subsystems=distinct_subsystems,
                           sync_filter=sync_filter,
                           page=page, per_page=per_page,
                           total=total, total_pages=total_pages)


@app.route('/webscenarios-review/initialize', methods=['POST'])
@_with_sync_lock
def initialize_webscenarios_review():
    """初始化 webscenario_items_review 表：全量清空重建。
    触发器名称动态注入机房对应的 Zabbix Server IP:
      格式: [{zabbix_ip}] Web scenario [{name}] failed
    """
    data = request.get_json() if request.is_json else {}
    system_filter = data.get('system', '').strip() if data else ''
    subsystem_filter = data.get('subsystem', '').strip() if data else ''

    # 加载机房映射
    room_mapping = _config.get('zabbix_room_mapping', {}) or {}

    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            # 1. 清空复核表
            cur.execute("TRUNCATE webscenario_items_review RESTART IDENTITY")

            # 2. 拉取源数据（4 个 UNION ALL）
            source_where = ""
            source_params = []
            if system_filter:
                source_where += " AND system = %s"
                source_params.append(system_filter)
            if subsystem_filter:
                source_where += " AND subsystem = %s"
                source_params.append(subsystem_filter)

            cur.execute(f"""
                SELECT system, subsystem, host, name, url, status_code, in_room
                FROM (
                    SELECT system, subsystem,
                        'Zabbix server' as host,
                        system || '_' || subsystem || '_clb' as name,
                        nginx_clb as url, '200' as status_code, in_room
                    FROM webscenario_items
                    WHERE nginx_clb IS NOT NULL AND nginx_clb != ''{source_where}
                    UNION ALL
                    SELECT system, subsystem,
                        'Zabbix server' as host,
                        system || '_' || subsystem || '_nginx' as name,
                        nginx as url, '200' as status_code, in_room
                    FROM webscenario_items
                    WHERE nginx IS NOT NULL AND nginx != ''{source_where}
                    UNION ALL
                    SELECT system, subsystem,
                        'Zabbix server' as host,
                        system || '_' || subsystem || '_clb_direct' as name,
                        clb as url, '200' as status_code, in_room
                    FROM webscenario_items
                    WHERE clb IS NOT NULL AND clb != ''{source_where}
                    UNION ALL
                    SELECT system, subsystem,
                        'Zabbix server' as host,
                        system || '_' || subsystem || '_pod' as name,
                        pod as url, '200' as status_code, in_room
                    FROM webscenario_items
                    WHERE pod IS NOT NULL AND pod != ''{source_where}
                ) src
                ORDER BY name
            """, source_params)
            rows = cur.fetchall()

            if not rows:
                conn.commit()
                return jsonify({'success': True, 'message': '源表无数据，复核表已清空'})

            # 3. 注入机房 IP → 转换名称
            from psycopg2.extras import execute_values
            insert_rows = []
            for r in rows:
                room = (r.get('in_room') or '').strip()
                zabbix_ip = room_mapping.get(room) or room_mapping.get(str(room))
                if not zabbix_ip:
                    zabbix_ip = 'Unknown'
                new_name = f"[{zabbix_ip}] Web scenario [{r['name']}] failed"
                insert_rows.append((
                    r['system'], r['subsystem'], r['host'],
                    new_name, r['url'], r['status_code'], r['in_room']
                ))

            # 4. 批量 INSERT
            cols = ['system', 'subsystem', 'host', 'name', 'url', 'status_code', 'in_room']
            sql = f"INSERT INTO webscenario_items_review ({', '.join(cols)}) VALUES %s"
            execute_values(cur, sql, insert_rows)

        conn.commit()
        return jsonify({
            'success': True,
            'message': f'webscenario_items_review 初始化完成：插入 {len(insert_rows)} 条记录'
        })
    except Exception as e:
        conn.rollback()
        app.logger.error(f"WebScenario 复核表初始化失败: {e}")
        return jsonify({'success': False, 'message': f'初始化失败: {str(e)}'}), 500
    finally:
        conn.close()


@app.route('/webscenarios-review/sync', methods=['POST'])
@_with_sync_lock
def sync_webscenarios_to_zabbix():
    """同步已确认Web场景到指定 Zabbix 环境（含孤儿清理）"""
    data = request.get_json()
    environment = data.get('environment', '')
    if not environment:
        return jsonify({'success': False, 'message': '请选择目标环境机房'}), 400

    env_config = ZABBIX_ENVIRONMENTS[environment]
    if not env_config['url']:
        return jsonify({'success': False, 'message': f'环境 {environment} 未配置 URL'}), 400

    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("SELECT * FROM webscenario_items_review WHERE confirmed = TRUE ORDER BY host, name")
            confirmed_scenarios = cur.fetchall()
    finally:
        conn.close()

    if not confirmed_scenarios:
        return jsonify({'success': True, 'message': '没有已确认的Web场景需要同步', 'synced_count': 0})

    from zabbix_mac import ZabbixClient, ZabbixAPIException

    client = ZabbixClient(env_config['url'], env_config['username'], env_config['password'])
    created = 0
    updated = 0
    deleted = 0
    errors = []

    # 按主机分组
    hosts = {}
    for row in confirmed_scenarios:
        host = row['host']
        if host not in hosts:
            hosts[host] = []
        hosts[host].append(row)

    for host_name, rows in hosts.items():
        try:
            host_id = client.get_host_id(host_name)
            if not host_id:
                errors.append(f'主机 {host_name} 在 Zabbix 中不存在')
                continue

            # 获取该主机所有自有 Web 场景（排除模板继承的）
            try:
                all_scenarios = client.api.httptest.get(
                    hostids=host_id,
                    output="extend",
                    selectSteps="extend"
                )
                all_scenarios = [s for s in all_scenarios if s.get("templateid") == "0"]
            except ZabbixAPIException as e:
                errors.append(f'主机 {host_name}: 获取Web场景失败 - {e}')
                continue

            current_map = {s['name']: s for s in all_scenarios}
            target_names = set()

            # 第一轮：创建/更新目标 Web 场景
            for row in rows:
                try:
                    scenario_name = row['name']
                    target_names.add(scenario_name)

                    # Zabbix 5.0 httptest name 限 64 字符，超长截断
                    safe_name = scenario_name[:60] if len(scenario_name) > 63 else scenario_name
                    step_name = row['url'][:50] if row.get('url') else 'HTTP check'

                    scenario_data = {
                        "name": safe_name,
                        "hostid": host_id,
                        "agent": "0",
                        "retries": "1",
                        "steps": [{
                            "no": 1,
                            "name": step_name,
                            "url": row['url'],
                            "timeout": "30",
                            "status_codes": str(row.get('status_code', '200')),
                            "follow_redirects": "1"
                        }]
                    }

                    if scenario_name in current_map:
                        existing = current_map[scenario_name]
                        target_fp = client.calculate_fingerprint(scenario_data)
                        current_fp = client.calculate_fingerprint(existing)
                        if target_fp != current_fp:
                            client.update_web_scenario(existing['httptestid'], scenario_data)
                            updated += 1
                    else:
                        client.create_web_scenario(scenario_data)
                        created += 1

                except ZabbixAPIException as e:
                    errors.append(f'{host_name}/{scenario_name}: Zabbix API 错误 - {e}')
                except Exception as e:
                    errors.append(f'{host_name}/{scenario_name}: {e}')

            # 第二轮：清理孤儿 Web 场景（Zabbix 中存在但不在已确认列表中的）
            for name, scenario in current_map.items():
                if name not in target_names:
                    try:
                        client.delete_web_scenario(scenario['httptestid'])
                        deleted += 1
                    except ZabbixAPIException as e:
                        errors.append(f'{host_name}/{name}: 删除失败 - {e}')
                    except Exception as e:
                        errors.append(f'{host_name}/{name}: 删除异常 - {e}')

        except ZabbixAPIException as e:
            errors.append(f'主机 {host_name}: Zabbix API 错误 - {e}')
        except Exception as e:
            errors.append(f'主机 {host_name}: {e}')

    msg = f'已成功同步至{environment} Zabbix：新建 {created}，更新 {updated}，删除 {deleted}'
    if errors:
        msg += f'，{len(errors)} 个失败'
        return jsonify({'success': True, 'message': msg, 'synced_count': created + updated,
                        'deleted_count': deleted, 'errors': errors[:10]})
    return jsonify({'success': True, 'message': msg, 'synced_count': created + updated,
                    'deleted_count': deleted})


@app.route('/webscenarios-review/sync-triggers', methods=['POST'])
@_with_sync_lock
def sync_webscenario_triggers_to_zabbix():
    """同步Web场景触发器到指定 Zabbix 环境"""
    data = request.get_json()
    environment = data.get('environment', '')
    if not environment:
        return jsonify({'success': False, 'message': '请选择目标环境机房'}), 400

    try:
        env_config = ZABBIX_ENVIRONMENTS[environment]
        if not env_config['url']:
            return jsonify({'success': False, 'message': f'环境 {environment} 未配置 URL'}), 400

        from zabbix_mac import ConfigLoader, ZabbixClient, ZabbixUltimateAutomator
        loader = ConfigLoader()
        client = ZabbixClient(env_config['url'], env_config['username'], env_config['password'])
        automator = ZabbixUltimateAutomator(config_loader=loader, zabbix_client=client)
        automator.create_web_scenario_triggers()

        return jsonify({'success': True, 'message': f'Web场景触发器同步到 {environment} 完成'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'同步失败: {str(e)}'}), 500


@app.route('/webscenario-review/edit/<int:review_id>', methods=['GET', 'POST'])
def edit_webscenario_review(review_id):
    """编辑单条 Web 场景复核记录"""
    conn = get_db_connection()
    if request.method == 'GET':
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("SELECT * FROM webscenario_items_review WHERE id = %s", (review_id,))
            ws = cur.fetchone()
        conn.close()
        if not ws:
            flash('记录不存在')
            return redirect(url_for('webscenarios_review'))
        return render_template('edit_webscenario_review.html', ws=ws)

    # POST — save changes
    host = request.form['host']
    name = request.form['name']
    url = request.form['url']
    status_code = request.form['status_code']
    system = request.form.get('system', '')
    subsystem = request.form.get('subsystem', '')

    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE webscenario_items_review
                SET host = %s, name = %s, url = %s, status_code = %s,
                    system = %s, subsystem = %s, modified = true, updated_at = NOW()
                WHERE id = %s
            """, (host, name, url, status_code, system, subsystem, review_id))
        conn.commit()
        flash('保存成功')
    except Exception as e:
        conn.rollback()
        flash(f'保存失败: {e}')
    finally:
        conn.close()
    return redirect(url_for('webscenarios_review'))


@app.route('/webscenario-review/confirm/<int:review_id>', methods=['POST'])
def confirm_webscenario_review(review_id):
    """确认 Web 场景复核记录"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE webscenario_items_review SET confirmed = true, sync_status = 'synced', change_type = NULL, updated_at = CURRENT_TIMESTAMP WHERE id = %s", (review_id,))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@app.route('/webscenario-review/unconfirm/<int:review_id>', methods=['POST'])
def unconfirm_webscenario_review(review_id):
    """取消确认 Web 场景复核记录（已废弃，前端已移除对应按钮）"""
    logging.warning('DEPRECATED route /webscenario-review/unconfirm called for review_id=%s', review_id)
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE webscenario_items_review SET confirmed = false, sync_status = 'pending_confirm', updated_at = CURRENT_TIMESTAMP WHERE id = %s", (review_id,))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@app.route('/webscenario-review/add', methods=['POST'])
def add_webscenario_from_review():
    """手动添加 Web 场景到复核表"""
    name = request.form['name']
    host = request.form['host']
    url = request.form['url']
    status_code = request.form['status_code']
    system = request.form.get('system', '')
    subsystem = request.form.get('subsystem', '')

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO webscenario_items_review (name, host, url, status_code, system, subsystem, modified, confirmed, status_verification)
                VALUES (%s, %s, %s, %s, %s, %s, false, false, 'pending')
            """, (name, host, url, status_code, system, subsystem))
        conn.commit()
        return jsonify({'success': True, 'message': 'Web场景添加成功'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': f'添加失败: {str(e)}'}), 500
    finally:
        conn.close()


@app.route('/webscenarios-review/export')
def export_webscenarios_review():
    """导出 webscenario_items_review 到 Excel"""
    import pandas as pd
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM webscenario_items_review ORDER BY id")
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
        df = pd.DataFrame(rows, columns=columns)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='webscenario_items_review')
        output.seek(0)
        return send_file(output, download_name='webscenario_items_review.xlsx',
                         mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                         as_attachment=True)
    except Exception as e:
        return jsonify({'success': False, 'message': f'导出失败: {str(e)}'}), 500
    finally:
        conn.close()


@app.route('/webscenarios-review/import', methods=['POST'])
def import_webscenarios_review():
    """从 Excel 导入数据到 webscenario_items_review 表（清空后写入）"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '未选择文件'}), 400

    file = request.files['file']
    if not file.filename:
        return jsonify({'success': False, 'message': '文件名为空'}), 400

    conn = get_db_connection()
    try:
        df = pd.read_excel(file, engine='openpyxl')

        with conn.cursor() as cur:
            cur.execute("DELETE FROM webscenario_items_review")
            deleted = cur.rowcount

            columns = _sanitize_import_columns('webscenario_items_review', list(df.columns))
            placeholders = ', '.join(['%s'] * len(columns))
            column_names = ', '.join(columns)
            all_values = []
            for _, row in df.iterrows():
                values = []
                for col in columns:
                    val = row[col]
                    if pd.isna(val):
                        values.append(None)
                    else:
                        values.append(val)
                all_values.append(values)
            cur.executemany(
                f"INSERT INTO webscenario_items_review ({column_names}) VALUES ({placeholders})",
                all_values
            )
            inserted = len(all_values)
        conn.commit()
        return jsonify({
            'success': True,
            'message': f'webscenario_items_review 导入成功：删除 {deleted} 条，导入 {inserted} 条'
        })
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': f'导入失败: {str(e)}'}), 500
    finally:
        conn.close()


# ============================================================
# Web触发器复核表管理路由
# ============================================================



@app.route('/web-triggers-review')
def web_triggers_review():
    """Web触发器复核表列表"""
    host = request.args.get('host', '').strip()
    system = request.args.get('system', '').strip()
    subsystem = request.args.get('subsystem', '').strip()
    sync_filter = request.args.get('sync_filter', 'all').strip()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    page, per_page = _safe_pagination(page, per_page)
    offset = (page - 1) * per_page

    conn = get_db_connection()
    with conn.cursor(cursor_factory=DictCursor) as cur:
        where_parts = []
        params = []
        if host:
            where_parts.append("host ILIKE %s")
            params.append(f'%{host}%')
        if system:
            where_parts.append("system ILIKE %s")
            params.append(f'%{system}%')
        if subsystem:
            where_parts.append("subsystem ILIKE %s")
            params.append(f'%{subsystem}%')
        if sync_filter == 'pending':
            where_parts.append("(sync_status != 'synced' OR sync_status IS NULL)")
        where_clause = (" WHERE " + " AND ".join(where_parts)) if where_parts else ""

        cur.execute(f"SELECT COUNT(*) FROM web_trigger_review{where_clause}", params)
        total = cur.fetchone()['count']
        cur.execute(f"SELECT * FROM web_trigger_review{where_clause} ORDER BY id LIMIT %s OFFSET %s",
                    params + [per_page, offset])
        triggers = cur.fetchall()

        cur.execute("SELECT DISTINCT system FROM web_trigger_review WHERE system IS NOT NULL AND system != '' ORDER BY system")
        distinct_systems = [r['system'] for r in cur.fetchall()]
        cur.execute("SELECT DISTINCT subsystem FROM web_trigger_review WHERE subsystem IS NOT NULL AND subsystem != '' ORDER BY subsystem")
        distinct_subsystems = [r['subsystem'] for r in cur.fetchall()]

    conn.close()

    total_pages = (total + per_page - 1) // per_page
    return render_template('web_triggers_review.html', triggers=triggers,
                           distinct_systems=distinct_systems,
                           distinct_subsystems=distinct_subsystems,
                           sync_filter=sync_filter,
                           page=page, per_page=per_page,
                           total=total, total_pages=total_pages)


@app.route('/web-triggers-review/initialize', methods=['POST'])
@_with_sync_lock
def initialize_web_triggers_review():
    """初始化 web_trigger_review 表：全量清空重建。
    触发器名称动态注入机房对应的 Zabbix Server IP:
      格式: [{zabbix_ip}] Web scenario [{scenario_name}] failed
    """
    room_mapping = _config.get('zabbix_room_mapping', {}) or {}

    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            # 1. 清空复核表
            cur.execute("TRUNCATE web_trigger_review RESTART IDENTITY")

            # 2. 拉取已确认的 Web 场景数据
            cur.execute("""
                SELECT
                    host,
                    name as web_scenario_name,
                    system,
                    subsystem,
                    in_room
                FROM webscenario_items_review
                WHERE confirmed = TRUE
                ORDER BY host, name
            """)
            rows = cur.fetchall()

            if not rows:
                conn.commit()
                return jsonify({'success': True,
                    'message': 'web_trigger_review 初始化完成：无已确认的 Web 场景，表已清空'})

            # 3. 注入机房 IP，构建触发器记录
            from psycopg2.extras import execute_values
            insert_rows = []
            for r in rows:
                room = (r.get('in_room') or '').strip()
                zabbix_ip = room_mapping.get(room) or room_mapping.get(str(room))
                if not zabbix_ip:
                    zabbix_ip = 'Unknown'

                scenario_name = r['web_scenario_name']
                host = r['host']
                trigger_name = f"[{zabbix_ip}] Web scenario [{scenario_name}] failed"
                expression = "{" + f"{host}:web.test.fail[{scenario_name}].count(#3,0,ne)" + "}>2"

                insert_rows.append((
                    host,
                    scenario_name,
                    trigger_name,
                    expression,
                    3,   # priority: warning
                    0,   # status: enabled
                    r.get('system', ''),
                    r.get('subsystem', ''),
                    r.get('in_room', '')
                ))

            # 4. 批量 INSERT
            cols = ['host', 'web_scenario_name', 'trigger_name', 'expression',
                    'priority', 'status', 'system', 'subsystem', 'in_room']
            sql = f"INSERT INTO web_trigger_review ({', '.join(cols)}) VALUES %s"
            execute_values(cur, sql, insert_rows)

        conn.commit()
        return jsonify({
            'success': True,
            'message': f'web_trigger_review 初始化完成：插入 {len(insert_rows)} 条记录'
        })
    except Exception as e:
        conn.rollback()
        app.logger.error(f"Web 触发器复核表初始化失败: {e}")
        return jsonify({'success': False, 'message': f'初始化失败: {str(e)}'}), 500
    finally:
        conn.close()


@app.route('/web-triggers-review/verify', methods=['POST'])
def verify_web_triggers_review():
    """核验 Web 触发器复核表：从 Zabbix 拉取实际状态并与复核表比对"""
    data = request.get_json() if request.is_json else {}
    environment = data.get('environment', '').strip() if data else ''
    ids = data.get('ids', []) if data else []

    if environment not in ZABBIX_ENVIRONMENTS:
        return jsonify({'success': False, 'message': f'无效的环境: {environment}'}), 400

    env_config = ZABBIX_ENVIRONMENTS[environment]
    if not env_config['url']:
        return jsonify({'success': False, 'message': f'环境 "{environment}" 未配置 Zabbix URL'}), 500

    app.logger.info(f"开始执行状态核验逻辑... (table=web_trigger_review, environment={environment})")

    from zabbix_mac import ZabbixClient, StatusVerifier
    client = ZabbixClient(env_config['url'], env_config['username'], env_config['password'])
    if not getattr(client, 'api', None):
        return jsonify({'success': False, 'message': f'无法连接到 {environment} Zabbix API，请检查配置'}), 500

    conn = get_db_connection()
    try:
        # 统计总记录数和已确认记录数
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("SELECT COUNT(*) AS total FROM web_trigger_review")
            total_all = cur.fetchone()['total']
            cur.execute("SELECT COUNT(*) AS total FROM web_trigger_review WHERE confirmed = TRUE")
            total_confirmed = cur.fetchone()['total']
            if ids:
                placeholders = ','.join(['%s'] * len(ids))
                cur.execute(f"SELECT DISTINCT host FROM web_trigger_review WHERE id IN ({placeholders})", ids)
            else:
                cur.execute("SELECT DISTINCT host FROM web_trigger_review WHERE confirmed = TRUE")
            host_names = [r['host'] for r in cur.fetchall()]

        skipped = total_all - total_confirmed

        if not host_names:
            msg = 'web_trigger_review 表中没有已确认的记录，无需核验'
            if skipped > 0:
                msg += f'（{skipped} 条未确认记录已跳过）'
            return jsonify({'success': True, 'message': msg, 'results': {}})

        verifier = StatusVerifier(client, {}, db_conn=conn)
        total = {'verified': 0, 'not_found': 0}
        errors = []
        for host_name in host_names:
            try:
                stats = verifier.verify_web_triggers(host_name)
                total['verified'] += stats['verified']
                total['not_found'] += stats['not_found']
            except Exception as e:
                errors.append(f'{host_name}: {e}')
                app.logger.error(f"主机 {host_name} Web 触发器核验失败: {e}")

        msg = f'Web 触发器核验完成：verified={total["verified"]}, not_found={total["not_found"]}'
        if skipped > 0:
            msg += f'，跳过 {skipped} 条未确认记录'
        if errors:
            msg += f'，{len(errors)} 个主机失败'
        conn.commit()
        app.logger.info(f"核验完成: {msg}")
        conn.rollback()
        return jsonify({
            'success': True,
            'message': msg,
            'results': total,
            'skipped_unconfirmed': skipped,
            'errors': errors[:10] if errors else None
        })
    except Exception as e:
        app.logger.error(f"Web 触发器核验失败: {e}")
        return jsonify({'success': False, 'message': f'核验失败: {str(e)}'}), 500
    finally:
        conn.close()


@app.route('/web-trigger-review/confirm/<int:review_id>', methods=['POST'])
def confirm_web_trigger_review(review_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE web_trigger_review SET confirmed = true, sync_status = 'synced', change_type = NULL, updated_at = CURRENT_TIMESTAMP WHERE id = %s", (review_id,))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@app.route('/web-trigger-review/unconfirm/<int:review_id>', methods=['POST'])
def unconfirm_web_trigger_review(review_id):
    """取消确认Web触发器复核记录（已废弃，前端已移除对应按钮）"""
    logging.warning('DEPRECATED route /web-trigger-review/unconfirm called for review_id=%s', review_id)
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE web_trigger_review SET confirmed = false, sync_status = 'pending_confirm', updated_at = CURRENT_TIMESTAMP WHERE id = %s", (review_id,))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@app.route('/web-trigger-review/add', methods=['POST'])
def add_web_trigger_from_review():
    form = request.form
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO web_trigger_review (host, web_scenario_name, trigger_name, expression,
                                                 priority, status, system, subsystem,
                                                 modified, confirmed, status_verification)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, false, false, 'pending')
            """, (form.get('host'), form.get('web_scenario_name'), form.get('trigger_name'),
                  form.get('expression'), int(form.get('priority', 3)), int(form.get('status', 0)),
                  form.get('system'), form.get('subsystem')))
        conn.commit()
        return jsonify({'success': True, 'message': 'Web触发器添加成功'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@app.route('/web-trigger-review/edit/<int:review_id>', methods=['GET', 'POST'])
def edit_web_trigger_review(review_id):
    conn = get_db_connection()
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute("SELECT * FROM web_trigger_review WHERE id = %s", (review_id,))
        trigger = cur.fetchone()

    if not trigger:
        conn.close()
        flash('记录不存在')
        return redirect(url_for('web_triggers_review'))

    if request.method == 'POST':
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE web_trigger_review SET host=%s, web_scenario_name=%s, trigger_name=%s,
                        expression=%s, priority=%s, status=%s, system=%s, subsystem=%s,
                        modified=true, updated_at=CURRENT_TIMESTAMP
                    WHERE id=%s
                """, (request.form.get('host'), request.form.get('web_scenario_name'),
                      request.form.get('trigger_name'), request.form.get('expression'),
                      int(request.form.get('priority', 3)), int(request.form.get('status', 0)),
                      request.form.get('system'), request.form.get('subsystem'), review_id))
            conn.commit()
            flash('更新成功')
            return redirect(url_for('web_triggers_review'))
        except Exception as e:
            conn.rollback()
            flash(f'更新失败: {e}')
    conn.close()
    return render_template('edit_web_trigger_review.html', trigger=trigger)


@app.route('/web-triggers-review/export')
def export_web_triggers_review():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM web_trigger_review ORDER BY id")
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
        df = pd.DataFrame(rows, columns=columns)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='web_trigger_review')
        output.seek(0)
        return send_file(output, download_name='web_trigger_review.xlsx',
                         mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                         as_attachment=True)
    except Exception as e:
        return jsonify({'success': False, 'message': f'导出失败: {str(e)}'}), 500
    finally:
        conn.close()


@app.route('/web-triggers-review/import', methods=['POST'])
def import_web_triggers_review():
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '未选择文件'}), 400
    file = request.files['file']
    if not file.filename:
        return jsonify({'success': False, 'message': '文件名为空'}), 400
    conn = get_db_connection()
    try:
        df = pd.read_excel(file, engine='openpyxl')
        with conn.cursor() as cur:
            cur.execute("DELETE FROM web_trigger_review")
            deleted = cur.rowcount
            columns = _sanitize_import_columns('web_trigger_review', list(df.columns))
            placeholders = ', '.join(['%s'] * len(columns))
            col_names = ', '.join(columns)
            all_values = []
            for _, row in df.iterrows():
                values = []
                for col in columns:
                    val = row[col]
                    if pd.isna(val):
                        values.append(None)
                    else:
                        values.append(val)
                all_values.append(values)
            cur.executemany(f"INSERT INTO web_trigger_review ({col_names}) VALUES ({placeholders})", all_values)
            inserted = len(all_values)
        conn.commit()
        return jsonify({'success': True, 'message': f'导入成功：删除 {deleted} 条，导入 {inserted} 条'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': f'导入失败: {str(e)}'}), 500
    finally:
        conn.close()


@app.route('/item-prototypes-review')
def item_prototypes_review():
    """监控项原型复核表管理"""
    sync_filter = request.args.get('sync_filter', 'all').strip()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    page, per_page = _safe_pagination(page, per_page)
    offset = (page - 1) * per_page

    conn = get_db_connection()
    with conn.cursor(cursor_factory=DictCursor) as cur:
        where_extra = ""
        params = []
        if sync_filter == 'pending':
            where_extra = " WHERE (sync_status != 'synced' OR sync_status IS NULL)"
        cur.execute(f"SELECT COUNT(*) FROM item_prototypes_review ipr{where_extra}", params)
        total = cur.fetchone()['count']
        cur.execute(f"SELECT ipr.*, dr.name AS dr_name, dr.key AS dr_key FROM item_prototypes_review ipr LEFT JOIN discovery_rules dr ON ipr.discovery_rule_id = dr.id{where_extra} ORDER BY ipr.id LIMIT %s OFFSET %s",
                    params + [per_page, offset])
        prototypes = cur.fetchall()
    conn.close()

    total_pages = (total + per_page - 1) // per_page
    return render_template('item_prototypes_review.html', prototypes=prototypes,
                           sync_filter=sync_filter,
                           page=page, per_page=per_page,
                           total=total, total_pages=total_pages)

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

@app.route('/item-prototype-review/confirm/<int:review_id>', methods=['POST'])
def confirm_item_prototype_review(review_id):
    """确认监控项原型复核表记录"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE item_prototypes_review SET confirmed = true, sync_status = 'synced', change_type = NULL, updated_at = CURRENT_TIMESTAMP WHERE id = %s", (review_id,))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

@app.route('/item-prototype-review/unconfirm/<int:review_id>', methods=['POST'])
def unconfirm_item_prototype_review(review_id):
    """取消确认监控项原型复核表记录（已废弃，前端已移除对应按钮）"""
    logging.warning('DEPRECATED route /item-prototype-review/unconfirm called for review_id=%s', review_id)
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE item_prototypes_review SET confirmed = false, sync_status = 'pending_confirm', updated_at = CURRENT_TIMESTAMP WHERE id = %s", (review_id,))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

@app.route('/trigger-prototypes-review')
def trigger_prototypes_review():
    """触发器原型复核表管理"""
    sync_filter = request.args.get('sync_filter', 'all').strip()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    page, per_page = _safe_pagination(page, per_page)
    offset = (page - 1) * per_page

    conn = get_db_connection()
    with conn.cursor(cursor_factory=DictCursor) as cur:
        where_extra = ""
        params = []
        if sync_filter == 'pending':
            where_extra = " WHERE (tpr.sync_status != 'synced' OR tpr.sync_status IS NULL)"
        cur.execute(f"SELECT COUNT(*) FROM trigger_prototypes_review tpr{where_extra}", params)
        total = cur.fetchone()['count']
        cur.execute(f"""SELECT tpr.*, dr.name AS dr_name, dr.key AS dr_key
                        FROM trigger_prototypes_review tpr
                        LEFT JOIN discovery_rules dr ON tpr.discovery_rule_id = dr.id
                        {where_extra} ORDER BY tpr.id LIMIT %s OFFSET %s""",
                    params + [per_page, offset])
        prototypes = cur.fetchall()
    conn.close()

    total_pages = (total + per_page - 1) // per_page
    return render_template('trigger_prototypes_review.html', prototypes=prototypes,
                           sync_filter=sync_filter,
                           page=page, per_page=per_page,
                           total=total, total_pages=total_pages)

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

@app.route('/trigger-prototype-review/confirm/<int:review_id>', methods=['POST'])
def confirm_trigger_prototype_review(review_id):
    """确认触发器原型复核表记录"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE trigger_prototypes_review SET confirmed = true, sync_status = 'synced', change_type = NULL, updated_at = CURRENT_TIMESTAMP WHERE id = %s", (review_id,))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

@app.route('/trigger-prototype-review/unconfirm/<int:review_id>', methods=['POST'])
def unconfirm_trigger_prototype_review(review_id):
    """取消确认触发器原型复核表记录（已废弃，前端已移除对应按钮）"""
    logging.warning('DEPRECATED route /trigger-prototype-review/unconfirm called for review_id=%s', review_id)
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE trigger_prototypes_review SET confirmed = false, sync_status = 'pending_confirm', updated_at = CURRENT_TIMESTAMP WHERE id = %s", (review_id,))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@app.route('/item-prototypes-review/initialize', methods=['POST'])
@_with_sync_lock
def initialize_item_prototypes_review():
    """初始化 item_prototypes_review 表：基于 Diff 算法增量更新"""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            # 1. 获取现有记录
            cur.execute("SELECT * FROM item_prototypes_review")
            existing_rows = cur.fetchall()

            # 2. 获取上游最新数据
            cur.execute("""
                SELECT
                    ip.id as item_prototype_id,
                    ip.discovery_rule_id,
                    h.name as host_ip,
                    ip.name, ip.key, ip.value_type, ip.delay,
                    ip.description, ip.units, ip.multiplier, ip.delta, ip.history, ip.trends,
                    ip.status, h.system, h.subsystem, h.in_room
                FROM item_prototypes ip
                CROSS JOIN hosts h
                JOIN discovery_rules dr ON ip.discovery_rule_id = dr.id
                WHERE dr.template_name = %s AND h.template_id = dr.template_name
                ORDER BY ip.id, h.name
            """, (app.config['DEFAULT_TEMPLATE_NAME'],))
            new_rows = cur.fetchall()

            all_insert_cols = [
                'item_prototype_id', 'discovery_rule_id', 'host_ip', 'name', 'key',
                'value_type', 'delay', 'description', 'units', 'multiplier', 'delta',
                'history', 'trends', 'status', 'system', 'subsystem', 'in_room'
            ]
            content_columns = [
                'name', 'key', 'value_type', 'delay', 'description', 'units',
                'multiplier', 'delta', 'history', 'trends', 'status', 'system', 'subsystem', 'in_room'
            ]
            unique_keys = ['item_prototype_id', 'host_ip']

            result = _diff_and_merge(
                cur, 'item_prototypes_review', unique_keys, content_columns,
                new_rows, existing_rows, all_insert_cols
            )
        conn.commit()
        return jsonify({
            'success': True,
            'message': f'item_prototypes_review 表 Diff 完成：新增 {result["new"]} 条，变更 {result["update"]} 条，标记删除 {result["delete"]} 条，无变化 {result["unchanged"]} 条'
        })
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': f'初始化失败: {str(e)}'}), 500
    finally:
        conn.close()


@app.route('/item-prototypes-review/export')
def export_item_prototypes_review():
    """导出 item_prototypes_review 表到 Excel 文件"""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("SELECT * FROM item_prototypes_review ORDER BY host_ip, key")
            rows = cur.fetchall()
        if not rows:
            return jsonify({'success': False, 'message': 'item_prototypes_review 表为空'}), 400

        df = pd.DataFrame([dict(r) for r in rows])
        tmp = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
        df.to_excel(tmp.name, index=False, engine='openpyxl')
        tmp.close()

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return send_file(tmp.name, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                         as_attachment=True, download_name=f'item_prototypes_review_{timestamp}.xlsx')
    except Exception as e:
        return jsonify({'success': False, 'message': f'导出失败: {str(e)}'}), 500
    finally:
        conn.close()


@app.route('/item-prototypes-review/import', methods=['POST'])
def import_item_prototypes_review():
    """从 Excel 文件导入数据到 item_prototypes_review 表（清空后写入）"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '未选择文件'}), 400

    file = request.files['file']
    if not file.filename:
        return jsonify({'success': False, 'message': '文件名为空'}), 400

    conn = get_db_connection()
    try:
        df = pd.read_excel(file, engine='openpyxl')

        with conn.cursor() as cur:
            cur.execute("DELETE FROM item_prototypes_review")
            deleted = cur.rowcount

            columns = _sanitize_import_columns('item_prototypes_review', list(df.columns))
            placeholders = ', '.join(['%s'] * len(columns))
            column_names = ', '.join(columns)
            all_values = []
            for _, row in df.iterrows():
                values = []
                for col in columns:
                    val = row[col]
                    if pd.isna(val):
                        values.append(None)
                    elif isinstance(val, str) and (val.startswith('{') or val.startswith('[')):
                        try:
                            values.append(json.dumps(ast.literal_eval(val)))
                        except (ValueError, SyntaxError):
                            values.append(val)
                    else:
                        values.append(val)
                all_values.append(values)
            cur.executemany(
                f"INSERT INTO item_prototypes_review ({column_names}) VALUES ({placeholders})",
                all_values
            )
            inserted = len(all_values)
        conn.commit()
        return jsonify({
            'success': True,
            'message': f'item_prototypes_review 导入成功：删除 {deleted} 条，导入 {inserted} 条'
        })
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': f'导入失败: {str(e)}'}), 500
    finally:
        conn.close()


@app.route('/trigger-prototypes-review/initialize', methods=['POST'])
@_with_sync_lock
def initialize_trigger_prototypes_review():
    """初始化 trigger_prototypes_review 表：基于 Diff 算法增量更新"""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            # 1. 获取现有记录
            cur.execute("SELECT * FROM trigger_prototypes_review")
            existing_rows = cur.fetchall()

            # 2. 获取上游最新数据
            cur.execute("""
                SELECT
                    tp.id as trigger_prototype_id,
                    tp.discovery_rule_id,
                    h.name as host_ip,
                    tp.description,
                    REPLACE(tp.expression, '{host:', '{' || h.name || ':') as expression,
                    tp.priority, tp.status, h.system, h.subsystem, h.in_room
                FROM trigger_prototypes tp
                CROSS JOIN hosts h
                JOIN discovery_rules dr ON tp.discovery_rule_id = dr.id
                WHERE dr.template_name = %s AND h.template_id = dr.template_name
                ORDER BY tp.id, h.name
            """, (app.config['DEFAULT_TEMPLATE_NAME'],))
            new_rows = cur.fetchall()

            all_insert_cols = [
                'trigger_prototype_id', 'discovery_rule_id', 'host_ip', 'description',
                'expression', 'priority', 'status', 'system', 'subsystem', 'in_room'
            ]
            content_columns = [
                'description', 'expression', 'priority', 'status', 'system', 'subsystem', 'in_room'
            ]
            unique_keys = ['trigger_prototype_id', 'host_ip']

            result = _diff_and_merge(
                cur, 'trigger_prototypes_review', unique_keys, content_columns,
                new_rows, existing_rows, all_insert_cols
            )
        conn.commit()
        return jsonify({
            'success': True,
            'message': f'trigger_prototypes_review 表 Diff 完成：新增 {result["new"]} 条，变更 {result["update"]} 条，标记删除 {result["delete"]} 条，无变化 {result["unchanged"]} 条'
        })
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': f'初始化失败: {str(e)}'}), 500
    finally:
        conn.close()


@app.route('/trigger-prototypes-review/export')
def export_trigger_prototypes_review():
    """导出 trigger_prototypes_review 表到 Excel 文件"""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("SELECT * FROM trigger_prototypes_review ORDER BY host_ip, description")
            rows = cur.fetchall()
        if not rows:
            return jsonify({'success': False, 'message': 'trigger_prototypes_review 表为空'}), 400

        df = pd.DataFrame([dict(r) for r in rows])
        tmp = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
        df.to_excel(tmp.name, index=False, engine='openpyxl')
        tmp.close()

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return send_file(tmp.name, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                         as_attachment=True, download_name=f'trigger_prototypes_review_{timestamp}.xlsx')
    except Exception as e:
        return jsonify({'success': False, 'message': f'导出失败: {str(e)}'}), 500
    finally:
        conn.close()


@app.route('/trigger-prototypes-review/import', methods=['POST'])
def import_trigger_prototypes_review():
    """从 Excel 文件导入数据到 trigger_prototypes_review 表（清空后写入）"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '未选择文件'}), 400

    file = request.files['file']
    if not file.filename:
        return jsonify({'success': False, 'message': '文件名为空'}), 400

    conn = get_db_connection()
    try:
        df = pd.read_excel(file, engine='openpyxl')

        with conn.cursor() as cur:
            cur.execute("DELETE FROM trigger_prototypes_review")
            deleted = cur.rowcount

            columns = _sanitize_import_columns('trigger_prototypes_review', list(df.columns))
            placeholders = ', '.join(['%s'] * len(columns))
            column_names = ', '.join(columns)
            all_values = []
            for _, row in df.iterrows():
                values = []
                for col in columns:
                    val = row[col]
                    if pd.isna(val):
                        values.append(None)
                    elif isinstance(val, str) and (val.startswith('{') or val.startswith('[')):
                        try:
                            values.append(json.dumps(ast.literal_eval(val)))
                        except (ValueError, SyntaxError):
                            values.append(val)
                    else:
                        values.append(val)
                all_values.append(values)
            cur.executemany(
                f"INSERT INTO trigger_prototypes_review ({column_names}) VALUES ({placeholders})",
                all_values
            )
            inserted = len(all_values)
        conn.commit()
        return jsonify({
            'success': True,
            'message': f'trigger_prototypes_review 导入成功：删除 {deleted} 条，导入 {inserted} 条'
        })
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': f'导入失败: {str(e)}'}), 500
    finally:
        conn.close()


@app.route('/items-review/verify', methods=['POST'])
def verify_items_review():
    """核验 items_review 状态：从 Zabbix 拉取实际监控项并与复核表比对"""
    data = request.get_json()
    environment = data.get('environment', '').strip() if data else ''
    ids = data.get('ids', []) if data else []

    if environment not in ZABBIX_ENVIRONMENTS:
        return jsonify({'success': False, 'message': f'无效的环境: {environment}'}), 400

    env_config = ZABBIX_ENVIRONMENTS[environment]
    if not env_config['url']:
        return jsonify({'success': False, 'message': f'环境 "{environment}" 未配置 Zabbix URL'}), 500

    app.logger.info(f"开始执行状态核验逻辑... (table=items_review, environment={environment})")

    from zabbix_mac import ZabbixClient, StatusVerifier
    client = ZabbixClient(env_config['url'], env_config['username'], env_config['password'])
    if not getattr(client, 'api', None):
        return jsonify({'success': False, 'message': f'无法连接到 {environment} Zabbix API，请检查配置'}), 500

    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            if ids:
                placeholders = ','.join(['%s'] * len(ids))
                cur.execute(f"SELECT DISTINCT host_ip FROM items_review WHERE id IN ({placeholders})", ids)
            else:
                cur.execute("SELECT DISTINCT host_ip FROM items_review")
            host_ips = [r['host_ip'] for r in cur.fetchall()]

        if not host_ips:
            return jsonify({'success': True, 'message': 'items_review 表为空，无需核验', 'results': {}})

        verifier = StatusVerifier(client, {}, db_conn=conn)
        total = {'verified': 0, 'mismatch': 0, 'not_found': 0}
        errors = []
        for host_ip in host_ips:
            try:
                stats = verifier.verify_items(host_ip)
                total['verified'] += stats['verified']
                total['mismatch'] += stats['mismatch']
                total['not_found'] += stats['not_found']
            except Exception as e:
                errors.append(f'{host_ip}: {e}')
                app.logger.error(f"主机 {host_ip} 监控项核验失败: {e}")

        msg = f'监控项核验完成：verified={total["verified"]}, mismatch={total["mismatch"]}, not_found={total["not_found"]}'
        if errors:
            msg += f'，{len(errors)} 个主机失败'
        conn.commit()
        app.logger.info(f"核验完成: {msg}")
        conn.rollback()
        return jsonify({
            'success': True,
            'message': msg,
            'results': total,
            'errors': errors[:10] if errors else None
        })
    except Exception as e:
        app.logger.error(f"监控项核验失败: {e}")
        conn.rollback()
        return jsonify({'success': False, 'message': f'核验失败: {str(e)}'}), 500
    finally:
        conn.close()


@app.route('/triggers-review/verify', methods=['POST'])
def verify_triggers_review():
    """核验 triggers_review 状态：从 Zabbix 拉取实际触发器并与复核表比对"""
    data = request.get_json()
    environment = data.get('environment', '').strip() if data else ''
    ids = data.get('ids', []) if data else []

    if environment not in ZABBIX_ENVIRONMENTS:
        return jsonify({'success': False, 'message': f'无效的环境: {environment}'}), 400

    env_config = ZABBIX_ENVIRONMENTS[environment]
    if not env_config['url']:
        return jsonify({'success': False, 'message': f'环境 "{environment}" 未配置 Zabbix URL'}), 500

    app.logger.info(f"开始执行状态核验逻辑... (table=triggers_review, environment={environment})")

    from zabbix_mac import ZabbixClient, StatusVerifier
    client = ZabbixClient(env_config['url'], env_config['username'], env_config['password'])
    if not getattr(client, 'api', None):
        return jsonify({'success': False, 'message': f'无法连接到 {environment} Zabbix API，请检查配置'}), 500

    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            if ids:
                placeholders = ','.join(['%s'] * len(ids))
                cur.execute(f"SELECT DISTINCT host_ip FROM triggers_review WHERE id IN ({placeholders})", ids)
            else:
                cur.execute("SELECT DISTINCT host_ip FROM triggers_review")
            host_ips = [r['host_ip'] for r in cur.fetchall()]

        if not host_ips:
            return jsonify({'success': True, 'message': 'triggers_review 表为空，无需核验', 'results': {}})

        verifier = StatusVerifier(client, {}, db_conn=conn)
        total = {'verified': 0, 'not_found': 0}
        errors = []
        for host_ip in host_ips:
            try:
                stats = verifier.verify_triggers(host_ip)
                total['verified'] += stats['verified']
                total['not_found'] += stats['not_found']
            except Exception as e:
                errors.append(f'{host_ip}: {e}')
                app.logger.error(f"主机 {host_ip} 触发器核验失败: {e}")

        msg = f'触发器核验完成：verified={total["verified"]}, not_found={total["not_found"]}'
        if errors:
            msg += f'，{len(errors)} 个主机失败'
        conn.commit()
        app.logger.info(f"核验完成: {msg}")
        conn.rollback()
        return jsonify({
            'success': True,
            'message': msg,
            'results': total,
            'errors': errors[:10] if errors else None
        })
    except Exception as e:
        app.logger.error(f"触发器核验失败: {e}")
        conn.rollback()
        return jsonify({'success': False, 'message': f'核验失败: {str(e)}'}), 500
    finally:
        conn.close()


@app.route('/webscenarios-review/verify', methods=['POST'])
def verify_webscenarios_review():
    """核验 webscenario_items_review 状态：从 Zabbix 拉取实际 Web 场景并与复核表比对"""
    data = request.get_json()
    ids = data.get('ids', []) if data else []
    environment = data.get('environment', '').strip() if data else ''

    if environment not in ZABBIX_ENVIRONMENTS:
        return jsonify({'success': False, 'message': f'无效的环境: {environment}'}), 400

    env_config = ZABBIX_ENVIRONMENTS[environment]
    if not env_config['url']:
        return jsonify({'success': False, 'message': f'环境 "{environment}" 未配置 Zabbix URL'}), 500

    app.logger.info(f"开始执行状态核验逻辑... (table=webscenario_items_review, environment={environment})")

    from zabbix_mac import ZabbixClient, StatusVerifier
    client = ZabbixClient(env_config['url'], env_config['username'], env_config['password'])
    if not getattr(client, 'api', None):
        return jsonify({'success': False, 'message': f'无法连接到 {environment} Zabbix API，请检查配置'}), 500

    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            if ids:
                placeholders = ','.join(['%s'] * len(ids))
                cur.execute(f"SELECT DISTINCT host FROM webscenario_items_review WHERE id IN ({placeholders})", ids)
            else:
                cur.execute("SELECT DISTINCT host FROM webscenario_items_review")
            host_names = [r['host'] for r in cur.fetchall()]

        if not host_names:
            return jsonify({'success': True, 'message': 'webscenario_items_review 表为空，无需核验', 'results': {}})

        verifier = StatusVerifier(client, {}, db_conn=conn)
        total = {'verified': 0, 'mismatch': 0, 'not_found': 0}
        errors = []
        for host_name in host_names:
            try:
                stats = verifier.verify_web_scenarios(host_name)
                total['verified'] += stats['verified']
                total['mismatch'] += stats['mismatch']
                total['not_found'] += stats['not_found']
            except Exception as e:
                errors.append(f'{host_name}: {e}')
                app.logger.error(f"主机 {host_name} Web 场景核验失败: {e}")

        msg = f'Web 场景核验完成：verified={total["verified"]}, mismatch={total["mismatch"]}, not_found={total["not_found"]}'
        if errors:
            msg += f'，{len(errors)} 个主机失败'
        conn.commit()
        app.logger.info(f"核验完成: {msg}")
        conn.rollback()
        return jsonify({
            'success': True,
            'message': msg,
            'results': total,
            'errors': errors[:10] if errors else None
        })
    except Exception as e:
        app.logger.error(f"Web 场景核验失败: {e}")
        conn.rollback()
        return jsonify({'success': False, 'message': f'核验失败: {str(e)}'}), 500
    finally:
        conn.close()


@app.route('/item-prototypes-review/verify', methods=['POST'])
def verify_item_prototypes_review():
    """核验 item_prototypes_review 状态：从 Zabbix 拉取实际监控项原型并与复核表比对"""
    data = request.get_json()
    ids = data.get('ids', []) if data else []
    environment = data.get('environment', '').strip() if data else ''

    if environment not in ZABBIX_ENVIRONMENTS:
        return jsonify({'success': False, 'message': f'无效的环境: {environment}'}), 400

    env_config = ZABBIX_ENVIRONMENTS[environment]
    if not env_config['url']:
        return jsonify({'success': False, 'message': f'环境 "{environment}" 未配置 Zabbix URL'}), 500

    app.logger.info(f"开始执行状态核验逻辑... (table=item_prototypes_review, environment={environment})")

    from zabbix_mac import ZabbixClient, StatusVerifier
    client = ZabbixClient(env_config['url'], env_config['username'], env_config['password'])
    if not getattr(client, 'api', None):
        return jsonify({'success': False, 'message': f'无法连接到 {environment} Zabbix API，请检查配置'}), 500

    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            if ids:
                placeholders = ','.join(['%s'] * len(ids))
                cur.execute(f"SELECT DISTINCT host_ip FROM item_prototypes_review WHERE id IN ({placeholders})", ids)
            else:
                cur.execute("SELECT DISTINCT host_ip FROM item_prototypes_review")
            host_ips = [r['host_ip'] for r in cur.fetchall()]

        if not host_ips:
            return jsonify({'success': True, 'message': 'item_prototypes_review 表为空，无需核验', 'results': {}})

        verifier = StatusVerifier(client, {}, db_conn=conn)
        total = {'verified': 0, 'mismatch': 0, 'not_found': 0}
        errors = []
        for host_ip in host_ips:
            try:
                stats = verifier.verify_item_prototypes(host_ip)
                total['verified'] += stats['verified']
                total['mismatch'] += stats['mismatch']
                total['not_found'] += stats['not_found']
            except Exception as e:
                errors.append(f'{host_ip}: {e}')
                app.logger.error(f"主机 {host_ip} 监控项原型核验失败: {e}")

        msg = f'监控项原型核验完成：verified={total["verified"]}, mismatch={total["mismatch"]}, not_found={total["not_found"]}'
        if errors:
            msg += f'，{len(errors)} 个主机失败'
        conn.commit()
        app.logger.info(f"核验完成: {msg}")
        conn.rollback()
        return jsonify({
            'success': True,
            'message': msg,
            'results': total,
            'errors': errors[:10] if errors else None
        })
    except Exception as e:
        app.logger.error(f"监控项原型核验失败: {e}")
        conn.rollback()
        return jsonify({'success': False, 'message': f'核验失败: {str(e)}'}), 500
    finally:
        conn.close()


@app.route('/trigger-prototypes-review/verify', methods=['POST'])
def verify_trigger_prototypes_review():
    """核验 trigger_prototypes_review 状态：从 Zabbix 拉取实际触发器原型并与复核表比对"""
    data = request.get_json()
    ids = data.get('ids', []) if data else []
    environment = data.get('environment', '').strip() if data else ''

    if environment not in ZABBIX_ENVIRONMENTS:
        return jsonify({'success': False, 'message': f'无效的环境: {environment}'}), 400

    env_config = ZABBIX_ENVIRONMENTS[environment]
    if not env_config['url']:
        return jsonify({'success': False, 'message': f'环境 "{environment}" 未配置 Zabbix URL'}), 500

    app.logger.info(f"开始执行状态核验逻辑... (table=trigger_prototypes_review, environment={environment})")

    from zabbix_mac import ZabbixClient, StatusVerifier
    client = ZabbixClient(env_config['url'], env_config['username'], env_config['password'])
    if not getattr(client, 'api', None):
        return jsonify({'success': False, 'message': f'无法连接到 {environment} Zabbix API，请检查配置'}), 500

    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            if ids:
                placeholders = ','.join(['%s'] * len(ids))
                cur.execute(f"SELECT DISTINCT host_ip FROM trigger_prototypes_review WHERE id IN ({placeholders})", ids)
            else:
                cur.execute("SELECT DISTINCT host_ip FROM trigger_prototypes_review")
            host_ips = [r['host_ip'] for r in cur.fetchall()]

        if not host_ips:
            return jsonify({'success': True, 'message': 'trigger_prototypes_review 表为空，无需核验', 'results': {}})

        verifier = StatusVerifier(client, {}, db_conn=conn)
        total = {'verified': 0, 'not_found': 0}
        errors = []
        for host_ip in host_ips:
            try:
                stats = verifier.verify_trigger_prototypes(host_ip)
                total['verified'] += stats['verified']
                total['not_found'] += stats['not_found']
            except Exception as e:
                errors.append(f'{host_ip}: {e}')
                app.logger.error(f"主机 {host_ip} 触发器原型核验失败: {e}")

        msg = f'触发器原型核验完成：verified={total["verified"]}, not_found={total["not_found"]}'
        if errors:
            msg += f'，{len(errors)} 个主机失败'
        conn.commit()
        app.logger.info(f"核验完成: {msg}")
        conn.rollback()
        return jsonify({
            'success': True,
            'message': msg,
            'results': total,
            'errors': errors[:10] if errors else None
        })
    except Exception as e:
        app.logger.error(f"触发器原型核验失败: {e}")
        conn.rollback()
        return jsonify({'success': False, 'message': f'核验失败: {str(e)}'}), 500
    finally:
        conn.close()


# ============================================================
# 自动发现规则管理
# ============================================================

@app.route('/discovery-rules')
def discovery_rules():
    """自动发现规则列表"""
    template = request.args.get('template', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    page, per_page = _safe_pagination(page, per_page)
    offset = (page - 1) * per_page

    conn = get_db_connection()
    with conn.cursor(cursor_factory=DictCursor) as cur:
        where_clause = ""
        where_join = ""
        params = []
        if template:
            where_clause = " WHERE dr.template_name ILIKE %s"
            where_join = " AND dr.template_name ILIKE %s"
            params.append(f'%{template}%')
        cur.execute(f"SELECT COUNT(*) FROM discovery_rules dr{where_clause}", params)
        total = cur.fetchone()['count']
        cur.execute(f"""
            SELECT dr.*,
                   (SELECT COUNT(*) FROM filter_conditions fc WHERE fc.discovery_rule_id = dr.id) as filter_count
            FROM discovery_rules dr
            WHERE 1=1{where_join}
            ORDER BY dr.id LIMIT %s OFFSET %s
        """, params + [per_page, offset])
        rules = cur.fetchall()
    conn.close()

    total_pages = (total + per_page - 1) // per_page
    return render_template('discovery_rules.html', rules=rules,
                           page=page, per_page=per_page,
                           total=total, total_pages=total_pages)


@app.route('/discovery-rules/export')
def export_discovery_rules():
    """导出 discovery_rules 表到 Excel"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM discovery_rules ORDER BY id")
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
        df = pd.DataFrame(rows, columns=columns)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='discovery_rules')
        output.seek(0)
        return send_file(output, download_name='discovery_rules.xlsx',
                         mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                         as_attachment=True)
    except Exception as e:
        return jsonify({'success': False, 'message': f'导出失败: {str(e)}'}), 500
    finally:
        conn.close()


@app.route('/discovery-rules/import', methods=['POST'])
def import_discovery_rules():
    """从 Excel 导入数据到 discovery_rules 表（清空后写入）"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '未选择文件'}), 400
    file = request.files['file']
    if not file.filename:
        return jsonify({'success': False, 'message': '文件名为空'}), 400
    conn = get_db_connection()
    try:
        df = pd.read_excel(file, engine='openpyxl')
        with conn.cursor() as cur:
            cur.execute("DELETE FROM discovery_rules")
            deleted = cur.rowcount
            columns = _sanitize_import_columns('discovery_rules', list(df.columns))
            placeholders = ', '.join(['%s'] * len(columns))
            column_names = ', '.join(columns)
            all_values = []
            for _, row in df.iterrows():
                values = []
                for col in columns:
                    val = row[col]
                    if pd.isna(val):
                        values.append(None)
                    elif isinstance(val, str) and (val.startswith('{') or val.startswith('[')):
                        try:
                            values.append(json.dumps(ast.literal_eval(val)))
                        except (ValueError, SyntaxError):
                            values.append(val)
                    else:
                        values.append(val)
                all_values.append(values)
            cur.executemany(f"INSERT INTO discovery_rules ({column_names}) VALUES ({placeholders})", all_values)
            inserted = len(all_values)
        conn.commit()
        return jsonify({'success': True, 'message': f'discovery_rules 导入成功：删除 {deleted} 条，导入 {inserted} 条'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': f'导入失败: {str(e)}'}), 500
    finally:
        conn.close()


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
    template = request.args.get('template', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    page, per_page = _safe_pagination(page, per_page)
    offset = (page - 1) * per_page

    conn = get_db_connection()
    with conn.cursor(cursor_factory=DictCursor) as cur:
        where_clause = ""
        where_join = ""
        params = []
        if template:
            where_clause = " WHERE dr.template_name ILIKE %s"
            where_join = " AND dr.template_name ILIKE %s"
            params.append(f'%{template}%')
        cur.execute(f"SELECT COUNT(*) FROM filter_conditions fc JOIN discovery_rules dr ON fc.discovery_rule_id = dr.id{where_clause}", params)
        total = cur.fetchone()['count']
        cur.execute(f"""
            SELECT fc.*, dr.name as rule_name, dr.template_name
            FROM filter_conditions fc
            JOIN discovery_rules dr ON fc.discovery_rule_id = dr.id
            {where_join}
            ORDER BY fc.id LIMIT %s OFFSET %s
        """, params + [per_page, offset])
        conditions = cur.fetchall()
    conn.close()

    total_pages = (total + per_page - 1) // per_page
    return render_template('filter_conditions.html', conditions=conditions,
                           page=page, per_page=per_page,
                           total=total, total_pages=total_pages)


@app.route('/filter-conditions/export')
def export_filter_conditions():
    """导出 filter_conditions 表到 Excel"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM filter_conditions ORDER BY id")
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
        df = pd.DataFrame(rows, columns=columns)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='filter_conditions')
        output.seek(0)
        return send_file(output, download_name='filter_conditions.xlsx',
                         mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                         as_attachment=True)
    except Exception as e:
        return jsonify({'success': False, 'message': f'导出失败: {str(e)}'}), 500
    finally:
        conn.close()


@app.route('/filter-conditions/import', methods=['POST'])
def import_filter_conditions():
    """从 Excel 导入数据到 filter_conditions 表（清空后写入）"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '未选择文件'}), 400
    file = request.files['file']
    if not file.filename:
        return jsonify({'success': False, 'message': '文件名为空'}), 400
    conn = get_db_connection()
    try:
        df = pd.read_excel(file, engine='openpyxl')
        with conn.cursor() as cur:
            cur.execute("DELETE FROM filter_conditions")
            deleted = cur.rowcount
            columns = _sanitize_import_columns('filter_conditions', list(df.columns))
            placeholders = ', '.join(['%s'] * len(columns))
            column_names = ', '.join(columns)
            all_values = []
            for _, row in df.iterrows():
                values = []
                for col in columns:
                    val = row[col]
                    if pd.isna(val):
                        values.append(None)
                    elif isinstance(val, str) and (val.startswith('{') or val.startswith('[')):
                        try:
                            values.append(json.dumps(ast.literal_eval(val)))
                        except (ValueError, SyntaxError):
                            values.append(val)
                    else:
                        values.append(val)
                all_values.append(values)
            cur.executemany(f"INSERT INTO filter_conditions ({column_names}) VALUES ({placeholders})", all_values)
            inserted = len(all_values)
        conn.commit()
        return jsonify({'success': True, 'message': f'filter_conditions 导入成功：删除 {deleted} 条，导入 {inserted} 条'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': f'导入失败: {str(e)}'}), 500
    finally:
        conn.close()


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
                "SELECT id, name, template_id, 'host' as type FROM hosts WHERE name ILIKE %s OR template_id ILIKE %s LIMIT 10",
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


# ============================================================
# Batch Sync Preview & Apply API
# ============================================================

_ALLOWED_SYNC_TABLES = {
    'items_review', 'triggers_review', 'web_trigger_review',
    'item_prototypes_review', 'trigger_prototypes_review', 'webscenario_items_review'
}

_ACTION_TYPE_TO_TABLE = {
    'item': 'items_review',
    'trigger': 'triggers_review',
    'webscenario': 'webscenario_items_review',
    'itemprototype': 'item_prototypes_review',
    'triggerprototype': 'trigger_prototypes_review',
}


def _resolve_table(table: str = '', action_type: str = '') -> str:
    """Resolve either table or action_type to an internal table name.
    Backward compatible: existing callers send 'table', new callers send 'action_type'.
    """
    if table:
        return table
    if action_type:
        resolved = _ACTION_TYPE_TO_TABLE.get(action_type)
        if resolved:
            return resolved
        raise ValueError(f'无效的 action_type: {action_type}。'
                         f'支持: item, trigger, webscenario, itemprototype, triggerprototype')
    raise ValueError('请提供 table 或 action_type 参数')


def _parse_trigger_item_keys(expression: str) -> List[str]:
    """Extract item keys from a Zabbix trigger expression.

    Zabbix trigger expressions look like:
      {hostname:item.key[param1,param2].last()}>0
      {hostname:mysql.status[uptime].last()}=0

    Returns a list of unique item key strings, e.g. ['item.key[param1,param2]'].
    """
    if not expression or not isinstance(expression, str):
        return []

    # Match {hostname:item_key.function(params)} patterns
    # The item_key is everything between : and the .function() part
    # Supported Zabbix trigger functions
    func_names = (
        r'last|avg|min|max|sum|count|change|diff|rate|kurtosis|band|prev|'
        r'nodata|date|dayofweek|trendavg|trendmax|trendmin|logeventid|logseverity|logsource|'
        r'forecast|timeleft|abschange|baselinewma|baselineavg|baselinemad|str|strlen|'
        r'regexp|iregexp|fuzzytime|percentile'
    )
    pattern = re.compile(
        r'\{[^}:]+:([^}]+?)\.(?:' + func_names + r')\s*\([^)]*\)\}',
        re.IGNORECASE
    )

    keys = set()
    for match in pattern.finditer(expression):
        key = match.group(1).strip()
        if key:
            keys.add(key)

    return sorted(keys)


def _check_item_exists_in_zabbix(client, host_id: str, item_key: str) -> bool:
    """Check if a specific item key exists on a given host in Zabbix."""
    try:
        items = client.api.item.get(
            hostids=host_id,
            filter={'key_': item_key},
            output=['itemid']
        )
        return len(items) > 0
    except Exception as e:
        app.logger.error(f"查询监控项 {item_key} 失败 (host_id={host_id}): {e}")
        return False


def _batch_check_items_exist(client, host_id: str, keys: list) -> tuple:
    """Batch check if multiple item keys exist on a host. Returns (existing_keys, missing_keys)."""
    if not keys:
        return set(), []
    try:
        # Zabbix API filter supports array for key_ for batch lookup
        items = client.api.item.get(
            hostids=host_id,
            filter={'key_': keys},
            output=['itemid', 'key_']
        )
        existing_keys = {item['key_'] for item in items}
        missing = [k for k in keys if k not in existing_keys]
        return existing_keys, missing
    except Exception as e:
        app.logger.error(f"批量查询监控项失败 (host_id={host_id}): {e}")
        # Fall back to per-key check on batch failure
        existing = set()
        missing = []
        for key in keys:
            if _check_item_exists_in_zabbix(client, host_id, key):
                existing.add(key)
            else:
                missing.append(key)
        return existing, missing


def _validate_trigger_dependencies(client, rows: list, host_col: str):
    """Validate that all item keys referenced in trigger expressions exist in Zabbix.

    Returns:
        (is_valid, error_dict) where error_dict is None if valid,
        or {"success": False, "status": "error", "message": "..."} if invalid.
    """
    # Step 1: Extract item keys per host from trigger expressions
    host_item_keys = {}  # {host: set of item keys}

    for row in rows:
        host = row[host_col]
        expression = row.get('expression', '')
        keys = _parse_trigger_item_keys(expression)
        if host not in host_item_keys:
            host_item_keys[host] = set()
        host_item_keys[host].update(keys)

    # Step 2: For each host, check if ALL referenced item keys exist in Zabbix
    missing_by_host = {}

    for host, keys in host_item_keys.items():
        if not keys:
            continue

        host_id = client.get_host_id(host)
        if not host_id:
            missing_by_host[host] = sorted(keys)
            continue

        # Batch check all keys for this host in one API call
        _, missing_for_host = _batch_check_items_exist(client, host_id, sorted(keys))

        if missing_for_host:
            missing_by_host[host] = sorted(missing_for_host)

    if missing_by_host:
        missing_summary = []
        for host, keys in missing_by_host.items():
            missing_summary.append(f'{host}: [{", ".join(keys)}]')
        msg = (
            f'同步失败：触发器依赖的监控项尚未在 Zabbix 中同步，'
            f'请先去【监控项复核】页面完成该监控项的同步！\n'
            f'缺失详情：{"; ".join(missing_summary)}'
        )
        return False, {'success': False, 'status': 'error', 'message': msg}

    return True, None


def _get_entity_type(table: str) -> str:
    mapping = {
        'items_review': 'Item',
        'triggers_review': 'Trigger',
        'web_trigger_review': 'WebTrigger',
        'item_prototypes_review': 'ItemPrototype',
        'trigger_prototypes_review': 'TriggerPrototype',
        'webscenario_items_review': 'WebScenario',
    }
    return mapping.get(table, table)

def _get_entity_key(table: str, row: dict) -> str:
    key_map = {
        'items_review': 'item_key',
        'triggers_review': 'name',
        'web_trigger_review': 'trigger_name',
        'item_prototypes_review': 'key',
        'trigger_prototypes_review': 'description',
        'webscenario_items_review': 'name',
    }
    col = key_map.get(table, 'id')
    return str(row.get(col, ''))

def _get_entity_name(table: str, row: dict) -> str:
    name_map = {
        'items_review': 'name',
        'triggers_review': 'name',
        'web_trigger_review': 'trigger_name',
        'item_prototypes_review': 'name',
        'trigger_prototypes_review': 'description',
        'webscenario_items_review': 'name',
    }
    col = name_map.get(table, 'name')
    return str(row.get(col, ''))

def _get_host_col(table: str) -> str:
    return 'host' if table in ('webscenario_items_review', 'web_trigger_review') else 'host_ip'


def _normalize_delay(delay: Any) -> str:
    """确保 delay 值为 Zabbix 5.0 合法的非零字符串格式。

    Zabbix 5.0 LLD item prototype 拒绝 delay=0 或空值，
    报错 "Specified update interval is not valid"。
    """
    if not delay or str(delay).strip() in ('', '0', '0s', '0m', '0h'):
        return '60s'
    return str(delay).strip()


def _build_item_data_from_row(row: dict, host_id: str, interface_id: str = None) -> dict:
    """从 items_review 行构建 item_data (匹配 sync_items_to_zabbix 的逻辑)"""
    item_data = {
        'hostid': host_id,
        'key_': row['item_key'],
        'name': row['name'],
        'type': row['type'],
        'value_type': row['value_type'],
        'delay': row['delay'],
    }
    if interface_id:
        item_data['interfaceid'] = interface_id
    if row.get('description'):
        item_data['description'] = row['description']
    if row.get('units'):
        item_data['units'] = row['units']
    if row.get('history'):
        item_data['history'] = f"{row['history']}d"
    if row.get('trends'):
        item_data['trends'] = f"{row['trends']}d"
    if row.get('status'):
        item_data['status'] = row['status']
    if row.get('preprocessing'):
        item_data['preprocessing'] = row['preprocessing']
    return item_data

def _compare_entity(table: str, client, host_id: str, rows: list,
                    changes: list, summary: dict, interface_id: str = None,
                    dr_configs: dict = None):
    """对指定表的一批行与 Zabbix 实际状态做 dry-run 比对"""
    from zabbix_mac import ZabbixAPIException

    if table == 'items_review':
        existing_items = client.get_managed_items(host_id)
        current_map = {it['key_']: it for it in existing_items}
        for row in rows:
            key = row['item_key']
            if row.get('change_type') == 'delete':
                if key in current_map:
                    changes.append({'host': row['host_ip'], 'type': 'Item', 'key': key,
                                    'name': row.get('name', ''), 'action': 'DELETE',
                                    'details': 'Zabbix 中存在但已标记为删除'})
                    summary['delete_count'] += 1
                else:
                    summary['unchanged_count'] += 1
                continue

            item_data = _build_item_data_from_row(row, host_id, interface_id)
            if key not in current_map:
                changes.append({'host': row['host_ip'], 'type': 'Item', 'key': key,
                                'name': row.get('name', ''), 'action': 'CREATE',
                                'details': 'Zabbix 中不存在，将新建'})
                summary['create_count'] += 1
            else:
                target_fp = client.calculate_fingerprint(item_data)
                current_fp = client.calculate_fingerprint(current_map[key])
                if target_fp != current_fp:
                    changes.append({'host': row['host_ip'], 'type': 'Item', 'key': key,
                                    'name': row.get('name', ''), 'action': 'UPDATE',
                                    'details': '配置已变更，将更新'})
                    summary['update_count'] += 1
                else:
                    summary['unchanged_count'] += 1

    elif table == 'triggers_review':
        existing_triggers = client.get_managed_triggers(host_id)
        current_map = {t['description']: t for t in existing_triggers}
        for row in rows:
            name = row['name']
            if row.get('change_type') == 'delete':
                if name in current_map:
                    changes.append({'host': row['host_ip'], 'type': 'Trigger', 'key': name,
                                    'name': name, 'action': 'DELETE',
                                    'details': 'Zabbix 中存在但已标记为删除'})
                    summary['delete_count'] += 1
                else:
                    summary['unchanged_count'] += 1
                continue

            trigger_data = {
                'description': name,
                'expression': row.get('expression', ''),
                'priority': int(row.get('priority', 0)),
            }
            if name not in current_map:
                changes.append({'host': row['host_ip'], 'type': 'Trigger', 'key': name,
                                'name': name, 'action': 'CREATE',
                                'details': 'Zabbix 中不存在，将新建'})
                summary['create_count'] += 1
            else:
                target_fp = client.calculate_fingerprint(trigger_data)
                current_fp = client.calculate_fingerprint(current_map[name])
                if target_fp != current_fp:
                    changes.append({'host': row['host_ip'], 'type': 'Trigger', 'key': name,
                                    'name': name, 'action': 'UPDATE',
                                    'details': '配置已变更，将更新'})
                    summary['update_count'] += 1
                else:
                    summary['unchanged_count'] += 1

    elif table == 'web_trigger_review':
        try:
            zabbix_triggers = client.api.trigger.get({
                'hostids': host_id,
                'output': ['triggerid', 'description'],
            })
            zabbix_names = {t['description'] for t in zabbix_triggers}
        except Exception as e:
            app.logger.error(f"compare_entity fetch failed: {e}"); zabbix_names = set()
        for row in rows:
            tname = row['trigger_name']
            if tname in zabbix_names:
                summary['unchanged_count'] += 1
            else:
                changes.append({'host': row['host'], 'type': 'WebTrigger', 'key': tname,
                                'name': tname, 'action': 'CREATE',
                                'details': 'Zabbix 中不存在，将新建'})
                summary['create_count'] += 1

    elif table == 'item_prototypes_review':
        # 从本地 discovery_rules 获取 dr_key（替代原来不可用的 row.dr_key）
        dr_configs = dr_configs or {}
        try:
            zabbix_rules = client.api.discoveryrule.get({
                'hostids': host_id,
                'output': ['itemid', 'key_'],
            })
        except Exception as e:
            app.logger.error(f"compare_entity fetch rules failed: {e}"); zabbix_rules = []
        for row in rows:
            dr_id = int(row.get('discovery_rule_id', 0))
            dr_cfg = dr_configs.get(dr_id, {})
            dr_key = dr_cfg.get('key', '')
            if not dr_key:
                changes.append({'host': row['host_ip'], 'type': 'ItemPrototype',
                                'key': row.get('key', ''),
                                'name': row.get('name', ''), 'action': 'CREATE',
                                'details': '本地未找到关联的发现规则配置，将新建 LLD 规则后下发'})
                summary['create_count'] += 1
                continue
            rule = next((r for r in zabbix_rules if r['key_'] == dr_key), None)
            if not rule:
                changes.append({'host': row['host_ip'], 'type': 'ItemPrototype',
                                'key': row.get('key', ''),
                                'name': row.get('name', ''), 'action': 'CREATE',
                                'details': f'LLD 规则 {dr_key} 不存在，将自动创建后下发'})
                summary['create_count'] += 1
                continue
            try:
                existing_protos = client.get_item_prototypes(rule['itemid'])
                proto_map = {p['key_']: p for p in existing_protos}
            except Exception as e:
                app.logger.error(f"compare_entity itemprototype fetch failed: {e}"); proto_map = {}
            key = row.get('key', '')
            if key not in proto_map:
                changes.append({'host': row['host_ip'], 'type': 'ItemPrototype', 'key': key,
                                'name': row.get('name', ''), 'action': 'CREATE',
                                'details': 'Zabbix 中不存在，将新建'})
                summary['create_count'] += 1
            else:
                summary['unchanged_count'] += 1

    elif table == 'trigger_prototypes_review':
        dr_configs = dr_configs or {}
        try:
            zabbix_rules = client.api.discoveryrule.get({
                'hostids': host_id,
                'output': ['itemid', 'key_'],
            })
        except Exception as e:
            app.logger.error(f"compare_entity fetch rules failed: {e}"); zabbix_rules = []
        for row in rows:
            dr_id = int(row.get('discovery_rule_id', 0))
            dr_cfg = dr_configs.get(dr_id, {})
            dr_key = dr_cfg.get('key', '')
            if not dr_key:
                changes.append({'host': row['host_ip'], 'type': 'TriggerPrototype',
                                'key': row.get('description', ''),
                                'name': row.get('description', ''), 'action': 'CREATE',
                                'details': '本地未找到关联的发现规则配置，将新建 LLD 规则后下发'})
                summary['create_count'] += 1
                continue
            rule = next((r for r in zabbix_rules if r['key_'] == dr_key), None)
            if not rule:
                changes.append({'host': row['host_ip'], 'type': 'TriggerPrototype',
                                'key': row.get('description', ''),
                                'name': row.get('description', ''), 'action': 'CREATE',
                                'details': f'LLD 规则 {dr_key} 不存在，将自动创建后下发'})
                summary['create_count'] += 1
                continue
            try:
                existing_tprotos = client.get_trigger_prototypes(rule['itemid'])
                tproto_map = {t['description']: t for t in existing_tprotos}
            except Exception as e:
                app.logger.error(f"compare_entity triggerprototype fetch failed: {e}"); tproto_map = {}
            desc = row.get('description', '')
            if desc not in tproto_map:
                changes.append({'host': row['host_ip'], 'type': 'TriggerPrototype', 'key': desc,
                                'name': desc, 'action': 'CREATE',
                                'details': 'Zabbix 中不存在，将新建'})
                summary['create_count'] += 1
            else:
                summary['unchanged_count'] += 1

    elif table == 'webscenario_items_review':
        try:
            existing_scenarios = client.api.httptest.get({
                'hostids': host_id,
                'output': ['httptestid', 'name', 'url'],
            })
            scenario_map = {s['name']: s for s in existing_scenarios}
        except Exception as e:
            app.logger.error(f"compare_entity webscenario fetch failed: {e}"); scenario_map = {}
        for row in rows:
            name = row.get('name', '')
            url = row.get('url', '')
            if name not in scenario_map:
                changes.append({'host': row['host'], 'type': 'WebScenario', 'key': name,
                                'name': name, 'action': 'CREATE',
                                'details': f'URL: {url}，Zabbix 中不存在'})
                summary['create_count'] += 1
            else:
                existing = scenario_map[name]
                if existing.get('url', '') != url:
                    changes.append({'host': row['host'], 'type': 'WebScenario', 'key': name,
                                    'name': name, 'action': 'UPDATE',
                                    'details': f'URL 变更: {existing.get("url", "")} -> {url}'})
                    summary['update_count'] += 1
                else:
                    summary['unchanged_count'] += 1


@app.route('/api/sync/preview', methods=['POST'])
def api_sync_preview():
    """预览同步差异：针对指定 ID 列表进行 dry-run 比对"""
    data = request.get_json()
    ids = data.get('ids', []) if data else []
    table = data.get('table', '').strip() if data else ''
    action_type = data.get('action_type', '').strip() if data else ''
    environment = data.get('environment', '').strip() if data else ''

    # Resolve table: prefer explicit table, fall back to action_type mapping
    try:
        table = _resolve_table(table, action_type)
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400

    if table not in _ALLOWED_SYNC_TABLES:
        return jsonify({'success': False, 'message': f'无效的表名: {table}'}), 400
    if not ids or not isinstance(ids, list):
        return jsonify({'success': False, 'message': '请提供有效的 ID 列表'}), 400
    if environment not in ZABBIX_ENVIRONMENTS:
        return jsonify({'success': False, 'message': f'无效的环境: {environment}'}), 400

    env_config = ZABBIX_ENVIRONMENTS[environment]
    if not env_config['url']:
        return jsonify({'success': False, 'message': f'环境 "{environment}" 未配置 Zabbix URL'}), 500

    app.logger.info(f"开始差异预览: table={table}, ids={ids[:20]}..., environment={environment}")

    from zabbix_mac import ZabbixClient
    client = ZabbixClient(env_config['url'], env_config['username'], env_config['password'])
    if not getattr(client, 'api', None):
        return jsonify({'success': False, 'message': f'无法连接到 {environment} Zabbix API，请检查配置'}), 500

    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            placeholders = ','.join(['%s'] * len(ids))
            cur.execute(f"SELECT * FROM {table} WHERE id IN ({placeholders})", ids)
            rows = cur.fetchall()

        if not rows:
            return jsonify({'success': False, 'message': '未找到匹配的记录'}), 404

        # 原型表需要 discovery_rules 配置做 dr_key 查找
        dr_configs = {}
        if table in ('item_prototypes_review', 'trigger_prototypes_review'):
            dr_ids = list({int(r['discovery_rule_id']) for r in rows
                           if r.get('discovery_rule_id')})
            if dr_ids:
                with conn.cursor(cursor_factory=DictCursor) as cur2:
                    cur2.execute(
                        f"SELECT id, name, key, delay, evaltype, status "
                        f"FROM discovery_rules WHERE id IN ({','.join(['%s']*len(dr_ids))})",
                        dr_ids)
                    dr_configs = {r['id']: r for r in cur2.fetchall()}

        host_col = _get_host_col(table)
        hosts = {}
        for row in rows:
            h = row[host_col]
            hosts.setdefault(h, []).append(row)

        changes = []
        summary = {'create_count': 0, 'update_count': 0, 'delete_count': 0, 'unchanged_count': 0}

        for host_key, host_rows in hosts.items():
            host_id = client.get_host_id(host_key)
            interface_id = None
            if host_id and table in ('items_review', 'item_prototypes_review',
                                      'trigger_prototypes_review'):
                interface_id = client.get_host_interface_id(host_id)

            if not host_id:
                for r in host_rows:
                    changes.append({
                        'host': host_key,
                        'type': _get_entity_type(table),
                        'key': _get_entity_key(table, r),
                        'name': _get_entity_name(table, r),
                        'action': 'CREATE',
                        'details': f'主机 {host_key} 在 Zabbix 中不存在，将新建'
                    })
                    summary['create_count'] += 1
                continue

            _compare_entity(table, client, host_id, host_rows, changes, summary,
                            interface_id=interface_id, dr_configs=dr_configs)

        app.logger.info(f"差异预览完成: {summary}")
        return jsonify({
            'success': True,
            'summary': summary,
            'changes': changes
        })
    except Exception as e:
        app.logger.error(f"差异预览失败: {e}")
        return jsonify({'success': False, 'message': f'预览失败: {str(e)}'}), 500
    finally:
        conn.close()


@app.route('/api/sync/apply', methods=['POST'])
@_with_sync_lock
def api_sync_apply():
    """执行同步：针对指定 ID 列表实际下发到 Zabbix"""
    data = request.get_json()
    ids = data.get('ids', []) if data else []
    table = data.get('table', '').strip() if data else ''
    environment = data.get('environment', '').strip() if data else ''

    if table not in _ALLOWED_SYNC_TABLES:
        return jsonify({'success': False, 'message': f'无效的表名: {table}'}), 400
    if not ids or not isinstance(ids, list):
        return jsonify({'success': False, 'message': '请提供有效的 ID 列表'}), 400
    if environment not in ZABBIX_ENVIRONMENTS:
        return jsonify({'success': False, 'message': f'无效的环境: {environment}'}), 400

    env_config = ZABBIX_ENVIRONMENTS[environment]
    if not env_config['url']:
        return jsonify({'success': False, 'message': f'环境 "{environment}" 未配置 Zabbix URL'}), 500

    app.logger.info(f"开始批量同步: table={table}, ids={ids[:20]}..., environment={environment}")

    from zabbix_mac import ZabbixClient, ZabbixAPIException
    client = ZabbixClient(env_config['url'], env_config['username'], env_config['password'])
    if not getattr(client, 'api', None):
        return jsonify({'success': False, 'message': f'无法连接到 {environment} Zabbix API，请检查配置'}), 500

    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            placeholders = ','.join(['%s'] * len(ids))
            cur.execute(f"SELECT * FROM {table} WHERE id IN ({placeholders})", ids)
            rows = cur.fetchall()

        if not rows:
            return jsonify({'success': False, 'message': '未找到匹配的记录'}), 404

        host_col = _get_host_col(table)
        hosts = {}
        for row in rows:
            h = row[host_col]
            hosts.setdefault(h, []).append(row)

        created = updated = deleted = 0
        errors = []

        for host_key, host_rows in hosts.items():
            try:
                host_id = client.get_host_id(host_key)
                if not host_id:
                    errors.append(f'主机 {host_key} 在 Zabbix 中不存在')
                    continue

                # Get interface_id for tables that need it (items + prototypes)
                interface_id = None
                if table in ('items_review', 'item_prototypes_review',
                             'trigger_prototypes_review'):
                    interface_id = client.get_host_interface_id(host_id)
                    if not interface_id:
                        errors.append(f'主机 {host_key} 无可用接口')
                        continue

                if table == 'items_review':
                    existing_items = client.get_managed_items(host_id)
                    current_map = {it['key_']: it for it in existing_items}

                    # 3-pass: independent first, then dependent
                    independent = []
                    dependent = []
                    for row in host_rows:
                        item_type = int(row.get('type', 0))
                        if item_type in (15, 18) and row.get('master_item'):
                            dependent.append(row)
                        else:
                            independent.append(row)

                    for row in independent:
                        if row.get('change_type') == 'delete':
                            key = row['item_key']
                            if key in current_map:
                                client.delete_item(current_map[key]['itemid'])
                                deleted += 1
                            continue
                        item_data = _build_item_data_from_row(row, host_id, interface_id)
                        key = row['item_key']
                        if key in current_map:
                            if client.calculate_fingerprint(item_data) != client.calculate_fingerprint(current_map[key]):
                                client.update_item(current_map[key]['itemid'], item_data)
                                updated += 1
                        else:
                            item_id = client.create_item(item_data)
                            if item_id:
                                current_map[key] = {'itemid': item_id, 'key_': key}
                                created += 1

                    for row in dependent:
                        if row.get('change_type') == 'delete':
                            key = row['item_key']
                            if key in current_map:
                                client.delete_item(current_map[key]['itemid'])
                                deleted += 1
                            continue
                        item_data = _build_item_data_from_row(row, host_id, interface_id)
                        key = row['item_key']
                        master_key = row.get('master_item', '')
                        if master_key in current_map:
                            item_data['master_itemid'] = current_map[master_key]['itemid']
                        else:
                            errors.append(f'{host_key}/{key}: 主监控项 {master_key} 不存在，跳过')
                            continue
                        if key in current_map:
                            if client.calculate_fingerprint(item_data) != client.calculate_fingerprint(current_map[key]):
                                client.update_item(current_map[key]['itemid'], item_data)
                                updated += 1
                        else:
                            item_id = client.create_item(item_data)
                            if item_id:
                                current_map[key] = {'itemid': item_id, 'key_': key}
                                created += 1

                elif table == 'triggers_review':
                    existing_triggers = client.get_managed_triggers(host_id)
                    current_map = {t['description']: t for t in existing_triggers}
                    for row in host_rows:
                        name = row['name']
                        if row.get('change_type') == 'delete':
                            if name in current_map:
                                client.delete_trigger(current_map[name]['triggerid'])
                                deleted += 1
                            continue
                        trigger_data = {
                            'description': name,
                            'expression': row.get('expression', ''),
                            'priority': int(row.get('priority', 0)),
                        }
                        if name in current_map:
                            if client.calculate_fingerprint(trigger_data) != client.calculate_fingerprint(current_map[name]):
                                client.update_trigger(current_map[name]['triggerid'], trigger_data)
                                updated += 1
                        else:
                            client.create_trigger(trigger_data)
                            created += 1

                elif table == 'web_trigger_review':
                    # Use ZabbixUltimateAutomator for web trigger sync
                    from zabbix_mac import ZabbixUltimateAutomator
                    automator = ZabbixUltimateAutomator(client)
                    for row in host_rows:
                        try:
                            automator.create_web_scenario_triggers(
                                host_name=row['host'],
                                scenario_name=row.get('web_scenario_name', ''),
                                triggers_config=[{
                                    'description': row['trigger_name'],
                                    'expression': row.get('expression', ''),
                                    'priority': int(row.get('priority', 3)),
                                }]
                            )
                            created += 1
                        except Exception as e:
                            errors.append(f'{row["host"]}/{row["trigger_name"]}: {e}')

                elif table == 'item_prototypes_review':
                    # 查询所有涉及的 discovery_rules 配置
                    dr_ids = list({int(r['discovery_rule_id']) for r in host_rows
                                   if r.get('discovery_rule_id')})
                    if dr_ids:
                        dr_placeholders = ','.join(['%s'] * len(dr_ids))
                        cur2 = conn.cursor(cursor_factory=DictCursor)
                        cur2.execute(
                            f"SELECT id, name, key, delay, evaltype, status "
                            f"FROM discovery_rules WHERE id IN ({dr_placeholders})",
                            dr_ids)
                        dr_configs = {r['id']: r for r in cur2.fetchall()}
                        cur2.close()
                    else:
                        dr_configs = {}

                    # 确保每个 LLD 规则存在，然后同步原型
                    for dr_id, dr_rows_iter in itertools.groupby(
                            sorted(host_rows, key=lambda r: r.get('discovery_rule_id', 0)),
                            key=lambda r: r.get('discovery_rule_id', 0)):
                        dr_rows = list(dr_rows_iter)
                        dr_cfg = dr_configs.get(int(dr_id) if dr_id else 0, {})
                        dr_key = dr_cfg.get('key', '')

                        if not dr_key:
                            errors.append(f'{host_key}: 未找到 discovery_rule_id={dr_id} 的配置')
                            continue

                        # 确保 LLD 规则存在
                        try:
                            rule_id = client.ensure_discovery_rule(
                                host_id, dr_key, dr_cfg, interface_id)
                        except ZabbixAPIException as e:
                            errors.append(
                                f'{host_key}/LLD {dr_key}: 规则创建失败 - {e}')
                            continue

                        # 同步监控项原型
                        existing_protos = client.get_item_prototypes(rule_id)
                        current_map = {p['key_']: p for p in existing_protos}
                        target_keys = set()

                        for row in dr_rows:
                            key = row.get('key', '')
                            target_keys.add(key)
                            try:
                                proto_data = {
                                    'ruleid': rule_id, 'hostid': host_id,
                                    'name': row['name'], 'key_': key,
                                    'type': int(row.get('type', 0)),
                                    'value_type': row.get('value_type', 3),
                                    'delay': _normalize_delay(row.get('delay')),
                                }
                                if interface_id:
                                    proto_data['interfaceid'] = interface_id
                                if row.get('description'):
                                    proto_data['description'] = row['description']
                                if row.get('history'):
                                    proto_data['history'] = f"{row['history']}d"
                                if row.get('trends'):
                                    proto_data['trends'] = f"{row['trends']}d"
                                if row.get('status') is not None:
                                    proto_data['status'] = row['status']

                                if key in current_map:
                                    fp_t = client.calculate_fingerprint(proto_data)
                                    fp_c = client.calculate_fingerprint(current_map[key])
                                    if fp_t != fp_c:
                                        client.api.itemprototype.update(
                                            {'itemid': current_map[key]['itemid'], **proto_data})
                                        updated += 1
                                else:
                                    result_id = client.create_item_prototype(proto_data)
                                    if result_id:
                                        current_map[key] = {'itemid': result_id, 'key_': key}
                                        created += 1
                            except ZabbixAPIException as e:
                                errors.append(f'{host_key}/{key}: {e}')

                        # 清理孤儿
                        for key, p in current_map.items():
                            if key not in target_keys:
                                try:
                                    client.api.itemprototype.delete(p['itemid'])
                                    deleted += 1
                                except ZabbixAPIException as e:
                                    errors.append(f'{host_key}/删除原型 {key}: {e}')

                elif table == 'trigger_prototypes_review':
                    # 查询 discovery_rules 配置
                    dr_ids = list({int(r['discovery_rule_id']) for r in host_rows
                                   if r.get('discovery_rule_id')})
                    if dr_ids:
                        dr_placeholders = ','.join(['%s'] * len(dr_ids))
                        cur2 = conn.cursor(cursor_factory=DictCursor)
                        cur2.execute(
                            f"SELECT id, name, key, delay, evaltype, status "
                            f"FROM discovery_rules WHERE id IN ({dr_placeholders})",
                            dr_ids)
                        dr_configs = {r['id']: r for r in cur2.fetchall()}
                        cur2.close()
                    else:
                        dr_configs = {}

                    for dr_id, dr_rows_iter in itertools.groupby(
                            sorted(host_rows, key=lambda r: r.get('discovery_rule_id', 0)),
                            key=lambda r: r.get('discovery_rule_id', 0)):
                        dr_rows = list(dr_rows_iter)
                        dr_cfg = dr_configs.get(int(dr_id) if dr_id else 0, {})
                        dr_key = dr_cfg.get('key', '')

                        if not dr_key:
                            errors.append(f'{host_key}: 未找到 discovery_rule_id={dr_id} 的配置')
                            continue

                        try:
                            rule_id = client.ensure_discovery_rule(
                                host_id, dr_key, dr_cfg, interface_id)
                        except ZabbixAPIException as e:
                            errors.append(
                                f'{host_key}/LLD {dr_key}: 规则创建失败 - {e}')
                            continue

                        existing_tprotos = client.get_trigger_prototypes(rule_id)
                        current_map = {t['description']: t for t in existing_tprotos}
                        target_descs = set()

                        for row in dr_rows:
                            desc = row.get('description', '')
                            target_descs.add(desc)
                            try:
                                tp_data = {
                                    'description': desc,
                                    'expression': row.get('expression', ''),
                                    'priority': int(row.get('priority', 0)),
                                }
                                if row.get('status') is not None:
                                    tp_data['status'] = int(row['status'])

                                if desc in current_map:
                                    fp_t = client.calculate_fingerprint(tp_data)
                                    fp_c = client.calculate_fingerprint(current_map[desc])
                                    if fp_t != fp_c:
                                        tp_data['triggerid'] = current_map[desc]['triggerid']
                                        client.api.triggerprototype.update(tp_data)
                                        updated += 1
                                else:
                                    tp_data['discoveryruleid'] = rule_id
                                    client.create_trigger_prototype(tp_data)
                                    created += 1
                            except ZabbixAPIException as e:
                                errors.append(f'{host_key}/{desc}: {e}')

                        for desc, t in current_map.items():
                            if desc not in target_descs:
                                try:
                                    client.api.triggerprototype.delete(t['triggerid'])
                                    deleted += 1
                                except ZabbixAPIException as e:
                                    errors.append(f'{host_key}/删除触发器原型 {desc}: {e}')

                elif table == 'webscenario_items_review':
                    errors.append(f'{host_key}: Web 场景同步请使用全局"监控同步"功能')
                    continue

            except ZabbixAPIException as e:
                errors.append(f'{host_key}: Zabbix API 错误 - {e}')
            except Exception as e:
                errors.append(f'{host_key}: {e}')

        msg = f'同步至{environment}完成：新建 {created}，更新 {updated}，删除 {deleted}'
        if errors:
            msg += f'，{len(errors)} 个失败'
        app.logger.info(f"批量同步完成: {msg}")
        return jsonify({
            'success': True,
            'message': msg,
            'created': created,
            'updated': updated,
            'deleted': deleted,
            'errors': errors[:10]
        })
    except Exception as e:
        app.logger.error(f"批量同步失败: {e}")
        return jsonify({'success': False, 'message': f'同步失败: {str(e)}'}), 500
    finally:
        conn.close()


@app.route('/api/sync/execute', methods=['POST'])
@_with_sync_lock
def api_sync_execute():
    """分页面独立同步：根据 action_type 执行针对性同步。

    接受 JSON: {action_type: "item"|"trigger"|"webscenario", ids: [...], environment: "..."}

    - action_type='item': 仅同步 items_review 中的监控项（3-pass independent/dependent）
    - action_type='trigger': 先执行严格的依赖项前置校验，通过后方可同步触发器
    - action_type='webscenario': 独立同步 Web 场景配置
    """
    data = request.get_json()
    ids = data.get('ids', []) if data else []
    action_type = data.get('action_type', '').strip() if data else ''
    environment = data.get('environment', '').strip() if data else ''

    if not action_type:
        return jsonify({'success': False, 'message': '请提供 action_type 参数 (item/trigger/webscenario)'}), 400
    if not ids or not isinstance(ids, list):
        return jsonify({'success': False, 'message': '请提供有效的 ID 列表'}), 400
    if environment not in ZABBIX_ENVIRONMENTS:
        return jsonify({'success': False, 'message': f'无效的环境: {environment}'}), 400

    env_config = ZABBIX_ENVIRONMENTS[environment]
    if not env_config['url']:
        return jsonify({'success': False, 'message': f'环境 "{environment}" 未配置 Zabbix URL'}), 500

    try:
        table = _resolve_table(action_type=action_type)
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400

    app.logger.info(f"开始同步执行: action_type={action_type}, table={table}, ids={ids[:20]}..., environment={environment}")

    from zabbix_mac import ZabbixClient, ZabbixAPIException
    client = ZabbixClient(env_config['url'], env_config['username'], env_config['password'])
    if not getattr(client, 'api', None):
        return jsonify({'success': False, 'message': f'无法连接到 {environment} Zabbix API，请检查配置'}), 500

    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            placeholders = ','.join(['%s'] * len(ids))
            cur.execute(f"SELECT * FROM {table} WHERE id IN ({placeholders})", ids)
            rows = cur.fetchall()

        if not rows:
            return jsonify({'success': False, 'message': '未找到匹配的记录'}), 404

        host_col = _get_host_col(table)
        hosts = {}
        for row in rows:
            h = row[host_col]
            hosts.setdefault(h, []).append(row)

        # ========== TRIGGER DEPENDENCY VALIDATION (strict gate) ==========
        if action_type == 'trigger':
            is_valid, error_response = _validate_trigger_dependencies(client, rows, host_col)
            if not is_valid:
                app.logger.warning(f"触发器依赖验证失败: {error_response.get('message', '')}")
                return jsonify(error_response), 400

        # ========== ACTUAL SYNC (reuses apply logic per entity type) ==========
        created = updated = deleted = 0
        errors = []

        for host_key, host_rows in hosts.items():
            try:
                host_id = client.get_host_id(host_key)
                if not host_id:
                    errors.append(f'主机 {host_key} 在 Zabbix 中不存在')
                    continue

                # Get interface_id for tables that need it (items + prototypes)
                interface_id = None
                if table in ('items_review', 'item_prototypes_review',
                             'trigger_prototypes_review'):
                    interface_id = client.get_host_interface_id(host_id)
                    if not interface_id:
                        errors.append(f'主机 {host_key} 无可用接口')
                        continue

                if table == 'items_review':
                    existing_items = client.get_managed_items(host_id)
                    current_map = {it['key_']: it for it in existing_items}

                    # 3-pass: independent first, then dependent
                    independent = []
                    dependent = []
                    for row in host_rows:
                        item_type = int(row.get('type', 0))
                        if item_type in (15, 18) and row.get('master_item'):
                            dependent.append(row)
                        else:
                            independent.append(row)

                    for row in independent:
                        if row.get('change_type') == 'delete':
                            key = row['item_key']
                            if key in current_map:
                                client.delete_item(current_map[key]['itemid'])
                                deleted += 1
                            continue
                        item_data = _build_item_data_from_row(row, host_id, interface_id)
                        key = row['item_key']
                        if key in current_map:
                            if client.calculate_fingerprint(item_data) != client.calculate_fingerprint(current_map[key]):
                                client.update_item(current_map[key]['itemid'], item_data)
                                updated += 1
                        else:
                            item_id = client.create_item(item_data)
                            if item_id:
                                current_map[key] = {'itemid': item_id, 'key_': key}
                                created += 1

                    for row in dependent:
                        if row.get('change_type') == 'delete':
                            key = row['item_key']
                            if key in current_map:
                                client.delete_item(current_map[key]['itemid'])
                                deleted += 1
                            continue
                        item_data = _build_item_data_from_row(row, host_id, interface_id)
                        key = row['item_key']
                        master_key = row.get('master_item', '')
                        if master_key in current_map:
                            item_data['master_itemid'] = current_map[master_key]['itemid']
                        else:
                            errors.append(f'{host_key}/{key}: 主监控项 {master_key} 不存在，跳过')
                            continue
                        if key in current_map:
                            if client.calculate_fingerprint(item_data) != client.calculate_fingerprint(current_map[key]):
                                client.update_item(current_map[key]['itemid'], item_data)
                                updated += 1
                        else:
                            item_id = client.create_item(item_data)
                            if item_id:
                                current_map[key] = {'itemid': item_id, 'key_': key}
                                created += 1

                elif table == 'triggers_review':
                    existing_triggers = client.get_managed_triggers(host_id)
                    current_map = {t['description']: t for t in existing_triggers}
                    for row in host_rows:
                        name = row['name']
                        if row.get('change_type') == 'delete':
                            if name in current_map:
                                client.delete_trigger(current_map[name]['triggerid'])
                                deleted += 1
                            continue
                        trigger_data = {
                            'description': name,
                            'expression': row.get('expression', ''),
                            'priority': int(row.get('priority', 0)),
                        }
                        if name in current_map:
                            if client.calculate_fingerprint(trigger_data) != client.calculate_fingerprint(current_map[name]):
                                client.update_trigger(current_map[name]['triggerid'], trigger_data)
                                updated += 1
                        else:
                            client.create_trigger(trigger_data)
                            created += 1

                elif table == 'web_trigger_review':
                    from zabbix_mac import ZabbixUltimateAutomator
                    automator = ZabbixUltimateAutomator(client)
                    for row in host_rows:
                        try:
                            automator.create_web_scenario_triggers(
                                host_name=row['host'],
                                scenario_name=row.get('web_scenario_name', ''),
                                triggers_config=[{
                                    'description': row['trigger_name'],
                                    'expression': row.get('expression', ''),
                                    'priority': int(row.get('priority', 3)),
                                }]
                            )
                            created += 1
                        except Exception as e:
                            errors.append(f'{row["host"]}/{row["trigger_name"]}: {e}')

                elif table == 'webscenario_items_review':
                    existing_scenarios = client.get_managed_web_scenarios(host_id)
                    scenario_map = {s['name']: s for s in existing_scenarios}
                    for row in host_rows:
                        name = row['name']
                        if row.get('change_type') == 'delete':
                            if name in scenario_map:
                                client.delete_web_scenario(scenario_map[name]['httptestid'])
                                deleted += 1
                            continue
                        scenario_data = {
                            'name': name,
                            'hostid': host_id,
                            'url': row.get('url', ''),
                            'status_codes': int(row.get('status_code', 200)),
                            'timeout': '15s',
                        }
                        if name in scenario_map:
                            existing = scenario_map[name]
                            if client.calculate_fingerprint(scenario_data) != client.calculate_fingerprint(existing):
                                client.update_web_scenario(existing['httptestid'], scenario_data)
                                updated += 1
                        else:
                            client.create_web_scenario(scenario_data)
                            created += 1

                elif table == 'item_prototypes_review':
                    dr_ids = list({int(r['discovery_rule_id']) for r in host_rows
                                   if r.get('discovery_rule_id')})
                    if dr_ids:
                        with conn.cursor(cursor_factory=DictCursor) as cur2:
                            cur2.execute(
                                f"SELECT id, name, key, delay, evaltype, status "
                                f"FROM discovery_rules WHERE id IN "
                                f"({','.join(['%s']*len(dr_ids))})", dr_ids)
                            dr_cfgs = {r['id']: r for r in cur2.fetchall()}
                    else:
                        dr_cfgs = {}

                    for dr_id, dr_rows_iter in itertools.groupby(
                            sorted(host_rows, key=lambda r: r.get('discovery_rule_id', 0)),
                            key=lambda r: r.get('discovery_rule_id', 0)):
                        dr_rows = list(dr_rows_iter)
                        dr_cfg = dr_cfgs.get(int(dr_id) if dr_id else 0, {})
                        dr_key = dr_cfg.get('key', '')
                        if not dr_key:
                            errors.append(f'{host_key}: 未找到 discovery_rule_id={dr_id} 的配置')
                            continue
                        try:
                            rule_id = client.ensure_discovery_rule(
                                host_id, dr_key, dr_cfg, interface_id)
                        except ZabbixAPIException as e:
                            errors.append(f'{host_key}/LLD {dr_key}: 规则创建失败 - {e}')
                            continue
                        existing_protos = client.get_item_prototypes(rule_id)
                        current_map = {p['key_']: p for p in existing_protos}
                        target_keys = set()
                        for row in dr_rows:
                            key = row.get('key', '')
                            target_keys.add(key)
                            try:
                                proto_data = {
                                    'ruleid': rule_id, 'hostid': host_id,
                                    'name': row['name'], 'key_': key,
                                    'type': int(row.get('type', 0)),
                                    'value_type': row.get('value_type', 3),
                                    'delay': _normalize_delay(row.get('delay')),
                                }
                                if interface_id:
                                    proto_data['interfaceid'] = interface_id
                                if row.get('description'):
                                    proto_data['description'] = row['description']
                                if row.get('history'):
                                    proto_data['history'] = f"{row['history']}d"
                                if row.get('status') is not None:
                                    proto_data['status'] = row['status']
                                if key in current_map:
                                    fp_t = client.calculate_fingerprint(proto_data)
                                    fp_c = client.calculate_fingerprint(current_map[key])
                                    if fp_t != fp_c:
                                        client.api.itemprototype.update(
                                            {'itemid': current_map[key]['itemid'], **proto_data})
                                        updated += 1
                                else:
                                    result_id = client.create_item_prototype(proto_data)
                                    if result_id:
                                        current_map[key] = {'itemid': result_id, 'key_': key}
                                        created += 1
                            except ZabbixAPIException as e:
                                errors.append(f'{host_key}/{key}: {e}')
                        for key, p in current_map.items():
                            if key not in target_keys:
                                try:
                                    client.api.itemprototype.delete(p['itemid'])
                                    deleted += 1
                                except ZabbixAPIException as e:
                                    errors.append(f'{host_key}/删除原型 {key}: {e}')

                elif table == 'trigger_prototypes_review':
                    dr_ids = list({int(r['discovery_rule_id']) for r in host_rows
                                   if r.get('discovery_rule_id')})
                    if dr_ids:
                        with conn.cursor(cursor_factory=DictCursor) as cur2:
                            cur2.execute(
                                f"SELECT id, name, key, delay, evaltype, status "
                                f"FROM discovery_rules WHERE id IN "
                                f"({','.join(['%s']*len(dr_ids))})", dr_ids)
                            dr_cfgs = {r['id']: r for r in cur2.fetchall()}
                    else:
                        dr_cfgs = {}
                    for dr_id, dr_rows_iter in itertools.groupby(
                            sorted(host_rows, key=lambda r: r.get('discovery_rule_id', 0)),
                            key=lambda r: r.get('discovery_rule_id', 0)):
                        dr_rows = list(dr_rows_iter)
                        dr_cfg = dr_cfgs.get(int(dr_id) if dr_id else 0, {})
                        dr_key = dr_cfg.get('key', '')
                        if not dr_key:
                            errors.append(f'{host_key}: 未找到 discovery_rule_id={dr_id} 的配置')
                            continue
                        try:
                            rule_id = client.ensure_discovery_rule(
                                host_id, dr_key, dr_cfg, interface_id)
                        except ZabbixAPIException as e:
                            errors.append(f'{host_key}/LLD {dr_key}: 规则创建失败 - {e}')
                            continue
                        existing_tprotos = client.get_trigger_prototypes(rule_id)
                        current_map = {t['description']: t for t in existing_tprotos}
                        target_descs = set()
                        for row in dr_rows:
                            desc = row.get('description', '')
                            target_descs.add(desc)
                            try:
                                tp_data = {
                                    'description': desc,
                                    'expression': row.get('expression', ''),
                                    'priority': int(row.get('priority', 0)),
                                }
                                if row.get('status') is not None:
                                    tp_data['status'] = int(row['status'])
                                if desc in current_map:
                                    fp_t = client.calculate_fingerprint(tp_data)
                                    fp_c = client.calculate_fingerprint(current_map[desc])
                                    if fp_t != fp_c:
                                        tp_data['triggerid'] = current_map[desc]['triggerid']
                                        client.api.triggerprototype.update(tp_data)
                                        updated += 1
                                else:
                                    tp_data['discoveryruleid'] = rule_id
                                    client.create_trigger_prototype(tp_data)
                                    created += 1
                            except ZabbixAPIException as e:
                                errors.append(f'{host_key}/{desc}: {e}')
                        for desc, t in current_map.items():
                            if desc not in target_descs:
                                try:
                                    client.api.triggerprototype.delete(t['triggerid'])
                                    deleted += 1
                                except ZabbixAPIException as e:
                                    errors.append(f'{host_key}/删除触发器原型 {desc}: {e}')

                else:
                    errors.append(f'{host_key}: 该类型同步请使用全局"监控同步"功能')
                    continue

            except ZabbixAPIException as e:
                errors.append(f'{host_key}: Zabbix API 错误 - {e}')
            except Exception as e:
                errors.append(f'{host_key}: {e}')

        msg = f'同步至{environment}完成：新建 {created}，更新 {updated}，删除 {deleted}'
        if errors:
            msg += f'，{len(errors)} 个失败'
        app.logger.info(f"同步执行完成: {msg}")
        return jsonify({
            'success': True,
            'message': msg,
            'created': created,
            'updated': updated,
            'deleted': deleted,
            'errors': errors[:10]
        })
    except Exception as e:
        app.logger.error(f"同步执行失败: {e}")
        return jsonify({'success': False, 'message': f'同步失败: {str(e)}'}), 500
    finally:
        conn.close()


if __name__ == '__main__':
    app.run(
        debug=_config['app']['debug'],
        host=_config['app']['host'],
        port=_config['app']['port'],
    )
