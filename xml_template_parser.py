# -*- coding: utf-8 -*-
"""
Zabbix 模板 XML 解析（基础模板配置 → 模板 XML 导入）

将 zabbix_export 结构的模板 XML 解析为与 6 张配置表对应的结构化 dict：
  templates / items / triggers / discovery_rules / filter_conditions
  / item_prototypes / trigger_prototypes

仅使用标准库 xml.etree.ElementTree，不引入新依赖（CLAUDE.md 铁律）。
Zabbix 5.0 XML 导出无命名空间，元素均为裸标签。
"""
import json
import re
import xml.etree.ElementTree as ET

# ---- Zabbix XML 字符串 → DB 数字码映射 ----

# 监控项类型（items.type / discovery_rules 类型；item_prototypes 无 type 列）
ITEM_TYPE_MAP = {
    'ZABBIX_PASSIVE': 0,
    'SNMPV1_AGENT': 1,
    'ZABBIX_TRAP': 2,
    'SIMPLE_CHECK': 3,
    'SNMPV2_AGENT': 4,
    'INTERNAL': 5,
    'SNMPV3_AGENT': 6,
    'ZABBIX_ACTIVE': 7,
    'ZABBIX_AGGREGATE': 8,
    'WEB_ITEM': 9,
    'EXTERNAL': 10,
    'DB_MONITOR': 11,
    'IPMI_AGENT': 12,
    'SSH_AGENT': 13,
    'TELNET_AGENT': 14,
    'CALCULATED': 15,
    'JMX_AGENT': 16,
    'SNMP_TRAP': 17,
    'DEPENDENT': 18,
    'HTTP_AGENT': 19,
    'PROMETHEUS': 20,
    'SCRIPT': 21,
}

# 值类型（items.value_type / item_prototypes.value_type）
VALUE_TYPE_MAP = {
    'FLOAT': 0,
    'CHAR': 1,
    'LOG': 2,
    'UNSIGNED': 3,
    'TEXT': 4,
}

# 触发器优先级（triggers.priority / trigger_prototypes.priority）
PRIORITY_MAP = {
    'NOT_CLASSIFIED': 0,
    'INFORMATION': 1,
    'WARNING': 2,
    'AVERAGE': 3,
    'HIGH': 4,
    'DISASTER': 5,
}

# 状态（0=启用 / 1=禁用）
STATUS_MAP = {
    'ENABLED': 0,
    'DISABLED': 1,
}

# 过滤器评估类型（discovery_rules.evaltype）
EVALTYPE_MAP = {
    'AND_OR': 0,
    'AND': 1,
    'OR': 2,
}

# 预处理类型（items.preprocessing JSONB 中的 type 数字字符串）
PREPROCESSING_TYPE_MAP = {
    'REGSUB': '0',
    'RTRIM': '1',
    'LTRIM': '2',
    'XML_PATH': '3',
    'JSON_PATH': '4',
    'MULTIPLIER': '5',
    'DTRIM': '6',
    'BOOL_TO_DECIMAL': '7',
    'OCTAL_TO_DECIMAL': '8',
    'HEX_TO_DECIMAL': '9',
    'DELTA_VALUE': '10',
    'DELTA_SPEED': '11',
    'CHANGE': '12',
    'CHANGE_PER_SECOND': '13',
    'CUSTOM_MULTIPLIER': '14',
    'CUSTOM_DELTA': '15',
    'CUSTOM_DELTA_PER_SECOND': '16',
    'TO_LOWER': '17',
    'TO_UPPER': '18',
    'TRIM': '19',
    'REGSUB2': '20',
    'JAVASCRIPT': '21',
    'CSV_TO_JSON': '22',
    'STR': '23',
}

# 过滤运算符：旧导出用 REGEX / NOT_REGEX，归一化到 DB 现行值
OPERATOR_NORMALIZE = {
    'REGEX': 'MATCHES_REGEX',
    'NOT_REGEX': 'NOT_MATCHES_REGEX',
}

