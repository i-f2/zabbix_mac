--
-- PostgreSQL database dump
--

\restrict kR9SC7cO79M3FwNF64rF56N9U7yj0ksTKIXT4ssilAhPsKyEatDRzQczOqvTdeg

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
-- Name: item_prototypes_review; Type: TABLE; Schema: zabbix_mac; Owner: -
--

CREATE TABLE zabbix_mac.item_prototypes_review (
    id integer NOT NULL,
    item_prototype_id integer NOT NULL,
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
    modified boolean DEFAULT false,
    confirmed boolean DEFAULT false,
    status_verification character varying(50) DEFAULT 'pending'::character varying,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    host_ip character varying(255) NOT NULL,
    system character varying(100),
    subsystem character varying(100)
);


--
-- Name: item_prototypes_review_id_seq; Type: SEQUENCE; Schema: zabbix_mac; Owner: -
--

CREATE SEQUENCE zabbix_mac.item_prototypes_review_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: item_prototypes_review_id_seq; Type: SEQUENCE OWNED BY; Schema: zabbix_mac; Owner: -
--

ALTER SEQUENCE zabbix_mac.item_prototypes_review_id_seq OWNED BY zabbix_mac.item_prototypes_review.id;


--
-- Name: item_prototypes_review id; Type: DEFAULT; Schema: zabbix_mac; Owner: -
--

ALTER TABLE ONLY zabbix_mac.item_prototypes_review ALTER COLUMN id SET DEFAULT nextval('zabbix_mac.item_prototypes_review_id_seq'::regclass);


--
-- Data for Name: item_prototypes_review; Type: TABLE DATA; Schema: zabbix_mac; Owner: -
--

