# ZAC (Zabbix MaC Review Platform) — 开发与架构规范

> **这是项目的最高上下文指南。** 所有开发、重构、UI 调整必须以本文档为基准。
> 详细文档见 [`CODE_WIKI.md`](./CODE_WIKI.md)，产品需求见 [`PRD.md`](./PRD.md)。

---

## 1. 项目概览与核心栈

| 层 | 技术 | 说明 |
|---|---|---|
| **Backend** | Python 3.12 + Flask | Jinja2 服务端渲染，116 routes，`app.py`（~7300 行） |
| **Database** | PostgreSQL + psycopg2 | DictCursor，原生 SQL（非 ORM），`config_loader.py` |
| **Frontend** | Bootstrap 5.3 + 原生 JS | **无 DataTables 库，无 jQuery**。纯 HTML `<table>` + CSS sticky 列 |
| **CSS** | Bootstrap Icons + `static/css/app.css` | 单一主样式表（~1140 行） |
| **JS** | `app.js` + `review_common.js` | 原生 ES5，无构建工具，无模块打包器 |
| **Integration** | Zabbix 5.0 JSON-RPC API | 通过 `pyzabbix` 库，`zabbix_mac.py`（~4800 行） |
| **Parser** | `xml_template_parser.py` | 模板 XML 导入解析器（标准库 xml，~400 行），供 `/base-template/import` 使用 |
| **Deploy** | Docker (Linux x86), 本地开发 (macOS ARM) | 开发端口 5050，容器端口 5000 |

> 行数与 routes 数为概数锚点（用于判断"该不该整读文件"），**勿作精确依据**；以 `wc -l` / `grep -c "@app.route"` 实测为准。

---

## 2. 核心业务逻辑与数据治理

### 2.1 单一事实来源 (Single Source of Truth)
**远程 Zabbix 5.0 API 为准。** 本地 PostgreSQL `*_review` 表仅记录审核状态与变更暂存（指纹比对 + 差异合并）。

### 2.2 术语与状态标准化

| 状态字段 | 允许值 | 说明 |
|---|---|---|
| `sync_status` | `synced`, `pending_confirm`(等同于空), `pending_delete` | 同步状态 |
| `status_verification` | `verified`, `mismatch`, `not_found`, 空(未核验) | Zabbix API 核验结果 |
| `change_type` | `new`, `update`, `delete` | 变更类型（行样式驱动） |
| `confirmed` | `true`/`false` | 确认状态（确认后不可撤销） |

- **同步状态文案**：统一为 `待同步` 与 `已同步`。**禁止出现 `待确认` 文案。**
- **审计终局性**：确认操作不可撤销。代码中不提供"取消确认"按钮，后端 unconfirm 路由已标记 deprecated。
- **确认按钮文案**：`change_type` 驱动 → `确认新增` (new) / `确认变更` (update) / `确认下线` (delete)
- **机房字段**：6 张 review 表均含 `in_room`（机房）列；6 条 list 路由统一支持 `ip/system/subsystem/room`（items 另有 `baseline`）服务端 ILIKE 筛选，机房控件用 datalist（取值 `DISTINCT in_room`）。**新增筛选字段必须 6 路由 + 6 模板联动，Tab 表单 hidden 区同步补齐**

### 2.3 6 大复核模块协同

| 模块 | Flask Route | 数据库表 | 模板 |
|---|---|---|---|
| 监控项复核 | `/items-review` | `items_review` | `items_review.html` |
| 触发器复核 | `/triggers-review` | `triggers_review` | `triggers_review.html` |
| 监控项原型复核 | `/item-prototypes-review` | `item_prototypes_review` | `item_prototypes_review.html` |
| 触发器原型复核 | `/trigger-prototypes-review` | `trigger_prototypes_review` | `trigger_prototypes_review.html` |
| Web 场景复核 | `/webscenarios-review` | `webscenarios_review` | `webscenarios_review.html` |
| Web 触发器复核 | `/web-triggers-review` | `web_triggers_review` | `web_triggers_review.html` |

