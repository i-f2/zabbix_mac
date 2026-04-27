-- 复核表结构设计
-- Zabbix Monitor as Code (MaC) 数据库模式

-- 1. 监控项复核表
CREATE TABLE IF NOT EXISTS items_review (
    id SERIAL PRIMARY KEY,
    host_id INTEGER NOT NULL REFERENCES hosts(id) ON DELETE CASCADE,
    item_id INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    item_key VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    type INTEGER NOT NULL,
    value_type INTEGER NOT NULL,
    delay VARCHAR(50) NOT NULL,
    description TEXT,
    units VARCHAR(50),
    multiplier INTEGER DEFAULT 0,
    delta INTEGER DEFAULT 0,
    history INTEGER DEFAULT 7,
    trends INTEGER DEFAULT 365,
    status INTEGER DEFAULT 0,
    template_name VARCHAR(255) NOT NULL,
    system VARCHAR(100),
    subsystem VARCHAR(100),
    -- 复核字段
    modified BOOLEAN DEFAULT FALSE,  -- 修改字段
    confirmed BOOLEAN DEFAULT FALSE,  -- 确认字段
    status_verification VARCHAR(50) DEFAULT 'pending',  -- 状态核验字段
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- 唯一约束
    UNIQUE(host_id, item_id)
);

