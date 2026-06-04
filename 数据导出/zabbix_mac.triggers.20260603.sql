--
-- PostgreSQL database dump
--

\restrict Sc5QLQIiIkEv0OYwM0Bu1aCkGCYaxfybQSLnGIHjSMLg8De0n7xCg14Ts9fxtyO

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
-- Name: triggers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.triggers (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    expression text NOT NULL,
    priority integer NOT NULL,
    description text,
    status integer DEFAULT 0,
    template_name character varying(255) NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    system character varying(255),
    subsystem character varying(255)
);


--
-- Name: triggers_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.triggers_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: triggers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.triggers_id_seq OWNED BY public.triggers.id;


--
-- Name: triggers id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.triggers ALTER COLUMN id SET DEFAULT nextval('public.triggers_id_seq'::regclass);


--
-- Data for Name: triggers; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.triggers (id, name, expression, priority, description, status, template_name, created_at, updated_at, system, subsystem) FROM stdin;
1	{HOST.NAME}_{HOST.IP} CPU使用率 (over 100% for 5m)	{host:system.cpu.util.last()}>100	3	\N	0	21001	2026-04-17 09:02:07.059233	2026-04-17 09:02:07.059233	上市系统	上市日常监管模块
2	{HOST.NAME}_{HOST.IP} Configured max number of open filedescriptors is too low (< 256)	{host:kernel.maxfiles.last()}<256	1	\N	0	21001	2026-04-17 09:02:07.059233	2026-04-17 09:02:07.059233	上市系统	上市日常监管模块
4	{HOST.NAME}_{HOST.IP} System name has changed (new name: {ITEM.VALUE})	{host:system.hostname.diff()}=1 and {host:system.hostname.strlen()}>0	1	\N	0	21001	2026-04-17 09:02:07.059233	2026-04-17 09:02:07.059233	上市系统	上市日常监管模块
17	{HOST.NAME}_{HOST.IP} CPU负载单核已满载 (per CPU load over 1 for 5m)	{host:system.cpu.load[all,avg1].min(5m)}/{host:system.cpu.num.last()}>1 and {host:system.cpu.load[all,avg5].last()}>0 and {host:system.cpu.load[all,avg15].last()}>0	0		0	21001	2026-04-29 18:05:22.699039	2026-04-29 18:05:22.699039	上市系统	上市日常监管模块
13	{HOST.NAME}_{HOST.IP} has been restarted (uptime < 10m)	{host:system.uptime.last()}<10m	2		0	21001	2026-04-29 17:34:16.347324	2026-04-29 17:34:16.347324	上市系统	上市日常监管模块
16	{HOST.NAME}_{HOST.IP} CPU使用率 (over 60% for 5m)	{host:system.cpu.util.min(5m)}>60	0		0	21001	2026-04-29 18:02:21.489376	2026-04-29 18:02:21.489376	上市系统	上市日常监管模块
15	{HOST.NAME}_{HOST.IP} CPU使用率 (over 80% for 5m)	{host:system.cpu.util.min(5m)}>80	1		0	21001	2026-04-29 18:01:16.877681	2026-04-29 18:01:16.877681	上市系统	上市日常监管模块
14	{HOST.NAME}_{HOST.IP} 内存使用率 (>80% for 5m)	{host:vm.memory.utilization.min(5m)}>80	1		0	21001	2026-04-29 17:54:36.558982	2026-04-29 17:54:36.558982	上市系统	上市日常监管模块
7	{HOST.NAME}_{HOST.IP} 内存使用率 (>90% for 5m)	{host:vm.memory.utilization.min(5m)}>90	3		0	21001	2026-04-29 17:17:17.83902	2026-04-29 17:17:17.83902	上市系统	上市日常监管模块
9	{HOST.NAME}_{HOST.IP} 可用内存 (<20M of {ITEM.VALUE2})	{host:vm.memory.size[available].max(5m)}<20M and {host:vm.memory.size[total].last()}>0	3		0	21001	2026-04-29 17:22:13.614714	2026-04-29 17:22:13.614714	上市系统	上市日常监管模块
10	{HOST.NAME}_{HOST.IP} Operating system description has changed	{host:system.sw.os.diff()}=1 and {host:system.sw.os.strlen()}>0	1		0	21001	2026-04-29 17:29:59.275176	2026-04-29 17:29:59.275176	上市系统	上市日常监管模块
11	{HOST.NAME}_{HOST.IP} System time is out of sync (diff with Zabbix server > 60s)	{host:system.localtime.fuzzytime(60)}=0	2		0	21001	2026-04-29 17:31:50.761174	2026-04-29 17:31:50.761174	上市系统	上市日常监管模块
8	{HOST.NAME}_{HOST.IP} High swap space usage (less than 50% free)	{host:system.swap.size[,pfree].max(5m)}<50 and {host:system.swap.size[,total].last()}>0	2		0	21001	2026-04-29 17:18:52.789115	2026-04-29 17:18:52.789115	上市系统	上市日常监管模块
6	{HOST.NAME}_{HOST.IP} Getting closer to process limit (over 80% used)	{host:proc.num.last()}/{host:kernel.maxproc.last()}*100>80	1		0	21001	2026-04-29 17:16:12.280037	2026-04-29 17:16:12.280037	上市系统	上市日常监管模块
5	{HOST.NAME}_{HOST.IP} /etc/passwd has been changed	{host:vfs.file.cksum[/etc/passwd].diff()}>0	1		0	21001	2026-04-29 17:14:24.26742	2026-04-29 17:14:24.26742	上市系统	上市日常监管模块
12	{HOST.NAME}_{HOST.IP}Zabbix agent is not available (for 3m)	{host:zabbix[host,agent,available].max(3m)}=0	3		0	21001	2026-04-29 17:33:32.516352	2026-04-29 17:33:32.516352	上市系统	上市日常监管模块
3	{HOST.NAME}_{HOST.IP} Configured max number of processes is too low (< 1024)	{host:kernel.maxproc.last()}<1024	1	None	0	21001	2026-04-17 09:02:07.059233	2026-04-17 09:02:07.059233	上市系统	上市日常监管模块
\.


--
-- Name: triggers_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.triggers_id_seq', 17, true);


--
-- Name: triggers triggers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.triggers
    ADD CONSTRAINT triggers_pkey PRIMARY KEY (id);


--
-- Name: idx_triggers_template; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_triggers_template ON public.triggers USING btree (template_name);


--
-- PostgreSQL database dump complete
--

\unrestrict Sc5QLQIiIkEv0OYwM0Bu1aCkGCYaxfybQSLnGIHjSMLg8De0n7xCg14Ts9fxtyO