**⚠️ 铁律：任何在 `items_review` 上的 UI 调整或公共逻辑变更，必须同步评估并更新至其他 5 个模块。**

**附属域（不属 6 模块联动集）**：**模板 XML 导入** `/base-template/import`（模板 `base_template_import.html` + 解析器 `xml_template_parser.py`）——解析 Zabbix XML 导出文件，幂等 Upsert 至 6 张基础表，用户输入的 `template_id` 值级绑定 `template_name` 列。修改解析/导入逻辑须同步 `tests/test_xml_template_import.py`。

### 2.4 共享模板片段
- `templates/_dashboard_cards.html` — KPI 统计大盘（6 个 review 页面共用）
- `templates/_batch_sync_modal.html` — 批量同步预览弹窗（6 个 review 页面共用）
- `templates/_pagination.html` — 统一分页组件

---

## 3. 前端与表格布局严格铁律

### 3.1 当前 Sticky 固定列布局（`app.css` 中 `.col-sticky` 系列，以类名定位勿用行号）

本项目的固定列采用**硬编码 CSS 偏移量**方案（非 JS 动态计算）：

```
左固定列:
  col-cb (checkbox):       width=36px, 无 sticky
  expand (展开按钮):       width=32px, 无 sticky
  col-sticky-l1 (ID):      left=0,    width=50px
  col-sticky-l2 (IP/主机): left=68px, width=140px    ← 68 = 36 + 32

右固定列 (从右边缘叠层):
  col-sticky-r1 (操作):     right=0,     width=100px
  col-sticky-r2 (状态核验): right=100px, width=80px
  col-sticky-r3 (确认状态): right=180px, width=80px
  col-sticky-r4 (同步状态): right=260px, width=80px
  col-sticky-r5 (修改状态): right=340px, width=80px
```

**关键 CSS 属性：**

```css
.table .col-sticky {
    position: sticky !important;
    z-index: 2;
}
.table thead .col-sticky {
    z-index: 3;
}
/* Sticky 列必须有不透明背景——否则滚动内容会透出 */
.table tbody .col-sticky {
    background: #fff !important;
}
/* 表格必须 border-collapse: collapse 以保证偏移计算一致 */
.data-card .table {
    border-collapse: collapse !important;
}
```

### 3.2 修改 Sticky 列偏移量的正确步骤

1. **先锁定盒模型宽度**：`.col-fw-*` 类用 `width + min-width + max-width` 三重锁定
2. **计算 left/right 偏移**：每个 sticky 列的 `left`/`right` = 其外侧所有列的 `width` 之和
3. **同步更新 `.col-sticky` 背景色声明**：`app.css` 中有 4 组背景色规则（tbody 白 / thead 灰 / striped 奇数行灰 / striped 偶数行白），必须都更新
4. **所有 6 个 review 模板的表头 `<th>` 和表体 `<td>` 必须使用相同的 CSS class**

### 3.3 DOM 列索引与表头严格 1:1 对齐

- `<thead>` 中的 `<th>` 数量必须与 `<tbody>` 中的 `<td>` 数量 **100% 严格一致**。
- 控制列（复选框 `col-cb`、展开按钮 `32px`）在表头必须保留对应的占位 `<th>`。
- 本项目 **不使用 DataTables**——表格是纯 HTML + Jinja2 for-loop 渲染，列宽度由 CSS 类控制，不涉及 JS `columns` 配置。

### 3.4 侧边栏折叠触发表格重绘

侧边栏折叠时，`.app-main` 执行 `margin-left: 200px → 0` 的 0.3s CSS transition。Sticky 定位的列不会自动重算位置。

**当前方案**（`app.js` DOMContentLoaded 内 transitionend 监听段落）：
1. 监听 `.app-main` 的 `transitionend` 事件（`propertyName === 'margin-left'`）
2. 通过 `transform: translateZ(0)` + `requestAnimationFrame` 触发浏览器强制重绘
3. `setTimeout(350ms)` 兜底，处理 transition 未触发情况

