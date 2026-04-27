#!/bin/bash

# Zabbix 同步脚本

# Zabbix API 配置
ZABBIX_URL="http://localhost:8080/api_jsonrpc.php"
ZABBIX_USER="Admin"
ZABBIX_PASS="zabbix"

# 数据库配置
DB_HOST="localhost"
DB_PORT="5433"
DB_NAME="zabbix"
DB_USER="zabbix"
DB_PASS="zabbix"

# 配置文件路径
CONFIG_FILE="monitor_config.yaml"

# 运行同步
python3 zabbix_mac.py \
    --url "$ZABBIX_URL" \
    --username "$ZABBIX_USER" \
    --password "$ZABBIX_PASS" \
    --config "$CONFIG_FILE" \
    --db-host "$DB_HOST" \
    --db-port "$DB_PORT" \
    --db-name "$DB_NAME" \
    --db-user "$DB_USER" \
    --db-password "$DB_PASS"
