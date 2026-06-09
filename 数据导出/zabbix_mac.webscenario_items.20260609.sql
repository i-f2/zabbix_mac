--
-- PostgreSQL database dump
--

\restrict b7nyO0ebWKoJGkMKKMhPRX8Gw4cHQHt7YCqUdGkJ0juBAYWvrTlncsz4ldhQzSd

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
-- Data for Name: webscenario_items; Type: TABLE DATA; Schema: zabbix_mac; Owner: -
--

INSERT INTO zabbix_mac.webscenario_items VALUES (1, 'Test System', 'Test Subsystem', '192.168.1.1:8080', '192.168.1.2:8080', '192.168.1.3:8080', '192.168.1.4:8080', '/api/test', '/nginx/api/test', 'Room A', '2026-04-24 17:50:52.977611', '2026-04-24 17:50:52.977611');
INSERT INTO zabbix_mac.webscenario_items VALUES (2, 'Another System', 'Another Subsystem', '192.168.2.1:8080', '192.168.2.2:8080', '192.168.2.3:8080', '192.168.2.4:8080', '/api/another', '/nginx/api/another', 'Room B', '2026-04-24 17:50:52.977611', '2026-04-24 17:50:52.977611');


--
-- Name: webscenario_items_id_seq; Type: SEQUENCE SET; Schema: zabbix_mac; Owner: -
--

SELECT pg_catalog.setval('zabbix_mac.webscenario_items_id_seq', 2, true);


--
-- PostgreSQL database dump complete
--

\unrestrict b7nyO0ebWKoJGkMKKMhPRX8Gw4cHQHt7YCqUdGkJ0juBAYWvrTlncsz4ldhQzSd

