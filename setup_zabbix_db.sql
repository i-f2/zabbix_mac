-- 创建 Zabbix 数据库和用户
CREATE USER zabbix WITH PASSWORD 'zabbix';
CREATE DATABASE zabbix OWNER zabbix;
GRANT ALL PRIVILEGES ON DATABASE zabbix TO zabbix;

-- 连接到 zabbix 数据库
\c zabbix;

-- 设置时区
SET TIME ZONE 'Asia/Shanghai';