-- 2. 触发器复核表
CREATE TABLE IF NOT EXISTS triggers_review (
    id SERIAL PRIMARY KEY,
    host_id INTEGER NOT NULL REFERENCES hosts(id) ON DELETE CASCADE,
    trigger_id INTEGER NOT NULL REFERENCES triggers(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    expression TEXT NOT NULL,
    priority INTEGER NOT NULL,
    description TEXT,
    status INTEGER DEFAULT 0,
    template_name VARCHAR(255) NOT NULL,
    system VARCHAR(100),
    subsystem VARCHAR(100),
    -- 复核字段
    modified BOOLEAN DEFAULT FALSE,  -- 修改字段
    confirmed BOOLEAN DEFAULT FALSE,  -- 确认字段
    status_verification VARCHAR(50) DEFAULT 'pending',  -- 状态核验字段
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- 唯一约束
    UNIQUE(host_id, trigger_id)
);

-- 3. 监控项原型复核表
CREATE TABLE IF NOT EXISTS item_prototypes_review (
    id SERIAL PRIMARY KEY,
    host_id INTEGER NOT NULL REFERENCES hosts(id) ON DELETE CASCADE,
    item_prototype_id INTEGER NOT NULL REFERENCES item_prototypes(id) ON DELETE CASCADE,
    discovery_rule_id INTEGER NOT NULL REFERENCES discovery_rules(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    key VARCHAR(255) NOT NULL,
    value_type INTEGER NOT NULL,
    delay VARCHAR(50) NOT NULL,
    description TEXT,
    units VARCHAR(50),
    multiplier INTEGER DEFAULT 0,
    delta INTEGER DEFAULT 0,
    history INTEGER DEFAULT 7,
    trends INTEGER DEFAULT 365,
    status INTEGER DEFAULT 0,
    system VARCHAR(100),
    subsystem VARCHAR(100),
    -- 复核字段
    modified BOOLEAN DEFAULT FALSE,  -- 修改字段
    confirmed BOOLEAN DEFAULT FALSE,  -- 确认字段
    status_verification VARCHAR(50) DEFAULT 'pending',  -- 状态核验字段
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- 唯一约束
    UNIQUE(host_id, item_prototype_id)
);

-- 4. 触发器原型复核表
CREATE TABLE IF NOT EXISTS trigger_prototypes_review (
    id SERIAL PRIMARY KEY,
    host_id INTEGER NOT NULL REFERENCES hosts(id) ON DELETE CASCADE,
    trigger_prototype_id INTEGER NOT NULL REFERENCES trigger_prototypes(id) ON DELETE CASCADE,
    discovery_rule_id INTEGER NOT NULL REFERENCES discovery_rules(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    expression TEXT NOT NULL,
    priority INTEGER NOT NULL,
    status INTEGER DEFAULT 0,
    system VARCHAR(100),
    subsystem VARCHAR(100),
    -- 复核字段
    modified BOOLEAN DEFAULT FALSE,  -- 修改字段
    confirmed BOOLEAN DEFAULT FALSE,  -- 确认字段
    status_verification VARCHAR(50) DEFAULT 'pending',  -- 状态核验字段
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- 唯一约束
    UNIQUE(host_id, trigger_prototype_id)
);

-- 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_items_review_host ON items_review(host_id);
CREATE INDEX IF NOT EXISTS idx_items_review_item ON items_review(item_id);
CREATE INDEX IF NOT EXISTS idx_items_review_confirmed ON items_review(confirmed);

CREATE INDEX IF NOT EXISTS idx_triggers_review_host ON triggers_review(host_id);
CREATE INDEX IF NOT EXISTS idx_triggers_review_trigger ON triggers_review(trigger_id);
CREATE INDEX IF NOT EXISTS idx_triggers_review_confirmed ON triggers_review(confirmed);

CREATE INDEX IF NOT EXISTS idx_item_prototypes_review_host ON item_prototypes_review(host_id);
CREATE INDEX IF NOT EXISTS idx_item_prototypes_review_prototype ON item_prototypes_review(item_prototype_id);
CREATE INDEX IF NOT EXISTS idx_item_prototypes_review_confirmed ON item_prototypes_review(confirmed);

CREATE INDEX IF NOT EXISTS idx_trigger_prototypes_review_host ON trigger_prototypes_review(host_id);
CREATE INDEX IF NOT EXISTS idx_trigger_prototypes_review_prototype ON trigger_prototypes_review(trigger_prototype_id);
CREATE INDEX IF NOT EXISTS idx_trigger_prototypes_review_confirmed ON trigger_prototypes_review(confirmed);

-- 初始化复核表数据
-- 1. 初始化监控项复核表
INSERT INTO items_review (host_id, item_id, item_key, name, type, value_type, delay, description, units, multiplier, delta, history, trends, status, template_name, system, subsystem)
SELECT 
    ht.host_id,
    i.id,
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
    h.system,
    h.subsystem
FROM items i
JOIN templates t ON i.template_name = t.name
JOIN host_templates ht ON t.id = ht.template_id
JOIN hosts h ON ht.host_id = h.id
ON CONFLICT (host_id, item_id) DO NOTHING;

-- 2. 初始化触发器复核表
INSERT INTO triggers_review (host_id, trigger_id, name, expression, priority, description, status, template_name, system, subsystem)
SELECT 
    ht.host_id,
    tr.id,
    tr.name,
    tr.expression,
    tr.priority,
    tr.description,
    tr.status,
    tr.template_name,
    h.system,
    h.subsystem
FROM triggers tr
JOIN templates t ON tr.template_name = t.name
JOIN host_templates ht ON t.id = ht.template_id
JOIN hosts h ON ht.host_id = h.id
ON CONFLICT (host_id, trigger_id) DO NOTHING;

-- 3. 初始化监控项原型复核表
INSERT INTO item_prototypes_review (host_id, item_prototype_id, discovery_rule_id, name, key, value_type, delay, description, units, multiplier, delta, history, trends, status, system, subsystem)
SELECT 
    ht.host_id,
    ip.id,
    ip.discovery_rule_id,
    ip.name,
    ip.key,
    ip.value_type,
    ip.delay,
    ip.description,
    ip.units,
    ip.multiplier,
    ip.delta,
    ip.history,
    ip.trends,
    ip.status,
    h.system,
    h.subsystem
FROM item_prototypes ip
JOIN discovery_rules dr ON ip.discovery_rule_id = dr.id
JOIN templates t ON dr.template_name = t.name
JOIN host_templates ht ON t.id = ht.template_id
JOIN hosts h ON ht.host_id = h.id
ON CONFLICT (host_id, item_prototype_id) DO NOTHING;

-- 4. 初始化触发器原型复核表
INSERT INTO trigger_prototypes_review (host_id, trigger_prototype_id, discovery_rule_id, description, expression, priority, status, system, subsystem)
SELECT 
    ht.host_id,
    tp.id,
    tp.discovery_rule_id,
    tp.description,
    tp.expression,
    tp.priority,
    tp.status,
    h.system,
    h.subsystem
FROM trigger_prototypes tp
JOIN discovery_rules dr ON tp.discovery_rule_id = dr.id
JOIN templates t ON dr.template_name = t.name
JOIN host_templates ht ON t.id = ht.template_id
JOIN hosts h ON ht.host_id = h.id
ON CONFLICT (host_id, trigger_prototype_id) DO NOTHING;

-- 提交事务
COMMIT;