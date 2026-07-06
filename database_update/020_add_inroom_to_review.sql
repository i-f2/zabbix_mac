-- 020: 为 items_review 和 triggers_review 添加 in_room 字段
-- 数据流: hosts.in_room -> items_review.in_room / triggers_review.in_room

ALTER TABLE zabbix_mac.items_review
  ADD COLUMN IF NOT EXISTS in_room VARCHAR(100);

ALTER TABLE zabbix_mac.triggers_review
  ADD COLUMN IF NOT EXISTS in_room VARCHAR(100);

COMMIT;
