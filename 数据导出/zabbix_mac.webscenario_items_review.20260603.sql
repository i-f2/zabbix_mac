--
-- PostgreSQL database dump
--

\restrict sToNO09is1tPSc6AuFkd26cG4IE3Zkh6Oaeb4twIhxg6XuWcpJQWjDSz1BNCKWD

-- Dumped from database version 14.22
-- Dumped by pg_dump version 14.22

\connect ops
SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'SQL_ASCII';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', 'zabbix_mac', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: webscenario_items_review; Type: TABLE; Schema: zabbix_mac; Owner: -
--

CREATE TABLE zabbix_mac.webscenario_items_review (
    id integer NOT NULL,
    system character varying(100) NOT NULL,
    subsystem character varying(100) NOT NULL,
    host character varying(255) DEFAULT 'Zabbix server'::character varying NOT NULL,
    name character varying(255) NOT NULL,
    url character varying(255) NOT NULL,
    status_code character varying(50) DEFAULT '200'::character varying NOT NULL,
    modified boolean DEFAULT false,
    confirmed boolean DEFAULT false,
    status_verification character varying(50) DEFAULT 'pending'::character varying,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: webscenario_items_review_id_seq; Type: SEQUENCE; Schema: zabbix_mac; Owner: -
--

CREATE SEQUENCE zabbix_mac.webscenario_items_review_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: webscenario_items_review_id_seq; Type: SEQUENCE OWNED BY; Schema: zabbix_mac; Owner: -
--

ALTER SEQUENCE zabbix_mac.webscenario_items_review_id_seq OWNED BY zabbix_mac.webscenario_items_review.id;


--
-- Name: webscenario_items_review id; Type: DEFAULT; Schema: zabbix_mac; Owner: -
--

ALTER TABLE ONLY zabbix_mac.webscenario_items_review ALTER COLUMN id SET DEFAULT nextval('zabbix_mac.webscenario_items_review_id_seq'::regclass);


--
-- Data for Name: webscenario_items_review; Type: TABLE DATA; Schema: zabbix_mac; Owner: -
--

COPY zabbix_mac.webscenario_items_review (id, system, subsystem, host, name, url, status_code, modified, confirmed, status_verification, created_at, updated_at) FROM stdin;
1	Test System	Test Subsystem	Zabbix server	http://192.168.1.1:8080/nginx/api/test_interface	http://192.168.1.1:8080/nginx/api/test	200	f	t	approved	2026-04-27 10:16:54.71775	2026-04-27 10:16:54.71775
2	Another System	Another Subsystem	Zabbix server	http://192.168.2.1:8080/nginx/api/another_interface	http://192.168.2.1:8080/nginx/api/another	200	f	t	approved	2026-04-27 10:16:54.71775	2026-04-27 10:16:54.71775
3	Test System	Test Subsystem	Zabbix server	http://192.168.1.2:8080/nginx/api/test_interface	http://192.168.1.2:8080/nginx/api/test	200	f	t	approved	2026-04-27 10:16:54.722086	2026-04-27 10:16:54.722086
4	Another System	Another Subsystem	Zabbix server	http://192.168.2.2:8080/nginx/api/another_interface	http://192.168.2.2:8080/nginx/api/another	200	f	t	approved	2026-04-27 10:16:54.722086	2026-04-27 10:16:54.722086
5	Test System	Test Subsystem	Zabbix server	http://192.168.1.3:8080/api/test_interface	http://192.168.1.3:8080/api/test	200	f	t	approved	2026-04-27 10:16:54.722947	2026-04-27 10:16:54.722947
6	Another System	Another Subsystem	Zabbix server	http://192.168.2.3:8080/api/another_interface	http://192.168.2.3:8080/api/another	200	f	t	approved	2026-04-27 10:16:54.722947	2026-04-27 10:16:54.722947
7	Test System	Test Subsystem	Zabbix server	http://192.168.1.4:8080/api/test_interface	http://192.168.1.4:8080/api/test	200	f	t	approved	2026-04-27 10:16:54.725175	2026-04-27 10:16:54.725175
8	Another System	Another Subsystem	Zabbix server	http://192.168.2.4:8080/api/another_interface	http://192.168.2.4:8080/api/another	200	f	t	approved	2026-04-27 10:16:54.725175	2026-04-27 10:16:54.725175
\.


--
-- Name: webscenario_items_review_id_seq; Type: SEQUENCE SET; Schema: zabbix_mac; Owner: -
--

SELECT pg_catalog.setval('zabbix_mac.webscenario_items_review_id_seq', 8, true);


--
-- Name: webscenario_items_review webscenario_items_review_pkey; Type: CONSTRAINT; Schema: zabbix_mac; Owner: -
--

ALTER TABLE ONLY zabbix_mac.webscenario_items_review
    ADD CONSTRAINT webscenario_items_review_pkey PRIMARY KEY (id);


--
-- Name: idx_webscenario_items_review_host; Type: INDEX; Schema: zabbix_mac; Owner: -
--

CREATE INDEX idx_webscenario_items_review_host ON zabbix_mac.webscenario_items_review USING btree (host);


--
-- Name: idx_webscenario_items_review_subsystem; Type: INDEX; Schema: zabbix_mac; Owner: -
--

CREATE INDEX idx_webscenario_items_review_subsystem ON zabbix_mac.webscenario_items_review USING btree (subsystem);


--
-- Name: idx_webscenario_items_review_system; Type: INDEX; Schema: zabbix_mac; Owner: -
--

CREATE INDEX idx_webscenario_items_review_system ON zabbix_mac.webscenario_items_review USING btree (system);


--
-- PostgreSQL database dump complete
--

\unrestrict sToNO09is1tPSc6AuFkd26cG4IE3Zkh6Oaeb4twIhxg6XuWcpJQWjDSz1BNCKWD