_DURATION_RE = re.compile(r'^(\d+(?:\.\d+)?)\s*([smhdwMy])$')


# ---- 元素读取辅助 ----

def _text(el, tag, default=None):
    """读取子元素文本（去除首尾空白），不存在返回 default"""
    if el is None:
        return default
    sub = el.find(tag)
    if sub is None or sub.text is None:
        return default
    return sub.text.strip()


def _children(el, tag):
    if el is None:
        return []
    return el.findall(tag)


def _int_field(el, tag, default):
    t = _text(el, tag)
    if t is None or t == '':
        return default
    try:
        return int(t)
    except (ValueError, TypeError):
        return default


def _duration_to_days(text):
    """Zabbix 时长字符串 → 天数整数（history/trends 列为 INTEGER 天）。
    例: 7d→7, 365d→365, 1w→7, 1M→30, 1y→365, 12h→1(四舍五入)。"""
    text = (text or '').strip()
    if not text:
        return None
    m = _DURATION_RE.match(text)
    if not m:
        return None
    val = float(m.group(1))
    unit = m.group(2)
    mult = {'s': 1.0 / 86400, 'm': 1.0 / 1440, 'h': 1.0 / 24,
            'd': 1.0, 'w': 7.0, 'M': 30.0, 'y': 365.0}[unit]
    # 四舍五入取整（round() 为银行家舍入，0.5 → 0，改用 +0.5 实现半上取整）
    return int(val * mult + 0.5)


def _parse_preprocessing(item_el):
    """<preprocessing><step><type>/<params>/<error_handler>...</step></preprocessing> → JSONB 列表"""
    steps = _children(_children(item_el, 'preprocessing')[0] if _children(item_el, 'preprocessing') else None, 'step')
    out = []
    for step in steps:
        type_name = _text(step, 'type')
        code = PREPROCESSING_TYPE_MAP.get(type_name)
        if code is None:
            continue
        out.append({
            'type': code,
            'params': _text(step, 'params', ''),
            'error_handler': _text(step, 'error_handler', '0'),
            'error_handler_params': _text(step, 'error_handler_params', ''),
        })
    return out if out else None


def _parse_master_item(item_el):
    """依赖监控项的 <master_item><key>...</key></master_item> → key 字符串"""
    return _text(_children(item_el, 'master_item')[0] if _children(item_el, 'master_item') else None, 'key')


# ---- 各组件解析 ----

def _parse_condition(cond_el):
    """单个过滤条件 → filter_conditions 行 dict"""
    operator = _text(cond_el, 'operator', 'MATCHES_REGEX')
    operator = OPERATOR_NORMALIZE.get(operator, operator)
    return {
        'macro': _text(cond_el, 'macro', ''),
        'value': _text(cond_el, 'value', ''),
        'operator': operator,
    }


def _parse_item(item_el, template_name):
    """监控项 → items 行 dict"""
    item = {
        'item_key': _text(item_el, 'key'),
        'name': _text(item_el, 'name'),
        'type': ITEM_TYPE_MAP.get(_text(item_el, 'type'), 0),
        'value_type': VALUE_TYPE_MAP.get(_text(item_el, 'value_type'), 0),
        'delay': _text(item_el, 'delay', '1m'),
        'description': _text(item_el, 'description', ''),
        'units': _text(item_el, 'units', ''),
        'multiplier': _int_field(item_el, 'multiplier', 0),
        'delta': _int_field(item_el, 'delta', 0),
        'history': _duration_to_days(_text(item_el, 'history')),
        'trends': _duration_to_days(_text(item_el, 'trends')),
        'status': STATUS_MAP.get(_text(item_el, 'status', 'ENABLED'), 0),
        'template_name': template_name,
        'master_item': _parse_master_item(item_el),
    }
    preprocessing = _parse_preprocessing(item_el)
    if preprocessing:
        item['preprocessing'] = json.dumps(preprocessing, ensure_ascii=False)
    return item


