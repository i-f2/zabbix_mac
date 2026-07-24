-- 024: 规范化 hosts 表 — 重命名 template_name 列为 template_id
-- 背景：DDL 002 定义列为 template_id VARCHAR，但早期代码误用 template_name
-- 导致生产环境中列名实际为 template_name（手工修改），与 DDL 不一致
-- 此迁移将列名统一为 template_id，消除 schema-code 不一致

-- 仅在列名确为 template_name 时执行重命名（幂等保护）
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'zabbix_mac'
          AND table_name = 'hosts'
          AND column_name = 'template_name'
    ) THEN
        ALTER TABLE zabbix_mac.hosts RENAME COLUMN template_name TO template_id;
    END IF;
END $$;

COMMIT;
