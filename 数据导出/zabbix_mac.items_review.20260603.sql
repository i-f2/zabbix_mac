--
-- PostgreSQL database dump
--

\restrict 2II1TylsBAiQBvDOO3YtjOOYlVDed1LkpW7Y906dvOztelSYUBGj68ktdDOixmX

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
-- Name: items_review; Type: TABLE; Schema: zabbix_mac; Owner: -
--

CREATE TABLE zabbix_mac.items_review (
    id integer NOT NULL,
    item_id integer NOT NULL,
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
    modified boolean DEFAULT false,
    confirmed boolean DEFAULT false,
    status_verification character varying(50) DEFAULT 'pending'::character varying,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    host_ip character varying(255) NOT NULL,
    master_item character varying(255),
    preprocessing jsonb,
    system character varying(100),
    subsystem character varying(100)
);


--
-- Name: items_review_id_seq; Type: SEQUENCE; Schema: zabbix_mac; Owner: -
--

CREATE SEQUENCE zabbix_mac.items_review_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: items_review_id_seq; Type: SEQUENCE OWNED BY; Schema: zabbix_mac; Owner: -
--

ALTER SEQUENCE zabbix_mac.items_review_id_seq OWNED BY zabbix_mac.items_review.id;


--
-- Name: items_review id; Type: DEFAULT; Schema: zabbix_mac; Owner: -
--

ALTER TABLE ONLY zabbix_mac.items_review ALTER COLUMN id SET DEFAULT nextval('zabbix_mac.items_review_id_seq'::regclass);


--
-- Data for Name: items_review; Type: TABLE DATA; Schema: zabbix_mac; Owner: -
--

