-- 更新复核表结构，添加system和subsystem字段
-- Zabbix Monitor as Code (MaC) 数据库模式

-- 1. 更新监控项复核表
ALTER TABLE items_review ADD COLUMN IF NOT EXISTS system VARCHAR(100);
ALTER TABLE items_review ADD COLUMN IF NOT EXISTS subsystem VARCHAR(100);

-- 2. 更新触发器复核表
ALTER TABLE triggers_review ADD COLUMN IF NOT EXISTS system VARCHAR(100);
ALTER TABLE triggers_review ADD COLUMN IF NOT EXISTS subsystem VARCHAR(100);

-- 3. 更新监控项原型复核表
ALTER TABLE item_prototypes_review ADD COLUMN IF NOT EXISTS system VARCHAR(100);
ALTER TABLE item_prototypes_review ADD COLUMN IF NOT EXISTS subsystem VARCHAR(100);

-- 4. 更新触发器原型复核表
ALTER TABLE trigger_prototypes_review ADD COLUMN IF NOT EXISTS system VARCHAR(100);
ALTER TABLE trigger_prototypes_review ADD COLUMN IF NOT EXISTS subsystem VARCHAR(100);

-- 更新现有数据
-- 1. 更新监控项复核表
UPDATE items_review ir
SET system = h.system, subsystem = h.subsystem
FROM hosts h
WHERE ir.host_ip = h.name;

-- 2. 更新触发器复核表
UPDATE triggers_review tr
SET system = h.system, subsystem = h.subsystem
FROM hosts h
WHERE tr.host_ip = h.name;

-- 3. 更新监控项原型复核表
UPDATE item_prototypes_review ipr
SET system = h.system, subsystem = h.subsystem
FROM hosts h
WHERE ipr.host_ip = h.name;

-- 4. 更新触发器原型复核表
UPDATE trigger_prototypes_review tpr
SET system = h.system, subsystem = h.subsystem
FROM hosts h
WHERE tpr.host_ip = h.name;

-- 提交事务
COMMIT;