-- PostgreSQL 数据库架构更新脚本
-- 用于实现用户需求中的数据库更改

-- 1. 为主机表添加模板名称字段
ALTER TABLE mac_hosts ADD COLUMN IF NOT EXISTS template_name VARCHAR(255);

-- 2. 为监控项原型表和触发器原型表添加模板名称字段
ALTER TABLE mac_item_prototypes ADD COLUMN IF NOT EXISTS template_name VARCHAR(255);
ALTER TABLE mac_trigger_prototypes ADD COLUMN IF NOT EXISTS template_name VARCHAR(255);

-- 3. 创建 items_extra 表 - 用于存储用户自定义修改的监控项
CREATE TABLE IF NOT EXISTS mac_items_extra (
    id SERIAL PRIMARY KEY,
    host_id INTEGER NOT NULL REFERENCES mac_hosts(id) ON DELETE CASCADE,
    item_key VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    type INTEGER,
    value_type INTEGER,
    delay VARCHAR(50),
    description TEXT,
    units VARCHAR(50),
    multiplier INTEGER,
    delta INTEGER,
    history INTEGER,
    trends INTEGER,
    status INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(host_id, item_key)
);

-- 4. 创建 triggers_extra 表 - 用于存储用户自定义修改的触发器
CREATE TABLE IF NOT EXISTS mac_triggers_extra (
    id SERIAL PRIMARY KEY,
    host_id INTEGER NOT NULL REFERENCES mac_hosts(id) ON DELETE CASCADE,
    trigger_name VARCHAR(255) NOT NULL,
    expression TEXT,
    priority INTEGER,
    description TEXT,
    status INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(host_id, trigger_name)
);

-- 5. 创建 items_total 视图 - 整合所有监控项信息
CREATE OR REPLACE VIEW mac_items_total AS
SELECT 
    h.id AS host_id,
    h.name AS host_name,
    h.template_name,
    -- 模板监控项数据
    mi.id AS template_item_id,
    mi.item_key,
    COALESCE(mie.name, mi.name) AS name,
    COALESCE(mie.type, mi.type) AS type,
    COALESCE(mie.value_type, mi.value_type) AS value_type,
    COALESCE(mie.delay, mi.delay) AS delay,
    COALESCE(mie.description, mi.description) AS description,
    COALESCE(mie.units, mi.units) AS units,
    COALESCE(mie.multiplier, mi.multiplier) AS multiplier,
    COALESCE(mie.delta, mi.delta) AS delta,
    COALESCE(mie.history, mi.history) AS history,
    COALESCE(mie.trends, mi.trends) AS trends,
    COALESCE(mie.status, mi.status) AS status,
    -- 标记是否有用户自定义修改
    CASE WHEN mie.id IS NOT NULL THEN TRUE ELSE FALSE END AS has_custom_modification
FROM mac_hosts h
JOIN mac_host_templates ht ON h.id = ht.host_id
JOIN mac_templates t ON ht.template_id = t.id
JOIN mac_items mi ON t.name = mi.template_name
LEFT JOIN mac_items_extra mie ON h.id = mie.host_id AND mi.item_key = mie.item_key;

-- 6. 创建 triggers_total 视图 - 整合所有触发器信息
CREATE OR REPLACE VIEW mac_triggers_total AS
SELECT 
    h.id AS host_id,
    h.name AS host_name,
    h.template_name,
    -- 模板触发器数据
    mt.id AS template_trigger_id,
    mt.name AS trigger_name,
    COALESCE(mte.expression, mt.expression) AS expression,
    COALESCE(mte.priority, mt.priority) AS priority,
    COALESCE(mte.description, mt.description) AS description,
    COALESCE(mte.status, mt.status) AS status,
    -- 标记是否有用户自定义修改
    CASE WHEN mte.id IS NOT NULL THEN TRUE ELSE FALSE END AS has_custom_modification
FROM mac_hosts h
JOIN mac_host_templates ht ON h.id = ht.host_id
JOIN mac_templates t ON ht.template_id = t.id
JOIN mac_triggers mt ON t.name = mt.template_name
LEFT JOIN mac_triggers_extra mte ON h.id = mte.host_id AND mt.name = mte.trigger_name;

-- 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_mac_items_extra_host ON mac_items_extra(host_id);
CREATE INDEX IF NOT EXISTS idx_mac_items_extra_key ON mac_items_extra(item_key);
CREATE INDEX IF NOT EXISTS idx_mac_triggers_extra_host ON mac_triggers_extra(host_id);
CREATE INDEX IF NOT EXISTS idx_mac_triggers_extra_name ON mac_triggers_extra(trigger_name);

-- 更新已有的主机数据，设置默认模板名称为 "21001"
UPDATE mac_hosts SET template_name = '21001' WHERE template_name IS NULL;

-- 更新已有的监控项原型和触发器原型，设置模板名称
UPDATE mac_item_prototypes mip 
SET template_name = (
    SELECT mdr.template_name 
    FROM mac_discovery_rules mdr 
    WHERE mdr.id = mip.discovery_rule_id
)
WHERE mip.template_name IS NULL;

UPDATE mac_trigger_prototypes mtp 
SET template_name = (
    SELECT mdr.template_name 
    FROM mac_discovery_rules mdr 
    WHERE mdr.id = mtp.discovery_rule_id
)
WHERE mtp.template_name IS NULL;

-- 提交事务
COMMIT;
