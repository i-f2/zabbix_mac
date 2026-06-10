-- 005: 创建触发器表
-- Zabbix Monitor as Code (MaC) 数据库模式

CREATE TABLE IF NOT EXISTS zabbix_mac.triggers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    expression TEXT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 0,
    description TEXT,
    status INTEGER DEFAULT 0,
    template_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_triggers_template_name ON zabbix_mac.triggers(template_name);

COMMIT;
