--
-- PostgreSQL database dump
--

\restrict 1a2qcHyJi5xIecvliE9odNobTEZBj7h63xRX0q0pSHoK24AiHVTWC11d3lpbepP

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
-- Data for Name: webscenario_items_review; Type: TABLE DATA; Schema: zabbix_mac; Owner: -
--

INSERT INTO zabbix_mac.webscenario_items_review VALUES (1, 'Test System', 'Test Subsystem', 'Zabbix server', 'http://192.168.1.1:8080/nginx/api/test_interface', 'http://192.168.1.1:8080/nginx/api/test', '200', false, true, 'approved', '2026-04-27 10:16:54.71775', '2026-04-27 10:16:54.71775');
INSERT INTO zabbix_mac.webscenario_items_review VALUES (2, 'Another System', 'Another Subsystem', 'Zabbix server', 'http://192.168.2.1:8080/nginx/api/another_interface', 'http://192.168.2.1:8080/nginx/api/another', '200', false, true, 'approved', '2026-04-27 10:16:54.71775', '2026-04-27 10:16:54.71775');
INSERT INTO zabbix_mac.webscenario_items_review VALUES (3, 'Test System', 'Test Subsystem', 'Zabbix server', 'http://192.168.1.2:8080/nginx/api/test_interface', 'http://192.168.1.2:8080/nginx/api/test', '200', false, true, 'approved', '2026-04-27 10:16:54.722086', '2026-04-27 10:16:54.722086');
INSERT INTO zabbix_mac.webscenario_items_review VALUES (4, 'Another System', 'Another Subsystem', 'Zabbix server', 'http://192.168.2.2:8080/nginx/api/another_interface', 'http://192.168.2.2:8080/nginx/api/another', '200', false, true, 'approved', '2026-04-27 10:16:54.722086', '2026-04-27 10:16:54.722086');
INSERT INTO zabbix_mac.webscenario_items_review VALUES (5, 'Test System', 'Test Subsystem', 'Zabbix server', 'http://192.168.1.3:8080/api/test_interface', 'http://192.168.1.3:8080/api/test', '200', false, true, 'approved', '2026-04-27 10:16:54.722947', '2026-04-27 10:16:54.722947');
INSERT INTO zabbix_mac.webscenario_items_review VALUES (6, 'Another System', 'Another Subsystem', 'Zabbix server', 'http://192.168.2.3:8080/api/another_interface', 'http://192.168.2.3:8080/api/another', '200', false, true, 'approved', '2026-04-27 10:16:54.722947', '2026-04-27 10:16:54.722947');
INSERT INTO zabbix_mac.webscenario_items_review VALUES (7, 'Test System', 'Test Subsystem', 'Zabbix server', 'http://192.168.1.4:8080/api/test_interface', 'http://192.168.1.4:8080/api/test', '200', false, true, 'approved', '2026-04-27 10:16:54.725175', '2026-04-27 10:16:54.725175');
INSERT INTO zabbix_mac.webscenario_items_review VALUES (8, 'Another System', 'Another Subsystem', 'Zabbix server', 'http://192.168.2.4:8080/api/another_interface', 'http://192.168.2.4:8080/api/another', '200', false, true, 'approved', '2026-04-27 10:16:54.725175', '2026-04-27 10:16:54.725175');


--
-- Name: webscenario_items_review_id_seq; Type: SEQUENCE SET; Schema: zabbix_mac; Owner: -
--

SELECT pg_catalog.setval('zabbix_mac.webscenario_items_review_id_seq', 8, true);


--
-- PostgreSQL database dump complete
--

\unrestrict 1a2qcHyJi5xIecvliE9odNobTEZBj7h63xRX0q0pSHoK24AiHVTWC11d3lpbepP

