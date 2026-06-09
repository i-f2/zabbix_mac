--
-- PostgreSQL database dump
--

\restrict Uafjx78DFKQwdWVfVbx3NcYxNL3GY1SnNuUj6lq7hb446dPperz8eP1Ihhtno5T

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
-- Data for Name: templates; Type: TABLE DATA; Schema: zabbix_mac; Owner: -
--

INSERT INTO zabbix_mac.templates VALUES (2, '21001', 'Standard Linux monitoring template', '2026-04-17 09:02:07.059233', '2026-04-17 09:02:07.059233');


--
-- Name: templates_id_seq; Type: SEQUENCE SET; Schema: zabbix_mac; Owner: -
--

SELECT pg_catalog.setval('zabbix_mac.templates_id_seq', 2, true);


--
-- PostgreSQL database dump complete
--

\unrestrict Uafjx78DFKQwdWVfVbx3NcYxNL3GY1SnNuUj6lq7hb446dPperz8eP1Ihhtno5T

