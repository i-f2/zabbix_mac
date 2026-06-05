--
-- PostgreSQL database dump
--

\restrict ZKC44xdzynxKakbzJEUuVv0b4nharYy1osiSxaCXPrWVIZigOKWVkAIkXGravPx

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
-- Name: templates; Type: TABLE; Schema: zabbix_mac; Owner: -
--

CREATE TABLE zabbix_mac.templates (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: templates_id_seq; Type: SEQUENCE; Schema: zabbix_mac; Owner: -
--

CREATE SEQUENCE zabbix_mac.templates_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: templates_id_seq; Type: SEQUENCE OWNED BY; Schema: zabbix_mac; Owner: -
--

ALTER SEQUENCE zabbix_mac.templates_id_seq OWNED BY zabbix_mac.templates.id;


--
-- Name: templates id; Type: DEFAULT; Schema: zabbix_mac; Owner: -
--

ALTER TABLE ONLY zabbix_mac.templates ALTER COLUMN id SET DEFAULT nextval('zabbix_mac.templates_id_seq'::regclass);


--
-- Data for Name: templates; Type: TABLE DATA; Schema: zabbix_mac; Owner: -
--

COPY zabbix_mac.templates (id, name, description, created_at, updated_at) FROM stdin;
2	21001	Standard Linux monitoring template	2026-04-17 09:02:07.059233	2026-04-17 09:02:07.059233
\.


--
-- Name: templates_id_seq; Type: SEQUENCE SET; Schema: zabbix_mac; Owner: -
--

SELECT pg_catalog.setval('zabbix_mac.templates_id_seq', 2, true);


--
-- Name: templates templates_name_key; Type: CONSTRAINT; Schema: zabbix_mac; Owner: -
--

ALTER TABLE ONLY zabbix_mac.templates
    ADD CONSTRAINT templates_name_key UNIQUE (name);


--
-- Name: templates templates_pkey; Type: CONSTRAINT; Schema: zabbix_mac; Owner: -
--

ALTER TABLE ONLY zabbix_mac.templates
    ADD CONSTRAINT templates_pkey PRIMARY KEY (id);


--
-- PostgreSQL database dump complete
--

\unrestrict ZKC44xdzynxKakbzJEUuVv0b4nharYy1osiSxaCXPrWVIZigOKWVkAIkXGravPx

