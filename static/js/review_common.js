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
window.ReviewSyncPoller = {
    _timer: null,

    start: function(syncFn) {
        var modalEl = document.getElementById('syncProgressModal');
        if (!modalEl) { showToast('同步进度弹窗未找到', 'danger'); return; }
        var modal = new bootstrap.Modal(modalEl, {backdrop: 'static', keyboard: false});
        modal.show();

        var bar = document.getElementById('syncProgressBar');
        var text = document.getElementById('syncProgressText');
        if (bar) { bar.style.width = '0%'; bar.textContent = '0%'; }
        if (text) text.textContent = '发起同步请求...';

        syncFn().catch(function(e) { showToast('同步请求失败: ' + e.message, 'danger'); });

        var self = this;
        if (self._timer) clearInterval(self._timer);
        self._timer = setInterval(function() { self.poll(); }, 500);
    },

    poll: function() {
        fetch('/review/sync-progress')
            .then(function(r) { return r.json(); })
            .then(function(data) {
                var pct = data.hosts_total > 0 ? Math.round(data.hosts_done / data.hosts_total * 100) : 0;
                var bar = document.getElementById('syncProgressBar');
                var textEl = document.getElementById('syncProgressText');
                if (bar) { bar.style.width = pct + '%'; bar.textContent = pct + '%'; }
                if (textEl) textEl.textContent = data.hosts_done + '/' + data.hosts_total + ' ' + data.message;
                if (data.errors && data.errors.length > 0) {
                    var errList = document.getElementById('syncErrorList');
                    if (errList) {
                        errList.innerHTML = data.errors.slice(-3).map(function(e) {
                            return '<div>' + e + '</div>';
                        }).join('');
                    }
                }
                if (!data.running) {
                    if (window.ReviewSyncPoller._timer) {
                        clearInterval(window.ReviewSyncPoller._timer);
                        window.ReviewSyncPoller._timer = null;
                    }
                    // 同步结束：释放已勾选项，避免 reload 后勾选被 sessionStorage 恢复
                    if (window.BatchSync) { BatchSync.clearSelection(); }
                    setTimeout(function() { location.reload(); }, 1500);
                }
            })
            .catch(function(e) {
                if (window.ReviewSyncPoller._timer) {
                    clearInterval(window.ReviewSyncPoller._timer);
                    window.ReviewSyncPoller._timer = null;
                }
                showToast('进度查询失败: ' + e.message, 'danger');
            });
    },

    stop: function() {
        if (this._timer) {
            clearInterval(this._timer);
            this._timer = null;
        }
        fetch('/review/sync-abort', { method: 'POST' })
            .then(function() {
                showToast('已发送停止信号', 'warning');
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
        fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            showToast(data.message, data.success ? 'success' : 'danger');
            // Show warning if hosts were skipped (no template)
            if (data.success && data.data && data.data.skipped_hosts > 0) {
                setTimeout(function() {
                    showToast(data.data.skipped_hosts + ' 台主机未绑定模板，已用默认模板兜底初始化', 'warning');
                }, 500);
            }
            if (data.success) setTimeout(function() { location.reload(); }, 2000);
        })
        .catch(function(e) {
            showToast('初始化请求失败: ' + e.message, 'danger');
        })
        .then(function() {
            btn.disabled = false;
            btn.innerHTML = orig;
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