COPY zabbix_mac.item_prototypes_review (id, item_prototype_id, discovery_rule_id, name, key, value_type, delay, description, units, multiplier, delta, history, trends, status, modified, confirmed, status_verification, created_at, updated_at, host_ip, system, subsystem) FROM stdin;
175	11	2	{#FSNAME}: Space utilization	vfs.fs.size[{#FSNAME},pused]	0	1m	\N	\N	0	0	7	365	0	f	f	pending	2026-04-30 17:26:59.89368	2026-04-30 17:26:59.89368	10.24.3.12	上市系统	上市日常监管模块
176	11	2	{#FSNAME}: Space utilization	vfs.fs.size[{#FSNAME},pused]	0	1m	\N	\N	0	0	7	365	0	f	f	pending	2026-04-30 17:26:59.89368	2026-04-30 17:26:59.89368	10.24.3.23	上市系统	上市日常监管模块
177	12	2	{#FSNAME}: Total space	vfs.fs.size[{#FSNAME},total]	3	1m	\N	\N	0	0	7	365	0	f	f	pending	2026-04-30 17:26:59.89368	2026-04-30 17:26:59.89368	Zabbix server	上市系统	上市日常监管模块
178	12	2	{#FSNAME}: Total space	vfs.fs.size[{#FSNAME},total]	3	1m	\N	\N	0	0	7	365	0	f	f	pending	2026-04-30 17:26:59.89368	2026-04-30 17:26:59.89368	10.24.3.12	上市系统	上市日常监管模块
179	12	2	{#FSNAME}: Total space	vfs.fs.size[{#FSNAME},total]	3	1m	\N	\N	0	0	7	365	0	f	f	pending	2026-04-30 17:26:59.89368	2026-04-30 17:26:59.89368	10.24.3.23	上市系统	上市日常监管模块
180	13	2	{#FSNAME}: Used space	vfs.fs.size[{#FSNAME},used]	3	1m	\N	\N	0	0	7	365	0	f	f	pending	2026-04-30 17:26:59.89368	2026-04-30 17:26:59.89368	Zabbix server	上市系统	上市日常监管模块
181	13	2	{#FSNAME}: Used space	vfs.fs.size[{#FSNAME},used]	3	1m	\N	\N	0	0	7	365	0	f	f	pending	2026-04-30 17:26:59.89368	2026-04-30 17:26:59.89368	10.24.3.12	上市系统	上市日常监管模块
182	13	2	{#FSNAME}: Used space	vfs.fs.size[{#FSNAME},used]	3	1m	\N	\N	0	0	7	365	0	f	f	pending	2026-04-30 17:26:59.89368	2026-04-30 17:26:59.89368	10.24.3.23	上市系统	上市日常监管模块
144	1	1	{#DEVNAME}: Disk average queue size (avgqu-sz)	vfs.dev.queue_size[{#DEVNAME}]	0	0	\N	\N	0	0	7	365	0	f	f	pending	2026-04-30 17:26:59.89368	2026-04-30 17:26:59.89368	Zabbix server	上市系统	上市日常监管模块
145	1	1	{#DEVNAME}: Disk average queue size (avgqu-sz)	vfs.dev.queue_size[{#DEVNAME}]	0	0	\N	\N	0	0	7	365	0	f	f	pending	2026-04-30 17:26:59.89368	2026-04-30 17:26:59.89368	10.24.3.12	上市系统	上市日常监管模块
146	1	1	{#DEVNAME}: Disk average queue size (avgqu-sz)	vfs.dev.queue_size[{#DEVNAME}]	0	0	\N	\N	0	0	7	365	0	f	f	pending	2026-04-30 17:26:59.89368	2026-04-30 17:26:59.89368	10.24.3.23	上市系统	上市日常监管模块
147	2	1	{#DEVNAME}: Disk read request avg waiting time (r_await)	vfs.dev.read.await[{#DEVNAME}]	0	1m	\N	\N	0	0	7	365	0	f	f	pending	2026-04-30 17:26:59.89368	2026-04-30 17:26:59.89368	Zabbix server	上市系统	上市日常监管模块
148	2	1	{#DEVNAME}: Disk read request avg waiting time (r_await)	vfs.dev.read.await[{#DEVNAME}]	0	1m	\N	\N	0	0	7	365	0	f	f	pending	2026-04-30 17:26:59.89368	2026-04-30 17:26:59.89368	10.24.3.12	上市系统	上市日常监管模块
149	2	1	{#DEVNAME}: Disk read request avg waiting time (r_await)	vfs.dev.read.await[{#DEVNAME}]	0	1m	\N	\N	0	0	7	365	0	f	f	pending	2026-04-30 17:26:59.89368	2026-04-30 17:26:59.89368	10.24.3.23	上市系统	上市日常监管模块
150	3	1	{#DEVNAME}: Disk read rate	vfs.dev.read.rate[{#DEVNAME}]	0	0	\N	\N	0	0	7	365	0	f	f	pending	2026-04-30 17:26:59.89368	2026-04-30 17:26:59.89368	Zabbix server	上市系统	上市日常监管模块
151	3	1	{#DEVNAME}: Disk read rate	vfs.dev.read.rate[{#DEVNAME}]	0	0	\N	\N	0	0	7	365	0	f	f	pending	2026-04-30 17:26:59.89368	2026-04-30 17:26:59.89368	10.24.3.12	上市系统	上市日常监管模块
152	3	1	{#DEVNAME}: Disk read rate	vfs.dev.read.rate[{#DEVNAME}]	0	0	\N	\N	0	0	7	365	0	f	f	pending	2026-04-30 17:26:59.89368	2026-04-30 17:26:59.89368	10.24.3.23	上市系统	上市日常监管模块
153	4	1	{#DEVNAME}: Disk read time (rate)	vfs.dev.read.time.rate[{#DEVNAME}]	0	0	\N	\N	0	0	7	365	0	f	f	pending	2026-04-30 17:26:59.89368	2026-04-30 17:26:59.89368	Zabbix server	上市系统	上市日常监管模块
154	4	1	{#DEVNAME}: Disk read time (rate)	vfs.dev.read.time.rate[{#DEVNAME}]	0	0	\N	\N	0	0	7	365	0	f	f	pending	2026-04-30 17:26:59.89368	2026-04-30 17:26:59.89368	10.24.3.12	上市系统	上市日常监管模块
155	4	1	{#DEVNAME}: Disk read time (rate)	vfs.dev.read.time.rate[{#DEVNAME}]	0	0	\N	\N	0	0	7	365	0	f	f	pending	2026-04-30 17:26:59.89368	2026-04-30 17:26:59.89368	10.24.3.23	上市系统	上市日常监管模块
156	5	1	{#DEVNAME}: Disk utilization	vfs.dev.util[{#DEVNAME}]	0	0	\N	\N	0	0	7	365	0	f	f	pending	2026-04-30 17:26:59.89368	2026-04-30 17:26:59.89368	Zabbix server	上市系统	上市日常监管模块
157	5	1	{#DEVNAME}: Disk utilization	vfs.dev.util[{#DEVNAME}]	0	0	\N	\N	0	0	7	365	0	f	f	pending	2026-04-30 17:26:59.89368	2026-04-30 17:26:59.89368	10.24.3.12	上市系统	上市日常监管模块
158	5	1	{#DEVNAME}: Disk utilization	vfs.dev.util[{#DEVNAME}]	0	0	\N	\N	0	0	7	365	0	f	f	pending	2026-04-30 17:26:59.89368	2026-04-30 17:26:59.89368	10.24.3.23	上市系统	上市日常监管模块
159	6	1	{#DEVNAME}: Disk write request avg waiting time (w_await)	vfs.dev.write.await[{#DEVNAME}]	0	1m	\N	\N	0	0	7	365	0	f	f	pending	2026-04-30 17:26:59.89368	2026-04-30 17:26:59.89368	Zabbix server	上市系统	上市日常监管模块
160	6	1	{#DEVNAME}: Disk write request avg waiting time (w_await)	vfs.dev.write.await[{#DEVNAME}]	0	1m	\N	\N	0	0	7	365	0	f	f	pending	2026-04-30 17:26:59.89368	2026-04-30 17:26:59.89368	10.24.3.12	上市系统	上市日常监管模块
161	6	1	{#DEVNAME}: Disk write request avg waiting time (w_await)	vfs.dev.write.await[{#DEVNAME}]	0	1m	\N	\N	0	0	7	365	0	f	f	pending	2026-04-30 17:26:59.89368	2026-04-30 17:26:59.89368	10.24.3.23	上市系统	上市日常监管模块
162	7	1	{#DEVNAME}: Disk write rate	vfs.dev.write.rate[{#DEVNAME}]	0	0	\N	\N	0	0	7	365	0	f	f	pending	2026-04-30 17:26:59.89368	2026-04-30 17:26:59.89368	Zabbix server	上市系统	上市日常监管模块
163	7	1	{#DEVNAME}: Disk write rate	vfs.dev.write.rate[{#DEVNAME}]	0	0	\N	\N	0	0	7	365	0	f	f	pending	2026-04-30 17:26:59.89368	2026-04-30 17:26:59.89368	10.24.3.12	上市系统	上市日常监管模块
164	7	1	{#DEVNAME}: Disk write rate	vfs.dev.write.rate[{#DEVNAME}]	0	0	\N	\N	0	0	7	365	0	f	f	pending	2026-04-30 17:26:59.89368	2026-04-30 17:26:59.89368	10.24.3.23	上市系统	上市日常监管模块
165	8	1	{#DEVNAME}: Disk write time (rate)	vfs.dev.write.time.rate[{#DEVNAME}]	0	0	\N	\N	0	0	7	365	0	f	f	pending	2026-04-30 17:26:59.89368	2026-04-30 17:26:59.89368	Zabbix server	上市系统	上市日常监管模块
166	8	1	{#DEVNAME}: Disk write time (rate)	vfs.dev.write.time.rate[{#DEVNAME}]	0	0	\N	\N	0	0	7	365	0	f	f	pending	2026-04-30 17:26:59.89368	2026-04-30 17:26:59.89368	10.24.3.12	上市系统	上市日常监管模块
167	8	1	{#DEVNAME}: Disk write time (rate)	vfs.dev.write.time.rate[{#DEVNAME}]	0	0	\N	\N	0	0	7	365	0	f	f	pending	2026-04-30 17:26:59.89368	2026-04-30 17:26:59.89368	10.24.3.23	上市系统	上市日常监管模块
168	9	1	{#DEVNAME}: Get stats	vfs.file.contents[/sys/block/{#DEVNAME}/stat]	4	1m	\N	\N	0	0	7	365	0	f	f	pending	2026-04-30 17:26:59.89368	2026-04-30 17:26:59.89368	Zabbix server	上市系统	上市日常监管模块
169	9	1	{#DEVNAME}: Get stats	vfs.file.contents[/sys/block/{#DEVNAME}/stat]	4	1m	\N	\N	0	0	7	365	0	f	f	pending	2026-04-30 17:26:59.89368	2026-04-30 17:26:59.89368	10.24.3.12	上市系统	上市日常监管模块
170	9	1	{#DEVNAME}: Get stats	vfs.file.contents[/sys/block/{#DEVNAME}/stat]	4	1m	\N	\N	0	0	7	365	0	f	f	pending	2026-04-30 17:26:59.89368	2026-04-30 17:26:59.89368	10.24.3.23	上市系统	上市日常监管模块
171	10	2	{#FSNAME}: Free inodes in %	vfs.fs.inode[{#FSNAME},pfree]	0	1m	\N	\N	0	0	7	365	0	f	f	pending	2026-04-30 17:26:59.89368	2026-04-30 17:26:59.89368	Zabbix server	上市系统	上市日常监管模块
172	10	2	{#FSNAME}: Free inodes in %	vfs.fs.inode[{#FSNAME},pfree]	0	1m	\N	\N	0	0	7	365	0	f	f	pending	2026-04-30 17:26:59.89368	2026-04-30 17:26:59.89368	10.24.3.12	上市系统	上市日常监管模块
173	10	2	{#FSNAME}: Free inodes in %	vfs.fs.inode[{#FSNAME},pfree]	0	1m	\N	\N	0	0	7	365	0	f	f	pending	2026-04-30 17:26:59.89368	2026-04-30 17:26:59.89368	10.24.3.23	上市系统	上市日常监管模块
174	11	2	{#FSNAME}: Space utilization	vfs.fs.size[{#FSNAME},pused]	0	1m	\N	\N	0	0	7	365	0	f	f	pending	2026-04-30 17:26:59.89368	2026-04-30 17:26:59.89368	Zabbix server	上市系统	上市日常监管模块
\.


--
-- Name: item_prototypes_review_id_seq; Type: SEQUENCE SET; Schema: zabbix_mac; Owner: -
--

SELECT pg_catalog.setval('zabbix_mac.item_prototypes_review_id_seq', 182, true);


--
-- Name: item_prototypes_review item_prototypes_review_pkey; Type: CONSTRAINT; Schema: zabbix_mac; Owner: -
--

ALTER TABLE ONLY zabbix_mac.item_prototypes_review
    ADD CONSTRAINT item_prototypes_review_pkey PRIMARY KEY (id);


--
-- Name: idx_item_prototypes_review_confirmed; Type: INDEX; Schema: zabbix_mac; Owner: -
--

CREATE INDEX idx_item_prototypes_review_confirmed ON zabbix_mac.item_prototypes_review USING btree (confirmed);


--
-- Name: idx_item_prototypes_review_host_ip; Type: INDEX; Schema: zabbix_mac; Owner: -
--

CREATE INDEX idx_item_prototypes_review_host_ip ON zabbix_mac.item_prototypes_review USING btree (host_ip);


--
-- Name: idx_item_prototypes_review_prototype; Type: INDEX; Schema: zabbix_mac; Owner: -
--

CREATE INDEX idx_item_prototypes_review_prototype ON zabbix_mac.item_prototypes_review USING btree (item_prototype_id);


--
-- Name: item_prototypes_review item_prototypes_review_discovery_rule_id_fkey; Type: FK CONSTRAINT; Schema: zabbix_mac; Owner: -
--

ALTER TABLE ONLY zabbix_mac.item_prototypes_review
    ADD CONSTRAINT item_prototypes_review_discovery_rule_id_fkey FOREIGN KEY (discovery_rule_id) REFERENCES zabbix_mac.discovery_rules(id) ON DELETE CASCADE;


--
-- Name: item_prototypes_review item_prototypes_review_item_prototype_id_fkey; Type: FK CONSTRAINT; Schema: zabbix_mac; Owner: -
--

ALTER TABLE ONLY zabbix_mac.item_prototypes_review
    ADD CONSTRAINT item_prototypes_review_item_prototype_id_fkey FOREIGN KEY (item_prototype_id) REFERENCES zabbix_mac.item_prototypes(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict kR9SC7cO79M3FwNF64rF56N9U7yj0ksTKIXT4ssilAhPsKyEatDRzQczOqvTdeg

