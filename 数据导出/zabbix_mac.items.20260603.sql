--
-- PostgreSQL database dump
--

\restrict IrRzZ7kK5LLX2baRC9KSR5Q1gJf947j0FbaAzGhwSMMuJ6c4AQZV4GySDUThm8s

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
-- Name: items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.items (
    id integer NOT NULL,
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
    template_name character varying(255) NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    master_item character varying(255),
    preprocessing jsonb
);


--
-- Name: items_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.items_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: items_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.items_id_seq OWNED BY public.items.id;


--
-- Name: items id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.items ALTER COLUMN id SET DEFAULT nextval('public.items_id_seq'::regclass);


--
-- Data for Name: items; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.items (id, item_key, name, type, value_type, delay, description, units, multiplier, delta, history, trends, status, template_name, created_at, updated_at, master_item, preprocessing) FROM stdin;
22	system.swap.size[,free]	Free swap space	0	3	1m		B	0	0	7	365	0	21001	2026-04-29 16:17:34.133078	2026-04-29 16:17:34.133078	\N	\N
24	system.swap.size[,total]	Total swap space	0	3	1m		B	0	0	7	365	0	21001	2026-04-29 16:20:27.054296	2026-04-29 16:20:27.054296	\N	\N
26	vm.memory.size[pavailable]	Available memory in %	0	0	1m		%	0	0	7	365	0	21001	2026-04-29 16:22:09.324243	2026-04-29 16:22:09.324243	\N	\N
37	system.sw.os	Operating system	0	1	1h			0	0	7	365	0	21001	2026-04-29 16:43:08.050444	2026-04-29 16:43:08.050444	\N	\N
39	system.uname	System description	0	1	15m			0	0	12	365	0	21001	2026-04-29 16:45:15.423314	2026-04-29 16:45:15.423314	\N	\N
41	system.users.num	Number of logged in users	0	3	1m			0	0	7	365	0	21001	2026-04-29 16:47:35.838108	2026-04-29 16:47:35.838108	\N	\N
28	vm.memory.utilization	Memory utilization	18	0	1m		%	0	0	7	365	0	21001	2026-04-29 16:24:59.421969	2026-04-29 16:24:59.421969	vm.memory.size[pavailable]	[{"type": "21", "params": "return (100-value);", "error_handler": "0", "error_handler_params": ""}]
7	system.cpu.load[all,avg15]	Load average (15m avg)	0	0	1m	\N	\N	0	0	7	365	0	21001	2026-04-17 09:02:07.059233	2026-04-17 09:02:07.059233	\N	\N
8	system.cpu.load[all,avg5]	Load average (5m avg)	0	0	1m	\N	\N	0	0	7	365	0	21001	2026-04-17 09:02:07.059233	2026-04-17 09:02:07.059233	\N	\N
1	agent.hostname	Host name of Zabbix agent running	0	1	1h			0	0	7	365	0	21001	2026-04-29 15:09:39.062209	2026-04-29 15:09:39.062209	\N	\N
2	agent.ping	Zabbix agent ping	0	0	1m			0	0	7	365	0	21001	2026-04-29 15:11:22.281085	2026-04-29 15:11:22.281085	\N	\N
23	system.swap.size[,pfree]	Free swap space in %	0	0	1m		%	0	0	7	365	0	21001	2026-04-29 16:18:16.05008	2026-04-29 16:18:16.05008	\N	\N
25	vm.memory.size[available]	Available memory	0	3	1m		B	0	0	7	365	0	21001	2026-04-29 16:21:27.423412	2026-04-29 16:21:27.423412	\N	\N
3	agent.version	Version of Zabbix agent running	0	1	1h			0	0	7	365	0	21001	2026-04-29 15:22:08.687299	2026-04-29 15:22:08.687299	\N	\N
27	vm.memory.size[total]	Total memory	0	3	1m		B	0	0	7	365	0	21001	2026-04-29 16:23:11.433385	2026-04-29 16:23:11.433385	\N	\N
4	zabbix[host,agent,available]	Zabbix agent availability	5	0	1m			0	0	7	365	0	21001	2026-04-29 15:25:23.620969	2026-04-29 15:25:23.620969	\N	\N
29	kernel.maxfiles	Maximum number of open file descriptors	0	3	1h			0	0	7	365	0	21001	2026-04-17 09:02:07.059233	2026-04-17 09:02:07.059233	\N	\N
5	system.cpu.intr	Interrupts per second	0	0	1m	\N	\N	0	0	7	365	0	21001	2026-04-17 09:02:07.059233	2026-04-17 09:02:07.059233	\N	\N
9	system.cpu.num	Number of CPUs	0	3	1m	\N	\N	0	0	7	365	0	21001	2026-04-17 09:02:07.059233	2026-04-17 09:02:07.059233	\N	\N
6	system.cpu.load[all,avg1]	Load average (1m avg)	0	0	1m			0	0	7	365	0	21001	2026-04-17 09:02:07.059233	2026-04-17 09:02:07.059233	\N	\N
10	system.cpu.switches	Context switches per second	0	0	1m	\N	\N	0	0	7	365	0	21001	2026-04-17 09:02:07.059233	2026-04-17 09:02:07.059233	\N	\N
11	system.cpu.util[,idle]	CPU idle time	0	0	1m	\N	\N	0	0	7	365	0	21001	2026-04-17 09:02:07.059233	2026-04-17 09:02:07.059233	\N	\N
13	system.cpu.util[,guest_nice]	CPU guest nice time	0	0	1m		%	0	0	7	365	0	21001	2026-04-17 09:02:07.059233	2026-04-17 09:02:07.059233	\N	\N
14	system.cpu.util[,guest]	CPU guest time	0	0	1m		%	0	0	7	365	0	21001	2026-04-17 09:02:07.059233	2026-04-17 09:02:07.059233	\N	\N
15	system.cpu.util[,interrupt]	CPU interrupt time	0	0	1m		%	0	0	7	365	0	21001	2026-04-17 09:02:07.059233	2026-04-17 09:02:07.059233	\N	\N
16	system.cpu.util[,iowait]	CPU iowait time	0	0	1m		%	0	0	7	365	0	21001	2026-04-17 09:02:07.059233	2026-04-17 09:02:07.059233	\N	\N
17	system.cpu.util[,nice]	CPU nice time	0	0	1m		%	0	0	7	365	0	21001	2026-04-17 09:02:07.059233	2026-04-17 09:02:07.059233	\N	\N
18	system.cpu.util[,softirq]	CPU softirq time	0	0	1m		%	0	0	7	365	0	21001	2026-04-17 09:02:07.059233	2026-04-17 09:02:07.059233	\N	\N
19	system.cpu.util[,steal]	CPU steal time	0	0	1m		%	0	0	7	365	0	21001	2026-04-17 09:02:07.059233	2026-04-17 09:02:07.059233	\N	\N
20	system.cpu.util[,system]	CPU system time	0	0	1m		%	0	0	7	365	0	21001	2026-04-17 09:02:07.059233	2026-04-17 09:02:07.059233	\N	\N
21	system.cpu.util[,user]	CPU user time	0	0	1m		%	0	0	7	365	0	21001	2026-04-17 09:02:07.059233	2026-04-17 09:02:07.059233	\N	\N
30	kernel.maxproc	Maximum number of processes	0	3	1h			0	0	7	365	0	21001	2026-04-17 09:02:07.059233	2026-04-17 09:02:07.059233	\N	\N
31	proc.num	Number of processes	0	3	1m			0	0	7	365	0	21001	2026-04-17 09:02:07.059233	2026-04-17 09:02:07.059233	\N	\N
32	proc.num[,,run]	Number of running processes	0	3	1m			0	0	7	365	0	21001	2026-04-17 09:02:07.059233	2026-04-17 09:02:07.059233	\N	\N
33	system.boottime	System boot time	0	3	15m		unixtime	0	0	7	365	0	21001	2026-04-17 09:02:07.059233	2026-04-17 09:02:07.059233	\N	\N
34	system.hostname	System name	0	1	1h			0	0	11	365	0	21001	2026-04-17 09:02:07.059233	2026-04-17 09:02:07.059233	\N	\N
35	system.localtime	System local time	0	3	1m		unixtime	0	0	7	365	0	21001	2026-04-17 09:02:07.059233	2026-04-17 09:02:07.059233	\N	\N
36	system.sw.arch	Operating system architecture	0	1	1h			0	0	7	365	0	21001	2026-04-29 16:36:33.697853	2026-04-29 16:36:33.697853	\N	\N
38	system.sw.packages	Software installed	0	4	1h			0	0	11	365	0	21001	2026-04-29 16:44:16.320316	2026-04-29 16:44:16.320316	\N	\N
40	system.uptime	System uptime	0	3	30s		uptime	0	0	14	365	0	21001	2026-04-29 16:46:51.128525	2026-04-29 16:46:51.128525	\N	\N
42	vfs.file.cksum[/etc/passwd]	Checksum of /etc/passwd	0	1	15m			0	0	7	365	0	21001	2026-04-29 16:48:35.950744	2026-04-29 16:48:35.950744	\N	\N
12	system.cpu.util	CPU utilization	18	0	1m		%	0	0	7	365	0	21001	2026-04-17 09:02:07.059233	2026-04-17 09:02:07.059233	system.cpu.util[,idle]	[{"type": "21", "params": "return (100 - value)", "error_handler": "0", "error_handler_params": ""}]
\.


--
-- Name: items_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.items_id_seq', 66, true);


--
-- Name: items items_item_key_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.items
    ADD CONSTRAINT items_item_key_key UNIQUE (item_key);


--
-- Name: items items_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.items
    ADD CONSTRAINT items_pkey PRIMARY KEY (id);


--
-- Name: idx_items_item_key; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_items_item_key ON public.items USING btree (item_key);


--
-- Name: idx_items_master_item; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_items_master_item ON public.items USING btree (master_item);


--
-- Name: idx_items_template; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_items_template ON public.items USING btree (template_name);


--
-- PostgreSQL database dump complete
--

\unrestrict IrRzZ7kK5LLX2baRC9KSR5Q1gJf947j0FbaAzGhwSMMuJ6c4AQZV4GySDUThm8s

