--
-- PostgreSQL database dump
--

\restrict a8dufQGxzuzP3v2NIeeB1Fozp8kdzHAIwmXqG1w8z90BQcVreYftPYR2fe1UODT

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
-- Data for Name: trigger_prototypes_review; Type: TABLE DATA; Schema: zabbix_mac; Owner: -
--

INSERT INTO zabbix_mac.trigger_prototypes_review VALUES (56, 1, 1, '{#DEVNAME}: Disk read/write request responses are too high (read > 20 ms for 15m or write > 20 ms for 15m)', '{host:vfs.dev.read.await[{#DEVNAME}].min(15m)} > 20 or {host:vfs.dev.write.await[{#DEVNAME}].min(15m)} > 20', 3, 0, false, false, 'pending', '2026-04-30 17:26:59.904407', '2026-04-30 17:26:59.904407', 'Zabbix server', '上市系统', '上市日常监管模块');
INSERT INTO zabbix_mac.trigger_prototypes_review VALUES (57, 2, 2, '{#FSNAME}: Running out of free inodes (free < 10%)', '{host:vfs.fs.inode[{#FSNAME},pfree].min(5m)}<10', 3, 0, false, false, 'pending', '2026-04-30 17:26:59.904407', '2026-04-30 17:26:59.904407', 'Zabbix server', '上市系统', '上市日常监管模块');
INSERT INTO zabbix_mac.trigger_prototypes_review VALUES (58, 3, 2, '{#FSNAME}: Running out of free inodes (free < 20%)', '{host:vfs.fs.inode[{#FSNAME},pfree].min(5m)}<20', 2, 0, false, false, 'pending', '2026-04-30 17:26:59.904407', '2026-04-30 17:26:59.904407', 'Zabbix server', '上市系统', '上市日常监管模块');
INSERT INTO zabbix_mac.trigger_prototypes_review VALUES (59, 4, 2, '{#FSNAME}: Disk space is critically low (used > 90%)', '{host:vfs.fs.size[{#FSNAME},pused].last()}>90 and (({host:vfs.fs.size[{#FSNAME},total].last()}-{host:vfs.fs.size[{#FSNAME},used].last()})<5G or {host:vfs.fs.size[{#FSNAME},pused].timeleft(1h,,100)}<1d)', 3, 0, false, false, 'pending', '2026-04-30 17:26:59.904407', '2026-04-30 17:26:59.904407', 'Zabbix server', '上市系统', '上市日常监管模块');
INSERT INTO zabbix_mac.trigger_prototypes_review VALUES (60, 5, 2, '{#FSNAME}: Disk space is low (used > 80%)', '{host:vfs.fs.size[{#FSNAME},pused].last()}>80 and (({host:vfs.fs.size[{#FSNAME},total].last()}-{host:vfs.fs.size[{#FSNAME},used].last()})<10G or {host:vfs.fs.size[{#FSNAME},pused].timeleft(1h,,100)}<1d)', 2, 0, false, false, 'pending', '2026-04-30 17:26:59.904407', '2026-04-30 17:26:59.904407', 'Zabbix server', '上市系统', '上市日常监管模块');
INSERT INTO zabbix_mac.trigger_prototypes_review VALUES (61, 1, 1, '{#DEVNAME}: Disk read/write request responses are too high (read > 20 ms for 15m or write > 20 ms for 15m)', '{host:vfs.dev.read.await[{#DEVNAME}].min(15m)} > 20 or {host:vfs.dev.write.await[{#DEVNAME}].min(15m)} > 20', 3, 0, false, false, 'pending', '2026-04-30 17:26:59.904407', '2026-04-30 17:26:59.904407', '10.24.3.12', '上市系统', '上市日常监管模块');
INSERT INTO zabbix_mac.trigger_prototypes_review VALUES (62, 2, 2, '{#FSNAME}: Running out of free inodes (free < 10%)', '{host:vfs.fs.inode[{#FSNAME},pfree].min(5m)}<10', 3, 0, false, false, 'pending', '2026-04-30 17:26:59.904407', '2026-04-30 17:26:59.904407', '10.24.3.12', '上市系统', '上市日常监管模块');
INSERT INTO zabbix_mac.trigger_prototypes_review VALUES (63, 3, 2, '{#FSNAME}: Running out of free inodes (free < 20%)', '{host:vfs.fs.inode[{#FSNAME},pfree].min(5m)}<20', 2, 0, false, false, 'pending', '2026-04-30 17:26:59.904407', '2026-04-30 17:26:59.904407', '10.24.3.12', '上市系统', '上市日常监管模块');
INSERT INTO zabbix_mac.trigger_prototypes_review VALUES (64, 4, 2, '{#FSNAME}: Disk space is critically low (used > 90%)', '{host:vfs.fs.size[{#FSNAME},pused].last()}>90 and (({host:vfs.fs.size[{#FSNAME},total].last()}-{host:vfs.fs.size[{#FSNAME},used].last()})<5G or {host:vfs.fs.size[{#FSNAME},pused].timeleft(1h,,100)}<1d)', 3, 0, false, false, 'pending', '2026-04-30 17:26:59.904407', '2026-04-30 17:26:59.904407', '10.24.3.12', '上市系统', '上市日常监管模块');
INSERT INTO zabbix_mac.trigger_prototypes_review VALUES (65, 5, 2, '{#FSNAME}: Disk space is low (used > 80%)', '{host:vfs.fs.size[{#FSNAME},pused].last()}>80 and (({host:vfs.fs.size[{#FSNAME},total].last()}-{host:vfs.fs.size[{#FSNAME},used].last()})<10G or {host:vfs.fs.size[{#FSNAME},pused].timeleft(1h,,100)}<1d)', 2, 0, false, false, 'pending', '2026-04-30 17:26:59.904407', '2026-04-30 17:26:59.904407', '10.24.3.12', '上市系统', '上市日常监管模块');
INSERT INTO zabbix_mac.trigger_prototypes_review VALUES (66, 1, 1, '{#DEVNAME}: Disk read/write request responses are too high (read > 20 ms for 15m or write > 20 ms for 15m)', '{host:vfs.dev.read.await[{#DEVNAME}].min(15m)} > 20 or {host:vfs.dev.write.await[{#DEVNAME}].min(15m)} > 20', 3, 0, false, false, 'pending', '2026-04-30 17:26:59.904407', '2026-04-30 17:26:59.904407', '10.24.3.23', '上市系统', '上市日常监管模块');
INSERT INTO zabbix_mac.trigger_prototypes_review VALUES (67, 2, 2, '{#FSNAME}: Running out of free inodes (free < 10%)', '{host:vfs.fs.inode[{#FSNAME},pfree].min(5m)}<10', 3, 0, false, false, 'pending', '2026-04-30 17:26:59.904407', '2026-04-30 17:26:59.904407', '10.24.3.23', '上市系统', '上市日常监管模块');
INSERT INTO zabbix_mac.trigger_prototypes_review VALUES (68, 3, 2, '{#FSNAME}: Running out of free inodes (free < 20%)', '{host:vfs.fs.inode[{#FSNAME},pfree].min(5m)}<20', 2, 0, false, false, 'pending', '2026-04-30 17:26:59.904407', '2026-04-30 17:26:59.904407', '10.24.3.23', '上市系统', '上市日常监管模块');
INSERT INTO zabbix_mac.trigger_prototypes_review VALUES (69, 4, 2, '{#FSNAME}: Disk space is critically low (used > 90%)', '{host:vfs.fs.size[{#FSNAME},pused].last()}>90 and (({host:vfs.fs.size[{#FSNAME},total].last()}-{host:vfs.fs.size[{#FSNAME},used].last()})<5G or {host:vfs.fs.size[{#FSNAME},pused].timeleft(1h,,100)}<1d)', 3, 0, false, false, 'pending', '2026-04-30 17:26:59.904407', '2026-04-30 17:26:59.904407', '10.24.3.23', '上市系统', '上市日常监管模块');
INSERT INTO zabbix_mac.trigger_prototypes_review VALUES (70, 5, 2, '{#FSNAME}: Disk space is low (used > 80%)', '{host:vfs.fs.size[{#FSNAME},pused].last()}>80 and (({host:vfs.fs.size[{#FSNAME},total].last()}-{host:vfs.fs.size[{#FSNAME},used].last()})<10G or {host:vfs.fs.size[{#FSNAME},pused].timeleft(1h,,100)}<1d)', 2, 0, false, false, 'pending', '2026-04-30 17:26:59.904407', '2026-04-30 17:26:59.904407', '10.24.3.23', '上市系统', '上市日常监管模块');


--
-- Name: trigger_prototypes_review_id_seq; Type: SEQUENCE SET; Schema: zabbix_mac; Owner: -
--

SELECT pg_catalog.setval('zabbix_mac.trigger_prototypes_review_id_seq', 70, true);


--
-- PostgreSQL database dump complete
--

\unrestrict a8dufQGxzuzP3v2NIeeB1Fozp8kdzHAIwmXqG1w8z90BQcVreYftPYR2fe1UODT

