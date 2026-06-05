--
-- PostgreSQL database dump
--

\restrict 6BsS0UIMaitYSH41k23fZ92AR1FivxYuAmUOq9rcUJcUT2loJcls65G9ettJWky

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
-- Name: webscenario_items; Type: TABLE; Schema: zabbix_mac; Owner: -
--

CREATE TABLE zabbix_mac.webscenario_items (
    id integer NOT NULL,
    system character varying(100) NOT NULL,
    subsystem character varying(100) NOT NULL,
    nginx_clb character varying(255),
    nginx character varying(255),
    clb character varying(255),
    pod character varying(255),
    webtest_api character varying(255) NOT NULL,
    webtest_nginx_api character varying(255) NOT NULL,
    in_room character varying(100),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: webscenario_items_id_seq; Type: SEQUENCE; Schema: zabbix_mac; Owner: -
--

CREATE SEQUENCE zabbix_mac.webscenario_items_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: webscenario_items_id_seq; Type: SEQUENCE OWNED BY; Schema: zabbix_mac; Owner: -
--

ALTER SEQUENCE zabbix_mac.webscenario_items_id_seq OWNED BY zabbix_mac.webscenario_items.id;


--
-- Name: webscenario_items id; Type: DEFAULT; Schema: zabbix_mac; Owner: -
--

ALTER TABLE ONLY zabbix_mac.webscenario_items ALTER COLUMN id SET DEFAULT nextval('zabbix_mac.webscenario_items_id_seq'::regclass);


--
-- Data for Name: webscenario_items; Type: TABLE DATA; Schema: zabbix_mac; Owner: -
--

COPY zabbix_mac.webscenario_items (id, system, subsystem, nginx_clb, nginx, clb, pod, webtest_api, webtest_nginx_api, in_room, created_at, updated_at) FROM stdin;
1	Test System	Test Subsystem	192.168.1.1:8080	192.168.1.2:8080	192.168.1.3:8080	192.168.1.4:8080	/api/test	/nginx/api/test	Room A	2026-04-24 17:50:52.977611	2026-04-24 17:50:52.977611
2	Another System	Another Subsystem	192.168.2.1:8080	192.168.2.2:8080	192.168.2.3:8080	192.168.2.4:8080	/api/another	/nginx/api/another	Room B	2026-04-24 17:50:52.977611	2026-04-24 17:50:52.977611
\.


--
-- Name: webscenario_items_id_seq; Type: SEQUENCE SET; Schema: zabbix_mac; Owner: -
--

SELECT pg_catalog.setval('zabbix_mac.webscenario_items_id_seq', 2, true);


--
-- Name: webscenario_items webscenario_items_pkey; Type: CONSTRAINT; Schema: zabbix_mac; Owner: -
--

ALTER TABLE ONLY zabbix_mac.webscenario_items
    ADD CONSTRAINT webscenario_items_pkey PRIMARY KEY (id);


--
-- Name: idx_webscenario_items_subsystem; Type: INDEX; Schema: zabbix_mac; Owner: -
--

CREATE INDEX idx_webscenario_items_subsystem ON zabbix_mac.webscenario_items USING btree (subsystem);


--
-- Name: idx_webscenario_items_system; Type: INDEX; Schema: zabbix_mac; Owner: -
--

CREATE INDEX idx_webscenario_items_system ON zabbix_mac.webscenario_items USING btree (system);


--
-- PostgreSQL database dump complete
--

\unrestrict 6BsS0UIMaitYSH41k23fZ92AR1FivxYuAmUOq9rcUJcUT2loJcls65G9ettJWky

