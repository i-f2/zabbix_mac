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
    // Confirm Dialog Helper
    // ========================================================
    window.confirmAction = function (message) {
        return confirm(message || '确定要执行此操作吗？');
    };

    // ========================================================
    // Table Row Click (for clickable rows)
    // ========================================================
    document.querySelectorAll('tr[data-href]').forEach(function (row) {
        row.addEventListener('click', function () {
            window.location.href = this.getAttribute('data-href');
        });
        row.style.cursor = 'pointer';
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
    toastEl.innerHTML =
        '<div class="d-flex">' +
            '<div class="toast-body">' + message + '</div>' +
            '<button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>' +
        '</div>';
    document.body.appendChild(toastEl);
    var toast = new bootstrap.Toast(toastEl, { delay: 3000 });
    toast.show();
    toastEl.addEventListener('hidden.bs.toast', function () { toastEl.remove(); });
}
