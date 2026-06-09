# Zabbix Monitor as Code (MaC) — 产品需求文档 (PRD)

> **版本**: v1.0.0  
> **更新日期**: 2026-06-09  
> **分支**: dev1.0.0  
> **作者**: Dingfan

---

## 1. 产品概述

### 1.1 产品名称

**Zabbix Monitor as Code (MaC) — 监控审核和自动化控制中心**

### 1.2 产品定位

面向证券行业多机房 Zabbix 监控环境的声明式配置管理平台。通过将监控配置代码化、审核流程化，实现监控项（Items）、触发器（Triggers）、自动发现规则（LLD）及 Web 场景的版本控制、自动化同步和合规审核。

### 1.3 核心价值

| 痛点 | 解决方案 |
|------|----------|
| 监控配置手动操作，易出错 | 声明式配置，从数据库一键同步到 Zabbix |
| 多机房（深交所/上交所 × 证联网/互联网）配置不一致 | 按环境隔离的 Zabbix API 端点，分别同步 |
| 监控变更无审核追溯 | 复核表机制 + 确认/取消确认状态流转 |
| 配置与 Zabbix 实际状态脱节 | StatusVerifier 实时核验，对比数据库与线上差异 |
| 批量导入导出困难 | Excel 导入/导出功能 |

### 1.4 目标用户

- **运维工程师**: 管理监控模板、同步配置到 Zabbix
- **审核人员**: 通过 Web 界面审核监控项/触发器的变更
- **系统管理员**: 管理主机资产、自动发现规则

---

## 2. 系统架构

### 2.1 技术栈

| 层级 | 技术 | 版本 |
|------|------|------|
| 后端框架 | Flask | 3.1.3 |
| 数据库 | PostgreSQL (schema: `zabbix_mac`) | 12 |
| 前端 | Bootstrap 5 + Jinja2 模板 | 5.3 / 3.1.6 |
| 核心引擎 | Python 3 (zabbix_mac.py) | 3.12 |
| Zabbix API | Zabbix 5.0 LTS JSON-RPC | 5.0 |
| 数据处理 | pandas + openpyxl | 2.3.2 / 3.1.5 |
| 部署 | Docker Compose | — |

### 2.2 系统组件

```
┌─────────────────────────────────────────────────────┐
│                   Web 管理界面 (Flask)                │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────────┐ │
│  │ 模板管理  │ │ 主机管理  │ │  复核表管理 (核心)    │ │
│  │ 监控项管理│ │ 触发器管理│ │  确认/核验/导入导出   │ │
│  │ LLD 管理 │ │ 原型管理  │ │  环境同步             │ │
│  └──────────┘ └──────────┘ └──────────────────────┘ │
├─────────────────────────────────────────────────────┤
│              核心引擎 (zabbix_mac.py)                │
│  ┌────────────┐ ┌──────────┐ ┌──────────────────┐  │
│  │ SyncEngine │ │ConfigLoad│ │ StatusVerifier   │  │
│  │ (并发同步)  │ │ (DB加载) │ │ (线上状态核验)    │  │
│  └────────────┘ └──────────┘ └──────────────────┘  │
├─────────────────────────────────────────────────────┤
│            PostgreSQL (schema: zabbix_mac)           │
│  items │ triggers │ discovery_rules │ hosts         │
│  items_review │ triggers_review │ templates         │
│  item_prototypes │ trigger_prototypes │ ...         │
├─────────────────────────────────────────────────────┤
│                  Zabbix 5.0 API                      │
│  深交所证联网 │ 深交所互联网 │ 上交所证联网 │ 上交所互联网 │
└─────────────────────────────────────────────────────┘
```

### 2.3 核心文件

| 文件 | 说明 |
|------|------|
| `app.py` | Flask Web 应用，含全部路由和业务逻辑 |
| `zabbix_mac.py` | 核心引擎：同步、核验、导入导出 |
| `CODE_WIKI.md` | 项目技术文档 |
| `ZABBIX_MAC_USAGE_MANUAL.md` | 使用手册 |

---

## 3. 功能需求

### 3.1 模块总览

