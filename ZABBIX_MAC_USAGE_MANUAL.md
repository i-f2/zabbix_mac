# zabbix_mac.py 使用手册

## 概述

`zabbix_mac.py` 是一个 Zabbix 监控审核和自动化控制中心工具，用于自动化管理 Zabbix 监控配置。该工具支持多种操作模式，包括同步监控配置、初始化复核表、导出/导入数据以及创建 Web 场景监控等功能。

## 基本语法

```bash
python3 zabbix_mac.py [操作模式] [参数]
```

## 操作模式

### 1. 同步操作
```bash
python3 zabbix_mac.py --sync --url <ZABBIX_API_URL> --username <USERNAME> --password <PASSWORD>
```

**说明**：执行监控配置同步操作，将数据库中的配置同步到 Zabbix 服务器。

**必需参数**：
- `--url`: Zabbix API URL（如 http://localhost:8080）
- `--username`: Zabbix 用户名
- `--password`: Zabbix 密码

### 2. 初始化复核表
```bash
python3 zabbix_mac.py --initialize-reviews --db-host <DB_HOST> --db-port <DB_PORT> --db-name <DB_NAME> --db-user <DB_USER>
```

**说明**：初始化 `items_review` 和 `triggers_review` 两个复核表。

### 3. 初始化 items_review 表
```bash
python3 zabbix_mac.py --initialize-items-review --db-host <DB_HOST> --db-port <DB_PORT> --db-name <DB_NAME> --db-user <DB_USER>
```

**说明**：只初始化 `items_review` 表。

### 4. 初始化 triggers_review 表
```bash
python3 zabbix_mac.py --initialize-triggers-review --db-host <DB_HOST> --db-port <DB_PORT> --db-name <DB_NAME> --db-user <DB_USER>
```

**说明**：只初始化 `triggers_review` 表。

### 5. 初始化 webscenario_items_review 表
```bash
python3 zabbix_mac.py --initialize-webscenario-items-review --db-host <DB_HOST> --db-port <DB_PORT> --db-name <DB_NAME> --db-user <DB_USER>
```

**说明**：初始化 `webscenario_items_review` 表，从 `webscenario_items` 表导入数据。

### 6. 导出 items_review 到 Excel
```bash
python3 zabbix_mac.py --export-items-review <OUTPUT_FILE> --db-host <DB_HOST> --db-port <DB_PORT> --db-name <DB_NAME> --db-user <DB_USER>
```

**说明**：将 `items_review` 表数据导出到指定的 Excel 文件。

### 7. 导出 triggers_review 到 Excel
```bash
python3 zabbix_mac.py --export-triggers-review <OUTPUT_FILE> --db-host <DB_HOST> --db-port <DB_PORT> --db-name <DB_NAME> --db-user <DB_USER>
```

**说明**：将 `triggers_review` 表数据导出到指定的 Excel 文件。

### 8. 从 Excel 导入 items_review
```bash
python3 zabbix_mac.py --import-items-review <INPUT_FILE> --db-host <DB_HOST> --db-port <DB_PORT> --db-name <DB_NAME> --db-user <DB_USER>
```

**说明**：从指定的 Excel 文件导入数据到 `items_review` 表。

### 9. 从 Excel 导入 triggers_review
```bash
python3 zabbix_mac.py --import-triggers-review <INPUT_FILE> --db-host <DB_HOST> --db-port <DB_PORT> --db-name <DB_NAME> --db-user <DB_USER>
```

**说明**：从指定的 Excel 文件导入数据到 `triggers_review` 表。

### 10. 创建 Web 场景监控
```bash
python3 zabbix_mac.py --create-web-scenarios --url <ZABBIX_API_URL> --username <USERNAME> --password <PASSWORD> --db-host <DB_HOST> --db-port <DB_PORT> --db-name <DB_NAME> --db-user <DB_USER>
```

**说明**：从 `webscenario_items_review` 表中读取已确认的记录，创建 Web 场景监控到 Zabbix 服务器。

### 11. 创建 Web 场景触发器
```bash
python3 zabbix_mac.py --create-web-scenario-triggers --url <ZABBIX_API_URL> --username <USERNAME> --password <PASSWORD> --db-host <DB_HOST> --db-port <DB_PORT> --db-name <DB_NAME> --db-user <DB_USER>
```

**说明**：为 Web 场景创建触发器，触发器表达式格式为 `{host:web.test.fail[name].count(#3,0,ne)}>2`。

## 参数说明

### Zabbix API 配置参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--url` | Zabbix API URL | 无（必需） |
| `--username` | Zabbix 用户名 | 无（必需） |
| `--password` | Zabbix 密码 | 无（必需） |

### 数据库配置参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--db-host` | PostgreSQL 主机地址 | localhost |
| `--db-port` | PostgreSQL 端口 | 5432 |
| `--db-name` | PostgreSQL 数据库名称 | zabbix_mac |
| `--db-user` | PostgreSQL 用户名 | fan |
| `--db-password` | PostgreSQL 密码 | 空 |

