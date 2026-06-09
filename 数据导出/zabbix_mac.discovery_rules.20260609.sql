--
-- PostgreSQL database dump
--

\restrict H3LXSysxDQCKtBA4KKD19QFOp91oNGIVH3eGlxzRD1CDw66pHE1LFODDN3Z1TBY

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
-- Data for Name: discovery_rules; Type: TABLE DATA; Schema: zabbix_mac; Owner: -
--

INSERT INTO zabbix_mac.discovery_rules VALUES (1, 'Block devices discovery', 'vfs.dev.discovery', '1h', 0, 0, '21001', '2026-04-17 09:02:07.059233', '2026-04-17 09:02:07.059233');
INSERT INTO zabbix_mac.discovery_rules VALUES (2, 'Mounted filesystem discovery', 'vfs.fs.discovery', '1h', 0, 0, '21001', '2026-04-17 09:02:07.059233', '2026-04-17 09:02:07.059233');


--
-- Name: discovery_rules_id_seq; Type: SEQUENCE SET; Schema: zabbix_mac; Owner: -
--

SELECT pg_catalog.setval('zabbix_mac.discovery_rules_id_seq', 2, true);


--
-- PostgreSQL database dump complete
--

\unrestrict H3LXSysxDQCKtBA4KKD19QFOp91oNGIVH3eGlxzRD1CDw66pHE1LFODDN3Z1TBY

