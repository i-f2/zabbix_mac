/**
 * review_common.js — Shared helpers for all review pages
 * Relies on: app.js (showToast, BatchSync)
 * Loaded via {% block scripts_extra %} in each review template
 */

// ========================================================
// ReviewDashboard — KPI summary cards + severity maps
// ========================================================
window.ReviewDashboard = {
    PRIORITY_LABELS: {0:'未分类',1:'信息',2:'警告',3:'一般',4:'严重',5:'灾难'},
    PRIORITY_COLORS: {0:'#6c757d',1:'#17a2b8',2:'#ffc107',3:'#fd7e14',4:'#dc3545',5:'#dc3545'},
    PRIORITY_BS:    {0:'secondary',1:'info',2:'warning',3:'warning',4:'danger',5:'danger'},

    fetchStats: function(tableName) {
        fetch('/api/review/dashboard-stats?table=' + encodeURIComponent(tableName))
            .then(function(r) { return r.json(); })
            .then(function(resp) {
                if (!resp || !resp.success) return;
                var d = resp.data;
                var setText = function(id, val) {
                    var el = document.getElementById(id);
                    if (el) el.textContent = val;
                };
                var setWidth = function(id, pct) {
                    var el = document.getElementById(id);
                    if (el) el.style.width = pct + '%';
                };
                setText('dashTotal', d.total);
                setText('dashConfirmed', d.confirmed);
                setText('dashPending', d.pending);
                setWidth('dashProgressBar', d.completion_pct);
                setText('dashCompletionText', '完成率: ' + d.completion_pct + '%');
                setText('dashSynced', d.synced);
                setText('dashPendingSync', d.pending_sync + d.pending_delete);
                var warnEl = document.getElementById('dashSyncWarn');
                var warnTextEl = document.getElementById('dashSyncWarnText');
                var pendingTotal = d.pending_sync + d.pending_delete;
                if (warnEl && warnTextEl) {
                    if (pendingTotal > 0) {
                        warnEl.style.display = '';
                        warnTextEl.textContent = ' 还有 ' + pendingTotal + ' 条待同步';
                    } else {
                        warnEl.style.display = 'none';
                        warnTextEl.textContent = '全部已同步';
                    }
                }
                setText('dashTriggersTotal', d.triggers_total);
                var sevContainer = document.getElementById('dashSeverityBars');
                if (sevContainer) {
                    sevContainer.innerHTML = this._renderSeverityBars(d.triggers_by_priority || {});
                }
            })
            .catch(function() {});
    },

    _renderSeverityBars: function(byPriority) {
        var vals = Object.values(byPriority).map(Number);
        var maxCount = vals.length ? Math.max.apply(null, vals) : 1;
        var html = '';
        [5,4,3,2,1,0].forEach(function(p) {
            var cnt = byPriority[String(p)] || 0;
            var pct = cnt > 0 ? Math.round(cnt / maxCount * 100) : 0;
            html += '<div class="d-flex align-items-center mb-1" style="font-size:11px;">' +
                '<span style="width:40px;">' + (window.ReviewDashboard.PRIORITY_LABELS[p] || '?') + '</span>' +
                '<div class="flex-grow-1 mx-1 prog-bar"><div style="width:' + pct + '%;height:8px;background:' + (window.ReviewDashboard.PRIORITY_COLORS[p] || '#ccc') + ';border-radius:3px;"></div></div>' +
                '<span style="width:20px;text-align:right;">' + cnt + '</span></div>';
        });
        return html;
    }
};

// ========================================================
// TechViewToggle — Business vs Technical column visibility
// ========================================================
window.TechViewToggle = {
    _getKey: function(pageKey) { return 'review_techView_' + pageKey; },

    isOn: function(pageKey) {
        return localStorage.getItem(this._getKey(pageKey)) === 'true';
    },

    apply: function(pageKey) {
        var show = this.isOn(pageKey);
        document.querySelectorAll('.col-tech').forEach(function(el) {
            el.style.display = show ? '' : 'none';
        });
        var btn = document.getElementById('techViewToggle');
        if (btn) {
            btn.innerHTML = show
                ? '<i class="bi bi-gear-fill"></i> 隐藏技术细节'
                : '<i class="bi bi-gear"></i> 显示技术细节';
            if (show) btn.classList.add('active'); else btn.classList.remove('active');
        }
    },

    toggle: function(pageKey) {
        localStorage.setItem(this._getKey(pageKey), (!this.isOn(pageKey)).toString());
        this.apply(pageKey);
        // Force sticky column reposition after column visibility change
        if (window.recalcTableLayouts) {
            requestAnimationFrame(function() { window.recalcTableLayouts(); });
        }
    },

    init: function(pageKey, toggleBtnId) {
        var self = this;
        var ready = function() { self.apply(pageKey); };
        if (document.readyState !== 'loading') { ready(); }
        else { document.addEventListener('DOMContentLoaded', ready); }
    }
};

