--
-- PostgreSQL database dump
--

\restrict Xs85Qgte9g0wAPAJPBiOeXzaAmZeChaiyMBhw65VLTvbEzmQEXLiOU1e8eNGMg4

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
-- Data for Name: item_prototypes; Type: TABLE DATA; Schema: zabbix_mac; Owner: -
--

INSERT INTO zabbix_mac.item_prototypes VALUES (1, 1, '{#DEVNAME}: Disk average queue size (avgqu-sz)', 'vfs.dev.queue_size[{#DEVNAME}]', 0, '0', NULL, NULL, 0, 0, 7, 365, 0, '2026-04-17 09:02:07.059233', '2026-04-17 09:02:07.059233');
INSERT INTO zabbix_mac.item_prototypes VALUES (2, 1, '{#DEVNAME}: Disk read request avg waiting time (r_await)', 'vfs.dev.read.await[{#DEVNAME}]', 0, '1m', NULL, NULL, 0, 0, 7, 365, 0, '2026-04-17 09:02:07.059233', '2026-04-17 09:02:07.059233');
INSERT INTO zabbix_mac.item_prototypes VALUES (3, 1, '{#DEVNAME}: Disk read rate', 'vfs.dev.read.rate[{#DEVNAME}]', 0, '0', NULL, NULL, 0, 0, 7, 365, 0, '2026-04-17 09:02:07.059233', '2026-04-17 09:02:07.059233');
INSERT INTO zabbix_mac.item_prototypes VALUES (4, 1, '{#DEVNAME}: Disk read time (rate)', 'vfs.dev.read.time.rate[{#DEVNAME}]', 0, '0', NULL, NULL, 0, 0, 7, 365, 0, '2026-04-17 09:02:07.059233', '2026-04-17 09:02:07.059233');
INSERT INTO zabbix_mac.item_prototypes VALUES (5, 1, '{#DEVNAME}: Disk utilization', 'vfs.dev.util[{#DEVNAME}]', 0, '0', NULL, NULL, 0, 0, 7, 365, 0, '2026-04-17 09:02:07.059233', '2026-04-17 09:02:07.059233');
INSERT INTO zabbix_mac.item_prototypes VALUES (6, 1, '{#DEVNAME}: Disk write request avg waiting time (w_await)', 'vfs.dev.write.await[{#DEVNAME}]', 0, '1m', NULL, NULL, 0, 0, 7, 365, 0, '2026-04-17 09:02:07.059233', '2026-04-17 09:02:07.059233');
INSERT INTO zabbix_mac.item_prototypes VALUES (7, 1, '{#DEVNAME}: Disk write rate', 'vfs.dev.write.rate[{#DEVNAME}]', 0, '0', NULL, NULL, 0, 0, 7, 365, 0, '2026-04-17 09:02:07.059233', '2026-04-17 09:02:07.059233');
INSERT INTO zabbix_mac.item_prototypes VALUES (8, 1, '{#DEVNAME}: Disk write time (rate)', 'vfs.dev.write.time.rate[{#DEVNAME}]', 0, '0', NULL, NULL, 0, 0, 7, 365, 0, '2026-04-17 09:02:07.059233', '2026-04-17 09:02:07.059233');
INSERT INTO zabbix_mac.item_prototypes VALUES (9, 1, '{#DEVNAME}: Get stats', 'vfs.file.contents[/sys/block/{#DEVNAME}/stat]', 4, '1m', NULL, NULL, 0, 0, 7, 365, 0, '2026-04-17 09:02:07.059233', '2026-04-17 09:02:07.059233');
INSERT INTO zabbix_mac.item_prototypes VALUES (10, 2, '{#FSNAME}: Free inodes in %', 'vfs.fs.inode[{#FSNAME},pfree]', 0, '1m', NULL, NULL, 0, 0, 7, 365, 0, '2026-04-17 09:02:07.059233', '2026-04-17 09:02:07.059233');
INSERT INTO zabbix_mac.item_prototypes VALUES (11, 2, '{#FSNAME}: Space utilization', 'vfs.fs.size[{#FSNAME},pused]', 0, '1m', NULL, NULL, 0, 0, 7, 365, 0, '2026-04-17 09:02:07.059233', '2026-04-17 09:02:07.059233');
INSERT INTO zabbix_mac.item_prototypes VALUES (12, 2, '{#FSNAME}: Total space', 'vfs.fs.size[{#FSNAME},total]', 3, '1m', NULL, NULL, 0, 0, 7, 365, 0, '2026-04-17 09:02:07.059233', '2026-04-17 09:02:07.059233');
INSERT INTO zabbix_mac.item_prototypes VALUES (13, 2, '{#FSNAME}: Used space', 'vfs.fs.size[{#FSNAME},used]', 3, '1m', NULL, NULL, 0, 0, 7, 365, 0, '2026-04-17 09:02:07.059233', '2026-04-17 09:02:07.059233');


--
-- Name: item_prototypes_id_seq; Type: SEQUENCE SET; Schema: zabbix_mac; Owner: -
--

SELECT pg_catalog.setval('zabbix_mac.item_prototypes_id_seq', 13, true);


--
-- PostgreSQL database dump complete
--

\unrestrict Xs85Qgte9g0wAPAJPBiOeXzaAmZeChaiyMBhw65VLTvbEzmQEXLiOU1e8eNGMg4

