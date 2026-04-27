# 数据库迁移规划：从 YAML 到 PostgreSQL 表

## 1. 项目现状分析

### 1.1 现有架构

- **当前输入方式**：使用 YAML 配置文件（monitor_config.yaml）和模板文件（base_templates/*.yaml）
- **现有数据库结构**：已存在完整的表结构，包括：
  - `items` - 存储监控项模板
  - `triggers` - 存储触发器模板
  - `discovery_rules` - 存储自动发现规则模板
  - `filter_conditions` - 存储自动发现规则的过滤条件
  - `item_prototypes` - 存储监控项原型
  - `trigger_prototypes` - 存储触发器原型
  - `templates` - 存储模板信息

### 1.2 现有代码逻辑

- `ConfigLoader` 类已经实现了从数据库加载模板的功能
- 模板加载优先级：先从数据库加载，失败后回退到 YAML 文件
- 主机配置目前仅从 YAML 文件加载

## 2. 迁移规划

### 2.1 数据库表扩展

需要添加以下表来存储主机配置信息：

#### 2.1.1 主机表（hosts）

```sql
CREATE TABLE IF NOT EXISTS hosts (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,  -- 主机名
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 2.1.2 主机模板关联表（host_templates）

```sql
CREATE TABLE IF NOT EXISTS host_templates (
    id SERIAL PRIMARY KEY,
    host_id INTEGER NOT NULL REFERENCES hosts(id) ON DELETE CASCADE,
    template_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(host_id, template_name)
);
```

#### 2.1.3 主机额外监控项表（host_extra_items）

```sql
CREATE TABLE IF NOT EXISTS host_extra_items (
    id SERIAL PRIMARY KEY,
    host_id INTEGER NOT NULL REFERENCES hosts(id) ON DELETE CASCADE,
    item_key VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    type INTEGER NOT NULL,
    value_type INTEGER NOT NULL,
    delay VARCHAR(50) NOT NULL,
    description TEXT,
    units VARCHAR(50),
    multiplier INTEGER DEFAULT 0,
    delta INTEGER DEFAULT 0,
    history INTEGER DEFAULT 7,
    trends INTEGER DEFAULT 365,
    status INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(host_id, item_key)
);
```

### 2.2 代码修改规划

#### 2.2.1 ConfigLoader 类修改

1. **添加从数据库加载主机配置的方法**：
   - `load_host_config_from_db(self, host_name: str) -> Dict[str, Any]`
   - 从 `hosts`、`host_templates` 和 `host_extra_items` 表加载主机配置

2. **修改 get_host_config 方法**：
   - 优先从数据库加载主机配置
   - 失败后回退到 YAML 文件

3. **修改 build_host_config 方法**：
   - 保持现有逻辑，但使用从数据库加载的主机配置

#### 2.2.2 配置加载流程修改

1. **修改 load_config 方法**：
   - 当启用数据库配置时，直接从数据库加载所有主机配置
   - 不再加载 YAML 配置文件

2. **添加数据库配置验证**：
   - 确保数据库连接正常
   - 确保必要的表结构存在

### 2.3 数据迁移策略

1. **现有 YAML 配置迁移**：
   - 编写迁移脚本，将现有的 YAML 配置导入到数据库中
   - 包括主机配置、模板配置等

2. **验证迁移**：
   - 确保迁移后的数据与原 YAML 配置一致
   - 运行测试，确保系统正常工作

## 3. 实现比较逻辑

### 3.1 监控项比较

1. **从数据库加载目标配置**：
   - 从 `items` 表加载监控项模板
   - 从 `host_extra_items` 表加载主机额外监控项

2. **从 Zabbix API 获取当前配置**：
   - 使用 `ZabbixClient.get_managed_items()` 获取当前监控项

3. **比较逻辑**：
   - 使用 `ZabbixClient.calculate_fingerprint()` 计算指纹
   - 比较指纹，确定需要创建、更新或删除的监控项

### 3.2 触发器比较

1. **从数据库加载目标配置**：
   - 从 `triggers` 表加载触发器模板

2. **从 Zabbix API 获取当前配置**：
   - 使用 `ZabbixClient.get_managed_triggers()` 获取当前触发器

3. **比较逻辑**：
   - 使用 `ZabbixClient.calculate_fingerprint()` 计算指纹
   - 比较指纹，确定需要创建或更新的触发器

### 3.3 自动发现规则比较

1. **从数据库加载目标配置**：
   - 从 `discovery_rules` 表加载自动发现规则
   - 从 `filter_conditions` 表加载过滤条件
   - 从 `item_prototypes` 表加载监控项原型
   - 从 `trigger_prototypes` 表加载触发器原型

2. **从 Zabbix API 获取当前配置**：
   - 使用 `ZabbixClient.get_managed_discovery_rules()` 获取当前自动发现规则
   - 使用 `ZabbixClient.get_item_prototypes()` 获取当前监控项原型
   - 使用 `ZabbixClient.get_trigger_prototypes()` 获取当前触发器原型

3. **比较逻辑**：
   - 比较规则、过滤条件、原型的指纹
   - 确定需要创建、更新或删除的规则和原型

## 4. 运行方式修改

### 4.1 命令行参数修改

- 保持现有参数不变
- 添加 `--db-only` 参数，强制使用数据库配置

### 4.2 运行流程修改

1. **解析命令行参数**
2. **初始化数据库连接**
3. **加载数据库配置**
4. **同步所有主机**
5. **生成变更报告**

## 5. 实施步骤

### 5.1 准备阶段

1. **备份现有 YAML 配置**
2. **创建新的数据库表**
3. **编写数据迁移脚本**

### 5.2 实施阶段

1. **执行数据迁移**
2. **修改代码**
3. **测试运行**

### 5.3 验证阶段

1. **运行 dry-run 模式验证**
2. **运行实际同步验证**
3. **检查 Zabbix 中的配置**

## 6. 优势与风险

### 6.1 优势

- **集中管理**：所有配置集中存储在数据库中，便于管理
- **版本控制**：可以通过数据库事务和备份实现配置的版本控制
- **灵活性**：可以通过 SQL 查询快速分析和修改配置
- **安全性**：可以通过数据库权限控制配置的访问

### 6.2 风险

- **迁移风险**：数据迁移过程中可能出现数据丢失或错误
- **依赖风险**：系统将依赖数据库服务的可用性
- **学习成本**：团队需要熟悉数据库操作

## 7. 结论

将脚本的输入从 YAML 切换到数据库表的形式是可行的，并且具有许多优势。通过合理的规划和实施，可以实现平滑迁移，同时提高系统的可维护性和可靠性。

实施过程中需要注意数据迁移的准确性和代码修改的兼容性，确保系统在迁移后能够正常工作。