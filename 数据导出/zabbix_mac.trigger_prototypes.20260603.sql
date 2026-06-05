--
-- PostgreSQL database dump
--

\restrict a7LC4WyG29p7l8getQzQX1eG5gno9C4yGJhgxzhmKbcGK5g3uNw27fqUEpA7x2a

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
-- Name: trigger_prototypes; Type: TABLE; Schema: zabbix_mac; Owner: -
--

CREATE TABLE zabbix_mac.trigger_prototypes (
    id integer NOT NULL,
    discovery_rule_id integer NOT NULL,
    description text NOT NULL,
    expression text NOT NULL,
    priority integer NOT NULL,
    status integer DEFAULT 0,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: trigger_prototypes_id_seq; Type: SEQUENCE; Schema: zabbix_mac; Owner: -
--

CREATE SEQUENCE zabbix_mac.trigger_prototypes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: trigger_prototypes_id_seq; Type: SEQUENCE OWNED BY; Schema: zabbix_mac; Owner: -
--

ALTER SEQUENCE zabbix_mac.trigger_prototypes_id_seq OWNED BY zabbix_mac.trigger_prototypes.id;


--
-- Name: trigger_prototypes id; Type: DEFAULT; Schema: zabbix_mac; Owner: -
--

ALTER TABLE ONLY zabbix_mac.trigger_prototypes ALTER COLUMN id SET DEFAULT nextval('zabbix_mac.trigger_prototypes_id_seq'::regclass);


--
-- Data for Name: trigger_prototypes; Type: TABLE DATA; Schema: zabbix_mac; Owner: -
--

COPY zabbix_mac.trigger_prototypes (id, discovery_rule_id, description, expression, priority, status, created_at, updated_at) FROM stdin;
3	2	{#FSNAME}: Running out of free inodes (free < 20%)	{host:vfs.fs.inode[{#FSNAME},pfree].min(5m)}<20	2	0	2026-04-17 09:02:07.059233	2026-04-17 09:02:07.059233
4	2	{#FSNAME}: Disk space is critically low (used > 90%)	{host:vfs.fs.size[{#FSNAME},pused].last()}>90 and (({host:vfs.fs.size[{#FSNAME},total].last()}-{host:vfs.fs.size[{#FSNAME},used].last()})<5G or {host:vfs.fs.size[{#FSNAME},pused].timeleft(1h,,100)}<1d)	3	0	2026-04-17 09:02:07.059233	2026-04-17 09:02:07.059233
5	2	{#FSNAME}: Disk space is low (used > 80%)	{host:vfs.fs.size[{#FSNAME},pused].last()}>80 and (({host:vfs.fs.size[{#FSNAME},total].last()}-{host:vfs.fs.size[{#FSNAME},used].last()})<10G or {host:vfs.fs.size[{#FSNAME},pused].timeleft(1h,,100)}<1d)	2	0	2026-04-17 09:02:07.059233	2026-04-17 09:02:07.059233
2	2	{#FSNAME}: Running out of free inodes (free < 10%)	{host:vfs.fs.inode[{#FSNAME},pfree].min(5m)}<10	3	0	2026-04-17 09:02:07.059233	2026-04-17 09:02:07.059233
1	1	{#DEVNAME}: Disk read/write request responses are too high (read > 20 ms for 15m or write > 20 ms for 15m)	{host:vfs.dev.read.await[{#DEVNAME}].min(15m)} > 20 or {host:vfs.dev.write.await[{#DEVNAME}].min(15m)} > 20	3	0	2026-04-17 09:02:07.059233	2026-04-17 09:02:07.059233
\.


--
-- Name: trigger_prototypes_id_seq; Type: SEQUENCE SET; Schema: zabbix_mac; Owner: -
--

SELECT pg_catalog.setval('zabbix_mac.trigger_prototypes_id_seq', 5, true);


--
-- Name: trigger_prototypes trigger_prototypes_pkey; Type: CONSTRAINT; Schema: zabbix_mac; Owner: -
--

ALTER TABLE ONLY zabbix_mac.trigger_prototypes
    ADD CONSTRAINT trigger_prototypes_pkey PRIMARY KEY (id);


--
-- Name: idx_trigger_prototypes_rule; Type: INDEX; Schema: zabbix_mac; Owner: -
--

CREATE INDEX idx_trigger_prototypes_rule ON zabbix_mac.trigger_prototypes USING btree (discovery_rule_id);


--
-- Name: trigger_prototypes trigger_prototypes_discovery_rule_id_fkey; Type: FK CONSTRAINT; Schema: zabbix_mac; Owner: -
--

ALTER TABLE ONLY zabbix_mac.trigger_prototypes
    ADD CONSTRAINT trigger_prototypes_discovery_rule_id_fkey FOREIGN KEY (discovery_rule_id) REFERENCES zabbix_mac.discovery_rules(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict a7LC4WyG29p7l8getQzQX1eG5gno9C4yGJhgxzhmKbcGK5g3uNw27fqUEpA7x2a

