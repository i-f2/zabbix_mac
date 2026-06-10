-- 010: 创建主机-模板关联表
-- Zabbix Monitor as Code (MaC) 数据库模式

CREATE TABLE IF NOT EXISTS zabbix_mac.host_templates (
    id SERIAL PRIMARY KEY,
    host_id INTEGER NOT NULL REFERENCES zabbix_mac.hosts(id) ON DELETE CASCADE,
    template_id INTEGER NOT NULL REFERENCES zabbix_mac.templates(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_host_templates_host ON zabbix_mac.host_templates(host_id);
CREATE INDEX IF NOT EXISTS idx_host_templates_template ON zabbix_mac.host_templates(template_id);

COMMIT;
