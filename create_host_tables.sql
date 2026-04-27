-- 主机相关表结构

-- 1. 主机表
CREATE TABLE IF NOT EXISTS hosts (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. 主机模板关联表
CREATE TABLE IF NOT EXISTS host_templates (
    id SERIAL PRIMARY KEY,
    host_id INTEGER NOT NULL REFERENCES hosts(id) ON DELETE CASCADE,
    template_id INTEGER NOT NULL REFERENCES templates(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(host_id, template_id)
);

-- 3. 主机额外监控项表
CREATE TABLE IF NOT EXISTS host_extra_items (
    id SERIAL PRIMARY KEY,
    host_name VARCHAR(255) NOT NULL,
    item_key VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    type INTEGER NOT NULL,
    value_type INTEGER NOT NULL,
    delay VARCHAR(50) NOT NULL,
    description TEXT,
    units VARCHAR(50),
    multiplier INTEGER DEFAULT 0,
    delta INTEGER DEFAULT 0,
    history INTEGER DEFAULT 7,
    trends INTEGER DEFAULT 365,
    status INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(host_name, item_key)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_hosts_name ON hosts(name);
CREATE INDEX IF NOT EXISTS idx_host_templates_host ON host_templates(host_id);
CREATE INDEX IF NOT EXISTS idx_host_templates_template ON host_templates(template_id);
CREATE INDEX IF NOT EXISTS idx_host_extra_items_host ON host_extra_items(host_name);
CREATE INDEX IF NOT EXISTS idx_host_extra_items_key ON host_extra_items(item_key);

-- 插入示例主机数据
INSERT INTO hosts (name, description) VALUES
('Zabbix server', 'Local Zabbix server'),
('Test Host 1', 'Test server 1');

-- 关联主机与模板
INSERT INTO host_templates (host_id, template_id) VALUES
((SELECT id FROM hosts WHERE name = 'Zabbix server'), (SELECT id FROM templates WHERE name = 'Template OS Linux by Zabbix agent - Standardized')),
((SELECT id FROM hosts WHERE name = 'Test Host 1'), (SELECT id FROM templates WHERE name = 'Template OS Linux by Zabbix agent - Standardized'));

-- 提交事务
COMMIT;