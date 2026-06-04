--
-- PostgreSQL database dump
--

\restrict ah750O6btA1gxv4vHqn7gzmEfVuJEAyF1xCEFyZIvX1dw6nIY8r7OuXxggxl4RD

-- Dumped from database version 14.22
-- Dumped by pg_dump version 14.22

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'SQL_ASCII';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: trigger_prototypes_review; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.trigger_prototypes_review (
    id integer NOT NULL,
    trigger_prototype_id integer NOT NULL,
    discovery_rule_id integer NOT NULL,
    description text NOT NULL,
    expression text NOT NULL,
    priority integer NOT NULL,
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
-- Name: trigger_prototypes_review_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.trigger_prototypes_review_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: trigger_prototypes_review_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.trigger_prototypes_review_id_seq OWNED BY public.trigger_prototypes_review.id;


--
-- Name: trigger_prototypes_review id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trigger_prototypes_review ALTER COLUMN id SET DEFAULT nextval('public.trigger_prototypes_review_id_seq'::regclass);


--
-- Data for Name: trigger_prototypes_review; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.trigger_prototypes_review (id, trigger_prototype_id, discovery_rule_id, description, expression, priority, status, modified, confirmed, status_verification, created_at, updated_at, host_ip, system, subsystem) FROM stdin;
56	1	1	{#DEVNAME}: Disk read/write request responses are too high (read > 20 ms for 15m or write > 20 ms for 15m)	{host:vfs.dev.read.await[{#DEVNAME}].min(15m)} > 20 or {host:vfs.dev.write.await[{#DEVNAME}].min(15m)} > 20	3	0	f	f	pending	2026-04-30 17:26:59.904407	2026-04-30 17:26:59.904407	Zabbix server	上市系统	上市日常监管模块
57	2	2	{#FSNAME}: Running out of free inodes (free < 10%)	{host:vfs.fs.inode[{#FSNAME},pfree].min(5m)}<10	3	0	f	f	pending	2026-04-30 17:26:59.904407	2026-04-30 17:26:59.904407	Zabbix server	上市系统	上市日常监管模块
58	3	2	{#FSNAME}: Running out of free inodes (free < 20%)	{host:vfs.fs.inode[{#FSNAME},pfree].min(5m)}<20	2	0	f	f	pending	2026-04-30 17:26:59.904407	2026-04-30 17:26:59.904407	Zabbix server	上市系统	上市日常监管模块
59	4	2	{#FSNAME}: Disk space is critically low (used > 90%)	{host:vfs.fs.size[{#FSNAME},pused].last()}>90 and (({host:vfs.fs.size[{#FSNAME},total].last()}-{host:vfs.fs.size[{#FSNAME},used].last()})<5G or {host:vfs.fs.size[{#FSNAME},pused].timeleft(1h,,100)}<1d)	3	0	f	f	pending	2026-04-30 17:26:59.904407	2026-04-30 17:26:59.904407	Zabbix server	上市系统	上市日常监管模块
60	5	2	{#FSNAME}: Disk space is low (used > 80%)	{host:vfs.fs.size[{#FSNAME},pused].last()}>80 and (({host:vfs.fs.size[{#FSNAME},total].last()}-{host:vfs.fs.size[{#FSNAME},used].last()})<10G or {host:vfs.fs.size[{#FSNAME},pused].timeleft(1h,,100)}<1d)	2	0	f	f	pending	2026-04-30 17:26:59.904407	2026-04-30 17:26:59.904407	Zabbix server	上市系统	上市日常监管模块
61	1	1	{#DEVNAME}: Disk read/write request responses are too high (read > 20 ms for 15m or write > 20 ms for 15m)	{host:vfs.dev.read.await[{#DEVNAME}].min(15m)} > 20 or {host:vfs.dev.write.await[{#DEVNAME}].min(15m)} > 20	3	0	f	f	pending	2026-04-30 17:26:59.904407	2026-04-30 17:26:59.904407	10.24.3.12	上市系统	上市日常监管模块
62	2	2	{#FSNAME}: Running out of free inodes (free < 10%)	{host:vfs.fs.inode[{#FSNAME},pfree].min(5m)}<10	3	0	f	f	pending	2026-04-30 17:26:59.904407	2026-04-30 17:26:59.904407	10.24.3.12	上市系统	上市日常监管模块
63	3	2	{#FSNAME}: Running out of free inodes (free < 20%)	{host:vfs.fs.inode[{#FSNAME},pfree].min(5m)}<20	2	0	f	f	pending	2026-04-30 17:26:59.904407	2026-04-30 17:26:59.904407	10.24.3.12	上市系统	上市日常监管模块
64	4	2	{#FSNAME}: Disk space is critically low (used > 90%)	{host:vfs.fs.size[{#FSNAME},pused].last()}>90 and (({host:vfs.fs.size[{#FSNAME},total].last()}-{host:vfs.fs.size[{#FSNAME},used].last()})<5G or {host:vfs.fs.size[{#FSNAME},pused].timeleft(1h,,100)}<1d)	3	0	f	f	pending	2026-04-30 17:26:59.904407	2026-04-30 17:26:59.904407	10.24.3.12	上市系统	上市日常监管模块
65	5	2	{#FSNAME}: Disk space is low (used > 80%)	{host:vfs.fs.size[{#FSNAME},pused].last()}>80 and (({host:vfs.fs.size[{#FSNAME},total].last()}-{host:vfs.fs.size[{#FSNAME},used].last()})<10G or {host:vfs.fs.size[{#FSNAME},pused].timeleft(1h,,100)}<1d)	2	0	f	f	pending	2026-04-30 17:26:59.904407	2026-04-30 17:26:59.904407	10.24.3.12	上市系统	上市日常监管模块
66	1	1	{#DEVNAME}: Disk read/write request responses are too high (read > 20 ms for 15m or write > 20 ms for 15m)	{host:vfs.dev.read.await[{#DEVNAME}].min(15m)} > 20 or {host:vfs.dev.write.await[{#DEVNAME}].min(15m)} > 20	3	0	f	f	pending	2026-04-30 17:26:59.904407	2026-04-30 17:26:59.904407	10.24.3.23	上市系统	上市日常监管模块
67	2	2	{#FSNAME}: Running out of free inodes (free < 10%)	{host:vfs.fs.inode[{#FSNAME},pfree].min(5m)}<10	3	0	f	f	pending	2026-04-30 17:26:59.904407	2026-04-30 17:26:59.904407	10.24.3.23	上市系统	上市日常监管模块
68	3	2	{#FSNAME}: Running out of free inodes (free < 20%)	{host:vfs.fs.inode[{#FSNAME},pfree].min(5m)}<20	2	0	f	f	pending	2026-04-30 17:26:59.904407	2026-04-30 17:26:59.904407	10.24.3.23	上市系统	上市日常监管模块
69	4	2	{#FSNAME}: Disk space is critically low (used > 90%)	{host:vfs.fs.size[{#FSNAME},pused].last()}>90 and (({host:vfs.fs.size[{#FSNAME},total].last()}-{host:vfs.fs.size[{#FSNAME},used].last()})<5G or {host:vfs.fs.size[{#FSNAME},pused].timeleft(1h,,100)}<1d)	3	0	f	f	pending	2026-04-30 17:26:59.904407	2026-04-30 17:26:59.904407	10.24.3.23	上市系统	上市日常监管模块
70	5	2	{#FSNAME}: Disk space is low (used > 80%)	{host:vfs.fs.size[{#FSNAME},pused].last()}>80 and (({host:vfs.fs.size[{#FSNAME},total].last()}-{host:vfs.fs.size[{#FSNAME},used].last()})<10G or {host:vfs.fs.size[{#FSNAME},pused].timeleft(1h,,100)}<1d)	2	0	f	f	pending	2026-04-30 17:26:59.904407	2026-04-30 17:26:59.904407	10.24.3.23	上市系统	上市日常监管模块
\.


--
-- Name: trigger_prototypes_review_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.trigger_prototypes_review_id_seq', 70, true);


--
-- Name: trigger_prototypes_review trigger_prototypes_review_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trigger_prototypes_review
    ADD CONSTRAINT trigger_prototypes_review_pkey PRIMARY KEY (id);


--
-- Name: idx_trigger_prototypes_review_confirmed; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_trigger_prototypes_review_confirmed ON public.trigger_prototypes_review USING btree (confirmed);


--
-- Name: idx_trigger_prototypes_review_host_ip; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_trigger_prototypes_review_host_ip ON public.trigger_prototypes_review USING btree (host_ip);


--
-- Name: idx_trigger_prototypes_review_prototype; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_trigger_prototypes_review_prototype ON public.trigger_prototypes_review USING btree (trigger_prototype_id);


--
-- Name: trigger_prototypes_review trigger_prototypes_review_discovery_rule_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trigger_prototypes_review
    ADD CONSTRAINT trigger_prototypes_review_discovery_rule_id_fkey FOREIGN KEY (discovery_rule_id) REFERENCES public.discovery_rules(id) ON DELETE CASCADE;


--
-- Name: trigger_prototypes_review trigger_prototypes_review_trigger_prototype_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trigger_prototypes_review
    ADD CONSTRAINT trigger_prototypes_review_trigger_prototype_id_fkey FOREIGN KEY (trigger_prototype_id) REFERENCES public.trigger_prototypes(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict ah750O6btA1gxv4vHqn7gzmEfVuJEAyF1xCEFyZIvX1dw6nIY8r7OuXxggxl4RD

