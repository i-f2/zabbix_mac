--
-- PostgreSQL database dump
--

\restrict 0iA7gkkFT0ffX59b9pl0EafWAOWQlFjtbAxl4zj5ycjxAf3m4SA3fS3EoxpyF6x

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
-- Data for Name: items; Type: TABLE DATA; Schema: zabbix_mac; Owner: -
--

INSERT INTO zabbix_mac.items VALUES (22, 'system.swap.size[,free]', 'Free swap space', 0, 3, '1m', '', 'B', 0, 0, 7, 365, 0, '21001', '2026-04-29 16:17:34.133078', '2026-04-29 16:17:34.133078', NULL, NULL);
INSERT INTO zabbix_mac.items VALUES (24, 'system.swap.size[,total]', 'Total swap space', 0, 3, '1m', '', 'B', 0, 0, 7, 365, 0, '21001', '2026-04-29 16:20:27.054296', '2026-04-29 16:20:27.054296', NULL, NULL);
INSERT INTO zabbix_mac.items VALUES (26, 'vm.memory.size[pavailable]', 'Available memory in %', 0, 0, '1m', '', '%', 0, 0, 7, 365, 0, '21001', '2026-04-29 16:22:09.324243', '2026-04-29 16:22:09.324243', NULL, NULL);
INSERT INTO zabbix_mac.items VALUES (37, 'system.sw.os', 'Operating system', 0, 1, '1h', '', '', 0, 0, 7, 365, 0, '21001', '2026-04-29 16:43:08.050444', '2026-04-29 16:43:08.050444', NULL, NULL);
INSERT INTO zabbix_mac.items VALUES (39, 'system.uname', 'System description', 0, 1, '15m', '', '', 0, 0, 12, 365, 0, '21001', '2026-04-29 16:45:15.423314', '2026-04-29 16:45:15.423314', NULL, NULL);
INSERT INTO zabbix_mac.items VALUES (41, 'system.users.num', 'Number of logged in users', 0, 3, '1m', '', '', 0, 0, 7, 365, 0, '21001', '2026-04-29 16:47:35.838108', '2026-04-29 16:47:35.838108', NULL, NULL);
INSERT INTO zabbix_mac.items VALUES (28, 'vm.memory.utilization', 'Memory utilization', 18, 0, '1m', '', '%', 0, 0, 7, 365, 0, '21001', '2026-04-29 16:24:59.421969', '2026-04-29 16:24:59.421969', 'vm.memory.size[pavailable]', '[{"type": "21", "params": "return (100-value);", "error_handler": "0", "error_handler_params": ""}]');
INSERT INTO zabbix_mac.items VALUES (7, 'system.cpu.load[all,avg15]', 'Load average (15m avg)', 0, 0, '1m', NULL, NULL, 0, 0, 7, 365, 0, '21001', '2026-04-17 09:02:07.059233', '2026-04-17 09:02:07.059233', NULL, NULL);
INSERT INTO zabbix_mac.items VALUES (8, 'system.cpu.load[all,avg5]', 'Load average (5m avg)', 0, 0, '1m', NULL, NULL, 0, 0, 7, 365, 0, '21001', '2026-04-17 09:02:07.059233', '2026-04-17 09:02:07.059233', NULL, NULL);
INSERT INTO zabbix_mac.items VALUES (1, 'agent.hostname', 'Host name of Zabbix agent running', 0, 1, '1h', '', '', 0, 0, 7, 365, 0, '21001', '2026-04-29 15:09:39.062209', '2026-04-29 15:09:39.062209', NULL, NULL);
INSERT INTO zabbix_mac.items VALUES (2, 'agent.ping', 'Zabbix agent ping', 0, 0, '1m', '', '', 0, 0, 7, 365, 0, '21001', '2026-04-29 15:11:22.281085', '2026-04-29 15:11:22.281085', NULL, NULL);
INSERT INTO zabbix_mac.items VALUES (23, 'system.swap.size[,pfree]', 'Free swap space in %', 0, 0, '1m', '', '%', 0, 0, 7, 365, 0, '21001', '2026-04-29 16:18:16.05008', '2026-04-29 16:18:16.05008', NULL, NULL);
INSERT INTO zabbix_mac.items VALUES (25, 'vm.memory.size[available]', 'Available memory', 0, 3, '1m', '', 'B', 0, 0, 7, 365, 0, '21001', '2026-04-29 16:21:27.423412', '2026-04-29 16:21:27.423412', NULL, NULL);
INSERT INTO zabbix_mac.items VALUES (3, 'agent.version', 'Version of Zabbix agent running', 0, 1, '1h', '', '', 0, 0, 7, 365, 0, '21001', '2026-04-29 15:22:08.687299', '2026-04-29 15:22:08.687299', NULL, NULL);
INSERT INTO zabbix_mac.items VALUES (27, 'vm.memory.size[total]', 'Total memory', 0, 3, '1m', '', 'B', 0, 0, 7, 365, 0, '21001', '2026-04-29 16:23:11.433385', '2026-04-29 16:23:11.433385', NULL, NULL);
INSERT INTO zabbix_mac.items VALUES (4, 'zabbix[host,agent,available]', 'Zabbix agent availability', 5, 0, '1m', '', '', 0, 0, 7, 365, 0, '21001', '2026-04-29 15:25:23.620969', '2026-04-29 15:25:23.620969', NULL, NULL);
INSERT INTO zabbix_mac.items VALUES (29, 'kernel.maxfiles', 'Maximum number of open file descriptors', 0, 3, '1h', '', '', 0, 0, 7, 365, 0, '21001', '2026-04-17 09:02:07.059233', '2026-04-17 09:02:07.059233', NULL, NULL);
INSERT INTO zabbix_mac.items VALUES (5, 'system.cpu.intr', 'Interrupts per second', 0, 0, '1m', NULL, NULL, 0, 0, 7, 365, 0, '21001', '2026-04-17 09:02:07.059233', '2026-04-17 09:02:07.059233', NULL, NULL);
INSERT INTO zabbix_mac.items VALUES (9, 'system.cpu.num', 'Number of CPUs', 0, 3, '1m', NULL, NULL, 0, 0, 7, 365, 0, '21001', '2026-04-17 09:02:07.059233', '2026-04-17 09:02:07.059233', NULL, NULL);
INSERT INTO zabbix_mac.items VALUES (6, 'system.cpu.load[all,avg1]', 'Load average (1m avg)', 0, 0, '1m', '', '', 0, 0, 7, 365, 0, '21001', '2026-04-17 09:02:07.059233', '2026-04-17 09:02:07.059233', NULL, NULL);
INSERT INTO zabbix_mac.items VALUES (10, 'system.cpu.switches', 'Context switches per second', 0, 0, '1m', NULL, NULL, 0, 0, 7, 365, 0, '21001', '2026-04-17 09:02:07.059233', '2026-04-17 09:02:07.059233', NULL, NULL);
INSERT INTO zabbix_mac.items VALUES (11, 'system.cpu.util[,idle]', 'CPU idle time', 0, 0, '1m', NULL, NULL, 0, 0, 7, 365, 0, '21001', '2026-04-17 09:02:07.059233', '2026-04-17 09:02:07.059233', NULL, NULL);
INSERT INTO zabbix_mac.items VALUES (13, 'system.cpu.util[,guest_nice]', 'CPU guest nice time', 0, 0, '1m', '', '%', 0, 0, 7, 365, 0, '21001', '2026-04-17 09:02:07.059233', '2026-04-17 09:02:07.059233', NULL, NULL);
INSERT INTO zabbix_mac.items VALUES (14, 'system.cpu.util[,guest]', 'CPU guest time', 0, 0, '1m', '', '%', 0, 0, 7, 365, 0, '21001', '2026-04-17 09:02:07.059233', '2026-04-17 09:02:07.059233', NULL, NULL);
INSERT INTO zabbix_mac.items VALUES (15, 'system.cpu.util[,interrupt]', 'CPU interrupt time', 0, 0, '1m', '', '%', 0, 0, 7, 365, 0, '21001', '2026-04-17 09:02:07.059233', '2026-04-17 09:02:07.059233', NULL, NULL);
INSERT INTO zabbix_mac.items VALUES (16, 'system.cpu.util[,iowait]', 'CPU iowait time', 0, 0, '1m', '', '%', 0, 0, 7, 365, 0, '21001', '2026-04-17 09:02:07.059233', '2026-04-17 09:02:07.059233', NULL, NULL);
INSERT INTO zabbix_mac.items VALUES (17, 'system.cpu.util[,nice]', 'CPU nice time', 0, 0, '1m', '', '%', 0, 0, 7, 365, 0, '21001', '2026-04-17 09:02:07.059233', '2026-04-17 09:02:07.059233', NULL, NULL);
INSERT INTO zabbix_mac.items VALUES (18, 'system.cpu.util[,softirq]', 'CPU softirq time', 0, 0, '1m', '', '%', 0, 0, 7, 365, 0, '21001', '2026-04-17 09:02:07.059233', '2026-04-17 09:02:07.059233', NULL, NULL);
INSERT INTO zabbix_mac.items VALUES (19, 'system.cpu.util[,steal]', 'CPU steal time', 0, 0, '1m', '', '%', 0, 0, 7, 365, 0, '21001', '2026-04-17 09:02:07.059233', '2026-04-17 09:02:07.059233', NULL, NULL);
INSERT INTO zabbix_mac.items VALUES (20, 'system.cpu.util[,system]', 'CPU system time', 0, 0, '1m', '', '%', 0, 0, 7, 365, 0, '21001', '2026-04-17 09:02:07.059233', '2026-04-17 09:02:07.059233', NULL, NULL);
INSERT INTO zabbix_mac.items VALUES (21, 'system.cpu.util[,user]', 'CPU user time', 0, 0, '1m', '', '%', 0, 0, 7, 365, 0, '21001', '2026-04-17 09:02:07.059233', '2026-04-17 09:02:07.059233', NULL, NULL);
INSERT INTO zabbix_mac.items VALUES (30, 'kernel.maxproc', 'Maximum number of processes', 0, 3, '1h', '', '', 0, 0, 7, 365, 0, '21001', '2026-04-17 09:02:07.059233', '2026-04-17 09:02:07.059233', NULL, NULL);
INSERT INTO zabbix_mac.items VALUES (31, 'proc.num', 'Number of processes', 0, 3, '1m', '', '', 0, 0, 7, 365, 0, '21001', '2026-04-17 09:02:07.059233', '2026-04-17 09:02:07.059233', NULL, NULL);
INSERT INTO zabbix_mac.items VALUES (32, 'proc.num[,,run]', 'Number of running processes', 0, 3, '1m', '', '', 0, 0, 7, 365, 0, '21001', '2026-04-17 09:02:07.059233', '2026-04-17 09:02:07.059233', NULL, NULL);
INSERT INTO zabbix_mac.items VALUES (33, 'system.boottime', 'System boot time', 0, 3, '15m', '', 'unixtime', 0, 0, 7, 365, 0, '21001', '2026-04-17 09:02:07.059233', '2026-04-17 09:02:07.059233', NULL, NULL);
INSERT INTO zabbix_mac.items VALUES (34, 'system.hostname', 'System name', 0, 1, '1h', '', '', 0, 0, 11, 365, 0, '21001', '2026-04-17 09:02:07.059233', '2026-04-17 09:02:07.059233', NULL, NULL);
INSERT INTO zabbix_mac.items VALUES (35, 'system.localtime', 'System local time', 0, 3, '1m', '', 'unixtime', 0, 0, 7, 365, 0, '21001', '2026-04-17 09:02:07.059233', '2026-04-17 09:02:07.059233', NULL, NULL);
INSERT INTO zabbix_mac.items VALUES (36, 'system.sw.arch', 'Operating system architecture', 0, 1, '1h', '', '', 0, 0, 7, 365, 0, '21001', '2026-04-29 16:36:33.697853', '2026-04-29 16:36:33.697853', NULL, NULL);
INSERT INTO zabbix_mac.items VALUES (38, 'system.sw.packages', 'Software installed', 0, 4, '1h', '', '', 0, 0, 11, 365, 0, '21001', '2026-04-29 16:44:16.320316', '2026-04-29 16:44:16.320316', NULL, NULL);
INSERT INTO zabbix_mac.items VALUES (40, 'system.uptime', 'System uptime', 0, 3, '30s', '', 'uptime', 0, 0, 14, 365, 0, '21001', '2026-04-29 16:46:51.128525', '2026-04-29 16:46:51.128525', NULL, NULL);
INSERT INTO zabbix_mac.items VALUES (42, 'vfs.file.cksum[/etc/passwd]', 'Checksum of /etc/passwd', 0, 1, '15m', '', '', 0, 0, 7, 365, 0, '21001', '2026-04-29 16:48:35.950744', '2026-04-29 16:48:35.950744', NULL, NULL);
INSERT INTO zabbix_mac.items VALUES (12, 'system.cpu.util', 'CPU utilization', 18, 0, '1m', '', '%', 0, 0, 7, 365, 0, '21001', '2026-04-17 09:02:07.059233', '2026-04-17 09:02:07.059233', 'system.cpu.util[,idle]', '[{"type": "21", "params": "return (100 - value)", "error_handler": "0", "error_handler_params": ""}]');
INSERT INTO zabbix_mac.items VALUES (67, 'test.key.from.review', 'Test Item From Review', 2, 3, '30s', 'Test from review page', NULL, 0, 0, 7, 365, 0, '21001', '2026-06-08 18:31:41.956302', '2026-06-08 18:31:41.956302', NULL, NULL);
INSERT INTO zabbix_mac.items VALUES (68, 'test.sys.check', 'Test System Item', 7, 3, '1m', NULL, NULL, 0, 0, 7, 365, 0, '21001', '2026-06-08 19:44:44.824288', '2026-06-08 19:44:44.824288', NULL, NULL);


--
-- Name: items_id_seq; Type: SEQUENCE SET; Schema: zabbix_mac; Owner: -
--

SELECT pg_catalog.setval('zabbix_mac.items_id_seq', 68, true);


--
-- PostgreSQL database dump complete
--

\unrestrict 0iA7gkkFT0ffX59b9pl0EafWAOWQlFjtbAxl4zj5ycjxAf3m4SA3fS3EoxpyF6x

