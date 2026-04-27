#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import psycopg2

def insert_sample_data():
    conn = None
    try:
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            database='zabbix_mac',
            user='fan',
            password=''
        )
        
        cur = conn.cursor()
        
        # 1. 插入模板
        print("正在插入模板...")
        cur.execute("""
            INSERT INTO templates (name, description) 
            VALUES (%s, %s)
            ON CONFLICT (name) DO NOTHING
        """, ('Template OS Linux by Zabbix agent - Standardized', 'Standard Linux monitoring template'))
        print("✓ 模板插入成功")
        
        # 获取模板 ID
        cur.execute("SELECT id FROM templates WHERE name = %s", 
                   ('Template OS Linux by Zabbix agent - Standardized',))
        template_id = cur.fetchone()[0]
        
        # 2. 插入监控项
        print("\n正在插入监控项...")
        items = [
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
            ('system.localtime', 'System local time', 0, 3, '1m', 'Template OS Linux by Zabbix agent - Standardized'),
        ]
        
        for item in items:
            cur.execute("""
                INSERT INTO items (item_key, name, type, value_type, delay, template_name)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (item_key) DO NOTHING
            """, item)
        print(f"✓ {len(items)} 个监控项插入成功")
        
        # 3. 插入触发器 - 先检查是否已存在
        print("\n正在插入触发器...")
        triggers = [
            ('High CPU utilization (over {$CPU.UTIL.CRIT}% for 5m)', '{host:system.cpu.util.last()}>90', 3, 'Template OS Linux by Zabbix agent - Standardized'),
            ('Configured max number of open filedescriptors is too low (< {$KERNEL.MAXFILES.MIN})', '{host:kernel.maxfiles.last()}<100000', 1, 'Template OS Linux by Zabbix agent - Standardized'),
            ('Configured max number of processes is too low (< {$KERNEL.MAXPROC.MIN})', '{host:kernel.maxproc.last()}<10000', 1, 'Template OS Linux by Zabbix agent - Standardized'),
            ('System name has changed (new name: {ITEM.VALUE})', '{host:system.hostname.diff()}=1 and {host:system.hostname.strlen()}>0', 1, 'Template OS Linux by Zabbix agent - Standardized'),
        ]
        
        inserted_triggers = 0
        for trigger in triggers:
            # 检查是否已存在
            cur.execute("""
                SELECT id FROM triggers 
                WHERE name = %s AND template_name = %s
            """, (trigger[0], trigger[3]))
            
            if cur.fetchone() is None:
                cur.execute("""
                    INSERT INTO triggers (name, expression, priority, template_name)
                    VALUES (%s, %s, %s, %s)
                """, trigger)
                inserted_triggers += 1
        print(f"✓ {inserted_triggers} 个触发器插入成功")
        
        # 4. 插入自动发现规则
        print("\n正在插入自动发现规则...")
        discovery_rules = [
            ('Block devices discovery', 'vfs.dev.discovery', '1h', 0, 'Template OS Linux by Zabbix agent - Standardized'),
            ('Mounted filesystem discovery', 'vfs.fs.discovery', '1h', 0, 'Template OS Linux by Zabbix agent - Standardized'),
        ]
        
        inserted_rules = 0
        for rule in discovery_rules:
            # 检查是否已存在
            cur.execute("""
                SELECT id FROM discovery_rules 
                WHERE name = %s AND template_name = %s
            """, (rule[0], rule[4]))
            
            existing = cur.fetchone()
            if existing is None:
                cur.execute("""
                    INSERT INTO discovery_rules (name, key, delay, evaltype, template_name)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                """, rule)
                inserted_rules += 1
        print(f"✓ {inserted_rules} 个自动发现规则插入成功")
        
        # 获取规则 ID
        cur.execute("SELECT id, name FROM discovery_rules WHERE template_name = %s", 
                   ('Template OS Linux by Zabbix agent - Standardized',))
        rules = {row[1]: row[0] for row in cur.fetchall()}
        
        # 5. 插入过滤条件
        print("\n正在插入过滤条件...")
        
        # 块设备发现的过滤条件
        block_conditions = [
            (rules['Block devices discovery'], '{#DEVTYPE}', 'disk', 'MATCHES_REGEX'),
            (rules['Block devices discovery'], '{#DEVNAME}', '.+', 'MATCHES_REGEX'),
            (rules['Block devices discovery'], '{#DEVNAME}', '^(loop[0-9]*|sd[a-z][0-9]+|nbd[0-9]+|sr[0-9]+|fd[0-9]+|dm-[0-9]+|ram[0-9]+|ploop[a-z0-9]+|md[0-9]*|hcp[0-9]*|zram[0-9]*)$', 'NOT_MATCHES_REGEX'),
        ]
        
        # 文件系统发现的过滤条件
        fs_conditions = [
            (rules['Mounted filesystem discovery'], '{#FSTYPE}', '^(btrfs|ext2|ext3|ext4|reiser|xfs|ffs|ufs|jfs|jfs2|vxfs|hfs|apfs|refs|ntfs|fat32|zfs)$', 'MATCHES_REGEX'),
            (rules['Mounted filesystem discovery'], '{#FSTYPE}', '^\\s$', 'NOT_MATCHES_REGEX'),
            (rules['Mounted filesystem discovery'], '{#FSNAME}', '.+', 'MATCHES_REGEX'),
            (rules['Mounted filesystem discovery'], '{#FSNAME}', '^(/dev|/sys|/run|/proc|.+/shm$)', 'NOT_MATCHES_REGEX'),
        ]
        
        all_conditions = block_conditions + fs_conditions
        for cond in all_conditions:
            cur.execute("""
                INSERT INTO filter_conditions (discovery_rule_id, macro, value, operator)
                VALUES (%s, %s, %s, %s)
            """, cond)
        print(f"✓ {len(all_conditions)} 个过滤条件插入成功")
        
        # 6. 插入监控项原型
        print("\n正在插入监控项原型...")
        
        # 块设备发现的监控项原型
        block_item_protos = [
            (rules['Block devices discovery'], '{#DEVNAME}: Disk average queue size (avgqu-sz)', 'vfs.dev.queue_size[{#DEVNAME}]', 0, '0'),
            (rules['Block devices discovery'], '{#DEVNAME}: Disk read request avg waiting time (r_await)', 'vfs.dev.read.await[{#DEVNAME}]', 0, '1m'),
            (rules['Block devices discovery'], '{#DEVNAME}: Disk read rate', 'vfs.dev.read.rate[{#DEVNAME}]', 0, '0'),
            (rules['Block devices discovery'], '{#DEVNAME}: Disk read time (rate)', 'vfs.dev.read.time.rate[{#DEVNAME}]', 0, '0'),
            (rules['Block devices discovery'], '{#DEVNAME}: Disk utilization', 'vfs.dev.util[{#DEVNAME}]', 0, '0'),
            (rules['Block devices discovery'], '{#DEVNAME}: Disk write request avg waiting time (w_await)', 'vfs.dev.write.await[{#DEVNAME}]', 0, '1m'),
            (rules['Block devices discovery'], '{#DEVNAME}: Disk write rate', 'vfs.dev.write.rate[{#DEVNAME}]', 0, '0'),
            (rules['Block devices discovery'], '{#DEVNAME}: Disk write time (rate)', 'vfs.dev.write.time.rate[{#DEVNAME}]', 0, '0'),
            (rules['Block devices discovery'], '{#DEVNAME}: Get stats', 'vfs.file.contents[/sys/block/{#DEVNAME}/stat]', 4, '1m'),
        ]
        
        # 文件系统发现的监控项原型
        fs_item_protos = [
            (rules['Mounted filesystem discovery'], '{#FSNAME}: Free inodes in %', 'vfs.fs.inode[{#FSNAME},pfree]', 0, '1m'),
            (rules['Mounted filesystem discovery'], '{#FSNAME}: Space utilization', 'vfs.fs.size[{#FSNAME},pused]', 0, '1m'),
            (rules['Mounted filesystem discovery'], '{#FSNAME}: Total space', 'vfs.fs.size[{#FSNAME},total]', 3, '1m'),
            (rules['Mounted filesystem discovery'], '{#FSNAME}: Used space', 'vfs.fs.size[{#FSNAME},used]', 3, '1m'),
        ]
        
        all_item_protos = block_item_protos + fs_item_protos
        for proto in all_item_protos:
            cur.execute("""
                INSERT INTO item_prototypes (discovery_rule_id, name, key, value_type, delay)
                VALUES (%s, %s, %s, %s, %s)
            """, proto)
        print(f"✓ {len(all_item_protos)} 个监控项原型插入成功")
        
        # 7. 插入触发器原型
        print("\n正在插入触发器原型...")
        
        # 块设备发现的触发器原型
        block_trigger_protos = [
            (rules['Block devices discovery'], '{#DEVNAME}: Disk read/write request responses are too high (read > {$VFS.DEV.READ.AWAIT.WARN:"{#DEVNAME}"} ms for 15m or write > {$VFS.DEV.WRITE.AWAIT.WARN:"{#DEVNAME}"} ms for 15m)', 'min(15m)>20 or min(15m)>20', 3),
        ]
        
        # 文件系统发现的触发器原型
        fs_trigger_protos = [
            (rules['Mounted filesystem discovery'], '{#FSNAME}: Running out of free inodes (free < {$VFS.FS.INODE.PFREE.MIN.CRIT:"{#FSNAME}"}%)', 'min(5m)<10', 3),
            (rules['Mounted filesystem discovery'], '{#FSNAME}: Running out of free inodes (free < {$VFS.FS.INODE.PFREE.MIN.WARN:"{#FSNAME}"}%)', 'min(5m)<20', 2),
            (rules['Mounted filesystem discovery'], '{#FSNAME}: Disk space is critically low (used > {$VFS.FS.PUSED.MAX.CRIT:"{#FSNAME}"}%)', 'last()>90', 3),
            (rules['Mounted filesystem discovery'], '{#FSNAME}: Disk space is low (used > {$VFS.FS.PUSED.MAX.WARN:"{#FSNAME}"}%)', 'last()>80', 2),
        ]
        
        all_trigger_protos = block_trigger_protos + fs_trigger_protos
        for proto in all_trigger_protos:
            cur.execute("""
                INSERT INTO trigger_prototypes (discovery_rule_id, description, expression, priority)
                VALUES (%s, %s, %s, %s)
            """, proto)
        print(f"✓ {len(all_trigger_protos)} 个触发器原型插入成功")
        
        conn.commit()
        print("\n✅ 所有示例数据插入成功！")
        
        # 验证数据
        print("\n验证数据:")
        cur.execute('SELECT COUNT(*) FROM items')
        items_count = cur.fetchone()[0]
        print(f'监控项数量: {items_count}')
        
        cur.execute('SELECT COUNT(*) FROM triggers')
        triggers_count = cur.fetchone()[0]
        print(f'触发器数量: {triggers_count}')
        
        cur.execute('SELECT COUNT(*) FROM discovery_rules')
        rules_count = cur.fetchone()[0]
        print(f'自动发现规则数量: {rules_count}')
        
        cur.execute('SELECT COUNT(*) FROM templates')
        templates_count = cur.fetchone()[0]
        print(f'模板数量: {templates_count}')
        
        cur.close()
        
    except Exception as e:
        print(f"❌ 插入数据失败: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    insert_sample_data()
