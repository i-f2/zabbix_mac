-- 012: 创建 Web 场景监控项表
-- Zabbix Monitor as Code (MaC) 数据库模式

CREATE TABLE IF NOT EXISTS zabbix_mac.webscenario_items (
    id SERIAL PRIMARY KEY,
    system VARCHAR(100) NOT NULL,
    subsystem VARCHAR(100) NOT NULL,
    nginx_clb VARCHAR(255),
    nginx VARCHAR(255),
    clb VARCHAR(255),
    pod VARCHAR(255),
    webtest_api VARCHAR(255) NOT NULL,
    webtest_nginx_api VARCHAR(255) NOT NULL,
    in_room VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_webscenario_items_system ON zabbix_mac.webscenario_items(system);
CREATE INDEX IF NOT EXISTS idx_webscenario_items_subsystem ON zabbix_mac.webscenario_items(subsystem);

COMMIT;
