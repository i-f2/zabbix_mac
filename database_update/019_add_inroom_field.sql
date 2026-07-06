-- 019: 为 hosts 和 sub_assets 表添加机房字段 in_room
-- 数据流: ops.sub_assets -> zabbix_mac.hosts -> items_review / triggers_review

ALTER TABLE zabbix_mac.hosts
  ADD COLUMN IF NOT EXISTS in_room VARCHAR(100);

ALTER TABLE ops.sub_assets
  ADD COLUMN IF NOT EXISTS in_room VARCHAR(100);

COMMIT;