COPY zabbix_mac.items_review (id, item_id, item_key, name, type, value_type, delay, description, units, multiplier, delta, history, trends, status, template_name, modified, confirmed, status_verification, created_at, updated_at, host_ip, master_item, preprocessing, system, subsystem) FROM stdin;
746	22	system.swap.size[,free]	Free swap space	0	3	1m		B	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	Zabbix server	\N	\N	上市系统	上市日常监管模块
747	24	system.swap.size[,total]	Total swap space	0	3	1m		B	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	Zabbix server	\N	\N	上市系统	上市日常监管模块
748	26	vm.memory.size[pavailable]	Available memory in %	0	0	1m		%	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	Zabbix server	\N	\N	上市系统	上市日常监管模块
749	37	system.sw.os	Operating system	0	1	1h			0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	Zabbix server	\N	\N	上市系统	上市日常监管模块
750	39	system.uname	System description	0	1	15m			0	0	12	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	Zabbix server	\N	\N	上市系统	上市日常监管模块
751	41	system.users.num	Number of logged in users	0	3	1m			0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	Zabbix server	\N	\N	上市系统	上市日常监管模块
752	28	vm.memory.utilization	Memory utilization	18	0	1m		%	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	Zabbix server	vm.memory.size[pavailable]	[{"type": "21", "params": "return (100-value);", "error_handler": "0", "error_handler_params": ""}]	上市系统	上市日常监管模块
753	7	system.cpu.load[all,avg15]	Load average (15m avg)	0	0	1m	\N	\N	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	Zabbix server	\N	\N	上市系统	上市日常监管模块
754	8	system.cpu.load[all,avg5]	Load average (5m avg)	0	0	1m	\N	\N	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	Zabbix server	\N	\N	上市系统	上市日常监管模块
755	1	agent.hostname	Host name of Zabbix agent running	0	1	1h			0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	Zabbix server	\N	\N	上市系统	上市日常监管模块
756	2	agent.ping	Zabbix agent ping	0	0	1m			0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	Zabbix server	\N	\N	上市系统	上市日常监管模块
757	23	system.swap.size[,pfree]	Free swap space in %	0	0	1m		%	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	Zabbix server	\N	\N	上市系统	上市日常监管模块
758	25	vm.memory.size[available]	Available memory	0	3	1m		B	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	Zabbix server	\N	\N	上市系统	上市日常监管模块
759	3	agent.version	Version of Zabbix agent running	0	1	1h			0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	Zabbix server	\N	\N	上市系统	上市日常监管模块
760	27	vm.memory.size[total]	Total memory	0	3	1m		B	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	Zabbix server	\N	\N	上市系统	上市日常监管模块
761	4	zabbix[host,agent,available]	Zabbix agent availability	5	0	1m			0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	Zabbix server	\N	\N	上市系统	上市日常监管模块
762	29	kernel.maxfiles	Maximum number of open file descriptors	0	3	1h			0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	Zabbix server	\N	\N	上市系统	上市日常监管模块
763	5	system.cpu.intr	Interrupts per second	0	0	1m	\N	\N	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	Zabbix server	\N	\N	上市系统	上市日常监管模块
764	9	system.cpu.num	Number of CPUs	0	3	1m	\N	\N	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	Zabbix server	\N	\N	上市系统	上市日常监管模块
765	6	system.cpu.load[all,avg1]	Load average (1m avg)	0	0	1m			0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	Zabbix server	\N	\N	上市系统	上市日常监管模块
766	10	system.cpu.switches	Context switches per second	0	0	1m	\N	\N	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	Zabbix server	\N	\N	上市系统	上市日常监管模块
767	11	system.cpu.util[,idle]	CPU idle time	0	0	1m	\N	\N	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	Zabbix server	\N	\N	上市系统	上市日常监管模块
768	13	system.cpu.util[,guest_nice]	CPU guest nice time	0	0	1m		%	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	Zabbix server	\N	\N	上市系统	上市日常监管模块
769	14	system.cpu.util[,guest]	CPU guest time	0	0	1m		%	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	Zabbix server	\N	\N	上市系统	上市日常监管模块
770	15	system.cpu.util[,interrupt]	CPU interrupt time	0	0	1m		%	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	Zabbix server	\N	\N	上市系统	上市日常监管模块
771	16	system.cpu.util[,iowait]	CPU iowait time	0	0	1m		%	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	Zabbix server	\N	\N	上市系统	上市日常监管模块
772	17	system.cpu.util[,nice]	CPU nice time	0	0	1m		%	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	Zabbix server	\N	\N	上市系统	上市日常监管模块
773	18	system.cpu.util[,softirq]	CPU softirq time	0	0	1m		%	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	Zabbix server	\N	\N	上市系统	上市日常监管模块
774	19	system.cpu.util[,steal]	CPU steal time	0	0	1m		%	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	Zabbix server	\N	\N	上市系统	上市日常监管模块
775	20	system.cpu.util[,system]	CPU system time	0	0	1m		%	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	Zabbix server	\N	\N	上市系统	上市日常监管模块
776	21	system.cpu.util[,user]	CPU user time	0	0	1m		%	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	Zabbix server	\N	\N	上市系统	上市日常监管模块
777	30	kernel.maxproc	Maximum number of processes	0	3	1h			0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	Zabbix server	\N	\N	上市系统	上市日常监管模块
778	31	proc.num	Number of processes	0	3	1m			0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	Zabbix server	\N	\N	上市系统	上市日常监管模块
779	32	proc.num[,,run]	Number of running processes	0	3	1m			0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	Zabbix server	\N	\N	上市系统	上市日常监管模块
780	33	system.boottime	System boot time	0	3	15m		unixtime	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	Zabbix server	\N	\N	上市系统	上市日常监管模块
781	34	system.hostname	System name	0	1	1h			0	0	11	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	Zabbix server	\N	\N	上市系统	上市日常监管模块
782	35	system.localtime	System local time	0	3	1m		unixtime	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	Zabbix server	\N	\N	上市系统	上市日常监管模块
783	36	system.sw.arch	Operating system architecture	0	1	1h			0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	Zabbix server	\N	\N	上市系统	上市日常监管模块
784	38	system.sw.packages	Software installed	0	4	1h			0	0	11	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	Zabbix server	\N	\N	上市系统	上市日常监管模块
785	40	system.uptime	System uptime	0	3	30s		uptime	0	0	14	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	Zabbix server	\N	\N	上市系统	上市日常监管模块
786	42	vfs.file.cksum[/etc/passwd]	Checksum of /etc/passwd	0	1	15m			0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	Zabbix server	\N	\N	上市系统	上市日常监管模块
787	12	system.cpu.util	CPU utilization	18	0	1m		%	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	Zabbix server	system.cpu.util[,idle]	[{"type": "21", "params": "return (100 - value)", "error_handler": "0", "error_handler_params": ""}]	上市系统	上市日常监管模块
788	22	system.swap.size[,free]	Free swap space	0	3	1m		B	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.12	\N	\N	上市系统	上市日常监管模块
789	24	system.swap.size[,total]	Total swap space	0	3	1m		B	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.12	\N	\N	上市系统	上市日常监管模块
790	26	vm.memory.size[pavailable]	Available memory in %	0	0	1m		%	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.12	\N	\N	上市系统	上市日常监管模块
791	37	system.sw.os	Operating system	0	1	1h			0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.12	\N	\N	上市系统	上市日常监管模块
792	39	system.uname	System description	0	1	15m			0	0	12	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.12	\N	\N	上市系统	上市日常监管模块
793	41	system.users.num	Number of logged in users	0	3	1m			0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.12	\N	\N	上市系统	上市日常监管模块
794	28	vm.memory.utilization	Memory utilization	18	0	1m		%	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.12	vm.memory.size[pavailable]	[{"type": "21", "params": "return (100-value);", "error_handler": "0", "error_handler_params": ""}]	上市系统	上市日常监管模块
795	7	system.cpu.load[all,avg15]	Load average (15m avg)	0	0	1m	\N	\N	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.12	\N	\N	上市系统	上市日常监管模块
796	8	system.cpu.load[all,avg5]	Load average (5m avg)	0	0	1m	\N	\N	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.12	\N	\N	上市系统	上市日常监管模块
797	1	agent.hostname	Host name of Zabbix agent running	0	1	1h			0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.12	\N	\N	上市系统	上市日常监管模块
798	2	agent.ping	Zabbix agent ping	0	0	1m			0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.12	\N	\N	上市系统	上市日常监管模块
799	23	system.swap.size[,pfree]	Free swap space in %	0	0	1m		%	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.12	\N	\N	上市系统	上市日常监管模块
800	25	vm.memory.size[available]	Available memory	0	3	1m		B	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.12	\N	\N	上市系统	上市日常监管模块
801	3	agent.version	Version of Zabbix agent running	0	1	1h			0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.12	\N	\N	上市系统	上市日常监管模块
802	27	vm.memory.size[total]	Total memory	0	3	1m		B	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.12	\N	\N	上市系统	上市日常监管模块
803	4	zabbix[host,agent,available]	Zabbix agent availability	5	0	1m			0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.12	\N	\N	上市系统	上市日常监管模块
804	29	kernel.maxfiles	Maximum number of open file descriptors	0	3	1h			0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.12	\N	\N	上市系统	上市日常监管模块
805	5	system.cpu.intr	Interrupts per second	0	0	1m	\N	\N	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.12	\N	\N	上市系统	上市日常监管模块
806	9	system.cpu.num	Number of CPUs	0	3	1m	\N	\N	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.12	\N	\N	上市系统	上市日常监管模块
807	6	system.cpu.load[all,avg1]	Load average (1m avg)	0	0	1m			0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.12	\N	\N	上市系统	上市日常监管模块
808	10	system.cpu.switches	Context switches per second	0	0	1m	\N	\N	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.12	\N	\N	上市系统	上市日常监管模块
809	11	system.cpu.util[,idle]	CPU idle time	0	0	1m	\N	\N	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.12	\N	\N	上市系统	上市日常监管模块
810	13	system.cpu.util[,guest_nice]	CPU guest nice time	0	0	1m		%	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.12	\N	\N	上市系统	上市日常监管模块
811	14	system.cpu.util[,guest]	CPU guest time	0	0	1m		%	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.12	\N	\N	上市系统	上市日常监管模块
812	15	system.cpu.util[,interrupt]	CPU interrupt time	0	0	1m		%	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.12	\N	\N	上市系统	上市日常监管模块
813	16	system.cpu.util[,iowait]	CPU iowait time	0	0	1m		%	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.12	\N	\N	上市系统	上市日常监管模块
814	17	system.cpu.util[,nice]	CPU nice time	0	0	1m		%	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.12	\N	\N	上市系统	上市日常监管模块
815	18	system.cpu.util[,softirq]	CPU softirq time	0	0	1m		%	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.12	\N	\N	上市系统	上市日常监管模块
816	19	system.cpu.util[,steal]	CPU steal time	0	0	1m		%	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.12	\N	\N	上市系统	上市日常监管模块
817	20	system.cpu.util[,system]	CPU system time	0	0	1m		%	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.12	\N	\N	上市系统	上市日常监管模块
818	21	system.cpu.util[,user]	CPU user time	0	0	1m		%	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.12	\N	\N	上市系统	上市日常监管模块
819	30	kernel.maxproc	Maximum number of processes	0	3	1h			0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.12	\N	\N	上市系统	上市日常监管模块
820	31	proc.num	Number of processes	0	3	1m			0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.12	\N	\N	上市系统	上市日常监管模块
821	32	proc.num[,,run]	Number of running processes	0	3	1m			0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.12	\N	\N	上市系统	上市日常监管模块
822	33	system.boottime	System boot time	0	3	15m		unixtime	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.12	\N	\N	上市系统	上市日常监管模块
823	34	system.hostname	System name	0	1	1h			0	0	11	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.12	\N	\N	上市系统	上市日常监管模块
824	35	system.localtime	System local time	0	3	1m		unixtime	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.12	\N	\N	上市系统	上市日常监管模块
825	36	system.sw.arch	Operating system architecture	0	1	1h			0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.12	\N	\N	上市系统	上市日常监管模块
826	38	system.sw.packages	Software installed	0	4	1h			0	0	11	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.12	\N	\N	上市系统	上市日常监管模块
827	40	system.uptime	System uptime	0	3	30s		uptime	0	0	14	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.12	\N	\N	上市系统	上市日常监管模块
828	42	vfs.file.cksum[/etc/passwd]	Checksum of /etc/passwd	0	1	15m			0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.12	\N	\N	上市系统	上市日常监管模块
829	12	system.cpu.util	CPU utilization	18	0	1m		%	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.12	system.cpu.util[,idle]	[{"type": "21", "params": "return (100 - value)", "error_handler": "0", "error_handler_params": ""}]	上市系统	上市日常监管模块
830	22	system.swap.size[,free]	Free swap space	0	3	1m		B	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.23	\N	\N	上市系统	上市日常监管模块
831	24	system.swap.size[,total]	Total swap space	0	3	1m		B	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.23	\N	\N	上市系统	上市日常监管模块
832	26	vm.memory.size[pavailable]	Available memory in %	0	0	1m		%	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.23	\N	\N	上市系统	上市日常监管模块
833	37	system.sw.os	Operating system	0	1	1h			0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.23	\N	\N	上市系统	上市日常监管模块
834	39	system.uname	System description	0	1	15m			0	0	12	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.23	\N	\N	上市系统	上市日常监管模块
835	41	system.users.num	Number of logged in users	0	3	1m			0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.23	\N	\N	上市系统	上市日常监管模块
836	28	vm.memory.utilization	Memory utilization	18	0	1m		%	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.23	vm.memory.size[pavailable]	[{"type": "21", "params": "return (100-value);", "error_handler": "0", "error_handler_params": ""}]	上市系统	上市日常监管模块
837	7	system.cpu.load[all,avg15]	Load average (15m avg)	0	0	1m	\N	\N	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.23	\N	\N	上市系统	上市日常监管模块
838	8	system.cpu.load[all,avg5]	Load average (5m avg)	0	0	1m	\N	\N	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.23	\N	\N	上市系统	上市日常监管模块
839	1	agent.hostname	Host name of Zabbix agent running	0	1	1h			0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.23	\N	\N	上市系统	上市日常监管模块
840	2	agent.ping	Zabbix agent ping	0	0	1m			0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.23	\N	\N	上市系统	上市日常监管模块
841	23	system.swap.size[,pfree]	Free swap space in %	0	0	1m		%	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.23	\N	\N	上市系统	上市日常监管模块
842	25	vm.memory.size[available]	Available memory	0	3	1m		B	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.23	\N	\N	上市系统	上市日常监管模块
843	3	agent.version	Version of Zabbix agent running	0	1	1h			0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.23	\N	\N	上市系统	上市日常监管模块
844	27	vm.memory.size[total]	Total memory	0	3	1m		B	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.23	\N	\N	上市系统	上市日常监管模块
845	4	zabbix[host,agent,available]	Zabbix agent availability	5	0	1m			0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.23	\N	\N	上市系统	上市日常监管模块
846	29	kernel.maxfiles	Maximum number of open file descriptors	0	3	1h			0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.23	\N	\N	上市系统	上市日常监管模块
847	5	system.cpu.intr	Interrupts per second	0	0	1m	\N	\N	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.23	\N	\N	上市系统	上市日常监管模块
848	9	system.cpu.num	Number of CPUs	0	3	1m	\N	\N	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.23	\N	\N	上市系统	上市日常监管模块
849	6	system.cpu.load[all,avg1]	Load average (1m avg)	0	0	1m			0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.23	\N	\N	上市系统	上市日常监管模块
850	10	system.cpu.switches	Context switches per second	0	0	1m	\N	\N	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.23	\N	\N	上市系统	上市日常监管模块
851	11	system.cpu.util[,idle]	CPU idle time	0	0	1m	\N	\N	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.23	\N	\N	上市系统	上市日常监管模块
852	13	system.cpu.util[,guest_nice]	CPU guest nice time	0	0	1m		%	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.23	\N	\N	上市系统	上市日常监管模块
853	14	system.cpu.util[,guest]	CPU guest time	0	0	1m		%	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.23	\N	\N	上市系统	上市日常监管模块
854	15	system.cpu.util[,interrupt]	CPU interrupt time	0	0	1m		%	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.23	\N	\N	上市系统	上市日常监管模块
855	16	system.cpu.util[,iowait]	CPU iowait time	0	0	1m		%	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.23	\N	\N	上市系统	上市日常监管模块
856	17	system.cpu.util[,nice]	CPU nice time	0	0	1m		%	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.23	\N	\N	上市系统	上市日常监管模块
857	18	system.cpu.util[,softirq]	CPU softirq time	0	0	1m		%	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.23	\N	\N	上市系统	上市日常监管模块
858	19	system.cpu.util[,steal]	CPU steal time	0	0	1m		%	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.23	\N	\N	上市系统	上市日常监管模块
859	20	system.cpu.util[,system]	CPU system time	0	0	1m		%	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.23	\N	\N	上市系统	上市日常监管模块
860	21	system.cpu.util[,user]	CPU user time	0	0	1m		%	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.23	\N	\N	上市系统	上市日常监管模块
861	30	kernel.maxproc	Maximum number of processes	0	3	1h			0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.23	\N	\N	上市系统	上市日常监管模块
862	31	proc.num	Number of processes	0	3	1m			0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.23	\N	\N	上市系统	上市日常监管模块
863	32	proc.num[,,run]	Number of running processes	0	3	1m			0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.23	\N	\N	上市系统	上市日常监管模块
864	33	system.boottime	System boot time	0	3	15m		unixtime	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.23	\N	\N	上市系统	上市日常监管模块
865	34	system.hostname	System name	0	1	1h			0	0	11	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.23	\N	\N	上市系统	上市日常监管模块
866	35	system.localtime	System local time	0	3	1m		unixtime	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.23	\N	\N	上市系统	上市日常监管模块
867	36	system.sw.arch	Operating system architecture	0	1	1h			0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.23	\N	\N	上市系统	上市日常监管模块
868	38	system.sw.packages	Software installed	0	4	1h			0	0	11	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.23	\N	\N	上市系统	上市日常监管模块
869	40	system.uptime	System uptime	0	3	30s		uptime	0	0	14	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.23	\N	\N	上市系统	上市日常监管模块
870	42	vfs.file.cksum[/etc/passwd]	Checksum of /etc/passwd	0	1	15m			0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.23	\N	\N	上市系统	上市日常监管模块
871	12	system.cpu.util	CPU utilization	18	0	1m		%	0	0	7	365	0	21001	f	f	pending	2026-04-30 17:26:59.866883	2026-04-30 17:26:59.866883	10.24.3.23	system.cpu.util[,idle]	[{"type": "21", "params": "return (100 - value)", "error_handler": "0", "error_handler_params": ""}]	上市系统	上市日常监管模块
\.


