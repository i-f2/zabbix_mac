-- 022: 为剩余复核表添加机房字段 in_room
-- 数据流: hosts.in_room -> item_prototypes_review / trigger_prototypes_review
--         webscenario_items.in_room -> webscenario_items_review -> web_trigger_review

ALTER TABLE zabbix_mac.item_prototypes_review ADD COLUMN IF NOT EXISTS in_room VARCHAR(100);
ALTER TABLE zabbix_mac.trigger_prototypes_review ADD COLUMN IF NOT EXISTS in_room VARCHAR(100);
ALTER TABLE zabbix_mac.webscenario_items_review ADD COLUMN IF NOT EXISTS in_room VARCHAR(100);
ALTER TABLE zabbix_mac.web_trigger_review ADD COLUMN IF NOT EXISTS in_room VARCHAR(100);

COMMIT;
