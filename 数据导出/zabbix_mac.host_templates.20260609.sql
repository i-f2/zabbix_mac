--
-- PostgreSQL database dump
--

\restrict FGCtd5P8I9034JfwRtaYqOU4uFMybm2sv4LCOsSoyuK0Mm38S4eKoRpTFjzKjVd

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
-- Data for Name: host_templates; Type: TABLE DATA; Schema: zabbix_mac; Owner: -
--

INSERT INTO zabbix_mac.host_templates VALUES (6, 1, 2, '2026-04-24 15:30:05.529296');
INSERT INTO zabbix_mac.host_templates VALUES (7, 2, 2, '2026-04-24 15:30:11.369041');
INSERT INTO zabbix_mac.host_templates VALUES (9, 3, 2, '2026-04-24 15:34:24.213349');


--
-- Name: host_templates_id_seq; Type: SEQUENCE SET; Schema: zabbix_mac; Owner: -
--

SELECT pg_catalog.setval('zabbix_mac.host_templates_id_seq', 9, true);


--
-- PostgreSQL database dump complete
--

\unrestrict FGCtd5P8I9034JfwRtaYqOU4uFMybm2sv4LCOsSoyuK0Mm38S4eKoRpTFjzKjVd

