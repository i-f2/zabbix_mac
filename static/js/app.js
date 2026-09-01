/* ============================================================
   Zabbix MaC 管理界面 - 自定义脚本
   ============================================================ */

document.addEventListener('DOMContentLoaded', function () {
    'use strict';

    // ========================================================
    // Sidebar Toggle
    // ========================================================
    const sidebar = document.querySelector('.app-sidebar');
    const toggleBtn = document.getElementById('sidebarToggle');
    const overlay = document.getElementById('sidebarOverlay');
    const body = document.body;

    function isMobile() {
        return window.innerWidth <= 768;
    }

    function collapseSidebar() {
        body.classList.add('sidebar-collapsed');
        if (overlay) overlay.style.display = 'none';
    }

    function expandSidebar() {
        body.classList.remove('sidebar-collapsed');
        if (isMobile() && overlay) overlay.style.display = 'block';
    }

    function toggleSidebar() {
        if (body.classList.contains('sidebar-collapsed')) {
            expandSidebar();
            localStorage.setItem('sidebarCollapsed', 'false');
        } else {
            collapseSidebar();
            localStorage.setItem('sidebarCollapsed', 'true');
        }
    }

    // Restore sidebar state from localStorage
    const savedState = localStorage.getItem('sidebarCollapsed');
    if (savedState === 'true') {
        collapseSidebar();
    }

    // Auto-collapse on mobile
    if (isMobile() && savedState !== 'false') {
        collapseSidebar();
    }

    // Toggle button click
    if (toggleBtn) {
        toggleBtn.addEventListener('click', toggleSidebar);
    }

    // Overlay click (mobile) to close sidebar
    if (overlay) {
        overlay.addEventListener('click', collapseSidebar);
    }

    // Handle window resize
    let lastWidth = window.innerWidth;
    window.addEventListener('resize', function () {
        const currentWidth = window.innerWidth;
        // Only react when crossing the 768px breakpoint
        if ((lastWidth <= 768 && currentWidth > 768) || (lastWidth > 768 && currentWidth <= 768)) {
            if (currentWidth <= 768) {
                // Switched to mobile: collapse sidebar
                collapseSidebar();
            } else {
                // Switched to desktop: restore if user preference was expanded
                if (localStorage.getItem('sidebarCollapsed') !== 'true') {
                    expandSidebar();
                }
            }
        }
        lastWidth = currentWidth;
    });

    // ========================================================
    // Sidebar Transition → Table Repaint
    // When sidebar collapses/expands, available width changes.
    // Sticky columns need a forced repaint to recalculate positions.
    // ========================================================
    function recalcTableLayouts() {
        var tables = document.querySelectorAll('.data-card .table');
        if (tables.length === 0) return;
        // Force browser style recalc on parent to trigger sticky repaint
        var wrapper = document.querySelector('.app-main');
        if (wrapper) {
            wrapper.style.transform = 'translateZ(0)';
            requestAnimationFrame(function() {
                wrapper.style.transform = '';
            });
        }
    }

    // Debounced wrapper: coalesces rapid successive calls within 200ms
    // Exposed as window.recalcTableLayouts for use by TechViewToggle etc.
    var _recalcDebounceTimer = null;
    window.recalcTableLayouts = function() {
        if (_recalcDebounceTimer !== null) {
            clearTimeout(_recalcDebounceTimer);
        }
        _recalcDebounceTimer = setTimeout(function() {
            _recalcDebounceTimer = null;
            recalcTableLayouts();
        }, 200);
    };

    // Listen for sidebar margin-left animation completion
    var mainEl = document.querySelector('.app-main');
    if (mainEl) {
        mainEl.addEventListener('transitionend', function(e) {
            if (e.propertyName === 'margin-left') {
                window.recalcTableLayouts();
            }
        });
    }

    // Override toggleSidebar to add repaint after animation
    var _origToggleSidebar = toggleSidebar;
    window.toggleSidebar = function() {
        _origToggleSidebar();
        setTimeout(window.recalcTableLayouts, 350);  // 300ms CSS transition + 50ms buffer
    };
    if (toggleBtn) {
        toggleBtn.removeEventListener('click', toggleSidebar);
        toggleBtn.addEventListener('click', window.toggleSidebar);
    }

    // ========================================================
    // Active Menu Highlighting
    // ========================================================
    const currentPath = window.location.pathname;
    const menuItems = document.querySelectorAll('.sidebar-menu-item[data-route]');

    menuItems.forEach(function (item) {
        const routes = item.getAttribute('data-route').split('|');
        let matched = false;

        for (let i = 0; i < routes.length; i++) {
            const route = routes[i].trim();
            // Match: route name as a complete path segment (word-boundary aware)
            if (route) {
                const pattern = '/' + route;
                const idx = currentPath.indexOf(pattern);
                if (idx !== -1) {
                    const nextChar = currentPath[idx + pattern.length];
                    if (nextChar === undefined || nextChar === '/' || nextChar === '?') {
                        matched = true;
                        break;
                    }
                }
            }
            // Special case: index page
            if (route === 'index' && (currentPath === '/' || currentPath === '')) {
                matched = true;
                break;
            }
            // Special case: system-info also matched by system_info
            if (route === 'system_info' && currentPath.indexOf('/system-info') !== -1) {
                matched = true;
                break;
            }
        }

        if (matched) {
            item.classList.add('active');
        }
    });

    // ========================================================
    // Sidebar Group Collapse Persistence — 分组展开状态跨页面持久化
    // 分组一旦开启即保持展开，只有再次点击分组标题（关闭按钮）才折叠；
    // 当前路由命中的子菜单所在分组强制展开，保证直达子页面时菜单可见。
    // ========================================================
    (function () {
        var GROUP_IDS = ['sidebarCollapseReview', 'sidebarCollapseTemplate'];
        function groupKey(id) { return 'sidebarGroupOpen_' + id; }

        GROUP_IDS.forEach(function (id) {
            var groupEl = document.getElementById(id);
            if (!groupEl) return;

            // 切换开始时即持久化最终意图，避免动画未结束就跳转导致状态丢失
            groupEl.addEventListener('show.bs.collapse', function () {
                localStorage.setItem(groupKey(id), '1');
            });
            groupEl.addEventListener('hide.bs.collapse', function () {
                localStorage.setItem(groupKey(id), '0');
            });

            // 目标显隐：显式开/关优先（开启后保持展开、点关闭后保持折叠）；
            // 无显式偏好且当前页命中该分组子菜单时自动展开（直达子页面菜单可见）；
            // 无显式偏好且不在该分组 → 保持服务端渲染默认，不干预。
            var hasActive = groupEl.querySelector('.sidebar-menu-item.active') !== null;
            var saved = localStorage.getItem(groupKey(id));
            var isShown = groupEl.classList.contains('show');

            var wantShow;
            if (saved === '1') {
                wantShow = true;
            } else if (saved === '0') {
                wantShow = false;
            } else if (hasActive) {
                wantShow = true;
            } else {
                return;
            }

            // 目标状态与服务端渲染一致 → 直接跳过。
            // 注意：此处不能调用 bootstrap.Collapse.getOrCreateInstance(groupEl) 来建实例，
            // Bootstrap 5.3 的 Collapse 构造器会自动执行一次 toggle()，会把折叠组强制展开/展开组强制折叠。
            if (wantShow === isShown) return;

            // 状态不一致：直接修正 DOM（不创建 Collapse 实例），并同步 toggle 的 aria-expanded（驱动箭头旋转）。
            groupEl.classList.toggle('show', wantShow);
            document.querySelectorAll('[data-bs-toggle="collapse"][href="#' + id + '"], [data-bs-toggle="collapse"][data-bs-target="#' + id + '"]')
                .forEach(function (toggleEl) {
                    toggleEl.setAttribute('aria-expanded', wantShow ? 'true' : 'false');
                });
        });
    })();

    // ========================================================
    // Sidebar Pending Badges — 异步获取未确认复核数量
    // ========================================================
    fetch('/api/review/pending-counts')
        .then(function(r) { return r.json(); })
        .then(function(response) {
            if (!response.success) return;
            var data = response.data;
            var badgeMap = {
                items: 'badge-items-count',
                triggers: 'badge-triggers-count',
                web: 'badge-web-count'
            };
            Object.keys(badgeMap).forEach(function(k) {
                var el = document.getElementById(badgeMap[k]);
                if (!el) return;
                var count = data[k] || 0;
                el.textContent = count;
                if (count > 0) {
                    el.classList.remove('d-none');
                } else {
                    el.classList.add('d-none');
                }
            });
        })
        .catch(function() { /* 优雅降级：保持 Badge 隐藏 */ });

    // ========================================================
    // Global Search
    // ========================================================
    const searchInput = document.getElementById('globalSearch');
    if (searchInput) {
        searchInput.addEventListener('keydown', function (e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                const query = this.value.trim();
                if (query) {
                    window.location.href = '/search?q=' + encodeURIComponent(query);
                }
            }
        });
    }

    // ========================================================
    // Flash Message Auto-Dismiss
    // ========================================================
    const flashAlerts = document.querySelectorAll('.alert-dismissible');
    flashAlerts.forEach(function (alert) {
        setTimeout(function () {
            const closeBtn = alert.querySelector('.btn-close');
            if (closeBtn) {
                closeBtn.click();
            }
        }, 5000);
    });

    // ========================================================
    // Centralized confirm toggle — AJAX call, then remove button
    // Templates call: toggleConfirmRow(id, btn, confirmUrl)
    // ========================================================
    window.toggleConfirmRow = function (id, btn, confirmUrl) {
        _executeToggle(id, btn, confirmUrl);
    };

    function _executeToggle(id, btn, confirmUrl) {
        var origHTML = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm" style="width:14px;height:14px;"></span>';

        var url = confirmUrl.replace('__ID__', id);
        fetch(url, { method: 'POST' })
            .then(function (res) { return res.json(); })
            .then(function (data) {
                if (!data.success) {
                    showToast(data.message || '操作失败', 'danger');
                    btn.disabled = false;
                    btn.innerHTML = origHTML;
                    return;
                }
                showToast('已确认', 'success');

                // Update confirm status cell and remove confirm button
                var row = btn.closest('tr');
                if (row) {
                    var statusCell = row.querySelector('.col-fw-status.col-sticky-r3, td.col-sticky-r3');
                    if (statusCell) {
                        statusCell.textContent = '已确认';
                    }
                    // Remove the confirm button — now confirmed, no cancel needed
                    btn.remove();
                }
            })
            .catch(function (e) {
                showToast('请求失败: ' + e.message, 'danger');
                btn.disabled = false;
                btn.innerHTML = origHTML;
            });
    }

    // ========================================================
    // Table Row Click (for clickable rows)
    // ========================================================
    document.querySelectorAll('tr[data-href]').forEach(function (row) {
        row.addEventListener('click', function () {
            window.location.href = this.getAttribute('data-href');
        });
        row.style.cursor = 'pointer';
    });

    // ========================================================
    // Bootstrap Tooltip Initialization
    // ========================================================
    document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(function (el) {
        new bootstrap.Tooltip(el);
    });

    // ========================================================
    // Cross-page checkbox selection restoration
    // ========================================================
    if (window.BATCH_SYNC_CONFIG && window.BATCH_SYNC_CONFIG.table) {
        BatchSync._restoreCheckboxes();
    }
});

