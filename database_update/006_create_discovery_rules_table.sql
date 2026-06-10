-- 006: 创建自动发现规则表
-- Zabbix Monitor as Code (MaC) 数据库模式

CREATE TABLE IF NOT EXISTS zabbix_mac.discovery_rules (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    key VARCHAR(255) NOT NULL,
    delay VARCHAR(50) NOT NULL DEFAULT '1h',
    type INTEGER NOT NULL DEFAULT 0,
    status INTEGER DEFAULT 0,
    template_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_discovery_rules_template_name ON zabbix_mac.discovery_rules(template_name);

COMMIT;
