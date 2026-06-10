# Database Update 迁移规范

## 目录说明

`database_update/` 存放 Zabbix Monitor as Code (MaC) 项目的数据库结构变更（DDL）脚本。
每个文件只包含数据结构定义（CREATE/ALTER/DROP/INDEX），**不含数据内容**（INSERT/UPDATE/DELETE）。

## 文件命名规则

```
NNN_description.sql
```

- `NNN`: 三位数字编号，从 `001` 开始递增
- `description`: 英文下划线描述，简要说明变更内容
- 编号一旦分配即**不可更改**（即使后续插入新文件，也使用下一个可用编号）

示例：
```
001_create_schema.sql
002_create_hosts_table.sql
016_add_system_subsystem_to_hosts.sql
```

## 如何新增迁移文件

每次开发涉及数据库结构变更时：

1. 查看 `database_update/` 目录中当前最大编号
2. 创建新文件，编号 = 当前最大编号 + 1
3. 文件名格式：`NNN_简短描述.sql`
4. 文件内容**仅包含 DDL 语句**（CREATE、ALTER、DROP 等）
5. 每个文件以 `COMMIT;` 结尾
6. 将新文件随代码一起提交 Git

## 部署流程

在目标数据库服务器上：

```bash
# 基本用法（使用默认参数）
cd database_update/
./apply_migrations.sh

# 指定数据库连接参数
./apply_migrations.sh db.example.com 5432 ops postgres

# 带密码
PGPASSWORD=yourpassword ./apply_migrations.sh db.example.com 5432 ops postgres
```

脚本会自动：
1. 创建 `schema_migrations` 追踪表（如不存在）
2. 扫描目录下所有 `.sql` 文件，按编号排序
3. 跳过已在追踪表中记录的迁移
4. 执行未应用的迁移，并记录到追踪表

## 验证迁移状态

```sql
-- 查看所有已应用的迁移
SELECT * FROM zabbix_mac.schema_migrations ORDER BY version;

-- 或（如追踪表在 public schema）
SELECT * FROM public.schema_migrations ORDER BY version;
```

## 注意事项

- **不要在已有迁移文件中追加内容** — 每次变更都创建新文件
- **不要修改已执行的迁移文件** — 这会导致迁移追踪失效
- **不要重排编号** — 编号是迁移的永久标识
- IDEMPOTENT 原则 — 使用 `CREATE TABLE IF NOT EXISTS`、`ADD COLUMN IF NOT EXISTS` 等幂等语法
- 生产环境执行前建议先在测试数据库验证

## 现有迁移列表

| 编号 | 文件 | 说明 |
|------|------|------|
| 001 | `001_create_schema.sql` | 创建 zabbix_mac schema |
| 002 | `002_create_hosts_table.sql` | 主机表 |
| 003 | `003_create_templates_table.sql` | 模板表 |
| 004 | `004_create_items_table.sql` | 监控项表 |
| 005 | `005_create_triggers_table.sql` | 触发器表 |
| 006 | `006_create_discovery_rules_table.sql` | 自动发现规则表 |
| 007 | `007_create_item_prototypes_table.sql` | 监控项原型表 |
| 008 | `008_create_trigger_prototypes_table.sql` | 触发器原型表 |
| 009 | `009_create_filter_conditions_table.sql` | 过滤器条件表 |
| 010 | `010_create_host_templates_table.sql` | 主机-模板关联表 |
| 011 | `011_create_host_extra_items_table.sql` | 主机额外监控项表 |
| 012 | `012_create_webscenario_items_table.sql` | Web 场景监控项表 |
| 013 | `013_create_review_tables.sql` | 复核表（4张） |
| 014 | `014_create_webscenario_review_table.sql` | Web 场景复核表 |
| 015 | `015_create_sub_assets_table.sql` | ops.sub_assets 资产表 |
| 016 | `016_add_system_subsystem_to_hosts.sql` | hosts 表补充 system/subsystem |
| 017 | `017_add_system_subsystem_to_review.sql` | 复核表补充 system/subsystem |
