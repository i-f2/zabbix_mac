-- 011: 创建主机额外监控项表
-- Zabbix Monitor as Code (MaC) 数据库模式

CREATE TABLE IF NOT EXISTS zabbix_mac.host_extra_items (
    id SERIAL PRIMARY KEY,
    host_name VARCHAR(255) NOT NULL,
    item_key VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    type INTEGER NOT NULL DEFAULT 0,
    value_type INTEGER NOT NULL DEFAULT 0,
    delay VARCHAR(50) DEFAULT '1m',
    description TEXT,
    units VARCHAR(50),
    multiplier INTEGER DEFAULT 0,
    delta INTEGER DEFAULT 0,
    history INTEGER DEFAULT 7,
    trends INTEGER DEFAULT 365,
    status INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_host_extra_items_host_name ON zabbix_mac.host_extra_items(host_name);

COMMIT;
