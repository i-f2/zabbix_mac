#!/bin/bash
# =============================================================================
# Zabbix Monitor as Code (MaC) - 数据库迁移脚本
# =============================================================================
# 按编号顺序执行 database_update/ 中未应用的 SQL 迁移文件。
# 使用 schema_migrations 追踪表记录已应用的迁移，避免重复执行。
#
# 用法:
#   ./apply_migrations.sh [DB_HOST] [DB_PORT] [DB_NAME] [DB_USER]
#
# 参数:
#   DB_HOST  数据库主机地址 (默认: localhost)
#   DB_PORT  数据库端口     (默认: 5432)
#   DB_NAME  数据库名称     (默认: ops)
#   DB_USER  数据库用户     (默认: postgres)
#
# 示例:
#   ./apply_migrations.sh
#   ./apply_migrations.sh 192.168.1.100 5432 ops_prod postgres
#   PGPASSWORD=secret ./apply_migrations.sh db.example.com 5432 ops postgres
# =============================================================================

set -e

# --- 参数解析 ---
DB_HOST="${1:-localhost}"
DB_PORT="${2:-5432}"
DB_NAME="${3:-ops}"
DB_USER="${4:-postgres}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "============================================"
echo "  Zabbix MaC 数据库迁移"
echo "============================================"
echo "  主机: ${DB_HOST}:${DB_PORT}"
echo "  数据库: ${DB_NAME}"
echo "  用户: ${DB_USER}"
echo "  迁移目录: ${SCRIPT_DIR}"
echo "============================================"

# --- 确保迁移追踪表存在 ---
echo ""
echo "[INFO] 确保迁移追踪表存在..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "
  CREATE TABLE IF NOT EXISTS zabbix_mac.schema_migrations (
      version VARCHAR(10) PRIMARY KEY,
      filename VARCHAR(255) NOT NULL,
      applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );
" 2>&1 || {
    # 如果 zabbix_mac schema 不存在，先在 public schema 创建追踪表
    echo "[WARN] zabbix_mac schema 可能不存在，在 public schema 创建追踪表"
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "
      CREATE TABLE IF NOT EXISTS public.schema_migrations (
          version VARCHAR(10) PRIMARY KEY,
          filename VARCHAR(255) NOT NULL,
          applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      );
    "
}

# --- 遍历并应用迁移 ---
echo ""
echo "[INFO] 开始扫描迁移文件..."

APPLIED_COUNT=0
SKIPPED_COUNT=0

for f in $(ls "${SCRIPT_DIR}"/*.sql | grep -v 'apply_migrations' | sort); do
    filename=$(basename "$f")
    version=$(echo "$filename" | cut -d'_' -f1)

    # 检查迁移追踪表所在的 schema
    TRACKING_TABLE="zabbix_mac.schema_migrations"
    applied=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c \
        "SELECT COUNT(*) FROM ${TRACKING_TABLE} WHERE version='${version}';" 2>/dev/null || echo "")

    if [ -z "$applied" ]; then
        TRACKING_TABLE="public.schema_migrations"
        applied=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c \
            "SELECT COUNT(*) FROM ${TRACKING_TABLE} WHERE version='${version}';" 2>/dev/null || echo "0")
    fi

    applied=$(echo "$applied" | tr -d '[:space:]')

    if [ "$applied" = "0" ] || [ -z "$applied" ]; then
        echo ""
        echo "----------------------------------------"
        echo "  应用: ${filename}"
        echo "----------------------------------------"
        psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$f" -v ON_ERROR_STOP=1
        psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c \
            "INSERT INTO ${TRACKING_TABLE} (version, filename) VALUES ('${version}', '${filename}');"
        echo "[ OK ] ${filename} 应用成功"
        APPLIED_COUNT=$((APPLIED_COUNT + 1))
    else
        echo "  跳过: ${filename} (已应用)"
        SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
    fi
done

echo ""
echo "============================================"
echo "  迁移完成"
echo "  已应用: ${APPLIED_COUNT}  已跳过: ${SKIPPED_COUNT}"
echo "============================================"
