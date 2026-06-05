--
-- PostgreSQL database dump
--

\restrict D8qaLtExJaxmpDgg6fxYf7ZvR3o2wqyXwrp20mPGSnlWOS9aPvCLIZyHukn6YKl

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
-- Name: triggers_review; Type: TABLE; Schema: zabbix_mac; Owner: -
--

CREATE TABLE zabbix_mac.triggers_review (
    id integer NOT NULL,
    trigger_id integer NOT NULL,
    name character varying(255) NOT NULL,
    expression text NOT NULL,
    priority integer NOT NULL,
    description text,
    status integer DEFAULT 0,
    template_name character varying(255) NOT NULL,
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
-- Name: triggers_review_id_seq; Type: SEQUENCE; Schema: zabbix_mac; Owner: -
--

CREATE SEQUENCE zabbix_mac.triggers_review_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: triggers_review_id_seq; Type: SEQUENCE OWNED BY; Schema: zabbix_mac; Owner: -
--

ALTER SEQUENCE zabbix_mac.triggers_review_id_seq OWNED BY zabbix_mac.triggers_review.id;


--
-- Name: triggers_review id; Type: DEFAULT; Schema: zabbix_mac; Owner: -
--

ALTER TABLE ONLY zabbix_mac.triggers_review ALTER COLUMN id SET DEFAULT nextval('zabbix_mac.triggers_review_id_seq'::regclass);


--
-- Data for Name: triggers_review; Type: TABLE DATA; Schema: zabbix_mac; Owner: -
--

COPY zabbix_mac.triggers_review (id, trigger_id, name, expression, priority, description, status, template_name, modified, confirmed, status_verification, created_at, updated_at, host_ip, system, subsystem) FROM stdin;
245	1	{HOST.NAME}_{HOST.IP} CPU使用率 (over 100% for 5m)	{host:system.cpu.util.last()}>100	3	\N	0	21001	f	f	pending	2026-04-30 17:26:59.886658	2026-04-30 17:26:59.886658	Zabbix server	上市系统	上市日常监管模块
246	2	{HOST.NAME}_{HOST.IP} Configured max number of open filedescriptors is too low (< 256)	{host:kernel.maxfiles.last()}<256	1	\N	0	21001	f	f	pending	2026-04-30 17:26:59.886658	2026-04-30 17:26:59.886658	Zabbix server	上市系统	上市日常监管模块
247	4	{HOST.NAME}_{HOST.IP} System name has changed (new name: {ITEM.VALUE})	{host:system.hostname.diff()}=1 and {host:system.hostname.strlen()}>0	1	\N	0	21001	f	f	pending	2026-04-30 17:26:59.886658	2026-04-30 17:26:59.886658	Zabbix server	上市系统	上市日常监管模块
248	17	{HOST.NAME}_{HOST.IP} CPU负载单核已满载 (per CPU load over 1 for 5m)	{host:system.cpu.load[all,avg1].min(5m)}/{host:system.cpu.num.last()}>1 and {host:system.cpu.load[all,avg5].last()}>0 and {host:system.cpu.load[all,avg15].last()}>0	0		0	21001	f	f	pending	2026-04-30 17:26:59.886658	2026-04-30 17:26:59.886658	Zabbix server	上市系统	上市日常监管模块
249	13	{HOST.NAME}_{HOST.IP} has been restarted (uptime < 10m)	{host:system.uptime.last()}<10m	2		0	21001	f	f	pending	2026-04-30 17:26:59.886658	2026-04-30 17:26:59.886658	Zabbix server	上市系统	上市日常监管模块
250	16	{HOST.NAME}_{HOST.IP} CPU使用率 (over 60% for 5m)	{host:system.cpu.util.min(5m)}>60	0		0	21001	f	f	pending	2026-04-30 17:26:59.886658	2026-04-30 17:26:59.886658	Zabbix server	上市系统	上市日常监管模块
251	15	{HOST.NAME}_{HOST.IP} CPU使用率 (over 80% for 5m)	{host:system.cpu.util.min(5m)}>80	1		0	21001	f	f	pending	2026-04-30 17:26:59.886658	2026-04-30 17:26:59.886658	Zabbix server	上市系统	上市日常监管模块
252	14	{HOST.NAME}_{HOST.IP} 内存使用率 (>80% for 5m)	{host:vm.memory.utilization.min(5m)}>80	1		0	21001	f	f	pending	2026-04-30 17:26:59.886658	2026-04-30 17:26:59.886658	Zabbix server	上市系统	上市日常监管模块
253	7	{HOST.NAME}_{HOST.IP} 内存使用率 (>90% for 5m)	{host:vm.memory.utilization.min(5m)}>90	3		0	21001	f	f	pending	2026-04-30 17:26:59.886658	2026-04-30 17:26:59.886658	Zabbix server	上市系统	上市日常监管模块
254	9	{HOST.NAME}_{HOST.IP} 可用内存 (<20M of {ITEM.VALUE2})	{host:vm.memory.size[available].max(5m)}<20M and {host:vm.memory.size[total].last()}>0	3		0	21001	f	f	pending	2026-04-30 17:26:59.886658	2026-04-30 17:26:59.886658	Zabbix server	上市系统	上市日常监管模块
255	10	{HOST.NAME}_{HOST.IP} Operating system description has changed	{host:system.sw.os.diff()}=1 and {host:system.sw.os.strlen()}>0	1		0	21001	f	f	pending	2026-04-30 17:26:59.886658	2026-04-30 17:26:59.886658	Zabbix server	上市系统	上市日常监管模块
256	11	{HOST.NAME}_{HOST.IP} System time is out of sync (diff with Zabbix server > 60s)	{host:system.localtime.fuzzytime(60)}=0	2		0	21001	f	f	pending	2026-04-30 17:26:59.886658	2026-04-30 17:26:59.886658	Zabbix server	上市系统	上市日常监管模块
257	8	{HOST.NAME}_{HOST.IP} High swap space usage (less than 50% free)	{host:system.swap.size[,pfree].max(5m)}<50 and {host:system.swap.size[,total].last()}>0	2		0	21001	f	f	pending	2026-04-30 17:26:59.886658	2026-04-30 17:26:59.886658	Zabbix server	上市系统	上市日常监管模块
258	6	{HOST.NAME}_{HOST.IP} Getting closer to process limit (over 80% used)	{host:proc.num.last()}/{host:kernel.maxproc.last()}*100>80	1		0	21001	f	f	pending	2026-04-30 17:26:59.886658	2026-04-30 17:26:59.886658	Zabbix server	上市系统	上市日常监管模块
259	5	{HOST.NAME}_{HOST.IP} /etc/passwd has been changed	{host:vfs.file.cksum[/etc/passwd].diff()}>0	1		0	21001	f	f	pending	2026-04-30 17:26:59.886658	2026-04-30 17:26:59.886658	Zabbix server	上市系统	上市日常监管模块
260	12	{HOST.NAME}_{HOST.IP}Zabbix agent is not available (for 3m)	{host:zabbix[host,agent,available].max(3m)}=0	3		0	21001	f	f	pending	2026-04-30 17:26:59.886658	2026-04-30 17:26:59.886658	Zabbix server	上市系统	上市日常监管模块
261	3	{HOST.NAME}_{HOST.IP} Configured max number of processes is too low (< 1024)	{host:kernel.maxproc.last()}<1024	1	None	0	21001	f	f	pending	2026-04-30 17:26:59.886658	2026-04-30 17:26:59.886658	Zabbix server	上市系统	上市日常监管模块
262	1	{HOST.NAME}_{HOST.IP} CPU使用率 (over 100% for 5m)	{host:system.cpu.util.last()}>100	3	\N	0	21001	f	f	pending	2026-04-30 17:26:59.886658	2026-04-30 17:26:59.886658	10.24.3.12	上市系统	上市日常监管模块
263	2	{HOST.NAME}_{HOST.IP} Configured max number of open filedescriptors is too low (< 256)	{host:kernel.maxfiles.last()}<256	1	\N	0	21001	f	f	pending	2026-04-30 17:26:59.886658	2026-04-30 17:26:59.886658	10.24.3.12	上市系统	上市日常监管模块
264	4	{HOST.NAME}_{HOST.IP} System name has changed (new name: {ITEM.VALUE})	{host:system.hostname.diff()}=1 and {host:system.hostname.strlen()}>0	1	\N	0	21001	f	f	pending	2026-04-30 17:26:59.886658	2026-04-30 17:26:59.886658	10.24.3.12	上市系统	上市日常监管模块
265	17	{HOST.NAME}_{HOST.IP} CPU负载单核已满载 (per CPU load over 1 for 5m)	{host:system.cpu.load[all,avg1].min(5m)}/{host:system.cpu.num.last()}>1 and {host:system.cpu.load[all,avg5].last()}>0 and {host:system.cpu.load[all,avg15].last()}>0	0		0	21001	f	f	pending	2026-04-30 17:26:59.886658	2026-04-30 17:26:59.886658	10.24.3.12	上市系统	上市日常监管模块
266	13	{HOST.NAME}_{HOST.IP} has been restarted (uptime < 10m)	{host:system.uptime.last()}<10m	2		0	21001	f	f	pending	2026-04-30 17:26:59.886658	2026-04-30 17:26:59.886658	10.24.3.12	上市系统	上市日常监管模块
267	16	{HOST.NAME}_{HOST.IP} CPU使用率 (over 60% for 5m)	{host:system.cpu.util.min(5m)}>60	0		0	21001	f	f	pending	2026-04-30 17:26:59.886658	2026-04-30 17:26:59.886658	10.24.3.12	上市系统	上市日常监管模块
268	15	{HOST.NAME}_{HOST.IP} CPU使用率 (over 80% for 5m)	{host:system.cpu.util.min(5m)}>80	1		0	21001	f	f	pending	2026-04-30 17:26:59.886658	2026-04-30 17:26:59.886658	10.24.3.12	上市系统	上市日常监管模块
269	14	{HOST.NAME}_{HOST.IP} 内存使用率 (>80% for 5m)	{host:vm.memory.utilization.min(5m)}>80	1		0	21001	f	f	pending	2026-04-30 17:26:59.886658	2026-04-30 17:26:59.886658	10.24.3.12	上市系统	上市日常监管模块
270	7	{HOST.NAME}_{HOST.IP} 内存使用率 (>90% for 5m)	{host:vm.memory.utilization.min(5m)}>90	3		0	21001	f	f	pending	2026-04-30 17:26:59.886658	2026-04-30 17:26:59.886658	10.24.3.12	上市系统	上市日常监管模块
271	9	{HOST.NAME}_{HOST.IP} 可用内存 (<20M of {ITEM.VALUE2})	{host:vm.memory.size[available].max(5m)}<20M and {host:vm.memory.size[total].last()}>0	3		0	21001	f	f	pending	2026-04-30 17:26:59.886658	2026-04-30 17:26:59.886658	10.24.3.12	上市系统	上市日常监管模块
272	10	{HOST.NAME}_{HOST.IP} Operating system description has changed	{host:system.sw.os.diff()}=1 and {host:system.sw.os.strlen()}>0	1		0	21001	f	f	pending	2026-04-30 17:26:59.886658	2026-04-30 17:26:59.886658	10.24.3.12	上市系统	上市日常监管模块
273	11	{HOST.NAME}_{HOST.IP} System time is out of sync (diff with Zabbix server > 60s)	{host:system.localtime.fuzzytime(60)}=0	2		0	21001	f	f	pending	2026-04-30 17:26:59.886658	2026-04-30 17:26:59.886658	10.24.3.12	上市系统	上市日常监管模块
274	8	{HOST.NAME}_{HOST.IP} High swap space usage (less than 50% free)	{host:system.swap.size[,pfree].max(5m)}<50 and {host:system.swap.size[,total].last()}>0	2		0	21001	f	f	pending	2026-04-30 17:26:59.886658	2026-04-30 17:26:59.886658	10.24.3.12	上市系统	上市日常监管模块
275	6	{HOST.NAME}_{HOST.IP} Getting closer to process limit (over 80% used)	{host:proc.num.last()}/{host:kernel.maxproc.last()}*100>80	1		0	21001	f	f	pending	2026-04-30 17:26:59.886658	2026-04-30 17:26:59.886658	10.24.3.12	上市系统	上市日常监管模块
276	5	{HOST.NAME}_{HOST.IP} /etc/passwd has been changed	{host:vfs.file.cksum[/etc/passwd].diff()}>0	1		0	21001	f	f	pending	2026-04-30 17:26:59.886658	2026-04-30 17:26:59.886658	10.24.3.12	上市系统	上市日常监管模块
277	12	{HOST.NAME}_{HOST.IP}Zabbix agent is not available (for 3m)	{host:zabbix[host,agent,available].max(3m)}=0	3		0	21001	f	f	pending	2026-04-30 17:26:59.886658	2026-04-30 17:26:59.886658	10.24.3.12	上市系统	上市日常监管模块
278	3	{HOST.NAME}_{HOST.IP} Configured max number of processes is too low (< 1024)	{host:kernel.maxproc.last()}<1024	1	None	0	21001	f	f	pending	2026-04-30 17:26:59.886658	2026-04-30 17:26:59.886658	10.24.3.12	上市系统	上市日常监管模块
279	1	{HOST.NAME}_{HOST.IP} CPU使用率 (over 100% for 5m)	{host:system.cpu.util.last()}>100	3	\N	0	21001	f	f	pending	2026-04-30 17:26:59.886658	2026-04-30 17:26:59.886658	10.24.3.23	上市系统	上市日常监管模块
280	2	{HOST.NAME}_{HOST.IP} Configured max number of open filedescriptors is too low (< 256)	{host:kernel.maxfiles.last()}<256	1	\N	0	21001	f	f	pending	2026-04-30 17:26:59.886658	2026-04-30 17:26:59.886658	10.24.3.23	上市系统	上市日常监管模块
281	4	{HOST.NAME}_{HOST.IP} System name has changed (new name: {ITEM.VALUE})	{host:system.hostname.diff()}=1 and {host:system.hostname.strlen()}>0	1	\N	0	21001	f	f	pending	2026-04-30 17:26:59.886658	2026-04-30 17:26:59.886658	10.24.3.23	上市系统	上市日常监管模块
282	17	{HOST.NAME}_{HOST.IP} CPU负载单核已满载 (per CPU load over 1 for 5m)	{host:system.cpu.load[all,avg1].min(5m)}/{host:system.cpu.num.last()}>1 and {host:system.cpu.load[all,avg5].last()}>0 and {host:system.cpu.load[all,avg15].last()}>0	0		0	21001	f	f	pending	2026-04-30 17:26:59.886658	2026-04-30 17:26:59.886658	10.24.3.23	上市系统	上市日常监管模块
283	13	{HOST.NAME}_{HOST.IP} has been restarted (uptime < 10m)	{host:system.uptime.last()}<10m	2		0	21001	f	f	pending	2026-04-30 17:26:59.886658	2026-04-30 17:26:59.886658	10.24.3.23	上市系统	上市日常监管模块
284	16	{HOST.NAME}_{HOST.IP} CPU使用率 (over 60% for 5m)	{host:system.cpu.util.min(5m)}>60	0		0	21001	f	f	pending	2026-04-30 17:26:59.886658	2026-04-30 17:26:59.886658	10.24.3.23	上市系统	上市日常监管模块
285	15	{HOST.NAME}_{HOST.IP} CPU使用率 (over 80% for 5m)	{host:system.cpu.util.min(5m)}>80	1		0	21001	f	f	pending	2026-04-30 17:26:59.886658	2026-04-30 17:26:59.886658	10.24.3.23	上市系统	上市日常监管模块
286	14	{HOST.NAME}_{HOST.IP} 内存使用率 (>80% for 5m)	{host:vm.memory.utilization.min(5m)}>80	1		0	21001	f	f	pending	2026-04-30 17:26:59.886658	2026-04-30 17:26:59.886658	10.24.3.23	上市系统	上市日常监管模块
287	7	{HOST.NAME}_{HOST.IP} 内存使用率 (>90% for 5m)	{host:vm.memory.utilization.min(5m)}>90	3		0	21001	f	f	pending	2026-04-30 17:26:59.886658	2026-04-30 17:26:59.886658	10.24.3.23	上市系统	上市日常监管模块
288	9	{HOST.NAME}_{HOST.IP} 可用内存 (<20M of {ITEM.VALUE2})	{host:vm.memory.size[available].max(5m)}<20M and {host:vm.memory.size[total].last()}>0	3		0	21001	f	f	pending	2026-04-30 17:26:59.886658	2026-04-30 17:26:59.886658	10.24.3.23	上市系统	上市日常监管模块
289	10	{HOST.NAME}_{HOST.IP} Operating system description has changed	{host:system.sw.os.diff()}=1 and {host:system.sw.os.strlen()}>0	1		0	21001	f	f	pending	2026-04-30 17:26:59.886658	2026-04-30 17:26:59.886658	10.24.3.23	上市系统	上市日常监管模块
290	11	{HOST.NAME}_{HOST.IP} System time is out of sync (diff with Zabbix server > 60s)	{host:system.localtime.fuzzytime(60)}=0	2		0	21001	f	f	pending	2026-04-30 17:26:59.886658	2026-04-30 17:26:59.886658	10.24.3.23	上市系统	上市日常监管模块
291	8	{HOST.NAME}_{HOST.IP} High swap space usage (less than 50% free)	{host:system.swap.size[,pfree].max(5m)}<50 and {host:system.swap.size[,total].last()}>0	2		0	21001	f	f	pending	2026-04-30 17:26:59.886658	2026-04-30 17:26:59.886658	10.24.3.23	上市系统	上市日常监管模块
292	6	{HOST.NAME}_{HOST.IP} Getting closer to process limit (over 80% used)	{host:proc.num.last()}/{host:kernel.maxproc.last()}*100>80	1		0	21001	f	f	pending	2026-04-30 17:26:59.886658	2026-04-30 17:26:59.886658	10.24.3.23	上市系统	上市日常监管模块
293	5	{HOST.NAME}_{HOST.IP} /etc/passwd has been changed	{host:vfs.file.cksum[/etc/passwd].diff()}>0	1		0	21001	f	f	pending	2026-04-30 17:26:59.886658	2026-04-30 17:26:59.886658	10.24.3.23	上市系统	上市日常监管模块
294	12	{HOST.NAME}_{HOST.IP}Zabbix agent is not available (for 3m)	{host:zabbix[host,agent,available].max(3m)}=0	3		0	21001	f	f	pending	2026-04-30 17:26:59.886658	2026-04-30 17:26:59.886658	10.24.3.23	上市系统	上市日常监管模块
295	3	{HOST.NAME}_{HOST.IP} Configured max number of processes is too low (< 1024)	{host:kernel.maxproc.last()}<1024	1	None	0	21001	f	f	pending	2026-04-30 17:26:59.886658	2026-04-30 17:26:59.886658	10.24.3.23	上市系统	上市日常监管模块
\.


--
-- Name: triggers_review_id_seq; Type: SEQUENCE SET; Schema: zabbix_mac; Owner: -
--

SELECT pg_catalog.setval('zabbix_mac.triggers_review_id_seq', 295, true);


--
-- Name: triggers_review triggers_review_pkey; Type: CONSTRAINT; Schema: zabbix_mac; Owner: -
--

ALTER TABLE ONLY zabbix_mac.triggers_review
    ADD CONSTRAINT triggers_review_pkey PRIMARY KEY (id);


--
-- Name: idx_triggers_review_confirmed; Type: INDEX; Schema: zabbix_mac; Owner: -
--

CREATE INDEX idx_triggers_review_confirmed ON zabbix_mac.triggers_review USING btree (confirmed);


--
-- Name: idx_triggers_review_host_ip; Type: INDEX; Schema: zabbix_mac; Owner: -
--

CREATE INDEX idx_triggers_review_host_ip ON zabbix_mac.triggers_review USING btree (host_ip);


--
-- Name: idx_triggers_review_trigger; Type: INDEX; Schema: zabbix_mac; Owner: -
--

CREATE INDEX idx_triggers_review_trigger ON zabbix_mac.triggers_review USING btree (trigger_id);


--
-- PostgreSQL database dump complete
--

\unrestrict D8qaLtExJaxmpDgg6fxYf7ZvR3o2wqyXwrp20mPGSnlWOS9aPvCLIZyHukn6YKl

