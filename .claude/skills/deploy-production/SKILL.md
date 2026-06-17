---
name: deploy-production
description: This skill should be used when the user asks to "部署环境上线", "部署生产上线", "deploy to production", "prepare for production deployment", or "上线部署". It automates dependency checks, database migration verification, and data export for the Zabbix MaC project.
---

# 部署生产上线

三阶段部署准备流程：依赖检查 → 数据库迁移检查 → 数据导出。

---

## Phase 1: 依赖与 Dockerfile 检查

### 1.1 扫描项目依赖

Read `app.py` and `zabbix_mac.py`. Extract every import statement (`import X` / `from X import Y`) that refers to a third-party package. Build a set of required packages.

Compare this set against the packages listed in:
- `requirements-linux-x86.txt` (production)
- `requirements-macos-arm.txt` (development)

For each requirements file, report:
- Packages present in the file but NOT used by the code (possibly removable)
- Packages used by the code but NOT in the file (need to add)
- Version mismatches between the two requirements files

Ask the user before modifying any requirements file.

### 1.2 检查 Dockerfile

Read `Dockerfile`. Verify:
- Base image (`python:3.11-slim-bookworm`) is appropriate
- All required `apt-get` packages are listed (`libpq-dev`, `gcc`)
- `pip install` references the correct requirements file (`requirements-linux-x86.txt`)
- `COPY` directives cover all necessary files: `app.py`, `zabbix_mac.py`, `config_loader.py`, `config.yaml.example`, `templates/`, `static/`
- Check if any new files (e.g., `config.yaml.example`, `static/vendor/`) need to be added to `COPY`
- `EXPOSE` matches `config.yaml.example` port
- `CMD` is correct

Report any findings. Do NOT modify Dockerfile without asking the user.

### 1.3 config.yaml 检查

Check if `config.yaml` exists. If not, remind the user to create it from `config.yaml.example`:

```bash
cp config.yaml.example config.yaml
# Edit config.yaml with actual production values
```

---

## Phase 2: 数据库迁移检查

### 2.1 列出迁移状态

List all `.sql` files in `database_update/` sorted by numeric prefix (e.g., `001`, `002`, ...).

Attempt to connect to the database (read config from `config.yaml` or environment variables) and query the migration tracking table:

```sql
SELECT version FROM zabbix_mac.schema_migrations ORDER BY version;
```

If the tracking table doesn't exist, all migrations are unapplied.

Report a table:

```
| 迁移文件 | 状态 |
|---------|------|
| 001_create_schema.sql | ✓ 已应用 |
| 002_create_hosts_table.sql | ✓ 已应用 |
| ... | ... |
| 017_add_system_subsystem_to_review.sql | ✗ 未应用 |
```

### 2.2 询问并执行

If unapplied migrations exist, ask the user which to apply (all, specific ones, or skip). Use the AskUserQuestion tool.

To apply migrations, run:

```bash
cd database_update/
./apply_migrations.sh <DB_HOST> <DB_PORT> <DB_NAME> <DB_USER>
```

Default DB params: read from `config.yaml` or use environment variables `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`.

### 2.3 更新迁移文件部署检查

Check if `Dockerfile` copies the `database_update/` directory. If it doesn't, remind the user that database migrations must be run separately (they use `psql` which requires `postgresql-client` on the host, not inside the app container).

---

## Phase 3: 数据导出

Export the 6 predefined template management tables to Excel files in `数据导出/`.

### 3.1 确保目录存在

```bash
mkdir -p 数据导出
```

### 3.2 启动 Flask 服务

If Flask is not already running, start it on a free port:

```bash
lsof -ti :5001 | xargs kill -9 2>/dev/null
APP_PORT=5001 nohup python3 app.py > /tmp/flask_deploy_export.log 2>&1 &
```

Wait for the server to be ready:

```bash
until curl -s -o /dev/null -w "%{http_code}" http://localhost:5001/items | grep -q 200; do sleep 1; done
```

### 3.3 导出 6 张表

For each table, use curl to download the Excel file:

| 表名 | 导出 URL | 输出文件 |
|------|---------|---------|
| items | `http://localhost:5001/items/export` | `数据导出/items.xlsx` |
| triggers | `http://localhost:5001/triggers/export` | `数据导出/triggers.xlsx` |
| item_prototypes | `http://localhost:5001/item-prototypes/export` | `数据导出/item_prototypes.xlsx` |
| trigger_prototypes | `http://localhost:5001/trigger-prototypes/export` | `数据导出/trigger_prototypes.xlsx` |
| discovery_rules | `http://localhost:5001/discovery-rules/export` | `数据导出/discovery_rules.xlsx` |
| filter_conditions | `http://localhost:5001/filter-conditions/export` | `数据导出/filter_conditions.xlsx` |

Use `curl -s -L -o` with follow-redirect to save each file:

```bash
curl -s -L -o "数据导出/items.xlsx" "http://localhost:5001/items/export"
```

### 3.4 验证导出结果

For each exported file, check:
- File exists
- File size > 0 bytes
- Record count by reading with pandas (`pd.read_excel(path)`)

Report a summary table:

```
| 表名 | 文件 | 大小 | 记录数 |
|------|------|------|--------|
| items | 数据导出/items.xlsx | 12.3 KB | 156 |
| triggers | 数据导出/triggers.xlsx | 8.1 KB | 89 |
| ... | ... | ... | ... |
```

### 3.5 停止 Flask 服务

```bash
lsof -ti :5001 | xargs kill 2>/dev/null
```

### 3.6 生成时间戳备份

Copy all exported files with a timestamp suffix:

```bash
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
for f in 数据导出/*.xlsx; do
  cp "$f" "数据导出/$(basename "$f" .xlsx).${TIMESTAMP}.xlsx"
done
```

---

## 完成报告

After all 3 phases complete, output a final summary:

```
=== 部署上线准备完成 ===

Phase 1 - 依赖检查: [OK / 有 N 项需处理]
Phase 2 - 数据库迁移: [OK / 已应用 N 个新迁移 / 跳过]
Phase 3 - 数据导出: [OK / 已导出 6 个文件至 数据导出/]

下一步:
1. 确保 config.yaml 已配置生产环境参数
2. docker build -t zabbix-mac:latest .
3. docker run -d -p 5000:5000 -v $(pwd)/config.yaml:/app/config.yaml ...
```