```
Zabbix MaC
├── 1. 模板管理
│   ├── 模板列表查看
│   └── 模板详情查看
├── 2. 监控项管理 (Items)
│   ├── CRUD 操作
│   └── 关联模板/主机
├── 3. 触发器管理 (Triggers)
│   ├── CRUD 操作
│   └── 触发器表达式编辑
├── 4. 主机管理 (Hosts)
│   ├── CRUD 操作
│   ├── 从 sub_assets 同步资产 ★v1.0.0
│   └── 按模板/名称搜索
├── 5. 自动发现规则 (LLD)
│   ├── 规则查看/编辑
│   └── 过滤条件管理
├── 6. 原型管理
│   ├── 监控项原型 (Item Prototypes)
│   └── 触发器原型 (Trigger Prototypes)
├── 7. 复核表系统 (核心) ★★★
│   ├── 监控项复核表 (items_review)
│   ├── 触发器复核表 (triggers_review)
│   ├── 监控项原型复核表
│   ├── 触发器原型复核表
│   ├── Web 场景复核表
│   ├── 初始化复核表 (从主表导入)
│   ├── 确认/取消确认状态流转
│   ├── Excel 导出/导入 ★v1.0.0
│   ├── 复核表直接添加监控项/触发器 ★v1.0.0
│   ├── 按环境同步到 Zabbix ★v1.0.0
│   └── 状态核验 (StatusVerifier) ★v1.0.0
├── 8. Web 场景管理
│   ├── Web 场景列表
│   ├── 创建 Web 场景到 Zabbix
│   └── 创建 Web 场景触发器
├── 9. 全局搜索
│   └── 跨实体模糊搜索 API
└── 10. 系统信息
    └── 各表数据量统计
```

### 3.2 复核表系统（核心功能详细说明）

#### 3.2.1 复核表数据结构

每张复核表包含原始表全部字段，外加：

| 扩展字段 | 类型 | 说明 |
|----------|------|------|
| `host_ip` | VARCHAR | 关联主机 IP |
| `modified` | BOOLEAN | 是否被修改 |
| `confirmed` | BOOLEAN | 是否已确认 |
| `status_verification` | VARCHAR | 状态核验结果: `verified` / `mismatch` / `not_found` / `pending` |

#### 3.2.2 复核表工作流

```
主表数据 ──初始化──> 复核表 (confirmed=false, status_verification='pending')
                         │
                    ┌─────┴─────┐
                    ▼           ▼
               编辑修改      确认审核
              (modified)   (confirmed)
                    │           │
                    └─────┬─────┘
                          ▼
                    同步到 Zabbix
                    (按环境选择)
                          │
                          ▼
                    状态核验
              (StatusVerifier)
              verified / mismatch / not_found
```

#### 3.2.3 多机房环境同步 ★v1.0.0

支持 4 个 Zabbix 环境独立同步：

| 环境 | API 配置 |
|------|----------|
| 深交所证联网 | `ZABBIX_SZSE_ZW_*` |
| 深交所互联网 | `ZABBIX_SZSE_HLW_*` |
| 上交所证联网 | `ZABBIX_SSE_ZW_*` |
| 上交所互联网 | `ZABBIX_SSE_HLW_*` |

每个环境有独立的 API URL、用户名、密码（通过环境变量配置）。

### 3.3 v1.0.0 新增功能清单

| 功能 | 描述 |
|------|------|
| **状态核验 (StatusVerifier)** | 从 Zabbix API 拉取实际状态，对比复核表数据，标注 verified/mismatch/not_found |
| **主机资产同步** | 从 ops.sub_assets 表增量同步主机资产到 zabbix_mac.hosts，支持 UPSERT |
| **复核表 Excel 导出/导入** | items_review 和 triggers_review 支持 Excel 文件下载和上传导入 |
| **复核表直接添加** | 在 items-review 和 triggers-review 页面工具栏添加"添加监控项"/"添加触发器"按钮 |
| **复核表初始化按钮** | 在复核表页面工具栏添加"初始化"按钮，支持批量初始化复核数据 |
| **环境特异性同步** | Web UI 中选择目标环境，将已确认的复核记录同步到指定 Zabbix 环境 |
| **复核表筛选功能** | 按主机 IP、模板名、确认状态等维度筛选复核记录 |
| **触发器表列精简** | triggers 主表移除 system 和 subsystem 列 |
| **修复 system/subsystem 字段** | 在复核表编辑模态框和编辑表单中补全缺失的 system/subsystem 字段 |
| **修复自动发现规则同步** | 修复 LLD 过滤条件未同步到 Zabbix 的问题 |
| **ID 排序优化** | HTML 页面按 ID 从小到大排序显示 |
| **Flask debug 模式关闭** | 防止僵尸进程 |
| **部署支持** | 导出 SQL 数据（数据导出/）和 pip 离线包（packs/） |

---

## 4. 数据库设计

### 4.1 Schema 概览

所有表位于 PostgreSQL schema `zabbix_mac` 下。

### 4.2 核心业务表

