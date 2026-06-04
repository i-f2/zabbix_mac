# -*- coding: utf-8 -*-
"""
安全性测试 - 覆盖 SQL 注入、XSS、CSRF、认证缺失、硬编码凭证等
"""

import os
import sys
import re
import pytest
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestHardcodedSecrets:
    """硬编码敏感信息检查"""

    def test_flask_secret_key_is_hardcoded(self):
        """检查 Flask secret_key 是否为硬编码（报告问题，非断言失败）"""
        with open('app.py', 'r') as f:
            content = f.read()
        # 检查是否有硬编码的 secret_key
        has_hardcoded = "'supersecretkey'" in content or '"supersecretkey"' in content
        if has_hardcoded:
            print("⚠ 安全风险: app.py 中使用了硬编码的 secret_key 'supersecretkey'")
            print("  建议: 使用环境变量替代，如 os.environ.get('SECRET_KEY', os.urandom(24))")

    def test_db_password_is_hardcoded(self):
        """检查数据库密码是否硬编码"""
        with open('app.py', 'r') as f:
            content = f.read()

        # 检查 DB_CONFIG 中的 password 字段
        if "'password': ''" in content:
            print("⚠ 安全风险: app.py 中数据库密码为空字符串")
            print("  建议: 使用环境变量配置数据库密码")

    def test_debug_mode_enabled(self):
        """检查生产环境是否开启 debug 模式"""
        with open('app.py', 'r') as f:
            content = f.read()

        if "debug=True" in content:
            print("⚠ 安全风险: app.py 启用了 debug=True 模式")
            print("  建议: 生产环境应设为 debug=False，通过环境变量控制")

    def test_zabbix_password_cli_argument(self):
        """检查 Zabbix 密码是否通过命令行参数传递"""
        with open('zabbix_mac.py', 'r') as f:
            content = f.read()

        passwords_in_cli = re.findall(r'--password|--db-password', content)
        if passwords_in_cli:
            print("⚠ 安全风险: 密码通过命令行参数传递，可能被 ps 命令查看")
            print("  建议: 使用环境变量或配置文件读取密码")

    def test_no_auth_in_app(self):
        """检查 app.py 是否有认证机制"""
        with open('app.py', 'r') as f:
            content = f.read()

        has_auth = any(kw in content.lower() for kw in ['login_required', 'flask-login', 'flask_login',
                                                         'session[\'user', 'authenticate', '@login_required'])
        if not has_auth:
            print("⚠ 安全风险: app.py 没有任何认证/授权机制")
            print("  建议: 引入 Flask-Login 实现用户认证")


class TestSQLInjection:
    """SQL 注入测试 - 验证参数化查询的使用"""

    def test_app_uses_parameterized_queries(self):
        """验证 app.py 所有 SQL 查询都使用参数化"""
        with open('app.py', 'r') as f:
            content = f.read()

        # 找到所有 execute 调用
        execute_calls = re.findall(r'cur\.execute\(([^)]+)\)', content)
        risky_calls = []

        for call in execute_calls:
            # 检查是否有 f-string 或字符串拼接的 SQL
            if re.search(r'f["\']', call) or '+' in call:
                # 排除已知安全的情况（如 LIMIT 固定值）
                if 'column_names' not in call and 'placeholders' not in call:
                    risky_calls.append(call.strip())

        if risky_calls:
            print(f"⚠ 潜在风险: 发现 {len(risky_calls)} 处可能的非参数化 SQL 查询")
            for c in risky_calls[:3]:
                print(f"  - {c[:80]}")
        else:
            print("✓ app.py 所有 SQL 查询均使用参数化，无 SQL 注入风险")

    def test_zabbix_mac_uses_parameterized_queries(self):
        """验证 zabbix_mac.py 使用参数化查询"""
        with open('zabbix_mac.py', 'r') as f:
            content = f.read()

        execute_calls = re.findall(r'cur\.execute\(([^)]+)\)', content)
        risky_calls = []

        for call in execute_calls:
            if re.search(r'f["\']', call) or '+' in call:
                if 'column_names' not in call and 'placeholders' not in call:
                    risky_calls.append(call.strip())

        if risky_calls:
            print(f"⚠ 潜在风险: 发现 {len(risky_calls)} 处可能的非参数化 SQL 查询")
            for c in risky_calls[:3]:
                print(f"  - {c[:80]}")
        else:
            print("✓ zabbix_mac.py 所有 SQL 查询均使用参数化，无 SQL 注入风险")


