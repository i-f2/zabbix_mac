-- 025: 拆分 hosts 多模板支持 — 唯一键改为 (name, template_id)
-- 背景：ops.sub_assets.template_id 可能为逗号分隔的多模板（如 '21001,91001'），
-- /host/sync 同步时将拆分为多条 hosts 记录（每行绑定一个模板）。
-- 原唯一键 UNIQUE (name) 每台主机只能绑定一个模板，需替换为组合唯一键。
-- 同时保留「无模板主机每台一行」的部分唯一索引，防止 NULL 造成的重复绑定。

-- 1. 移除旧的单主机唯一键（此约束为早期手工添加，无迁移文件来源，此处幂等删除）
ALTER TABLE zabbix_mac.hosts DROP CONSTRAINT IF EXISTS hosts_name_key;

-- 2. 新增 (name, template_id) 组合唯一键 — 拆分后的幂等 UPSERT 依据
ALTER TABLE zabbix_mac.hosts ADD CONSTRAINT hosts_name_template_key UNIQUE (name, template_id);

-- 3. 无模板主机（template_id 为空/NULL）仍保持"每台一行"，防止 NULL 造成的重复
CREATE UNIQUE INDEX IF NOT EXISTS hosts_name_no_tpl_key
    ON zabbix_mac.hosts (name)
    WHERE template_id IS NULL OR template_id = '';

COMMIT;