def _parse_trigger(trig_el, template_name):
    """触发器 → triggers 行 dict"""
    return {
        'name': _text(trig_el, 'name'),
        'expression': _text(trig_el, 'expression'),
        'priority': PRIORITY_MAP.get(_text(trig_el, 'priority', 'NOT_CLASSIFIED'), 0),
        'description': _text(trig_el, 'description', ''),
        'status': STATUS_MAP.get(_text(trig_el, 'status', 'ENABLED'), 0),
        'template_name': template_name,
    }


def _parse_item_prototype(ip_el):
    """监控项原型 → item_prototypes 行 dict（live 表无 type 列）"""
    return {
        'name': _text(ip_el, 'name'),
        'key': _text(ip_el, 'key'),
        'value_type': VALUE_TYPE_MAP.get(_text(ip_el, 'value_type'), 0),
        'delay': _text(ip_el, 'delay', '1m'),
        'description': _text(ip_el, 'description', ''),
        'units': _text(ip_el, 'units', ''),
        'multiplier': _int_field(ip_el, 'multiplier', 0),
        'delta': _int_field(ip_el, 'delta', 0),
        'history': _duration_to_days(_text(ip_el, 'history')),
        'trends': _duration_to_days(_text(ip_el, 'trends')),
        'status': STATUS_MAP.get(_text(ip_el, 'status', 'ENABLED'), 0),
    }


def _parse_trigger_prototype(tp_el):
    """触发器原型 → trigger_prototypes 行 dict（live 表用 description 存名称）"""
    return {
        'description': _text(tp_el, 'name'),
        'expression': _text(tp_el, 'expression'),
        'priority': PRIORITY_MAP.get(_text(tp_el, 'priority', 'NOT_CLASSIFIED'), 0),
        'status': STATUS_MAP.get(_text(tp_el, 'status', 'ENABLED'), 0),
    }


def _children_under(el, wrapper_tag, item_tag):
    """取 wrapper 元素（如 <items>）下的 item 元素（如 <item>）列表。
    Zabbix 导出结构为 <items><item/></items>，wrapper 本身不可直接作为条目解析。"""
    if el is None:
        return []
    wrapper = el.find(wrapper_tag)
    if wrapper is None:
        return []
    return wrapper.findall(item_tag)


def _parse_discovery_rule(dr_el, template_name):
    """自动发现规则 → {rule, filter, item_prototypes, trigger_prototypes}"""
    filter_el = dr_el.find('filter')
    rule = {
        'name': _text(dr_el, 'name'),
        'key': _text(dr_el, 'key'),
        'delay': _text(dr_el, 'delay', '1h'),
        'evaltype': EVALTYPE_MAP.get(_text(filter_el, 'evaltype', 'AND_OR'), 0),
        'status': STATUS_MAP.get(_text(dr_el, 'status', 'ENABLED'), 0),
        'template_name': template_name,
    }
    # 过滤条件
    conditions = []
    if filter_el is not None:
        conds_el = filter_el.find('conditions')
        if conds_el is not None:
            for cond_el in conds_el.findall('condition'):
                c = _parse_condition(cond_el)
                if c['macro']:
                    conditions.append(c)
    # 原型
    item_proto_els = _children_under(dr_el, 'item_prototypes', 'item_prototype')
    item_prototypes = [_parse_item_prototype(ip) for ip in item_proto_els]
    trigger_prototypes = [_parse_trigger_prototype(tp)
                          for tp in _children_under(dr_el, 'trigger_prototypes', 'trigger_prototype')]
    # item_prototype 内嵌的触发器原型（与 item 内嵌简单触发器同理）
    for ip_el in item_proto_els:
        tp_wrap = ip_el.find('trigger_prototypes')
        if tp_wrap is not None:
            trigger_prototypes += [_parse_trigger_prototype(t)
                                   for t in tp_wrap.findall('trigger_prototype')]

    return {
        'rule': rule,
        'conditions': conditions,
        'item_prototypes': item_prototypes,
        'trigger_prototypes': trigger_prototypes,
    }


