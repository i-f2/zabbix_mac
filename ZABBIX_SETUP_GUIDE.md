# Zabbix 5.0 Docker 安装指南

## 已完成的步骤

✅ PostgreSQL 数据库已设置
- 数据库用户：zabbix
- 数据库名：zabbix
- 密码：zabbix

## 需要手动完成的步骤

### 1. 修改 PostgreSQL 配置

由于需要修改系统级别的 PostgreSQL 配置文件，请手动执行以下步骤：

#### 1.1 备份配置文件

```bash
sudo cp /opt/local/var/db/postgresql14/defaultdb/postgresql.conf /opt/local/var/db/postgresql14/defaultdb/postgresql.conf.backup
sudo cp /opt/local/var/db/postgresql14/defaultdb/pg_hba.conf /opt/local/var/db/postgresql14/defaultdb/pg_hba.conf.backup
```

#### 1.2 修改 postgresql.conf

编辑 `/opt/local/var/db/postgresql14/defaultdb/postgresql.conf`，找到 `listen_addresses` 并修改为：

```
listen_addresses = '*'
```

#### 1.3 修改 pg_hba.conf

编辑 `/opt/local/var/db/postgresql14/defaultdb/pg_hba.conf`，在文件末尾添加：

```
# Allow Docker containers to connect
host    all             all             172.16.0.0/12           scram-sha-256
host    all             all             192.168.0.0/16           scram-sha-256
host    all             all             10.0.0.0/8               scram-sha-256
```

#### 1.4 重启 PostgreSQL

```bash
sudo port reload postgresql14-server
```

或者：

```bash
sudo port unload postgresql14-server
sudo port load postgresql14-server
```

### 2. 启动 Zabbix Docker 容器

在项目目录下执行：

```bash
docker compose up -d
```

### 3. 验证安装

#### 3.1 检查容器状态

```bash
docker compose ps
```

#### 3.2 查看日志

```bash
docker compose logs -f zabbix-server
docker compose logs -f zabbix-web
```

#### 3.3 访问 Zabbix Web 界面

打开浏览器访问：http://localhost:8080

默认登录信息：
- 用户名：Admin
- 密码：zabbix

## 配置说明

### docker-compose.yml

- **zabbix-server**: Zabbix Server 5.0.45，连接到本地 PostgreSQL
- **zabbix-web-nginx-pgsql**: Zabbix Web 前端 5.0.45，使用 Nginx
- **zabbix-agent**: Zabbix Agent 5.0.45（可选）

### 网络配置

使用 `host.docker.internal` 让 Docker 容器访问宿主机的 PostgreSQL 服务。

### 数据库连接信息

- 数据库主机：host.docker.internal
- 数据库端口：5432
- 数据库名：zabbix
- 用户名：zabbix
- 密码：zabbix

## 故障排除

### 容器无法连接到数据库

1. 检查 PostgreSQL 是否正在监听所有地址：
```sql
SHOW listen_addresses;
```

2. 检查防火墙设置

3. 查看容器日志：
```bash
docker compose logs zabbix-server
```

### Web 界面无法访问

1. 检查容器状态：
```bash
docker compose ps
```

2. 检查端口是否被占用：
```bash
lsof -i :8080
```

3. 查看 Web 容器日志：
```bash
docker compose logs zabbix-web
```
