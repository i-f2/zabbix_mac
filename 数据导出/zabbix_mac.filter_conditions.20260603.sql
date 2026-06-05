--
-- PostgreSQL database dump
--

\restrict bwtlOve28bCGkcdM02vHZL2AmHSJ8vPkSXESrcCSeAdkhFbQv2O0X2Tgs6KG7ZY

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
-- Name: filter_conditions; Type: TABLE; Schema: zabbix_mac; Owner: -
--

CREATE TABLE zabbix_mac.filter_conditions (
    id integer NOT NULL,
    discovery_rule_id integer NOT NULL,
    macro character varying(255) NOT NULL,
    value text NOT NULL,
    operator character varying(50) DEFAULT 'MATCHES_REGEX'::character varying,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: filter_conditions_id_seq; Type: SEQUENCE; Schema: zabbix_mac; Owner: -
--

CREATE SEQUENCE zabbix_mac.filter_conditions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: filter_conditions_id_seq; Type: SEQUENCE OWNED BY; Schema: zabbix_mac; Owner: -
--

ALTER SEQUENCE zabbix_mac.filter_conditions_id_seq OWNED BY zabbix_mac.filter_conditions.id;


--
-- Name: filter_conditions id; Type: DEFAULT; Schema: zabbix_mac; Owner: -
--

ALTER TABLE ONLY zabbix_mac.filter_conditions ALTER COLUMN id SET DEFAULT nextval('zabbix_mac.filter_conditions_id_seq'::regclass);


--
-- Data for Name: filter_conditions; Type: TABLE DATA; Schema: zabbix_mac; Owner: -
--

COPY zabbix_mac.filter_conditions (id, discovery_rule_id, macro, value, operator, created_at) FROM stdin;
1	1	{#DEVTYPE}	disk	MATCHES_REGEX	2026-04-17 09:02:07.059233
2	1	{#DEVNAME}	.+	MATCHES_REGEX	2026-04-17 09:02:07.059233
3	1	{#DEVNAME}	^(loop[0-9]*|sd[a-z][0-9]+|nbd[0-9]+|sr[0-9]+|fd[0-9]+|dm-[0-9]+|ram[0-9]+|ploop[a-z0-9]+|md[0-9]*|hcp[0-9]*|zram[0-9]*)$	NOT_MATCHES_REGEX	2026-04-17 09:02:07.059233
4	2	{#FSTYPE}	^(btrfs|ext2|ext3|ext4|reiser|xfs|ffs|ufs|jfs|jfs2|vxfs|hfs|apfs|refs|ntfs|fat32|zfs)$	MATCHES_REGEX	2026-04-17 09:02:07.059233
5	2	{#FSTYPE}	^\\s$	NOT_MATCHES_REGEX	2026-04-17 09:02:07.059233
6	2	{#FSNAME}	.+	MATCHES_REGEX	2026-04-17 09:02:07.059233
7	2	{#FSNAME}	^(/dev|/sys|/run|/proc|.+/shm$)	NOT_MATCHES_REGEX	2026-04-17 09:02:07.059233
\.


--
-- Name: filter_conditions_id_seq; Type: SEQUENCE SET; Schema: zabbix_mac; Owner: -
--

SELECT pg_catalog.setval('zabbix_mac.filter_conditions_id_seq', 7, true);


--
-- Name: filter_conditions filter_conditions_pkey; Type: CONSTRAINT; Schema: zabbix_mac; Owner: -
--

ALTER TABLE ONLY zabbix_mac.filter_conditions
    ADD CONSTRAINT filter_conditions_pkey PRIMARY KEY (id);


--
-- Name: idx_filter_conditions_rule; Type: INDEX; Schema: zabbix_mac; Owner: -
--

CREATE INDEX idx_filter_conditions_rule ON zabbix_mac.filter_conditions USING btree (discovery_rule_id);


--
-- Name: filter_conditions filter_conditions_discovery_rule_id_fkey; Type: FK CONSTRAINT; Schema: zabbix_mac; Owner: -
--

ALTER TABLE ONLY zabbix_mac.filter_conditions
    ADD CONSTRAINT filter_conditions_discovery_rule_id_fkey FOREIGN KEY (discovery_rule_id) REFERENCES zabbix_mac.discovery_rules(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict bwtlOve28bCGkcdM02vHZL2AmHSJ8vPkSXESrcCSeAdkhFbQv2O0X2Tgs6KG7ZY

