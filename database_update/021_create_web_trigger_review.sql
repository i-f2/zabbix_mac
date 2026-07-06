-- 021: 创建 Web 触发器复核表
-- 用于 Web 场景关联的触发器审核、确认、同步与核验

CREATE TABLE IF NOT EXISTS zabbix_mac.web_trigger_review (
    id SERIAL PRIMARY KEY,
    host VARCHAR(255) NOT NULL,
    web_scenario_name VARCHAR(255) NOT NULL,
    trigger_name VARCHAR(255) NOT NULL,
    expression TEXT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 3,
    status INTEGER DEFAULT 0,
    modified BOOLEAN DEFAULT FALSE,
    confirmed BOOLEAN DEFAULT FALSE,
    status_verification VARCHAR(50) DEFAULT 'pending',
    system VARCHAR(100),
    subsystem VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_wtr_host ON zabbix_mac.web_trigger_review(host);
CREATE INDEX IF NOT EXISTS idx_wtr_confirmed ON zabbix_mac.web_trigger_review(confirmed);
CREATE INDEX IF NOT EXISTS idx_wtr_system ON zabbix_mac.web_trigger_review(system);

COMMIT;