### 3.5 技术列切换（TechViewToggle）

`review_common.js` 中的 `TechViewToggle` 模块控制 `.col-tech` 列的显隐：

- **不是** DataTables `columns().visible()`——是 `el.style.display = 'none'`。
- CSS 配合 `.col-tech[style*="display: none"]` 实现 collapse 动画（`opacity: 0; max-width: 0; padding: 0`）。
- 持久化 key：`localStorage` → `review_techView_{pageKey}`。
- 6 个页面统一使用 `TechViewToggle.toggle('<pageKey>')` + `TechViewToggle.init('<pageKey>', 'techViewToggle')`。

### 3.6 BatchSync 勾选契约（`app.js`）

- 勾选状态持久化于 `sessionStorage`，key 为 `selectedIds_<table>`，目的：**跨分页 reload 保留勾选**。勿因"勾选莫名恢复"而删除该机制——分页场景依赖它。
- **同步完成必须释放勾选**：两条完成路径都要接 `BatchSync.clearSelection()`——① `applySync()`（差异预览弹窗"确认同步下发"，日常主路径）；② `ReviewSyncPoller.poll()` 的 `!data.running` 分支（全量同步/Web 场景）。**改动同步行为时逐一核对这两条路径，漏一条即复现"同步后勾选不释放"缺陷。**
- 同步失败分支**不得**释放勾选（用户需保留选择修正后重试）。

### 3.7 侧边栏分组持久化（`app.js` "Sidebar Group Collapse Persistence" 段）

- 分组展开状态持久化于 `localStorage`（key `sidebarGroupOpen_<groupId>`）；当前路由命中子菜单所在分组自动展开。
- **⚠️ 陷阱：Bootstrap 5.3 的 Collapse 构造器会自动执行一次 `toggle()`**——恢复状态时严禁调用 `bootstrap.Collapse.getOrCreateInstance(el)`（会强制开↔关翻转）。只能直接改 DOM：`groupEl.classList.toggle('show', wantShow)` + 同步触发器的 `aria-expanded`。
- Flask 生产模式（`debug: false`）不热载模板与 Python 代码——**改模板/app.py 后必须重启 dev 服务器**才能验证；静态 JS/CSS 每请求读盘即时生效。

---

## 4. 代码架构与重构原则

### 4.1 文件职责边界

| 文件 | 职责 | 不可放入 |
|---|---|---|
| `app.js` | 全局行为（侧边栏、搜索、Toast、CSRF fetch 封装、BatchSync 勾选/同步预览、confirm 按钮） | 页面专属业务逻辑 |
| `review_common.js` | 复核页面共享模块（ReviewDashboard、TechViewToggle、ReviewSyncPoller、RenderHelpers、TriggerDrillDown、ReviewActions） | 页面专属逻辑 |
| 各模板 `<script>` 块 | 该页面专属逻辑（初始化、特定 CRUD 操作、行展开） | 跨页面共享逻辑 |
| `xml_template_parser.py` | Zabbix 模板 XML 导出文件的解析（items/triggers/LLD/原型/过滤器 → dict） | SQL 落库逻辑（归 app.py 路由层） |

### 4.2 重构原则

1. **优先抽取至 `review_common.js`**：任何被 ≥2 个页面使用的函数/模块必须放入共享 JS。
2. **CSS 类优于内联样式**：禁止在 HTML 中写 `style="..."`，统一通过 `app.css` 中的语义化 CSS 类控制。
3. **所有 fetch 的 POST/PUT/DELETE 自动带 CSRF token**：`app.js` 已包装 `window.fetch`，不要手动加 `X-CSRF-Token` 头。
4. **Toast 消息统一走 `showToast(message, type)`**：type 为 `success | danger | warning | info`。
5. **确认操作统一走 `toggleConfirmRow(id, btn, confirmUrl)`**：定义在 `app.js` 中，各页面通过 `toggleConfirmRow` 调用。

