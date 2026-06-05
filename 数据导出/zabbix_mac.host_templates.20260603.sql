--
-- PostgreSQL database dump
--

\restrict 7AfmxffBcVNuhxR5G1faiKjNye4EV9xW54FWHmzJNXSjxnRYb9fMMAHkl9I4CrN

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
-- Name: host_templates; Type: TABLE; Schema: zabbix_mac; Owner: -
--

CREATE TABLE zabbix_mac.host_templates (
    id integer NOT NULL,
    host_id integer NOT NULL,
    template_id integer NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: host_templates_id_seq; Type: SEQUENCE; Schema: zabbix_mac; Owner: -
--

CREATE SEQUENCE zabbix_mac.host_templates_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: host_templates_id_seq; Type: SEQUENCE OWNED BY; Schema: zabbix_mac; Owner: -
--

ALTER SEQUENCE zabbix_mac.host_templates_id_seq OWNED BY zabbix_mac.host_templates.id;


--
-- Name: host_templates id; Type: DEFAULT; Schema: zabbix_mac; Owner: -
--

ALTER TABLE ONLY zabbix_mac.host_templates ALTER COLUMN id SET DEFAULT nextval('zabbix_mac.host_templates_id_seq'::regclass);


--
-- Data for Name: host_templates; Type: TABLE DATA; Schema: zabbix_mac; Owner: -
--

COPY zabbix_mac.host_templates (id, host_id, template_id, created_at) FROM stdin;
6	1	2	2026-04-24 15:30:05.529296
7	2	2	2026-04-24 15:30:11.369041
9	3	2	2026-04-24 15:34:24.213349
\.


--
-- Name: host_templates_id_seq; Type: SEQUENCE SET; Schema: zabbix_mac; Owner: -
--

SELECT pg_catalog.setval('zabbix_mac.host_templates_id_seq', 9, true);


--
-- Name: host_templates host_templates_host_id_template_id_key; Type: CONSTRAINT; Schema: zabbix_mac; Owner: -
--

ALTER TABLE ONLY zabbix_mac.host_templates
    ADD CONSTRAINT host_templates_host_id_template_id_key UNIQUE (host_id, template_id);


--
-- Name: host_templates host_templates_pkey; Type: CONSTRAINT; Schema: zabbix_mac; Owner: -
--

ALTER TABLE ONLY zabbix_mac.host_templates
    ADD CONSTRAINT host_templates_pkey PRIMARY KEY (id);


--
-- Name: idx_host_templates_host; Type: INDEX; Schema: zabbix_mac; Owner: -
--

CREATE INDEX idx_host_templates_host ON zabbix_mac.host_templates USING btree (host_id);


--
-- Name: idx_host_templates_template; Type: INDEX; Schema: zabbix_mac; Owner: -
--

CREATE INDEX idx_host_templates_template ON zabbix_mac.host_templates USING btree (template_id);


--
-- Name: host_templates host_templates_host_id_fkey; Type: FK CONSTRAINT; Schema: zabbix_mac; Owner: -
--

ALTER TABLE ONLY zabbix_mac.host_templates
    ADD CONSTRAINT host_templates_host_id_fkey FOREIGN KEY (host_id) REFERENCES zabbix_mac.hosts(id) ON DELETE CASCADE;


--
-- Name: host_templates host_templates_template_id_fkey; Type: FK CONSTRAINT; Schema: zabbix_mac; Owner: -
--

ALTER TABLE ONLY zabbix_mac.host_templates
    ADD CONSTRAINT host_templates_template_id_fkey FOREIGN KEY (template_id) REFERENCES zabbix_mac.templates(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict 7AfmxffBcVNuhxR5G1faiKjNye4EV9xW54FWHmzJNXSjxnRYb9fMMAHkl9I4CrN