// ========================================================
// ReviewSyncPoller — shared sync progress polling
// ========================================================
// 后台任务阶段 → 文案。与 app.py 的 _JobContext.report_phase() 约定一一对应。
var SYNC_PHASE_LABELS = {
    load:   '正在读取现有记录',
    source: '正在读取上游模板数据',
    diff:   '正在比对差异',
    build:  '正在组装记录',
    insert: '正在写入新增',
    update: '正在更新变更',
    delete: '正在标记删除',
    hosts:  '正在同步主机资产',
    cleanup: '正在清理失效绑定'
};

window.ReviewSyncPoller = {
    _timer: null,
    _modal: null,
    _settled: false,

    // 给数字加千分位：1200 -> 1,200（ES5 正则写法，无 Intl 依赖）
    _fmt: function(n) {
        return String(n == null ? 0 : n).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    },

    // kind: 'init' 用于初始化任务，文案与按钮保持"同步"语义时用默认值
    start: function(syncFn, opts) {
        opts = opts || {};
        var modalEl = document.getElementById('syncProgressModal');
        if (!modalEl) { showToast('同步进度弹窗未找到', 'danger'); return; }
        var modal = new bootstrap.Modal(modalEl, {backdrop: 'static', keyboard: false});
        modal.show();

        var self = this;
        self._modal = modal;
        self._opts = opts;
        self._settled = false;
        self._sawRunning = false;    // 是否观察到任务真正开始（running=true）
        self._requestDone = false;   // 发起请求是否已返回
        self._requestFailed = null;  // 请求本身的网络错误
        self._conflict = null;       // 409 并发冲突的提示语

        var title = document.getElementById('syncProgressTitle');
        if (title) title.textContent = opts.title || '同步进度';
        var bar = document.getElementById('syncProgressBar');
        var text = document.getElementById('syncProgressText');
        if (bar) { bar.style.width = '0%'; bar.textContent = '0%'; }
        if (text) text.textContent = opts.startText || '发起请求...';
        var warnList = document.getElementById('syncWarnList');
        if (warnList) warnList.innerHTML = '';
        var errList = document.getElementById('syncErrorList');
        if (errList) errList.innerHTML = '';
        var stopBtn = document.getElementById('stopSyncBtn');
        if (stopBtn) { stopBtn.disabled = false; stopBtn.innerHTML = '<i class="bi bi-stop-circle"></i> 停止同步'; }

        // fetch 对 409 也会 resolve，.catch 不触发 —— 必须显式看状态码，
        // 否则并发冲突会被当成"任务已结束"，导致页面在同步未跑的情况下刷新。
        var req = syncFn();
        if (req && req.then) {
            req.then(function(resp) {
                if (!resp) return;
                if (resp.status === 409) {
                    self._conflict = '另一个同步/初始化操作正在进行，请稍后再试';
                    return resp.json().then(function(d) {
                        if (d && d.message) self._conflict = d.message;
                    }).catch(function() {});
                }
                // 非 2xx 一律视为"任务没跑起来"。同样因为 fetch 只对网络故障 reject，
                // 不显式看状态码的话 400/500/504 会被当成成功并静默刷新页面
                // （504 正是本次改造要消灭的症状，被静默掉最难排查）。
                if (resp.ok === false) {
                    return resp.json().then(function(d) {
                        self._requestFailed = (d && d.message) || ('HTTP ' + resp.status);
                    }).catch(function() {
                        self._requestFailed = 'HTTP ' + resp.status;   // 非 JSON 错误页（如网关 HTML）
                    });
                }
            }).catch(function(e) {
                self._requestFailed = e && e.message ? e.message : String(e);
            }).then(function() {
                self._requestDone = true;
            });
        } else {
            self._requestDone = true;
        }

        if (self._timer) clearInterval(self._timer);
        self._timer = setInterval(function() { self.poll(); }, 500);
    },

    poll: function() {
        var self = window.ReviewSyncPoller;
        fetch('/review/sync-progress')
            .then(function(r) { return r.json(); })
            .then(function(data) {
                if (data.running) self._sawRunning = true;

                var pct;
                if (data.percent != null) pct = data.percent;
                else if (data.hosts_total > 0) pct = Math.round(data.hosts_done / data.hosts_total * 100);
                else pct = 0;

                var bar = document.getElementById('syncProgressBar');
                var textEl = document.getElementById('syncProgressText');
                if (bar) { bar.style.width = pct + '%'; bar.textContent = pct + '%'; }
                if (textEl) textEl.textContent = self._describe(data, pct);

                if (data.warnings && data.warnings.length > 0) {
                    var warnList = document.getElementById('syncWarnList');
                    if (warnList) {
                        warnList.innerHTML = data.warnings.slice(-3).map(function(w) {
                            return '<div>' + w + '</div>';
                        }).join('');
                    }
                }
                if (data.errors && data.errors.length > 0) {
                    var errList = document.getElementById('syncErrorList');
                    if (errList) {
                        errList.innerHTML = data.errors.slice(-3).map(function(e) {
                            return '<div>' + e + '</div>';
                        }).join('');
                    }
                }

                if (!data.running && self._readyToSettle()) self._settle(data);
            })
            .catch(function(e) {
                if (self._timer) { clearInterval(self._timer); self._timer = null; }
                showToast('进度查询失败: ' + e.message, 'danger');
            });
    },

    // 行级任务（后台初始化）显示 "阶段... 1,200 / 5,000 (24%)"；
    // 主机级任务（/review/sync-all）沿用 "3/10 消息" 文案，逐字不变。
    _describe: function(data, pct) {
        if (data.unit && data.rows_total > 0) {
            var label = SYNC_PHASE_LABELS[data.phase] || '正在处理';
            return label + '... ' + this._fmt(data.rows_done) + ' / ' +
                   this._fmt(data.rows_total) + ' (' + pct + '%)';
        }
        if (data.unit) {
            return data.message || (SYNC_PHASE_LABELS[data.phase] || '正在处理') + '...';
        }
        return data.hosts_done + '/' + data.hosts_total + ' ' + data.message;
    },

    // 何时可以判定任务已结束。
    // 尚未看到 running=true、且发起请求也还没返回时，不能结算 —— 否则首个
    // 500ms 轮询就会撞上"任务还没开始写进度"，把页面提前刷新掉。
    _readyToSettle: function() {
        if (this._settled) return false;
        if (this._sawRunning || this._requestDone) return true;
        return false;
    },

    _settle: function(data) {
        var self = this;
        self._settled = true;
        if (self._timer) { clearInterval(self._timer); self._timer = null; }

        var hide = function() { if (self._modal) self._modal.hide(); };
        // 调用方的收尾（如恢复初始化按钮）—— 无论走哪条分支都要执行，
        // 否则一次 409 会让按钮永久卡在"初始化中"。
        var rewrite = function() {
            if (self._opts && typeof self._opts.onSettle === 'function') {
                try { self._opts.onSettle(); } catch (e) { /* 收尾失败不影响主流程 */ }
            }
        };
        rewrite();

        if (self._conflict) {
            hide();
            showToast(self._conflict, 'warning');
            return;   // 任务根本没跑起来，不刷新
        }
        if (self._requestFailed) {
            hide();
            showToast('请求失败: ' + self._requestFailed, 'danger');
            return;
        }
        // 中止必须先于 success === false 判定：runner 用 success=False 记录中止，
        // 顺序反了会把"用户主动中止"报成"任务失败"。
        // 中止路径不刷新、也不释放勾选 —— 数据零变更，用户可直接重试。
        if (data.aborted) {
            hide();
            showToast(data.message || '任务已中止，数据未变更', 'warning');
            return;
        }
        // 严格比较 false：/review/sync-all 不写 success 字段（保持 undefined），
        // 仍应走 reload 分支 —— 用 if (!data.success) 会把它误判成失败。
        if (data.success === false) {
            hide();
            showToast(data.message || '任务失败', 'danger');
            return;
        }

        // 任务成功：释放已勾选项，避免 reload 后勾选被 sessionStorage 恢复
        if (window.BatchSync) { BatchSync.clearSelection(); }

        // 后台任务期的非致命提示（如"未绑定模板已用默认模板兜底"）逐条补弹 ——
        // 这些以前挂在响应体 data.skipped_hosts 上，异步化后改走 warnings 通道。
        if (data.warnings && data.warnings.length) {
            data.warnings.forEach(function(w, i) {
                setTimeout(function() { showToast(w, 'warning'); }, 300 * (i + 1));
            });
        }
        setTimeout(function() { location.reload(); }, 1500);
    },

    stop: function() {
        // 保持轮询：中止信号只让后台任务在下一个检查点退出，终态仍要靠轮询
        // 读回来才能关窗/恢复按钮。在这里 clearInterval 会把弹窗永久留在屏幕上。
        fetch('/review/sync-abort', { method: 'POST' })
            .then(function() {
                showToast('已发送停止信号，等待任务中止...', 'warning');
                var btn = document.getElementById('stopSyncBtn');
                if (btn) btn.disabled = true;
            })
            .catch(function(e) { showToast('发送停止信号失败: ' + e.message, 'danger'); });
    }
};

