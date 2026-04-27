-- 修改复核表结构，将host_id字段更改为host_ip

-- 1. 修改items_review表
ALTER TABLE items_review DROP CONSTRAINT items_review_host_id_fkey;
ALTER TABLE items_review DROP COLUMN host_id;
ALTER TABLE items_review ADD COLUMN host_ip VARCHAR(255);

-- 2. 修改triggers_review表
ALTER TABLE triggers_review DROP CONSTRAINT triggers_review_host_id_fkey;
ALTER TABLE triggers_review DROP COLUMN host_id;
ALTER TABLE triggers_review ADD COLUMN host_ip VARCHAR(255);

-- 3. 修改item_prototypes_review表
ALTER TABLE item_prototypes_review DROP CONSTRAINT item_prototypes_review_host_id_fkey;
ALTER TABLE item_prototypes_review DROP COLUMN host_id;
ALTER TABLE item_prototypes_review ADD COLUMN host_ip VARCHAR(255);

-- 4. 修改trigger_prototypes_review表
ALTER TABLE trigger_prototypes_review DROP CONSTRAINT trigger_prototypes_review_host_id_fkey;
ALTER TABLE trigger_prototypes_review DROP COLUMN host_id;
ALTER TABLE trigger_prototypes_review ADD COLUMN host_ip VARCHAR(255);

-- 5. 更新数据，将hosts表中的name字段值作为host_ip
-- 先获取所有主机名
DO $$
DECLARE
    host_name TEXT;
BEGIN
    -- 获取第一个主机名
    SELECT name INTO host_name FROM hosts LIMIT 1;
    
    -- 更新items_review表
    UPDATE items_review SET host_ip = host_name;
    
    -- 更新triggers_review表
    UPDATE triggers_review SET host_ip = host_name;
    
    -- 更新item_prototypes_review表
    UPDATE item_prototypes_review SET host_ip = host_name;
    
    -- 更新trigger_prototypes_review表
    UPDATE trigger_prototypes_review SET host_ip = host_name;
END $$;

-- 6. 设置host_ip字段为NOT NULL
ALTER TABLE items_review ALTER COLUMN host_ip SET NOT NULL;
ALTER TABLE triggers_review ALTER COLUMN host_ip SET NOT NULL;
ALTER TABLE item_prototypes_review ALTER COLUMN host_ip SET NOT NULL;
ALTER TABLE trigger_prototypes_review ALTER COLUMN host_ip SET NOT NULL;

-- 7. 更新索引
DROP INDEX IF EXISTS idx_items_review_host;
CREATE INDEX IF NOT EXISTS idx_items_review_host_ip ON items_review(host_ip);

DROP INDEX IF EXISTS idx_triggers_review_host;
CREATE INDEX IF NOT EXISTS idx_triggers_review_host_ip ON triggers_review(host_ip);

DROP INDEX IF EXISTS idx_item_prototypes_review_host;
CREATE INDEX IF NOT EXISTS idx_item_prototypes_review_host_ip ON item_prototypes_review(host_ip);

DROP INDEX IF EXISTS idx_trigger_prototypes_review_host;
CREATE INDEX IF NOT EXISTS idx_trigger_prototypes_review_host_ip ON trigger_prototypes_review(host_ip);

-- 8. 更新唯一约束
ALTER TABLE items_review DROP CONSTRAINT IF EXISTS items_review_host_id_item_id_key;
ALTER TABLE items_review ADD CONSTRAINT items_review_host_ip_item_id_key UNIQUE(host_ip, item_id);

ALTER TABLE triggers_review DROP CONSTRAINT IF EXISTS triggers_review_host_id_trigger_id_key;
ALTER TABLE triggers_review ADD CONSTRAINT triggers_review_host_ip_trigger_id_key UNIQUE(host_ip, trigger_id);

ALTER TABLE item_prototypes_review DROP CONSTRAINT IF EXISTS item_prototypes_review_host_id_item_prototype_id_key;
ALTER TABLE item_prototypes_review ADD CONSTRAINT item_prototypes_review_host_ip_item_prototype_id_key UNIQUE(host_ip, item_prototype_id);

ALTER TABLE trigger_prototypes_review DROP CONSTRAINT IF EXISTS trigger_prototypes_review_host_id_trigger_prototype_id_key;
ALTER TABLE trigger_prototypes_review ADD CONSTRAINT trigger_prototypes_review_host_ip_trigger_prototype_id_key UNIQUE(host_ip, trigger_prototype_id);

-- 提交事务
COMMIT;