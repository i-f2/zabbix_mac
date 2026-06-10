-- 013: 创建复核表（监控项复核、触发器复核、监控项原型复核、触发器原型复核）
-- Zabbix Monitor as Code (MaC) 数据库模式

-- 1. 监控项复核表
CREATE TABLE IF NOT EXISTS zabbix_mac.items_review (
    id SERIAL PRIMARY KEY,
    item_id INTEGER NOT NULL REFERENCES zabbix_mac.items(id) ON DELETE CASCADE,
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
CREATE TABLE IF NOT EXISTS zabbix_mac.triggers_review (
    id SERIAL PRIMARY KEY,
    trigger_id INTEGER NOT NULL REFERENCES zabbix_mac.triggers(id) ON DELETE CASCADE,
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
CREATE TABLE IF NOT EXISTS zabbix_mac.item_prototypes_review (
    id SERIAL PRIMARY KEY,
    item_prototype_id INTEGER NOT NULL REFERENCES zabbix_mac.item_prototypes(id) ON DELETE CASCADE,
    discovery_rule_id INTEGER NOT NULL REFERENCES zabbix_mac.discovery_rules(id) ON DELETE CASCADE,
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
CREATE TABLE IF NOT EXISTS zabbix_mac.trigger_prototypes_review (
    id SERIAL PRIMARY KEY,
    trigger_prototype_id INTEGER NOT NULL REFERENCES zabbix_mac.trigger_prototypes(id) ON DELETE CASCADE,
    discovery_rule_id INTEGER NOT NULL REFERENCES zabbix_mac.discovery_rules(id) ON DELETE CASCADE,
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

-- 索引
CREATE INDEX IF NOT EXISTS idx_items_review_item ON zabbix_mac.items_review(item_id);
CREATE INDEX IF NOT EXISTS idx_items_review_confirmed ON zabbix_mac.items_review(confirmed);
CREATE INDEX IF NOT EXISTS idx_items_review_host_ip ON zabbix_mac.items_review(host_ip);
CREATE INDEX IF NOT EXISTS idx_items_review_master_item ON zabbix_mac.items_review(master_item);

CREATE INDEX IF NOT EXISTS idx_triggers_review_trigger ON zabbix_mac.triggers_review(trigger_id);
CREATE INDEX IF NOT EXISTS idx_triggers_review_confirmed ON zabbix_mac.triggers_review(confirmed);
CREATE INDEX IF NOT EXISTS idx_triggers_review_host_ip ON zabbix_mac.triggers_review(host_ip);

CREATE INDEX IF NOT EXISTS idx_item_prototypes_review_prototype ON zabbix_mac.item_prototypes_review(item_prototype_id);
CREATE INDEX IF NOT EXISTS idx_item_prototypes_review_confirmed ON zabbix_mac.item_prototypes_review(confirmed);
CREATE INDEX IF NOT EXISTS idx_item_prototypes_review_host_ip ON zabbix_mac.item_prototypes_review(host_ip);

CREATE INDEX IF NOT EXISTS idx_trigger_prototypes_review_prototype ON zabbix_mac.trigger_prototypes_review(trigger_prototype_id);
CREATE INDEX IF NOT EXISTS idx_trigger_prototypes_review_confirmed ON zabbix_mac.trigger_prototypes_review(confirmed);
CREATE INDEX IF NOT EXISTS idx_trigger_prototypes_review_host_ip ON zabbix_mac.trigger_prototypes_review(host_ip);

COMMIT;
