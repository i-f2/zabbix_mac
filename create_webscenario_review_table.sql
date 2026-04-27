-- 创建 webscenario_items_review 表
CREATE TABLE IF NOT EXISTS webscenario_items_review (
    id SERIAL PRIMARY KEY,
    system VARCHAR(100) NOT NULL,
    subsystem VARCHAR(100) NOT NULL,
    host VARCHAR(255) NOT NULL DEFAULT 'Zabbix server',
    name VARCHAR(255) NOT NULL,
    url VARCHAR(255) NOT NULL,
    status_code VARCHAR(50) NOT NULL DEFAULT '200',
    modified BOOLEAN DEFAULT FALSE,
    confirmed BOOLEAN DEFAULT FALSE,
    status_verification VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_webscenario_items_review_system ON webscenario_items_review(system);
CREATE INDEX IF NOT EXISTS idx_webscenario_items_review_subsystem ON webscenario_items_review(subsystem);
CREATE INDEX IF NOT EXISTS idx_webscenario_items_review_host ON webscenario_items_review(host);

-- 提交事务
COMMIT;