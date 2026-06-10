-- 007: 创建监控项原型表
-- Zabbix Monitor as Code (MaC) 数据库模式

CREATE TABLE IF NOT EXISTS zabbix_mac.item_prototypes (
    id SERIAL PRIMARY KEY,
    discovery_rule_id INTEGER NOT NULL REFERENCES zabbix_mac.discovery_rules(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    key VARCHAR(255) NOT NULL,
    type INTEGER NOT NULL DEFAULT 0,
    delay VARCHAR(50) NOT NULL DEFAULT '1m',
    description TEXT,
    units VARCHAR(50),
    multiplier INTEGER DEFAULT 0,
    delta INTEGER DEFAULT 0,
    history INTEGER DEFAULT 7,
    trends INTEGER DEFAULT 365,
    status INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_item_prototypes_discovery ON zabbix_mac.item_prototypes(discovery_rule_id);

COMMIT;