### 同步操作参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--dry-run` | 模拟运行，不实际执行操作 | False |
| `--workers` | 并发线程数 | 5 |

## 使用示例

### 示例 1：同步监控配置
```bash
python3 zabbix_mac.py --sync \
  --url http://localhost:8080 \
  --username Admin \
  --password zabbix \
  --db-host localhost \
  --db-port 5432 \
  --db-name zabbix_mac \
  --db-user fan
```

### 示例 2：初始化所有复核表
```bash
python3 zabbix_mac.py --initialize-reviews \
  --db-host localhost \
  --db-port 5432 \
  --db-name zabbix_mac \
  --db-user fan
```

### 示例 3：创建 Web 场景监控
```bash
python3 zabbix_mac.py --create-web-scenarios \
  --url http://localhost:8080 \
  --username Admin \
  --password zabbix \
  --db-host localhost \
  --db-port 5432 \
  --db-name zabbix_mac \
  --db-user fan
```

### 示例 4：为 Web 场景创建触发器
```bash
python3 zabbix_mac.py --create-web-scenario-triggers \
  --url http://localhost:8080 \
  --username Admin \
  --password zabbix \
  --db-host localhost \
  --db-port 5432 \
  --db-name zabbix_mac \
  --db-user fan
```

### 示例 5：导出数据到 Excel
```bash
python3 zabbix_mac.py --export-items-review items_review.xlsx \
  --db-host localhost \
  --db-port 5432 \
  --db-name zabbix_mac \
  --db-user fan
```

### 示例 6：从 Excel 导入数据
```bash
python3 zabbix_mac.py --import-items-review items_review.xlsx \
  --db-host localhost \
  --db-port 5432 \
  --db-name zabbix_mac \
  --db-user fan
```

## 操作模式与必需参数对应表

| 操作模式 | 需要 Zabbix API | 需要数据库 |
|----------|-----------------|-----------|
| `--sync` | ✓ | ✓ |
| `--initialize-reviews` | ✗ | ✓ |
| `--initialize-items-review` | ✗ | ✓ |
| `--initialize-triggers-review` | ✗ | ✓ |
| `--initialize-webscenario-items-review` | ✗ | ✓ |
| `--export-items-review` | ✗ | ✓ |
| `--export-triggers-review` | ✗ | ✓ |
| `--import-items-review` | ✗ | ✓ |
| `--import-triggers-review` | ✗ | ✓ |
| `--create-web-scenarios` | ✓ | ✓ |
| `--create-web-scenario-triggers` | ✓ | ✓ |

## Web 场景监控工作流程

1. **准备数据**：确保 `webscenario_items` 表中有数据

2. **初始化复核表**：
   ```bash
   python3 zabbix_mac.py --initialize-webscenario-items-review --db-host localhost --db-port 5432 --db-name zabbix_mac --db-user fan
   ```

3. **确认数据**：在数据库中将 `webscenario_items_review` 表中的记录标记为已确认（`confirmed = true`）

4. **创建 Web 场景**：
   ```bash
   python3 zabbix_mac.py --create-web-scenarios --url http://localhost:8080 --username Admin --password zabbix --db-host localhost --db-port 5432 --db-name zabbix_mac --db-user fan
   ```

5. **创建触发器**：
   ```bash
   python3 zabbix_mac.py --create-web-scenario-triggers --url http://localhost:8080 --username Admin --password zabbix --db-host localhost --db-port 5432 --db-name zabbix_mac --db-user fan
   ```

## 注意事项

1. **Zabbix API 版本**：该工具适用于 Zabbix 5.0 版本，不同版本的 API 可能存在差异。

2. **权限要求**：执行操作的 Zabbix 用户需要具有相应的权限（如创建主机、监控项、触发器等）。

3. **数据库连接**：确保 PostgreSQL 数据库服务正在运行，并且提供的数据库用户具有足够的权限。

4. **Web 场景触发器**：创建触发器前，必须先创建对应的 Web 场景监控。

5. **表达式格式**：触发器表达式使用 `{host:web.test.fail[name].count(#3,0,ne)}>2` 格式，表示连续 3 次检查失败则触发告警。

## 故障排除

### 常见错误

| 错误信息 | 可能原因 | 解决方案 |
|----------|----------|----------|
| `502 Server Error: Bad Gateway` | Zabbix API URL 不正确或服务器未运行 | 检查 Zabbix 服务器状态和 API URL |
| `Invalid params., unexpected parameter "tags"` | Zabbix 5.0 API 不支持该参数 | 该问题已在代码中修复 |
| `Application with applicationid "xxx" does not exist` | 指定的应用程序不存在 | 移除 `applicationid` 参数或使用正确的 ID |
| `Invalid parameter "/1": unexpected parameter "hostid/hosts"` | Zabbix 5.0 API 创建触发器不需要该参数 | 该问题已在代码中修复 |

### 日志查看

工具执行时会输出详细的日志信息，可以根据日志定位问题所在。

---

**文档版本**: 1.0  
**生成日期**: 2026年4月  
**适用工具**: zabbix_mac.py