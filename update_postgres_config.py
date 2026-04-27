#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import psycopg2
import os

def update_postgres_config():
    print("开始更新 PostgreSQL 配置...")
    
    config_file = "/opt/local/var/db/postgresql14/defaultdb/postgresql.conf"
    hba_file = "/opt/local/var/db/postgresql14/defaultdb/pg_hba.conf"
    
    # 备份配置文件
    print("1. 备份配置文件...")
    os.system(f"cp {config_file} {config_file}.backup")
    os.system(f"cp {hba_file} {hba_file}.backup")
    print("   ✅ 备份完成")
    
    # 修改 postgresql.conf
    print("\n2. 修改 postgresql.conf...")
    with open(config_file, 'r') as f:
        content = f.read()
    
    # 修改 listen_addresses
    if 'listen_addresses' in content:
        lines = content.split('\n')
        new_lines = []
        for line in lines:
            if line.strip().startswith('listen_addresses') and not line.strip().startswith('#'):
                new_lines.append("listen_addresses = '*'")
                print(f"   修改 listen_addresses 为 '*'")
            else:
                new_lines.append(line)
        content = '\n'.join(new_lines)
    
    with open(config_file, 'w') as f:
        f.write(content)
    print("   ✅ postgresql.conf 更新完成")
    
    # 修改 pg_hba.conf
    print("\n3. 修改 pg_hba.conf...")
    with open(hba_file, 'r') as f:
        hba_content = f.read()
    
    # 添加 Docker 网络的访问权限
    docker_rules = [
        "# Allow Docker containers to connect",
        "host    all             all             172.16.0.0/12           scram-sha-256",
        "host    all             all             192.168.0.0/16           scram-sha-256",
        "host    all             all             10.0.0.0/8               scram-sha-256"
    ]
    
    if "172.16.0.0/12" not in hba_content:
        hba_content += '\n' + '\n'.join(docker_rules) + '\n'
        print("   添加 Docker 网络访问规则")
    
    with open(hba_file, 'w') as f:
        f.write(hba_content)
    print("   ✅ pg_hba.conf 更新完成")
    
    print("\n4. 重启 PostgreSQL...")
    # 尝试重启 PostgreSQL (MacPorts)
    os.system("sudo port load postgresql14-server 2>/dev/null || sudo port reload postgresql14-server 2>/dev/null || echo '请手动重启 PostgreSQL'")
    
    print("\n✅ PostgreSQL 配置更新完成！")
    print("\n请重启 PostgreSQL 服务以使配置生效：")
    print("  sudo port reload postgresql14-server")
    print("\n或者：")
    print("  sudo port unload postgresql14-server")
    print("  sudo port load postgresql14-server")

if __name__ == "__main__":
    update_postgres_config()