// ========================================================
// 主机资产同步
// ========================================================
async function syncHosts() {
    const btn = document.getElementById('syncHostsBtn');
    if (!btn) return;
    const originalHTML = btn.innerHTML;

    // Loading 状态
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 同步中...';

    try {
        const response = await fetch('/host/sync', { method: 'POST' });
        const data = await response.json();

        showToast(data.message, data.success ? 'success' : 'danger');

        if (data.success) {
            // 延迟刷新，让用户看到 toast
            setTimeout(function () { location.reload(); }, 1500);
        }
    } catch (error) {
        showToast('同步请求失败: ' + error.message, 'danger');
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalHTML;
    }
}

// 通用 toast 通知函数
function showToast(message, type) {
    var toastEl = document.createElement('div');
    toastEl.className = 'toast align-items-center text-white bg-' + type + ' border-0 position-fixed bottom-0 end-0 m-3';
    toastEl.setAttribute('role', 'alert');

    var flexDiv = document.createElement('div');
    flexDiv.className = 'd-flex';

    var bodyDiv = document.createElement('div');
    bodyDiv.className = 'toast-body';
    bodyDiv.textContent = message;

    var closeBtn = document.createElement('button');
    closeBtn.type = 'button';
    closeBtn.className = 'btn-close btn-close-white me-2 m-auto';
    closeBtn.setAttribute('data-bs-dismiss', 'toast');

    flexDiv.appendChild(bodyDiv);
    flexDiv.appendChild(closeBtn);
    toastEl.appendChild(flexDiv);

    document.body.appendChild(toastEl);
    var toast = new bootstrap.Toast(toastEl, { delay: 3000 });
    toast.show();
    toastEl.addEventListener('hidden.bs.toast', function () { toastEl.remove(); });
}

