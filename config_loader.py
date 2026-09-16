#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Zabbix Monitor as Code (MaC) 配置加载模块

优先级: 命令行参数 > 环境变量 > YAML 配置文件 > 内置默认值
"""

import os
from typing import Any, Dict, Optional

import yaml


def _defaults() -> Dict[str, Any]:
    """返回内置默认配置（兜底）"""
    return {
        'app': {
            'secret_key': 'dev-secret-key-change-me',
            'host': '127.0.0.1',
            'port': 5000,
            'debug': False,
            'default_template_name': '21001',
        },
        'database': {
            'host': 'localhost',
            'port': 5432,
            'name': 'ops',
            'user': 'postgres',
            'password': '',
            'client_encoding': 'utf8',
            'schema': 'zabbix_mac',
        },
        'zabbix_environments': [],
        'sync': {
            'default_workers': 5,
            'max_retry_attempts': 3,
            'retry_delay': 2,
            # 后台初始化/同步任务的单条语句超时（秒）。僵死任务的主防线：
            # 卡在 SQL 上时由 PostgreSQL 主动掐断，异常路径负责回滚并释放锁。
            'job_statement_timeout_seconds': 900,
            # 兜底硬超时（秒）。超过则强制回收全局同步锁，避免一次卡死
            # 导致此后所有同步/初始化永久返回 409。
            'job_hard_timeout_seconds': 1800,
        },
    }


def _deep_merge(base: Dict, override: Dict) -> None:
    """递归合并 override 到 base（原地修改）"""
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        elif value is not None:
            base[key] = value


def _apply_env_overrides(config: Dict) -> None:
    """用环境变量覆盖配置值"""
    # --- 数据库 ---
    for key in ['host', 'port', 'name', 'user', 'password']:
        env_val = os.environ.get(f'DB_{key.upper()}')
        if env_val is not None:
            target_key = 'port' if key == 'port' else key
            config['database'][target_key] = int(env_val) if key == 'port' else env_val

    # --- Flask ---
    for key in ['secret_key', 'host', 'port']:
        env_val = os.environ.get(f'APP_{key.upper()}')
        if env_val is not None:
            config['app'][key] = int(env_val) if key == 'port' else env_val

    # --- Zabbix 环境凭据（向后兼容现有环境变量命名） ---
    env_zabbix_map = {
        'szse_zw': ('ZABBIX_SZSE_ZW_URL', 'ZABBIX_SZSE_ZW_USER', 'ZABBIX_SZSE_ZW_PASS'),
        'szse_hlw': ('ZABBIX_SZSE_HLW_URL', 'ZABBIX_SZSE_HLW_USER', 'ZABBIX_SZSE_HLW_PASS'),
        'sse_zw': ('ZABBIX_SSE_ZW_URL', 'ZABBIX_SSE_ZW_USER', 'ZABBIX_SSE_ZW_PASS'),
        'sse_hlw': ('ZABBIX_SSE_HLW_URL', 'ZABBIX_SSE_HLW_USER', 'ZABBIX_SSE_HLW_PASS'),
    }
    for env in config.get('zabbix_environments', []):
        env_key = env.get('key', '')
        if env_key in env_zabbix_map:
            url_key, user_key, pass_key = env_zabbix_map[env_key]
            if os.environ.get(url_key):
                env['url'] = os.environ[url_key]
            if os.environ.get(user_key):
                env['username'] = os.environ[user_key]
            if os.environ.get(pass_key):
                env['password'] = os.environ[pass_key]


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """加载配置

    查找顺序:
    1. 传入的 config_path 参数
    2. APP_CONFIG 环境变量
    3. 当前目录下的 config.yaml（默认）

    Returns:
        合并后的完整配置字典
    """
    if config_path is None:
        config_path = os.environ.get('APP_CONFIG', 'config.yaml')

    config = _defaults()

    # 加载 YAML 文件
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                file_config = yaml.safe_load(f)
            if file_config:
                _deep_merge(config, file_config)
        except Exception as e:
            import sys
            print(f"[WARN] 无法加载配置文件 {config_path}: {e}", file=sys.stderr)

    # 应用环境变量覆盖
    _apply_env_overrides(config)

    # ENV 感知：ENV=local 时自动加载 config_{ENV}.yaml 并深度合并
    env_name = os.environ.get('ENV', '').strip()
    if env_name:
        local_path = f'config_{env_name}.yaml'
        if os.path.exists(local_path):
            try:
                with open(local_path, 'r', encoding='utf-8') as f:
                    local_config = yaml.safe_load(f)
                if local_config:
                    _deep_merge(config, local_config)
            except Exception as e:
                import sys
                print(f"[WARN] 无法加载 ENV 配置文件 {local_path}: {e}", file=sys.stderr)

    return config


def get_db_config(config: Optional[Dict] = None) -> Dict[str, Any]:
    """从配置中提取数据库连接参数字典（兼容 psycopg2.connect）"""
    if config is None:
        config = load_config()
    db = config['database']
    return {
        'host': db['host'],
        'port': db['port'],
        'database': db['name'],
        'user': db['user'],
        'password': db['password'],
        'client_encoding': db.get('client_encoding', 'utf8'),
        'options': f"-c search_path={db.get('schema', 'zabbix_mac')}",
    }


def get_zabbix_environments(config: Optional[Dict] = None) -> Dict[str, Dict[str, str]]:
    """从配置中提取 Zabbix 环境字典（兼容 app.py 旧格式）

    Returns:
        {环境名: {url, username, password}} 格式的字典
    """
    if config is None:
        config = load_config()
    envs = {}
    for env in config.get('zabbix_environments', []):
        envs[env['name']] = {
            'url': env.get('url', ''),
            'username': env.get('username', ''),
            'password': env.get('password', ''),
        }
    return envs
