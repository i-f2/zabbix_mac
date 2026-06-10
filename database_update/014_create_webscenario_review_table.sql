-- 014: 创建 Web 场景监控项复核表
-- Zabbix Monitor as Code (MaC) 数据库模式

CREATE TABLE IF NOT EXISTS zabbix_mac.webscenario_items_review (
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

CREATE INDEX IF NOT EXISTS idx_webscenario_items_review_system ON zabbix_mac.webscenario_items_review(system);
CREATE INDEX IF NOT EXISTS idx_webscenario_items_review_subsystem ON zabbix_mac.webscenario_items_review(subsystem);
CREATE INDEX IF NOT EXISTS idx_webscenario_items_review_host ON zabbix_mac.webscenario_items_review(host);

COMMIT;
