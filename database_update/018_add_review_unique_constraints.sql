-- 018: 为复核表添加唯一约束，支持已确认记录保护
-- 使得 initialize 可以使用 INSERT ... ON CONFLICT DO NOTHING
-- 避免覆盖已确认的记录

ALTER TABLE zabbix_mac.items_review
  ADD CONSTRAINT uq_items_review_item_host UNIQUE (item_id, host_ip);

ALTER TABLE zabbix_mac.triggers_review
  ADD CONSTRAINT uq_triggers_review_trigger_host UNIQUE (trigger_id, host_ip);

ALTER TABLE zabbix_mac.item_prototypes_review
  ADD CONSTRAINT uq_ipr_proto_host UNIQUE (item_prototype_id, host_ip);

ALTER TABLE zabbix_mac.trigger_prototypes_review
  ADD CONSTRAINT uq_tpr_proto_host UNIQUE (trigger_prototype_id, host_ip);

ALTER TABLE zabbix_mac.webscenario_items_review
  ADD CONSTRAINT uq_wsir_name_host_url UNIQUE (name, host, url);

COMMIT;