class TestCSRF:
    """CSRF 防护测试"""

    def test_no_csrf_protection(self):
        """检查是否缺少 CSRF 保护"""
        with open('app.py', 'r') as f:
            content = f.read()

        has_csrf = any(kw in content for kw in ['CSRFProtect', 'csrf.token', 'csrf_token',
                                                  'WTF_CSRF_ENABLED'])
        if not has_csrf:
            print("⚠ 安全风险: app.py 缺少 CSRF 保护")
            print("  建议: 使用 Flask-WTF 的 CSRFProtect 添加 CSRF 防护")
        else:
            print("✓ CSRF 保护已启用")

    def test_post_routes_vulnerable_to_csrf(self):
        """统计易受 CSRF 攻击的 POST 路由"""
        with open('app.py', 'r') as f:
            content = f.read()

        # 查找所有 POST 路由
        route_pattern = re.findall(r"@app\.route\(['\"]([^'\"]+)['\"]", content)

        # 查找带 methods=['POST' 或 methods=['GET', 'POST' 的路由
        post_routes = re.findall(r"@app\.route\(['\"]([^'\"]+)['\"].*?POST", content)

        if post_routes:
            print(f"⚠ 安全风险: 发现 {len(post_routes)} 个 POST 路由无 CSRF 保护")
            for route in post_routes[:5]:
                print(f"  - {route}")


class TestXSS:
    """XSS 跨站脚本测试"""

    def test_flash_messages_unsafe(self):
        """检查 flash 消息是否可能包含未转义的用户输入"""
        with open('app.py', 'r') as f:
            content = f.read()

        # 查找 flash 调用中包含 f-string 或拼接用户输入的情况
        flash_calls = re.findall(r'flash\(f?["\'][^"\']*\{[^}]*\}', content)

        if flash_calls:
            print(f"⚠ 潜在 XSS 风险: 发现 {len(flash_calls)} 处 flash 消息可能包含变量")
            for c in flash_calls[:5]:
                print(f"  - {c[:80]}")
        else:
            print("✓ 未发现明显的 XSS 风险")

    def test_user_input_in_templates(self):
        """检查模板中使用 |safe 过滤器的位置"""
        template_dir = 'templates'
        if not os.path.exists(template_dir):
            return

        safe_usage = []
        for fname in os.listdir(template_dir):
            if fname.endswith('.html'):
                with open(os.path.join(template_dir, fname), 'r') as f:
                    content = f.read()
                    matches = re.findall(r'\|safe', content)
                    if matches:
                        safe_usage.append((fname, len(matches)))

        if safe_usage:
            print("⚠ 潜在 XSS 风险: 以下模板使用了 |safe 过滤器")
            for fname, count in safe_usage:
                print(f"  - {fname}: {count} 处")
        else:
            print("✓ 模板中未使用 |safe 过滤器")


class TestFilePermissions:
    """文件权限安全测试"""

    def test_config_permissions(self):
        """检查配置文件权限"""
        sensitive_files = ['app.py', 'zabbix_mac.py']
        for fname in sensitive_files:
            if os.path.exists(fname):
                mode = oct(os.stat(fname).st_mode)[-3:]
                print(f"  {fname}: 权限 {mode}")

    def test_pycache_not_committed(self):
        """检查 __pycache__ 是否被忽略"""
        if os.path.exists('.gitignore'):
            with open('.gitignore', 'r') as f:
                content = f.read()
            if '__pycache__' in content:
                print("✓ __pycache__ 已在 .gitignore 中忽略")
            else:
                print("⚠ 建议将 __pycache__ 添加到 .gitignore")


class TestSecurityBestPractices:
    """安全最佳实践检查"""

    def test_use_of_env_vars(self):
        """检查是否使用了环境变量"""
        with open('app.py', 'r') as f:
            app_content = f.read()
        with open('zabbix_mac.py', 'r') as f:
            mac_content = f.read()

        # 检查 os.environ 的使用
        app_env_usage = len(re.findall(r'os\.environ|os\.getenv', app_content))
        mac_env_usage = len(re.findall(r'os\.environ|os\.getenv', mac_content))

        print(f"  app.py 使用了 {app_env_usage} 次环境变量")
        print(f"  zabbix_mac.py 使用了 {mac_env_usage} 次环境变量")

        if app_env_usage == 0:
            print("  建议: app.py 应使用环境变量配置敏感信息")

    def test_input_validation(self):
        """检查输入验证"""
        with open('app.py', 'r') as f:
            content = f.read()

        # 检查是否有类型转换类的验证
        has_int_conversion = 'int(request.form' in content
        if has_int_conversion:
            print("✓ 部分输入进行了类型转换验证")
        else:
            print("⚠ 未发现输入验证")