// ============================================================
// BatchSync: shared checkbox + diff-preview logic for all review tables
// ============================================================
// Cross-page selection persistence via sessionStorage.
// Pagination does full page reload, so DOM-only checkbox state is lost.
// sessionStorage survives navigations within the same tab.
window.BatchSync = {
    _getStorageKey: function() {
        var table = (window.BATCH_SYNC_CONFIG && window.BATCH_SYNC_CONFIG.table) || 'unknown';
        return 'selectedIds_' + table;
    },

    _getSelectedSet: function() {
        var raw = sessionStorage.getItem(BatchSync._getStorageKey());
        if (!raw) return new Set();
        try { return new Set(JSON.parse(raw)); } catch(e) { return new Set(); }
    },

    _saveSelectedSet: function(s) {
        sessionStorage.setItem(BatchSync._getStorageKey(), JSON.stringify(Array.from(s)));
    },

    _restoreCheckboxes: function() {
        var selected = BatchSync._getSelectedSet();
        var anyChecked = false;
        document.querySelectorAll('.row-checkbox').forEach(function(cb) {
            if (selected.has(cb.value)) {
                cb.checked = true;
                anyChecked = true;
            }
        });
        BatchSync._updateUI(selected.size);
    },

    onCheckboxChange: function() {
        var selected = BatchSync._getSelectedSet();
        document.querySelectorAll('.row-checkbox').forEach(function(cb) {
            if (cb.checked) { selected.add(cb.value); }
            else { selected.delete(cb.value); }
        });
        BatchSync._saveSelectedSet(selected);
        BatchSync._updateUI(selected.size);
    },

    toggleAll: function(el) {
        var selected = BatchSync._getSelectedSet();
        document.querySelectorAll('.row-checkbox').forEach(function(cb) {
            cb.checked = el.checked;
            if (el.checked) { selected.add(cb.value); }
            else { selected.delete(cb.value); }
        });
        BatchSync._saveSelectedSet(selected);
        BatchSync._updateUI(selected.size);
    },

    // 清空全部已勾选项：取消页面勾选 + 覆写 sessionStorage 选择集 + 复位按钮/全选框。
    // 同步结束后由 ReviewSyncPoller 调用，避免 reload 后 _restoreCheckboxes 恢复勾选。
    clearSelection: function() {
        document.querySelectorAll('.row-checkbox:checked').forEach(function(cb) {
            cb.checked = false;
        });
        BatchSync._saveSelectedSet(new Set());
        BatchSync._updateUI(0);
    },

    getSelectedIds: function() {
        return Array.from(BatchSync._getSelectedSet()).map(function(id) { return parseInt(id); });
    },

    verifySelected: async function() {
        var ids = BatchSync.getSelectedIds();
        if (ids.length === 0) {
            showToast('请先勾选需要核验的行', 'warning');
            return;
        }
        var env = (document.getElementById('syncEnvSelect') || document.getElementById('syncEnvSelectScenarios'))?.value;
        if (!env) { showToast('请先选择目标环境机房', 'warning'); return; }
        var actionType = (window.BATCH_SYNC_CONFIG && window.BATCH_SYNC_CONFIG.action_type) || 'item';

        var btn = document.getElementById('verifyBtn');
        if (!btn) { showToast('核验按钮未找到，请刷新页面', 'danger'); return; }
        var orig = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 核验中...';

        try {
            var res = await fetch('/api/review/verify', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action_type: actionType, environment: env, ids: ids })
            });
            var data = await res.json();
            if (data.status === 'warning') {
                // Show failed IDs alert for user to re-sync
                var failList = (data.failed_ids || []).join(', ');
                showToast(data.message + (failList ? ' 未找到的ID: ' + failList : ''), 'warning');
            } else {
                showToast(data.message, data.success ? 'success' : 'danger');
            }
            if (data.success) setTimeout(function () { location.reload(); }, 2000);
        } catch (e) {
            showToast('核验请求失败: ' + e.message, 'danger');
        } finally {
            btn.disabled = false;
            btn.innerHTML = orig;
        }
    },

    _updateUI: function(count) {
        var syncBtn = document.getElementById('syncBtn');
        var verifyBtn = document.getElementById('verifyBtn');
        var selectAll = document.getElementById('selectAllCheckbox');

        if (count > 0) {
            if (syncBtn) {
                syncBtn.disabled = false;
                syncBtn.innerHTML = '<i class="bi bi-cloud-upload"></i> 监控同步 (已选 ' + count + ' 条)';
            }
            if (verifyBtn) {
                verifyBtn.disabled = false;
                verifyBtn.innerHTML = '<i class="bi bi-check-circle"></i> 核验 (已选 ' + count + ' 条)';
            }
        } else {
            if (syncBtn) {
                syncBtn.disabled = true;
                syncBtn.innerHTML = '<i class="bi bi-cloud-upload"></i> 监控同步';
            }
            if (verifyBtn) {
                verifyBtn.disabled = true;
                verifyBtn.innerHTML = '<i class="bi bi-check-circle"></i> 核验';
            }
        }

        if (selectAll) {
            var pageTotal = document.querySelectorAll('.row-checkbox').length;
            var pageChecked = document.querySelectorAll('.row-checkbox:checked').length;
            selectAll.checked = (pageChecked === pageTotal && pageTotal > 0);
            selectAll.indeterminate = (pageChecked > 0 && pageChecked < pageTotal);
        }
    },

    previewSync: async function() {
        var ids = BatchSync.getSelectedIds();
        if (ids.length === 0) {
            showToast('请先勾选需要操作的行', 'warning');
            return;
        }
        var env = (document.getElementById('syncEnvSelect') || document.getElementById('syncEnvSelectScenarios'))?.value;
        if (!env) { showToast('请先选择目标环境机房', 'warning'); return; }

        var previewModalEl = document.getElementById('diffPreviewModal');
        if (!previewModalEl) { showToast('模态框未加载，请刷新页面', 'danger'); return; }

        var modal = new bootstrap.Modal(previewModalEl);
        var body = previewModalEl.querySelector('.modal-body');
        var summary = previewModalEl.querySelector('.diff-summary');
        var confirmBtn = previewModalEl.querySelector('#confirmSyncBtn');

        summary.innerHTML = '';
        body.innerHTML = '<div class="diff-summary mb-3"></div><div class="text-center py-5"><div class="spinner-border text-primary" role="status"></div><p class="mt-3 text-muted">正在获取差异对比...</p></div>';
        confirmBtn.disabled = true;
        modal.show();

        try {
            var res = await fetch('/api/sync/preview', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    ids: ids,
                    table: window.BATCH_SYNC_CONFIG.table,
                    action_type: window.BATCH_SYNC_CONFIG.action_type || window.BATCH_SYNC_CONFIG.table,
                    environment: env
                })
            });
            var data = await res.json();
            if (!data.success) {
                body.innerHTML = '<div class="diff-summary mb-3"></div><div class="alert alert-danger m-3">' + BatchSync._escapeHtml(data.message) + '</div>';
                return;
            }
            BatchSync.renderDiff(data);
            confirmBtn.disabled = false;
            previewModalEl._syncPayload = { ids: ids, table: window.BATCH_SYNC_CONFIG.table, action_type: window.BATCH_SYNC_CONFIG.action_type || window.BATCH_SYNC_CONFIG.table, environment: env };
        } catch (e) {
            body.innerHTML = '<div class="diff-summary mb-3"></div><div class="alert alert-danger m-3">请求失败: ' + BatchSync._escapeHtml(e.message) + '</div>';
        }
    },

    renderDiff: function(data) {
        var modalEl = document.getElementById('diffPreviewModal');
        var body = modalEl.querySelector('.modal-body');
        var summary = modalEl.querySelector('.diff-summary');
        // Defensive: recreate .diff-summary if destroyed by body.innerHTML overwrite
        if (!summary && body) {
            summary = document.createElement('div');
            summary.className = 'diff-summary mb-3';
            body.insertBefore(summary, body.firstChild);
        }
        if (!summary) return;  // fail gracefully if modal isn't in DOM
        var s = data.summary;

        summary.innerHTML =
            '<div class="d-flex gap-3 flex-wrap">' +
            '<span class="badge bg-success fs-6">新增 ' + (s.create_count || 0) + ' 个</span>' +
            '<span class="badge bg-warning text-dark fs-6">更新 ' + (s.update_count || 0) + ' 个</span>' +
            '<span class="badge bg-danger fs-6">删除 ' + (s.delete_count || 0) + ' 个</span>' +
            '<span class="badge bg-secondary fs-6">不变 ' + (s.unchanged_count || 0) + ' 个</span>' +
            '</div>';

        if (!data.changes || data.changes.length === 0) {
            body.innerHTML = '<div class="alert alert-info m-3">所有选中项已与 Zabbix 一致，无需同步。</div>';
            return;
        }

        var badgeClass = { CREATE: 'bg-success', UPDATE: 'bg-warning text-dark', DELETE: 'bg-danger' };
        var rows = data.changes.map(function(c) {
            return '<tr>' +
                '<td>' + BatchSync._escapeHtml(c.host || '') + '</td>' +
                '<td>' + BatchSync._escapeHtml(c.type || '') + '</td>' +
                '<td><code>' + BatchSync._escapeHtml(c.key || c.name || '') + '</code></td>' +
                '<td><span class="badge ' + (badgeClass[c.action] || 'bg-secondary') + '">' + BatchSync._escapeHtml(c.action || '') + '</span></td>' +
                '<td class="text-muted small">' + BatchSync._escapeHtml(c.details || '') + '</td>' +
                '</tr>';
        }).join('');

        body.innerHTML =
            '<div class="table-responsive" style="max-height: 400px; overflow-y: auto;">' +
            '<table class="table table-sm table-hover mb-0">' +
            '<thead><tr>' +
            '<th>主机</th><th>类型</th><th>键值/名称</th><th>动作</th><th>详情</th>' +
            '</tr></thead>' +
            '<tbody>' + rows + '</tbody>' +
            '</table></div>';
    },

    applySync: async function() {
        var modalEl = document.getElementById('diffPreviewModal');
        var payload = modalEl._syncPayload;
        var confirmBtn = document.getElementById('confirmSyncBtn');
        if (!payload) { showToast('同步数据丢失，请重新预览', 'danger'); return; }

        confirmBtn.disabled = true;
        confirmBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 同步中...';

        try {
            var res = await fetch('/api/sync/execute', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    ids: payload.ids,
                    action_type: payload.action_type,
                    environment: payload.environment
                })
            });
            var data = await res.json();

            // Differentiated error handling: status==='error' means dependency validation failure
            if (!data.success) {
                var modal = bootstrap.Modal.getInstance(modalEl);
                if (data.status === 'error') {
                    // Dependency validation error — show in modal, don't close it
                    BatchSync._showErrorModal(data.message);
                } else {
                    modal.hide();
                    showToast(data.message, 'danger');
                }
                confirmBtn.disabled = false;
                confirmBtn.innerHTML = '<i class="bi bi-cloud-upload"></i> 确认同步下发';
                return;
            }

            var modal = bootstrap.Modal.getInstance(modalEl);
            modal.hide();
            showToast(data.message, 'success');
            // 同步下发成功：释放已勾选项，避免 reload 后勾选被 sessionStorage 恢复
            BatchSync.clearSelection();
            setTimeout(function() { location.reload(); }, 1500);
        } catch (e) {
            showToast('同步请求失败: ' + e.message, 'danger');
            confirmBtn.disabled = false;
            confirmBtn.innerHTML = '<i class="bi bi-cloud-upload"></i> 确认同步下发';
        }
    },

    _showErrorModal: function(message) {
        // Show error in the already-open diffPreviewModal
        var modalEl = document.getElementById('diffPreviewModal');
        if (modalEl) {
            var body = modalEl.querySelector('.modal-body');
            var summary = modalEl.querySelector('.diff-summary');
            if (body) {
                body.innerHTML = '<div class="diff-summary mb-3"></div><div class="alert alert-danger m-3" style="white-space: pre-wrap; word-break: break-word;"><i class="bi bi-exclamation-triangle-fill me-2"></i>' +
                    BatchSync._escapeHtml(message) + '</div>';
            }
        }
        // Also show toast as backup notification
        showToast('同步失败：触发器依赖的监控项缺失，请查看弹窗详情', 'danger');
    },

    _escapeHtml: function(text) {
        var div = document.createElement('div');
        div.appendChild(document.createTextNode(text));
        return div.innerHTML;
    }
};
