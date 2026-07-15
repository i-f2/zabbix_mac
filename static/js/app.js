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
    // Popconfirm — bubble confirmation for unconfirm/sensitive actions
    // ========================================================
    window.popConfirm = function (btn, message, onConfirm) {
        if (btn._popconfirmActive) return;
        btn._popconfirmActive = true;

        var popover = new bootstrap.Popover(btn, {
            html: true,
            trigger: 'manual',
            placement: 'top',
            fallbackPlacements: ['bottom', 'right'],
            content: '<div class="popconfirm-box">' +
                '<span class="popconfirm-text">' + message + '</span>' +
                '<div class="popconfirm-actions mt-2 d-flex gap-2 justify-content-end">' +
                '<button class="btn btn-sm btn-danger popconfirm-yes">确认</button>' +
                '<button class="btn btn-sm btn-outline-secondary popconfirm-no">取消</button>' +
                '</div></div>'
        });
        popover.show();

        var handler = function (e) {
            if (e.target.classList.contains('popconfirm-yes')) {
                popover.dispose();
                btn._popconfirmActive = false;
                document.removeEventListener('click', handler);
                onConfirm();
            } else if (e.target.classList.contains('popconfirm-no') || !e.target.closest('.popover')) {
                popover.dispose();
                btn._popconfirmActive = false;
                document.removeEventListener('click', handler);
            }
        };
        setTimeout(function () { document.addEventListener('click', handler); }, 10);
    };

    // ========================================================
    // Centralized toggleConfirm — AJAX no-reload + popconfirm guard
    // Templates call: toggleConfirmRow(id, action, btn, confirmUrl, unconfirmUrl, rowSelector)
    // ========================================================
    window.toggleConfirmRow = async function (id, action, btn, confirmUrl, unconfirmUrl) {
        if (action === 'unconfirm') {
            popConfirm(btn, '确认取消该监控项的审核状态吗？', function () {
                _executeToggle(id, action, btn, confirmUrl, unconfirmUrl);
            });
            return;
        }
        _executeToggle(id, action, btn, confirmUrl, unconfirmUrl);
    };

    function _executeToggle(id, action, btn, confirmUrl, unconfirmUrl) {
        var origHTML = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm" style="width:14px;height:14px;"></span>';

        var url = action === 'confirm' ? confirmUrl.replace('__ID__', id) : unconfirmUrl.replace('__ID__', id);
        fetch(url, { method: 'POST' })
            .then(function (res) { return res.json(); })
            .then(function (data) {
                if (!data.success) {
                    showToast(data.message || '操作失败', 'danger');
                    btn.disabled = false;
                    btn.innerHTML = origHTML;
                    return;
                }
                showToast(action === 'confirm' ? '已确认' : '已取消确认', 'success');

                // Update confirm status cell in the same row
                var row = btn.closest('tr');
                if (row) {
                    var statusCell = row.querySelector('.col-fw-status.col-sticky-r3, td.col-sticky-r3');
                    if (statusCell) {
                        statusCell.textContent = action === 'confirm' ? '已确认' : '未确认';
                    }

                    // Swap button in action cell
                    var actionCell = row.querySelector('.col-sticky-r1');
                    if (actionCell) {
                        var editBtn = actionCell.querySelector('a');
                        var editHTML = editBtn ? editBtn.outerHTML : '';

                        if (action === 'confirm') {
                            // Now confirmed → show unconfirm button
                            actionCell.innerHTML = editHTML +
                                '<button class="btn btn-sm btn-outline-danger" ' +
                                'onclick="toggleConfirmRow(' + id + ', \'unconfirm\', this, ' +
                                '\'' + confirmUrl + '\', \'' + unconfirmUrl + '\')">' +
                                '<i class="bi bi-arrow-return-left"></i> 取消确认</button>';
                        } else {
                            // Now unconfirmed → show confirm button (read change_type from data attr)
                            var changeType = actionCell.getAttribute('data-change-type') || '';
                            var confirmBtnHTML = _buildConfirmButton(id, changeType, confirmUrl, unconfirmUrl);
                            actionCell.innerHTML = editHTML + confirmBtnHTML;
                        }
                    }
                }
            })
            .catch(function (e) {
                showToast('请求失败: ' + e.message, 'danger');
                btn.disabled = false;
                btn.innerHTML = origHTML;
            });
    }

    function _buildConfirmButton(id, changeType, confirmUrl, unconfirmUrl) {
        var map = {
            'new':      { cls: 'btn-success',   icon: 'bi-plus-circle',      label: '确认新增' },
            'update':   { cls: 'btn-warning',   icon: 'bi-arrow-clockwise',  label: '确认变更' },
            'delete':   { cls: 'btn-danger',    icon: 'bi-x-circle',         label: '确认下线' },
        };
        var cfg = map[changeType] || { cls: 'btn-success', icon: 'bi-check-lg', label: '确认' };
        return '<button class="btn btn-sm ' + cfg.cls + '" ' +
            'onclick="toggleConfirmRow(' + id + ', \'confirm\', this, ' +
            '\'' + confirmUrl + '\', \'' + unconfirmUrl + '\')">' +
            '<i class="bi ' + cfg.icon + '"></i> ' + cfg.label + '</button>';
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
window.BatchSync = {
    onCheckboxChange: function() {
        var checked = document.querySelectorAll('.row-checkbox:checked');
        var count = checked.length;
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
            var total = document.querySelectorAll('.row-checkbox').length;
            selectAll.checked = (count === total && total > 0);
            selectAll.indeterminate = (count > 0 && count < total);
        }
    },

    toggleAll: function(el) {
        var checkboxes = document.querySelectorAll('.row-checkbox');
        checkboxes.forEach(function(cb) { cb.checked = el.checked; });
        BatchSync.onCheckboxChange();
    },

    getSelectedIds: function() {
        var ids = [];
        document.querySelectorAll('.row-checkbox:checked').forEach(function(cb) {
            ids.push(parseInt(cb.value));
        });
        return ids;
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
        body.innerHTML = '<div class="text-center py-5"><div class="spinner-border text-primary" role="status"></div><p class="mt-3 text-muted">正在获取差异对比...</p></div>';
        confirmBtn.disabled = true;
        modal.show();

        try {
            var res = await fetch('/api/sync/preview', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    ids: ids,
                    table: window.BATCH_SYNC_CONFIG.table,
                    environment: env
                })
            });
            var data = await res.json();
            if (!data.success) {
                body.innerHTML = '<div class="alert alert-danger m-3">' + BatchSync._escapeHtml(data.message) + '</div>';
                return;
            }
            BatchSync.renderDiff(data);
            confirmBtn.disabled = false;
            previewModalEl._syncPayload = { ids: ids, table: window.BATCH_SYNC_CONFIG.table, environment: env };
        } catch (e) {
            body.innerHTML = '<div class="alert alert-danger m-3">请求失败: ' + BatchSync._escapeHtml(e.message) + '</div>';
        }
    },

    renderDiff: function(data) {
        var modalEl = document.getElementById('diffPreviewModal');
        var summary = modalEl.querySelector('.diff-summary');
        var body = modalEl.querySelector('.modal-body');
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
            var res = await fetch('/api/sync/apply', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            var data = await res.json();
            var modal = bootstrap.Modal.getInstance(modalEl);
            modal.hide();
            showToast(data.message, data.success ? 'success' : 'danger');
            if (data.success) setTimeout(function() { location.reload(); }, 1500);
        } catch (e) {
            showToast('同步请求失败: ' + e.message, 'danger');
            confirmBtn.disabled = false;
            confirmBtn.innerHTML = '<i class="bi bi-cloud-upload"></i> 确认同步下发';
        }
    },

    _escapeHtml: function(text) {
        var div = document.createElement('div');
        div.appendChild(document.createTextNode(text));
        return div.innerHTML;
    }
};