// ========================================================
// SeverityBadge — utility: returns HTML for priority badge
// ========================================================
window.RenderHelpers = {
    severityBadge: function(priority) {
        var p = String(priority);
        var label = ReviewDashboard.PRIORITY_LABELS[p] || '未知(' + p + ')';
        var bs = ReviewDashboard.PRIORITY_BS[p] || 'secondary';
        return '<span class="badge bg-' + bs + '" style="font-size:11px;">' + label + '</span>';
    },

    syncBadge: function(syncStatus) {
        if (syncStatus === 'synced') {
            return '<span class="status-badge synced" style="font-size:10px;display:inline-block;">已同步</span>';
        } else if (syncStatus === 'pending_delete') {
            return '<span class="status-badge pending-delete" style="font-size:10px;display:inline-block;">待清理</span>';
        } else {
            return '<span class="status-badge pending-sync" style="font-size:10px;display:inline-block;">待同步</span>';
        }
    },

    confirmBadge: function(confirmed) {
        return confirmed
            ? '<span class="badge bg-success" style="font-size:10px;">已确认</span>'
            : '<span class="badge bg-secondary" style="font-size:10px;">未确认</span>';
    }
};

// ========================================================
// TriggerDrillDown — Item-to-Trigger expandable child rows
// ========================================================
window.TriggerDrillDown = (function() {
    var _cache = {};

    function _renderChildRow(parentRow, triggers, matchKey, icon) {
        var filtered = triggers.filter(function(t) {
            return t.expression && t.expression.indexOf(matchKey) !== -1;
        });
        var childRow = document.createElement('tr');
        childRow.className = 'trigger-child-row';
        var td = document.createElement('td');
        td.colSpan = 100;
        td.style.padding = '8px 16px';
        td.style.background = '#f8f9fc';
        if (filtered.length === 0) {
            td.innerHTML = '<div class="text-muted small p-2"><i class="bi bi-info-circle"></i> 没有找到关联该监控项键值的触发器</div>';
        } else {
            var cardsHtml = '<div class="trigger-cards-container">';
            filtered.forEach(function(t) {
                cardsHtml += '<div class="trigger-card-item">' +
                    '<div class="d-flex justify-content-between align-items-start">' +
                    '<div><strong>' + (t.name || '') + '</strong> ' +
                    window.RenderHelpers.severityBadge(t.priority) + '</div>' +
                    '<div class="text-end" style="white-space:nowrap;">' +
                    window.RenderHelpers.syncBadge(t.sync_status) + ' ' +
                    window.RenderHelpers.confirmBadge(t.confirmed) + '</div>' +
                    '</div>' +
                    '<code class="text-muted" style="font-size:11px;">' + (t.expression || '') + '</code>' +
                    '</div>';
            });
            cardsHtml += '</div>';
            td.innerHTML = cardsHtml;
        }
        childRow.appendChild(td);
        parentRow.parentNode.insertBefore(childRow, parentRow.nextSibling);
        icon.classList.remove('bi-hourglass-split');
        icon.classList.add('bi-dash-square');
    }

    return {
        toggle: function(tdElement, hostIp, templateName, matchKey) {
            var row = tdElement.closest('tr');
            var icon = tdElement.querySelector('.expand-toggle-icon');
            if (!icon) return;
            var cacheKey = hostIp + '|' + templateName;
            var existingChild = row.nextElementSibling;
            if (existingChild && existingChild.classList.contains('trigger-child-row')) {
                existingChild.remove();
                icon.classList.remove('bi-dash-square');
                icon.classList.add('bi-plus-square');
                return;
            }
            icon.classList.remove('bi-plus-square');
            icon.classList.add('bi-hourglass-split');
            if (_cache[cacheKey]) {
                _renderChildRow(row, _cache[cacheKey], matchKey, icon);
            } else {
                fetch('/api/review/item-triggers?host_ip=' + encodeURIComponent(hostIp) + '&template_name=' + encodeURIComponent(templateName))
                    .then(function(r) { return r.json(); })
                    .then(function(data) {
                        if (!data.success) {
                            showToast('加载触发器失败: ' + (data.message || ''), 'warning');
                            icon.classList.remove('bi-hourglass-split');
                            icon.classList.add('bi-plus-square');
                            return;
                        }
                        _cache[cacheKey] = data.triggers || [];
                        _renderChildRow(row, _cache[cacheKey], matchKey, icon);
                    })
                    .catch(function(e) {
                        showToast('加载触发器失败: ' + e.message, 'danger');
                        icon.classList.remove('bi-hourglass-split');
                        icon.classList.add('bi-plus-square');
                    });
            }
        }
    };
})();

