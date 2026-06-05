--
-- PostgreSQL database dump
--

\restrict Y9WmLICfR9KjcE7JUIPOYiDk6L4qe0lBS3BH3B6sGJ0oEObp8MsQQFnckJhAacX

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
-- Name: host_extra_items; Type: TABLE; Schema: zabbix_mac; Owner: -
--

CREATE TABLE zabbix_mac.host_extra_items (
    id integer NOT NULL,
    host_name character varying(255) NOT NULL,
    item_key character varying(255) NOT NULL,
    name character varying(255) NOT NULL,
    type integer NOT NULL,
    value_type integer NOT NULL,
    delay character varying(50) NOT NULL,
    description text,
    units character varying(50),
    multiplier integer DEFAULT 0,
    delta integer DEFAULT 0,
    history integer DEFAULT 7,
    trends integer DEFAULT 365,
    status integer DEFAULT 0,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: host_extra_items_id_seq; Type: SEQUENCE; Schema: zabbix_mac; Owner: -
--

CREATE SEQUENCE zabbix_mac.host_extra_items_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: host_extra_items_id_seq; Type: SEQUENCE OWNED BY; Schema: zabbix_mac; Owner: -
--

ALTER SEQUENCE zabbix_mac.host_extra_items_id_seq OWNED BY zabbix_mac.host_extra_items.id;


--
-- Name: host_extra_items id; Type: DEFAULT; Schema: zabbix_mac; Owner: -
--

ALTER TABLE ONLY zabbix_mac.host_extra_items ALTER COLUMN id SET DEFAULT nextval('zabbix_mac.host_extra_items_id_seq'::regclass);


--
-- Data for Name: host_extra_items; Type: TABLE DATA; Schema: zabbix_mac; Owner: -
--

COPY zabbix_mac.host_extra_items (id, host_name, item_key, name, type, value_type, delay, description, units, multiplier, delta, history, trends, status, created_at, updated_at) FROM stdin;
\.


--
-- Name: host_extra_items_id_seq; Type: SEQUENCE SET; Schema: zabbix_mac; Owner: -
--

SELECT pg_catalog.setval('zabbix_mac.host_extra_items_id_seq', 1, false);


--
-- Name: host_extra_items host_extra_items_host_name_item_key_key; Type: CONSTRAINT; Schema: zabbix_mac; Owner: -
--

ALTER TABLE ONLY zabbix_mac.host_extra_items
    ADD CONSTRAINT host_extra_items_host_name_item_key_key UNIQUE (host_name, item_key);


--
-- Name: host_extra_items host_extra_items_pkey; Type: CONSTRAINT; Schema: zabbix_mac; Owner: -
--

ALTER TABLE ONLY zabbix_mac.host_extra_items
    ADD CONSTRAINT host_extra_items_pkey PRIMARY KEY (id);


--
-- Name: idx_host_extra_items_host; Type: INDEX; Schema: zabbix_mac; Owner: -
--

CREATE INDEX idx_host_extra_items_host ON zabbix_mac.host_extra_items USING btree (host_name);


--
-- Name: idx_host_extra_items_key; Type: INDEX; Schema: zabbix_mac; Owner: -
--

CREATE INDEX idx_host_extra_items_key ON zabbix_mac.host_extra_items USING btree (item_key);


--
-- PostgreSQL database dump complete
--

\unrestrict Y9WmLICfR9KjcE7JUIPOYiDk6L4qe0lBS3BH3B6sGJ0oEObp8MsQQFnckJhAacX

