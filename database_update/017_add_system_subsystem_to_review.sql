-- 017: 为复核表添加 system 和 subsystem 字段
-- 此迁移为增量变更，对于已有复核表的环境补充字段

ALTER TABLE zabbix_mac.items_review
    ADD COLUMN IF NOT EXISTS system VARCHAR(100),
    ADD COLUMN IF NOT EXISTS subsystem VARCHAR(100);

ALTER TABLE zabbix_mac.triggers_review
    ADD COLUMN IF NOT EXISTS system VARCHAR(100),
    ADD COLUMN IF NOT EXISTS subsystem VARCHAR(100);

ALTER TABLE zabbix_mac.item_prototypes_review
    ADD COLUMN IF NOT EXISTS system VARCHAR(100),
    ADD COLUMN IF NOT EXISTS subsystem VARCHAR(100);

ALTER TABLE zabbix_mac.trigger_prototypes_review
    ADD COLUMN IF NOT EXISTS system VARCHAR(100),
    ADD COLUMN IF NOT EXISTS subsystem VARCHAR(100);

COMMIT;
