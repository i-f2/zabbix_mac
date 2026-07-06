-- 023: 为复核表添加同步状态和变更类型字段，支持 Diff 增量同步
-- 新增 sync_status: pending_confirm | synced | pending_delete
-- 新增 change_type: new | update | delete | NULL（无变化）
-- 同时为 web_trigger_review 补充唯一约束

-- items_review
ALTER TABLE zabbix_mac.items_review ADD COLUMN IF NOT EXISTS sync_status VARCHAR(50) DEFAULT 'pending_confirm';
ALTER TABLE zabbix_mac.items_review ADD COLUMN IF NOT EXISTS change_type VARCHAR(20) DEFAULT NULL;

-- triggers_review
ALTER TABLE zabbix_mac.triggers_review ADD COLUMN IF NOT EXISTS sync_status VARCHAR(50) DEFAULT 'pending_confirm';
ALTER TABLE zabbix_mac.triggers_review ADD COLUMN IF NOT EXISTS change_type VARCHAR(20) DEFAULT NULL;

-- item_prototypes_review
ALTER TABLE zabbix_mac.item_prototypes_review ADD COLUMN IF NOT EXISTS sync_status VARCHAR(50) DEFAULT 'pending_confirm';
ALTER TABLE zabbix_mac.item_prototypes_review ADD COLUMN IF NOT EXISTS change_type VARCHAR(20) DEFAULT NULL;

-- trigger_prototypes_review
ALTER TABLE zabbix_mac.trigger_prototypes_review ADD COLUMN IF NOT EXISTS sync_status VARCHAR(50) DEFAULT 'pending_confirm';
ALTER TABLE zabbix_mac.trigger_prototypes_review ADD COLUMN IF NOT EXISTS change_type VARCHAR(20) DEFAULT NULL;

-- webscenario_items_review
ALTER TABLE zabbix_mac.webscenario_items_review ADD COLUMN IF NOT EXISTS sync_status VARCHAR(50) DEFAULT 'pending_confirm';
ALTER TABLE zabbix_mac.webscenario_items_review ADD COLUMN IF NOT EXISTS change_type VARCHAR(20) DEFAULT NULL;

-- web_trigger_review
ALTER TABLE zabbix_mac.web_trigger_review ADD COLUMN IF NOT EXISTS sync_status VARCHAR(50) DEFAULT 'pending_confirm';
ALTER TABLE zabbix_mac.web_trigger_review ADD COLUMN IF NOT EXISTS change_type VARCHAR(20) DEFAULT NULL;

-- 为 web_trigger_review 补充唯一约束（迁移 018 时此表尚未存在）
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'uq_wtr_host_scenario_trigger'
  ) THEN
    ALTER TABLE zabbix_mac.web_trigger_review
      ADD CONSTRAINT uq_wtr_host_scenario_trigger UNIQUE (host, web_scenario_name, trigger_name);
  END IF;
END $$;

COMMIT;
