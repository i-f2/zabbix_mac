--
-- PostgreSQL database dump
--

\restrict rtuqkU1td6NggnbeCmNa7ErVlm01EpeezN9UhOzbNcE2BH7ojPVv78bbSuAKL4O

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
-- Data for Name: item_prototypes_review; Type: TABLE DATA; Schema: zabbix_mac; Owner: -
--

INSERT INTO zabbix_mac.item_prototypes_review VALUES (175, 11, 2, '{#FSNAME}: Space utilization', 'vfs.fs.size[{#FSNAME},pused]', 0, '1m', NULL, NULL, 0, 0, 7, 365, 0, false, false, 'pending', '2026-04-30 17:26:59.89368', '2026-04-30 17:26:59.89368', '10.24.3.12', '上市系统', '上市日常监管模块');
INSERT INTO zabbix_mac.item_prototypes_review VALUES (176, 11, 2, '{#FSNAME}: Space utilization', 'vfs.fs.size[{#FSNAME},pused]', 0, '1m', NULL, NULL, 0, 0, 7, 365, 0, false, false, 'pending', '2026-04-30 17:26:59.89368', '2026-04-30 17:26:59.89368', '10.24.3.23', '上市系统', '上市日常监管模块');
INSERT INTO zabbix_mac.item_prototypes_review VALUES (177, 12, 2, '{#FSNAME}: Total space', 'vfs.fs.size[{#FSNAME},total]', 3, '1m', NULL, NULL, 0, 0, 7, 365, 0, false, false, 'pending', '2026-04-30 17:26:59.89368', '2026-04-30 17:26:59.89368', 'Zabbix server', '上市系统', '上市日常监管模块');
INSERT INTO zabbix_mac.item_prototypes_review VALUES (178, 12, 2, '{#FSNAME}: Total space', 'vfs.fs.size[{#FSNAME},total]', 3, '1m', NULL, NULL, 0, 0, 7, 365, 0, false, false, 'pending', '2026-04-30 17:26:59.89368', '2026-04-30 17:26:59.89368', '10.24.3.12', '上市系统', '上市日常监管模块');
INSERT INTO zabbix_mac.item_prototypes_review VALUES (179, 12, 2, '{#FSNAME}: Total space', 'vfs.fs.size[{#FSNAME},total]', 3, '1m', NULL, NULL, 0, 0, 7, 365, 0, false, false, 'pending', '2026-04-30 17:26:59.89368', '2026-04-30 17:26:59.89368', '10.24.3.23', '上市系统', '上市日常监管模块');
INSERT INTO zabbix_mac.item_prototypes_review VALUES (180, 13, 2, '{#FSNAME}: Used space', 'vfs.fs.size[{#FSNAME},used]', 3, '1m', NULL, NULL, 0, 0, 7, 365, 0, false, false, 'pending', '2026-04-30 17:26:59.89368', '2026-04-30 17:26:59.89368', 'Zabbix server', '上市系统', '上市日常监管模块');
INSERT INTO zabbix_mac.item_prototypes_review VALUES (181, 13, 2, '{#FSNAME}: Used space', 'vfs.fs.size[{#FSNAME},used]', 3, '1m', NULL, NULL, 0, 0, 7, 365, 0, false, false, 'pending', '2026-04-30 17:26:59.89368', '2026-04-30 17:26:59.89368', '10.24.3.12', '上市系统', '上市日常监管模块');
INSERT INTO zabbix_mac.item_prototypes_review VALUES (182, 13, 2, '{#FSNAME}: Used space', 'vfs.fs.size[{#FSNAME},used]', 3, '1m', NULL, NULL, 0, 0, 7, 365, 0, false, false, 'pending', '2026-04-30 17:26:59.89368', '2026-04-30 17:26:59.89368', '10.24.3.23', '上市系统', '上市日常监管模块');
INSERT INTO zabbix_mac.item_prototypes_review VALUES (144, 1, 1, '{#DEVNAME}: Disk average queue size (avgqu-sz)', 'vfs.dev.queue_size[{#DEVNAME}]', 0, '0', NULL, NULL, 0, 0, 7, 365, 0, false, false, 'pending', '2026-04-30 17:26:59.89368', '2026-04-30 17:26:59.89368', 'Zabbix server', '上市系统', '上市日常监管模块');
INSERT INTO zabbix_mac.item_prototypes_review VALUES (145, 1, 1, '{#DEVNAME}: Disk average queue size (avgqu-sz)', 'vfs.dev.queue_size[{#DEVNAME}]', 0, '0', NULL, NULL, 0, 0, 7, 365, 0, false, false, 'pending', '2026-04-30 17:26:59.89368', '2026-04-30 17:26:59.89368', '10.24.3.12', '上市系统', '上市日常监管模块');
INSERT INTO zabbix_mac.item_prototypes_review VALUES (146, 1, 1, '{#DEVNAME}: Disk average queue size (avgqu-sz)', 'vfs.dev.queue_size[{#DEVNAME}]', 0, '0', NULL, NULL, 0, 0, 7, 365, 0, false, false, 'pending', '2026-04-30 17:26:59.89368', '2026-04-30 17:26:59.89368', '10.24.3.23', '上市系统', '上市日常监管模块');
INSERT INTO zabbix_mac.item_prototypes_review VALUES (147, 2, 1, '{#DEVNAME}: Disk read request avg waiting time (r_await)', 'vfs.dev.read.await[{#DEVNAME}]', 0, '1m', NULL, NULL, 0, 0, 7, 365, 0, false, false, 'pending', '2026-04-30 17:26:59.89368', '2026-04-30 17:26:59.89368', 'Zabbix server', '上市系统', '上市日常监管模块');
INSERT INTO zabbix_mac.item_prototypes_review VALUES (148, 2, 1, '{#DEVNAME}: Disk read request avg waiting time (r_await)', 'vfs.dev.read.await[{#DEVNAME}]', 0, '1m', NULL, NULL, 0, 0, 7, 365, 0, false, false, 'pending', '2026-04-30 17:26:59.89368', '2026-04-30 17:26:59.89368', '10.24.3.12', '上市系统', '上市日常监管模块');
INSERT INTO zabbix_mac.item_prototypes_review VALUES (149, 2, 1, '{#DEVNAME}: Disk read request avg waiting time (r_await)', 'vfs.dev.read.await[{#DEVNAME}]', 0, '1m', NULL, NULL, 0, 0, 7, 365, 0, false, false, 'pending', '2026-04-30 17:26:59.89368', '2026-04-30 17:26:59.89368', '10.24.3.23', '上市系统', '上市日常监管模块');
INSERT INTO zabbix_mac.item_prototypes_review VALUES (150, 3, 1, '{#DEVNAME}: Disk read rate', 'vfs.dev.read.rate[{#DEVNAME}]', 0, '0', NULL, NULL, 0, 0, 7, 365, 0, false, false, 'pending', '2026-04-30 17:26:59.89368', '2026-04-30 17:26:59.89368', 'Zabbix server', '上市系统', '上市日常监管模块');
INSERT INTO zabbix_mac.item_prototypes_review VALUES (151, 3, 1, '{#DEVNAME}: Disk read rate', 'vfs.dev.read.rate[{#DEVNAME}]', 0, '0', NULL, NULL, 0, 0, 7, 365, 0, false, false, 'pending', '2026-04-30 17:26:59.89368', '2026-04-30 17:26:59.89368', '10.24.3.12', '上市系统', '上市日常监管模块');
INSERT INTO zabbix_mac.item_prototypes_review VALUES (152, 3, 1, '{#DEVNAME}: Disk read rate', 'vfs.dev.read.rate[{#DEVNAME}]', 0, '0', NULL, NULL, 0, 0, 7, 365, 0, false, false, 'pending', '2026-04-30 17:26:59.89368', '2026-04-30 17:26:59.89368', '10.24.3.23', '上市系统', '上市日常监管模块');
INSERT INTO zabbix_mac.item_prototypes_review VALUES (153, 4, 1, '{#DEVNAME}: Disk read time (rate)', 'vfs.dev.read.time.rate[{#DEVNAME}]', 0, '0', NULL, NULL, 0, 0, 7, 365, 0, false, false, 'pending', '2026-04-30 17:26:59.89368', '2026-04-30 17:26:59.89368', 'Zabbix server', '上市系统', '上市日常监管模块');
INSERT INTO zabbix_mac.item_prototypes_review VALUES (154, 4, 1, '{#DEVNAME}: Disk read time (rate)', 'vfs.dev.read.time.rate[{#DEVNAME}]', 0, '0', NULL, NULL, 0, 0, 7, 365, 0, false, false, 'pending', '2026-04-30 17:26:59.89368', '2026-04-30 17:26:59.89368', '10.24.3.12', '上市系统', '上市日常监管模块');
INSERT INTO zabbix_mac.item_prototypes_review VALUES (155, 4, 1, '{#DEVNAME}: Disk read time (rate)', 'vfs.dev.read.time.rate[{#DEVNAME}]', 0, '0', NULL, NULL, 0, 0, 7, 365, 0, false, false, 'pending', '2026-04-30 17:26:59.89368', '2026-04-30 17:26:59.89368', '10.24.3.23', '上市系统', '上市日常监管模块');
INSERT INTO zabbix_mac.item_prototypes_review VALUES (156, 5, 1, '{#DEVNAME}: Disk utilization', 'vfs.dev.util[{#DEVNAME}]', 0, '0', NULL, NULL, 0, 0, 7, 365, 0, false, false, 'pending', '2026-04-30 17:26:59.89368', '2026-04-30 17:26:59.89368', 'Zabbix server', '上市系统', '上市日常监管模块');
INSERT INTO zabbix_mac.item_prototypes_review VALUES (157, 5, 1, '{#DEVNAME}: Disk utilization', 'vfs.dev.util[{#DEVNAME}]', 0, '0', NULL, NULL, 0, 0, 7, 365, 0, false, false, 'pending', '2026-04-30 17:26:59.89368', '2026-04-30 17:26:59.89368', '10.24.3.12', '上市系统', '上市日常监管模块');
INSERT INTO zabbix_mac.item_prototypes_review VALUES (158, 5, 1, '{#DEVNAME}: Disk utilization', 'vfs.dev.util[{#DEVNAME}]', 0, '0', NULL, NULL, 0, 0, 7, 365, 0, false, false, 'pending', '2026-04-30 17:26:59.89368', '2026-04-30 17:26:59.89368', '10.24.3.23', '上市系统', '上市日常监管模块');
INSERT INTO zabbix_mac.item_prototypes_review VALUES (159, 6, 1, '{#DEVNAME}: Disk write request avg waiting time (w_await)', 'vfs.dev.write.await[{#DEVNAME}]', 0, '1m', NULL, NULL, 0, 0, 7, 365, 0, false, false, 'pending', '2026-04-30 17:26:59.89368', '2026-04-30 17:26:59.89368', 'Zabbix server', '上市系统', '上市日常监管模块');
INSERT INTO zabbix_mac.item_prototypes_review VALUES (160, 6, 1, '{#DEVNAME}: Disk write request avg waiting time (w_await)', 'vfs.dev.write.await[{#DEVNAME}]', 0, '1m', NULL, NULL, 0, 0, 7, 365, 0, false, false, 'pending', '2026-04-30 17:26:59.89368', '2026-04-30 17:26:59.89368', '10.24.3.12', '上市系统', '上市日常监管模块');
INSERT INTO zabbix_mac.item_prototypes_review VALUES (161, 6, 1, '{#DEVNAME}: Disk write request avg waiting time (w_await)', 'vfs.dev.write.await[{#DEVNAME}]', 0, '1m', NULL, NULL, 0, 0, 7, 365, 0, false, false, 'pending', '2026-04-30 17:26:59.89368', '2026-04-30 17:26:59.89368', '10.24.3.23', '上市系统', '上市日常监管模块');
INSERT INTO zabbix_mac.item_prototypes_review VALUES (162, 7, 1, '{#DEVNAME}: Disk write rate', 'vfs.dev.write.rate[{#DEVNAME}]', 0, '0', NULL, NULL, 0, 0, 7, 365, 0, false, false, 'pending', '2026-04-30 17:26:59.89368', '2026-04-30 17:26:59.89368', 'Zabbix server', '上市系统', '上市日常监管模块');
INSERT INTO zabbix_mac.item_prototypes_review VALUES (163, 7, 1, '{#DEVNAME}: Disk write rate', 'vfs.dev.write.rate[{#DEVNAME}]', 0, '0', NULL, NULL, 0, 0, 7, 365, 0, false, false, 'pending', '2026-04-30 17:26:59.89368', '2026-04-30 17:26:59.89368', '10.24.3.12', '上市系统', '上市日常监管模块');
INSERT INTO zabbix_mac.item_prototypes_review VALUES (164, 7, 1, '{#DEVNAME}: Disk write rate', 'vfs.dev.write.rate[{#DEVNAME}]', 0, '0', NULL, NULL, 0, 0, 7, 365, 0, false, false, 'pending', '2026-04-30 17:26:59.89368', '2026-04-30 17:26:59.89368', '10.24.3.23', '上市系统', '上市日常监管模块');
INSERT INTO zabbix_mac.item_prototypes_review VALUES (165, 8, 1, '{#DEVNAME}: Disk write time (rate)', 'vfs.dev.write.time.rate[{#DEVNAME}]', 0, '0', NULL, NULL, 0, 0, 7, 365, 0, false, false, 'pending', '2026-04-30 17:26:59.89368', '2026-04-30 17:26:59.89368', 'Zabbix server', '上市系统', '上市日常监管模块');
INSERT INTO zabbix_mac.item_prototypes_review VALUES (166, 8, 1, '{#DEVNAME}: Disk write time (rate)', 'vfs.dev.write.time.rate[{#DEVNAME}]', 0, '0', NULL, NULL, 0, 0, 7, 365, 0, false, false, 'pending', '2026-04-30 17:26:59.89368', '2026-04-30 17:26:59.89368', '10.24.3.12', '上市系统', '上市日常监管模块');
INSERT INTO zabbix_mac.item_prototypes_review VALUES (167, 8, 1, '{#DEVNAME}: Disk write time (rate)', 'vfs.dev.write.time.rate[{#DEVNAME}]', 0, '0', NULL, NULL, 0, 0, 7, 365, 0, false, false, 'pending', '2026-04-30 17:26:59.89368', '2026-04-30 17:26:59.89368', '10.24.3.23', '上市系统', '上市日常监管模块');
INSERT INTO zabbix_mac.item_prototypes_review VALUES (168, 9, 1, '{#DEVNAME}: Get stats', 'vfs.file.contents[/sys/block/{#DEVNAME}/stat]', 4, '1m', NULL, NULL, 0, 0, 7, 365, 0, false, false, 'pending', '2026-04-30 17:26:59.89368', '2026-04-30 17:26:59.89368', 'Zabbix server', '上市系统', '上市日常监管模块');
INSERT INTO zabbix_mac.item_prototypes_review VALUES (169, 9, 1, '{#DEVNAME}: Get stats', 'vfs.file.contents[/sys/block/{#DEVNAME}/stat]', 4, '1m', NULL, NULL, 0, 0, 7, 365, 0, false, false, 'pending', '2026-04-30 17:26:59.89368', '2026-04-30 17:26:59.89368', '10.24.3.12', '上市系统', '上市日常监管模块');
INSERT INTO zabbix_mac.item_prototypes_review VALUES (170, 9, 1, '{#DEVNAME}: Get stats', 'vfs.file.contents[/sys/block/{#DEVNAME}/stat]', 4, '1m', NULL, NULL, 0, 0, 7, 365, 0, false, false, 'pending', '2026-04-30 17:26:59.89368', '2026-04-30 17:26:59.89368', '10.24.3.23', '上市系统', '上市日常监管模块');
INSERT INTO zabbix_mac.item_prototypes_review VALUES (171, 10, 2, '{#FSNAME}: Free inodes in %', 'vfs.fs.inode[{#FSNAME},pfree]', 0, '1m', NULL, NULL, 0, 0, 7, 365, 0, false, false, 'pending', '2026-04-30 17:26:59.89368', '2026-04-30 17:26:59.89368', 'Zabbix server', '上市系统', '上市日常监管模块');
INSERT INTO zabbix_mac.item_prototypes_review VALUES (172, 10, 2, '{#FSNAME}: Free inodes in %', 'vfs.fs.inode[{#FSNAME},pfree]', 0, '1m', NULL, NULL, 0, 0, 7, 365, 0, false, false, 'pending', '2026-04-30 17:26:59.89368', '2026-04-30 17:26:59.89368', '10.24.3.12', '上市系统', '上市日常监管模块');
INSERT INTO zabbix_mac.item_prototypes_review VALUES (173, 10, 2, '{#FSNAME}: Free inodes in %', 'vfs.fs.inode[{#FSNAME},pfree]', 0, '1m', NULL, NULL, 0, 0, 7, 365, 0, false, false, 'pending', '2026-04-30 17:26:59.89368', '2026-04-30 17:26:59.89368', '10.24.3.23', '上市系统', '上市日常监管模块');
INSERT INTO zabbix_mac.item_prototypes_review VALUES (174, 11, 2, '{#FSNAME}: Space utilization', 'vfs.fs.size[{#FSNAME},pused]', 0, '1m', NULL, NULL, 0, 0, 7, 365, 0, false, false, 'pending', '2026-04-30 17:26:59.89368', '2026-04-30 17:26:59.89368', 'Zabbix server', '上市系统', '上市日常监管模块');


--
-- Name: item_prototypes_review_id_seq; Type: SEQUENCE SET; Schema: zabbix_mac; Owner: -
--

SELECT pg_catalog.setval('zabbix_mac.item_prototypes_review_id_seq', 182, true);


--
-- PostgreSQL database dump complete
--

\unrestrict rtuqkU1td6NggnbeCmNa7ErVlm01EpeezN9UhOzbNcE2BH7ojPVv78bbSuAKL4O