| 表名 | 说明 | 主键 |
|------|------|------|
| `templates` | 监控模板 | id |
| `hosts` | 主机资产（支持从 sub_assets 同步） | id (UNIQUE: name) |
| `host_templates` | 主机-模板关联 | id |
| `host_extra_items` | 主机额外监控项 | id |
| `items` | 监控项模板 | id |
| `triggers` | 触发器模板 | id |
| `discovery_rules` | 自动发现规则 | id |
| `filter_conditions` | LLD 过滤条件 | id |
| `item_prototypes` | 监控项原型 | id |
| `trigger_prototypes` | 触发器原型 | id |
| `webscenario_items` | Web 场景监控项 | id |

### 4.3 复核表

| 表名 | 对应主表 | 附加字段 |
|------|----------|----------|
| `items_review` | items | host_ip, modified, confirmed, status_verification |
| `triggers_review` | triggers | host_ip, modified, confirmed, status_verification |
| `item_prototypes_review` | item_prototypes | host_ip, modified, confirmed |
| `trigger_prototypes_review` | trigger_prototypes | host_ip, modified, confirmed |
| `webscenario_items_review` | webscenario_items | host_ip, modified, confirmed |

---

## 5. 非功能需求

### 5.1 性能

- 并发同步: 支持 `--workers` 参数配置并发线程数（默认 5）
- 数据库连接: psycopg2 直连
- 同步支持 dry-run 模式预先评估变更

### 5.2 安全

- Zabbix API 凭据通过环境变量注入，不硬编码
- Flask debug 模式已关闭（生产部署）
- Web 应用监听 `0.0.0.0:5001`

### 5.3 兼容性

- Zabbix 5.0 LTS API
- PostgreSQL 12
- Python 3.12

### 5.4 测试覆盖

| 测试文件 | 覆盖范围 |
|----------|----------|
| `test_app.py` | Flask Web 路由 |
| `test_zabbix_client.py` | Zabbix API 客户端 |
| `test_config_loader.py` | 配置加载器 |
| `test_sync_engine.py` | 同步引擎 |
| `test_concurrency.py` | 并发同步 |
| `test_performance.py` | 性能测试 |
| `test_security.py` | 安全性测试 |
| `test_environment.py` | 环境配置测试 |

---

## 6. 部署说明

### 6.1 依赖

- Python 3.12 + pip 包（`requirements.txt`，离线包在 `packs/` 目录）
- PostgreSQL 12（Docker Compose 提供）
- Zabbix Server 5.0（Docker Compose 提供）

### 6.2 部署步骤

1. 启动 Docker Compose 环境: `docker-compose up -d`（PostgreSQL + Zabbix Server）
2. 安装 Python 依赖: `pip install -r requirements.txt`（或从 `packs/` 离线安装）
3. 导入数据库表结构和数据: 执行 `数据导出/` 下的 SQL 文件
4. 启动 Web 服务: `python app.py`（监听端口 5001）
5. 配置环境变量（各机房 Zabbix API 凭据）

### 6.3 环境变量

```bash
ZABBIX_SZSE_ZW_URL      # 深交所证联网 API URL
ZABBIX_SZSE_ZW_USER     # 用户名
ZABBIX_SZSE_ZW_PASS     # 密码
ZABBIX_SZSE_HLW_URL     # 深交所互联网 API URL
ZABBIX_SZSE_HLW_USER
ZABBIX_SZSE_HLW_PASS
ZABBIX_SSE_ZW_URL       # 上交所证联网 API URL
ZABBIX_SSE_ZW_USER
ZABBIX_SSE_ZW_PASS
ZABBIX_SSE_HLW_URL      # 上交所互联网 API URL
ZABBIX_SSE_HLW_USER
ZABBIX_SSE_HLW_PASS
```

---

## 7. 路线图 / 后续规划

| 优先级 | 功能 | 说明 |
|--------|------|------|
| P0 | 复核表状态核验扩展 | 覆盖 item_prototypes_review 和 trigger_prototypes_review |
| P1 | Web 界面状态核验触发 | 当前仅 CLI 支持，计划加入 Web UI 按钮 |
| P1 | 用户认证与权限 | 当前无登录机制 |
| P2 | 操作审计日志 | 记录所有配置变更历史 |
| P2 | 批量操作增强 | 批量确认、批量同步 |
| P3 | API 接口开放 | RESTful API 供外部系统集成 |
| P3 | 仪表盘首页 | 可视化展示各环境配置一致性状态 |

---

## 8. 变更记录

| 日期 | 版本 | 变更内容 |
|------|------|----------|
| 2026-05-22 | — | 初始版本，项目基础功能 |
| 2026-06-04 | — | 实现状态核验功能 (StatusVerifier) |
| 2026-06-05 | — | Flask + PostgreSQL 环境就绪 |
| 2026-06-08 | — | 主机资产同步、复核表增强、Excel 导入导出 |
| 2026-06-09 | v1.0.0 | 部署支持（SQL 导出 + pip 离线包）、Bug 修复 |
