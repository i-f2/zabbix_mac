--
-- PostgreSQL database dump
--

\restrict ApX2V0s53Lm2sYQYHQGaB8AiQbcaTDgdkhZ9Hhjlv2EKgCccfvx68Vhd5dmGVV6

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
-- Data for Name: hosts; Type: TABLE DATA; Schema: zabbix_mac; Owner: -
--

INSERT INTO zabbix_mac.hosts VALUES (1, 'Zabbix server', 'Local Zabbix server', '2026-04-21 17:07:03.284849', '2026-04-21 17:07:03.284849', '上市系统', '上市日常监管模块', '21001');
INSERT INTO zabbix_mac.hosts VALUES (2, '10.24.3.12', 'Test server 1', '2026-04-21 17:07:03.284849', '2026-04-21 17:07:03.284849', '上市系统', '上市日常监管模块', '21001');
INSERT INTO zabbix_mac.hosts VALUES (3, '10.24.3.23', '', '2026-04-24 15:33:45.646743', '2026-04-24 15:33:45.646743', '上市系统', '上市日常监管模块', '21001');
INSERT INTO zabbix_mac.hosts VALUES (6, '192.168.1.200', 'test-server-2', '2026-06-08 16:02:38.967031', '2026-06-08 16:02:38.967031', '测试系统', '测试模块', '10002');
INSERT INTO zabbix_mac.hosts VALUES (5, '192.168.1.100', 'test-server-1', '2026-06-08 16:02:38.967031', '2026-06-08 16:03:00.844693', '更新系统', '更新模块', '10001');


--
-- Name: hosts_id_seq; Type: SEQUENCE SET; Schema: zabbix_mac; Owner: -
--

SELECT pg_catalog.setval('zabbix_mac.hosts_id_seq', 7, true);


--
-- PostgreSQL database dump complete
--

\unrestrict ApX2V0s53Lm2sYQYHQGaB8AiQbcaTDgdkhZ9Hhjlv2EKgCccfvx68Vhd5dmGVV6