def _parse_template(tpl_el, template_id=None):
    """单个 <template> → 模板 dict"""
    name = _text(tpl_el, 'name') or _text(tpl_el, 'template')
    if template_id:
        # 强制绑定用户输入的 template_id：作为模板标识 stamp 进所有记录的 template_name
        name = template_id
    if not name:
        raise ValueError('模板缺少名称（<name> 或 <template> 元素缺失）')
    item_els = _children_under(tpl_el, 'items', 'item')
    items = [_parse_item(i, name) for i in item_els]
    # item 内嵌简单触发器（表达式为 {last()}/{min()} 等相对引用，Zabbix 导出放在 <item>/<triggers> 下）
    nested_triggers = []
    for item_el in item_els:
        tr_wrap = item_el.find('triggers')
        if tr_wrap is not None:
            nested_triggers += [_parse_trigger(t, name) for t in tr_wrap.findall('trigger')]
    triggers = [_parse_trigger(t, name) for t in _children_under(tpl_el, 'triggers', 'trigger')]
    triggers += nested_triggers
    template = {
        'template_id': template_id or name,
        'name': name,
        'description': _text(tpl_el, 'description', ''),
        'items': items,
        'triggers': triggers,
        'discovery_rules': [_parse_discovery_rule(dr, name)
                            for dr in _children_under(tpl_el, 'discovery_rules', 'discovery_rule')],
    }
    return template


# ---- 入口 ----

def _resolve_owner(el, default_owner):
    """root 级孤儿元素的归属：优先取 <template> 子元素，否则回退唯一模板名。"""
    ref = el.find('template')
    if ref is not None and ref.text and ref.text.strip():
        return ref.text.strip()
    return default_owner


def _attach_root_sections(root, templates):
    """Zabbix 5.0 导出会把引用关联模板条目的触发器/监控项/发现规则放到根级
    <triggers>/<items>/<discovery_rules>（而非模板内部）。将这些孤儿元素挂到其
    所属模板下，保证计数与落库完整。归属无法确定（多模板且无 <template> 标记）时跳过。"""
    if len(templates) == 1:
        default_owner = templates[0]['name']
    else:
        default_owner = None
    name_to_tpl = {t['name']: t for t in templates}
    sections = (
        ('triggers', 'trigger', _parse_trigger, 'triggers'),
        ('items', 'item', _parse_item, 'items'),
        ('discovery_rules', 'discovery_rule', _parse_discovery_rule, 'discovery_rules'),
    )
    for wrapper_tag, el_tag, parse_fn, list_key in sections:
        wrapper = root.find(wrapper_tag)
        if wrapper is None:
            continue
        for el in wrapper.findall(el_tag):
            owner = _resolve_owner(el, default_owner)
            tpl = name_to_tpl.get(owner)
            if tpl is None:
                continue
            parsed = parse_fn(el, owner)
            if list_key == 'discovery_rules':
                tpl['discovery_rules'].append(parsed)
            else:
                tpl[list_key].append(parsed)


def parse_template_xml(content, template_id=None):
    """解析 Zabbix 模板 XML 内容 → 模板 dict 列表。
    参数: content 为 XML 字符串或字节；template_id 可选，非空时强制作为模板标识
    绑定到所有记录（写入 template_name 列，作为幂等匹配键与 templates 注册表键）。
    抛出 ValueError 表示 XML 结构非法。
    """
    if isinstance(content, bytes):
        content = content.decode('utf-8', errors='replace')
    try:
        root = ET.fromstring(content)
    except ET.ParseError as e:
        raise ValueError(f'XML 解析失败: {e}') from e

    if root.tag != 'zabbix_export':
        raise ValueError(f'不是有效的 Zabbix 导出文件（根元素为 {root.tag}）')
    templates_el = root.find('templates')
    if templates_el is None:
        raise ValueError('导出文件缺少 <templates> 元素')
    templates = [_parse_template(t, template_id) for t in templates_el.findall('template')]
    if not templates:
        raise ValueError('导出文件中没有 <template> 模板')
    _attach_root_sections(root, templates)
    return templates
