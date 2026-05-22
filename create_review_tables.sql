-- 复核表结构设计
-- Zabbix Monitor as Code (MaC) 数据库模式

-- 1. 监控项复核表
CREATE TABLE IF NOT EXISTS items_review (
    id SERIAL PRIMARY KEY,
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
    modified BOOLEAN DEFAULT FALSE,
    confirmed BOOLEAN DEFAULT FALSE,
    status_verification VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    host_ip VARCHAR(255) NOT NULL,
    master_item VARCHAR(255),
    preprocessing JSONB,
    system VARCHAR(100),
    subsystem VARCHAR(100)
);

-- 2. 触发器复核表
CREATE TABLE IF NOT EXISTS triggers_review (
    id SERIAL PRIMARY KEY,
    trigger_id INTEGER NOT NULL REFERENCES triggers(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    expression TEXT NOT NULL,
    priority INTEGER NOT NULL,
    description TEXT,
    status INTEGER DEFAULT 0,
    template_name VARCHAR(255) NOT NULL,
    modified BOOLEAN DEFAULT FALSE,
    confirmed BOOLEAN DEFAULT FALSE,
    status_verification VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    host_ip VARCHAR(255) NOT NULL,
    system VARCHAR(100),
    subsystem VARCHAR(100)
);

-- 3. 监控项原型复核表
CREATE TABLE IF NOT EXISTS item_prototypes_review (
    id SERIAL PRIMARY KEY,
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
    modified BOOLEAN DEFAULT FALSE,
    confirmed BOOLEAN DEFAULT FALSE,
    status_verification VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    host_ip VARCHAR(255) NOT NULL,
    system VARCHAR(100),
    subsystem VARCHAR(100)
);

-- 4. 触发器原型复核表
CREATE TABLE IF NOT EXISTS trigger_prototypes_review (
    id SERIAL PRIMARY KEY,
    trigger_prototype_id INTEGER NOT NULL REFERENCES trigger_prototypes(id) ON DELETE CASCADE,
    discovery_rule_id INTEGER NOT NULL REFERENCES discovery_rules(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    expression TEXT NOT NULL,
    priority INTEGER NOT NULL,
    status INTEGER DEFAULT 0,
    modified BOOLEAN DEFAULT FALSE,
    confirmed BOOLEAN DEFAULT FALSE,
    status_verification VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    host_ip VARCHAR(255) NOT NULL,
    system VARCHAR(100),
    subsystem VARCHAR(100)
);

-- 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_items_review_item ON items_review(item_id);
CREATE INDEX IF NOT EXISTS idx_items_review_confirmed ON items_review(confirmed);
CREATE INDEX IF NOT EXISTS idx_items_review_host_ip ON items_review(host_ip);
CREATE INDEX IF NOT EXISTS idx_items_review_master_item ON items_review(master_item);

CREATE INDEX IF NOT EXISTS idx_triggers_review_trigger ON triggers_review(trigger_id);
CREATE INDEX IF NOT EXISTS idx_triggers_review_confirmed ON triggers_review(confirmed);
CREATE INDEX IF NOT EXISTS idx_triggers_review_host_ip ON triggers_review(host_ip);

CREATE INDEX IF NOT EXISTS idx_item_prototypes_review_prototype ON item_prototypes_review(item_prototype_id);
CREATE INDEX IF NOT EXISTS idx_item_prototypes_review_confirmed ON item_prototypes_review(confirmed);
CREATE INDEX IF NOT EXISTS idx_item_prototypes_review_host_ip ON item_prototypes_review(host_ip);

CREATE INDEX IF NOT EXISTS idx_trigger_prototypes_review_prototype ON trigger_prototypes_review(trigger_prototype_id);
CREATE INDEX IF NOT EXISTS idx_trigger_prototypes_review_confirmed ON trigger_prototypes_review(confirmed);
CREATE INDEX IF NOT EXISTS idx_trigger_prototypes_review_host_ip ON trigger_prototypes_review(host_ip);

-- 提交事务
COMMIT;
