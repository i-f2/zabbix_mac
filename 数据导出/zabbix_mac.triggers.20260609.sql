--
-- PostgreSQL database dump
--

\restrict W8H2Wh5KkHTNgYJ98aWRcHL4Ni5vevbuJgF6318iwJYVJEKfjQXaJZByd8Onsh1

-- Dumped from database version 14.23
-- Dumped by pg_dump version 14.23

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Data for Name: triggers; Type: TABLE DATA; Schema: zabbix_mac; Owner: -
--

INSERT INTO zabbix_mac.triggers VALUES (1, '{HOST.NAME}_{HOST.IP} CPU使用率 (over 100% for 5m)', '{host:system.cpu.util.last()}>100', 3, NULL, 0, '21001', '2026-04-17 09:02:07.059233', '2026-04-17 09:02:07.059233');
INSERT INTO zabbix_mac.triggers VALUES (2, '{HOST.NAME}_{HOST.IP} Configured max number of open filedescriptors is too low (< 256)', '{host:kernel.maxfiles.last()}<256', 1, NULL, 0, '21001', '2026-04-17 09:02:07.059233', '2026-04-17 09:02:07.059233');
INSERT INTO zabbix_mac.triggers VALUES (4, '{HOST.NAME}_{HOST.IP} System name has changed (new name: {ITEM.VALUE})', '{host:system.hostname.diff()}=1 and {host:system.hostname.strlen()}>0', 1, NULL, 0, '21001', '2026-04-17 09:02:07.059233', '2026-04-17 09:02:07.059233');
INSERT INTO zabbix_mac.triggers VALUES (17, '{HOST.NAME}_{HOST.IP} CPU负载单核已满载 (per CPU load over 1 for 5m)', '{host:system.cpu.load[all,avg1].min(5m)}/{host:system.cpu.num.last()}>1 and {host:system.cpu.load[all,avg5].last()}>0 and {host:system.cpu.load[all,avg15].last()}>0', 0, '', 0, '21001', '2026-04-29 18:05:22.699039', '2026-04-29 18:05:22.699039');
INSERT INTO zabbix_mac.triggers VALUES (13, '{HOST.NAME}_{HOST.IP} has been restarted (uptime < 10m)', '{host:system.uptime.last()}<10m', 2, '', 0, '21001', '2026-04-29 17:34:16.347324', '2026-04-29 17:34:16.347324');
INSERT INTO zabbix_mac.triggers VALUES (16, '{HOST.NAME}_{HOST.IP} CPU使用率 (over 60% for 5m)', '{host:system.cpu.util.min(5m)}>60', 0, '', 0, '21001', '2026-04-29 18:02:21.489376', '2026-04-29 18:02:21.489376');
INSERT INTO zabbix_mac.triggers VALUES (15, '{HOST.NAME}_{HOST.IP} CPU使用率 (over 80% for 5m)', '{host:system.cpu.util.min(5m)}>80', 1, '', 0, '21001', '2026-04-29 18:01:16.877681', '2026-04-29 18:01:16.877681');
INSERT INTO zabbix_mac.triggers VALUES (14, '{HOST.NAME}_{HOST.IP} 内存使用率 (>80% for 5m)', '{host:vm.memory.utilization.min(5m)}>80', 1, '', 0, '21001', '2026-04-29 17:54:36.558982', '2026-04-29 17:54:36.558982');
INSERT INTO zabbix_mac.triggers VALUES (7, '{HOST.NAME}_{HOST.IP} 内存使用率 (>90% for 5m)', '{host:vm.memory.utilization.min(5m)}>90', 3, '', 0, '21001', '2026-04-29 17:17:17.83902', '2026-04-29 17:17:17.83902');
INSERT INTO zabbix_mac.triggers VALUES (9, '{HOST.NAME}_{HOST.IP} 可用内存 (<20M of {ITEM.VALUE2})', '{host:vm.memory.size[available].max(5m)}<20M and {host:vm.memory.size[total].last()}>0', 3, '', 0, '21001', '2026-04-29 17:22:13.614714', '2026-04-29 17:22:13.614714');
INSERT INTO zabbix_mac.triggers VALUES (10, '{HOST.NAME}_{HOST.IP} Operating system description has changed', '{host:system.sw.os.diff()}=1 and {host:system.sw.os.strlen()}>0', 1, '', 0, '21001', '2026-04-29 17:29:59.275176', '2026-04-29 17:29:59.275176');
INSERT INTO zabbix_mac.triggers VALUES (11, '{HOST.NAME}_{HOST.IP} System time is out of sync (diff with Zabbix server > 60s)', '{host:system.localtime.fuzzytime(60)}=0', 2, '', 0, '21001', '2026-04-29 17:31:50.761174', '2026-04-29 17:31:50.761174');
INSERT INTO zabbix_mac.triggers VALUES (8, '{HOST.NAME}_{HOST.IP} High swap space usage (less than 50% free)', '{host:system.swap.size[,pfree].max(5m)}<50 and {host:system.swap.size[,total].last()}>0', 2, '', 0, '21001', '2026-04-29 17:18:52.789115', '2026-04-29 17:18:52.789115');
INSERT INTO zabbix_mac.triggers VALUES (6, '{HOST.NAME}_{HOST.IP} Getting closer to process limit (over 80% used)', '{host:proc.num.last()}/{host:kernel.maxproc.last()}*100>80', 1, '', 0, '21001', '2026-04-29 17:16:12.280037', '2026-04-29 17:16:12.280037');
INSERT INTO zabbix_mac.triggers VALUES (5, '{HOST.NAME}_{HOST.IP} /etc/passwd has been changed', '{host:vfs.file.cksum[/etc/passwd].diff()}>0', 1, '', 0, '21001', '2026-04-29 17:14:24.26742', '2026-04-29 17:14:24.26742');
INSERT INTO zabbix_mac.triggers VALUES (12, '{HOST.NAME}_{HOST.IP}Zabbix agent is not available (for 3m)', '{host:zabbix[host,agent,available].max(3m)}=0', 3, '', 0, '21001', '2026-04-29 17:33:32.516352', '2026-04-29 17:33:32.516352');
INSERT INTO zabbix_mac.triggers VALUES (3, '{HOST.NAME}_{HOST.IP} Configured max number of processes is too low (< 1024)', '{host:kernel.maxproc.last()}<1024', 1, 'None', 0, '21001', '2026-04-17 09:02:07.059233', '2026-04-17 09:02:07.059233');


--
-- Name: triggers_id_seq; Type: SEQUENCE SET; Schema: zabbix_mac; Owner: -
--

SELECT pg_catalog.setval('zabbix_mac.triggers_id_seq', 20, true);


--
-- PostgreSQL database dump complete
--

\unrestrict W8H2Wh5KkHTNgYJ98aWRcHL4Ni5vevbuJgF6318iwJYVJEKfjQXaJZByd8Onsh1