### 4.3 模板继承链

```
base.html
  ├─ items_review.html
  ├─ triggers_review.html
  ├─ item_prototypes_review.html
  ├─ trigger_prototypes_review.html
  ├─ webscenarios_review.html
  ├─ web_triggers_review.html
  ├─ items.html
  ├─ triggers.html
  ├─ ... (其余管理页面)
```

每个 review 模板覆盖 `{% block page_title %}`, `{% block toolbar %}`, `{% block content %}`, `{% block scripts_extra %}`。

---

## 5. 测试规范

| 命令 | 用途 |
|---|---|
| `python3 -m pytest tests/ -q` | 全量测试（通过数以实际输出为准，勿在文档硬编码） |
| `python3 -m pytest tests/ -q --tb=short` | 带简要堆栈 |
| `python3 -m pytest tests/test_helpers.py -v` | 单元测试 |

- **Mock 策略**：所有测试纯 mock（无 live DB，无真实 Zabbix API）。
- **CSRF 绕过**：测试中 `app.before_request_funcs[None] = []` 清除 CSRF 校验。
- **APP_SECRET_KEY**：`conftest.py` 已通过 `os.environ.setdefault()` 设置默认值。
- **数据库连接**：所有测试 mock `get_db_connection`，返回 `MagicMock` cursor。

---

## 6. 关键约定速查

- ✅ 表中新加列 → 同步更新 `<thead>` 的两个 `<tr>` + `<tbody>` 的 `<td>` → 检查 sticky 偏移量
- ✅ 修改 sticky 列宽度 → 更新 CSS `left`/`right` 值 → 检查 6 个模板一致
- ✅ 修改 `items_review.html` 的 DOM 结构 → 同步检查其余 5 个 review 模板
- ✅ 新增 JS 函数被 ≥2 页面使用 → 必须移入 `review_common.js`
- ✅ 同步文案 → `待同步` / `已同步`（**禁止** `待确认`）
- ✅ pyzabbix 一切 `.get()` 调用 → **必须关键字传参**（位置字典会静默吞掉 filter 等参数，真实踩坑）
- ✅ 改同步/勾选行为 → 核对 `applySync` 与 `ReviewSyncPoller` 两条完成路径（见 3.6）
- ✅ 改模板/后端代码 → 重启 dev 服务器再验证（`debug: false` 无热载，见 3.7）
- ❌ 禁止新增"取消确认"/"撤销"按钮或路由
- ❌ 禁止在 HTML 中写内联 `style="..."`（除 `width`/`min-width` 等布局关键属性）
- ❌ 禁止引入新的 CSS/JS 框架或库

---

## 7. 环境变量

| 变量 | 说明 | 必需 |
|---|---|---|
| `APP_SECRET_KEY` | Flask secret_key（覆盖 config.yaml `app.secret_key`） | ✅ 生产必需 |
| `APP_CONFIG` | 配置文件路径（默认 `config.yaml`） | ❌ |
| `DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASSWORD` | 数据库连接（按 key 覆盖 config.yaml `database.*`） | ❌ |
| `ZABBIX_<KEY>_URL/_USER/_PASS` | Zabbix 环境凭据（按环境 key 覆盖，如 `ZABBIX_SZSE_ZW_URL`） | ❌ |
| `TEST_DB_HOST/PORT/NAME/USER/PASSWORD` | 测试数据库 | ❌ |
| `TEST_ZABBIX_URL/USERNAME/PASSWORD` | 测试 Zabbix API | ❌ |

优先级：环境变量 > config.yaml > 内置默认（统一由 `config_loader.py` 处理，勿在业务代码直接读 os.environ）。

---

*最后更新：2026-08-31 · 本文档原则段落求稳定、事实段落求新；所有计数/行号均为概数锚点，以代码库实测为准*
