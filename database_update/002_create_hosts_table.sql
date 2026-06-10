-- 002: 创建主机表
-- Zabbix Monitor as Code (MaC) 数据库模式

CREATE TABLE IF NOT EXISTS zabbix_mac.hosts (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    system VARCHAR(100),
    subsystem VARCHAR(100),
    template_id VARCHAR(255)
);

CREATE INDEX IF NOT EXISTS idx_hosts_name ON zabbix_mac.hosts(name);
CREATE INDEX IF NOT EXISTS idx_hosts_system ON zabbix_mac.hosts(system);

COMMIT;
