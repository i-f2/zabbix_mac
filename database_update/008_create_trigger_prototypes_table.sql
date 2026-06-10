-- 008: 创建触发器原型表
-- Zabbix Monitor as Code (MaC) 数据库模式

CREATE TABLE IF NOT EXISTS zabbix_mac.trigger_prototypes (
    id SERIAL PRIMARY KEY,
    discovery_rule_id INTEGER NOT NULL REFERENCES zabbix_mac.discovery_rules(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    expression TEXT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 0,
    status INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_trigger_prototypes_discovery ON zabbix_mac.trigger_prototypes(discovery_rule_id);

COMMIT;