--
-- Name: items_review_id_seq; Type: SEQUENCE SET; Schema: zabbix_mac; Owner: -
--

SELECT pg_catalog.setval('zabbix_mac.items_review_id_seq', 871, true);


--
-- Name: items_review items_review_pkey; Type: CONSTRAINT; Schema: zabbix_mac; Owner: -
--

ALTER TABLE ONLY zabbix_mac.items_review
    ADD CONSTRAINT items_review_pkey PRIMARY KEY (id);


--
-- Name: idx_items_review_confirmed; Type: INDEX; Schema: zabbix_mac; Owner: -
--

CREATE INDEX idx_items_review_confirmed ON zabbix_mac.items_review USING btree (confirmed);


--
-- Name: idx_items_review_host_ip; Type: INDEX; Schema: zabbix_mac; Owner: -
--

CREATE INDEX idx_items_review_host_ip ON zabbix_mac.items_review USING btree (host_ip);


--
-- Name: idx_items_review_item; Type: INDEX; Schema: zabbix_mac; Owner: -
--

CREATE INDEX idx_items_review_item ON zabbix_mac.items_review USING btree (item_id);


--
-- Name: idx_items_review_master_item; Type: INDEX; Schema: zabbix_mac; Owner: -
--

CREATE INDEX idx_items_review_master_item ON zabbix_mac.items_review USING btree (master_item);


--
-- Name: items_review items_review_item_id_fkey; Type: FK CONSTRAINT; Schema: zabbix_mac; Owner: -
--

ALTER TABLE ONLY zabbix_mac.items_review
    ADD CONSTRAINT items_review_item_id_fkey FOREIGN KEY (item_id) REFERENCES zabbix_mac.items(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict 2II1TylsBAiQBvDOO3YtjOOYlVDed1LkpW7Y906dvOztelSYUBGj68ktdDOixmX

