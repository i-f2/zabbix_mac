--
-- PostgreSQL database dump
--

\restrict 7g0hurljSG1ICBDf2pd6VeZ3kUKFECl6uv0LlTXRyo834Qy96YdxytRqKMw33Qh

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
-- Data for Name: filter_conditions; Type: TABLE DATA; Schema: zabbix_mac; Owner: -
--

INSERT INTO zabbix_mac.filter_conditions VALUES (1, 1, '{#DEVTYPE}', 'disk', 'MATCHES_REGEX', '2026-04-17 09:02:07.059233');
INSERT INTO zabbix_mac.filter_conditions VALUES (2, 1, '{#DEVNAME}', '.+', 'MATCHES_REGEX', '2026-04-17 09:02:07.059233');
INSERT INTO zabbix_mac.filter_conditions VALUES (3, 1, '{#DEVNAME}', '^(loop[0-9]*|sd[a-z][0-9]+|nbd[0-9]+|sr[0-9]+|fd[0-9]+|dm-[0-9]+|ram[0-9]+|ploop[a-z0-9]+|md[0-9]*|hcp[0-9]*|zram[0-9]*)$', 'NOT_MATCHES_REGEX', '2026-04-17 09:02:07.059233');
INSERT INTO zabbix_mac.filter_conditions VALUES (4, 2, '{#FSTYPE}', '^(btrfs|ext2|ext3|ext4|reiser|xfs|ffs|ufs|jfs|jfs2|vxfs|hfs|apfs|refs|ntfs|fat32|zfs)$', 'MATCHES_REGEX', '2026-04-17 09:02:07.059233');
INSERT INTO zabbix_mac.filter_conditions VALUES (5, 2, '{#FSTYPE}', '^\s$', 'NOT_MATCHES_REGEX', '2026-04-17 09:02:07.059233');
INSERT INTO zabbix_mac.filter_conditions VALUES (6, 2, '{#FSNAME}', '.+', 'MATCHES_REGEX', '2026-04-17 09:02:07.059233');
INSERT INTO zabbix_mac.filter_conditions VALUES (7, 2, '{#FSNAME}', '^(/dev|/sys|/run|/proc|.+/shm$)', 'NOT_MATCHES_REGEX', '2026-04-17 09:02:07.059233');


--
-- Name: filter_conditions_id_seq; Type: SEQUENCE SET; Schema: zabbix_mac; Owner: -
--

SELECT pg_catalog.setval('zabbix_mac.filter_conditions_id_seq', 7, true);


--
-- PostgreSQL database dump complete
--

\unrestrict 7g0hurljSG1ICBDf2pd6VeZ3kUKFECl6uv0LlTXRyo834Qy96YdxytRqKMw33Qh

