-- 016: 为 hosts 表添加 system 和 subsystem 字段
-- 此迁移为增量变更，对于已有 hosts 表的环境补充字段

ALTER TABLE zabbix_mac.hosts
    ADD COLUMN IF NOT EXISTS system VARCHAR(100),
    ADD COLUMN IF NOT EXISTS subsystem VARCHAR(100);

COMMIT;
