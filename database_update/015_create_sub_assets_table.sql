-- 015: 创建 ops schema 和 sub_assets 资产表
-- Zabbix Monitor as Code (MaC) 数据库模式

CREATE SCHEMA IF NOT EXISTS ops;

CREATE TABLE IF NOT EXISTS ops.sub_assets (
    id SERIAL PRIMARY KEY,
    system VARCHAR(100),
    subsystem VARCHAR(100),
    hostname VARCHAR(255),
    ip VARCHAR(255) NOT NULL,
    template_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sub_assets_ip ON ops.sub_assets(ip);

COMMIT;
