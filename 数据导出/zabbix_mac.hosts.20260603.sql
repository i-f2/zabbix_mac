--
-- PostgreSQL database dump
--

\restrict Ik09Hdd8edUh0BpfaVKGthcjrdlZ7T9cbAfwqPxAx15u48STa4EXm6bkgeDniFT

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
-- Name: hosts; Type: TABLE; Schema: zabbix_mac; Owner: -
--

CREATE TABLE zabbix_mac.hosts (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    system character varying(100),
    subsystem character varying(100),
    template_name character varying(255)
);


--
-- Name: hosts_id_seq; Type: SEQUENCE; Schema: zabbix_mac; Owner: -
--

CREATE SEQUENCE zabbix_mac.hosts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: hosts_id_seq; Type: SEQUENCE OWNED BY; Schema: zabbix_mac; Owner: -
--

ALTER SEQUENCE zabbix_mac.hosts_id_seq OWNED BY zabbix_mac.hosts.id;


--
-- Name: hosts id; Type: DEFAULT; Schema: zabbix_mac; Owner: -
--

ALTER TABLE ONLY zabbix_mac.hosts ALTER COLUMN id SET DEFAULT nextval('zabbix_mac.hosts_id_seq'::regclass);


--
-- Data for Name: hosts; Type: TABLE DATA; Schema: zabbix_mac; Owner: -
--

COPY zabbix_mac.hosts (id, name, description, created_at, updated_at, system, subsystem, template_name) FROM stdin;
1	Zabbix server	Local Zabbix server	2026-04-21 17:07:03.284849	2026-04-21 17:07:03.284849	上市系统	上市日常监管模块	21001
2	10.24.3.12	Test server 1	2026-04-21 17:07:03.284849	2026-04-21 17:07:03.284849	上市系统	上市日常监管模块	21001
3	10.24.3.23		2026-04-24 15:33:45.646743	2026-04-24 15:33:45.646743	上市系统	上市日常监管模块	21001
\.


--
-- Name: hosts_id_seq; Type: SEQUENCE SET; Schema: zabbix_mac; Owner: -
--

SELECT pg_catalog.setval('zabbix_mac.hosts_id_seq', 4, true);


--
-- Name: hosts hosts_name_key; Type: CONSTRAINT; Schema: zabbix_mac; Owner: -
--

ALTER TABLE ONLY zabbix_mac.hosts
    ADD CONSTRAINT hosts_name_key UNIQUE (name);


--
-- Name: hosts hosts_pkey; Type: CONSTRAINT; Schema: zabbix_mac; Owner: -
--

ALTER TABLE ONLY zabbix_mac.hosts
    ADD CONSTRAINT hosts_pkey PRIMARY KEY (id);


--
-- Name: idx_hosts_name; Type: INDEX; Schema: zabbix_mac; Owner: -
--

CREATE INDEX idx_hosts_name ON zabbix_mac.hosts USING btree (name);


--
-- PostgreSQL database dump complete
--

\unrestrict Ik09Hdd8edUh0BpfaVKGthcjrdlZ7T9cbAfwqPxAx15u48STa4EXm6bkgeDniFT

