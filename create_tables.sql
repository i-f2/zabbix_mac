-- PostgreSQL 表结构设计
-- Zabbix Monitor as Code (MaC) 数据库模式

-- 1. 监控项表
CREATE TABLE IF NOT EXISTS items (
    id SERIAL PRIMARY KEY,
    item_key VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    type INTEGER NOT NULL,
    value_type INTEGER NOT NULL,
    delay VARCHAR(50) NOT NULL,
    description TEXT,
    units VARCHAR(50),
    multiplier INTEGER DEFAULT 0,
    delta INTEGER DEFAULT 0,
    history INTEGER DEFAULT 7,
    trends INTEGER DEFAULT 365,
    status INTEGER DEFAULT 0,
    template_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    master_item VARCHAR(255),
    preprocessing JSONB
);

-- 2. 触发器表
CREATE TABLE IF NOT EXISTS triggers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    expression TEXT NOT NULL,
    priority INTEGER NOT NULL,
    description TEXT,
    status INTEGER DEFAULT 0,
    template_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. 自动发现规则表
CREATE TABLE IF NOT EXISTS discovery_rules (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    key VARCHAR(255) NOT NULL,
    delay VARCHAR(50) NOT NULL,
    evaltype INTEGER DEFAULT 0,
    status INTEGER DEFAULT 0,
    template_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. 自动发现过滤条件表
CREATE TABLE IF NOT EXISTS filter_conditions (
    id SERIAL PRIMARY KEY,
    discovery_rule_id INTEGER NOT NULL REFERENCES discovery_rules(id) ON DELETE CASCADE,
    macro VARCHAR(255) NOT NULL,
    value TEXT NOT NULL,
    operator VARCHAR(50) DEFAULT 'MATCHES_REGEX',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. 监控项原型表
CREATE TABLE IF NOT EXISTS item_prototypes (
    id SERIAL PRIMARY KEY,
    discovery_rule_id INTEGER NOT NULL REFERENCES discovery_rules(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    key VARCHAR(255) NOT NULL,
    value_type INTEGER NOT NULL,
    delay VARCHAR(50) NOT NULL,
    description TEXT,
    units VARCHAR(50),
    multiplier INTEGER DEFAULT 0,
    delta INTEGER DEFAULT 0,
    history INTEGER DEFAULT 7,
    trends INTEGER DEFAULT 365,
    status INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. 触发器原型表
CREATE TABLE IF NOT EXISTS trigger_prototypes (
    id SERIAL PRIMARY KEY,
    discovery_rule_id INTEGER NOT NULL REFERENCES discovery_rules(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    expression TEXT NOT NULL,
    priority INTEGER NOT NULL,
    status INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7. 模板表
CREATE TABLE IF NOT EXISTS templates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_items_item_key ON items(item_key);
CREATE INDEX IF NOT EXISTS idx_items_template ON items(template_name);
CREATE INDEX IF NOT EXISTS idx_triggers_template ON triggers(template_name);
CREATE INDEX IF NOT EXISTS idx_discovery_rules_template ON discovery_rules(template_name);
CREATE INDEX IF NOT EXISTS idx_filter_conditions_rule ON filter_conditions(discovery_rule_id);
CREATE INDEX IF NOT EXISTS idx_item_prototypes_rule ON item_prototypes(discovery_rule_id);
CREATE INDEX IF NOT EXISTS idx_trigger_prototypes_rule ON trigger_prototypes(discovery_rule_id);

-- 插入示例数据（基于 common.yaml）
-- 1. 插入模板
INSERT INTO templates (name, description) VALUES 
('Template OS Linux by Zabbix agent - Standardized', 'Standard Linux monitoring template');

-- 2. 插入监控项
INSERT INTO items (item_key, name, type, value_type, delay, template_name) VALUES
('system.cpu.intr', 'Interrupts per second', 0, 0, '1m', 'Template OS Linux by Zabbix agent - Standardized'),
('system.cpu.load[all,avg1]', 'Load average (1m avg)', 0, 0, '1m', 'Template OS Linux by Zabbix agent - Standardized'),
('system.cpu.load[all,avg15]', 'Load average (15m avg)', 0, 0, '1m', 'Template OS Linux by Zabbix agent - Standardized'),
('system.cpu.load[all,avg5]', 'Load average (5m avg)', 0, 0, '1m', 'Template OS Linux by Zabbix agent - Standardized'),
('system.cpu.num', 'Number of CPUs', 0, 3, '1m', 'Template OS Linux by Zabbix agent - Standardized'),
('system.cpu.switches', 'Context switches per second', 0, 0, '1m', 'Template OS Linux by Zabbix agent - Standardized'),
('system.cpu.util', 'CPU utilization', 0, 0, '1m', 'Template OS Linux by Zabbix agent - Standardized'),
('system.cpu.util[,guest_nice]', 'CPU guest nice time', 0, 0, '1m', 'Template OS Linux by Zabbix agent - Standardized'),
('system.cpu.util[,guest]', 'CPU guest time', 0, 0, '1m', 'Template OS Linux by Zabbix agent - Standardized'),
('system.cpu.util[,idle]', 'CPU idle time', 0, 0, '1m', 'Template OS Linux by Zabbix agent - Standardized'),
('system.cpu.util[,interrupt]', 'CPU interrupt time', 0, 0, '1m', 'Template OS Linux by Zabbix agent - Standardized'),
('system.cpu.util[,iowait]', 'CPU iowait time', 0, 0, '1m', 'Template OS Linux by Zabbix agent - Standardized'),
('system.cpu.util[,nice]', 'CPU nice time', 0, 0, '1m', 'Template OS Linux by Zabbix agent - Standardized'),
('system.cpu.util[,softirq]', 'CPU softirq time', 0, 0, '1m', 'Template OS Linux by Zabbix agent - Standardized'),
('system.cpu.util[,steal]', 'CPU steal time', 0, 0, '1m', 'Template OS Linux by Zabbix agent - Standardized'),
('system.cpu.util[,system]', 'CPU system time', 0, 0, '1m', 'Template OS Linux by Zabbix agent - Standardized'),
('system.cpu.util[,user]', 'CPU user time', 0, 0, '1m', 'Template OS Linux by Zabbix agent - Standardized'),
('kernel.maxfiles', 'Maximum number of open file descriptors', 0, 3, '1h', 'Template OS Linux by Zabbix agent - Standardized'),
('kernel.maxproc', 'Maximum number of processes', 0, 3, '1h', 'Template OS Linux by Zabbix agent - Standardized'),
('proc.num', 'Number of processes', 0, 3, '1m', 'Template OS Linux by Zabbix agent - Standardized'),
('proc.num[,,run]', 'Number of running processes', 0, 3, '1m', 'Template OS Linux by Zabbix agent - Standardized'),
('system.boottime', 'System boot time', 0, 3, '15m', 'Template OS Linux by Zabbix agent - Standardized'),
('system.hostname', 'System name', 0, 4, '1h', 'Template OS Linux by Zabbix agent - Standardized'),
('system.localtime', 'System local time', 0, 3, '1m', 'Template OS Linux by Zabbix agent - Standardized');

-- 3. 插入触发器
INSERT INTO triggers (name, expression, priority, template_name) VALUES
('High CPU utilization (over {$CPU.UTIL.CRIT}% for 5m)', '{host:system.cpu.util.last()}>90', 3, 'Template OS Linux by Zabbix agent - Standardized'),
('Configured max number of open filedescriptors is too low (< {$KERNEL.MAXFILES.MIN})', '{host:kernel.maxfiles.last()}<100000', 1, 'Template OS Linux by Zabbix agent - Standardized'),
('Configured max number of processes is too low (< {$KERNEL.MAXPROC.MIN})', '{host:kernel.maxproc.last()}<10000', 1, 'Template OS Linux by Zabbix agent - Standardized'),
('System name has changed (new name: {ITEM.VALUE})', '{host:system.hostname.diff()}=1 and {host:system.hostname.strlen()}>0', 1, 'Template OS Linux by Zabbix agent - Standardized');

-- 4. 插入自动发现规则
-- 4.1 块设备发现
INSERT INTO discovery_rules (name, key, delay, evaltype, template_name) VALUES
('Block devices discovery', 'vfs.dev.discovery', '1h', 0, 'Template OS Linux by Zabbix agent - Standardized'),
('Mounted filesystem discovery', 'vfs.fs.discovery', '1h', 0, 'Template OS Linux by Zabbix agent - Standardized');

-- 4.2 插入块设备发现的过滤条件
INSERT INTO filter_conditions (discovery_rule_id, macro, value, operator) VALUES
((SELECT id FROM discovery_rules WHERE name = 'Block devices discovery'), '{#DEVTYPE}', 'disk', 'MATCHES_REGEX'),
((SELECT id FROM discovery_rules WHERE name = 'Block devices discovery'), '{#DEVNAME}', '.+', 'MATCHES_REGEX'),
((SELECT id FROM discovery_rules WHERE name = 'Block devices discovery'), '{#DEVNAME}', '^(loop[0-9]*|sd[a-z][0-9]+|nbd[0-9]+|sr[0-9]+|fd[0-9]+|dm-[0-9]+|ram[0-9]+|ploop[a-z0-9]+|md[0-9]*|hcp[0-9]*|zram[0-9]*)$', 'NOT_MATCHES_REGEX');

-- 4.3 插入文件系统发现的过滤条件
INSERT INTO filter_conditions (discovery_rule_id, macro, value, operator) VALUES
((SELECT id FROM discovery_rules WHERE name = 'Mounted filesystem discovery'), '{#FSTYPE}', '^(btrfs|ext2|ext3|ext4|reiser|xfs|ffs|ufs|jfs|jfs2|vxfs|hfs|apfs|refs|ntfs|fat32|zfs)$', 'MATCHES_REGEX'),
((SELECT id FROM discovery_rules WHERE name = 'Mounted filesystem discovery'), '{#FSTYPE}', '^\s$', 'NOT_MATCHES_REGEX'),
((SELECT id FROM discovery_rules WHERE name = 'Mounted filesystem discovery'), '{#FSNAME}', '.+', 'MATCHES_REGEX'),
((SELECT id FROM discovery_rules WHERE name = 'Mounted filesystem discovery'), '{#FSNAME}', '^(/dev|/sys|/run|/proc|.+/)shm$', 'NOT_MATCHES_REGEX');

-- 5. 插入块设备发现的监控项原型
INSERT INTO item_prototypes (discovery_rule_id, name, key, value_type, delay) VALUES
((SELECT id FROM discovery_rules WHERE name = 'Block devices discovery'), '{#DEVNAME}: Disk average queue size (avgqu-sz)', 'vfs.dev.queue_size[{#DEVNAME}]', 0, '0'),
((SELECT id FROM discovery_rules WHERE name = 'Block devices discovery'), '{#DEVNAME}: Disk read request avg waiting time (r_await)', 'vfs.dev.read.await[{#DEVNAME}]', 0, '1m'),
((SELECT id FROM discovery_rules WHERE name = 'Block devices discovery'), '{#DEVNAME}: Disk read rate', 'vfs.dev.read.rate[{#DEVNAME}]', 0, '0'),
((SELECT id FROM discovery_rules WHERE name = 'Block devices discovery'), '{#DEVNAME}: Disk read time (rate)', 'vfs.dev.read.time.rate[{#DEVNAME}]', 0, '0'),
((SELECT id FROM discovery_rules WHERE name = 'Block devices discovery'), '{#DEVNAME}: Disk utilization', 'vfs.dev.util[{#DEVNAME}]', 0, '0'),
((SELECT id FROM discovery_rules WHERE name = 'Block devices discovery'), '{#DEVNAME}: Disk write request avg waiting time (w_await)', 'vfs.dev.write.await[{#DEVNAME}]', 0, '1m'),
((SELECT id FROM discovery_rules WHERE name = 'Block devices discovery'), '{#DEVNAME}: Disk write rate', 'vfs.dev.write.rate[{#DEVNAME}]', 0, '0'),
((SELECT id FROM discovery_rules WHERE name = 'Block devices discovery'), '{#DEVNAME}: Disk write time (rate)', 'vfs.dev.write.time.rate[{#DEVNAME}]', 0, '0'),
((SELECT id FROM discovery_rules WHERE name = 'Block devices discovery'), '{#DEVNAME}: Get stats', 'vfs.file.contents[/sys/block/{#DEVNAME}/stat]', 4, '1m');

-- 6. 插入块设备发现的触发器原型
INSERT INTO trigger_prototypes (discovery_rule_id, description, expression, priority) VALUES
((SELECT id FROM discovery_rules WHERE name = 'Block devices discovery'), '{#DEVNAME}: Disk read/write request responses are too high (read > {$VFS.DEV.READ.AWAIT.WARN:"{#DEVNAME}"} ms for 15m or write > {$VFS.DEV.WRITE.AWAIT.WARN:"{#DEVNAME}"} ms for 15m)', 'min(15m)>20 or min(15m)>20', 3);

-- 7. 插入文件系统发现的监控项原型
INSERT INTO item_prototypes (discovery_rule_id, name, key, value_type, delay) VALUES
((SELECT id FROM discovery_rules WHERE name = 'Mounted filesystem discovery'), '{#FSNAME}: Free inodes in %', 'vfs.fs.inode[{#FSNAME},pfree]', 0, '1m'),
((SELECT id FROM discovery_rules WHERE name = 'Mounted filesystem discovery'), '{#FSNAME}: Space utilization', 'vfs.fs.size[{#FSNAME},pused]', 0, '1m'),
((SELECT id FROM discovery_rules WHERE name = 'Mounted filesystem discovery'), '{#FSNAME}: Total space', 'vfs.fs.size[{#FSNAME},total]', 3, '1m'),
((SELECT id FROM discovery_rules WHERE name = 'Mounted filesystem discovery'), '{#FSNAME}: Used space', 'vfs.fs.size[{#FSNAME},used]', 3, '1m');

-- 8. 插入文件系统发现的触发器原型
INSERT INTO trigger_prototypes (discovery_rule_id, description, expression, priority) VALUES
((SELECT id FROM discovery_rules WHERE name = 'Mounted filesystem discovery'), '{#FSNAME}: Running out of free inodes (free < {$VFS.FS.INODE.PFREE.MIN.CRIT:"{#FSNAME}"}%)', 'min(5m)<10', 3),
((SELECT id FROM discovery_rules WHERE name = 'Mounted filesystem discovery'), '{#FSNAME}: Running out of free inodes (free < {$VFS.FS.INODE.PFREE.MIN.WARN:"{#FSNAME}"}%)', 'min(5m)<20', 2),
((SELECT id FROM discovery_rules WHERE name = 'Mounted filesystem discovery'), '{#FSNAME}: Disk space is critically low (used > {$VFS.FS.PUSED.MAX.CRIT:"{#FSNAME}"}%)', 'last()>90', 3),
((SELECT id FROM discovery_rules WHERE name = 'Mounted filesystem discovery'), '{#FSNAME}: Disk space is low (used > {$VFS.FS.PUSED.MAX.WARN:"{#FSNAME}"}%)', 'last()>80', 2);

-- 提交事务
COMMIT;