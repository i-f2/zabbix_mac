-- 009: 创建过滤器条件表
-- Zabbix Monitor as Code (MaC) 数据库模式

CREATE TABLE IF NOT EXISTS zabbix_mac.filter_conditions (
    id SERIAL PRIMARY KEY,
    discovery_rule_id INTEGER NOT NULL REFERENCES zabbix_mac.discovery_rules(id) ON DELETE CASCADE,
    macro VARCHAR(255) NOT NULL,
    value VARCHAR(255) NOT NULL,
    formula VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_filter_conditions_discovery ON zabbix_mac.filter_conditions(discovery_rule_id);

COMMIT;
