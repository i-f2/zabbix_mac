--
-- PostgreSQL database dump
--

\restrict 3HZLcSWXpUAObJhtaG24V8Nim9EikgBO2lpHzjNlANde7bmbiW2AkdNBZDv2pFw

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
-- Name: item_prototypes; Type: TABLE; Schema: zabbix_mac; Owner: -
--

CREATE TABLE zabbix_mac.item_prototypes (
    id integer NOT NULL,
    discovery_rule_id integer NOT NULL,
    name character varying(255) NOT NULL,
    key character varying(255) NOT NULL,
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
-- Name: item_prototypes_id_seq; Type: SEQUENCE; Schema: zabbix_mac; Owner: -
--

CREATE SEQUENCE zabbix_mac.item_prototypes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: item_prototypes_id_seq; Type: SEQUENCE OWNED BY; Schema: zabbix_mac; Owner: -
--

ALTER SEQUENCE zabbix_mac.item_prototypes_id_seq OWNED BY zabbix_mac.item_prototypes.id;


--
-- Name: item_prototypes id; Type: DEFAULT; Schema: zabbix_mac; Owner: -
--

ALTER TABLE ONLY zabbix_mac.item_prototypes ALTER COLUMN id SET DEFAULT nextval('zabbix_mac.item_prototypes_id_seq'::regclass);


--
-- Data for Name: item_prototypes; Type: TABLE DATA; Schema: zabbix_mac; Owner: -
--

COPY zabbix_mac.item_prototypes (id, discovery_rule_id, name, key, value_type, delay, description, units, multiplier, delta, history, trends, status, created_at, updated_at) FROM stdin;
1	1	{#DEVNAME}: Disk average queue size (avgqu-sz)	vfs.dev.queue_size[{#DEVNAME}]	0	0	\N	\N	0	0	7	365	0	2026-04-17 09:02:07.059233	2026-04-17 09:02:07.059233
2	1	{#DEVNAME}: Disk read request avg waiting time (r_await)	vfs.dev.read.await[{#DEVNAME}]	0	1m	\N	\N	0	0	7	365	0	2026-04-17 09:02:07.059233	2026-04-17 09:02:07.059233
3	1	{#DEVNAME}: Disk read rate	vfs.dev.read.rate[{#DEVNAME}]	0	0	\N	\N	0	0	7	365	0	2026-04-17 09:02:07.059233	2026-04-17 09:02:07.059233
4	1	{#DEVNAME}: Disk read time (rate)	vfs.dev.read.time.rate[{#DEVNAME}]	0	0	\N	\N	0	0	7	365	0	2026-04-17 09:02:07.059233	2026-04-17 09:02:07.059233
5	1	{#DEVNAME}: Disk utilization	vfs.dev.util[{#DEVNAME}]	0	0	\N	\N	0	0	7	365	0	2026-04-17 09:02:07.059233	2026-04-17 09:02:07.059233
6	1	{#DEVNAME}: Disk write request avg waiting time (w_await)	vfs.dev.write.await[{#DEVNAME}]	0	1m	\N	\N	0	0	7	365	0	2026-04-17 09:02:07.059233	2026-04-17 09:02:07.059233
7	1	{#DEVNAME}: Disk write rate	vfs.dev.write.rate[{#DEVNAME}]	0	0	\N	\N	0	0	7	365	0	2026-04-17 09:02:07.059233	2026-04-17 09:02:07.059233
8	1	{#DEVNAME}: Disk write time (rate)	vfs.dev.write.time.rate[{#DEVNAME}]	0	0	\N	\N	0	0	7	365	0	2026-04-17 09:02:07.059233	2026-04-17 09:02:07.059233
9	1	{#DEVNAME}: Get stats	vfs.file.contents[/sys/block/{#DEVNAME}/stat]	4	1m	\N	\N	0	0	7	365	0	2026-04-17 09:02:07.059233	2026-04-17 09:02:07.059233
10	2	{#FSNAME}: Free inodes in %	vfs.fs.inode[{#FSNAME},pfree]	0	1m	\N	\N	0	0	7	365	0	2026-04-17 09:02:07.059233	2026-04-17 09:02:07.059233
11	2	{#FSNAME}: Space utilization	vfs.fs.size[{#FSNAME},pused]	0	1m	\N	\N	0	0	7	365	0	2026-04-17 09:02:07.059233	2026-04-17 09:02:07.059233
12	2	{#FSNAME}: Total space	vfs.fs.size[{#FSNAME},total]	3	1m	\N	\N	0	0	7	365	0	2026-04-17 09:02:07.059233	2026-04-17 09:02:07.059233
13	2	{#FSNAME}: Used space	vfs.fs.size[{#FSNAME},used]	3	1m	\N	\N	0	0	7	365	0	2026-04-17 09:02:07.059233	2026-04-17 09:02:07.059233
\.


--
-- Name: item_prototypes_id_seq; Type: SEQUENCE SET; Schema: zabbix_mac; Owner: -
--

SELECT pg_catalog.setval('zabbix_mac.item_prototypes_id_seq', 13, true);


--
-- Name: item_prototypes item_prototypes_pkey; Type: CONSTRAINT; Schema: zabbix_mac; Owner: -
--

ALTER TABLE ONLY zabbix_mac.item_prototypes
    ADD CONSTRAINT item_prototypes_pkey PRIMARY KEY (id);


--
-- Name: idx_item_prototypes_rule; Type: INDEX; Schema: zabbix_mac; Owner: -
--

CREATE INDEX idx_item_prototypes_rule ON zabbix_mac.item_prototypes USING btree (discovery_rule_id);


--
-- Name: item_prototypes item_prototypes_discovery_rule_id_fkey; Type: FK CONSTRAINT; Schema: zabbix_mac; Owner: -
--

ALTER TABLE ONLY zabbix_mac.item_prototypes
    ADD CONSTRAINT item_prototypes_discovery_rule_id_fkey FOREIGN KEY (discovery_rule_id) REFERENCES zabbix_mac.discovery_rules(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict 3HZLcSWXpUAObJhtaG24V8Nim9EikgBO2lpHzjNlANde7bmbiW2AkdNBZDv2pFw

