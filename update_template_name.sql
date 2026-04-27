-- 更新 template_name 字段值

-- 1. 更新 items 表
UPDATE items SET template_name = '21001' WHERE template_name = 'Template OS Linux by Zabbix agent - Standardized';

-- 2. 更新 triggers 表
UPDATE triggers SET template_name = '21001' WHERE template_name = 'Template OS Linux by Zabbix agent - Standardized';

-- 3. 更新 discovery_rules 表
UPDATE discovery_rules SET template_name = '21001' WHERE template_name = 'Template OS Linux by Zabbix agent - Standardized';

-- 4. 更新 templates 表
UPDATE templates SET name = '21001' WHERE name = 'Template OS Linux by Zabbix agent - Standardized';

-- 提交事务
COMMIT;