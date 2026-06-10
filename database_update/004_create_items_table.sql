-- 004: 创建监控项表
-- Zabbix Monitor as Code (MaC) 数据库模式

CREATE TABLE IF NOT EXISTS zabbix_mac.items (
    id SERIAL PRIMARY KEY,
    item_key VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    type INTEGER NOT NULL DEFAULT 0,
    value_type INTEGER NOT NULL DEFAULT 0,
    delay VARCHAR(50) NOT NULL DEFAULT '1m',
    description TEXT,
    units VARCHAR(50),
    multiplier INTEGER DEFAULT 0,
    delta INTEGER DEFAULT 0,
    history INTEGER DEFAULT 7,
    trends INTEGER DEFAULT 365,
    status INTEGER DEFAULT 0,
    template_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    master_item VARCHAR(255),
    preprocessing JSONB
);

CREATE INDEX IF NOT EXISTS idx_items_item_key ON zabbix_mac.items(item_key);
CREATE INDEX IF NOT EXISTS idx_items_template_name ON zabbix_mac.items(template_name);

COMMIT;
