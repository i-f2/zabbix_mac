-- 创建 webscenario_items 表
CREATE TABLE IF NOT EXISTS webscenario_items (
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

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_webscenario_items_system ON webscenario_items(system);
CREATE INDEX IF NOT EXISTS idx_webscenario_items_subsystem ON webscenario_items(subsystem);

-- 插入示例数据
INSERT INTO webscenario_items (
    system, subsystem, nginx_clb, nginx, clb, pod, 
    webtest_api, webtest_nginx_api, in_room
) VALUES
('Test System', 'Test Subsystem', '192.168.1.1:8080', '192.168.1.2:8080', '192.168.1.3:8080', '192.168.1.4:8080',
 '/api/test', '/nginx/api/test', 'Room A'),
('Another System', 'Another Subsystem', '192.168.2.1:8080', '192.168.2.2:8080', '192.168.2.3:8080', '192.168.2.4:8080',
 '/api/another', '/nginx/api/another', 'Room B');

-- 提交事务
COMMIT;