// ========================================================
// ReviewActions — shared init/import/sync actions for all review pages
// ========================================================
window.ReviewActions = {
    // 初始化：请求立即返回 202，实际工作跑在后台线程里，进度与终态由
    // ReviewSyncPoller 轮询 /review/sync-progress 得到。
    // 按钮在整个任务期间保持禁用 —— 提前恢复会在任务未结束时诱发重复点击（409）。
    initReview: function(btnId, url, includeFilters) {
        var btn = document.getElementById(btnId);
        if (!btn) return;
        var orig = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 初始化中...';
        var body = {};
        if (includeFilters) {
            var systemEl = document.querySelector('input[name="system"]');
            var subsystemEl = document.querySelector('input[name="subsystem"]');
            if (systemEl) body.system = systemEl.value || '';
            if (subsystemEl) body.subsystem = subsystemEl.value || '';
        }
        ReviewSyncPoller.start(function() {
            return fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });
        }, {
            title: '初始化进度',
            startText: '正在启动初始化任务...',
            onSettle: function() {
                btn.disabled = false;
                btn.innerHTML = orig;
            }
        });
    },

    importReview: function(input, url, tableLabel) {
        if (!input.files.length) return;
        if (!confirm('将清空 ' + tableLabel + ' 表现有数据并从 Excel 导入，确认继续？')) {
            input.value = '';
            return;
        }
        var formData = new FormData();
        formData.append('file', input.files[0]);
        fetch(url, { method: 'POST', body: formData })
            .then(function(r) { return r.json(); })
            .then(function(data) {
                showToast(data.message, data.success ? 'success' : 'danger');
                if (data.success) setTimeout(function() { location.reload(); }, 1500);
            })
            .catch(function(e) {
                showToast('导入失败: ' + e.message, 'danger');
            })
            .then(function() {
                input.value = '';
            });
    },

    syncAll: function() {
        var envSelect = document.querySelector('#syncEnvSelect');
        if (!envSelect) { showToast('环境选择器未找到', 'danger'); return; }
        var env = envSelect.value;
        if (!env) { showToast('请先选择目标环境机房', 'warning'); return; }
        var system = document.querySelector('input[name="system"]') ? document.querySelector('input[name="system"]').value : '';
        var subsystem = document.querySelector('input[name="subsystem"]') ? document.querySelector('input[name="subsystem"]').value : '';
        ReviewSyncPoller.start(function() {
            return fetch('/review/sync-all', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ environment: env, system: system, subsystem: subsystem })
            });
        });
    }
};
