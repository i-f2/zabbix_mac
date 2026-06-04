--
-- PostgreSQL database dump
--

\restrict 3HZLcSWXpUAObJhtaG24V8Nim9EikgBO2lpHzjNlANde7bmbiW2AkdNBZDv2pFw

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
-- Name: item_prototypes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.item_prototypes (
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
-- Name: item_prototypes_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.item_prototypes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: item_prototypes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.item_prototypes_id_seq OWNED BY public.item_prototypes.id;


--
-- Name: item_prototypes id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.item_prototypes ALTER COLUMN id SET DEFAULT nextval('public.item_prototypes_id_seq'::regclass);


--
-- Data for Name: item_prototypes; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.item_prototypes (id, discovery_rule_id, name, key, value_type, delay, description, units, multiplier, delta, history, trends, status, created_at, updated_at) FROM stdin;
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
-- Name: item_prototypes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.item_prototypes_id_seq', 13, true);


--
-- Name: item_prototypes item_prototypes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.item_prototypes
    ADD CONSTRAINT item_prototypes_pkey PRIMARY KEY (id);


--
-- Name: idx_item_prototypes_rule; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_item_prototypes_rule ON public.item_prototypes USING btree (discovery_rule_id);


--
-- Name: item_prototypes item_prototypes_discovery_rule_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.item_prototypes
    ADD CONSTRAINT item_prototypes_discovery_rule_id_fkey FOREIGN KEY (discovery_rule_id) REFERENCES public.discovery_rules(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict 3HZLcSWXpUAObJhtaG24V8Nim9EikgBO2lpHzjNlANde7bmbiW2AkdNBZDv2pFw

